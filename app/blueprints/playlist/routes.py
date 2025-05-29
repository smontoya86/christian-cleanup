"""
Playlist Blueprint Routes - Playlist viewing, management, and synchronization.

This file contains the routes for:
- Playlist synchronization with Spotify
- Playlist detail viewing and management
- Song removal from playlists
- Playlist analysis operations
"""

import time
import spotipy
from flask import render_template, flash, redirect, url_for, request, current_app, jsonify, session, abort
from flask_login import login_required, current_user as flask_login_current_user
from sqlalchemy.exc import SQLAlchemyError

# Import the blueprint
from . import playlist_bp

# Import required modules
from app import db
from app.models import User, Song, AnalysisResult, PlaylistSong, Playlist, Whitelist, Blacklist
from app.auth.decorators import spotify_token_required
from app.services.spotify_service import SpotifyService
from app.services.list_management_service import ListManagementService
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.utils.database import get_by_filter, get_all_by_filter
from app.services.whitelist_service import (
    add_to_whitelist,
    add_to_blacklist,
    ITEM_ADDED as WL_ITEM_ADDED,
    ITEM_ALREADY_EXISTS as WL_ITEM_ALREADY_EXISTS,
    ITEM_MOVED_FROM_BLACKLIST as WL_ITEM_MOVED_FROM_BLACKLIST,
    ERROR_OCCURRED as WL_ERROR_OCCURRED,
    ITEM_ADDED as BL_ITEM_ADDED,
    ITEM_ALREADY_EXISTS as BL_ITEM_ALREADY_EXISTS,
    ITEM_MOVED_FROM_WHITELIST as BL_ITEM_MOVED_FROM_WHITELIST,
    ERROR_OCCURRED as BL_ERROR_OCCURRED
)
from app.utils.cache import cache

# Constants
SONGS_PER_PAGE = 20

def invalidate_playlist_cache():
    """Utility function to invalidate playlist-related cache entries."""
    # Implementation for cache invalidation
    pass

def get_playlist_detail_data(playlist_id, user_id, page=1):
    """Get playlist detail data.
    
    Note: Caching disabled due to SQLAlchemy object serialization issues.
    The @cached decorator converts SongStatus objects to strings via json.dumps(default=str).
    """
    from app.services.spotify_service import SpotifyService
    
    # Get user's access token
    user = User.query.get(user_id)
    if not user or not user.ensure_token_valid():
        return None
    
    sp = SpotifyService(user.access_token)
    if not sp.sp:
        return None
    
    # OPTIMIZED: Pre-fetch whitelist and blacklist for the current user in bulk
    user_whitelisted_track_ids = {item.spotify_id for item in get_all_by_filter(Whitelist, user_id=user_id, item_type='track')}
    user_blacklisted_track_ids = {item.spotify_id for item in get_all_by_filter(Blacklist, user_id=user_id, item_type='track')}

    # Fetch basic playlist details
    playlist_data = sp.sp.playlist(playlist_id, fields="id,name,description,images,owner(display_name),tracks(total)")
    if not playlist_data:
        return None

    # Check if playlist exists in DB or add it
    playlist_in_db = get_by_filter(Playlist, spotify_id=playlist_id, owner_id=user_id)
    if not playlist_in_db:
        playlist_in_db = Playlist(
            spotify_id=playlist_data['id'],
            name=playlist_data['name'],
            owner_id=user_id,
            description=playlist_data.get('description', ''),
            image_url=playlist_data['images'][0]['url'] if playlist_data.get('images') else None
        )
        db.session.add(playlist_in_db)
        db.session.flush()  # Ensure playlist_in_db.id is available

    # Get paginated tracks from Spotify
    offset = (page - 1) * SONGS_PER_PAGE
    tracks_data = sp.sp.playlist_tracks(
        playlist_id, 
        fields="items(track(id,name,artists,album,duration_ms)),total,offset,limit", 
        offset=offset, 
        limit=SONGS_PER_PAGE
    )
    
    if not tracks_data:
        return None

    songs_with_status = []
    track_spotify_ids = []
    
    # Process tracks
    for item in tracks_data['items']:
        track = item.get('track')
        if not track or not track.get('id'):
            continue
            
        track_spotify_ids.append(track['id'])
        
        # Get or create song in database
        song_in_db = Song.query.filter_by(spotify_id=track['id']).first()
        if not song_in_db:
            song_in_db = Song(
                spotify_id=track['id'],
                title=track['name'],
                artist=', '.join([artist['name'] for artist in track['artists']]),
                album=track['album']['name'],
                duration_ms=track.get('duration_ms', 0)
            )
            db.session.add(song_in_db)
            db.session.flush()
        
        # Check if song is in playlist association
        playlist_song = PlaylistSong.query.filter_by(
            playlist_id=playlist_in_db.id, 
            song_id=song_in_db.id
        ).first()
        
        if not playlist_song:
            playlist_song = PlaylistSong(
                playlist_id=playlist_in_db.id,
                song_id=song_in_db.id,
                track_position=len(songs_with_status) + offset + 1
            )
            db.session.add(playlist_song)
        
        # Get analysis result
        analysis_result = AnalysisResult.query.filter_by(
            song_id=song_in_db.id, 
            status='completed'
        ).first()
        
        # Create song status object
        song_status = {
            'song': song_in_db,
            'track_id': track['id'],
            'is_whitelisted': track['id'] in user_whitelisted_track_ids,
            'is_blacklisted': track['id'] in user_blacklisted_track_ids,
            'analysis_result': analysis_result
        }
        
        songs_with_status.append(song_status)
    
    # Commit database changes
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error saving playlist data: {e}")
        db.session.rollback()
    
    # Calculate playlist analysis summary
    from app.blueprints.shared.utils import calculate_playlist_score
    playlist_analysis_summary = {
        'total_songs': len(songs_with_status),
        'analyzed_songs': sum(1 for s in songs_with_status if s['analysis_result']),
        'average_score': None
    }
    
    if playlist_analysis_summary['analyzed_songs'] > 0:
        scores = [s['analysis_result'].score for s in songs_with_status if s['analysis_result']]
        playlist_analysis_summary['average_score'] = sum(scores) / len(scores)
        
        # Update playlist overall score
        playlist_in_db.overall_alignment_score = playlist_analysis_summary['average_score']
        try:
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Error updating playlist score: {e}")
            db.session.rollback()
    
    # Create pagination object
    pagination = {
        'page': page,
        'per_page': SONGS_PER_PAGE,
        'total_pages': (tracks_data['total'] + SONGS_PER_PAGE - 1) // SONGS_PER_PAGE,
        'total_items': tracks_data['total'],
        'has_prev': page > 1,
        'has_next': offset + len(songs_with_status) < tracks_data['total'],
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if offset + len(songs_with_status) < tracks_data['total'] else None
    }
    
    return {
        'playlist': playlist_in_db,
        'songs_with_status': songs_with_status,
        'pagination': pagination,
        'playlist_analysis_summary': playlist_analysis_summary
    }

