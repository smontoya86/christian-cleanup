from flask import render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_required, current_user as flask_login_current_user
import spotipy

from .. import db
from ..models import User, Whitelist, Blacklist, Song, AnalysisResult, PlaylistSong, Playlist
from ..services.spotify_service import SpotifyService
from ..services.analysis_service import analyze_playlist_content, get_playlist_analysis_results, perform_christian_song_analysis_and_store # Added import
from app.auth.decorators import spotify_token_required
from app.services.whitelist_service import (
    add_to_whitelist,
    add_to_blacklist,
    remove_from_whitelist,
    remove_from_blacklist,
    ITEM_ADDED as WL_ITEM_ADDED,
    ITEM_ALREADY_EXISTS as WL_ITEM_ALREADY_EXISTS,
    ITEM_MOVED_FROM_BLACKLIST as WL_ITEM_MOVED_FROM_BLACKLIST,
    ERROR_OCCURRED as WL_ERROR_OCCURRED,
    ITEM_ADDED as BL_ITEM_ADDED,
    ITEM_ALREADY_EXISTS as BL_ITEM_ALREADY_EXISTS,
    ITEM_MOVED_FROM_WHITELIST as BL_ITEM_MOVED_FROM_WHITELIST,
    ERROR_OCCURRED as BL_ERROR_OCCURRED,
    ITEM_REMOVED,
    ITEM_NOT_FOUND,
    INVALID_INPUT
)
from app.utils.analysis import SongAnalyzer
from sqlalchemy.exc import SQLAlchemyError
from ..services.list_management_service import ListManagementService
from . import main_bp
import json
import os
import requests
from app.services.song_status_service import SongStatus 
from sqlalchemy.orm import joinedload

# Load Scripture Mappings
SCRIPTURE_MAPPINGS_PATH = os.path.join(os.path.dirname(__file__), 'scripture_mappings.json')
SCRIPTURE_MAPPINGS = {}
try:
    with open(SCRIPTURE_MAPPINGS_PATH, 'r') as f:
        SCRIPTURE_MAPPINGS = json.load(f)
except FileNotFoundError:
    print(f"ERROR: Scripture mappings file not found at {SCRIPTURE_MAPPINGS_PATH}")
except json.JSONDecodeError:
    print(f"ERROR: Error decoding JSON from {SCRIPTURE_MAPPINGS_PATH}")

@main_bp.route('/')
def index():
    if flask_login_current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/test_base_render')
def test_base_render_route():
    return render_template('test_page.html')

@main_bp.route('/dashboard')
@login_required
@spotify_token_required # Re-enabled
def dashboard():
    playlists_to_display = []
    error_message = None
    sync_message = "Synchronizing your playlists with Spotify. This may take a few moments..."

    try:
        spotify_service = SpotifyService(flask_login_current_user.access_token)
        # sync_user_playlists_with_db should return the playlists from the DB after sync
        synced_playlists = spotify_service.sync_user_playlists_with_db(flask_login_current_user.id)
        playlists_to_display = synced_playlists
        sync_message = "Playlist synchronization complete." if not error_message else sync_message # Keep initial if error happened during sync

    except spotipy.SpotifyException as e:
        current_app.logger.error(f"Spotify API error fetching user playlists for user {flask_login_current_user.id}: {e}")
        error_message = "Could not retrieve playlists from Spotify. Please try again later."
        sync_message = None # No sync message if Spotify API error before/during sync setup
    except Exception as e: # Catch other potential errors
        current_app.logger.error(f"Unexpected error fetching playlists for user {flask_login_current_user.id}: {e}")
        error_message = "An unexpected error occurred while fetching playlists."
        sync_message = None # No sync message on other unexpected errors
    
    return render_template('dashboard.html', 
                           playlists=playlists_to_display, 
                           error_message=error_message,
                           sync_message=sync_message)

@main_bp.route('/check_auth')
@login_required
def check_auth_status():
    return jsonify(
        is_authenticated=flask_login_current_user.is_authenticated,
        user_id=flask_login_current_user.id if flask_login_current_user.is_authenticated else None,
        is_anonymous=flask_login_current_user.is_anonymous,
        is_active=flask_login_current_user.is_active
    )

@main_bp.route('/health')
def health_check():
    current_app.logger.info("Health check route '/health' accessed via main_bp.")
    return jsonify(status="UP", message="Application is healthy."), 200

def update_playlist_score(playlist_id):
    current_app.logger.info(f"Placeholder: update_playlist_score called for playlist_id: {playlist_id}")
    pass

