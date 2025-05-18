"""
Service layer for interacting with the Spotify API.
"""
import spotipy
from flask import current_app, session, url_for, flash, redirect
from flask_login import current_user
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timedelta
from dateutil import parser # Added for timestamp parsing

# Added imports for DB interaction
from .. import db
from ..models import User, Playlist, Song, PlaylistSong, Whitelist, Blacklist
from .analysis_service import perform_christian_song_analysis_and_store # Added import
from sqlalchemy.exc import SQLAlchemyError
import logging
import requests

SPOTIFY_API_URL = 'https://api.spotify.com/v1'

class SpotifyService:

    def __init__(self, auth_token=None, logger=None):
        """
        Initializes the SpotifyService.
        If auth_token is provided, it uses it. Otherwise, attempts to use current_user's token.
        Requires a logger instance to be passed.
        """
        self.logger = logger or logging.getLogger(__name__) # Fallback if logger not provided

        if auth_token:
            self.sp = spotipy.Spotify(auth=auth_token)
        elif hasattr(current_user, 'access_token') and current_user.access_token:
            # Defer Spotipy client creation until needed by a method, 
            # as current_user might not be available during __init__
            self.sp = None 
            self.logger.debug("SpotifyService initialized, will use current_user token when needed.")
        else:
            self.logger.warning("SpotifyService initialized without specific auth token and no current_user context yet.")
            self.sp = None

    def _parse_spotify_datetime(self, datetime_str):
        """Helper method to parse datetime strings from Spotify (ISO 8601 format)."""
        if not datetime_str:
            return None
        try:
            # dateutil.parser.isoparse is robust and handles 'Z' for UTC
            return parser.isoparse(datetime_str)
        except ValueError as e:
            self.logger.error(f"Error parsing datetime string '{datetime_str}': {e}")
            return None
        except TypeError as e: # Handle if datetime_str is not a string
            self.logger.error(f"Invalid type for datetime parsing (expected string): '{datetime_str}': {e}")
            return None

    def get_user_profile(self):
        if not self.sp:
            self.logger.error("Spotify client not initialized in get_user_profile")
            return None
        try:
            return self.sp.current_user()
        except spotipy.SpotifyException as e:
            self.logger.error(f"Spotify API error fetching user profile: {e}")
            return None

    def get_user_playlists(self, limit=20, offset=0):
        if not self.sp:
            self.logger.error("Spotify client not initialized in get_user_playlists")
            return None
        try:
            return self.sp.current_user_playlists(limit=limit, offset=offset)
        except spotipy.SpotifyException as e:
            self.logger.error(f"Spotify API error fetching user playlists: {e}")
            return None

    def get_playlist_items(self, playlist_id, fields=None, limit=100, offset=0):
        if not self.sp:
            self.logger.error("Spotify client not initialized in get_playlist_items")
            return None
        try:
            return self.sp.playlist_items(playlist_id, fields=fields, limit=limit, offset=offset)
        except spotipy.SpotifyException as e:
            self.logger.error(f"Spotify API error fetching playlist items for {playlist_id}: {e}")
            return None

    def get_playlist_details(self, user, spotify_playlist_id):
        """Fetches details for a specific playlist from Spotify."""
        if not user or not hasattr(user, 'access_token'):
            self.logger.error("Invalid user object provided to get_playlist_details.")
            return None

        if not user.ensure_token_valid():
            self.logger.error(f"Spotify token for user {user.id} is invalid or could not be refreshed.")
            return None

        sp = spotipy.Spotify(auth=user.access_token)

        try:
            self.logger.info(f"Fetching details for playlist {spotify_playlist_id} for user {user.id}.")
            # Request specific fields to minimize data transfer if needed, e.g., 'id,name,snapshot_id'
            playlist_info = sp.playlist(spotify_playlist_id, fields='snapshot_id,id,name') 
            return playlist_info
        except spotipy.SpotifyException as e:
            self.logger.error(
                f"Spotify API error fetching details for playlist {spotify_playlist_id} for user {user.id}: {e}"
            )
            # Handle specific errors like 404 Not Found if necessary
            if e.http_status == 404:
                self.logger.warning(f"Playlist {spotify_playlist_id} not found on Spotify for user {user.id}.")
            return None
        except Exception as e:
            self.logger.error(
                f"Unexpected error fetching details for playlist {spotify_playlist_id} for user {user.id}: {e}"
            )
            return None

    def sync_user_playlists_with_db(self, user_id):
        """
        Fetches user playlists from Spotify, compares with local DB based on snapshot_id,
        and syncs tracks (including position, added_at, added_by) for new or changed playlists.
        Returns a list of playlist data suitable for display.
        Raises exceptions on critical Spotify errors (e.g., auth issues).
        """
        if not self.sp:
            self.logger.error(f"Spotify client not initialized for user {user_id} in sync_user_playlists_with_db")
            return []

        self.logger.info(f"Starting playlist sync for user_id: {user_id}")
        
        all_playlist_items = []
        offset = 0
        limit = 50
        try:
            while True:
                self.logger.debug(f"Fetching user playlists page for user {user_id}, offset {offset}, limit {limit}")
                playlists_response = self.sp.current_user_playlists(limit=limit, offset=offset)
                if not playlists_response or 'items' not in playlists_response:
                    self.logger.warning(f"No items found or malformed response fetching playlists for user {user_id} at offset {offset}")
                    break
                
                items = playlists_response.get('items', [])
                all_playlist_items.extend(items)
                self.logger.debug(f"Fetched {len(items)} playlist items in this page. Total fetched so far: {len(all_playlist_items)}.")

                if playlists_response.get('next'):
                    offset += limit
                else:
                    break
        except spotipy.SpotifyException as e:
            self.logger.error(f"Spotify API error during bulk playlist fetch for user {user_id} (offset {offset}): {e}")
            if e.http_status == 401:
                self.logger.error("Spotify API auth error (401). Re-raising to be handled by route.")
                raise
            # For other Spotify errors during bulk fetch, we might not be able to continue meaningfully.
            # Depending on the error, we might return [] or re-raise.
            # For now, let's re-raise to make the issue visible at the route level.
            raise 
        except Exception as e_bulk_fetch:
            self.logger.error(f"Unexpected error during bulk playlist fetch for user {user_id} (offset {offset}): {e_bulk_fetch}")
            raise # Re-raise to make it visible

        self.logger.info(f"Successfully fetched {len(all_playlist_items)} total playlist headers for user {user_id}.")

        user_playlists_display_data = []
        successfully_processed_count = 0
        error_processing_count = 0
        songs_successfully_added_to_db = 0
        songs_failed_to_add_or_find = 0
        songs_skipped = 0

        for index, item in enumerate(all_playlist_items):
            spotify_id = item.get('id')
            playlist_name_for_logging = item.get('name', '[Unnamed Playlist]')
            self.logger.info(f"Processing playlist {index + 1}/{len(all_playlist_items)}: '{playlist_name_for_logging}' (Spotify ID: {spotify_id}) for user {user_id}")

            try:
                snapshot_id = item.get('snapshot_id')
                if not spotify_id or not snapshot_id:
                    self.logger.warning(f"Skipping playlist item due to missing id or snapshot_id: {item.get('name', 'N/A')}")
                    error_processing_count += 1
                    continue
                
                playlist_in_db = Playlist.query.filter_by(spotify_id=spotify_id, owner_id=user_id).first()
                needs_track_sync = False
                is_new_playlist = False

                playlist_image_url = None
                if item.get('images') and len(item['images']) > 0 and item['images'][0].get('url'):
                    playlist_image_url = item['images'][0]['url']

                if not playlist_in_db:
                    self.logger.info(f"Playlist '{playlist_name_for_logging}' (ID: {spotify_id}) not in DB. Creating.")
                    playlist_in_db = Playlist(
                        spotify_id=spotify_id,
                        name=item['name'],
                        owner_id=user_id,
                        description=item.get('description', ''),
                        spotify_snapshot_id=snapshot_id,
                        image_url=playlist_image_url,
                        last_synced_from_spotify=datetime.utcnow() # Set initial sync time
                    )
                    db.session.add(playlist_in_db)
                    needs_track_sync = True
                    is_new_playlist = True
                    db.session.flush() # Get ID for new playlist if needed for tracks
                else:
                    playlist_in_db.name = item['name'] # Always update name
                    playlist_in_db.description = item.get('description', '') # Always update description
                    playlist_in_db.image_url = playlist_image_url # Always update image
                    if playlist_in_db.spotify_snapshot_id != snapshot_id:
                        self.logger.info(f"Snapshot ID changed for playlist '{playlist_name_for_logging}' (ID: {spotify_id}). Old: {playlist_in_db.spotify_snapshot_id}, New: {snapshot_id}. Re-syncing tracks.")
                        needs_track_sync = True
                        playlist_in_db.spotify_snapshot_id = snapshot_id
                    else:
                        self.logger.debug(f"Snapshot ID matches for playlist '{playlist_name_for_logging}'. Skipping full track sync. Metadata updated.")
                    playlist_in_db.last_synced_from_spotify = datetime.utcnow() # Update sync time

                if needs_track_sync:
                    self.logger.info(f"Starting track sync for playlist '{playlist_name_for_logging}' (DB ID: {playlist_in_db.id}).")
                    
                    # Delete existing tracks for this playlist
                    num_deleted = PlaylistSong.query.filter_by(playlist_id=playlist_in_db.id).delete()
                    if num_deleted > 0:
                        self.logger.info(f"Deleted {num_deleted} existing track entries for playlist '{playlist_name_for_logging}'.")
                    db.session.flush() # Apply deletions before adding new ones

                    current_position = 0
                    tracks_offset = 0
                    tracks_limit = 100 # Max limit for playlist_items is 100
                    total_tracks_in_playlist_spotify = item.get('tracks', {}).get('total', 0)
                    self.logger.debug(f"Playlist '{playlist_name_for_logging}' reports {total_tracks_in_playlist_spotify} tracks on Spotify.")
                    
                    processed_tracks_count_for_this_playlist = 0
                    while True:
                        self.logger.debug(f"Fetching tracks for playlist '{playlist_name_for_logging}' (Spotify ID: {spotify_id}), offset {tracks_offset}, limit {tracks_limit}")
                        try:
                            # Explicitly request all necessary fields
                            fields_to_request = "items(added_at,added_by.id,track(id,name,artists(name),album(name,release_date,images),duration_ms,explicit,is_local,uri)),next,total"
                            tracks_response = self.sp.playlist_items(spotify_id, limit=tracks_limit, offset=tracks_offset, fields=fields_to_request)
                        except spotipy.SpotifyException as spe_tracks:
                            self.logger.error(f"Spotify API error fetching tracks for playlist '{playlist_name_for_logging}' (ID: {spotify_id}) at offset {tracks_offset}: {spe_tracks}")
                            if spe_tracks.http_status == 401:
                                self.logger.error(f"Spotify API auth error (401) during track fetch for {playlist_name_for_logging}. Re-raising.")
                                raise # Critical auth error, stop everything
                            # For other errors (e.g., 404, 500s for specific playlist tracks), log and break this inner track loop.
                            self.logger.warning(f"Skipping further track fetching for '{playlist_name_for_logging}' due to API error.")
                            break # Break from while True for fetching tracks of THIS playlist
                        except Exception as e_tracks_fetch:
                            self.logger.error(f"Unexpected error fetching tracks for playlist '{playlist_name_for_logging}' (ID: {spotify_id}) at offset {tracks_offset}: {e_tracks_fetch}")
                            self.logger.warning(f"Skipping further track fetching for '{playlist_name_for_logging}' due to unexpected error.")
                            break # Break from while True

                        if not tracks_response or 'items' not in tracks_response:
                            self.logger.warning(f"No items in track response or malformed response for playlist '{playlist_name_for_logging}' at offset {tracks_offset}. Stopping track sync for this playlist.")
                            break

                        track_items = tracks_response.get('items', [])
                        if not track_items and tracks_offset == 0:
                             self.logger.info(f"Playlist '{playlist_name_for_logging}' is empty on Spotify or no tracks returned.")
                             # No tracks to add or remove, ensure local is also empty if it wasn't before (already handled by delete)

                        for track_item_data in track_items:
                            if not track_item_data or not track_item_data.get('track'):
                                self.logger.warning(f"Skipping track item due to missing track data in playlist '{playlist_name_for_logging}'. Data: {track_item_data}")
                                continue
                            
                            track_details = track_item_data['track']
                            if not track_details.get('id') or track_details.get('is_local'):
                                self.logger.info(f"Skipping local or ID-less track '{track_details.get('name', 'N/A')}' in playlist '{playlist_name_for_logging}'.")
                                songs_skipped += 1
                                continue # Skip track if essential details are missing

                            song_spotify_id = track_details['id']
                            song = Song.query.filter_by(spotify_id=song_spotify_id).first()

                            if not song:
                                self.logger.debug(f"Song with Spotify ID {song_spotify_id} not found in DB. Creating new song: {track_details.get('name', 'N/A')}.")
                                song_album_art_url = None
                                if track_details.get('album') and track_details['album'].get('images') and len(track_details['album']['images']) > 0:
                                    song_album_art_url = track_details['album']['images'][0]['url']
                                
                                try:
                                    song = Song(
                                        spotify_id=song_spotify_id,
                                        title=track_details['name'],
                                        artist=track_details['artists'][0]['name'] if track_details.get('artists') else 'Unknown Artist',
                                        album=track_details.get('album', {}).get('name'),
                                        explicit=track_details.get('explicit', False),
                                        album_art_url=song_album_art_url
                                    )
                                    db.session.add(song)
                                    db.session.flush() # Assigns ID to song object if new
                                    self.logger.info(f"Successfully created new song: {song.title} (ID: {song.id}) with Spotify ID {song.spotify_id}")
                                    # Enqueue analysis for the new song
                                    analysis_job = perform_christian_song_analysis_and_store(song.id)
                                    if analysis_job:
                                        self.logger.info(f"Analysis task for new song '{song.title}' (ID: {song.id}) enqueued. Job ID: {analysis_job.id}")
                                    else:
                                        self.logger.error(f"Failed to enqueue analysis task for new song '{song.title}' (ID: {song.id}).")
                                    songs_successfully_added_to_db += 1
                                except Exception as e_song_create:
                                    self.logger.error(f"Error creating song {track_details['name']} (Spotify ID: {song_spotify_id}): {e_song_create}")
                                    db.session.rollback()
                                    songs_failed_to_add_or_find += 1
                                    continue # Skip to next track
                            else:
                                self.logger.debug(f"Found existing song in DB: {song.title} (ID: {song.id}) with Spotify ID {song.spotify_id}")
                                # Potentially update existing song details if necessary
                                new_album_art_url = None
                                if track_details.get('album') and track_details['album'].get('images') and len(track_details['album']['images']) > 0:
                                    new_album_art_url = track_details['album']['images'][0]['url']
                                
                                updated_existing_song = False
                                if new_album_art_url and song.album_art_url != new_album_art_url:
                                    song.album_art_url = new_album_art_url
                                    updated_existing_song = True
                                if song.title != track_details['name']:
                                    song.title = track_details['name']
                                    updated_existing_song = True
                                current_artist_name_from_spotify = track_details['artists'][0]['name'] if track_details.get('artists') else 'Unknown Artist'
                                if song.artist != current_artist_name_from_spotify:
                                    song.artist = current_artist_name_from_spotify
                                    updated_existing_song = True
                                current_album_name_from_spotify = track_details.get('album', {}).get('name')
                                if song.album != current_album_name_from_spotify:
                                    song.album = current_album_name_from_spotify
                                    updated_existing_song = True
                                if song.explicit != track_details.get('explicit', False):
                                    song.explicit = track_details.get('explicit', False)
                                    updated_existing_song = True
                                
                                if updated_existing_song:
                                    self.logger.info(f"Updating details for existing song '{song.title}' (ID: {song.id})")
                                    try:
                                        # db.session.add(song) # Not strictly necessary if song is already in session and modified
                                        db.session.commit() # Commit update for existing song
                                        self.logger.info(f"Successfully updated existing song: '{song.title}' (ID: {song.id})")
                                    except Exception as e_song_update:
                                        self.logger.error(f"Error updating existing song '{song.title}' (ID: {song.id}): {e_song_update}")
                                        db.session.rollback()

                            # Ensure song object is valid before proceeding
                            if not song or not song.id:
                                self.logger.error(f"Song object is invalid or has no ID after find/create for Spotify ID {song_spotify_id}. Skipping PlaylistSong creation.")
                                songs_failed_to_add_or_find += 1
                                continue
                            # Check if this song is already in the playlist
                            existing_assoc = PlaylistSong.query.filter_by(
                                playlist_id=playlist_in_db.id,
                                song_id=song.id
                            ).first()
                            
                            if not existing_assoc:
                                # Create new association if it doesn't exist
                                playlist_song = PlaylistSong(
                                    playlist_id=playlist_in_db.id,
                                    song_id=song.id,
                                    track_position=current_position,
                                    added_at_spotify=self._parse_spotify_datetime(track_item_data.get('added_at')),
                                    added_by_spotify_user_id=track_item_data.get('added_by', {}).get('id')
                                )
                                db.session.add(playlist_song)
                                current_position += 1
                                processed_tracks_count_for_this_playlist += 1
                            else:
                                # Update existing association if needed
                                if (existing_assoc.track_position != current_position or
                                    existing_assoc.added_at_spotify != self._parse_spotify_datetime(track_item_data.get('added_at')) or
                                    existing_assoc.added_by_spotify_user_id != track_item_data.get('added_by', {}).get('id')):
                                    
                                    existing_assoc.track_position = current_position
                                    existing_assoc.added_at_spotify = self._parse_spotify_datetime(track_item_data.get('added_at'))
                                    existing_assoc.added_by_spotify_user_id = track_item_data.get('added_by', {}).get('id')
                                    db.session.add(existing_assoc)
                                    self.logger.debug(f"Updated existing playlist_song association for playlist {playlist_in_db.id}, song {song.id}")
                                current_position += 1
                                processed_tracks_count_for_this_playlist += 1
                        
                        self.logger.debug(f"Processed {len(track_items)} tracks from page for '{playlist_name_for_logging}'. Total for this playlist so far: {processed_tracks_count_for_this_playlist}")
                        if tracks_response.get('next'):
                            tracks_offset += tracks_limit
                        else:
                            break # No more tracks for this playlist
                    self.logger.info(f"Finished track sync for playlist '{playlist_name_for_logging}'. Added {processed_tracks_count_for_this_playlist} tracks.")
                
                # Add the playlist object to the list to return
                # The template will access songs through the songs relationship
                user_playlists_display_data.append(playlist_in_db)
                successfully_processed_count += 1

            except spotipy.SpotifyException as spe_playlist_item:
                self.logger.error(f"Spotify API error during processing of playlist '{playlist_name_for_logging}' (Spotify ID: {spotify_id}): {spe_playlist_item}")
                if spe_playlist_item.http_status == 401:
                    self.logger.error(f"Critical Spotify API auth error (401) for playlist '{playlist_name_for_logging}'. Re-raising.")
                    raise # Let the route handler catch this critical error
                error_processing_count += 1
            except Exception as e_playlist_item:
                self.logger.error(f"Unexpected error processing playlist '{playlist_name_for_logging}' (Spotify ID: {spotify_id}): {e_playlist_item}", exc_info=True)
                error_processing_count += 1
        
        self.logger.info(f"Completed processing all {len(all_playlist_items)} fetched playlist items for user {user_id}.")
        self.logger.info(f"Successfully processed: {successfully_processed_count} playlists. Encountered errors for: {error_processing_count} playlists.")
        self.logger.info(f"Song processing stats: Successfully added to DB: {songs_successfully_added_to_db}, Failed to add/find: {songs_failed_to_add_or_find}, Skipped: {songs_skipped}")

        # --- Deactivate playlists no longer returned by Spotify --- 
        # (This part might need its own try-catch or careful placement if db.session.commit() is moved)
        # current_spotify_playlist_ids = {item['id'] for item in all_playlist_items if item.get('id')}
        # playlists_to_deactivate = Playlist.query.filter(
        #     Playlist.owner_id == user_id,
        #     Playlist.is_active == True, # Assuming you have an 'is_active' flag
        #     ~Playlist.spotify_id.in_(current_spotify_playlist_ids)
        # ).all()
        # for p_deactivate in playlists_to_deactivate:
        #     self.logger.info(f"Deactivating playlist '{p_deactivate.name}' (ID: {p_deactivate.spotify_id}) as it's no longer on Spotify for user {user_id}.")
        #     p_deactivate.is_active = False # Or some other deactivation logic
        # db.session.flush() # Apply deactivations

        try:
            db.session.commit()
            self.logger.info(f"Successfully committed all database changes for user {user_id} playlist sync.")
        except Exception as e_commit:
            self.logger.error(f"CRITICAL: Failed to commit database changes after playlist sync for user {user_id}: {e_commit}", exc_info=True)
            db.session.rollback()
            self.logger.info("Database changes rolled back due to commit error.")
            # Depending on severity, might re-raise or return an error indicator to the route
            raise # Re-raise for now, as a failed commit is a significant problem.

        # Refresh the playlists to ensure we have all the latest data
        synced_playlists = (
            db.session.query(Playlist)
            .filter(Playlist.owner_id == user_id)
            .all()
        )
        
        return synced_playlists

    def add_tracks_to_spotify_playlist(self, user, spotify_playlist_id, track_uris):
        """
        Adds tracks to a specified Spotify playlist for a given user.

        Args:
            user (User): The User object for whom to add tracks.
            spotify_playlist_id (str): The ID of the Spotify playlist.
            track_uris (list): A list of Spotify track URIs (e.g., ["spotify:track:xxxx"]).
                               Max 100 URIs per call due to Spotify API limitations.

        Returns:
            bool: True if tracks were added successfully, False otherwise.
        """
        if not user or not hasattr(user, 'access_token'):
            self.logger.error("Invalid user object provided to add_tracks_to_spotify_playlist.")
            return False

        if not spotify_playlist_id:
            self.logger.error("Spotify playlist ID not provided.")
            return False

        if not track_uris:
            self.logger.info("No track URIs provided to add_tracks_to_spotify_playlist. Nothing to add.")
            return True # No action needed, so technically successful

        if len(track_uris) > 100:
            self.logger.warning(
                f"Attempting to add {len(track_uris)} tracks, but Spotify API limit is 100 per call. "
                f"This implementation does not yet handle batching for >100 tracks."
            )
            # For now, we'll proceed but it might fail or only add the first 100.
            # Future enhancement: implement batching.

        if not user.ensure_token_valid():
            self.logger.error(f"Spotify token for user {user.id} is invalid or could not be refreshed.")
            flash("Your Spotify session has expired. Please log in again.", "warning") # Consider if flash is appropriate here
            return False

        sp = spotipy.Spotify(auth=user.access_token)

        try:
            self.logger.info(f"Attempting to add {len(track_uris)} tracks to playlist {spotify_playlist_id} for user {user.id}.")
            sp.playlist_add_items(playlist_id=spotify_playlist_id, items=track_uris)
            self.logger.info(f"Successfully added tracks to playlist {spotify_playlist_id} for user {user.id}.")
            return True
        except spotipy.SpotifyException as e:
            self.logger.error(
                f"Spotify API error adding tracks to playlist {spotify_playlist_id} for user {user.id}: {e}"
            )
            # More specific error handling can be added based on e.status_code
            if e.http_status == 401:
                 flash("Spotify authentication error. Please try logging out and back in.", "danger")
            elif e.http_status == 403:
                 flash("You don't have permission to modify this playlist or required permissions are missing.", "danger")
            elif e.http_status == 404:
                 flash("The Spotify playlist was not found.", "danger")
            else:
                 flash("An error occurred while adding tracks to the Spotify playlist.", "danger")
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error adding tracks to playlist {spotify_playlist_id} for user {user.id}: {e}"
            )
            flash("An unexpected error occurred. Please try again.", "danger")
            return False

    def remove_tracks_from_spotify_playlist(self, user, spotify_playlist_id, track_uris):
        """
        Removes specified tracks from a Spotify playlist for a given user.
        Removes all occurrences of the specified track URIs.

        Args:
            user (User): The User object.
            spotify_playlist_id (str): The ID of the Spotify playlist.
            track_uris (list): A list of Spotify track URIs to remove (e.g., ["spotify:track:xxxx"]).
                               Max 100 URIs per call.

        Returns:
            bool: True if tracks were removed successfully or no tracks needed removal, False otherwise.
        """
        if not user or not hasattr(user, 'access_token'):
            self.logger.error("Invalid user object provided to remove_tracks_from_spotify_playlist.")
            return False

        if not spotify_playlist_id:
            self.logger.error("Spotify playlist ID not provided for track removal.")
            return False

        if not track_uris:
            self.logger.info("No track URIs provided to remove_tracks_from_spotify_playlist. Nothing to remove.")
            return True # No action needed

        if len(track_uris) > 100:
            self.logger.warning(
                f"Attempting to remove {len(track_uris)} tracks, but Spotify API limit is 100 per call. "
                f"This implementation does not yet handle batching for >100 tracks."
            )
            # Future enhancement: implement batching.

        if not user.ensure_token_valid():
            self.logger.error(f"Spotify token for user {user.id} is invalid or could not be refreshed for track removal.")
            flash("Your Spotify session has expired. Please log in again.", "warning")
            return False

        sp = spotipy.Spotify(auth=user.access_token)

        # Prepare items in the format required by playlist_remove_specific_occurrences_of_items
        # Each item is a dict {'uri': track_uri}. We are removing all occurrences.
        items_to_remove = [{'uri': uri} for uri in track_uris]

        try:
            self.logger.info(
                f"Attempting to remove {len(items_to_remove)} tracks from playlist {spotify_playlist_id} for user {user.id}."
            )
            sp.playlist_remove_specific_occurrences_of_items(playlist_id=spotify_playlist_id, items=items_to_remove)
            self.logger.info(
                f"Successfully processed track removal for playlist {spotify_playlist_id} for user {user.id}."
            )
            return True
        except spotipy.SpotifyException as e:
            self.logger.error(
                f"Spotify API error removing tracks from playlist {spotify_playlist_id} for user {user.id}: {e}"
            )
            if e.http_status == 401:
                 flash("Spotify authentication error. Please try logging out and back in.", "danger")
            elif e.http_status == 403:
                 flash("You don't have permission to modify this playlist or required permissions are missing.", "danger")
            elif e.http_status == 404:
                 flash("The Spotify playlist was not found.", "danger")
            else:
                 flash("An error occurred while removing tracks from the Spotify playlist.", "danger")
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error removing tracks from playlist {spotify_playlist_id} for user {user.id}: {e}"
            )
            flash("An unexpected error occurred. Please try again.", "danger")
            return False

    def reorder_tracks_in_spotify_playlist(self, user, spotify_playlist_id, range_start, insert_before, range_length=1, snapshot_id=None):
        """
        Reorders tracks in a specified Spotify playlist for a given user.

        Args:
            user (User): The User object.
            spotify_playlist_id (str): The ID of the Spotify playlist.
            range_start (int): The zero-indexed position of the first track to be reordered.
            insert_before (int): The zero-indexed position where the tracks should be inserted.
            range_length (int, optional): The number of tracks to reorder. Defaults to 1.
            snapshot_id (str, optional): The playlist's snapshot ID.

        Returns:
            str or None: The new snapshot_id if successful, None otherwise.
        """
        if not user or not hasattr(user, 'access_token'):
            self.logger.error("Invalid user object provided to reorder_tracks_in_spotify_playlist.")
            return None

        if not spotify_playlist_id:
            self.logger.error("Spotify playlist ID not provided for track reordering.")
            return None

        if not isinstance(range_start, int) or range_start < 0:
            self.logger.error(f"Invalid range_start: {range_start}. Must be a non-negative integer.")
            return None
        
        if not isinstance(insert_before, int) or insert_before < 0:
            self.logger.error(f"Invalid insert_before: {insert_before}. Must be a non-negative integer.")
            return None

        if not isinstance(range_length, int) or range_length < 1:
            self.logger.error(f"Invalid range_length: {range_length}. Must be a positive integer.")
            return None

        if not user.ensure_token_valid():
            self.logger.error(f"Spotify token for user {user.id} is invalid or could not be refreshed for track reordering.")
            flash("Your Spotify session has expired. Please log in again.", "warning")
            return None

        sp = spotipy.Spotify(auth=user.access_token)

        try:
            self.logger.info(
                f"Attempting to reorder tracks in playlist {spotify_playlist_id} for user {user.id}. "
                f"Range start: {range_start}, Insert before: {insert_before}, Range length: {range_length}."
            )
            result = sp.playlist_reorder_items(
                playlist_id=spotify_playlist_id,
                range_start=range_start,
                insert_before=insert_before,
                range_length=range_length,
                snapshot_id=snapshot_id
            )
            new_snapshot_id = result.get('snapshot_id')
            self.logger.info(
                f"Successfully reordered tracks in playlist {spotify_playlist_id} for user {user.id}. New snapshot_id: {new_snapshot_id}."
            )
            return new_snapshot_id
        except spotipy.SpotifyException as e:
            self.logger.error(
                f"Spotify API error reordering tracks in playlist {spotify_playlist_id} for user {user.id}: {e}"
            )
            if e.http_status == 401:
                 flash("Spotify authentication error. Please try logging out and back in.", "danger")
            elif e.http_status == 403:
                 flash("You don't have permission to modify this playlist or required permissions are missing.", "danger")
            elif e.http_status == 404:
                 flash("The Spotify playlist was not found.", "danger")
            else:
                 flash("An error occurred while reordering tracks in the Spotify playlist.", "danger")
            return None
        except Exception as e:
            self.logger.error(
                f"Unexpected error reordering tracks in playlist {spotify_playlist_id} for user {user.id}: {e}"
            )
            flash("An unexpected error occurred. Please try again.", "danger")
            return None

    def replace_playlist_tracks(self, user, spotify_playlist_id, track_uris):
        """
        Replaces all tracks in a specified Spotify playlist with a new set of tracks.

        Args:
            user (User): The User object.
            spotify_playlist_id (str): The ID of the Spotify playlist.
            track_uris (list): A list of Spotify track URIs for the new playlist content.
                               Max 100 URIs per call.

        Returns:
            str or None: The new snapshot_id if successful, None otherwise.
        """
        if not user or not hasattr(user, 'access_token'):
            self.logger.error("Invalid user object provided to replace_playlist_tracks.")
            return None

        if not spotify_playlist_id:
            self.logger.error("Spotify playlist ID not provided for replacing tracks.")
            return None

        # track_uris can be an empty list to clear the playlist
        if track_uris is None: # Explicitly check for None if empty list is valid
            self.logger.error("Track URIs not provided for replacing tracks.")
            return None
        
        if len(track_uris) > 100:
            self.logger.warning(
                f"Attempting to set {len(track_uris)} tracks, but Spotify API limit for replace_items is 100. "
                f"This may fail or require batching not yet implemented."
            )
            # Note: playlist_replace_items spotipy documentation doesn't explicitly state a limit,
            # but operations on items often have a 100-item limit. Best to be cautious.

        if not user.ensure_token_valid():
            self.logger.error(f"Spotify token for user {user.id} is invalid or could not be refreshed for replacing tracks.")
            # flash("Your Spotify session has expired. Please log in again.", "warning") # Service layer should not flash
            return None

        sp = spotipy.Spotify(auth=user.access_token)

        try:
            self.logger.info(
                f"Attempting to replace tracks in playlist {spotify_playlist_id} with {len(track_uris)} new tracks for user {user.id}."
            )
            sp.playlist_replace_items(playlist_id=spotify_playlist_id, items=track_uris)
            
            # After successful replacement, the snapshot_id changes.
            # We should fetch the updated playlist details to get the new snapshot_id.
            playlist_details = sp.playlist(spotify_playlist_id, fields="snapshot_id")
            new_snapshot_id = playlist_details.get('snapshot_id') if playlist_details else None

            self.logger.info(
                f"Successfully replaced tracks in playlist {spotify_playlist_id} for user {user.id}. New snapshot_id: {new_snapshot_id}."
            )
            return new_snapshot_id
        except spotipy.SpotifyException as e:
            self.logger.error(
                f"Spotify API error replacing tracks in playlist {spotify_playlist_id} for user {user.id}: {e}"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Unexpected error replacing tracks in playlist {spotify_playlist_id} for user {user.id}: {e}"
            )
            return None

    def get_multiple_track_details(self, user, track_uris):
        """
        Fetches details for multiple tracks from Spotify.

        Args:
            user (User): The User object for authentication.
            track_uris (list): A list of Spotify track URIs. Max 50 URIs per call.

        Returns:
            list: A list of track detail objects from Spotify, or None if an error occurs.
        """
        if not user or not hasattr(user, 'access_token'):
            self.logger.error("Invalid user object provided to get_multiple_track_details.")
            return None

        if not track_uris:
            self.logger.info("No track URIs provided to get_multiple_track_details.")
            return []

        # The calling method (_ensure_songs_exist_in_db) handles batching,
        # so this check is redundant here.
        # if len(track_uris) > 50:
        #     self.logger.warning(
        #         f"Attempting to fetch {len(track_uris)} tracks, but Spotify API limit for sp.tracks() is 50. "
        #         f"This implementation does not yet handle batching."
        #     )
        #     # Future enhancement: implement batching if more than 50 tracks need details at once.

        if not user.ensure_token_valid():
            self.logger.error(f"Spotify token for user {user.id} is invalid or could not be refreshed.")
            return None

        sp = spotipy.Spotify(auth=user.access_token)

        try:
            self.logger.info(f"Fetching details for {len(track_uris)} tracks for user {user.id}.")
            results = sp.tracks(tracks=track_uris) # 'tracks' is the keyword argument
            return results.get('tracks') if results else None
        except spotipy.SpotifyException as e:
            self.logger.error(
                f"Spotify API error fetching multiple track details for user {user.id}: {e}"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Unexpected error fetching multiple track details for user {user.id}: {e}"
            )
            return None

    @staticmethod
    def get_auth_manager():
        client_id = current_app.config.get('SPOTIPY_CLIENT_ID')
        client_secret = current_app.config.get('SPOTIPY_CLIENT_SECRET')
        redirect_uri = current_app.config.get('SPOTIPY_REDIRECT_URI')
        scopes = current_app.config.get('SPOTIFY_SCOPES')

        if not all([client_id, client_secret, redirect_uri, scopes]):
            current_app.logger.error("Spotify API credentials, redirect URI, or scopes not configured for auth manager.")
            return None
        
        # Using a session-based cache handler or similar might be better for multi-user app
        # For simplicity, not using a file cache here, but consider Flask session or DB for token storage.
        return SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scopes,
            cache_path=None # Explicitly no file cache, token management should be per user session
        )

    def get_spotify_data(self, endpoint, access_token, params=None):
        headers = {
            'Authorization': f'Bearer {access_token}'
        }
        try:
            response = requests.get(f'{SPOTIFY_API_URL}/{endpoint}', headers=headers, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_message = f'HTTP error occurred: {e}'
            if e.response is not None:
                try:
                    error_details = e.response.json()
                    if isinstance(error_details, dict) and 'error' in error_details and isinstance(error_details['error'], dict) and 'message' in error_details['error']:
                        error_message = error_details['error']['message']
                    elif isinstance(error_details, dict) and 'error_description' in error_details: # Handle OAuth errors which have a different structure
                        error_message = error_details['error_description']
                    else:
                        error_message = f'Spotify API error: {e.response.status_code} - {e.response.text}'
                except ValueError: # If response is not JSON
                    error_message = f'Spotify API error: {e.response.status_code} - {e.response.text}'
        
            if 'The access token expired' in str(error_message) or (e.response is not None and e.response.status_code == 401):
                current_app.logger.error('Spotify access token has expired. Please re-authenticate.')
                # Potentially, you could raise a custom exception here to be caught by the route
                # and trigger a re-authentication flow, or redirect to login.
                # For now, just logging and returning None or raising the original error.
                raise e # Or return None, or a specific error object
            else:
                current_app.logger.error(f'Error fetching data from Spotify: {error_message}')
            raise e # Re-raise the original exception or a custom one
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f'Request exception: {e}')
            raise e

    # Add more methods as needed, e.g.:
    # def get_track_details(self, track_id):
    #     ...
