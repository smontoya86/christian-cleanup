"""
Redis Queue configuration for background job processing.

This module provides a simple interface for queuing playlist analysis jobs
that run in the background, preventing request timeouts and providing
progress tracking capabilities.
"""
import os
import logging
from redis import Redis
from rq import Queue

logger = logging.getLogger(__name__)

# Use existing Redis connection from environment
# Note: decode_responses=False is required for RQ to work with pickled job data
redis_conn = Redis.from_url(
    os.environ.get('REDIS_URL', 'redis://redis:6379'),
    decode_responses=False
)

# Create queue for analysis jobs
analysis_queue = Queue('analysis', connection=redis_conn)


def enqueue_playlist_analysis(playlist_id: int, user_id: int) -> str:
    """
    Queue a playlist for background analysis.
    
    Args:
        playlist_id: ID of the playlist to analyze
        user_id: ID of the user who owns the playlist
        
    Returns:
        job_id: Unique identifier for tracking this job
    """
    try:
        job = analysis_queue.enqueue(
            'app.services.unified_analysis_service.analyze_playlist_async',
            playlist_id,
            user_id,
            job_timeout='30m',  # Max 30 minutes per playlist
            result_ttl=3600,    # Keep result for 1 hour
            failure_ttl=86400   # Keep failures for 24 hours for debugging
        )
        
        logger.info(f"Queued playlist {playlist_id} for analysis (job_id: {job.id})")
        return job.id
        
    except Exception as e:
        logger.error(f"Failed to queue playlist {playlist_id}: {e}")
        raise


def get_queue_length() -> int:
    """Get the number of jobs waiting in the queue."""
    return len(analysis_queue)


def get_active_workers() -> int:
    """Get the number of active RQ workers."""
    from rq import Worker
    return len(Worker.all(connection=redis_conn))


def get_job_status(job_id: str) -> dict:
    """
    Get the status and metadata for a job.
    
    Args:
        job_id: The job ID to check
    
    Returns:
        dict: Job status information including status and metadata
    """
    from rq.job import Job
    
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        return {
            'status': job.get_status(),
            'meta': job.meta,
            'created_at': job.created_at,
            'started_at': job.started_at,
            'ended_at': job.ended_at,
            'result': job.result if job.is_finished else None
        }
    except Exception:
        return {'status': 'not_found', 'meta': {}}


def cancel_job(job_id: str) -> bool:
    """
    Cancel a queued or running job.
    
    Args:
        job_id: The job ID to cancel
    
    Returns:
        bool: True if job was canceled, False otherwise
    """
    from rq.job import Job
    
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        job.cancel()
        logger.info(f"Canceled job {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        return False


def clean_failed_jobs() -> int:
    """
    Remove all failed jobs from the failed job registry.
    
    Returns:
        int: Number of jobs removed
    """
    from rq.registry import FailedJobRegistry
    
    registry = FailedJobRegistry(queue=analysis_queue)
    job_ids = registry.get_job_ids()
    
    count = 0
    for job_id in job_ids:
        registry.remove(job_id, delete_job=True)
        count += 1
    
    if count > 0:
        logger.info(f"Cleaned {count} failed jobs from registry")
    
    return count