@main_bp.route('/whitelist_playlist/<string:playlist_id>', methods=['POST'])
@login_required
def whitelist_playlist(playlist_id):
    user_id = flask_login_current_user.id
    
    status, _ = add_to_whitelist(user_id, playlist_id, 'playlist')

    if status == WL_ITEM_ADDED:
        flash(f'Playlist {playlist_id} added to your whitelist.', 'success')
    elif status == WL_ITEM_ALREADY_EXISTS:
        flash(f'Playlist {playlist_id} is already in your whitelist.', 'info')
    elif status == WL_ITEM_MOVED_FROM_BLACKLIST:
        flash(f'Playlist {playlist_id} removed from blacklist and added to your whitelist.', 'success')
    elif status == WL_ERROR_OCCURRED:
        flash(f'An error occurred while adding playlist {playlist_id} to whitelist.', 'danger')
    else:
        flash(f'Could not add playlist {playlist_id} to whitelist. Status code: {status}', 'danger')
    
    return redirect(url_for('main.dashboard'))

@main_bp.route('/blacklist_song/<string:playlist_id>/<string:track_id>', methods=['POST'])
@login_required
def blacklist_song(playlist_id, track_id):
    user_id = flask_login_current_user.id

    status, _ = add_to_blacklist(user_id, track_id, 'song')

    if status == BL_ITEM_ADDED:
        flash(f'Song {track_id} added to blacklist.', 'success')
    elif status == BL_ITEM_ALREADY_EXISTS:
        flash(f'Song {track_id} is already in blacklist.', 'info')
    elif status == BL_ITEM_MOVED_FROM_WHITELIST:
        flash(f'Song {track_id} removed from whitelist and added to blacklist.', 'success')
    elif status == BL_ERROR_OCCURRED:
        flash(f'An error occurred while adding song {track_id} to blacklist.', 'danger')
    else:
        flash(f'Could not add song {track_id} to blacklist. Status code: {status}', 'danger')

    return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))

@main_bp.route('/blacklist_playlist/<string:playlist_id>', methods=['POST'])
@login_required
def blacklist_playlist(playlist_id):
    user_id = flask_login_current_user.id

    status, _ = add_to_blacklist(user_id, playlist_id, 'playlist')

    if status == BL_ITEM_ADDED:
        flash(f'Playlist {playlist_id} added to blacklist.', 'success')
    elif status == BL_ITEM_ALREADY_EXISTS:
        flash(f'Playlist {playlist_id} is already in blacklist.', 'info')
    elif status == BL_ITEM_MOVED_FROM_WHITELIST:
        flash(f'Playlist {playlist_id} removed from whitelist and added to blacklist.', 'success')
    elif status == BL_ERROR_OCCURRED:
        flash(f'An error occurred while adding playlist {playlist_id} to blacklist.', 'danger')
    else:
        flash(f'Could not add playlist {playlist_id} to blacklist. Status code: {status}', 'danger')

    return redirect(url_for('main.dashboard'))

@main_bp.route('/whitelist_song/<string:playlist_id>/<string:track_id>', methods=['POST'])
@login_required
def whitelist_song(playlist_id, track_id):
    user_id = flask_login_current_user.id

    status, _ = add_to_whitelist(user_id, track_id, 'song')

    if status == WL_ITEM_ADDED:
        flash(f'Song {track_id} added to your whitelist.', 'success')
    elif status == WL_ITEM_ALREADY_EXISTS:
        flash(f'Song {track_id} is already in your whitelist.', 'info')
    elif status == WL_ITEM_MOVED_FROM_BLACKLIST:
        flash(f'Song {track_id} removed from blacklist and added to your whitelist.', 'success')
    elif status == WL_ERROR_OCCURRED:
        flash(f'An error occurred while adding song {track_id} to whitelist.', 'danger')
    else:
        flash(f'Could not add song {track_id} to whitelist. Status code: {status}', 'danger')

    return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))

SONGS_PER_PAGE = 20

