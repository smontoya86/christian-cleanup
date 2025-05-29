#!/usr/bin/env python3
"""
RQ Worker for Christian Cleanup application.
Handles background job processing with macOS fork safety measures, threading support,
process monitoring, and graceful shutdown capabilities.
"""

import os
import platform
import sys
import argparse
import signal
import time
import threading
import logging
from datetime import datetime, timedelta

from dotenv import load_dotenv
from redis import Redis
from rq import Worker
from rq.worker import WorkerStatus

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Set up worker logging before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CRITICAL: Set macOS fork safety BEFORE any other imports
# This must be done before any libraries that might use Objective-C are loaded
if platform.system() == 'Darwin':  # macOS
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
    logger.info("macOS detected: Applied fork safety measures",
        extra={'extra_fields': {
            'platform': platform.system(),
            'fork_safety_setting': 'OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES',
            'reason': 'prevent_macos_fork_issues'
        }})

# Import standalone worker configuration to avoid Flask app initialization issues
from worker_config_standalone import (
    configure_worker_for_platform, 
    create_threading_worker,
    print_worker_startup_info,
    DEFAULT_QUEUES
)

# Import enhanced Redis management and retry handling (if available)
try:
    from app.utils.redis_manager import redis_manager
    from app.utils.job_retry import handle_job_exception
    ENHANCED_REDIS_AVAILABLE = True
    logger.info("Enhanced Redis management and retry handling loaded",
        extra={'extra_fields': {
            'redis_manager_available': True,
            'job_retry_available': True,
            'enhanced_features': ['redis_manager', 'job_retry']
        }})
except ImportError as e:
    ENHANCED_REDIS_AVAILABLE = False
    logger.warning("Enhanced Redis features not available (running standalone)",
        extra={'extra_fields': {
            'redis_manager_available': False,
            'job_retry_available': False,
            'import_error': str(e),
            'fallback_mode': 'standalone'
        }})


