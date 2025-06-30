"""
Priority Queue Worker with Progress Tracking

This module provides an asynchronous worker that processes jobs from the priority queue
with real-time progress tracking and ETA calculations.
"""

import logging
import time
import signal
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from flask import current_app, Flask

from .priority_analysis_queue import PriorityAnalysisQueue, AnalysisJob, JobType, JobStatus, JobPriority
from .unified_analysis_service import UnifiedAnalysisService
from .progress_tracker import get_progress_tracker, ProgressTracker

logger = logging.getLogger(__name__)


class PriorityQueueWorker:
    """
    Worker that processes jobs from the priority analysis queue with progress tracking.
    
    Features:
    - Priority-based job processing (HIGH → MEDIUM → LOW)
    - Job interruption for higher priority work
    - Real-time progress tracking with ETA calculations
    - Graceful shutdown with configurable timeout
    - Health monitoring with heartbeat tracking
    - Statistics tracking (jobs processed, failed, interrupted)
    - Flask app context support for database operations
    """
    
    def __init__(self, app: Flask = None, check_interval: float = 1.0):
        self.app = app
        self.check_interval = check_interval
        self.queue = PriorityAnalysisQueue()
        self.progress_tracker = get_progress_tracker()
        
        # Worker state
        self.is_running = False
        self.should_stop = False
        self.worker_thread: Optional[threading.Thread] = None
        
        # Health monitoring
        self.start_time: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None
        self.current_job: Optional[AnalysisJob] = None
        
        # Statistics
        self.jobs_processed = 0
        self.jobs_failed = 0
        self.jobs_interrupted = 0
        
        logger.info("Priority queue worker initialized")
    
    def start(self) -> None:
        """Start the worker in a background thread"""
        if self.is_running:
            logger.warning("Worker is already running")
            return
        
        self.should_stop = False
        self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self.worker_thread.start()
        
        logger.info("Priority queue worker started")
    
    def stop(self, timeout: float = 30.0) -> bool:
        """
        Stop the worker gracefully
        
        Args:
            timeout: Maximum time to wait for worker to stop
            
        Returns:
            True if worker stopped successfully, False if timeout
        """
        if not self.is_running:
            logger.info("Worker is not running")
            return True
        
        logger.info(f"Stopping worker with {timeout}s timeout...")
        self.should_stop = True
        
        if self.worker_thread:
            self.worker_thread.join(timeout)
            if self.worker_thread.is_alive():
                logger.error(f"Worker did not stop within {timeout}s timeout")
                return False
        
        logger.info("Priority queue worker stopped")
        return True
    
    def _run_worker(self) -> None:
        """Main worker loop that processes jobs from the queue"""
        self.is_running = True
        self.start_time = datetime.now(timezone.utc)
        
        logger.info("Worker started processing jobs")
        
        try:
            while not self.should_stop:
                self._update_heartbeat()
                
                # Check for higher priority work if currently processing
                if self.current_job:
                    if self._should_interrupt_current_job():
                        self._interrupt_current_job()
                        continue
                
                # Get next job from queue
                job = self.queue.dequeue()
                if not job:
                    time.sleep(self.check_interval)
                    continue
                
                # Process the job
                self._process_job(job)
                
        except Exception as e:
            logger.error(f"Worker encountered unexpected error: {e}", exc_info=True)
        finally:
            self.is_running = False
            self.current_job = None
    
    def _update_heartbeat(self) -> None:
        """Update the worker heartbeat timestamp"""
        self.last_heartbeat = datetime.now(timezone.utc)
    
    def _should_interrupt_current_job(self) -> bool:
        """Check if current job should be interrupted for higher priority work"""
        if not self.current_job:
            return False
        
        # Check if there's a higher priority job waiting
        queue_status = self.queue.get_queue_status()
        current_priority = self.current_job.priority.value
        
        # Check for jobs with higher priority (lower number = higher priority)
        for priority_name, count in queue_status.get('priority_counts', {}).items():
            if count > 0:
                try:
                    priority_value = JobPriority[priority_name.upper()].value
                    if priority_value < current_priority:
                        logger.info(f"Found higher priority job ({priority_name}), interrupting current job")
                        return True
                except (KeyError, AttributeError):
                    continue
        
        return False
    
    def _interrupt_current_job(self) -> None:
        """Interrupt the current job and re-queue it"""
        if not self.current_job:
            return
        
        logger.info(f"Interrupting job {self.current_job.job_id}")
        
        # Mark job as interrupted and re-queue
        self.queue.interrupt_job(self.current_job.job_id)
        
        # Update statistics
        self.jobs_interrupted += 1
        
        # Complete progress tracking for interrupted job
        self.progress_tracker.complete_job_tracking(self.current_job.job_id, success=False)
        
        # Clear current job
        self.current_job = None
    
    def _process_job(self, job: AnalysisJob) -> None:
        """Process a single analysis job with progress tracking"""
        self.current_job = job
        logger.info(f"Processing job {job.job_id} ({job.job_type.value})")
        
        try:
            # Start progress tracking
            total_items = self._get_job_total_items(job)
            self.progress_tracker.start_job_tracking(
                job_id=job.job_id,
                job_type=job.job_type,
                total_items=total_items
            )
            
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
            self.queue.complete_job(job.job_id, success=True)
            self.progress_tracker.complete_job_tracking(job.job_id, success=True)
            
            # Update statistics
            self.jobs_processed += 1
            
            logger.info(f"Successfully completed job {job.job_id}")
            
        except Exception as e:
            logger.error(f"Failed to process job {job.job_id}: {e}", exc_info=True)
            
            # Mark job as failed
            self.queue.complete_job(job.job_id, success=False, error_message=str(e))
            self.progress_tracker.complete_job_tracking(job.job_id, success=False)
            
            # Update statistics
            self.jobs_failed += 1
            
        finally:
            self.current_job = None
    
    def _get_job_total_items(self, job: AnalysisJob) -> int:
        """Get the total number of items for a job"""
        if job.job_type == JobType.SONG_ANALYSIS:
            return 1
        elif job.job_type == JobType.PLAYLIST_ANALYSIS:
            # Get song count from metadata or database
            return job.metadata.get('song_count', 1)
        elif job.job_type == JobType.BACKGROUND_ANALYSIS:
            # Get song IDs from metadata
            song_ids = job.metadata.get('song_ids', [])
            return len(song_ids) if song_ids else 1
        else:
            return 1
    
    def _process_song_analysis(self, job: AnalysisJob) -> None:
        """Process a single song analysis job"""
        from ..services.unified_analysis_service import UnifiedAnalysisService
        
        # Update progress: Starting analysis
        self.progress_tracker.update_job_progress(
            job_id=job.job_id,
            completed_items=0,
            current_step="starting",
            step_progress=0.0,
            message="Starting song analysis"
        )
        
        # Get song from database
        from ..models.models import Song
        from .. import db
        
        if self.app:
            with self.app.app_context():
                song = Song.query.get(job.target_id)
                if not song:
                    raise ValueError(f"Song with ID {job.target_id} not found")
                
                # Update progress: Fetching lyrics
                self.progress_tracker.update_job_progress(
                    job_id=job.job_id,
                    current_step="lyrics_fetching",
                    step_progress=0.3,
                    message=f"Fetching lyrics for '{song.title}'"
                )
                
                # Perform analysis
                analysis_service = UnifiedAnalysisService()
                
                # Update progress: Analyzing content
                self.progress_tracker.update_job_progress(
                    job_id=job.job_id,
                    current_step="analysis",
                    step_progress=0.7,
                    message="Analyzing song content"
                )
                
                # Execute the analysis
                result = analysis_service.analyze_song(song)
                
                # Update progress: Complete
                self.progress_tracker.update_job_progress(
                    job_id=job.job_id,
                    completed_items=1,
                    current_step="complete",
                    step_progress=1.0,
                    message="Analysis complete"
                )
        else:
            # No app context - simulate analysis for testing
            time.sleep(2)  # Simulate processing time
            self.progress_tracker.update_job_progress(
                job_id=job.job_id,
                completed_items=1,
                message="Song analysis complete"
            )
    
    def _process_playlist_analysis(self, job: AnalysisJob) -> None:
        """Process a playlist analysis job"""
        from ..services.unified_analysis_service import UnifiedAnalysisService
        
        # Update progress: Starting
        self.progress_tracker.update_job_progress(
            job_id=job.job_id,
            completed_items=0,
            current_step="starting",
            step_progress=0.0,
            message="Starting playlist analysis"
        )
        
        if self.app:
            with self.app.app_context():
                from ..models.models import Playlist, Song, PlaylistSong
                from .. import db
                
                playlist = Playlist.query.get(job.target_id)
                if not playlist:
                    raise ValueError(f"Playlist with ID {job.target_id} not found")
                
                # Get songs to analyze
                songs_query = db.session.query(Song).join(PlaylistSong).filter(
                    PlaylistSong.playlist_id == playlist.id
                )
                
                # Filter for unanalyzed songs if specified
                if job.metadata.get('unanalyzed_only', False):
                    from ..models.models import AnalysisResult
                    songs_query = songs_query.outerjoin(AnalysisResult).filter(
                        AnalysisResult.id.is_(None)
                    )
                
                songs = songs_query.all()
                total_songs = len(songs)
                
                # Update total items in progress tracker
                if hasattr(self.progress_tracker.active_jobs.get(job.job_id), 'total_items'):
                    self.progress_tracker.active_jobs[job.job_id].total_items = total_songs
                
                analysis_service = UnifiedAnalysisService()
                
                # Process each song
                for i, song in enumerate(songs):
                    if self.should_stop:
                        break
                    
                    # Update progress
                    self.progress_tracker.update_job_progress(
                        job_id=job.job_id,
                        completed_items=i,
                        current_step="analysis",
                        step_progress=(i / total_songs) if total_songs > 0 else 1.0,
                        message=f"Analyzing '{song.title}' ({i+1}/{total_songs})"
                    )
                    
                    # Analyze the song
                    try:
                        analysis_service.analyze_song(song)
                    except Exception as e:
                        logger.warning(f"Failed to analyze song {song.id}: {e}")
                
                # Final progress update
                self.progress_tracker.update_job_progress(
                    job_id=job.job_id,
                    completed_items=total_songs,
                    current_step="complete",
                    step_progress=1.0,
                    message=f"Playlist analysis complete ({total_songs} songs)"
                )
        else:
            # No app context - simulate analysis for testing
            total_items = job.metadata.get('song_count', 5)
            for i in range(total_items):
                if self.should_stop:
                    break
                time.sleep(1)  # Simulate processing time
                self.progress_tracker.update_job_progress(
                    job_id=job.job_id,
                    completed_items=i + 1,
                    message=f"Processed song {i + 1}/{total_items}"
                )
    
    def _process_background_analysis(self, job: AnalysisJob) -> None:
        """Process a background analysis job"""
        from ..services.unified_analysis_service import UnifiedAnalysisService
        
        # Update progress: Starting
        self.progress_tracker.update_job_progress(
            job_id=job.job_id,
            completed_items=0,
            current_step="starting",
            step_progress=0.0,
            message="Starting background analysis"
        )
        
        if self.app:
            with self.app.app_context():
                from ..models.models import Song, AnalysisResult
                from .. import db
                
                # Get song IDs from metadata
                song_ids = job.metadata.get('song_ids', [])
                
                if not song_ids:
                    # Get all unanalyzed songs for the user
                    songs = db.session.query(Song).outerjoin(AnalysisResult).filter(
                        AnalysisResult.id.is_(None)
                    ).limit(100).all()  # Limit to prevent overwhelming
                    song_ids = [song.id for song in songs]
                
                total_songs = len(song_ids)
                
                # Update total items in progress tracker
                if hasattr(self.progress_tracker.active_jobs.get(job.job_id), 'total_items'):
                    self.progress_tracker.active_jobs[job.job_id].total_items = total_songs
                
                analysis_service = UnifiedAnalysisService()
                
                # Process each song
                for i, song_id in enumerate(song_ids):
                    if self.should_stop:
                        break
                    
                    song = Song.query.get(song_id)
                    if not song:
                        continue
                    
                    # Update progress
                    self.progress_tracker.update_job_progress(
                        job_id=job.job_id,
                        completed_items=i,
                        current_step="analysis",
                        step_progress=(i / total_songs) if total_songs > 0 else 1.0,
                        message=f"Background analysis: '{song.title}' ({i+1}/{total_songs})"
                    )
                    
                    # Analyze the song
                    try:
                        analysis_service.analyze_song(song)
                    except Exception as e:
                        logger.warning(f"Failed to analyze song {song.id}: {e}")
                
                # Final progress update
                self.progress_tracker.update_job_progress(
                    job_id=job.job_id,
                    completed_items=total_songs,
                    current_step="complete",
                    step_progress=1.0,
                    message=f"Background analysis complete ({total_songs} songs)"
                )
        else:
            # No app context - simulate analysis for testing
            song_ids = job.metadata.get('song_ids', [1, 2, 3])
            total_songs = len(song_ids)
            for i in range(total_songs):
                if self.should_stop:
                    break
                time.sleep(1)  # Simulate processing time
                self.progress_tracker.update_job_progress(
                    job_id=job.job_id,
                    completed_items=i + 1,
                    message=f"Background processed song {i + 1}/{total_songs}"
                )
    

    
    def get_status(self) -> Dict[str, Any]:
        """Get current worker status and statistics"""
        uptime_seconds = 0
        if self.start_time:
            uptime_seconds = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        return {
            'status': 'running' if self.is_running else 'stopped',
            'uptime_seconds': uptime_seconds,
            'jobs_processed': self.jobs_processed,
            'jobs_failed': self.jobs_failed,
            'jobs_interrupted': self.jobs_interrupted,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'current_job': {
                'job_id': self.current_job.job_id,
                'job_type': self.current_job.job_type.value,
                'priority': self.current_job.priority.value,
                'started_at': self.current_job.started_at
            } if self.current_job else None
        }


# Global worker instance
_worker: Optional[PriorityQueueWorker] = None


def get_worker() -> Optional[PriorityQueueWorker]:
    """Get the global worker instance"""
    return _worker


def start_worker(app: Flask = None) -> PriorityQueueWorker:
    """Start the global worker instance"""
    global _worker
    
    if _worker and _worker.is_running:
        logger.warning("Worker is already running")
        return _worker
    
    _worker = PriorityQueueWorker(app=app)
    _worker.start()
    return _worker


def get_worker_status() -> Dict[str, Any]:
    """
    Get the current worker status.
    
    Returns:
        Dictionary with worker status information, or default values if worker not available
    """
    worker = get_worker()
    
    if worker:
        return worker.get_status()
    else:
        # Return default status when worker is not available
        return {
            'status': 'not_running',
            'uptime_seconds': 0,
            'jobs_processed': 0,
            'jobs_failed': 0,
            'jobs_interrupted': 0,
            'last_heartbeat': None,
            'current_job': None
        }


def shutdown_worker() -> None:
    """Shutdown the global worker instance"""
    global _worker
    
    if _worker:
        _worker.stop()
        _worker = None
        logger.info("Global worker shutdown complete") 