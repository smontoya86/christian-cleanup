"""
Progress Tracking and ETA System

This module provides real-time progress tracking for analysis jobs with ETA calculations
and persistence across app restarts.
"""

import json
import redis
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

from flask import current_app
from .priority_analysis_queue import JobType, JobStatus


logger = logging.getLogger(__name__)


@dataclass
class ProgressUpdate:
    """Represents a progress update for a job"""
    job_id: str
    progress: float  # 0.0 to 1.0
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    step_progress: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'job_id': self.job_id,
            'progress': self.progress,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'step_progress': self.step_progress
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressUpdate':
        """Create from dictionary"""
        timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        return cls(
            job_id=data['job_id'],
            progress=data['progress'],
            message=data['message'],
            timestamp=timestamp,
            current_step=data.get('current_step'),
            total_steps=data.get('total_steps'),
            step_progress=data.get('step_progress')
        )


@dataclass
class JobProgress:
    """Tracks progress for a specific job"""
    job_id: str
    job_type: JobType
    total_items: int
    estimated_duration_per_item: float
    completed_items: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    current_step: Optional[str] = None
    step_progress: Optional[float] = None
    current_message: Optional[str] = None
    
    @property
    def current_progress(self) -> float:
        """Calculate current overall progress (0.0 to 1.0)"""
        if self.total_items == 0:
            return 1.0
        return self.completed_items / self.total_items
    
    @property
    def is_complete(self) -> bool:
        """Check if job is complete"""
        return self.completed_items >= self.total_items
    
    def update_completion(self, completed_items: int) -> None:
        """Update the number of completed items"""
        self.completed_items = min(completed_items, self.total_items)
    
    def update_step(self, step_name: str, step_progress: float, message: str = None) -> None:
        """Update current step progress"""
        self.current_step = step_name
        self.step_progress = step_progress
        if message:
            self.current_message = message
    
    def calculate_eta(self) -> float:
        """Calculate estimated time to completion in seconds"""
        if self.is_complete:
            return 0.0
        
        elapsed_time = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        if self.completed_items == 0:
            # No progress yet, use estimated duration
            return self.total_items * self.estimated_duration_per_item
        
        # Calculate average time per item based on actual progress
        avg_time_per_item = elapsed_time / self.completed_items
        remaining_items = self.total_items - self.completed_items
        
        return remaining_items * avg_time_per_item
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'job_id': self.job_id,
            'job_type': self.job_type.value,
            'total_items': self.total_items,
            'completed_items': self.completed_items,
            'current_progress': self.current_progress,
            'start_time': self.start_time.isoformat(),
            'estimated_duration_per_item': self.estimated_duration_per_item,
            'current_step': self.current_step,
            'step_progress': self.step_progress,
            'current_message': self.current_message,
            'is_complete': self.is_complete,
            'eta_seconds': self.calculate_eta()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobProgress':
        """Create from dictionary"""
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        job_type = JobType(data['job_type'])
        
        progress = cls(
            job_id=data['job_id'],
            job_type=job_type,
            total_items=data['total_items'],
            estimated_duration_per_item=data['estimated_duration_per_item'],
            completed_items=data['completed_items'],
            start_time=start_time,
            current_step=data.get('current_step'),
            step_progress=data.get('step_progress'),
            current_message=data.get('current_message')
        )
        
        return progress


