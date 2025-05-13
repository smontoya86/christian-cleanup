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
from sqlalchemy.exc import SQLAlchemyError
import logging

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
            # Consider raising an exception or returning an error state
            # raise Exception("Spotify client not initialized") 
            return [] # Return empty list for now

        self.logger.info(f"Starting playlist sync for user_id: {user_id}")
        
        # --- Fetch ALL User Playlists with Pagination --- 
        all_playlist_items = []
        offset = 0
        limit = 50 # Max limit for current_user_playlists
        while True:
            self.logger.debug(f"Fetching user playlists for user {user_id}, offset {offset}, limit {limit}")
            try:
                playlists_response = self.sp.current_user_playlists(limit=limit, offset=offset)
                if not playlists_response or 'items' not in playlists_response:
                    self.logger.warning(f"No items found or error fetching playlists for user {user_id} at offset {offset}")
                    break
                
                items = playlists_response.get('items', [])
                all_playlist_items.extend(items)

                if playlists_response.get('next'):
                    offset += limit
                else:
                    break # No more pages
            except spotipy.SpotifyException as e:
                self.logger.error(f"Spotify API error fetching user playlists page (offset {offset}) for user {user_id}: {e}")
                if e.http_status == 401:
                    raise # Re-raise auth errors to be caught by the route
                else:
                    raise # Re-raise other Spotify API errors to be caught by the calling route

        self.logger.info(f"Fetched {len(all_playlist_items)} total playlists for user {user_id}.")

        user_playlists_display_data = [] # Data to pass back
        synced_playlist_ids = set() # Keep track of playlists processed

        # Now iterate through the fetched items
        for item in all_playlist_items:
            spotify_id = item.get('id')
            snapshot_id = item.get('snapshot_id')
            
            # Basic check for essential data
            if not spotify_id or not snapshot_id or not item.get('name'):
                self.logger.warning(f"Skipping playlist item due to missing id, snapshot_id, or name: {item}")
                continue
                
            synced_playlist_ids.add(spotify_id)

            playlist_in_db = Playlist.query.filter_by(spotify_id=spotify_id, owner_id=user_id).first()
            needs_track_sync = False

            # Extract image URL (common for new and existing)
            playlist_image_url = None
            if item.get('images') and len(item['images']) > 0 and item['images'][0].get('url'):
                playlist_image_url = item['images'][0]['url']

            if not playlist_in_db:
                self.logger.info(f"Playlist '{item['name']}' (ID: {spotify_id}) not found in DB for user {user_id}. Creating...")
                playlist_in_db = Playlist(
                    spotify_id=spotify_id,
                    name=item['name'],
                    owner_id=user_id,
                    description=item.get('description', ''),
                    spotify_snapshot_id=snapshot_id, # Store initial snapshot_id
                    image_url=playlist_image_url
                )
                db.session.add(playlist_in_db)
                needs_track_sync = True # New playlist needs initial track sync
            else:
                # Existing playlist, check snapshot_id
                playlist_in_db.image_url = playlist_image_url # Always update image URL if available
                if playlist_in_db.spotify_snapshot_id != snapshot_id:
                    self.logger.info(f"Snapshot ID changed for playlist '{item['name']}' (ID: {spotify_id}, User: {user_id}). Re-syncing tracks.")
                    needs_track_sync = True
                    playlist_in_db.spotify_snapshot_id = snapshot_id
                    playlist_in_db.name = item['name'] 
                    playlist_in_db.description = item.get('description', '')
                else:
                    playlist_in_db.name = item['name'] # Still update non-content metadata
                    playlist_in_db.description = item.get('description', '')
                    self.logger.debug(f"Snapshot ID matches for playlist '{item['name']}' (ID: {spotify_id}, User: {user_id}). Skipping full track sync.")

            # --- Track Syncing Logic ---
            if needs_track_sync:
                self.logger.info(f"Starting track sync for playlist '{playlist_in_db.name}' (ID: {spotify_id}, User: {user_id}).")
                db.session.flush() # Assign ID if new
                
                PlaylistSong.query.filter_by(playlist_id=playlist_in_db.id).delete()
                db.session.flush()

                current_position = 0
                offset = 0
                limit = 100
                while True:
                    self.logger.debug(f"Fetching tracks for {spotify_id}, User: {user_id}, offset {offset}")
                    fields = 'items(track(id,name,artists(id,name),album(id,name),explicit),added_at,added_by(id)),next,limit,offset,total'
                    # Use the internal self.sp client
                    tracks_response = self.sp.playlist_items(
                        spotify_id, 
                        fields=fields, 
                        limit=limit, 
                        offset=offset,
                        additional_types=('track',)
                    )

                    if not tracks_response or 'items' not in tracks_response:
                        self.logger.warning(f"No items found or error fetching tracks for {spotify_id}, User: {user_id} at offset {offset}")
                        break

                    for track_item in tracks_response.get('items', []):
                        track_info = track_item.get('track')
                        if not track_info or not track_info.get('id'):
                            self.logger.warning(f"Skipping item without track info or track ID in playlist {spotify_id}, User: {user_id}")
                            continue

                        spotify_track_id = track_info['id']
                        song_in_db = Song.query.filter_by(spotify_id=spotify_track_id).first()
                        if not song_in_db:
                            song_in_db = Song(
                                spotify_id=spotify_track_id,
                                title=track_info.get('name', 'Unknown Track'), # Changed 'name' to 'title'
                                artist=', '.join([a['name'] for a in track_info.get('artists', []) if a.get('name')]), # Changed 'artist_name' to 'artist'
                                album=track_info.get('album', {}).get('name', 'Unknown Album') # Changed 'album_name' to 'album'
                            )
                            db.session.add(song_in_db)
                            db.session.flush() # Get song_in_db.id

                        added_at_ts = None
                        if track_item.get('added_at'):
                            try:
                                added_at_ts = parser.isoparse(track_item['added_at'])
                            except (ValueError, TypeError) as e:
                                self.logger.warning(f"Could not parse added_at timestamp '{track_item['added_at']}': {e}")

                        added_by_id = track_item.get('added_by', {}).get('id')

                        assoc = PlaylistSong(
                            playlist_id=playlist_in_db.id,
                            song_id=song_in_db.id,
                            track_position=current_position,
                            added_at_spotify=added_at_ts,
                            added_by_spotify_user_id=added_by_id
                        )
                        db.session.add(assoc)
                        current_position += 1

                    if tracks_response.get('next'):
                        offset += limit
                    else:
                        break
                self.logger.info(f"Finished track sync for playlist '{playlist_in_db.name}'. User: {user_id}. Synced {current_position} tracks.")

            # --- Prepare data for template ---
            is_whitelisted = Whitelist.query.filter_by(user_id=user_id, spotify_id=playlist_in_db.spotify_id, item_type='playlist').first() is not None
            is_blacklisted = Blacklist.query.filter_by(user_id=user_id, spotify_id=playlist_in_db.spotify_id, item_type='playlist').first() is not None
            image_url = item['images'][0]['url'] if item.get('images') else None

            user_playlists_display_data.append({
                'id': playlist_in_db.spotify_id,
                'name': playlist_in_db.name,
                'image_url': image_url,
                'track_count': item.get('tracks', {}).get('total', 0), # Safely access track count
                'score': playlist_in_db.overall_alignment_score,
                'is_whitelisted': is_whitelisted,
                'is_blacklisted': is_blacklisted,
                'snapshot_id': playlist_in_db.spotify_snapshot_id
            })

        try:
            db.session.commit()
            self.logger.info(f"Committed playlist changes to DB for user {user_id}.")
        except SQLAlchemyError as e:
            db.session.rollback()
            self.logger.error(f"Database error committing playlist changes for user {user_id}: {e}")
            # Decide if we should raise an error or return potentially stale/incomplete data
            # For now, let's re-raise to make the caller aware of the commit failure.
            raise
        except Exception as e: # Catch any other unexpected error during commit
            db.session.rollback()
            self.logger.error(f"Unexpected error committing playlist changes for user {user_id}: {e}")
            raise

        return user_playlists_display_data

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
            self.logger.info(f"Attempting to remove {len(items_to_remove)} tracks from playlist {spotify_playlist_id} for user {user.id}.")
            sp.playlist_remove_specific_occurrences_of_items(playlist_id=spotify_playlist_id, items=items_to_remove)
            self.logger.info(f"Successfully processed track removal for playlist {spotify_playlist_id} for user {user.id}.")
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

    # Add more methods as needed, e.g.:
    # def get_track_details(self, track_id):
    #     ...