@main_bp.route('/playlist/<string:playlist_id>')
@spotify_token_required
@login_required
def playlist_detail(playlist_id):
    sp = SpotifyService(flask_login_current_user.access_token)
    # list_manager = ListManagementService(sp) # No longer needed for direct lookups here

    if not sp.sp: # Check if the underlying spotipy client is initialized
        flash('Spotify client not available. Please log in again.', 'warning')
        return redirect(url_for('main.index'))

    try:
        user_id = flask_login_current_user.id
        # Pre-fetch whitelist and blacklist for the current user
        user_whitelisted_track_ids = {item.spotify_id for item in Whitelist.query.filter_by(user_id=user_id, item_type='track').all()}
        user_blacklisted_track_ids = {item.spotify_id for item in Blacklist.query.filter_by(user_id=user_id, item_type='track').all()}

        # Fetch basic playlist details
        playlist_data = sp.sp.playlist(playlist_id, fields="id,name,description,images,owner(display_name),tracks(total)")
        if not playlist_data:
            flash('Playlist not found or access denied.', 'danger')
            return redirect(url_for('main.dashboard'))

        # Check if playlist exists in DB or add it
        playlist_in_db = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=user_id).first()
        if not playlist_in_db:
            playlist_in_db = Playlist(
                spotify_id=playlist_data['id'],
                name=playlist_data['name'],
                owner_id=user_id,
                description=playlist_data.get('description', ''),
                image_url=playlist_data['images'][0]['url'] if playlist_data.get('images') else None
            )
            db.session.add(playlist_in_db)
            # db.session.flush() # Ensure playlist_in_db.id is available if needed before commit

        playlist_score_to_display = getattr(playlist_in_db, 'overall_score', None)
        if playlist_score_to_display is None and hasattr(playlist_in_db, 'score') and playlist_in_db.score is not None:
             playlist_score_to_display = playlist_in_db.score
        
        playlist_details = {
            'spotify_id': playlist_data['id'],
            'name': playlist_data['name'],
            'description': playlist_data.get('description'),
            'image_url': playlist_data['images'][0]['url'] if playlist_data.get('images') else None,
            'owner_name': playlist_data['owner']['display_name'],
            'total_tracks': playlist_data['tracks']['total'],
            'score': playlist_score_to_display
        }

        # Pagination logic
        page = request.args.get('page', 1, type=int)
        offset = (page - 1) * SONGS_PER_PAGE
        total_tracks_from_spotify = playlist_data['tracks']['total']
        total_pages = (total_tracks_from_spotify + SONGS_PER_PAGE - 1) // SONGS_PER_PAGE

        tracks_response = sp.get_playlist_items(
            playlist_id,
            fields='items(track(id,name,artists(name),album(name,images),duration_ms))',
            limit=SONGS_PER_PAGE,
            offset=offset
        )
        current_app.logger.debug(f"Spotify tracks_response for playlist {playlist_id}, page {page}: {tracks_response}")

        songs_with_status = []
        if tracks_response and tracks_response.get('items'):
            current_app.logger.debug(f"Processing {len(tracks_response['items'])} items from Spotify.")
            for idx, item in enumerate(tracks_response['items']):
                current_app.logger.debug(f"Processing item {idx+1}: {item}")
                track_data = item.get('track')
                if not track_data or not track_data.get('id'):
                    current_app.logger.warning(f"Skipping item {idx+1} in playlist {playlist_id} due to missing track data or ID: {item}")
                    continue
                
                song_spotify_id = track_data['id']
                current_app.logger.debug(f"Item {idx+1}: song_spotify_id = {song_spotify_id}")

                song_in_db = Song.query.filter_by(spotify_id=song_spotify_id).first()
                if not song_in_db:
                    current_app.logger.debug(f"Item {idx+1}: Song {song_spotify_id} not in DB, creating new entry.")
                    
                    album_art_url = None
                    album_data = track_data.get('album')
                    if album_data and album_data.get('images') and len(album_data['images']) > 0:
                        album_art_url = album_data['images'][0]['url']

                    song_in_db = Song(
                        spotify_id=song_spotify_id,
                        title=track_data.get('name', 'Unknown Title'),
                        artist=', '.join([artist['name'] for artist in track_data.get('artists', [])]),
                        album=album_data.get('name', 'Unknown Album') if album_data else 'Unknown Album',
                        album_art_url=album_art_url,
                        duration_ms=track_data.get('duration_ms') # Add this line
                    )
                    db.session.add(song_in_db)
                    db.session.flush() # Ensure song_in_db.id is populated for AnalysisResult query
                    current_app.logger.debug(f"Item {idx+1}: New song created with ID {song_in_db.id} (pending commit).")
                    # Enqueue analysis for the new song
                    analysis_job = perform_christian_song_analysis_and_store(song_in_db.id)
                    if analysis_job:
                        current_app.logger.info(f"Item {idx+1}: Analysis task enqueued for new song ID {song_in_db.id}. Job ID: {analysis_job.id}")
                    else:
                        current_app.logger.error(f"Item {idx+1}: Failed to enqueue analysis task for new song ID {song_in_db.id}.")
                else:
                    current_app.logger.debug(f"Item {idx+1}: Found song in DB with ID {song_in_db.id}. Current DB album_art_url: '{song_in_db.album_art_url}'")
                    album_data = track_data.get('album')
                    new_album_art_url_from_spotify = None
                    if album_data and album_data.get('images') and len(album_data['images']) > 0:
                        new_album_art_url_from_spotify = album_data['images'][0]['url']
                    current_app.logger.debug(f"Item {idx+1}: Fetched new_album_art_url_from_spotify: '{new_album_art_url_from_spotify}'")
                    
                    needs_db_update = False
                    if new_album_art_url_from_spotify:
                        if not song_in_db.album_art_url:
                            current_app.logger.info(f"Item {idx+1}: Populating missing DB album_art_url for song ID {song_in_db.id} with '{new_album_art_url_from_spotify}'.")
                            song_in_db.album_art_url = new_album_art_url_from_spotify
                            needs_db_update = True
                        elif song_in_db.album_art_url != new_album_art_url_from_spotify:
                            current_app.logger.info(f"Item {idx+1}: Updating DB album_art_url for song ID {song_in_db.id} from '{song_in_db.album_art_url}' to '{new_album_art_url_from_spotify}'.")
                            song_in_db.album_art_url = new_album_art_url_from_spotify
                            needs_db_update = True
                        else:
                            current_app.logger.debug(f"Item {idx+1}: DB album_art_url for song ID {song_in_db.id} is already correct ('{song_in_db.album_art_url}'). No update needed for album art.")
                    else:
                        current_app.logger.debug(f"Item {idx+1}: No new_album_art_url_from_spotify obtained. Cannot update album_art_url for song ID {song_in_db.id}.")

                    # Update duration_ms if it's not set in DB
                    spotify_duration_ms = track_data.get('duration_ms')
                    if spotify_duration_ms is not None: # Ensure we have a value from Spotify
                        if song_in_db.duration_ms is None: # Check if DB value is not set
                            current_app.logger.info(f"Item {idx+1}: Populating missing DB duration_ms for song ID {song_in_db.id} with {spotify_duration_ms} ms.")
                            song_in_db.duration_ms = spotify_duration_ms
                            needs_db_update = True
                        elif song_in_db.duration_ms != spotify_duration_ms: # Optional: update if different, though duration rarely changes
                            current_app.logger.info(f"Item {idx+1}: Updating DB duration_ms for song ID {song_in_db.id} from {song_in_db.duration_ms} to {spotify_duration_ms} ms.")
                            song_in_db.duration_ms = spotify_duration_ms
                            needs_db_update = True
                        else:
                             current_app.logger.debug(f"Item {idx+1}: DB duration_ms for song ID {song_in_db.id} is already correct ({song_in_db.duration_ms} ms). No update needed for duration.")
                    else:
                        current_app.logger.debug(f"Item {idx+1}: No duration_ms found in Spotify track_data for song ID {song_in_db.id}.")

                    # For existing songs, check if analysis is missing and perform it.
                    # The perform_christian_song_analysis_and_store function handles its own commit.
                    # This ensures that even if a song was in DB but never analyzed, it gets analyzed now.
                    # We query for analysis_result again in the common block below this 'if/else song_in_db'.
                    if not AnalysisResult.query.filter_by(song_id=song_in_db.id).first():
                        current_app.logger.info(f"Item {idx+1}: Existing song ID {song_in_db.id} has no AnalysisResult. Enqueuing analysis now.")
                        analysis_job_existing = perform_christian_song_analysis_and_store(song_in_db.id)
                        if analysis_job_existing:
                            current_app.logger.info(f"Item {idx+1}: Analysis task enqueued for existing song ID {song_in_db.id}. Job ID: {analysis_job_existing.id}")
                        else:
                            current_app.logger.error(f"Item {idx+1}: Failed to enqueue analysis task for existing song ID {song_in_db.id}.")

                    if needs_db_update:
                        db.session.add(song_in_db) # Mark as dirty for commit

                is_song_whitelisted = song_spotify_id in user_whitelisted_track_ids
                is_song_blacklisted = song_spotify_id in user_blacklisted_track_ids

                analysis_result = AnalysisResult.query.filter_by(song_id=song_in_db.id).first()
                current_app.logger.debug(f"Item {idx+1}: AnalysisResult query for song_id {song_in_db.id} found: {analysis_result}")

                # Create SongStatus object
                status_obj = SongStatus(
                    song=song_in_db,
                    analysis_result=analysis_result,
                    is_whitelisted=is_song_whitelisted,
                    is_blacklisted=is_song_blacklisted
                )

                # Construct the dictionary for the template
                item_data_to_append = {
                    'song': song_in_db,
                    'analysis_result': analysis_result, # Keep for direct access if needed, though status obj also has it
                    'is_whitelisted': is_song_whitelisted,
                    'is_blacklisted': is_song_blacklisted,
                    'status': status_obj
                    # 'alignment_score' key is removed as it's accessed via status.analysis_result.overall_score in template
                }

                # Detailed log for the status object within the fully constructed item_data_to_append
                current_app.logger.debug(
                    f"Item {idx+1}: STATUS OBJECT IN DICT CHECK. "
                    f"Type: {type(item_data_to_append.get('status'))}, "
                    f"Content: {str(item_data_to_append.get('status'))}, "
                    f"is_preferred: {item_data_to_append.get('status').is_preferred if item_data_to_append.get('status') else 'N/A'}, "
                    f"Display: {item_data_to_append.get('status').display_message if item_data_to_append.get('status') else 'N/A'}, "
                    f"Color: {item_data_to_append.get('status').color_class if item_data_to_append.get('status') else 'N/A'}"
                )
                current_app.logger.debug(f"Item {idx+1}: POST-CONSTRUCTION DICT CHECK. item_data_to_append: {str(item_data_to_append)[:500]}")

                songs_with_status.append(item_data_to_append)
                current_app.logger.debug(f"Item {idx+1}: Appended to songs_with_status. Current count: {len(songs_with_status)}")
            
            # Commit any changes made to song records (like new album_art_url)
            db.session.commit()
            current_app.logger.info(f"Committed session changes after processing tracks for playlist {playlist_id}, page {page}.")

        current_app.logger.debug(f"Finished processing tracks. Total songs in songs_with_status: {len(songs_with_status)}")

        pagination = {
            'page': page,
            'per_page': SONGS_PER_PAGE,
            'total_pages': total_pages,
            'total_items': total_tracks_from_spotify,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < total_pages else None
        }

    except spotipy.SpotifyException as e:
        current_app.logger.error(f"Spotify API error in playlist_detail for {playlist_id}: {e}")
        flash(f'Spotify API error: Could not load playlist details. Details: {str(e)}', 'danger')
        return redirect(url_for('main.dashboard'))
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in playlist_detail for {playlist_id}: {e}", exc_info=True)
        flash(f'A database error occurred. Details: {str(e)}', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in playlist_detail for {playlist_id}: {e}", exc_info=True)
        flash(f'An unexpected error occurred. Type: {type(e).__name__}, Details: {str(e)}', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_template('playlist_detail.html', playlist=playlist_details, songs_with_status=songs_with_status, pagination=pagination)

@main_bp.route('/playlist/<string:playlist_id>/update', methods=['POST'])
@login_required
def update_playlist(playlist_id):
    """Handles updating a playlist's tracks and syncing to Spotify."""
    merged_user = db.session.merge(flask_login_current_user) # Use new local variable name
    if not merged_user.ensure_token_valid(): # Use merged_user
        flash("Spotify session expired or token is invalid. Please refresh or log in again.", "warning")
        return redirect(url_for('auth.login'))

    db_playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=merged_user.id).first() # Use merged_user
    if not db_playlist:
        flash("Playlist not found or you don't have permission to update it.", "danger")
        return redirect(url_for('main.dashboard'))

    # Assuming the frontend sends a list of track URIs in order
    # For example, as 'track_uris[]' in form data or a JSON payload
    ordered_track_uris = request.form.getlist('track_uris[]') # Example: form data with multiple track_uris[]
    expected_snapshot_id = request.form.get('expected_snapshot_id')

    # Validate input types (example)
    if not isinstance(ordered_track_uris, list) or not isinstance(expected_snapshot_id, str):
        flash("Invalid data format for tracks or snapshot ID.", "warning") # Generic message, can be more specific
        # Log this as it might indicate a frontend issue or manipulation attempt
        current_app.logger.warning(
            f"Invalid data types received for playlist update. User: {merged_user.id}, Playlist: {playlist_id}. "
            f"Track URIs type: {type(ordered_track_uris)}, Snapshot ID type: {type(expected_snapshot_id)}"
        )
        # Redirect back to the playlist detail page, as that's where the form likely is.
        return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))

    # Check if ordered_track_uris is empty or not provided
    if not ordered_track_uris:
        flash("No track information received to update the playlist.", "warning")
        return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))

    # Initialize ListManagementService with the current user's SpotifyService instance
    spotify_service = SpotifyService(merged_user.access_token) # Use merged_user
    list_management_service = ListManagementService(spotify_service) # Corrected: removed db.session

    success, message, status_code = list_management_service.update_playlist_and_sync_to_spotify(
        user=merged_user, # Use merged_user
        local_playlist_id=db_playlist.id,
        new_track_uris_ordered=ordered_track_uris,
        expected_snapshot_id=expected_snapshot_id
    )

    flash_category = 'success' if success else ('warning' if status_code == 409 else 'danger')
    flash(message, flash_category)

    if not success and status_code == 401:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.playlist_detail', playlist_id=db_playlist.spotify_id))

