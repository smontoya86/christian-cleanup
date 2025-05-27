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

# CRITICAL: Set macOS fork safety BEFORE any other imports
# This must be done before any libraries that might use Objective-C are loaded
if platform.system() == 'Darwin':  # macOS
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
    print("macOS detected: Applied fork safety measures (OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES)")

# Import standalone worker configuration to avoid Flask app initialization issues
from worker_config_standalone import (
    configure_worker_for_platform, 
    create_threading_worker,
    print_worker_startup_info,
    DEFAULT_QUEUES
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        
        logger.info(f"MonitoredWorker initialized for worker {self.worker.name}")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
            self.shutdown_requested = True
            
            # Give current job time to complete
            if self.current_job:
                logger.info(f"Waiting for current job {self.current_job.id} to complete...")
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
                    logger.warning(f"Job {self.current_job.id} has been running for {job_duration}, may be stuck")
            
            # Log health status
            logger.info(f"Worker Health Check - Status: {worker_status}, "
                       f"Uptime: {uptime}, Jobs Processed: {self.stats['jobs_processed']}, "
                       f"Jobs Failed: {self.stats['jobs_failed']}, Stuck: {is_stuck}")
            
            return {
                'status': worker_status,
                'uptime': uptime,
                'is_stuck': is_stuck,
                'last_heartbeat': self.last_heartbeat,
                'stats': self.stats.copy()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return None
    
    def _monitor_worker(self):
        """Background monitoring thread function."""
        logger.info("Worker monitoring thread started")
        
        while not self.shutdown_requested:
            try:
                # Update heartbeat
                self._update_heartbeat()
                
                # Perform health check
                health_status = self._check_worker_health()
                
                # Sleep until next check
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Monitoring thread error: {e}")
                time.sleep(5)  # Brief pause before retrying
        
        logger.info("Worker monitoring thread stopped")
    
    def _job_started_callback(self, job, connection, worker):
        """Callback when a job starts."""
        self.current_job = job
        self.job_start_time = datetime.now()
        logger.info(f"Job started: {job.id} ({job.func_name})")
    
    def _job_finished_callback(self, job, connection, worker, result):
        """Callback when a job finishes successfully."""
        duration = datetime.now() - self.job_start_time if self.job_start_time else None
        self.stats['jobs_processed'] += 1
        self.stats['last_job_time'] = datetime.now()
        self.current_job = None
        self.job_start_time = None
        
        logger.info(f"Job completed: {job.id} in {duration}")
    
    def _job_failed_callback(self, job, connection, worker, exc_type, exc_value, traceback):
        """Callback when a job fails."""
        duration = datetime.now() - self.job_start_time if self.job_start_time else None
        self.stats['jobs_failed'] += 1
        self.stats['last_job_time'] = datetime.now()
        self.current_job = None
        self.job_start_time = None
        
        logger.error(f"Job failed: {job.id} after {duration} - {exc_type.__name__}: {exc_value}")
    
    def start_monitoring(self):
        """Start the monitoring thread."""
        if self.monitoring_enabled and not self.monitor_thread:
            self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
            self.monitor_thread.start()
            logger.info("Worker monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        if self.monitor_thread:
            self.shutdown_requested = True
            self.monitor_thread.join(timeout=5)
            logger.info("Worker monitoring stopped")
    
    def work(self, **kwargs):
        """Start the worker with monitoring and graceful shutdown."""
        # Setup job callbacks for monitoring
        self.worker.push_exc_handler(self._job_failed_callback)
        
        # Start monitoring if enabled
        self.start_monitoring()
        
        try:
            logger.info("Starting monitored worker...")
            
            # Override RQ's signal handlers to use our graceful shutdown
            original_sigterm_handler = signal.signal(signal.SIGTERM, self._signal_handler)
            original_sigint_handler = signal.signal(signal.SIGINT, self._signal_handler)
            
            # Start the worker - RQ will handle the main work loop
            self.worker.work(**kwargs)
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            self.shutdown_requested = True
        
        finally:
            # Cleanup
            self.stop_monitoring()
            
            # Final statistics
            uptime = datetime.now() - self.stats['start_time']
            logger.info(f"Worker shutdown complete. Final stats - "
                       f"Uptime: {uptime}, Jobs Processed: {self.stats['jobs_processed']}, "
                       f"Jobs Failed: {self.stats['jobs_failed']}")
    
    def _signal_handler(self, signum, frame):
        """Enhanced signal handler that integrates with RQ's shutdown."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")
        self.shutdown_requested = True
        
        # Give current job time to complete
        if self.current_job:
            logger.info(f"Waiting for current job {self.current_job.id} to complete...")
        
        # Call RQ's default signal handler to ensure proper shutdown
        self.worker.request_stop(signum, frame)


def create_worker(use_threading=False, queues=None):
    """
    Create an RQ worker with appropriate configuration for the platform.
    
    Args:
        use_threading: If True, create a threading-optimized worker
        queues: List of queue names to listen on
    
    Returns:
        Configured RQ Worker instance
    """
    # Get Redis connection
    redis_url = os.getenv('RQ_REDIS_URL', 'redis://localhost:6379/0')
    conn = Redis.from_url(redis_url)
    
    if queues is None:
        queues = DEFAULT_QUEUES
    
    # Create worker based on mode
    if use_threading:
        print("Creating threading-based worker...")
        worker = create_threading_worker(conn, queues=queues)
    else:
        print("Creating platform-optimized worker...")
        worker = configure_worker_for_platform(conn, queues=queues)
    
    return worker


def main():
    """Main worker entry point with command line argument support."""
    parser = argparse.ArgumentParser(description='RQ Worker for Christian Cleanup')
    parser.add_argument('--threading', action='store_true', 
                       help='Use threading-based worker mode (alternative to fork mode)')
    parser.add_argument('--queues', nargs='+', default=None,
                       help='Specify queues to listen on (default: high, default, low)')
    parser.add_argument('--info', action='store_true',
                       help='Show worker configuration info and exit')
    parser.add_argument('--test-mode', action='store_true',
                       help='Run in test mode (process one job and exit)')
    parser.add_argument('--no-monitoring', action='store_true',
                       help='Disable worker monitoring and health checks')
    parser.add_argument('--health-check-interval', type=int, default=30,
                       help='Health check interval in seconds (default: 30)')
    
    args = parser.parse_args()
    
    # Check for threading mode environment variable
    env_threading = os.environ.get('RQ_WORKER_USE_THREADING', 'false').lower() == 'true'
    use_threading = args.threading or env_threading
    
    # Create worker
    try:
        worker = create_worker(use_threading=use_threading, queues=args.queues)
        
        # Show configuration info
        print_worker_startup_info(worker)
        
        if args.info:
            print("Worker configuration displayed. Exiting.")
            return
        
        # Create monitored worker wrapper
        monitoring_enabled = not args.no_monitoring
        monitored_worker = MonitoredWorker(worker, monitoring_enabled=monitoring_enabled)
        monitored_worker.health_check_interval = args.health_check_interval
        
        # Start worker
        if args.test_mode:
            print("Running in test mode - will process one job and exit")
            worker.work(burst=True, max_jobs=1)
        else:
            print("Starting monitored worker... (Press Ctrl+C to stop)")
            monitored_worker.work()
            
    except KeyboardInterrupt:
        print("\nWorker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
