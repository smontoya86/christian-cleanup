#!/usr/bin/env python3
"""
Background playlist synchronization service using Flask-RQ2.

This module provides functions to synchronize user playlists from Spotify 
in the background to prevent UI freezes and timeouts.

Includes robust error handling, retry mechanisms, and comprehensive logging.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from rq import Retry
from sqlalchemy.exc import SQLAlchemyError

# Set up module logger
logger = logging.getLogger(__name__)

# Retry configuration constants
MAX_RETRIES = 3
RETRY_INTERVALS = [30, 120, 300]  # 30 seconds, 2 minutes, 5 minutes (exponential backoff)
DEFAULT_JOB_TIMEOUT = 1200  # 20 minutes

def _execute_playlist_sync_impl(user_id: int) -> Dict[str, Any]:
    """
    Implementation function that performs the actual playlist synchronization.
    
    Enhanced with comprehensive error handling, database transaction management,
    and detailed error categorization for retry decisions.
    
    Args:
        user_id: ID of the user whose playlists should be synced
        
    Returns:
        dict: Summary of the sync operation with success status and statistics
    """
    from flask import current_app
    from ..models import User
    from ..extensions import db
    from ..services.spotify_service import SpotifyService
    import spotipy
    
    current_app.logger.info(f"Starting background playlist sync for user {user_id}")
    
    # Track start time for performance monitoring
    start_time = datetime.utcnow()
    
    try:
        # Begin database transaction for consistency
        db.session.begin()
        
        # Get the user from the database
        user = db.session.get(User, user_id)
        if not user:
            error_msg = f"User with ID {user_id} not found in database"
            current_app.logger.error(error_msg)
            db.session.rollback()
            return {
                "success": False,
                "error": error_msg,
                "error_type": "user_not_found",
                "user_id": user_id,
                "retryable": False
            }
        
        # Ensure the user has a valid Spotify token
        if not user.access_token:
            error_msg = f"User {user_id} has no Spotify access token"
            current_app.logger.error(error_msg)
            db.session.rollback()
            return {
                "success": False,
                "error": error_msg,
                "error_type": "no_token",
                "user_id": user_id,
                "requires_reauth": True,
                "retryable": False
            }
        
        # Validate token before proceeding
        try:
            if not user.ensure_token_valid():
                error_msg = f"User {user_id} has invalid or expired Spotify token"
                current_app.logger.error(error_msg)
                db.session.rollback()
                return {
                    "success": False,
                    "error": error_msg,
                    "error_type": "invalid_token",
                    "user_id": user_id,
                    "requires_reauth": True,
                    "retryable": False
                }
        except Exception as token_error:
            error_msg = f"Token validation failed for user {user_id}: {token_error}"
            current_app.logger.error(error_msg)
            db.session.rollback()
            return {
                "success": False,
                "error": error_msg,
                "error_type": "token_validation_error",
                "user_id": user_id,
                "requires_reauth": True,
                "retryable": False
            }
        
        # Create SpotifyService instance with the user's token
        spotify_service = SpotifyService(auth_token=user.access_token, logger=current_app.logger)
        
        # Perform the synchronization with detailed progress tracking
        current_app.logger.info(f"Starting Spotify API sync for user {user_id}")
        synced_playlists = spotify_service.sync_user_playlists_with_db(user_id)
        
        # Commit the transaction on success
        db.session.commit()
        
        # Calculate performance metrics
        end_time = datetime.utcnow()
        duration_seconds = (end_time - start_time).total_seconds()
        
        sync_stats = {
            "success": True,
            "user_id": user_id,
            "user_spotify_id": user.spotify_id,
            "synced_playlists_count": len(synced_playlists) if synced_playlists else 0,
            "sync_completed_at": end_time.isoformat(),
            "sync_duration_seconds": duration_seconds,
            "message": f"Successfully synced {len(synced_playlists) if synced_playlists else 0} playlists in {duration_seconds:.2f} seconds"
        }
        
        current_app.logger.info(f"Background playlist sync completed for user {user_id}: {sync_stats['message']}")
        return sync_stats
        
    except spotipy.SpotifyException as e:
        # Rollback database transaction on error
        db.session.rollback()
        
        error_code = getattr(e, 'http_status', None)
        error_msg = f"Spotify API error during background sync for user {user_id}: {e}"
        current_app.logger.error(error_msg, extra={
            'user_id': user_id,
            'spotify_error_code': error_code,
            'error_type': 'spotify_api_error'
        })
        
        # Determine if error is retryable based on HTTP status code
        retryable = error_code in [429, 500, 502, 503, 504]  # Rate limit and server errors
        requires_reauth = error_code == 401
        
        return {
            "success": False,
            "error": error_msg,
            "error_type": "spotify_api_error",
            "user_id": user_id,
            "spotify_error_code": error_code,
            "requires_reauth": requires_reauth,
            "retryable": retryable
        }
        
    except SQLAlchemyError as e:
        # Rollback database transaction on database error
        db.session.rollback()
        
        error_msg = f"Database error during background sync for user {user_id}: {str(e)}"
        current_app.logger.exception(error_msg, extra={
            'user_id': user_id,
            'error_type': 'database_error'
        })
        
        return {
            "success": False,
            "error": error_msg,
            "error_type": "database_error",
            "user_id": user_id,
            "retryable": True  # Database errors are generally retryable
        }
        
    except Exception as e:
        # Rollback database transaction on any other error
        db.session.rollback()
        
        error_msg = f"Unexpected error during background playlist sync for user {user_id}: {str(e)}"
        current_app.logger.exception(error_msg, extra={
            'user_id': user_id,
            'error_type': 'unexpected_error'
        })
        
        return {
            "success": False,
            "error": error_msg,
            "error_type": "unexpected_error",
            "user_id": user_id,
            "retryable": True  # Unknown errors are generally retryable
        }

def _execute_playlist_sync_task(user_id: int, **kwargs) -> Dict[str, Any]:
    """
    Wrapper function that ensures the task runs within a Flask application context.
    This is the actual function that gets called by RQ.
    
    Enhanced with intelligent retry logic based on error types and improved error handling.
    
    Args:
        user_id: ID of the user whose playlists should be synced
        **kwargs: Additional keyword arguments (for RQ compatibility)
        
    Returns:
        dict: Summary of the sync operation
        
    Raises:
        Exception: Re-raises exceptions for RQ to handle based on retry configuration
    """
    import os
    from flask import current_app
    from .. import create_app
    from rq import get_current_job
    
    # Create a new app instance for the background task
    app = create_app()
    
    with app.app_context():
        # Get current job for metadata access
        job = get_current_job()
        attempt_number = getattr(job, 'retries_left', MAX_RETRIES) if job else MAX_RETRIES
        current_attempt = MAX_RETRIES - attempt_number + 1
        
        try:
            # Ensure environment variables are set from the app config
            spotify_config_keys = [
                'SPOTIPY_CLIENT_ID', 
                'SPOTIPY_CLIENT_SECRET', 
                'SPOTIPY_REDIRECT_URI',
                'SPOTIFY_SCOPES'
            ]
            for key in spotify_config_keys:
                if key not in os.environ and key in app.config:
                    os.environ[key] = app.config[key]
                    
            current_app.logger.info(
                f"Starting background playlist sync task for user_id={user_id} (attempt {current_attempt}/{MAX_RETRIES})"
            )
            
            # Update job metadata with attempt information
            if job:
                job.meta.update({
                    'current_attempt': current_attempt,
                    'max_attempts': MAX_RETRIES,
                    'started_at': datetime.utcnow().isoformat()
                })
                job.save_meta()
            
            # Call the implementation
            result = _execute_playlist_sync_impl(user_id)
            
            # Check if the result indicates a non-retryable error
            if not result.get('success', False):
                error_type = result.get('error_type', 'unknown')
                retryable = result.get('retryable', True)
                
                # Log the error result
                current_app.logger.warning(
                    f"Playlist sync failed for user_id={user_id}: {error_type}",
                    extra=result
                )
                
                # For non-retryable errors, don't raise an exception (job succeeds but with error result)
                if not retryable:
                    current_app.logger.info(f"Non-retryable error for user_id={user_id}, marking job as completed with error")
                    return result
                    
                # For retryable errors, raise an exception to trigger retry if attempts remain
                if current_attempt < MAX_RETRIES:
                    error_msg = result.get('error', 'Unknown error during playlist sync')
                    current_app.logger.info(f"Retryable error for user_id={user_id}, will retry (attempt {current_attempt}/{MAX_RETRIES})")
                    raise Exception(f"Retryable error: {error_msg}")
                else:
                    current_app.logger.error(f"Max retries exceeded for user_id={user_id}, giving up")
                    return result
            
            # Success case
            current_app.logger.info(f"Completed background playlist sync task for user_id={user_id} successfully")
            return result
            
        except Exception as e:
            # Enhanced error logging with context
            error_context = {
                'user_id': user_id,
                'attempt_number': current_attempt,
                'max_attempts': MAX_RETRIES,
                'job_id': job.id if job else None,
                'error_type': type(e).__name__
            }
            
            current_app.logger.exception(
                f"Error in _execute_playlist_sync_task for user_id={user_id} (attempt {current_attempt}): {e}",
                extra=error_context
            )
            
            # Update job metadata with error information
            if job:
                job.meta.update({
                    'last_error': str(e),
                    'error_type': type(e).__name__,
                    'failed_at': datetime.utcnow().isoformat(),
                    'attempt_number': current_attempt
                })
                job.save_meta()
            
            # Re-raise to mark the job as failed and trigger retry logic
            raise

def enqueue_playlist_sync(user_id: int) -> Optional[Any]:
    """
    Enqueue a background job to sync playlists for the given user.
    
    This function creates a background RQ job that will execute the playlist sync
    process asynchronously, allowing the web request to return immediately while
    the sync runs in the background.
    
    Args:
        user_id: ID of the user whose playlists should be synced
        
    Returns:
        Job object if enqueued successfully, None otherwise.
    """
    from flask import current_app
    
    # Use the current app context instead of creating a new one
    try:
        # Ensure environment variables are set from the app config
        import os
        spotify_config_keys = [
            'SPOTIPY_CLIENT_ID', 
            'SPOTIPY_CLIENT_SECRET', 
            'SPOTIPY_REDIRECT_URI',
            'SPOTIFY_SCOPES'
        ]
        for key in spotify_config_keys:
            if key not in os.environ and key in current_app.config:
                os.environ[key] = current_app.config[key]
        
        # Ensure we have a database session and the user exists
        from ..models import User
        from ..extensions import db
        
        # Commit any pending changes to ensure consistency
        db.session.commit()
        
        # Verify the user exists
        user = db.session.get(User, user_id)
        if not user:
            current_app.logger.error(f"Cannot enqueue playlist sync: User with ID {user_id} not found in database")
            return None
            
        current_app.logger.info(f"Enqueueing background playlist sync for user: {user.display_name or user.email} (ID: {user_id})")
        
        try:
            # Get the default queue
            from ..extensions import rq
            
            # Enqueue the job with retry configuration
            job = rq.get_queue().enqueue(
                'app.services.playlist_sync_service._execute_playlist_sync_task',
                user_id=user_id,
                job_timeout=current_app.config.get('RQ_JOB_TIMEOUT', DEFAULT_JOB_TIMEOUT),
                retry=Retry(max=MAX_RETRIES, interval=RETRY_INTERVALS),
                meta={
                    'user_id': user_id,
                    'task_type': 'playlist_sync',
                    'enqueued_at': datetime.utcnow().isoformat()
                }
            )
            
            if job:
                current_app.logger.info(f"Playlist sync task for user ID {user_id} enqueued with job ID: {job.id}")
                return job
            else:
                current_app.logger.error(f"Failed to enqueue playlist sync job for user ID {user_id}")
                return None
                
        except Exception as e:
            current_app.logger.exception(f"Error enqueueing playlist sync job for user ID {user_id}: {e}")
            return None
            
    except Exception as e:
        current_app.logger.exception(f"Unexpected error in enqueue_playlist_sync: {e}")
        return None

def get_sync_status(user_id: int) -> Dict[str, Any]:
    """
    Check if there's an active playlist sync job for the given user.
    
    Enhanced to include failed job information, retry status, and error details.
    
    Args:
        user_id: ID of the user to check sync status for
        
    Returns:
        dict: Status information about playlist sync jobs including active, failed, and retry information
    """
    from flask import current_app
    from ..extensions import rq
    
    try:
        queue = rq.get_queue()
        
        # Get jobs in various states (RQ get_jobs expects individual status args, not a list)
        active_jobs = []
        failed_jobs = []
        finished_jobs = []
        
        # Get jobs by status individually
        try:
            active_jobs.extend(queue.get_jobs(registry_type='started'))
        except:
            pass
        try:
            active_jobs.extend(queue.get_jobs(registry_type='queued'))
        except:
            pass
        try:
            failed_jobs = queue.get_jobs(registry_type='failed')
        except:
            pass
        try:
            finished_jobs = queue.get_jobs(registry_type='finished')
        except:
            pass
        
        user_sync_jobs = {
            'active': [],
            'failed': [],
            'recent_completed': []
        }
        
        # Process active jobs
        for job in active_jobs:
            if _is_user_sync_job(job, user_id):
                job_info = _extract_job_info(job)
                user_sync_jobs['active'].append(job_info)
        
        # Process failed jobs (recent failures)
        for job in failed_jobs[-10:]:  # Last 10 failed jobs
            if _is_user_sync_job(job, user_id):
                job_info = _extract_job_info(job)
                job_info.update({
                    'failure_info': {
                        'exc_info': job.exc_info,
                        'failed_at': job.ended_at.isoformat() if job.ended_at else None,
                        'retry_info': _get_retry_info(job)
                    }
                })
                user_sync_jobs['failed'].append(job_info)
        
        # Process recently completed jobs
        for job in finished_jobs[-5:]:  # Last 5 finished jobs
            if _is_user_sync_job(job, user_id):
                job_info = _extract_job_info(job)
                job_info.update({
                    'completed_at': job.ended_at.isoformat() if job.ended_at else None,
                    'result': job.result if hasattr(job, 'result') else None
                })
                user_sync_jobs['recent_completed'].append(job_info)
        
        # Determine overall status
        has_active_sync = len(user_sync_jobs['active']) > 0
        has_recent_failures = len(user_sync_jobs['failed']) > 0
        
        return {
            "user_id": user_id,
            "has_active_sync": has_active_sync,
            "has_recent_failures": has_recent_failures,
            "jobs": user_sync_jobs,
            "summary": {
                "active_count": len(user_sync_jobs['active']),
                "failed_count": len(user_sync_jobs['failed']),
                "recent_completed_count": len(user_sync_jobs['recent_completed'])
            },
            "checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        current_app.logger.exception(f"Error checking sync status for user {user_id}: {e}")
        return {
            "user_id": user_id,
            "has_active_sync": False,
            "has_recent_failures": False,
            "jobs": {'active': [], 'failed': [], 'recent_completed': []},
            "summary": {
                "active_count": 0,
                "failed_count": 0,
                "recent_completed_count": 0
            },
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat()
        }

def _is_user_sync_job(job, user_id: int) -> bool:
    """
    Check if a job is a playlist sync job for the specified user.
    
    Args:
        job: RQ job object
        user_id: User ID to check for
        
    Returns:
        bool: True if job belongs to the user and is a sync job
    """
    if not job:
        return False
        
    # Check function name
    if not ('playlist_sync' in job.func_name):
        return False
    
    # Check user ID in args
    if hasattr(job, 'args') and len(job.args) > 0:
        return str(job.args[0]) == str(user_id)
    
    # Check user ID in metadata
    if hasattr(job, 'meta') and job.meta:
        return str(job.meta.get('user_id', '')) == str(user_id)
    
    return False

def _extract_job_info(job) -> Dict[str, Any]:
    """
    Extract relevant information from an RQ job.
    
    Args:
        job: RQ job object
        
    Returns:
        dict: Job information dictionary
    """
    job_info = {
        'job_id': job.id,
        'status': job.get_status(),
        'created_at': job.created_at.isoformat() if job.created_at else None,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'meta': job.meta if hasattr(job, 'meta') else {}
    }
    
    return job_info

def _get_retry_info(job) -> Dict[str, Any]:
    """
    Extract retry information from a failed job.
    
    Args:
        job: RQ job object
        
    Returns:
        dict: Retry information
    """
    retry_info = {
        'has_retries': hasattr(job, 'retry') and job.retry is not None,
        'max_retries': 0,
        'attempts_made': 0,
        'retries_left': 0
    }
    
    if hasattr(job, 'retry') and job.retry:
        max_retries = getattr(job.retry, 'max', 0)
        retries_left = getattr(job, 'retries_left', 0)
        
        # Ensure we have numeric values for arithmetic
        try:
            max_retries = int(max_retries) if max_retries is not None else 0
            retries_left = int(retries_left) if retries_left is not None else 0
        except (ValueError, TypeError):
            max_retries = 0
            retries_left = 0
            
        retry_info.update({
            'max_retries': max_retries,
            'retries_left': retries_left
        })
        retry_info['attempts_made'] = max_retries - retries_left
    
    # Get attempt information from metadata if available
    if hasattr(job, 'meta') and job.meta:
        retry_info.update({
            'current_attempt': job.meta.get('current_attempt', 1),
            'max_attempts': job.meta.get('max_attempts', 1),
            'last_error': job.meta.get('last_error', ''),
            'retry_reason': job.meta.get('retry_reason', '')
        })
    
    return retry_info 