@playlist_bp.route('/sync-playlists', methods=['POST'])
@login_required
@spotify_token_required
def sync_playlists():
    """Trigger background playlist synchronization."""
    from app.services.playlist_sync_service import enqueue_playlist_sync, get_sync_status
    
    try:
        # Check if there's already an active sync job
        sync_status = get_sync_status(flask_login_current_user.id)
        
        if sync_status.get('has_active_sync', False):
            flash('Playlist synchronization is already in progress.', 'info')
            return redirect(url_for('core.dashboard'))
        
        # Enqueue the sync job
        job = enqueue_playlist_sync(flask_login_current_user.id)
        
        if job:
            # Invalidate dashboard cache since playlists will be updated
            invalidate_playlist_cache()
            
            # Set a session flag to track that we started a sync
            session['sync_in_progress'] = True
            session['sync_started_at'] = time.time()
            
            current_app.logger.info(f"Playlist sync job {job.id} enqueued for user {flask_login_current_user.id}")
            flash('Playlist synchronization started. This may take a few minutes.', 'success')
        else:
            current_app.logger.error(f"Failed to enqueue playlist sync for user {flask_login_current_user.id}")
            flash('Failed to start playlist synchronization. Please try again.', 'danger')
            
    except Exception as e:
        current_app.logger.exception(f"Error starting playlist sync for user {flask_login_current_user.id}: {e}")
        flash('An error occurred while starting playlist synchronization.', 'danger')
    
    return redirect(url_for('core.dashboard'))