class MonitoredWorker:
    """
    Enhanced RQ Worker with monitoring, health checks, and graceful shutdown capabilities.
    """
    
    def __init__(self, worker, monitoring_enabled=True):
        self.worker = worker
        self.monitoring_enabled = monitoring_enabled
        self.shutdown_requested = False
        self.health_check_interval = 30  # seconds
        self.last_heartbeat = datetime.now()
        self.job_start_time = None
        self.current_job = None
        self.monitor_thread = None
        self.stats = {
            'jobs_processed': 0,
            'jobs_failed': 0,
            'start_time': datetime.now(),
            'last_job_time': None
        }
        
        # Signal handlers will be setup in work() method
        
        logger.info("MonitoredWorker initialized",
            extra={'extra_fields': {
                'worker_name': self.worker.name,
                'monitoring_enabled': monitoring_enabled,
                'health_check_interval': self.health_check_interval,
                'init_time': self.stats['start_time'].isoformat()
            }})
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info("Received shutdown signal, initiating graceful shutdown",
                extra={'extra_fields': {
                    'signal_name': signal_name,
                    'signal_number': signum,
                    'shutdown_phase': 'initiated',
                    'current_job_id': self.current_job.id if self.current_job else None
                }})
            self.shutdown_requested = True
            
            # Give current job time to complete
            if self.current_job:
                logger.info("Waiting for current job to complete",
                    extra={'extra_fields': {
                        'job_id': self.current_job.id,
                        'job_function': self.current_job.func_name,
                        'graceful_shutdown': True
                    }})
                # RQ will handle job completion, we just set the flag
            
        # Register handlers for common shutdown signals
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination request
        
        # On Unix systems, also handle SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal_handler)
    
    def _update_heartbeat(self):
        """Update the worker heartbeat timestamp."""
        self.last_heartbeat = datetime.now()
    
    def _check_worker_health(self):
        """Check worker health and log status."""
        try:
            # Check if worker is still responsive
            worker_status = self.worker.get_state()
            
            # Calculate uptime
            uptime = datetime.now() - self.stats['start_time']
            
            # Check for stuck jobs (jobs running longer than expected)
            stuck_job_threshold = timedelta(minutes=30)  # Configurable threshold
            is_stuck = False
            
            if self.job_start_time and self.current_job:
                job_duration = datetime.now() - self.job_start_time
                if job_duration > stuck_job_threshold:
                    is_stuck = True
                    logger.warning("Job may be stuck - running longer than threshold",
                        extra={'extra_fields': {
                            'job_id': self.current_job.id,
                            'job_function': self.current_job.func_name,
                            'job_duration_seconds': job_duration.total_seconds(),
                            'stuck_threshold_seconds': stuck_job_threshold.total_seconds(),
                            'is_stuck': True
                        }})
            
            # Log health status
            logger.info("Worker health check completed",
                extra={'extra_fields': {
                    'worker_status': str(worker_status),
                    'uptime_seconds': uptime.total_seconds(),
                    'jobs_processed': self.stats['jobs_processed'],
                    'jobs_failed': self.stats['jobs_failed'],
                    'is_stuck': is_stuck,
                    'last_heartbeat': self.last_heartbeat.isoformat(),
                    'health_check_type': 'periodic'
                }})
            
            return {
                'status': worker_status,
                'uptime': uptime,
                'is_stuck': is_stuck,
                'last_heartbeat': self.last_heartbeat,
                'stats': self.stats.copy()
            }
            
        except Exception as e:
            logger.error("Health check failed",
                extra={'extra_fields': {
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'health_check_failed': True
                }})
            return None
    
    def _monitor_worker(self):
        """Background monitoring thread function."""
        logger.info("Worker monitoring thread started",
            extra={'extra_fields': {
                'monitor_thread_id': threading.get_ident(),
                'monitoring_interval': self.health_check_interval,
                'monitor_phase': 'started'
            }})
        
        while not self.shutdown_requested:
            try:
                # Update heartbeat
                self._update_heartbeat()
                
                # Perform health check
                health_status = self._check_worker_health()
                
                # Sleep until next check
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error("Monitoring thread error",
                    extra={'extra_fields': {
                        'error_type': type(e).__name__,
                        'error_message': str(e),
                        'monitor_phase': 'error',
                        'retry_delay': 5
                    }})
                time.sleep(5)  # Brief pause before retrying
        
        logger.info("Worker monitoring thread stopped",
            extra={'extra_fields': {
                'monitor_thread_id': threading.get_ident(),
                'monitor_phase': 'stopped',
                'shutdown_requested': self.shutdown_requested
            }})
    
    def _job_started_callback(self, job, connection, worker):
        """Callback when a job starts."""
        self.current_job = job
        self.job_start_time = datetime.now()
        
        # Import logging utilities
        try:
            from app.utils.logging import get_logger
            from app.utils.metrics import metrics_collector
            job_logger = get_logger('app.worker')
            
            job_logger.info("🚀 Worker job started", extra={
                'extra_fields': {
                    'job_id': job.id,
                    'job_function': job.func_name,
                    'job_queue': job.origin,
                    'worker_name': worker.name,
                    'job_args': str(job.args)[:200],  # Truncate long args
                    'job_kwargs': str(job.kwargs)[:200],  # Truncate long kwargs
                    'start_time': self.job_start_time.isoformat()
                }
            })
        except ImportError:
            logger.info("Worker job started",
                extra={'extra_fields': {
                    'job_id': job.id,
                    'job_function': job.func_name,
                    'worker_name': worker.name,
                    'start_time': self.job_start_time.isoformat(),
                    'logging_mode': 'basic'
                }})
    
    def _job_finished_callback(self, job, connection, worker, result):
        """Callback when a job finishes successfully."""
        duration = datetime.now() - self.job_start_time if self.job_start_time else None
        duration_seconds = duration.total_seconds() if duration else 0
        
        self.stats['jobs_processed'] += 1
        self.stats['last_job_time'] = datetime.now()
        self.current_job = None
        self.job_start_time = None
        
        # Import logging utilities
        try:
            from app.utils.logging import get_logger
            job_logger = get_logger('app.worker')
            
            job_logger.info("✅ Worker job completed successfully", extra={
                'extra_fields': {
                    'job_id': job.id,
                    'job_function': job.func_name,
                    'duration_seconds': duration_seconds,
                    'worker_name': worker.name,
                    'result_type': type(result).__name__ if result else 'None',
                    'completion_time': datetime.now().isoformat()
                }
            })
        except ImportError:
            logger.info("Worker job completed successfully",
                extra={'extra_fields': {
                    'job_id': job.id,
                    'job_function': job.func_name,
                    'duration_seconds': duration_seconds,
                    'worker_name': worker.name,
                    'completion_time': datetime.now().isoformat(),
                    'logging_mode': 'basic'
                }})
    
    def _job_failed_callback(self, job, connection, worker, exc_type, exc_value, traceback):
        """Callback when a job fails."""
        duration = datetime.now() - self.job_start_time if self.job_start_time else None
        duration_seconds = duration.total_seconds() if duration else 0
        
        self.stats['jobs_failed'] += 1
        self.current_job = None
        self.job_start_time = None
        
        # Import logging utilities
        try:
            from app.utils.logging import get_logger
            job_logger = get_logger('app.worker')
            
            job_logger.error("❌ Worker job failed", extra={
                'extra_fields': {
                    'job_id': job.id,
                    'job_function': job.func_name,
                    'duration_seconds': duration_seconds,
                    'worker_name': worker.name,
                    'exception_type': exc_type.__name__ if exc_type else 'Unknown',
                    'exception_message': str(exc_value) if exc_value else 'Unknown error',
                    'failure_time': datetime.now().isoformat()
                }
            })
        except ImportError:
            logger.error("Worker job failed",
                extra={'extra_fields': {
                    'job_id': job.id,
                    'job_function': job.func_name,
                    'duration_seconds': duration_seconds,
                    'worker_name': worker.name,
                    'exception_type': exc_type.__name__ if exc_type else 'Unknown',
                    'exception_message': str(exc_value) if exc_value else 'Unknown error',
                    'failure_time': datetime.now().isoformat(),
                    'logging_mode': 'basic'
                }})
        
        # Use enhanced error handling if available
        if ENHANCED_REDIS_AVAILABLE:
            try:
                handle_job_exception(job, exc_type, exc_value, traceback)
            except Exception as e:
                logger.error("Enhanced job exception handling failed",
                    extra={'extra_fields': {
                        'job_id': job.id,
                        'handler_error': str(e),
                        'fallback_mode': 'basic'
                    }})
    
    def start_monitoring(self):
        """Start the monitoring thread."""
        if self.monitoring_enabled and not self.monitor_thread:
            self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
            self.monitor_thread.start()
            logger.info("Worker monitoring started",
                extra={'extra_fields': {
                    'monitor_thread_id': self.monitor_thread.ident,
                    'monitoring_enabled': True
                }})
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.shutdown_requested = True
            self.monitor_thread.join(timeout=5)
            logger.info("Worker monitoring stopped",
                extra={'extra_fields': {
                    'monitor_thread_stopped': True,
                    'graceful_shutdown': True
                }})
    
    def work(self, **kwargs):
        """Start the worker with monitoring."""
        try:
            # Setup signal handlers
            self._setup_signal_handlers()
            
            # Start monitoring
            self.start_monitoring()
            
            # Add job callbacks
            self.worker.push_exc_handler(self._job_failed_callback)
            
            # Log worker startup
            logger.info("Starting monitored worker",
                extra={'extra_fields': {
                    'worker_name': self.worker.name,
                    'queues': [q.name for q in self.worker.queues],
                    'monitoring_enabled': self.monitoring_enabled,
                    'start_time': datetime.now().isoformat()
                }})
            
            # Start the worker
            self.worker.work(**kwargs)
            
        except Exception as e:
            logger.error("Worker encountered fatal error",
                extra={'extra_fields': {
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'worker_state': 'failed'
                }})
            raise
        finally:
            self.stop_monitoring()
            logger.info("Worker shutdown completed",
                extra={'extra_fields': {
                    'final_stats': self.stats,
                    'shutdown_time': datetime.now().isoformat()
                }})
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        signal_name = signal.Signals(signum).name
        logger.info("Received shutdown signal",
            extra={'extra_fields': {
                'signal_name': signal_name,
                'signal_number': signum,
                'current_job': self.current_job.id if self.current_job else None
            }})
        
        self.shutdown_requested = True
        
        # Request worker to stop gracefully  
        if hasattr(self.worker, 'request_stop'):
            self.worker.request_stop()


