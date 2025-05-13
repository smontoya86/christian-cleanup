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
    playlists = []
    error_message = None
    try:
        spotify_service = SpotifyService(flask_login_current_user.access_token)
        playlists = spotify_service.sync_user_playlists_with_db(flask_login_current_user.id)
    except spotipy.SpotifyException as e:
        current_app.logger.error(f"Spotify API error fetching user playlists for user {flask_login_current_user.id}: {e}")
        error_message = "Could not retrieve playlists from Spotify. Please try again later."
    except Exception as e: # Catch other potential errors
        current_app.logger.error(f"Unexpected error fetching playlists for user {flask_login_current_user.id}: {e}")
        error_message = "An unexpected error occurred while fetching playlists."
    return render_template('dashboard.html', playlists=playlists, error_message=error_message)

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

@main_bp.route('/playlist/<playlist_id>')
@spotify_token_required
@login_required
def playlist_detail(playlist_id):
    if not hasattr(flask_login_current_user, 'access_token') or not flask_login_current_user.access_token:
        flash('Spotify access token not found. Please re-login.', 'danger')
        return redirect(url_for('auth.logout'))

    sp = spotipy.Spotify(auth=flask_login_current_user.access_token)
    analyzer = SongAnalyzer()
    playlist_details = None
    songs_with_status = []

    try:
        playlist_data = sp.playlist(playlist_id)
        if not playlist_data:
            flash('Playlist not found.', 'danger')
            return redirect(url_for('main.dashboard'))

        playlist_in_db = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=flask_login_current_user.id).first()
        if not playlist_in_db:
            playlist_in_db = Playlist(
                spotify_id=playlist_data['id'], 
                name=playlist_data['name'], 
                owner_id=flask_login_current_user.id, 
                description=playlist_data.get('description', ''))
            db.session.add(playlist_in_db)
            db.session.commit()

        playlist_details = {
            'id': playlist_data['id'],
            'name': playlist_data['name'],
            'description': playlist_data.get('description'),
            'image_url': playlist_data['images'][0]['url'] if playlist_data.get('images') else None,
            'owner_name': playlist_data['owner']['display_name'],
            'total_tracks': playlist_data['tracks']['total']
        }

        tracks_response = sp.playlist_items(playlist_id, fields='items(track(id,name,artists(name),album(name,images)))')
        for item in tracks_response.get('items', []):
            track_data = item.get('track')
            if not track_data or not track_data.get('id'):
                current_app.logger.warning(f"Skipping item in playlist {playlist_id} due to missing track data or ID: {item}")
                continue

            song_spotify_id = track_data['id']
            
            song_in_db = Song.query.filter_by(spotify_id=song_spotify_id).first()
            if not song_in_db:
                song_in_db = Song(
                    spotify_id=song_spotify_id,
                    title=track_data['name'],
                    artist=', '.join([artist['name'] for artist in track_data.get('artists', [])]),
                    album=track_data.get('album', {}).get('name'),
                )
                db.session.add(song_in_db)
                try:
                    db.session.commit()
                    current_app.logger.info(f"Added new song {song_in_db.title} ({song_in_db.spotify_id}) to DB from playlist {playlist_id}")
                except SQLAlchemyError as e:
                    db.session.rollback()
                    current_app.logger.error(f"Error adding song {track_data['name']} to DB: {e}")
                    continue 

            song_status = 'none'
            is_song_whitelisted = Whitelist.query.filter_by(user_id=flask_login_current_user.id, spotify_id=song_spotify_id, item_type='song').first() is not None
            if is_song_whitelisted:
                song_status = 'whitelisted'
            else:
                is_song_blacklisted = Blacklist.query.filter_by(user_id=flask_login_current_user.id, spotify_id=song_spotify_id, item_type='song').first() is not None
                if is_song_blacklisted:
                    song_status = 'blacklisted'

            analysis_result = AnalysisResult.query.filter_by(song_id=song_in_db.id).first()
            themes_and_scriptures = None
            problematic_content = None
            alignment_score = None
            explanation = None

            if not analysis_result and song_in_db.lyrics:
                current_app.logger.info(f"No analysis found for {song_in_db.title}. Analyzing...")
                analyzer = SongAnalyzer()
                try:
                    analysis_data = analyzer.analyze_song(song_in_db.title, song_in_db.artist, lyrics=song_in_db.lyrics_cleaned or song_in_db.lyrics)
                    
                    if analysis_data:
                        new_analysis = AnalysisResult(
                            song_id=song_in_db.id,
                            themes=analysis_data.get('detailed_theme_analysis'), 
                            problematic_content=analysis_data.get('problematic_content'),
                            alignment_score=analysis_data.get('alignment_score'),
                            explanation=analysis_data.get('explanation')
                        )
                        db.session.add(new_analysis)
                        db.session.commit()
                        current_app.logger.info(f"Successfully analyzed and saved results for {song_in_db.title}")
                        themes_and_scriptures = new_analysis.themes
                        problematic_content = new_analysis.problematic_content
                        alignment_score = new_analysis.alignment_score
                        explanation = new_analysis.explanation
                    else:
                        current_app.logger.warning(f"Analysis for {song_in_db.title} returned no data.")

                except Exception as e:
                    current_app.logger.error(f"Error during song analysis for {song_in_db.title}: {e}")
                    db.session.rollback()
            elif analysis_result:
                themes_and_scriptures = analysis_result.themes
                problematic_content = analysis_result.problematic_content
                alignment_score = analysis_result.alignment_score
                explanation = analysis_result.explanation

            songs_with_status.append({
                'id': song_spotify_id,
                'spotify_id': song_spotify_id,
                'title': song_in_db.title,
                'artist': song_in_db.artist,
                'album': song_in_db.album,
                'status': song_status,
                'themes_and_scriptures': themes_and_scriptures,
                'problematic_content': problematic_content,
                'alignment_score': alignment_score,
                'score': alignment_score,
                'explanation': explanation
            })

        db.session.commit()

    except spotipy.SpotifyException as e:
        current_app.logger.error(f"Spotify API error for user {flask_login_current_user.id} on playlist_detail: {e}")
        if e.http_status == 401:
            flash('Your Spotify session has expired. Please log in again.', 'warning')
            return redirect(url_for('auth.logout'))
        flash('Could not retrieve playlist details from Spotify.', 'danger')
        return redirect(url_for('main.dashboard'))
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error on playlist_detail for user {flask_login_current_user.id}: {e}")
        flash('A database error occurred.', 'danger')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error on playlist_detail for user {flask_login_current_user.id}: {e}")
        flash('An unexpected error occurred.', 'danger')
        return redirect(url_for('main.dashboard'))

    return render_template('playlist_detail.html', playlist=playlist_details, songs=songs_with_status)

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
