from flask import current_app, flash
from sqlalchemy.exc import SQLAlchemyError

from .. import db
from ..models import User, Playlist, Song, PlaylistSong
from .spotify_service import SpotifyService
from datetime import datetime

class ListManagementService:
    def __init__(self, spotify_service: SpotifyService):
        if not isinstance(spotify_service, SpotifyService):
            current_app.logger.warning(
                f"ListManagementService initialized with spotify_service of type {type(spotify_service)}, expected SpotifyService."
            )
        self.spotify_service = spotify_service

    def _extract_spotify_track_id(self, track_uri):
        parts = track_uri.split(':')
        if len(parts) == 3 and parts[0] == 'spotify' and parts[1] == 'track':
            return parts[2]
        current_app.logger.warning(f"Could not extract track ID from URI: {track_uri}")
        return None

    def _ensure_songs_exist_in_db(self, user: User, track_uris_to_ensure: list):
        """
        Ensures all songs for the given URIs exist in the local DB.
        Fetches details for new songs from Spotify and creates them.
        Returns a dictionary mapping spotify_track_id to Song object.
        """
        if not track_uris_to_ensure:
            return {}

        song_map = {}
        uris_to_fetch_details_for = []

        for uri in track_uris_to_ensure:
            spotify_track_id = self._extract_spotify_track_id(uri)
            if not spotify_track_id:
                continue 
            
            # Check if song exists in DB
            # The variable name is spotify_track_id, but the keyword arg must match the model field 'spotify_id'
            song = Song.query.filter_by(spotify_id=spotify_track_id).first()

            if not song:
                # If song doesn't exist, fetch details from Spotify and create it
                if uri not in uris_to_fetch_details_for:
                    uris_to_fetch_details_for.append(uri)
            else:
                song_map[spotify_track_id] = song
        
        if not uris_to_fetch_details_for:
            return song_map

        new_songs_created_count = 0
        batch_size = 50 
        for i in range(0, len(uris_to_fetch_details_for), batch_size):
            batch_uris = uris_to_fetch_details_for[i:i + batch_size]
            current_app.logger.info(f"Fetching details for batch of {len(batch_uris)} new songs from Spotify.")
            track_details_list = self.spotify_service.get_multiple_track_details(user, batch_uris)

            if track_details_list:
                for detail in track_details_list:
                    if not detail: continue
                    spotify_id = detail.get('id')
                    if not spotify_id: continue

                    # Redundant check removed: We already know the song wasn't found in the first loop.
                    # song = Song.query.filter_by(spotify_id=spotify_id).first()
                    # if not song:
                    
                    # If we are here, it means the song wasn't found in the first pass.
                    artist_names = ", ".join([artist['name'] for artist in detail.get('artists', [])])
                    album_art_url = None # Not currently stored in Song model
                    if detail.get('album', {}).get('images'):
                        album_art_url = detail['album']['images'][0]['url']

                    # Assume song does not exist and create it.
                    # If it somehow got created between the check and now (race condition),
                    # the unique constraint on spotify_id would cause commit to fail later,
                    # which is acceptable behavior.
                    song = Song(
                        spotify_id=spotify_id,
                        title=detail.get('name'),
                        artist=artist_names,
                        album=detail.get('album', {}).get('name'),
                        album_art_url=album_art_url # Populate the new field
                    )
                    db.session.add(song)
                    new_songs_created_count += 1
                    song_map[spotify_id] = song # Add the newly created song to the map

        if new_songs_created_count > 0:
            current_app.logger.info(f"Added {new_songs_created_count} new songs to the session. Commit will occur in calling function.")

        return song_map

    def update_playlist_and_sync_to_spotify(self, user: User, local_playlist_id: int, new_track_uris_ordered: list, expected_snapshot_id: str):
        """
        Updates a playlist in the local database and syncs the changes to Spotify
        using playlist_replace_items.

        Args:
            user (User): The user performing the update.
            local_playlist_id (int): The ID of the playlist in the local database.
            new_track_uris_ordered (list): The list of Spotify track URIs to set.
            expected_snapshot_id (str): The snapshot_id the client expects the playlist to have.
                                         Used for conflict detection.

        Returns:
            tuple: (bool, str, int) indicating (success, message, http_status_code)
        """
        playlist = db.session.get(Playlist, local_playlist_id)
        if not playlist:
            current_app.logger.warning(f"Attempt to update non-existent local playlist with ID {local_playlist_id} by user {user.id}")
            return False, "Playlist not found.", 404

        if playlist.owner_id != user.id:
            current_app.logger.warning(f"User {user.id} attempted to modify playlist {local_playlist_id} owned by {playlist.owner_id}.")
            return False, "You do not have permission to modify this playlist.", 403

        # --- Conflict Detection --- 
        current_app.logger.info(f"Checking for conflicts for Spotify playlist {playlist.spotify_id} before update.")
        playlist_details = self.spotify_service.get_playlist_details(user, playlist.spotify_id)
        
        if not playlist_details:
            current_app.logger.error(f"Could not fetch current details for Spotify playlist {playlist.spotify_id} to check snapshot_id.")
            return False, "Could not verify playlist status on Spotify. Update cancelled.", 500

        current_snapshot_id = playlist_details.get('snapshot_id')
        if not current_snapshot_id:
             current_app.logger.error(f"Could not get current snapshot_id for Spotify playlist {playlist.spotify_id}.")
             return False, "Could not verify playlist status on Spotify. Update cancelled.", 500

        if current_snapshot_id != expected_snapshot_id:
            conflict_msg = (
                f"Playlist has been updated on Spotify since you loaded it. "
                f"Expected: {expected_snapshot_id}, Current: {current_snapshot_id}. Please refresh and try again."
            )
            current_app.logger.warning(
                f"Conflict detected for playlist {playlist.spotify_id}! "
                f"Expected snapshot_id: {expected_snapshot_id}, Current: {current_snapshot_id}. Update cancelled."
            )
            return False, "Playlist has been updated on Spotify since you loaded it. Please refresh and try again.", 409
        # --- End Conflict Detection ---

        current_app.logger.info(f"Attempting to replace Spotify playlist {playlist.spotify_id} for user {user.id}. Snapshot ID matches ({current_snapshot_id}).")
        new_spotify_snapshot_id = self.spotify_service.replace_playlist_tracks(
            user, playlist.spotify_id, new_track_uris_ordered
        )

        if not new_spotify_snapshot_id:
            current_app.logger.error(f"Failed to replace tracks on Spotify for playlist {playlist.spotify_id}.")
            return False, "Failed to update playlist on Spotify. Please try again.", 500
        
        current_app.logger.info(f"Spotify playlist {playlist.spotify_id} updated. New snapshot_id: {new_spotify_snapshot_id}")

        current_app.logger.info(f"Ensuring songs for playlist {local_playlist_id} exist in local DB.")
        song_map_by_spotify_id = self._ensure_songs_exist_in_db(user, new_track_uris_ordered)
        if not song_map_by_spotify_id and new_track_uris_ordered:
             current_app.logger.error(f"Failed to ensure songs in DB for playlist {local_playlist_id}.")
             return False, "Failed to update song details in the local database. Playlist may be out of sync.", 500

        try:
            PlaylistSong.query.filter_by(playlist_id=local_playlist_id).delete()
            current_app.logger.debug(f"Cleared existing tracks for local playlist {local_playlist_id}.")

            for idx, track_uri in enumerate(new_track_uris_ordered):
                spotify_track_id = self._extract_spotify_track_id(track_uri)
                if not spotify_track_id:
                    current_app.logger.warning(f"Skipping invalid URI {track_uri} during local playlist update.")
                    continue
                
                song_object = song_map_by_spotify_id.get(spotify_track_id)
                if song_object and song_object.id:
                    assoc = PlaylistSong(
                        playlist_id=local_playlist_id,
                        song_id=song_object.id,
                        track_position=idx
                    )
                    db.session.add(assoc)
                else:
                    current_app.logger.error(f"Song with spotify_track_id {spotify_track_id} not found in local DB after sync. URI: {track_uri}. Skipping association.")

            playlist.spotify_snapshot_id = new_spotify_snapshot_id
            playlist.last_synced_from_spotify = datetime.utcnow() # Tracks when the playlist tracks were last successfully synced FROM Spotify's perspective
            playlist.updated_at = datetime.utcnow() # Explicitly set updated_at for the local playlist record
            db.session.commit()
            current_app.logger.info(f"Local playlist {local_playlist_id} updated successfully, snapshot ID: {new_spotify_snapshot_id}.")
            return True, "Playlist updated successfully.", 200

        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.error(f"Database error updating local playlist {local_playlist_id}: {e}", exc_info=True)
            return False, "Database error during playlist update.", 500
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error updating playlist {local_playlist_id}: {e}", exc_info=True)
            # Consider if a more specific error/status code is needed depending on the exception type
            return False, "An unexpected error occurred during playlist update.", 500