def create_worker(use_threading=False, queues=None):
    """Create and configure an RQ worker."""
    if queues is None:
        queues = DEFAULT_QUEUES
    
    # Get Redis connection
    redis_url = os.getenv('RQ_REDIS_URL', 'redis://localhost:6379/0')
    connection = Redis.from_url(redis_url)
    
    logger.info("Creating worker",
        extra={'extra_fields': {
            'redis_url': redis_url,
            'queues': queues,
            'use_threading': use_threading,
            'enhanced_redis_available': ENHANCED_REDIS_AVAILABLE
        }})
    
    if use_threading:
        logger.info("Creating threading-based worker",
            extra={'extra_fields': {
                'worker_type': 'threading',
                'platform': platform.system(),
                'reason': 'threading_requested'
            }})
        worker = create_threading_worker(connection, queues)
    else:
        # Use enhanced Redis connection if available
        if ENHANCED_REDIS_AVAILABLE:
            logger.info("Using enhanced Redis connection manager",
                extra={'extra_fields': {
                    'worker_type': 'enhanced',
                    'redis_manager': True,
                    'connection_pooling': True
                }})
            try:
                connection = redis_manager.get_connection()
            except Exception as e:
                logger.warning("Failed to get enhanced Redis connection, falling back to basic",
                    extra={'extra_fields': {
                        'error': str(e),
                        'fallback': 'basic_redis'
                    }})
        
        logger.info("Creating platform-optimized worker",
            extra={'extra_fields': {
                'worker_type': 'platform_optimized',
                'platform': platform.system()
            }})
        worker = configure_worker_for_platform(connection, queues)
    
    # Add enhanced job retry handling if available
    if ENHANCED_REDIS_AVAILABLE:
        logger.info("Adding enhanced job retry handling",
            extra={'extra_fields': {
                'retry_handling': True,
                'enhanced_features': True
            }})
        # Additional retry configuration would go here
    
    return worker