@main_bp.route('/remove_song/<playlist_id>/<track_id>', methods=['POST'])
@login_required
def remove_song(playlist_id, track_id):
    merged_user = db.session.merge(flask_login_current_user) # Apply same pattern here for consistency
    if not merged_user.ensure_token_valid(): # Use merged_user
        flash('Your Spotify session has expired. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

    sp = spotipy.Spotify(auth=merged_user.access_token) # Use merged_user
    redirect_url = url_for('main.dashboard') # Default redirect
    
    try:
        user_spotify_id = merged_user.spotify_id # Use merged_user
        if not user_spotify_id:
            user_info = sp.me()
            user_spotify_id = user_info['id']

        playlist_info = sp.playlist(playlist_id, fields='owner.id')
        playlist_owner_id = playlist_info['owner']['id']
        
        # If we have a valid playlist_id, errors should generally redirect back to its detail page
        redirect_url = url_for('main.playlist_detail', playlist_id=playlist_id)

        if user_spotify_id == playlist_owner_id:
            sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_id])
            current_app.logger.info(f"User {user_spotify_id} successfully removed song {track_id} from Spotify playlist {playlist_id}.")

            db_playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=merged_user.id).first() # Use merged_user
            db_song = Song.query.filter_by(spotify_id=track_id).first()

            if db_song is None:
                flash(f'Song with track_id {track_id} not found in local database.', 'warning') # Changed to warning
            elif db_playlist and db_song:
                ps_assoc = PlaylistSong.query.filter_by(playlist_id=db_playlist.id, song_id=db_song.id).first()
                if ps_assoc:
                    db.session.delete(ps_assoc)
                    db.session.commit()
                    current_app.logger.info(f"Successfully removed song {db_song.title} from local playlist {db_playlist.name} for user {merged_user.id}.") # Use merged_user
                    flash(f'Song removed from playlist {playlist_id}.', 'success')
                    # Successful removal redirects to playlist detail
                    return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
                else:
                    current_app.logger.warning(f"PlaylistSong association not found locally for playlist {db_playlist.name} and song {db_song.title}.")
                    flash('Song not found in this playlist locally.', 'info') # Changed to info
            else:
                if not db_playlist:
                    current_app.logger.warning(f"Local playlist with spotify_id {playlist_id} not found for user {merged_user.id}.") # Use merged_user
                    flash('Local playlist data not found.', 'warning') # Changed to warning
            
        else:
            flash('You can only remove songs from playlists you own.', 'danger')
            current_app.logger.warning(f"User {user_spotify_id} attempt to remove song from unowned playlist {playlist_id}.")
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
    except spotipy.SpotifyException as e:
        flash(f'Could not remove song from Spotify: {str(e)}', 'danger')
        current_app.logger.error(f"Spotify API error for user {merged_user.id} removing song: {e}") # Use merged_user
        return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
    except SQLAlchemyError as e:
        db.session.rollback()
        flash('A database error occurred while removing the song.', 'danger')
        current_app.logger.error(f"Database error removing song association: {e}")
        return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
    except Exception as e:
        flash('An unexpected error occurred.', 'danger')
        current_app.logger.error(f"Unexpected error in remove_song: {e}")
        # For truly unexpected errors, dashboard might be safer if playlist_id context is lost/corrupt
        return redirect(url_for('main.dashboard'))
    
    return redirect(redirect_url) # Use the determined redirect_url

