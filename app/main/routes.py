from flask import render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_required, current_user as flask_login_current_user
import spotipy

from .. import db
from ..models import User, Whitelist, Blacklist, Song, AnalysisResult, PlaylistSong, Playlist
from ..services.spotify_service import SpotifyService
from ..services.analysis_service import analyze_playlist_content, get_playlist_analysis_results
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
from app.services.song_status_service import SongStatus # UPDATE THIS IMPORT

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

@main_bp.route('/playlist/<string:playlist_spotify_id>/song/<string:track_spotify_id>')
@login_required
@spotify_token_required
def song_detail(playlist_spotify_id, track_spotify_id):
    song = Song.query.filter_by(spotify_id=track_spotify_id).first()

    if not song:
        flash('Song not found in the database.', 'danger')
        return redirect(url_for('main.playlist_detail', playlist_id=playlist_spotify_id))

    lyrics = song.lyrics_cleaned or song.lyrics
    analysis_results_data = {
        'final_score': None,
        'concern_level': 'Not Analyzed',
        'concern_level_class': 'text-muted',
        'purity_flags_triggered': {},
        'positive_themes': {},
        'negative_themes': {}
    }

    analysis_record = AnalysisResult.query.filter_by(song_id=song.id).first()

    if analysis_record:
        analysis_results_data['final_score'] = analysis_record.alignment_score # This is the overall score from SongAnalyzer

        # Process Purity Flags
        # Assumes analysis_record.problematic_content is a list of detected canonical flag names (strings)
        if analysis_record.problematic_content and isinstance(analysis_record.problematic_content, (list, set)):
            for flag_name in analysis_record.problematic_content:
                if flag_name in PURITY_FLAGS_SCORING:
                    analysis_results_data['purity_flags_triggered'][flag_name] = \
                        {'penalty': PURITY_FLAGS_SCORING[flag_name]}
        elif isinstance(analysis_record.problematic_content, dict):
            # Fallback for older dict structure, preferring canonical scores
            current_app.logger.warning(f"Problematic content for song {song.id} is a dict, processing keys.")
            for flag_name in analysis_record.problematic_content.keys():
                 if flag_name in PURITY_FLAGS_SCORING:
                    analysis_results_data['purity_flags_triggered'][flag_name] = \
                        {'penalty': PURITY_FLAGS_SCORING[flag_name]}

        # Process Themes
        # Assumes analysis_record.themes is a list of detected canonical theme names (strings)
        if analysis_record.themes and isinstance(analysis_record.themes, (list, set)):
            for theme_name in analysis_record.themes:
                if theme_name in POSITIVE_THEMES_SCORING:
                    analysis_results_data['positive_themes'][theme_name] = \
                        {'points': POSITIVE_THEMES_SCORING[theme_name]}
                elif theme_name in NEGATIVE_THEMES_SCORING:
                    analysis_results_data['negative_themes'][theme_name] = \
                        {'penalty': NEGATIVE_THEMES_SCORING[theme_name]}
        elif isinstance(analysis_record.themes, dict):
            # Fallback for older dict structure, preferring canonical scores
            current_app.logger.warning(f"Themes for song {song.id} is a dict, processing keys.")
            for theme_name in analysis_record.themes.keys():
                if theme_name in POSITIVE_THEMES_SCORING:
                    analysis_results_data['positive_themes'][theme_name] = \
                        {'points': POSITIVE_THEMES_SCORING[theme_name]}
                elif theme_name in NEGATIVE_THEMES_SCORING:
                    analysis_results_data['negative_themes'][theme_name] = \
                        {'penalty': NEGATIVE_THEMES_SCORING[theme_name]}

        purity_flags_count = len(analysis_results_data['purity_flags_triggered'])
        concern_level, concern_class = _get_concern_level_details(analysis_results_data['final_score'], purity_flags_count)
        analysis_results_data['concern_level'] = concern_level
        analysis_results_data['concern_level_class'] = concern_class
    
    scriptures = []
    # Fetch scriptures for all identified themes and flags
    items_for_scripture_lookup = list(analysis_results_data['positive_themes'].keys()) + \
                                 list(analysis_results_data['negative_themes'].keys()) + \
                                 list(analysis_results_data['purity_flags_triggered'].keys())

    for item_name in items_for_scripture_lookup:
        if item_name in SCRIPTURE_MAPPINGS:
            for ref_string in SCRIPTURE_MAPPINGS[item_name]:
                bsb_text = get_bible_verse_text(ref_string, 'bsb')
                kjv_text = None
                if bsb_text is None: # Fallback to KJV if BSB fails or returns nothing
                    current_app.logger.info(f"BSB text not found for '{ref_string}', trying KJV.")
                    kjv_text = get_bible_verse_text(ref_string, 'kjv')
                
                # Only add if at least one translation was successful
                if bsb_text or kjv_text:
                    scriptures.append({
                        'reference': ref_string,
                        'theme_or_flag': item_name,
                        'text_bsb': bsb_text,
                        'text_kjv': kjv_text
                    })
                else:
                    current_app.logger.warning(f"Could not fetch scripture for '{ref_string}' (Theme/Flag: {item_name}) in BSB or KJV.")

    return render_template('song_detail.html', 
                           song=song, 
                           lyrics=lyrics, 
                           analysis_results=analysis_results_data, 
                           scriptures=scriptures, 
                           playlist_spotify_id=playlist_spotify_id)