def main():
    """Main entry point for the worker."""
    parser = argparse.ArgumentParser(description='RQ Worker for Christian Cleanup application')
    parser.add_argument('--queues', '-q', nargs='+', default=DEFAULT_QUEUES,
                       help='Queues to listen on')
    parser.add_argument('--threading', action='store_true',
                       help='Use threading-based worker')
    parser.add_argument('--monitoring', action='store_true', default=True,
                       help='Enable worker monitoring')
    parser.add_argument('--config', action='store_true',
                       help='Show worker configuration and exit')
    parser.add_argument('--test', action='store_true',
                       help='Run in test mode (process one job and exit)')
    
    args = parser.parse_args()
    
    logger.info("Worker startup initiated",
        extra={'extra_fields': {
            'queues': args.queues,
            'threading_mode': args.threading,
            'monitoring_enabled': args.monitoring,
            'test_mode': args.test,
            'platform': platform.system(),
            'python_version': sys.version
        }})
    
    if args.config:
        print_worker_startup_info()
        logger.info("Worker configuration displayed, exiting",
            extra={'extra_fields': {
                'config_mode': True,
                'exit_reason': 'config_display'
            }})
        return
    
    try:
        # Create worker
        worker = create_worker(use_threading=args.threading, queues=args.queues)
        
        # Create monitored wrapper
        monitored_worker = MonitoredWorker(worker, monitoring_enabled=args.monitoring)
        
        if args.test:
            logger.info("Running in test mode - will process one job and exit",
                extra={'extra_fields': {
                    'test_mode': True,
                    'max_jobs': 1
                }})
            monitored_worker.work(burst=True, max_jobs=1)
        else:
            logger.info("Starting monitored worker (Press Ctrl+C to stop)",
                extra={'extra_fields': {
                    'worker_mode': 'continuous',
                    'shutdown_signal': 'SIGINT'
                }})
            monitored_worker.work()
            
    except KeyboardInterrupt:
        logger.info("Worker stopped by user",
            extra={'extra_fields': {
                'shutdown_reason': 'keyboard_interrupt',
                'graceful_shutdown': True
            }})
    except Exception as e:
        logger.error("Worker failed with unexpected error",
            extra={'extra_fields': {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'shutdown_reason': 'fatal_error'
            }})
        sys.exit(1)


if __name__ == '__main__':
    main() 