@main_bp.route('/remove_whitelist_playlist/<string:playlist_id>', methods=['POST'])
@login_required
def remove_whitelist_playlist(playlist_id):
    user_id = flask_login_current_user.id
    status, message = remove_from_whitelist(user_id, spotify_id=playlist_id, item_type='playlist')

    if status == ITEM_REMOVED:
        flash(f'Playlist {playlist_id} removed from your whitelist.', 'success')
    elif status == ITEM_NOT_FOUND:
        flash(f'Playlist {playlist_id} was not found in your whitelist.', 'info')
    else:
        flash(f'Error removing playlist {playlist_id} from whitelist: {message}', 'danger')

    return redirect(request.referrer or url_for('main.dashboard')) 

@main_bp.route('/remove_blacklist_playlist/<string:playlist_id>', methods=['POST'])
@login_required
def remove_blacklist_playlist(playlist_id):
    user_id = flask_login_current_user.id
    status, message = remove_from_blacklist(user_id, spotify_id=playlist_id, item_type='playlist')

    if status == ITEM_REMOVED:
        flash(f'Playlist {playlist_id} removed from your blacklist.', 'success')
    elif status == ITEM_NOT_FOUND:
        flash(f'Playlist {playlist_id} was not found in your blacklist.', 'info')
    else:
        flash(f'Error removing playlist {playlist_id} from blacklist: {message}', 'danger')

    return redirect(request.referrer or url_for('main.dashboard'))

