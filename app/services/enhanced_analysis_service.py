"""
Enhanced analysis service with task prioritization for RQ background processing.
"""
import logging
from flask import current_app
from ..extensions import rq
from ..worker_config import HIGH_QUEUE, DEFAULT_QUEUE, LOW_QUEUE

logger = logging.getLogger(__name__)


def analyze_song_user_initiated(song_id, user_id=None):
    """
    Analyze a song with high priority (user-initiated).
    
    Args:
        song_id (str): ID of the song to analyze
        user_id (int, optional): ID of the user requesting analysis
    
    Returns:
        Job: RQ job object
    """
    try:
        # Use high priority queue for user-initiated analysis
        job = rq.get_queue(HIGH_QUEUE).enqueue(
            'app.services.unified_analysis_service.execute_comprehensive_analysis_task',
            song_id,
            user_id=user_id,
            job_timeout=300,  # 5 minutes
            result_ttl=86400,  # 24 hours
            failure_ttl=86400,  # 24 hours
            job_id=f"analyze_song:{song_id}"
        )
        logger.info(f"Enqueued high priority analysis for song {song_id}, job ID: {job.id}")
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue high priority analysis for song {song_id}: {e}")
        raise


def analyze_song_background(song_id, user_id=None):
    """
    Analyze a song with default priority (background sync).
    
    Args:
        song_id (str): ID of the song to analyze
        user_id (int, optional): ID of the user requesting analysis
    
    Returns:
        Job: RQ job object
    """
    try:
        # Use default priority queue for background analysis
        job = rq.get_queue(DEFAULT_QUEUE).enqueue(
            'app.services.unified_analysis_service.execute_comprehensive_analysis_task',
            song_id,
            user_id=user_id,
            job_timeout=600,  # 10 minutes
            result_ttl=86400,  # 24 hours
            failure_ttl=86400,  # 24 hours
            job_id=f"analyze_song:{song_id}"
        )
        logger.info(f"Enqueued default priority analysis for song {song_id}, job ID: {job.id}")
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue default priority analysis for song {song_id}: {e}")
        raise


def analyze_songs_batch(song_ids, user_id=None):
    """
    Analyze multiple songs with low priority (batch operations).
    
    Args:
        song_ids (list): List of song IDs to analyze
        user_id (int, optional): ID of the user requesting analysis
    
    Returns:
        list: List of RQ job objects
    """
    jobs = []
    try:
        for song_id in song_ids:
            job = rq.get_queue(LOW_QUEUE).enqueue(
                'app.services.unified_analysis_service.execute_comprehensive_analysis_task',
                song_id,
                user_id=user_id,
                job_timeout=1800,  # 30 minutes
                result_ttl=86400,  # 24 hours
                failure_ttl=86400,  # 24 hours
                job_id=f"analyze_song:{song_id}"
            )
            jobs.append(job)
            logger.debug(f"Enqueued low priority analysis for song {song_id}, job ID: {job.id}")
        
        logger.info(f"Enqueued {len(jobs)} low priority analysis jobs for batch processing")
        return jobs
    except Exception as e:
        logger.error(f"Failed to enqueue batch analysis for songs {song_ids}: {e}")
        raise


def sync_playlist_background(playlist_id, user_id):
    """
    Sync a playlist with default priority (background operation).
    
    Args:
        playlist_id (str): ID of the playlist to sync
        user_id (int): ID of the user owning the playlist
    
    Returns:
        Job: RQ job object
    """
    try:
        job = rq.get_queue(DEFAULT_QUEUE).enqueue(
            'app.services.playlist_sync_service.sync_playlist_job',
            playlist_id,
            user_id,
            job_timeout=1800,  # 30 minutes
            result_ttl=86400,  # 24 hours
            failure_ttl=86400,  # 24 hours
            job_id=f"sync_playlist:{playlist_id}"
        )
        logger.info(f"Enqueued playlist sync for playlist {playlist_id}, job ID: {job.id}")
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue playlist sync for playlist {playlist_id}: {e}")
        raise


def sync_all_playlists_background(user_id):
    """
    Sync all playlists for a user with low priority (bulk operation).
    
    Args:
        user_id (int): ID of the user
    
    Returns:
        Job: RQ job object
    """
    try:
        job = rq.get_queue(LOW_QUEUE).enqueue(
            'app.services.playlist_sync_service.sync_all_playlists_job',
            user_id,
            job_timeout=3600,  # 1 hour
            result_ttl=86400,  # 24 hours
            failure_ttl=86400,  # 24 hours
            job_id=f"sync_all_playlists:{user_id}"
        )
        logger.info(f"Enqueued sync all playlists for user {user_id}, job ID: {job.id}")
        return job
    except Exception as e:
        logger.error(f"Failed to enqueue sync all playlists for user {user_id}: {e}")
        raise


def get_job_status(job_id):
    """
    Get the status of a job across all queues.
    
    Args:
        job_id (str): ID of the job
    
    Returns:
        dict: Job status information
    """
    try:
        # Try to find the job in any queue
        for queue_name in [HIGH_QUEUE, DEFAULT_QUEUE, LOW_QUEUE]:
            try:
                job = rq.get_queue(queue_name).fetch_job(job_id)
                if job:
                    return {
                        'id': job.id,
                        'status': job.get_status(),
                        'queue': queue_name,
                        'created_at': job.created_at.isoformat() if job.created_at else None,
                        'enqueued_at': job.enqueued_at.isoformat() if job.enqueued_at else None,
                        'started_at': job.started_at.isoformat() if job.started_at else None,
                        'ended_at': job.ended_at.isoformat() if job.ended_at else None,
                        'result': job.result,
                        'exc_info': job.exc_info
                    }
            except Exception:
                continue
        
        return {'error': 'Job not found'}
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}")
        return {'error': str(e)}


def get_queue_statistics():
    """
    Get statistics for all priority queues.
    
    Returns:
        dict: Queue statistics
    """
    try:
        stats = {}
        for queue_name in [HIGH_QUEUE, DEFAULT_QUEUE, LOW_QUEUE]:
            queue = rq.get_queue(queue_name)
            stats[queue_name] = {
                'name': queue_name,
                'count': queue.count,
                'failed_count': queue.failed_job_registry.count,
                'workers': len(queue.worker_ids),
                'jobs': [
                    {
                        'id': job.id,
                        'description': job.description,
                        'created_at': job.created_at.isoformat() if job.created_at else None,
                        'status': job.get_status()
                    }
                    for job in queue.jobs[:10]  # Get first 10 jobs
                ]
            }
        
        return stats
    except Exception as e:
        logger.error(f"Failed to get queue statistics: {e}")
        return {'error': str(e)} 