@playlist_bp.route('/playlist/<string:playlist_id>')
@spotify_token_required
@login_required
def playlist_detail(playlist_id):
    """View detailed information about a specific playlist."""
    # Ensure token is valid before proceeding
    if not flask_login_current_user.ensure_token_valid():
        flash('Your Spotify session has expired. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

    try:
        user_id = flask_login_current_user.id
        page = request.args.get('page', 1, type=int)
        
        # Get cached playlist detail data
        playlist_data = get_playlist_detail_data(playlist_id, user_id, page)
        
        if not playlist_data:
            flash('Playlist not found or access denied.', 'danger')
            return redirect(url_for('core.dashboard'))
        
        return render_template('playlist_detail.html', 
                               playlist=playlist_data['playlist'], 
                               songs_with_status=playlist_data['songs_with_status'], 
                               pagination=playlist_data['pagination'], 
                               playlist_analysis_summary=playlist_data['playlist_analysis_summary'])
                               
    except spotipy.SpotifyException as e:
        current_app.logger.error(f"Spotify API error in playlist_detail for {playlist_id}: {e}")
        flash(f'Spotify API error: Could not load playlist details. Details: {str(e)}', 'danger')
        return redirect(url_for('core.dashboard'))
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error in playlist_detail for {playlist_id}: {e}", exc_info=True)
        flash(f'A database error occurred. Details: {str(e)}', 'danger')
        return redirect(url_for('core.dashboard'))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in playlist_detail for {playlist_id}: {e}", exc_info=True)
        flash(f'An unexpected error occurred. Type: {type(e).__name__}, Details: {str(e)}', 'danger')
        return redirect(url_for('core.dashboard'))

@playlist_bp.route('/playlist/<string:playlist_id>/update', methods=['POST'])
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
        return redirect(url_for('core.dashboard'))

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
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

    # Check if ordered_track_uris is empty or not provided
    if not ordered_track_uris:
        flash("No track information received to update the playlist.", "warning")
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

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
        return redirect(url_for('core.dashboard'))
    return redirect(url_for('playlist.playlist_detail', playlist_id=db_playlist.spotify_id))

@playlist_bp.route('/remove_song/<playlist_id>/<track_id>', methods=['POST'])
@login_required
def remove_song(playlist_id, track_id):
    """Remove a song from a playlist."""
    merged_user = db.session.merge(flask_login_current_user) # Apply same pattern here for consistency
    if not merged_user.ensure_token_valid(): # Use merged_user
        flash('Your Spotify session has expired. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

    sp = spotipy.Spotify(auth=merged_user.access_token) # Use merged_user
    redirect_url = url_for('core.dashboard') # Default redirect
    
    try:
        user_spotify_id = merged_user.spotify_id # Use merged_user
        if not user_spotify_id:
            user_info = sp.me()
            user_spotify_id = user_info['id']

        playlist_info = sp.playlist(playlist_id, fields='owner.id')
        playlist_owner_id = playlist_info['owner']['id']
        
        # If we have a valid playlist_id, errors should generally redirect back to its detail page
        redirect_url = url_for('playlist.playlist_detail', playlist_id=playlist_id)

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
                    return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
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
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
    except spotipy.SpotifyException as e:
        flash(f'Could not remove song from Spotify: {str(e)}', 'danger')
        current_app.logger.error(f"Spotify API error for user {merged_user.id} removing song: {e}") # Use merged_user
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
    except SQLAlchemyError as e:
        db.session.rollback()
        flash('A database error occurred while removing the song.', 'danger')
        current_app.logger.error(f"Database error removing song association: {e}")
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
    except Exception as e:
        flash('An unexpected error occurred.', 'danger')
        current_app.logger.error(f"Unexpected error in remove_song: {e}")
        # For truly unexpected errors, dashboard might be safer if playlist_id context is lost/corrupt
        return redirect(url_for('core.dashboard'))
    
    return redirect(redirect_url) # Use the determined redirect_url

@playlist_bp.route('/analyze_playlist_api/<string:playlist_id>', methods=['POST'])
@login_required
@spotify_token_required
def analyze_playlist_api(playlist_id):
    """
    API endpoint to analyze all songs in a playlist.
    This endpoint can be called via AJAX or regular form submission.
    """
    current_app.logger.info(f"analyze_playlist_api called for playlist_id: {playlist_id}")
    
    # Check if the playlist exists and belongs to the current user
    playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=flask_login_current_user.id).first()
    if not playlist:
        error_msg = "Playlist not found or you don't have permission to access it."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": error_msg}), 404
        flash(error_msg, 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
    
    try:
        # Call the unified analysis service to analyze the playlist
        analysis_service = UnifiedAnalysisService()
        analysis_summary = analysis_service.analyze_playlist_content(playlist_id, flask_login_current_user.id)

        if analysis_summary.get("error"):
            error_msg = analysis_summary["error"]
            current_app.logger.error(f"Error analyzing playlist {playlist_id}: {error_msg}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": error_msg}), 400
                
            flash(error_msg, 'error')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

        # Prepare success response
        success_msg = f"Analysis for playlist '{playlist.name}' initiated successfully."
        response_data = {
            "success": True, 
            "message": success_msg,
            "analysis_summary": analysis_summary,
            "playlist_id": playlist_id,
            "playlist_name": playlist.name
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(response_data)
            
        flash(success_msg, 'success')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        error_msg = f"An unexpected error occurred during playlist analysis: {str(e)}"
        current_app.logger.error(f"Exception in analyze_playlist_api for playlist {playlist_id}: {e}", exc_info=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": error_msg}), 500
            
        flash(error_msg, 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