@main_bp.route('/remove_whitelist_song/<string:playlist_id>/<string:track_id>', methods=['POST'])
@login_required
def remove_whitelist_song(playlist_id, track_id):
    user_id = flask_login_current_user.id
    status, message = remove_from_whitelist(user_id, spotify_id=track_id, item_type='song')

    if status == ITEM_REMOVED:
        flash(f'Song {track_id} removed from your whitelist.', 'success')
    elif status == ITEM_NOT_FOUND:
        flash(f'Song {track_id} was not found in your whitelist.', 'info')
    else:
        flash(f'Error removing song {track_id} from whitelist: {message}', 'danger')

    return redirect(request.referrer or url_for('main.playlist_detail', playlist_id=playlist_id))

@main_bp.route('/remove_blacklist_song/<string:playlist_id>/<string:track_id>', methods=['POST'])
@login_required
def remove_blacklist_song(playlist_id, track_id):
    user_id = flask_login_current_user.id
    status, message = remove_from_blacklist(user_id, spotify_id=track_id, item_type='song')

    if status == ITEM_REMOVED:
        flash(f'Song {track_id} removed from your blacklist.', 'success')
    elif status == ITEM_NOT_FOUND:
        flash(f'Song {track_id} was not found in your blacklist.', 'info')
    else:
        flash(f'Error removing song {track_id} from blacklist: {message}', 'danger')
        
    return redirect(request.referrer or url_for('main.playlist_detail', playlist_id=playlist_id))

