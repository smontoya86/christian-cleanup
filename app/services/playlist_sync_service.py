"""
Playlist Sync Service

This module provides background job functionality for syncing playlists
with Spotify and managing sync status.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .. import db
from ..models.models import Playlist, PlaylistSong, Song, User

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
                "status": "failed",
                "error": error_msg,
                "user_id": user_id,
                "duration": 0,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        # Use the sync service to perform the actual sync
        sync_service = PlaylistSyncService()
        result = sync_service.sync_user_playlists(user)

        # Calculate duration
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        result["duration"] = duration
        result["completed_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"User playlist sync completed for user {user_id}: {result}")
        return result

    except Exception as e:
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        error_msg = f"Error in user playlist sync task for user {user_id}: {e}"
        logger.error(error_msg)
        return {
            "status": "failed",
            "error": str(e),
            "user_id": user_id,
            "duration": duration,
            "completed_at": datetime.now(timezone.utc).isoformat(),
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
                    "status": "completed",
                    "playlists_synced": 0,
                    "new_playlists": 0,
                    "updated_playlists": 0,
                    "total_tracks": 0,
                    "message": "No playlists found or access token invalid",
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
                        total_tracks += track_result.get("tracks_synced", 0)

                        # Check if playlist is new based on the _is_new attribute
                        if hasattr(playlist, "_is_new") and playlist._is_new:
                            new_playlists += 1
                        else:
                            updated_playlists += 1
                        playlists_synced += 1
                except Exception as e:
                    error_msg = (
                        f"Error syncing playlist {spotify_playlist.get('name', 'Unknown')}: {e}"
                    )
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
                "status": "completed",
                "playlists_synced": playlists_synced,
                "new_playlists": new_playlists,
                "updated_playlists": updated_playlists,
                "total_tracks": total_tracks,
                "errors": errors,
            }

        except Exception as e:
            self.logger.error(f"Error syncing playlists for user {user.id}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "playlists_synced": 0,
                "new_playlists": 0,
                "updated_playlists": 0,
                "total_tracks": 0,
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
                    "status": "completed",
                    "tracks_synced": 0,
                    "new_tracks": 0,
                    "message": "No tracks found for playlist",
                }

            # Use single transaction for all operations
            try:
                # Clear existing playlist-song associations
                PlaylistSong.query.filter_by(playlist_id=playlist.id).delete()

                # Sync each track using batch operations
                tracks_synced = 0
                new_tracks = 0
                playlist_songs_to_add = []
                album_art_urls = []

                # Track which songs we've already added to avoid duplicates
                added_song_ids = set()
                
                for i, track_data in enumerate(spotify_tracks):
                    try:
                        song = self._sync_single_song_atomic(track_data)
                        if song:
                            # Only add first occurrence of each song (skip duplicates)
                            if song.id not in added_song_ids:
                                playlist_songs_to_add.append(
                                    {
                                        "playlist_id": playlist.id,
                                        "song_id": song.id,
                                        "track_position": i,
                                    }
                                )
                                added_song_ids.add(song.id)
                                tracks_synced += 1

                                # Check if this is a new song
                                if hasattr(song, "_is_new") and song._is_new:
                                    new_tracks += 1

                                # Collect album art URL for collage
                                if song.album_art_url:
                                    album_art_urls.append(song.album_art_url)

                    except Exception as e:
                        self.logger.error(f"Error syncing track: {e}")
                        continue

                # Batch insert playlist-song associations
                if playlist_songs_to_add:
                    db.session.bulk_insert_mappings(PlaylistSong, playlist_songs_to_add)

                # Update playlist track count and timestamp
                playlist.track_count = tracks_synced
                playlist.updated_at = datetime.now(timezone.utc)

                # Compute up to 4 deduplicated collage URLs in-order of appearance
                if album_art_urls:
                    seen = set()
                    deduped = []
                    for url in album_art_urls:
                        if url and url not in seen:
                            seen.add(url)
                            deduped.append(url)
                        if len(deduped) >= 4:
                            break
                    playlist.cover_collage_urls = deduped if deduped else None
                else:
                    playlist.cover_collage_urls = None

                # Commit all changes in single transaction
                db.session.commit()

                return {
                    "status": "completed",
                    "tracks_synced": tracks_synced,
                    "new_tracks": new_tracks,
                    "playlist_id": playlist.id,
                }

            except Exception as e:
                # Rollback the entire transaction on any failure
                db.session.rollback()
                self.logger.error(f"Transaction failed during playlist sync: {e}")
                return {
                    "status": "failed",
                    "error": str(e),
                    "tracks_synced": 0,
                    "new_tracks": 0,
                    "playlist_id": playlist.id,
                }

        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error syncing tracks for playlist {playlist.id}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "tracks_synced": 0,
                "new_tracks": 0,
                "playlist_id": playlist.id,
            }

    def _sync_single_playlist(
        self, user: User, spotify_playlist: Dict[str, Any]
    ) -> Optional[Playlist]:
        """Sync a single playlist from Spotify data."""
        try:
            spotify_id = spotify_playlist["id"]

            # Check if playlist already exists
            playlist = Playlist.query.filter_by(owner_id=user.id, spotify_id=spotify_id).first()

            is_new = playlist is None

            if not playlist:
                playlist = Playlist(owner_id=user.id, spotify_id=spotify_id)
                db.session.add(playlist)

            # Update playlist data and timestamp
            playlist.name = spotify_playlist["name"]
            playlist.description = spotify_playlist.get("description", "")
            playlist.public = spotify_playlist.get("public", False)
            playlist.updated_at = datetime.now(timezone.utc)

            # Handle image URL
            images = spotify_playlist.get("images", [])
            if images:
                playlist.image_url = images[0]["url"]

            # Don't set track_count from Spotify API here - it will be set accurately during sync
            # This ensures consistency between services and reflects actual synced tracks
            if is_new:
                playlist.track_count = 0  # Will be updated during track sync

            db.session.commit()
            playlist._is_new = is_new  # Mark for tracking

            return playlist

        except Exception as e:
            db.session.rollback()
            self.logger.error(
                f"Error syncing playlist {spotify_playlist.get('name', 'Unknown')}: {e}"
            )
            return None

    def _sync_single_song(self, track_data: Dict[str, Any]) -> Optional[Song]:
        """Sync a single song from Spotify track data."""
        try:
            track = track_data["track"]
            if not track or track["id"] is None:
                return None

            spotify_id = track["id"]

            # Check if song already exists
            song = Song.query.filter_by(spotify_id=spotify_id).first()

            is_new = song is None

            if not song:
                song = Song(spotify_id=spotify_id)
                db.session.add(song)

            # Update song data
            song.title = track["name"] or "Unknown Title"
            # Filter out None/empty artist names and provide fallback
            artist_names = [a["name"] for a in track.get("artists", []) if a.get("name")]
            song.artist = ", ".join(artist_names) if artist_names else "Unknown Artist"
            song.album = track.get("album", {}).get("name") or "Unknown Album"
            song.duration_ms = track.get("duration_ms", 0)

            # Handle album art
            album_images = track.get("album", {}).get("images", [])
            if album_images:
                song.album_art_url = album_images[0]["url"]

            db.session.commit()
            song._is_new = is_new  # Mark for tracking

            return song

        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error syncing song: {e}")
            return None

    def _sync_single_song_atomic(self, track_data: Dict[str, Any]) -> Optional[Song]:
        """Sync a single song from Spotify track data without committing (for atomic operations)."""
        try:
            track = track_data["track"]
            if not track or track["id"] is None:
                return None

            spotify_id = track["id"]

            # Check if song already exists
            song = Song.query.filter_by(spotify_id=spotify_id).first()

            is_new = song is None

            if not song:
                song = Song(spotify_id=spotify_id)
                db.session.add(song)

            # Update song data
            song.title = track["name"] or "Unknown Title"
            # Filter out None/empty artist names and provide fallback
            artist_names = [a["name"] for a in track.get("artists", []) if a.get("name")]
            song.artist = ", ".join(artist_names) if artist_names else "Unknown Artist"
            song.album = track.get("album", {}).get("name") or "Unknown Album"
            song.duration_ms = track.get("duration_ms", 0)

            # Handle album art
            album_images = track.get("album", {}).get("images", [])
            if album_images:
                song.album_art_url = album_images[0]["url"]

            # Flush to get the ID but don't commit
            db.session.flush()
            song._is_new = is_new  # Mark for tracking

            return song

        except Exception as e:
            self.logger.error(f"Error syncing song: {e}")
            raise  # Re-raise to allow transaction rollback


def enqueue_user_playlist_sync(user_id: int, priority: str = "default") -> Dict[str, Any]:
    """
    DEPRECATED: Queue system removed - playlist sync is now immediate.

    Args:
        user_id (int): ID of the user (parameter kept for compatibility)
        priority (str): Job priority (ignored - parameter kept for compatibility)

    Returns:
        Dict containing deprecation notice
    """
    logger.warning(
        f"enqueue_user_playlist_sync called for user {user_id} - DEPRECATED: Queue system removed"
    )

    return {
        "job_id": f"deprecated_sync_{user_id}",
        "status": "deprecated",
        "user_id": user_id,
        "priority": priority,
        "message": "Queue system removed. Playlist sync is now immediate.",
        "deprecated": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def enqueue_playlist_sync(
    playlist_id: int, user_id: int, priority: str = "normal"
) -> Dict[str, Any]:
    """
    DEPRECATED: Queue system removed - playlist sync is now immediate.

    Args:
        playlist_id (int): ID of the playlist (parameter kept for compatibility)
        user_id (int): ID of the user (parameter kept for compatibility)
        priority (str): Job priority (ignored - parameter kept for compatibility)

    Returns:
        Dict containing deprecation notice
    """
    logger.warning(
        f"enqueue_playlist_sync called for playlist {playlist_id} - DEPRECATED: Queue system removed"
    )

    return {
        "job_id": f"deprecated_playlist_sync_{playlist_id}",
        "status": "deprecated",
        "playlist_id": playlist_id,
        "user_id": user_id,
        "priority": priority,
        "message": "Queue system removed. Playlist sync is now immediate.",
        "deprecated": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_sync_status(job_id: Optional[str] = None, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    DEPRECATED: Queue system removed - sync status checking no longer available.

    Args:
        job_id (str, optional): Job ID (parameter kept for compatibility)
        user_id (int, optional): User ID (parameter kept for compatibility)

    Returns:
        Dict containing deprecation notice
    """
    logger.warning(
        f"get_sync_status called for job {job_id}, user {user_id} - DEPRECATED: Queue system removed"
    )

    if job_id:
        return {
            "job_id": job_id,
            "status": "deprecated",
            "message": "Queue system removed. Sync status tracking no longer available.",
            "deprecated": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    else:
        return {
            "user_id": user_id,
            "active_count": 0,
            "completed_count": 0,
            "failed_count": 0,
            "total_jobs": 0,
            "message": "Queue system removed. Sync status tracking no longer available.",
            "deprecated": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def sync_playlist_task(playlist_id: int, user_id: int) -> Dict[str, Any]:
    """
    Background task function for syncing a playlist.

    This function is executed by priority queue workers.

    Args:
        playlist_id (int): ID of the playlist to sync
        user_id (int): ID of the user

    Returns:
        Dict containing sync results
    """
    start_time = datetime.now(timezone.utc)

    try:
        logger.info(f"Starting playlist sync: playlist_id={playlist_id}, user_id={user_id}")

        # Get user and playlist from database
        user = db.session.get(User, user_id)
        playlist = db.session.get(Playlist, playlist_id)

        if not user:
            error_msg = f"User {user_id} not found"
            logger.error(error_msg)
            return {
                "playlist_id": playlist_id,
                "user_id": user_id,
                "status": "failed",
                "error": error_msg,
                "duration": 0,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        if not playlist:
            error_msg = f"Playlist {playlist_id} not found"
            logger.error(error_msg)
            return {
                "playlist_id": playlist_id,
                "user_id": user_id,
                "status": "failed",
                "error": error_msg,
                "duration": 0,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

        # Use the sync service to perform the actual sync
        sync_service = PlaylistSyncService()
        result = sync_service.sync_playlist_tracks(user, playlist)

        # Calculate duration
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Format result for task response
        task_result = {
            "playlist_id": playlist_id,
            "user_id": user_id,
            "status": result.get("status", "completed"),
            "tracks_synced": result.get("tracks_synced", 0),
            "new_tracks": result.get("new_tracks", 0),
            "updated_tracks": result.get("updated_tracks", 0),
            "errors": result.get("errors", []),
            "duration": duration,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"Playlist sync completed: {task_result}")
        return task_result

    except Exception as e:
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.error(f"Error in playlist sync task: {e}")
        return {
            "playlist_id": playlist_id,
            "user_id": user_id,
            "status": "failed",
            "error": str(e),
            "duration": duration,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