def _get_concern_level_details(score, purity_flags_triggered_count):
    """Helper function to determine concern level and CSS class based on score and purity flags."""
    concern_level = "Not Analyzed"
    concern_level_class = "text-muted"

    if score is not None:
        if purity_flags_triggered_count > 0:
            concern_level = "High"
            concern_level_class = "text-danger"
        elif 40 <= score <= 69:
            concern_level = "Medium"
            concern_level_class = "text-warning"
        elif score >= 70:
            concern_level = "Low"
            concern_level_class = "text-success"
        else: # Score < 40 and no purity flags
            concern_level = "Medium" # Or potentially another category like 'Low - Needs Review'
            concern_level_class = "text-warning"
    return concern_level, concern_level_class

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

@main_bp.route('/api/playlist/<string:playlist_spotify_id>/analyze', methods=['POST'])
@login_required
@spotify_token_required
def api_analyze_playlist(playlist_spotify_id):
    user_id = flask_login_current_user.id
    playlist = Playlist.query.filter_by(spotify_id=playlist_spotify_id, user_id=user_id).first()

    if not playlist:
        current_app.logger.warn(f"Attempt to analyze non-existent or unauthorized playlist {playlist_spotify_id} by user {user_id}")
        return jsonify({'success': False, 'message': 'Playlist not found or not authorized.'}), 404

    # Get all song database IDs and Spotify IDs from the playlist
    songs_in_playlist_query = db.session.query(Song.id, Song.spotify_id, Song.title)\
                                  .join(PlaylistSong, Song.id == PlaylistSong.song_id)\
                                  .filter(PlaylistSong.playlist_id == playlist.id)\
                                  .all()

    if not songs_in_playlist_query:
        current_app.logger.info(f"Playlist {playlist_spotify_id} (DB ID: {playlist.id}) has no songs to analyze for user {user_id}.")
        return jsonify({'success': True, 'message': 'Playlist has no songs to analyze.'}), 200

    song_spotify_ids_to_fetch = [s.spotify_id for s in songs_in_playlist_query if s.spotify_id]
    if not song_spotify_ids_to_fetch:
        current_app.logger.info(f"Playlist {playlist_spotify_id} has songs, but none with Spotify IDs. Analysis skipped.")
        return jsonify({'success': True, 'message': 'No songs with Spotify IDs in the playlist to analyze.'}), 200

    analyzer = SongAnalyzer()
    spotify_service = SpotifyService(flask_login_current_user.access_token)

    analyzed_count = 0
    error_count = 0
    errors_details = []
    already_analyzed_count = 0

    try:
        detailed_spotify_tracks_info_list = spotify_service.get_tracks_details(song_spotify_ids_to_fetch)
        spotify_tracks_map = {track['id']: track for track in detailed_spotify_tracks_info_list if track and track.get('id')}
    except Exception as e:
        current_app.logger.error(f"Failed to fetch batch track details from Spotify for playlist {playlist_spotify_id}: {e}")
        return jsonify({'success': False, 'message': f'Error fetching track details from Spotify: {str(e)}'}), 500

    for song_record in songs_in_playlist_query:
        song_db_id = song_record.id
        song_spotify_id_val = song_record.spotify_id
        song_title = song_record.title

        if not song_spotify_id_val:
            current_app.logger.warning(f"Song '{song_title}' (DB ID {song_db_id}) in playlist {playlist_spotify_id} has no Spotify ID. Skipping analysis.")
            continue

        track_info = spotify_tracks_map.get(song_spotify_id_val)
        if not track_info:
            current_app.logger.warning(f"Could not retrieve Spotify details for track '{song_title}' ({song_spotify_id_val}). Skipping analysis.")
            error_count += 1
            errors_details.append(f"Spotify details missing for '{song_title}' ({song_spotify_id_val})")
            continue
        
        try:
            # Check if already analyzed to avoid re-processing if not needed, or if SongAnalyzer handles this idempotently
            # For now, we assume analyze_song_for_user is idempotent or we always want to re-trigger.
            # It returns (analysis_result, was_analyzed_now)
            analysis_result, was_analyzed_now = analyzer.analyze_song_for_user(
                song_db_id=song_db_id,
                user_id=user_id,
                spotify_track_info=track_info
            )
            
            if analysis_result:
                if was_analyzed_now:
                    analyzed_count += 1
                else:
                    already_analyzed_count +=1 # Count as processed, but not newly analyzed
            else:
                error_count += 1
                errors_details.append(f"Analysis failed for song '{song_title}' ({song_spotify_id_val})")

        except Exception as e:
            current_app.logger.error(f"Error analyzing song '{song_title}' ({song_spotify_id_val}) in playlist {playlist_spotify_id}: {e}", exc_info=True)
            error_count += 1
            errors_details.append(f"Error during analysis for '{song_title}' ({song_spotify_id_val}): An unexpected error occurred.")
    
    total_processed = analyzed_count + already_analyzed_count
    message = f"Playlist analysis processed. Newly analyzed: {analyzed_count} songs. Already analyzed: {already_analyzed_count} songs. Total processed: {total_processed}."
    if error_count > 0:
        message += f" Errors encountered for {error_count} songs."
    
    current_app.logger.info(message + f" For playlist: {playlist_spotify_id}, User: {user_id}")

    # Note: SongAnalyzer.analyze_song_for_user commits its own AnalysisResult changes.
    # If playlist-level aggregates were updated (e.g. playlist score), a commit might be needed here.
    # For now, assuming only song analyses are performed and committed individually.

    return jsonify({
        'success': True, 
        'message': message,
        'newly_analyzed_count': analyzed_count,
        'already_analyzed_count': already_analyzed_count,
        'total_processed_count': total_processed,
        'error_count': error_count,
        'errors_details': errors_details if error_count > 0 else []
    }), 200

# Note: Ensure scripture_mappings.json is correctly loaded and handled if its path changes or if it's critical for startup.
# The SCRIPTURE_MAPPINGS loading block appears at the top of this file.
