"""
Priority-based analysis queue service using Redis.

This service manages analysis jobs with different priority levels:
- high: User-initiated song analysis
- medium: User-initiated playlist analysis  
- low: Background analysis

Jobs are stored in Redis sorted sets for efficient priority-based retrieval.
"""

import json
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
import redis
from flask import current_app

from ..utils.logging import get_logger

logger = get_logger(__name__)


class JobType(Enum):
    """Analysis job types"""
    SONG_ANALYSIS = "song_analysis"
    PLAYLIST_ANALYSIS = "playlist_analysis" 
    BACKGROUND_ANALYSIS = "background_analysis"


class JobPriority(Enum):
    """Job priority levels (lower number = higher priority)"""
    HIGH = 1    # User song analysis
    MEDIUM = 2  # User playlist analysis
    LOW = 3     # Background analysis


class JobStatus(Enum):
    """Job status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


@dataclass
class AnalysisJob:
    """Analysis job data structure"""
    job_id: str
    job_type: JobType
    priority: JobPriority
    user_id: int
    target_id: int  # song_id or playlist_id
    created_at: datetime
    status: JobStatus = JobStatus.PENDING
    metadata: Dict[str, Any] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for Redis storage"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        # Convert enums to values
        data['job_type'] = self.job_type.value
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisJob':
        """Create job from dictionary stored in Redis"""
        # Convert ISO strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        # Convert values back to enums
        data['job_type'] = JobType(data['job_type'])
        data['priority'] = JobPriority(data['priority'])
        data['status'] = JobStatus(data['status'])
        return cls(**data)


class PriorityAnalysisQueue:
    """Redis-based priority queue for analysis jobs"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize the priority queue
        
        Args:
            redis_client: Optional Redis client. If None, creates from app config.
        """
        self._redis_client = redis_client
        self._redis = None
        
        # Redis key names
        self.queue_key = "analysis_queue"  # Sorted set for priority queue
        self.jobs_key = "analysis_jobs"    # Hash for job data
        self.active_key = "analysis_active"  # Key for currently active job
        
        logger.info("PriorityAnalysisQueue initialized")
    
    @property
    def redis(self) -> redis.Redis:
        """Lazy Redis client initialization"""
        if self._redis is None:
            if self._redis_client:
                self._redis = self._redis_client
            else:
                # Get Redis connection from Flask app config or environment
                try:
                    redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
                except RuntimeError:
                    # Fallback when outside app context
                    import os
                    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
                
                self._redis = redis.from_url(redis_url, decode_responses=True)
        
        return self._redis
    
    def enqueue(self, job_type: JobType, user_id: int, target_id: int, 
                priority: JobPriority, metadata: Dict[str, Any] = None) -> str:
        """Enqueue a new analysis job
        
        Args:
            job_type: Type of analysis job
            user_id: ID of user requesting analysis
            target_id: ID of target (song_id or playlist_id)
            priority: Job priority level
            metadata: Optional additional job metadata
            
        Returns:
            str: Unique job ID
        """
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job object
        job = AnalysisJob(
            job_id=job_id,
            job_type=job_type,
            priority=priority,
            user_id=user_id,
            target_id=target_id,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {}
        )
        
        # Store job data in Redis hash
        self.redis.hset(self.jobs_key, job_id, json.dumps(job.to_dict()))
        
        # Add job to priority queue (sorted set)
        # Score is priority value + timestamp for FIFO within same priority
        score = priority.value + (time.time() / 1000000)  # Microsecond precision
        self.redis.zadd(self.queue_key, {job_id: score})
        
        logger.info(f"Enqueued {job_type.value} job {job_id} for user {user_id} "
                   f"with priority {priority.value}")
        
        return job_id
    
    def dequeue(self) -> Optional[AnalysisJob]:
        """Dequeue the highest priority job
        
        Returns:
            AnalysisJob: Next job to process, or None if queue is empty
        """
        # Get the job with lowest score (highest priority)
        result = self.redis.zpopmin(self.queue_key)
        
        if not result:
            return None
        
        job_id, score = result[0]
        
        # Get job data from hash
        job_data = self.redis.hget(self.jobs_key, job_id)
        if not job_data:
            logger.error(f"Job data not found for job_id: {job_id}")
            return None
        
        # Parse job data
        job = AnalysisJob.from_dict(json.loads(job_data))
        
        # Mark job as in progress
        job.status = JobStatus.IN_PROGRESS
        job.started_at = datetime.now(timezone.utc)
        
        # Update job data in Redis
        self.redis.hset(self.jobs_key, job_id, json.dumps(job.to_dict()))
        
        # Set as active job
        self.redis.set(self.active_key, job_id, ex=3600)  # 1 hour TTL
        
        logger.info(f"Dequeued job {job_id} ({job.job_type.value}) for processing")
        
        return job
    
    def complete_job(self, job_id: str, success: bool = True, 
                    error_message: Optional[str] = None) -> bool:
        """Mark a job as completed or failed
        
        Args:
            job_id: ID of the job to complete
            success: Whether the job completed successfully
            error_message: Error message if job failed
            
        Returns:
            bool: True if job was updated successfully
        """
        # Get job data
        job_data = self.redis.hget(self.jobs_key, job_id)
        if not job_data:
            logger.error(f"Job data not found for job_id: {job_id}")
            return False
        
        # Parse and update job
        job = AnalysisJob.from_dict(json.loads(job_data))
        job.status = JobStatus.COMPLETED if success else JobStatus.FAILED
        job.completed_at = datetime.now(timezone.utc)
        if error_message:
            job.error_message = error_message
        
        # Update job data in Redis
        self.redis.hset(self.jobs_key, job_id, json.dumps(job.to_dict()))
        
        # Clear active job if this was it
        active_job_id = self.redis.get(self.active_key)
        if active_job_id == job_id:
            self.redis.delete(self.active_key)
        
        # Set TTL for completed job data (cleanup after 24 hours)
        self.redis.expire(f"{self.jobs_key}:{job_id}", 86400)
        
        status = "completed" if success else "failed"
        logger.info(f"Job {job_id} marked as {status}")
        
        return True
    
    def interrupt_job(self, job_id: str) -> bool:
        """Mark a job as interrupted (for priority preemption)
        
        Args:
            job_id: ID of the job to interrupt
            
        Returns:
            bool: True if job was updated successfully
        """
        # Get job data
        job_data = self.redis.hget(self.jobs_key, job_id)
        if not job_data:
            logger.error(f"Job data not found for job_id: {job_id}")
            return False
        
        # Parse and update job
        job = AnalysisJob.from_dict(json.loads(job_data))
        job.status = JobStatus.INTERRUPTED
        
        # Update job data in Redis
        self.redis.hset(self.jobs_key, job_id, json.dumps(job.to_dict()))
        
        # Re-queue the job with original priority
        score = job.priority.value + (time.time() / 1000000)
        self.redis.zadd(self.queue_key, {job_id: score})
        
        # Clear active job
        active_job_id = self.redis.get(self.active_key)
        if active_job_id == job_id:
            self.redis.delete(self.active_key)
        
        logger.info(f"Job {job_id} interrupted and re-queued")
        
        return True
    
    def get_job(self, job_id: str) -> Optional[AnalysisJob]:
        """Get job data by ID
        
        Args:
            job_id: Job ID to retrieve
            
        Returns:
            AnalysisJob: Job data or None if not found
        """
        job_data = self.redis.hget(self.jobs_key, job_id)
        if not job_data:
            return None
        
        return AnalysisJob.from_dict(json.loads(job_data))
    
    def get_active_job(self) -> Optional[AnalysisJob]:
        """Get currently active job
        
        Returns:
            AnalysisJob: Currently active job or None
        """
        active_job_id = self.redis.get(self.active_key)
        if not active_job_id:
            return None
        
        return self.get_job(active_job_id)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status information
        
        Returns:
            dict: Queue status including counts by priority and status
        """
        # Get queue length
        queue_length = self.redis.zcard(self.queue_key)
        
        # Get all jobs in queue
        queue_jobs = self.redis.zrange(self.queue_key, 0, -1, withscores=True)
        
        # Count by priority
        priority_counts = {priority.name: 0 for priority in JobPriority}
        for job_id, score in queue_jobs:
            priority_value = int(score)  # Extract priority from score
            for priority in JobPriority:
                if priority.value == priority_value:
                    priority_counts[priority.name] += 1
                    break
        
        # Get active job
        active_job = self.get_active_job()
        
        # Get job status counts (from all jobs, not just queued)
        all_job_ids = self.redis.hkeys(self.jobs_key)
        status_counts = {status.name: 0 for status in JobStatus}
        
        for job_id in all_job_ids:
            job = self.get_job(job_id)
            if job:
                status_counts[job.status.name] += 1
        
        return {
            'queue_length': queue_length,
            'priority_counts': priority_counts,
            'status_counts': status_counts,
            'active_job': active_job.to_dict() if active_job else None,
            'total_jobs': len(all_job_ids)
        }
    
    def clear_queue(self, user_id: Optional[int] = None) -> int:
        """Clear jobs from queue
        
        Args:
            user_id: If provided, only clear jobs for this user
            
        Returns:
            int: Number of jobs cleared
        """
        if user_id is None:
            # Clear entire queue
            cleared_count = self.redis.zcard(self.queue_key)
            self.redis.delete(self.queue_key)
            self.redis.delete(self.jobs_key)
            self.redis.delete(self.active_key)
            logger.info(f"Cleared entire queue ({cleared_count} jobs)")
            return cleared_count
        
        # Clear jobs for specific user
        queue_jobs = self.redis.zrange(self.queue_key, 0, -1)
        cleared_count = 0
        
        for job_id in queue_jobs:
            job = self.get_job(job_id)
            if job and job.user_id == user_id:
                # Remove from queue and job data
                self.redis.zrem(self.queue_key, job_id)
                self.redis.hdel(self.jobs_key, job_id)
                cleared_count += 1
        
        logger.info(f"Cleared {cleared_count} jobs for user {user_id}")
        return cleared_count
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the queue system
        
        Returns:
            dict: Health status information
        """
        try:
            # Test Redis connection
            self.redis.ping()
            redis_healthy = True
            redis_error = None
        except Exception as e:
            redis_healthy = False
            redis_error = str(e)
        
        # Get queue statistics
        status = self.get_queue_status()
        
        return {
            'redis_healthy': redis_healthy,
            'redis_error': redis_error,
            'queue_operational': redis_healthy and status['total_jobs'] >= 0,
            'queue_status': status,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


# Convenience functions for common operations
def enqueue_song_analysis(song_id: int, user_id: int, priority: JobPriority = JobPriority.HIGH,
                         metadata: Dict[str, Any] = None) -> AnalysisJob:
    """Enqueue a song analysis job"""
    queue = PriorityAnalysisQueue()
    job_id = queue.enqueue(
        job_type=JobType.SONG_ANALYSIS,
        user_id=user_id,
        target_id=song_id,
        priority=priority,
        metadata=metadata
    )
    return queue.get_job(job_id)


def enqueue_playlist_analysis(playlist_id: int, song_ids: List[int], user_id: int, 
                             priority: JobPriority = JobPriority.MEDIUM,
                             metadata: Dict[str, Any] = None) -> AnalysisJob:
    """Enqueue a playlist analysis job"""
    queue = PriorityAnalysisQueue()
    
    # Add song_ids to metadata
    if metadata is None:
        metadata = {}
    metadata['song_ids'] = song_ids
    
    job_id = queue.enqueue(
        job_type=JobType.PLAYLIST_ANALYSIS,
        user_id=user_id,
        target_id=playlist_id,
        priority=priority,
        metadata=metadata
    )
    return queue.get_job(job_id)


def enqueue_background_analysis(user_id: int, song_ids: List[int], 
                               priority: JobPriority = JobPriority.LOW,
                               metadata: Dict[str, Any] = None) -> AnalysisJob:
    """Enqueue a background analysis job for multiple songs"""
    queue = PriorityAnalysisQueue()
    
    # Add song_ids to metadata
    if metadata is None:
        metadata = {}
    metadata['song_ids'] = song_ids
    
    job_id = queue.enqueue(
        job_type=JobType.BACKGROUND_ANALYSIS,
        user_id=user_id,
        target_id=user_id,  # Use user_id as target for background analysis
        priority=priority,
        metadata=metadata
    )
    return queue.get_job(job_id) 