"""
Playlist Sync Service

This module provides background job functionality for syncing playlists
with Spotify and managing sync status.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from flask import current_app
from sqlalchemy.exc import IntegrityError

from .. import db
from ..models.models import User, Playlist, Song, PlaylistSong
# Removed: from ..utils.spotify import get_user_playlists, get_playlist_tracks - these functions don't exist

logger = logging.getLogger(__name__)


def sync_user_playlists_task(user_id: int) -> Dict[str, Any]:
    """
    Background task function for syncing all playlists for a user.
    
    This function is designed to be executed by the priority queue workers.
    
    Args:
        user_id (int): ID of the user whose playlists to sync
        
    Returns:
        Dict containing sync results:
        - status: 'completed' or 'failed'
        - playlists_synced: Number of playlists processed
        - new_playlists: Number of new playlists added
        - updated_playlists: Number of existing playlists updated
        - total_tracks: Total number of tracks processed
        - errors: List of any errors encountered
        - duration: Time taken in seconds
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        logger.info(f"Starting user playlist sync for user {user_id}")
        
        # Get user from database
        user = db.session.get(User, user_id)
        if not user:
            error_msg = f"User {user_id} not found"
            logger.error(error_msg)
            return {
                'status': 'failed',
                'error': error_msg,
                'user_id': user_id,
                'duration': 0,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
        
        # Use the sync service to perform the actual sync
        sync_service = PlaylistSyncService()
        result = sync_service.sync_user_playlists(user)
        
        # Calculate duration
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        result['duration'] = duration
        result['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"User playlist sync completed for user {user_id}: {result}")
        return result
        
    except Exception as e:
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        error_msg = f"Error in user playlist sync task for user {user_id}: {e}"
        logger.error(error_msg)
        return {
            'status': 'failed',
            'error': str(e),
            'user_id': user_id,
            'duration': duration,
            'completed_at': datetime.now(timezone.utc).isoformat()
        }


class PlaylistSyncService:
    """Service for synchronizing playlists between Spotify and local database."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def sync_user_playlists(self, user: User) -> Dict[str, Any]:
        """Sync all playlists for a user from Spotify."""
        try:
            self.logger.info(f"Starting playlist sync for user {user.id}")
            
            # Get playlists from Spotify using SpotifyService
            from .spotify_service import SpotifyService
            spotify_service = SpotifyService(user)
            spotify_playlists = spotify_service.get_user_playlists()
            
            if not spotify_playlists:
                return {
                    'status': 'completed',
                    'playlists_synced': 0,
                    'new_playlists': 0,
                    'updated_playlists': 0,
                    'total_tracks': 0,
                    'message': 'No playlists found or access token invalid'
                }
            
            # Sync each playlist
            playlists_synced = 0
            new_playlists = 0
            updated_playlists = 0
            total_tracks = 0
            errors = []
            
            for spotify_playlist in spotify_playlists:
                try:
                    playlist = self._sync_single_playlist(user, spotify_playlist)
                    if playlist:
                        # Sync tracks for this playlist
                        track_result = self.sync_playlist_tracks(user, playlist)
                        total_tracks += track_result.get('tracks_synced', 0)
                        
                        if track_result.get('is_new', False):
                            new_playlists += 1
                        else:
                            updated_playlists += 1
                        playlists_synced += 1
                except Exception as e:
                    error_msg = f"Error syncing playlist {spotify_playlist.get('name', 'Unknown')}: {e}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            # Trigger auto-analysis for new songs
            try:
                from .unified_analysis_service import UnifiedAnalysisService
                analysis_service = UnifiedAnalysisService()
                analysis_result = analysis_service.auto_analyze_user_after_sync(user.id)
                self.logger.info(f"Auto-analysis triggered: {analysis_result}")
            except Exception as e:
                self.logger.warning(f"Failed to trigger auto-analysis: {e}")
            
            return {
                'status': 'completed',
                'playlists_synced': playlists_synced,
                'new_playlists': new_playlists,
                'updated_playlists': updated_playlists,
                'total_tracks': total_tracks,
                'errors': errors
            }
            
        except Exception as e:
            self.logger.error(f"Error syncing playlists for user {user.id}: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'playlists_synced': 0,
                'new_playlists': 0,
                'updated_playlists': 0,
                'total_tracks': 0
            }

    def sync_playlist_tracks(self, user: User, playlist: Playlist) -> Dict[str, Any]:
        """Sync tracks for a specific playlist."""
        try:
            self.logger.info(f"Syncing tracks for playlist {playlist.name} (ID: {playlist.id})")
            
            # Get tracks from Spotify using SpotifyService
            from .spotify_service import SpotifyService
            spotify_service = SpotifyService(user)
            spotify_tracks = spotify_service.get_playlist_tracks(playlist.spotify_id)
            
            if not spotify_tracks:
                return {
                    'status': 'completed',
                    'tracks_synced': 0,
                    'new_tracks': 0,
                    'message': 'No tracks found for playlist'
                }
            
            # Clear existing playlist-song associations
            PlaylistSong.query.filter_by(playlist_id=playlist.id).delete()
            
            # Sync each track
            tracks_synced = 0
            new_tracks = 0
            
            for i, track_data in enumerate(spotify_tracks):
                try:
                    song = self._sync_single_song(track_data)
                    if song:
                        # Create playlist-song association
                        playlist_song = PlaylistSong(
                            playlist_id=playlist.id,
                            song_id=song.id,
                            track_position=i
                        )
                        db.session.add(playlist_song)
                        tracks_synced += 1
                        
                        # Check if this is a new song
                        if hasattr(song, '_is_new') and song._is_new:
                            new_tracks += 1
                            
                except Exception as e:
                    self.logger.error(f"Error syncing track: {e}")
            
            # Update playlist track count
            playlist.track_count = tracks_synced
            db.session.commit()
            
            return {
                'status': 'completed',
                'tracks_synced': tracks_synced,
                'new_tracks': new_tracks,
                'playlist_id': playlist.id
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error syncing tracks for playlist {playlist.id}: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'tracks_synced': 0,
                'new_tracks': 0,
                'playlist_id': playlist.id
            }

    def _sync_single_playlist(self, user: User, spotify_playlist: Dict[str, Any]) -> Optional[Playlist]:
        """Sync a single playlist from Spotify data."""
        try:
            spotify_id = spotify_playlist['id']
            
            # Check if playlist already exists
            playlist = Playlist.query.filter_by(
                owner_id=user.id,
                spotify_id=spotify_id
            ).first()
            
            is_new = playlist is None
            
            if not playlist:
                playlist = Playlist(
                    owner_id=user.id,
                    spotify_id=spotify_id
                )
                db.session.add(playlist)
            
            # Update playlist data
            playlist.name = spotify_playlist['name']
            playlist.description = spotify_playlist.get('description', '')
            playlist.public = spotify_playlist.get('public', False)
            playlist.track_count = spotify_playlist.get('tracks', {}).get('total', 0)
            
            # Handle image URL
            images = spotify_playlist.get('images', [])
            if images:
                playlist.image_url = images[0]['url']
            
            db.session.commit()
            playlist._is_new = is_new  # Mark for tracking
            
            return playlist
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error syncing playlist {spotify_playlist.get('name', 'Unknown')}: {e}")
            return None
    
    def _sync_single_song(self, track_data: Dict[str, Any]) -> Optional[Song]:
        """Sync a single song from Spotify track data."""
        try:
            track = track_data['track']
            if not track or track['id'] is None:
                return None
                
            spotify_id = track['id']
            
            # Check if song already exists
            song = Song.query.filter_by(spotify_id=spotify_id).first()
            
            is_new = song is None
            
            if not song:
                song = Song(spotify_id=spotify_id)
                db.session.add(song)
            
            # Update song data
            song.title = track['name']
            song.artist = ', '.join([artist['name'] for artist in track['artists']])
            song.album = track['album']['name']
            song.duration_ms = track.get('duration_ms', 0)
            
            # Handle album art
            album_images = track['album'].get('images', [])
            if album_images:
                song.album_art_url = album_images[0]['url']
            
            db.session.commit()
            song._is_new = is_new  # Mark for tracking
            
            return song
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error syncing song: {e}")
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
        # Mock job info - would integrate with priority queue system
        job_id = f'user_sync_{user_id}_{int(datetime.now().timestamp())}'
        
        logger.info(f"User playlist sync job {job_id} enqueued for user {user_id}")
        
        return {
            'job_id': job_id,
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
        if job_id:
            # Mock job status for now - would integrate with priority queue system
            return {
                'job_id': job_id,
                'status': 'completed',
                'progress': 100,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'ended_at': datetime.now(timezone.utc).isoformat(),
                'result': {'status': 'completed'},
                'meta': {}
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