# API Endpoints for Quick Song Actions (Whitelist/Blacklist)

@main_bp.route('/api/song/<int:song_db_id>/whitelist', methods=['POST'])
@login_required
def api_whitelist_song(song_db_id):
    user_id = flask_login_current_user.id
    song = Song.query.get(song_db_id)

    if not song:
        return jsonify({'success': False, 'message': 'Song not found.'}), 404

    if not song.spotify_id:
        return jsonify({'success': False, 'message': 'Song does not have a Spotify ID.'}), 400

    status, _ = add_to_whitelist(user_id, song.spotify_id, 'song')

    new_status_for_ui = 'unknown'
    if status == WL_ITEM_ADDED:
        message = 'Song added to your whitelist.'
        new_status_for_ui = 'whitelisted'
        success = True
    elif status == WL_ITEM_ALREADY_EXISTS:
        message = 'Song is already in your whitelist.'
        new_status_for_ui = 'whitelisted'
        success = True
    elif status == WL_ITEM_MOVED_FROM_BLACKLIST:
        message = 'Song removed from blacklist and added to your whitelist.'
        new_status_for_ui = 'whitelisted'
        success = True
    else: # WL_ERROR_OCCURRED or other
        message = 'An error occurred while adding song to whitelist.'
        new_status_for_ui = 'error'
        success = False
    
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error during whitelist API call: {e}")
        return jsonify({'success': False, 'message': 'Database error occurred.', 'new_status': 'error'}), 500
        
    return jsonify({'success': success, 'message': message, 'new_status': new_status_for_ui, 'spotify_id': song.spotify_id})

@main_bp.route('/api/song/<int:song_db_id>/blacklist', methods=['POST'])
@login_required
def api_blacklist_song(song_db_id):
    user_id = flask_login_current_user.id
    song = Song.query.get(song_db_id)

    if not song:
        return jsonify({'success': False, 'message': 'Song not found.'}), 404
    
    if not song.spotify_id:
        return jsonify({'success': False, 'message': 'Song does not have a Spotify ID.'}), 400

    status, _ = add_to_blacklist(user_id, song.spotify_id, 'song')

    new_status_for_ui = 'unknown'
    if status == BL_ITEM_ADDED:
        message = 'Song added to blacklist.'
        new_status_for_ui = 'blacklisted'
        success = True
    elif status == BL_ITEM_ALREADY_EXISTS:
        message = 'Song is already in blacklist.'
        new_status_for_ui = 'blacklisted'
        success = True
    elif status == BL_ITEM_MOVED_FROM_WHITELIST:
        message = 'Song removed from whitelist and added to blacklist.'
        new_status_for_ui = 'blacklisted'
        success = True
    else: # BL_ERROR_OCCURRED or other
        message = 'An error occurred while adding song to blacklist.'
        new_status_for_ui = 'error'
        success = False

    try:
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error during blacklist API call: {e}")
        return jsonify({'success': False, 'message': 'Database error occurred.', 'new_status': 'error'}), 500

    return jsonify({'success': success, 'message': message, 'new_status': new_status_for_ui, 'spotify_id': song.spotify_id})

