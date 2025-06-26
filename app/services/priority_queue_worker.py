"""
Priority Queue Worker for Christian Music Analysis

A dedicated worker that processes analysis jobs from our priority queue system.
Supports priority-based job processing, graceful shutdown, and health monitoring.
"""

import logging
import time
import signal
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from flask import current_app

from .priority_analysis_queue import PriorityAnalysisQueue, AnalysisJob, JobType, JobStatus, JobPriority
from .unified_analysis_service import UnifiedAnalysisService

logger = logging.getLogger(__name__)


class PriorityQueueWorker:
    """
    Worker that processes analysis jobs from the priority queue.
    
    Features:
    - Priority-based job processing (HIGH -> MEDIUM -> LOW)
    - Graceful shutdown handling
    - Job interruption support for higher priority jobs
    - Health monitoring and statistics
    - Automatic retry on failures
    """
    
    def __init__(self, app=None, poll_interval: float = 1.0, 
                 queue=None, analysis_service=None):
        """
        Initialize the priority queue worker.
        
        Args:
            app: Flask application instance (optional)
            poll_interval: How often to check for new jobs (seconds)
            queue: Priority queue instance (optional, for testing)
            analysis_service: Analysis service instance (optional, for testing)
        """
        self.app = app
        self.poll_interval = poll_interval
        self.running = False
        self.shutdown_requested = False
        self.current_job: Optional[AnalysisJob] = None
        self.worker_thread: Optional[threading.Thread] = None
        
        # Initialize services
        self.queue = queue or PriorityAnalysisQueue()
        self.analysis_service = analysis_service or UnifiedAnalysisService()
        
        # Statistics
        self.stats = {
            'jobs_processed': 0,
            'jobs_failed': 0,
            'jobs_interrupted': 0,
            'start_time': datetime.now(),
            'last_job_time': None,
            'last_heartbeat': datetime.now()
        }
        
        # Setup signal handlers
        self._setup_signal_handlers()
        
        logger.info("PriorityQueueWorker initialized")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"Received {signal_name}, initiating graceful shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self, background: bool = True) -> None:
        """
        Start the worker.
        
        Args:
            background: If True, run in background thread. If False, run in current thread.
        """
        if self.running:
            logger.warning("Worker is already running")
            return
        
        self.running = True
        self.shutdown_requested = False
        
        logger.info("Starting PriorityQueueWorker")
        
        if background:
            self.worker_thread = threading.Thread(target=self._work_loop, daemon=True)
            self.worker_thread.start()
            logger.info("Worker started in background thread")
        else:
            self._work_loop()
    
    def shutdown(self, timeout: float = 30.0) -> None:
        """
        Gracefully shutdown the worker.
        
        Args:
            timeout: Maximum time to wait for current job to complete
        """
        if not self.running:
            return
        
        logger.info("Shutting down PriorityQueueWorker...")
        self.shutdown_requested = True
        
        # Wait for current job to complete
        if self.current_job:
            logger.info(f"Waiting for current job {self.current_job.job_id} to complete...")
            start_time = time.time()
            while self.current_job and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.current_job:
                logger.warning(f"Job {self.current_job.job_id} did not complete within timeout")
        
        # Wait for worker thread to finish
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
        
        self.running = False
        uptime = datetime.now() - self.stats['start_time']
        logger.info(f"Worker shutdown complete. Uptime: {uptime}, "
                   f"Jobs processed: {self.stats['jobs_processed']}, "
                   f"Jobs failed: {self.stats['jobs_failed']}")
    
    def _work_loop(self) -> None:
        """Main worker loop that processes jobs from the priority queue."""
        logger.info("Worker loop started")
        
        while not self.shutdown_requested:
            try:
                # Update heartbeat
                self.stats['last_heartbeat'] = datetime.now()
                
                # Check for higher priority job that could interrupt current work
                if self.current_job and self._should_interrupt_current_job():
                    self._interrupt_current_job()
                
                # Get next job from queue
                job = self.queue.dequeue()
                
                if job:
                    self._process_job(job)
                else:
                    # No jobs available, sleep and continue
                    time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                time.sleep(5.0)  # Back off on errors
        
        logger.info("Worker loop stopped")
    
    def _should_interrupt_current_job(self) -> bool:
        """
        Check if current job should be interrupted for a higher priority job.
        
        Returns:
            True if current job should be interrupted
        """
        if not self.current_job:
            return False
        
        # Check if there's a higher priority job waiting
        queue_status = self.queue.get_queue_status()
        
        # Only interrupt for significantly higher priority jobs
        current_priority = self.current_job.priority.value
        
        # Check for high priority jobs if current is medium/low
        priority_counts = queue_status.get('priority_counts', {})
        if current_priority > 1 and priority_counts.get('HIGH', 0) > 0:
            return True
        
        # Check for medium priority jobs if current is low
        if current_priority > 2 and priority_counts.get('MEDIUM', 0) > 0:
            return True
        
        return False
    
    def _interrupt_current_job(self) -> None:
        """Interrupt the current job and re-queue it."""
        if not self.current_job:
            return
        
        logger.info(f"Interrupting job {self.current_job.job_id} for higher priority work")
        
        # Mark job as interrupted and re-queue it
        self.queue.interrupt_job(self.current_job.job_id)
        self.stats['jobs_interrupted'] += 1
        self.current_job = None
    
    def _process_job(self, job: AnalysisJob) -> None:
        """
        Process a single analysis job.
        
        Args:
            job: The analysis job to process
        """
        self.current_job = job
        start_time = datetime.now()
        
        logger.info(f"Processing {job.job_type.value} job {job.job_id} "
                   f"(priority: {job.priority.name}, user: {job.user_id})")
        
        try:
            # Process based on job type
            if job.job_type == JobType.SONG_ANALYSIS:
                self._process_song_analysis(job)
            elif job.job_type == JobType.PLAYLIST_ANALYSIS:
                self._process_playlist_analysis(job)
            elif job.job_type == JobType.BACKGROUND_ANALYSIS:
                self._process_background_analysis(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
            
            # Mark job as completed
            duration = datetime.now() - start_time
            self.queue.complete_job(job.job_id, success=True)
            self.stats['jobs_processed'] += 1
            self.stats['last_job_time'] = datetime.now()
            
            logger.info(f"Completed job {job.job_id} in {duration.total_seconds():.2f}s")
            
        except Exception as e:
            # Mark job as failed
            duration = datetime.now() - start_time
            error_msg = f"Job failed: {str(e)}"
            self.queue.complete_job(job.job_id, success=False, error_message=error_msg)
            self.stats['jobs_failed'] += 1
            
            logger.error(f"Job {job.job_id} failed after {duration.total_seconds():.2f}s: {e}",
                        exc_info=True)
        
        finally:
            self.current_job = None
    
    def _process_song_analysis(self, job: AnalysisJob) -> None:
        """Process a single song analysis job."""
        song_id = job.metadata.get('song_id')
        if not song_id:
            raise ValueError("Song analysis job missing song_id in metadata")
        
        # Use the existing analysis service but ensure it doesn't do immediate processing
        # Instead, we'll call the core analysis logic directly
        result = self._execute_song_analysis(song_id, job.user_id)
        
        # Handle case where result is None (shouldn't happen but be safe)
        if result is None:
            result = {
                'score': 0,
                'concern_level': 'high',
                'status': 'failed',
                'themes': [],
                'explanation': 'Analysis returned no result'
            }
        
        # Update job metadata with results
        job.metadata['analysis_result'] = {
            'score': result.get('score'),
            'concern_level': result.get('concern_level'),
            'completed_at': datetime.now().isoformat()
        }
    
    def _process_playlist_analysis(self, job: AnalysisJob) -> None:
        """Process a playlist analysis job."""
        playlist_id = job.metadata.get('playlist_id')
        if not playlist_id:
            raise ValueError("Playlist analysis job missing playlist_id in metadata")
        
        # Process all songs in the playlist
        song_ids = job.metadata.get('song_ids', [])
        completed_songs = 0
        
        for song_id in song_ids:
            # Check if we should be interrupted
            if self.shutdown_requested or self._should_interrupt_current_job():
                break
            
            try:
                self._execute_song_analysis(song_id, job.user_id)
                completed_songs += 1
            except Exception as e:
                logger.warning(f"Failed to analyze song {song_id} in playlist {playlist_id}: {e}")
        
        # Update job metadata
        job.metadata['analysis_result'] = {
            'completed_songs': completed_songs,
            'total_songs': len(song_ids),
            'completed_at': datetime.now().isoformat()
        }
    
    def _process_background_analysis(self, job: AnalysisJob) -> None:
        """Process a background analysis job."""
        song_ids = job.metadata.get('song_ids', [])
        if not song_ids:
            raise ValueError("Background analysis job missing song_ids in metadata")
        
        completed_songs = 0
        
        for song_id in song_ids:
            # Check if we should be interrupted (background jobs are lowest priority)
            if self.shutdown_requested or self._should_interrupt_current_job():
                break
            
            try:
                self._execute_song_analysis(song_id, job.user_id)
                completed_songs += 1
            except Exception as e:
                logger.warning(f"Failed to analyze song {song_id} in background job: {e}")
        
        # Update job metadata
        job.metadata['analysis_result'] = {
            'completed_songs': completed_songs,
            'total_songs': len(song_ids),
            'completed_at': datetime.now().isoformat()
        }
    
    def _execute_song_analysis(self, song_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute the actual song analysis using the existing analysis service.
        
        Args:
            song_id: ID of the song to analyze
            user_id: ID of the user requesting analysis
            
        Returns:
            Analysis results dictionary
        """
        # Use Flask app context if available
        if self.app:
            with self.app.app_context():
                # Use the existing analyze_song method which handles the complete flow
                analysis_result = self.analysis_service.analyze_song(song_id, user_id)
                
                # Handle case where analysis returns None (shouldn't happen but be safe)
                if analysis_result is None:
                    raise ValueError("Analysis service returned None")
                
                # Convert AnalysisResult object to dictionary
                return {
                    'score': getattr(analysis_result, 'score', 0),
                    'concern_level': getattr(analysis_result, 'concern_level', 'unknown'),
                    'status': getattr(analysis_result, 'status', 'completed'),
                    'themes': getattr(analysis_result, 'themes', []) or [],
                    'explanation': getattr(analysis_result, 'explanation', '') or ''
                }
        else:
            # Fallback without app context (shouldn't happen in practice)
            analysis_result = self.analysis_service.analyze_song(song_id, user_id)
            
            # Handle case where analysis returns None
            if analysis_result is None:
                raise ValueError("Analysis service returned None")
            
            return {
                'score': getattr(analysis_result, 'score', 0),
                'concern_level': getattr(analysis_result, 'concern_level', 'unknown'),
                'status': getattr(analysis_result, 'status', 'completed'),
                'themes': getattr(analysis_result, 'themes', []) or [],
                'explanation': getattr(analysis_result, 'explanation', '') or ''
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current worker status and statistics.
        
        Returns:
            Dictionary with worker status information
        """
        uptime = datetime.now() - self.stats['start_time']
        
        status = {
            'running': self.running,
            'current_job': {
                'job_id': self.current_job.job_id if self.current_job else None,
                'job_type': self.current_job.job_type.name if self.current_job else None,
                'priority': self.current_job.priority.name if self.current_job else None,
                'user_id': self.current_job.user_id if self.current_job else None
            } if self.current_job else None,
            'stats': {
                **self.stats,
                'uptime_seconds': uptime.total_seconds(),
                'uptime_str': str(uptime)
            },
            'queue_status': self.queue.get_queue_status(),
            'health': self.queue.health_check()
        }
        
        return status
    
    def is_healthy(self) -> bool:
        """
        Check if the worker is healthy.
        
        Returns:
            True if worker is healthy
        """
        if not self.running:
            return False
        
        # Check if heartbeat is recent
        time_since_heartbeat = datetime.now() - self.stats['last_heartbeat']
        if time_since_heartbeat > timedelta(seconds=30):
            return False
        
        # Check queue health
        queue_health = self.queue.health_check()
        if not queue_health['healthy']:
            return False
        
        return True


# Global worker instance for app integration
_worker_instance: Optional[PriorityQueueWorker] = None


def get_worker() -> Optional[PriorityQueueWorker]:
    """Get the global worker instance."""
    return _worker_instance


def init_worker(app) -> PriorityQueueWorker:
    """
    Initialize the global worker instance with Flask app.
    
    Args:
        app: Flask application instance
        
    Returns:
        Initialized worker instance
    """
    global _worker_instance
    
    if _worker_instance is None:
        _worker_instance = PriorityQueueWorker(app=app)
        logger.info("Global PriorityQueueWorker initialized")
    
    return _worker_instance


def start_worker(background: bool = True) -> None:
    """Start the global worker instance."""
    if _worker_instance:
        _worker_instance.start(background=background)
    else:
        logger.error("Worker not initialized. Call init_worker() first.")


def shutdown_worker() -> None:
    """Shutdown the global worker instance."""
    if _worker_instance:
        _worker_instance.shutdown() 