class ETACalculator:
    """Calculates ETAs based on historical job completion data"""
    
    def __init__(self):
        self.historical_data: Dict[JobType, List[float]] = defaultdict(list)
        self.max_history_size = 100  # Keep last 100 completions per job type
        
        # Default durations in seconds per item
        self.default_durations = {
            JobType.SONG_ANALYSIS: 30.0,
            JobType.PLAYLIST_ANALYSIS: 25.0,
            JobType.BACKGROUND_ANALYSIS: 20.0
        }
    
    def record_completion(self, job_type: JobType, duration_per_item: float) -> None:
        """Record a job completion for historical data"""
        self.historical_data[job_type].append(duration_per_item)
        
        # Keep only recent history
        if len(self.historical_data[job_type]) > self.max_history_size:
            self.historical_data[job_type] = self.historical_data[job_type][-self.max_history_size:]
    
    def get_average_duration(self, job_type: JobType) -> float:
        """Get average duration per item for a job type"""
        if not self.historical_data[job_type]:
            return self.default_durations.get(job_type, 30.0)
        
        return sum(self.historical_data[job_type]) / len(self.historical_data[job_type])
    
    def calculate_eta(self, job_type: JobType, total_items: int, 
                     completed_items: int, elapsed_time: float) -> float:
        """Calculate ETA based on historical data and current progress"""
        remaining_items = total_items - completed_items
        
        if completed_items == 0:
            # No progress yet, use historical/default average
            avg_duration = self.get_average_duration(job_type)
            return remaining_items * avg_duration
        
        # Use actual performance for this job
        actual_avg_duration = elapsed_time / completed_items
        return remaining_items * actual_avg_duration


class ProgressPersistence:
    """Handles persistence of progress data in Redis"""
    
    def __init__(self):
        redis_url = current_app.config.get('RQ_REDIS_URL', 'redis://localhost:6379/0')
        self.redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = "progress:"
        self.ttl_seconds = 86400  # 24 hours
    
    def save_progress(self, progress: JobProgress) -> None:
        """Save job progress to Redis"""
        try:
            key = f"{self.key_prefix}{progress.job_id}"
            data = json.dumps(progress.to_dict())
            self.redis.set(key, data, ex=self.ttl_seconds)
            logger.debug(f"Saved progress for job {progress.job_id}")
        except Exception as e:
            logger.error(f"Failed to save progress for job {progress.job_id}: {e}")
    
    def load_progress(self, job_id: str) -> Optional[JobProgress]:
        """Load job progress from Redis"""
        try:
            key = f"{self.key_prefix}{job_id}"
            data = self.redis.get(key)
            
            if not data:
                return None
            
            progress_dict = json.loads(data)
            return JobProgress.from_dict(progress_dict)
        except Exception as e:
            logger.error(f"Failed to load progress for job {job_id}: {e}")
            return None
    
    def delete_progress(self, job_id: str) -> None:
        """Delete job progress from Redis"""
        try:
            key = f"{self.key_prefix}{job_id}"
            self.redis.delete(key)
            logger.debug(f"Deleted progress for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to delete progress for job {job_id}: {e}")


