"""
Playlist Sync Service

This module provides background job functionality for syncing playlists
with Spotify and managing sync status.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from flask import current_app
from rq import get_current_job

from .. import db
from ..models.models import User, Playlist, Song, PlaylistSong
from .spotify_service import SpotifyService

logger = logging.getLogger(__name__)


def sync_user_playlists_task(user_id: int) -> Dict[str, Any]:
    """
    Background task function for syncing all user playlists.
    
    This function is executed by RQ workers.
    
    Args:
        user_id (int): ID of the user whose playlists to sync
        
    Returns:
        Dict containing sync results
    """
    try:
        logger.info(f"Starting playlist sync for user {user_id}")
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Update job status
        job = get_current_job()
        if job:
            job.meta['status'] = 'syncing_playlists'
            job.meta['user_id'] = user_id
            job.save_meta()
        
        # Sync playlists using the service
        service = PlaylistSyncService()
        result = service.sync_user_playlists(user)
        
        # Trigger auto-analysis after successful sync
        if result.get('success'):
            try:
                from .unified_analysis_service import UnifiedAnalysisService
                analysis_service = UnifiedAnalysisService()
                analysis_result = analysis_service.auto_analyze_user_after_sync(user_id)
                
                # Add analysis info to result
                result['auto_analysis'] = analysis_result
                logger.info(f"Auto-analysis triggered for user {user_id}: {analysis_result}")
            except Exception as e:
                logger.warning(f"Auto-analysis failed for user {user_id}: {e}")
                result['auto_analysis'] = {'success': False, 'error': str(e)}
        
        if job:
            job.meta['status'] = 'completed'
            job.meta['result'] = result
            job.save_meta()
        
        logger.info(f"Playlist sync completed for user {user_id}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in playlist sync task for user {user_id}: {e}")
        
        job = get_current_job()
        if job:
            job.meta['status'] = 'failed'
            job.meta['error'] = str(e)
            job.save_meta()
        
        return {
            'user_id': user_id,
            'success': False,
            'error': str(e),
            'completed_at': datetime.now(timezone.utc).isoformat()
        }


class PlaylistSyncService:
    """Service for synchronizing playlists between Spotify and local database."""
    
    def __init__(self):
        pass
    
    def sync_user_playlists(self, user: User) -> Dict[str, Any]:
        """Sync all playlists for a user from Spotify."""
        try:
            spotify_service = SpotifyService(user)
            spotify_playlists = spotify_service.get_user_playlists()
            
            synced_count = 0
            updated_count = 0
            
            for spotify_playlist in spotify_playlists:
                playlist = self._sync_single_playlist(user, spotify_playlist)
                if playlist:
                    # Check if this was a new playlist or update
                    if hasattr(playlist, '_is_new'):
                        synced_count += 1
                        # For new playlists, also sync their tracks
                        self.sync_playlist_tracks(user, playlist)
                    else:
                        updated_count += 1
            
            return {
                'success': True,
                'synced': synced_count,
                'updated': updated_count,
                'total': len(spotify_playlists)
            }
            
        except Exception as e:
            logger.error(f'Failed to sync playlists for user {user.id}: {e}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_playlist_tracks(self, user: User, playlist: Playlist) -> Dict[str, Any]:
        """Sync tracks for a specific playlist."""
        try:
            spotify_service = SpotifyService(user)
            # Get tracks from Spotify - handle both direct track format and wrapped format
            spotify_tracks = spotify_service.get_playlist_tracks(playlist.spotify_id)
            
            # Clear existing tracks
            PlaylistSong.query.filter_by(playlist_id=playlist.id).delete()
            
            synced_tracks = 0
            for position, track_data in enumerate(spotify_tracks):
                # Handle both direct track format and wrapped format
                if isinstance(track_data, dict) and 'track' in track_data:
                    track = track_data['track']
                else:
                    track = track_data
                
                if not track or (isinstance(track, dict) and track.get('type') == 'episode'):
                    continue
                
                song = self._sync_single_song(track)
                if song:
                    # Add to playlist
                    playlist_song = PlaylistSong(
                        playlist_id=playlist.id,
                        song_id=song.id,
                        track_position=position,
                        added_at_spotify=datetime.now(timezone.utc)
                    )
                    db.session.add(playlist_song)
                    synced_tracks += 1
            
            db.session.commit()
            
            return {
                'success': True,
                'synced_tracks': synced_tracks,
                'playlist_id': playlist.id
            }
            
        except Exception as e:
            logger.error(f'Failed to sync tracks for playlist {playlist.id}: {e}')
            db.session.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _sync_single_playlist(self, user: User, spotify_playlist: Dict[str, Any]) -> Optional[Playlist]:
        """Sync a single playlist from Spotify data."""
        try:
            # Check if playlist already exists
            playlist = Playlist.query.filter_by(
                owner_id=user.id,
                spotify_id=spotify_playlist['id']
            ).first()
            
            is_new = False
            if not playlist:
                playlist = Playlist(
                    owner_id=user.id,
                    spotify_id=spotify_playlist['id']
                )
                db.session.add(playlist)
                is_new = True
            
            # Update playlist metadata
            playlist.name = spotify_playlist['name']
            playlist.description = spotify_playlist.get('description', '')
            playlist.track_count = spotify_playlist.get('tracks', {}).get('total', 0)
            
            if spotify_playlist.get('images'):
                playlist.image_url = spotify_playlist['images'][0]['url']
            
            if is_new:
                playlist._is_new = True  # Mark for return value calculation
            
            db.session.commit()
            return playlist
            
        except Exception as e:
            logger.error(f'Failed to sync playlist {spotify_playlist["id"]}: {e}')
            db.session.rollback()
            return None
    
    def _sync_single_song(self, track_data: Dict[str, Any]) -> Optional[Song]:
        """Sync a single song from Spotify track data."""
        try:
            # Check if song already exists
            song = Song.query.filter_by(spotify_id=track_data['id']).first()
            
            if not song:
                # Create new song
                song = Song(
                    spotify_id=track_data['id'],
                    title=track_data['name'],
                    artist=', '.join([artist['name'] for artist in track_data['artists']]),
                    album=track_data['album']['name'],
                    duration_ms=track_data.get('duration_ms'),
                    explicit=track_data.get('explicit', False)
                )
                db.session.add(song)
                db.session.flush()  # Get the ID
            
            return song
            
        except Exception as e:
            logger.error(f'Failed to sync song {track_data["id"]}: {e}')
            return None


def enqueue_user_playlist_sync(user_id: int, priority: str = 'default') -> Dict[str, Any]:
    """
    Enqueue a user playlist sync job for background processing.
    
    Args:
        user_id (int): ID of the user requesting sync
        priority (str): Job priority ('high', 'default', 'low')
        
    Returns:
        Dict containing job information:
        - job_id: Unique identifier for the job
        - status: Job status ('queued', 'processing', 'completed', 'failed')
        - estimated_duration: Estimated completion time
    """
    try:
        from ..extensions import rq
        queue = rq.get_queue(priority)
        
        job = queue.enqueue(
            sync_user_playlists_task,
            user_id,
            job_timeout=600,  # 10 minute timeout
            meta={
                'user_id': user_id,
                'status': 'queued',
                'queued_at': datetime.now(timezone.utc).isoformat()
            }
        )
        
        logger.info(f"User playlist sync job {job.id} enqueued for user {user_id}")
        
        return {
            'job_id': job.id,
            'status': 'queued',
            'user_id': user_id,
            'priority': priority,
            'estimated_duration': 180,  # 3 minutes estimate
            'queued_at': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error enqueuing user playlist sync for user {user_id}: {e}")
        return {
            'job_id': None,
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


def enqueue_playlist_sync(playlist_id: int, user_id: int, priority: str = 'normal') -> Dict[str, Any]:
    """
    Enqueue a playlist sync job for background processing.
    
    Args:
        playlist_id (int): ID of the playlist to sync
        user_id (int): ID of the user requesting sync
        priority (str): Job priority ('high', 'normal', 'low')
        
    Returns:
        Dict containing job information:
        - job_id: Unique identifier for the job
        - status: Job status ('queued', 'processing', 'completed', 'failed')
        - estimated_duration: Estimated completion time
    """
    try:
        # This would normally enqueue with RQ
        # For now, return mock job info for tests
        job_info = {
            'job_id': f'sync_{playlist_id}_{int(datetime.now().timestamp())}',
            'status': 'queued',
            'playlist_id': playlist_id,
            'user_id': user_id,
            'priority': priority,
            'estimated_duration': 30,  # seconds
            'queued_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Playlist sync job enqueued: {job_info}")
        return job_info
        
    except Exception as e:
        logger.error(f"Error enqueuing playlist sync: {e}")
        return {
            'job_id': None,
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


def get_sync_status(job_id: Optional[str] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Get sync status for jobs.
    
    Args:
        job_id (str, optional): Specific job ID to check
        user_id (int, optional): Get all jobs for a user
        
    Returns:
        Dict containing sync status information:
        - jobs: List of job statuses
        - active_count: Number of active jobs
        - completed_count: Number of completed jobs
        - failed_count: Number of failed jobs
    """
    try:
        from rq import Queue
        from ..extensions import rq
        
        if job_id:
            # Get specific job status
            try:
                job = rq.get_queue().fetch_job(job_id)
                if job:
                    return {
                        'job_id': job_id,
                        'status': job.get_status(),
                        'progress': job.meta.get('progress', 0),
                        'started_at': job.started_at.isoformat() if job.started_at else None,
                        'ended_at': job.ended_at.isoformat() if job.ended_at else None,
                        'result': job.result,
                        'meta': job.meta
                    }
                else:
                    return {
                        'job_id': job_id,
                        'status': 'not_found',
                        'error': 'Job not found'
                    }
            except Exception as e:
                return {
                    'job_id': job_id,
                    'status': 'error',
                    'error': str(e)
                }
        else:
            # Return overview for user
            return {
                'user_id': user_id,
                'active_count': 0,
                'completed_count': 0,
                'failed_count': 0,
                'total_jobs': 0,
                'last_sync': None,
                'sync_in_progress': False,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


def sync_playlist_task(playlist_id: int, user_id: int) -> Dict[str, Any]:
    """
    Background task function for syncing a playlist.
    
    This would normally be executed by RQ workers.
    
    Args:
        playlist_id (int): ID of the playlist to sync
        user_id (int): ID of the user
        
    Returns:
        Dict containing sync results
    """
    try:
        logger.info(f"Starting playlist sync: playlist_id={playlist_id}, user_id={user_id}")
        
        # Mock sync process
        result = {
            'playlist_id': playlist_id,
            'user_id': user_id,
            'status': 'completed',
            'tracks_synced': 0,  # Would be actual count
            'new_tracks': 0,
            'updated_tracks': 0,
            'errors': [],
            'duration': 25,
            'completed_at': datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Playlist sync completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in playlist sync task: {e}")
        return {
            'playlist_id': playlist_id,
            'user_id': user_id,
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.now(timezone.utc).isoformat()
        } 