@main_bp.route('/song/<string:song_id>')
@login_required
def song_detail(song_id):
    current_app.logger.info(f"Accessing song detail page for song_id: {song_id}")
    # Using generic song_id now. Could be Spotify ID or local DB ID depending on how you link to this page.
    # For consistency, let's assume song_id IS the Spotify ID for now.
    song = Song.query.filter_by(spotify_id=song_id).first()

    if not song:
        flash('Song not found.', 'danger')
        current_app.logger.warning(f"Song with spotify_id '{song_id}' not found.")
        return redirect(url_for('main.dashboard')) # Or some other appropriate page

    analysis_result_db = AnalysisResult.query.filter_by(song_id=song.id).first()
    
    prepared_analysis_data = {}
    lyrics_to_render = song.lyrics # Assuming Song model has a lyrics field, fallback later
    concern_level_class = "text-muted"
    scriptures_to_render = []
    positive_themes_to_render = {}
    negative_themes_to_render = {} # Placeholder for now
    purity_flags_triggered_to_render = {}

    if analysis_result_db:
        try:
            raw_analysis = json.loads(analysis_result_db.raw_analysis) if analysis_result_db.raw_analysis else {}
            lyrics_to_render = raw_analysis.get('lyrics_used_for_analysis', song.lyrics)
            
            parsed_themes = json.loads(analysis_result_db.themes) if analysis_result_db.themes else []
            parsed_purity_flags = json.loads(analysis_result_db.purity_flags_details) if analysis_result_db.purity_flags_details else []

            prepared_analysis_data = {
                "score": analysis_result_db.score,
                "concern_level": analysis_result_db.concern_level,
                "analyzed_at": analysis_result_db.analyzed_at,
                # Raw fields for potential direct use or debugging in template
                "raw_themes_list": parsed_themes,
                "raw_purity_flags_list": parsed_purity_flags,
                "raw_full_analysis_blob": raw_analysis
            }

            # Determine concern_level_class
            if analysis_result_db.concern_level:
                level_lower = analysis_result_db.concern_level.lower()
                if level_lower == "high": concern_level_class = "text-danger"
                elif level_lower == "medium": concern_level_class = "text-warning"
                elif level_lower == "low": concern_level_class = "text-success"
                else: concern_level_class = "text-info" # For 'None' or other

            # Transform purity_flags_details (list of dicts) to dict for template
            # Original template: {% for flag, details in purity_flags_triggered.items() %}
            # where details might be like {'penalty': X}
            # Assuming parsed_purity_flags is like [{'category': 'Profanity', 'level': 'Low', 'penalty': 5, 'details': '...'}, ...]
            for flag_detail in parsed_purity_flags:
                purity_flags_triggered_to_render[flag_detail.get('category', 'Unknown Flag')] = {
                    'penalty': flag_detail.get('penalty', 0),
                    'level': flag_detail.get('level', 'N/A'),
                    'details': flag_detail.get('details', '')
                }

            # Transform themes (list of dicts) to dicts for template
            # Original template expects: positive_themes = {theme_name: {points: Y}}, negative_themes = ...
            # Assuming parsed_themes is like [{'theme': 'Faith', 'score_impact': 5, 'keywords': [], 'scriptures': [REF1,...]}, ...]
            # For now, consider all themes in parsed_themes as positive.
            for theme_detail in parsed_themes:
                theme_name = theme_detail.get('theme', 'Unknown Theme')
                positive_themes_to_render[theme_name] = {
                    'points': theme_detail.get('score_impact', 0), # or some other field representing points
                    'keywords': theme_detail.get('keywords', [])
                    # Scriptures for this theme will be handled in the scripture_to_render loop
                }
                # Populate scriptures_to_render
                for ref in theme_detail.get('scriptures', []):
                    scripture_info = SCRIPTURE_MAPPINGS.get(ref, {})
                    scriptures_to_render.append({
                        'reference': ref,
                        'theme_or_flag': theme_name,
                        'text_bsb': scripture_info.get('text_bsb'),
                        'text_kjv': scripture_info.get('text_kjv'),
                        'full_mapping': scripture_info # For more detailed display if needed
                    })

        except json.JSONDecodeError as e:
            current_app.logger.error(f"Error decoding JSON for analysis of song {song.id}: {e}")
            prepared_analysis_data = {"error": "Could not parse analysis data."}
        except Exception as e:
            current_app.logger.error(f"Unexpected error processing analysis for song {song.id}: {e}")
            prepared_analysis_data = {"error": "An unexpected error occurred while processing analysis data."}
    else:
        current_app.logger.info(f"No analysis found for song '{song.title}' (ID: {song.id}).")
        # Provide default empty structures if no analysis
        prepared_analysis_data = {"score": "N/A", "concern_level": "Not Analyzed"}

    # Get playlist_id from request arguments for 'back' links
    playlist_spotify_id_from_request = request.args.get('playlist_id')

    return render_template('song_detail.html', 
                           song=song, 
                           analysis=prepared_analysis_data, 
                           lyrics=lyrics_to_render,
                           concern_level_class=concern_level_class,
                           purity_flags_triggered=purity_flags_triggered_to_render,
                           positive_themes=positive_themes_to_render,
                           negative_themes=negative_themes_to_render, # Still empty for now
                           scriptures=scriptures_to_render,
                           playlist_spotify_id=playlist_spotify_id_from_request)

@main_bp.route('/analyze_playlist_api/<string:playlist_id>', methods=['POST'])
@login_required
@spotify_token_required
def analyze_playlist_api(playlist_id):
    current_app.logger.info(f"analyze_playlist_api called for playlist_id: {playlist_id}")
    try:
        # Call the service function to analyze the playlist
        analysis_summary = analyze_playlist_content(playlist_id, flask_login_current_user.id)

        if analysis_summary.get("error"):
            current_app.logger.error(f"Error analyzing playlist {playlist_id}: {analysis_summary['error']}")
            return jsonify({"success": False, "message": analysis_summary["error"]}), 500

        current_app.logger.info(f"Playlist {playlist_id} analysis triggered successfully. Summary: {analysis_summary}")
        return jsonify({
            "success": True, 
            "message": f"Analysis for playlist {playlist_id} initiated.", 
            "analysis_summary": analysis_summary
        })
    except Exception as e:
        current_app.logger.error(f"Exception in analyze_playlist_api for playlist {playlist_id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "An unexpected error occurred during playlist analysis."}), 500