class ProgressTracker:
    """Main progress tracking system"""
    
    def __init__(self):
        self.eta_calculator = ETACalculator()
        self.persistence = ProgressPersistence()
        self.active_jobs: Dict[str, JobProgress] = {}
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
    
    def start_job_tracking(self, job_id: str, job_type: JobType, 
                          total_items: int, estimated_duration_per_item: float = None) -> JobProgress:
        """Start tracking progress for a job"""
        if estimated_duration_per_item is None:
            estimated_duration_per_item = self.eta_calculator.get_average_duration(job_type)
        
        progress = JobProgress(
            job_id=job_id,
            job_type=job_type,
            total_items=total_items,
            estimated_duration_per_item=estimated_duration_per_item
        )
        
        self.active_jobs[job_id] = progress
        self.persistence.save_progress(progress)
        
        logger.info(f"Started tracking job {job_id} ({job_type.value}) with {total_items} items")
        return progress
    
    def update_job_progress(self, job_id: str, completed_items: int = None,
                           current_step: str = None, step_progress: float = None,
                           message: str = None) -> Optional[ProgressUpdate]:
        """Update job progress and notify subscribers"""
        progress = self.active_jobs.get(job_id)
        if not progress:
            logger.warning(f"Attempted to update progress for unknown job {job_id}")
            return None
        
        # Update progress
        if completed_items is not None:
            progress.update_completion(completed_items)
        
        if current_step is not None:
            progress.update_step(current_step, step_progress or 0.0, message)
        
        # Create progress update
        update = ProgressUpdate(
            job_id=job_id,
            progress=progress.current_progress,
            message=message or progress.current_message or f"Progress: {progress.completed_items}/{progress.total_items}",
            current_step=progress.current_step,
            total_steps=None,  # Could be enhanced to track analysis steps
            step_progress=progress.step_progress
        )
        
        # Save to persistence
        self.persistence.save_progress(progress)
        
        # Notify subscribers
        self._notify_subscribers(update)
        
        logger.debug(f"Updated progress for job {job_id}: {progress.current_progress:.2%}")
        return update
    
    def complete_job_tracking(self, job_id: str, success: bool = True) -> None:
        """Complete job tracking and record completion data"""
        progress = self.active_jobs.get(job_id)
        if not progress:
            logger.warning(f"Attempted to complete tracking for unknown job {job_id}")
            return
        
        if success:
            # Record completion for ETA calculation
            elapsed_time = (datetime.now(timezone.utc) - progress.start_time).total_seconds()
            if progress.completed_items > 0:
                duration_per_item = elapsed_time / progress.completed_items
                self.eta_calculator.record_completion(progress.job_type, duration_per_item)
        
        # Clean up
        del self.active_jobs[job_id]
        self.persistence.delete_progress(job_id)
        
        # Clean up subscribers
        if job_id in self.subscribers:
            del self.subscribers[job_id]
        
        logger.info(f"Completed tracking for job {job_id} (success: {success})")
    
    def get_job_progress(self, job_id: str) -> Optional[JobProgress]:
        """Get current progress for a job"""
        # Check active jobs first
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        
        # Try to load from persistence
        return self.persistence.load_progress(job_id)
    
    def subscribe_to_progress(self, job_id: str, callback: Callable[[ProgressUpdate], None]) -> None:
        """Subscribe to progress updates for a job"""
        self.subscribers[job_id].append(callback)
        logger.debug(f"Added subscriber for job {job_id}")
    
    def unsubscribe_from_progress(self, job_id: str, callback: Callable[[ProgressUpdate], None]) -> None:
        """Unsubscribe from progress updates for a job"""
        if job_id in self.subscribers and callback in self.subscribers[job_id]:
            self.subscribers[job_id].remove(callback)
            if not self.subscribers[job_id]:
                del self.subscribers[job_id]
            logger.debug(f"Removed subscriber for job {job_id}")
    
    def _notify_subscribers(self, update: ProgressUpdate) -> None:
        """Notify all subscribers of a progress update"""
        subscribers = self.subscribers.get(update.job_id, [])
        for callback in subscribers:
            try:
                callback(update)
            except Exception as e:
                logger.error(f"Error notifying progress subscriber for job {update.job_id}: {e}")
    
    def get_all_active_progress(self) -> Dict[str, JobProgress]:
        """Get progress for all active jobs"""
        return self.active_jobs.copy()
    
    def cleanup_stale_jobs(self, max_age_hours: int = 24) -> None:
        """Clean up jobs that have been running too long"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        stale_jobs = []
        
        for job_id, progress in self.active_jobs.items():
            if progress.start_time < cutoff_time:
                stale_jobs.append(job_id)
        
        for job_id in stale_jobs:
            logger.warning(f"Cleaning up stale job {job_id}")
            self.complete_job_tracking(job_id, success=False)


# Global progress tracker instance
_progress_tracker: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker instance"""
    global _progress_tracker
    if _progress_tracker is None:
        _progress_tracker = ProgressTracker()
    return _progress_tracker


def init_progress_tracker() -> ProgressTracker:
    """Initialize the global progress tracker"""
    global _progress_tracker
    _progress_tracker = ProgressTracker()
    return _progress_tracker 