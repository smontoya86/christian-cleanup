#!/usr/bin/env python3
"""
Custom exception handlers for playlist synchronization tasks.

These handlers provide specialized error handling, logging, and alerting
for different types of failures that can occur during playlist sync operations.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from rq.job import Job
from flask import current_app

logger = logging.getLogger(__name__)

def playlist_sync_exception_handler(job: Job, exc_type, exc_value, traceback) -> bool:
    """
    Main exception handler for playlist sync tasks.
    
    Routes different types of exceptions to specialized handlers and
    provides comprehensive error logging and alerting.
    
    Args:
        job: The RQ job that failed
        exc_type: Type of the exception
        exc_value: The exception instance
        traceback: The traceback object
        
    Returns:
        bool: True to continue to next handler, False to stop processing
    """
    try:
        # Extract user_id from job metadata
        user_id = job.meta.get('user_id', 'unknown')
        task_type = job.meta.get('task_type', 'unknown')
        
        # Log the exception with detailed context
        error_context = {
            'job_id': job.id,
            'user_id': user_id,
            'task_type': task_type,
            'exception_type': exc_type.__name__,
            'exception_message': str(exc_value),
            'failed_at': datetime.utcnow().isoformat(),
            'attempt_number': getattr(job, 'retries_left', 0),
            'max_retries': getattr(job, 'retry', {}).get('max', 0) if hasattr(job, 'retry') else 0
        }
        
        logger.error(
            f"Playlist sync task failed for user {user_id}: {exc_type.__name__}: {exc_value}",
            extra=error_context
        )
        
        # Handle specific exception types
        if _is_spotify_api_error(exc_type, exc_value):
            return _handle_spotify_api_error(job, exc_type, exc_value, error_context)
        elif _is_database_error(exc_type, exc_value):
            return _handle_database_error(job, exc_type, exc_value, error_context)
        elif _is_auth_error(exc_type, exc_value):
            return _handle_auth_error(job, exc_type, exc_value, error_context)
        else:
            return _handle_generic_error(job, exc_type, exc_value, error_context)
            
    except Exception as handler_error:
        # Log any errors in the exception handler itself
        logger.exception(f"Error in playlist sync exception handler: {handler_error}")
        return True  # Continue to default handler
        
def _is_spotify_api_error(exc_type, exc_value) -> bool:
    """Check if the exception is a Spotify API error."""
    return 'spotipy' in str(exc_type).lower() or 'spotify' in str(exc_value).lower()

def _is_database_error(exc_type, exc_value) -> bool:
    """Check if the exception is a database error."""
    return any(db_error in str(exc_type).lower() for db_error in ['sqlalchemy', 'database', 'psycopg'])

def _is_auth_error(exc_type, exc_value) -> bool:
    """Check if the exception is an authentication error."""
    return any(auth_term in str(exc_value).lower() for auth_term in ['unauthorized', 'token', 'auth'])

def _handle_spotify_api_error(job: Job, exc_type, exc_value, context: Dict[str, Any]) -> bool:
    """
    Handle Spotify API specific errors.
    
    Args:
        job: The failed job
        exc_type: Exception type
        exc_value: Exception value
        context: Error context dictionary
        
    Returns:
        bool: Whether to continue to next handler
    """
    logger.warning(
        f"Spotify API error for user {context['user_id']}: {exc_value}",
        extra=context
    )
    
    # Check if it's a rate limit error
    if hasattr(exc_value, 'http_status') and exc_value.http_status == 429:
        logger.info(f"Rate limit hit for user {context['user_id']}, job will be retried")
        _update_job_meta(job, {
            'last_error': 'spotify_rate_limit',
            'retry_reason': 'Rate limit exceeded'
        })
        
    # Check if it's an auth error
    elif hasattr(exc_value, 'http_status') and exc_value.http_status == 401:
        logger.warning(f"Authentication failed for user {context['user_id']}, user needs to re-authenticate")
        _update_job_meta(job, {
            'last_error': 'spotify_auth_failed',
            'requires_reauth': True
        })
        
    return False  # Stop processing, we've handled this error

def _handle_database_error(job: Job, exc_type, exc_value, context: Dict[str, Any]) -> bool:
    """
    Handle database specific errors.
    
    Args:
        job: The failed job
        exc_type: Exception type
        exc_value: Exception value
        context: Error context dictionary
        
    Returns:
        bool: Whether to continue to next handler
    """
    logger.error(
        f"Database error for user {context['user_id']}: {exc_value}",
        extra=context
    )
    
    _update_job_meta(job, {
        'last_error': 'database_error',
        'retry_reason': 'Database connection or query failed'
    })
    
    # Database errors are generally retryable
    return False

def _handle_auth_error(job: Job, exc_type, exc_value, context: Dict[str, Any]) -> bool:
    """
    Handle authentication specific errors.
    
    Args:
        job: The failed job
        exc_type: Exception type
        exc_value: Exception value
        context: Error context dictionary
        
    Returns:
        bool: Whether to continue to next handler
    """
    logger.warning(
        f"Authentication error for user {context['user_id']}: {exc_value}",
        extra=context
    )
    
    _update_job_meta(job, {
        'last_error': 'authentication_error',
        'requires_reauth': True,
        'retry_reason': 'User authentication required'
    })
    
    return False

def _handle_generic_error(job: Job, exc_type, exc_value, context: Dict[str, Any]) -> bool:
    """
    Handle generic/unknown errors.
    
    Args:
        job: The failed job
        exc_type: Exception type
        exc_value: Exception value
        context: Error context dictionary
        
    Returns:
        bool: Whether to continue to next handler
    """
    logger.error(
        f"Generic error for user {context['user_id']}: {exc_type.__name__}: {exc_value}",
        extra=context
    )
    
    _update_job_meta(job, {
        'last_error': 'generic_error',
        'error_type': exc_type.__name__,
        'retry_reason': 'Unknown error occurred'
    })
    
    return False

def _update_job_meta(job: Job, meta_updates: Dict[str, Any]) -> None:
    """
    Update job metadata with error information.
    
    Args:
        job: The RQ job to update
        meta_updates: Dictionary of metadata updates
    """
    try:
        # Update job metadata
        if not hasattr(job, 'meta') or job.meta is None:
            job.meta = {}
            
        job.meta.update(meta_updates)
        job.meta['last_updated'] = datetime.utcnow().isoformat()
        job.save_meta()
        
    except Exception as meta_error:
        logger.error(f"Failed to update job metadata: {meta_error}")

def work_horse_killed_handler(job: Job, retpid: int, ret_val: int, rusage) -> None:
    """
    Handler for when a worker process is unexpectedly terminated.
    
    This happens when a worker is killed due to memory issues, system shutdown, etc.
    
    Args:
        job: The job that was being processed when worker died
        retpid: Return process ID
        ret_val: Return value
        rusage: Resource usage information
    """
    user_id = job.meta.get('user_id', 'unknown') if job.meta else 'unknown'
    
    logger.critical(
        f"Worker process killed while processing playlist sync for user {user_id}",
        extra={
            'job_id': job.id,
            'user_id': user_id,
            'retpid': retpid,
            'ret_val': ret_val,
            'killed_at': datetime.utcnow().isoformat()
        }
    )
    
    # Update job metadata to indicate worker was killed
    if hasattr(job, 'meta') and job.meta:
        try:
            job.meta.update({
                'worker_killed': True,
                'killed_at': datetime.utcnow().isoformat(),
                'last_error': 'worker_process_killed'
            })
            job.save_meta()
        except Exception as meta_error:
            logger.error(f"Failed to update job metadata after worker kill: {meta_error}") 