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
    logger.info("macOS detected: Applied fork safety measures")

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
    print("Enhanced Redis management and retry handling loaded")
except ImportError as e:
    print(f"Enhanced Redis features not available (running standalone): {e}")
    ENHANCED_REDIS_AVAILABLE = False


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
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            print(f"\nReceived {signal_name}, initiating graceful shutdown...")
            self.shutdown_requested = True
            if self.current_job:
                print(f"Waiting for current job {self.current_job.id} to complete...")
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _update_heartbeat(self):
        """Update the worker heartbeat timestamp."""
        self.last_heartbeat = datetime.now()
    
    def _check_worker_health(self):
        """Check worker health and log status."""
        try:
            worker_status = self.worker.get_state()
            uptime = datetime.now() - self.stats['start_time']
            
            is_stuck = False
            if self.job_start_time and self.current_job:
                job_duration = datetime.now() - self.job_start_time
                if job_duration > timedelta(minutes=30):
                    is_stuck = True
                    logger.warning(f"Job {self.current_job.id} may be stuck (running for {job_duration})")
            
            logger.info(
                f"Health Check: Status={worker_status}, Uptime={uptime}, "
                f"Processed={self.stats['jobs_processed']}, Failed={self.stats['jobs_failed']}"
            )
            return {'status': worker_status, 'uptime': uptime, 'is_stuck': is_stuck, 'stats': self.stats}
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return None
    
    def _monitor_worker(self):
        """Background monitoring thread function."""
        print("Starting worker monitoring thread...")
        while not self.shutdown_requested:
            try:
                self._update_heartbeat()
                self._check_worker_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Monitoring thread error: {e}")
                time.sleep(5)
        print("Worker monitoring thread stopped.")
    
    def _job_started_callback(self, job, connection, worker):
        """Callback when a job starts."""
        self.current_job = job
        self.job_start_time = datetime.now()
        try:
            from app.utils.logging import get_logger
            job_logger = get_logger('app.worker')
            job_logger.info("🚀 Worker job started", extra={
                'extra_fields': {
                    'job_id': job.id,
                    'job_function': job.func_name,
                    'job_queue': job.origin
                }
            })
        except ImportError:
            logger.info(f"Job started: {job.id}")
    
    def _job_finished_callback(self, job, connection, worker, result):
        """Callback when a job finishes successfully."""
        duration = datetime.now() - self.job_start_time if self.job_start_time else None
        self.stats['jobs_processed'] += 1
        self.stats['last_job_time'] = datetime.now()
        self.current_job = None
        self.job_start_time = None
        try:
            from app.utils.logging import get_logger
            job_logger = get_logger('app.worker')
            job_logger.info("✅ Worker job completed", extra={
                'extra_fields': {
                    'job_id': job.id,
                    'job_function': job.func_name,
                    'duration_ms': round(duration.total_seconds() * 1000, 2) if duration else None
                }
            })
        except ImportError:
            logger.info(f"Job completed: {job.id} in {duration}")
    
    def _job_failed_callback(self, job, connection, worker, exc_type, exc_value, traceback):
        """Callback when a job fails."""
        duration = datetime.now() - self.job_start_time if self.job_start_time else None
        self.stats['jobs_failed'] += 1
        self.current_job = None
        self.job_start_time = None
        try:
            from app.utils.logging import get_logger
            job_logger = get_logger('app.worker')
            job_logger.error("❌ Worker job failed", extra={
                'extra_fields': {
                    'job_id': job.id,
                    'job_function': job.func_name,
                    'duration_ms': round(duration.total_seconds() * 1000, 2) if duration else None,
                    'error_type': exc_type.__name__,
                    'error_message': str(exc_value)
                }
            })
        except ImportError:
            logger.error(f"Job failed: {job.id} after {duration} - {exc_type.__name__}: {exc_value}")
    
    def start_monitoring(self):
        """Start the monitoring thread."""
        if self.monitoring_enabled and not self.monitor_thread:
            self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
            self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.shutdown_requested = True
            self.monitor_thread.join(timeout=5)
            print("Worker monitoring stopped.")
    
    def work(self, **kwargs):
        """Start the worker with monitoring."""
        self._setup_signal_handlers()
        self.start_monitoring()
        
        try:
            print("Starting monitored worker...")
            self.worker.work(**kwargs)
        finally:
            self.stop_monitoring()
            uptime = datetime.now() - self.stats['start_time']
            print(f"Worker shutdown complete. Final stats - "
                  f"Uptime: {uptime}, Jobs Processed: {self.stats['jobs_processed']}, "
                  f"Jobs Failed: {self.stats['jobs_failed']}")
    
    def _signal_handler(self, signum, frame):
        """Enhanced signal handler that integrates with RQ's shutdown."""
        signal_name = signal.Signals(signum).name
        logger.warning(f"\nReceived signal: {signal_name}. Requesting worker to stop gracefully.")
        self.shutdown_requested = True
        
        # Tell the worker to stop after the current job
        self.worker.request_stop(signum, frame)
        
        # Start a shutdown timer
        shutdown_timer = threading.Timer(10.0, self._force_shutdown)
        shutdown_timer.start()
    
    def _force_shutdown(self):
        """Force shutdown if graceful period expires."""
        if not self.worker.is_stopped:
            logger.error("Graceful shutdown period expired. Forcing exit.")
            # This is a last resort; ideally the worker stops on its own
            os._exit(1)


def create_worker(use_threading=False, queues=None):
    """Create and configure an RQ worker."""
    if queues is None:
        queues = DEFAULT_QUEUES
    
    redis_url = os.getenv('RQ_REDIS_URL', 'redis://localhost:6379/0')
    conn = Redis.from_url(redis_url)
    
    if use_threading:
        print("Creating threading-based worker...")
        worker = create_threading_worker(conn, queues)
    else:
        if ENHANCED_REDIS_AVAILABLE:
            print("Using enhanced Redis connection manager...")
            try:
                conn = redis_manager.get_connection()
            except Exception as e:
                logger.warning(f"Could not get enhanced redis connection: {e}")
        
        print("Creating platform-optimized worker...")
        worker = configure_worker_for_platform(conn, queues=queues)
    
    # Add enhanced exception handler if available
    if ENHANCED_REDIS_AVAILABLE:
        print("Adding enhanced job retry handling...")
        worker.push_exc_handler(handle_job_exception)
    
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
    
    print_worker_startup_info()
    
    if args.config:
        return
    
    try:
        worker = create_worker(use_threading=args.threading, queues=args.queues)
        monitored_worker = MonitoredWorker(worker, monitoring_enabled=args.monitoring)
        
        if args.test:
            print("Running in test mode - will process one job and exit.")
            monitored_worker.work(burst=True, max_jobs=1)
        else:
            print("Starting monitored worker (Press Ctrl+C to stop)...")
            monitored_worker.work()
            
    except KeyboardInterrupt:
        print("\nWorker stopped by user.")
    except Exception as e:
        logger.critical(f"Worker failed with unhandled exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
