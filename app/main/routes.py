from flask import render_template, flash, redirect, url_for, request, current_app, jsonify, has_request_context, session, abort
from flask_login import login_required, current_user, current_user as flask_login_current_user
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
from app.utils.database import get_by_id, get_by_filter, get_all_by_filter, db_transaction  # SQLAlchemy 2.0 utilities
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select  # SQLAlchemy 2.0 imports
from ..services.list_management_service import ListManagementService
from . import main_bp
import json
import os
import requests
from app.services.song_status_service import SongStatus 
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone
from ..utils.analysis import SongAnalyzer  # For analyzing song lyrics
from ..utils.cache import cached, invalidate_playlist_cache, cache

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

PLAYLISTS_PER_PAGE = 25

def get_dashboard_data(user_id, page=1):
    """Get dashboard data for a user. 
    
    Note: Caching temporarily disabled due to SQLAlchemy object serialization issues.
    The @cached decorator converts Playlist objects to strings via json.dumps(default=str).
    """
    from ..services.playlist_sync_service import get_sync_status
    from ..models import AnalysisResult
    
    # Get sync status
    sync_status = get_sync_status(user_id)
    
    # OPTIMIZED: Get stats using efficient database queries instead of loading all data
    stats = {
        'total_playlists': 0,
        'total_songs': 0,
        'analyzed_songs': 0,
        'clean_playlists': 0
    }
    
    # Efficient query for total playlists count
    stats['total_playlists'] = db.session.query(Playlist).filter_by(owner_id=user_id).count()
    
    # Efficient query for total songs count using PlaylistSong JOIN
    stats['total_songs'] = db.session.query(Song).join(
        PlaylistSong, Song.id == PlaylistSong.song_id
    ).join(
        Playlist, PlaylistSong.playlist_id == Playlist.id
    ).filter(Playlist.owner_id == user_id).count()
    
    # Efficient query for analyzed songs count using PlaylistSong JOIN
    stats['analyzed_songs'] = db.session.query(Song).join(
        PlaylistSong, Song.id == PlaylistSong.song_id
    ).join(
        Playlist, PlaylistSong.playlist_id == Playlist.id
    ).join(
        AnalysisResult, Song.id == AnalysisResult.song_id
    ).filter(
        Playlist.owner_id == user_id,
        AnalysisResult.status == 'completed'
    ).count()
    
    # Efficient query for clean playlists count
    stats['clean_playlists'] = db.session.query(Playlist).filter(
        Playlist.owner_id == user_id,
        Playlist.overall_alignment_score >= 75.0
    ).count()
    
    # Get paginated playlists using optimized query
    playlists_query = Playlist.query.filter_by(owner_id=user_id)\
        .order_by(Playlist.updated_at.desc())
    
    # Get paginated playlists
    paginated_playlists = playlists_query.paginate(
        page=page,
        per_page=PLAYLISTS_PER_PAGE,
        error_out=False
    )
    
    playlists = paginated_playlists.items
    
    # OPTIMIZED: Only calculate scores for playlists on current page
    for playlist in playlists:
        if playlist.overall_alignment_score is None:
            calculate_playlist_score(playlist)
    
    # Commit any playlist score updates
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Error committing playlist score updates: {e}")
        db.session.rollback()
    
    # OPTIMIZED: Get last sync info efficiently
    last_sync_info = None
    most_recent_playlist = db.session.query(Playlist).filter_by(owner_id=user_id)\
        .order_by(Playlist.updated_at.desc()).first()
    
    if most_recent_playlist and most_recent_playlist.updated_at:
        last_sync_info = {
            'last_sync_at': most_recent_playlist.updated_at.isoformat()
        }
    
    # Create pagination object for template
    pagination = {
        'page': page,
        'per_page': PLAYLISTS_PER_PAGE,
        'total_pages': paginated_playlists.pages,
        'total_items': stats['total_playlists'],
        'has_prev': paginated_playlists.has_prev,
        'has_next': paginated_playlists.has_next,
        'prev_num': paginated_playlists.prev_num,
        'next_num': paginated_playlists.next_num
    }
    
    return {
        'playlists': playlists,
        'stats': stats,
        'sync_status': sync_status,
        'last_sync_info': last_sync_info,
        'pagination': pagination
    }

@main_bp.route('/dashboard')
@login_required
@spotify_token_required # Re-enabled
def dashboard():
    from ..services.background_analysis_service import BackgroundAnalysisService
    
    try:
        # Ensure token is valid before proceeding
        if not flask_login_current_user.ensure_token_valid():
            flash('Your Spotify session has expired. Please log in again.', 'warning')
            return redirect(url_for('auth.login'))
        
        user_id = flask_login_current_user.id
        
        # Handle clearing auto_sync_started flag
        if request.method == 'POST' and request.form.get('clear_auto_sync'):
            session.pop('auto_sync_started', None)
            return jsonify({"status": "success"})
        
        # Check for sync message in session
        sync_message = session.pop('sync_message', None)
        
        # Pagination logic
        page = request.args.get('page', 1, type=int)
        
        # Get cached dashboard data
        dashboard_data = get_dashboard_data(user_id, page)
        
        # Start background analysis if needed
        try:
            if BackgroundAnalysisService.should_start_background_analysis(user_id, min_interval_hours=1):
                background_result = BackgroundAnalysisService.start_background_analysis_for_user(user_id, max_songs_per_batch=25)
                current_app.logger.info(f"Background analysis started for user {user_id}: {background_result}")
        except Exception as e:
            current_app.logger.error(f"Error starting background analysis for user {user_id}: {e}")
        
        current_app.logger.debug(f"Dashboard for user {user_id}: {len(dashboard_data['playlists'])} playlists, sync_status: {dashboard_data['sync_status']}")
        
        return render_template('dashboard.html', 
                               playlists=dashboard_data['playlists'], 
                               stats=dashboard_data['stats'],
                               sync_status=dashboard_data['sync_status'],
                               sync_message=sync_message,
                               last_sync_info=dashboard_data['last_sync_info'],
                               pagination=dashboard_data['pagination'])
                               
    except Exception as e:
        current_app.logger.exception(f"Error loading dashboard for user {flask_login_current_user.id}: {e}")
        flash('Error loading dashboard. Please try refreshing the page.', 'danger')
        return render_template('dashboard.html', 
                               playlists=[], 
                               stats={
                                   'total_playlists': 0,
                                   'total_songs': 0,
                                   'analyzed_songs': 0,
                                   'clean_playlists': 0
                               },
                               sync_status={'has_active_sync': False})

@main_bp.route('/dashboard', methods=['POST'])
@login_required  
def dashboard_post():
    """Handle POST requests to dashboard (like clearing auto_sync flag)"""
    if request.form.get('clear_auto_sync'):
        session.pop('auto_sync_started', None)
        return jsonify({"status": "success"})
    
    # Redirect to GET dashboard for other POST requests
    return redirect(url_for('main.dashboard'))

@main_bp.route('/sync-playlists', methods=['POST'])
@login_required
@spotify_token_required
def sync_playlists():
    """Trigger background playlist synchronization."""
    from ..services.playlist_sync_service import enqueue_playlist_sync, get_sync_status
    
    try:
        # Check if there's already an active sync job
        sync_status = get_sync_status(flask_login_current_user.id)
        
        if sync_status.get('has_active_sync', False):
            flash('Playlist synchronization is already in progress.', 'info')
            return redirect(url_for('main.dashboard'))
        
        # Enqueue the sync job
        job = enqueue_playlist_sync(flask_login_current_user.id)
        
        if job:
            # Invalidate dashboard cache since playlists will be updated
            invalidate_playlist_cache()
            
            current_app.logger.info(f"Playlist sync job {job.id} enqueued for user {flask_login_current_user.id}")
            flash('Playlist synchronization started. This may take a few minutes.', 'success')
        else:
            current_app.logger.error(f"Failed to enqueue playlist sync for user {flask_login_current_user.id}")
            flash('Failed to start playlist synchronization. Please try again.', 'danger')
            
    except Exception as e:
        current_app.logger.exception(f"Error starting playlist sync for user {flask_login_current_user.id}: {e}")
        flash('An error occurred while starting playlist synchronization.', 'danger')
    
    return redirect(url_for('main.dashboard'))

@main_bp.route('/api/sync-status')
@login_required
def api_sync_status():
    """API endpoint to check playlist sync status."""
    from ..services.playlist_sync_service import get_sync_status
    
    try:
        user_id = flask_login_current_user.id
        sync_status = get_sync_status(user_id)
        return jsonify(sync_status)
    except Exception as e:
        try:
            user_id = flask_login_current_user.id if flask_login_current_user.is_authenticated else 'unknown'
        except:
            user_id = 'unknown'
        current_app.logger.exception(f"Error checking sync status for user {user_id}: {e}")
        return jsonify({
            "user_id": user_id,
            "has_active_sync": False,
            "error": "Failed to check sync status"
        }), 500

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

def get_playlist_detail_data(playlist_id, user_id, page=1):
    """Get playlist detail data.
    
    Note: Caching disabled due to SQLAlchemy object serialization issues.
    The @cached decorator converts SongStatus objects to strings via json.dumps(default=str).
    """
    from ..services.spotify_service import SpotifyService
    
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

    playlist_score_to_display = getattr(playlist_in_db, 'overall_score', None)
    if playlist_score_to_display is None and hasattr(playlist_in_db, 'score') and playlist_in_db.score is not None:
         playlist_score_to_display = playlist_in_db.score
    
    # Get paginated tracks
    offset = (page - 1) * SONGS_PER_PAGE
    tracks_response = sp.sp.playlist_tracks(
        playlist_id, 
        offset=offset, 
        limit=SONGS_PER_PAGE,
        fields="items(track(id,name,artists(name),album(name),external_urls)),next,previous,total"
    )
    
    tracks = tracks_response.get('items', [])
    total_tracks_from_spotify = tracks_response.get('total', 0)
    total_pages = (total_tracks_from_spotify + SONGS_PER_PAGE - 1) // SONGS_PER_PAGE
    
    # Process tracks and get analysis data
    songs_with_status = []
    for track_item in tracks:
        track = track_item.get('track')
        if not track or not track.get('id'):
            continue
            
        track_id = track['id']
        
        # Check if song exists in database
        song_in_db = get_by_filter(Song, spotify_id=track_id)
        
        # Get analysis result if song exists
        analysis_result = None
        if song_in_db:
            analysis_result = get_by_filter(AnalysisResult, song_id=song_in_db.id, status='completed')
        
        # Determine status using SongStatus service
        is_whitelisted = track_id in user_whitelisted_track_ids
        is_blacklisted = track_id in user_blacklisted_track_ids
        
        # Create SongStatus instance to get proper status (only if song exists in DB)
        status_service = None
        if song_in_db:
            status_service = SongStatus(
                song=song_in_db,
                analysis_result=analysis_result,
                is_whitelisted=is_whitelisted,
                is_blacklisted=is_blacklisted,
                is_preferred=False
            )
        
        # For template compatibility, create a simple status object
        if is_whitelisted:
            status = 'whitelisted'
        elif is_blacklisted:
            status = 'blacklisted'
        elif analysis_result:
            if analysis_result.concern_level in ['extreme', 'high']:
                status = 'flagged'
            else:
                status = 'clean'
        else:
            status = 'not_analyzed'
        
        # Create a song object that matches what the template expects
        # Handle podcast episodes where artist names might be None
        artists = track.get('artists', [])
        artist_names = [artist['name'] for artist in artists if artist.get('name') is not None]
        artist_str = ', '.join(artist_names) if artist_names else 'Unknown Artist'
        
        # Use stored album art URL if song exists in database, otherwise get from Spotify API
        album_art_url = None
        if song_in_db and song_in_db.album_art_url:
            album_art_url = song_in_db.album_art_url
        elif track.get('album', {}).get('images'):
            album_art_url = track['album']['images'][0].get('url')
        
        song_for_template = {
            'id': song_in_db.id if song_in_db else None,
            'title': track.get('name', 'Unknown Title'),
            'artist': artist_str,
            'album': track.get('album', {}).get('name', 'Unknown Album') if track.get('album') else 'Unknown Album',
            'spotify_id': track_id,
            'album_art_url': album_art_url
        }
        
        songs_with_status.append({
            'track': track,  # Keep original track data for reference
            'song': song_for_template,  # Add song data in expected format
            'song_db_id': song_in_db.id if song_in_db else None,
            'analysis_result': analysis_result,
            'status': status,
            'status_service': status_service,  # Will be None if song doesn't exist in DB
            'is_whitelisted': is_whitelisted,
            'is_blacklisted': is_blacklisted
        })
    
    # Calculate playlist analysis summary
    try:
        playlist_analysis_summary = {
            'total_songs': total_tracks_from_spotify,
            'analyzed_songs': 0,
            'analysis_percentage': 0,
            'overall_score': playlist_score_to_display,
            'concern_levels': {'extreme': 0, 'high': 0, 'medium': 0, 'low': 0},
            'clean_songs': 0,
            'problem_songs': 0
        }
        
        # Count analysis results for this playlist
        if playlist_in_db:
            analysis_results = db.session.query(AnalysisResult).join(
                Song, AnalysisResult.song_id == Song.id
            ).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).filter(
                PlaylistSong.playlist_id == playlist_in_db.id,
                AnalysisResult.status == 'completed'
            ).all()
            
            playlist_analysis_summary['analyzed_songs'] = len(analysis_results)
            
            if total_tracks_from_spotify > 0:
                playlist_analysis_summary['analysis_percentage'] = round(
                    (len(analysis_results) / total_tracks_from_spotify) * 100, 1
                )
            
            # Count by concern level
            for result in analysis_results:
                concern_level = result.concern_level.lower()
                if concern_level in playlist_analysis_summary['concern_levels']:
                    playlist_analysis_summary['concern_levels'][concern_level] += 1
                
                if concern_level in ['extreme', 'high']:
                    playlist_analysis_summary['problem_songs'] += 1
                else:
                    playlist_analysis_summary['clean_songs'] += 1
    
    except Exception as e:
        current_app.logger.error(f"Error calculating playlist analysis summary: {e}")
        playlist_analysis_summary = {
            'total_songs': total_tracks_from_spotify,
            'analyzed_songs': 0,
            'analysis_percentage': 0,
            'overall_score': None,
            'concern_levels': {'extreme': 0, 'high': 0, 'medium': 0, 'low': 0},
            'clean_songs': 0,
            'problem_songs': 0
        }

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
    
    return {
        'playlist': {
            'id': playlist_data['id'],
            'name': playlist_data['name'],
            'description': playlist_data.get('description', ''),
            'images': playlist_data.get('images', []),
            'owner': playlist_data.get('owner', {}),
            'tracks': {'total': total_tracks_from_spotify}
        },
        'songs_with_status': songs_with_status,
        'pagination': pagination,
        'playlist_analysis_summary': playlist_analysis_summary
    }

@main_bp.route('/playlist/<string:playlist_id>')
@spotify_token_required
@login_required
def playlist_detail(playlist_id):
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
            return redirect(url_for('main.dashboard'))
        
        return render_template('playlist_detail.html', 
                               playlist=playlist_data['playlist'], 
                               songs_with_status=playlist_data['songs_with_status'], 
                               pagination=playlist_data['pagination'], 
                               playlist_analysis_summary=playlist_data['playlist_analysis_summary'])
                               
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
    song = get_by_id(Song, song_db_id)

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
    song = get_by_id(Song, song_db_id)

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

@main_bp.route('/songs/<int:song_id>')
@main_bp.route('/songs/<int:song_id>/')
@login_required
@spotify_token_required
def song_detail(song_id):
    """Display detailed information about a specific song."""
    current_app.logger.info(f"Accessing song detail for song_id: {song_id}")
    
    # Get the playlist_id from query parameters if provided
    playlist_id = request.args.get('playlist_id')
    
    try:
        # Get the song
        song = get_by_id(Song, song_id)
        if not song:
            abort(404)
        current_app.logger.info(f"Found song: {song.title} by {song.artist}")
        
        # Get the analysis result
        analysis_result_db = AnalysisResult.query.filter_by(song_id=song.id).first()
        current_app.logger.info(f"Analysis result found: {analysis_result_db is not None}")
        
        # Build analysis data for template
        analysis = None
        if analysis_result_db:
            # Helper function to safely parse JSON fields
            def safe_json_parse(field_value, default=None):
                if field_value is None:
                    return default or []
                if isinstance(field_value, str):
                    try:
                        import json
                        return json.loads(field_value)
                    except (json.JSONDecodeError, ValueError):
                        return default or []
                return field_value
            
            analysis = {
                'score': analysis_result_db.score,
                'concern_level': analysis_result_db.concern_level,
                'explanation': analysis_result_db.explanation,
                'themes': safe_json_parse(analysis_result_db.themes, {}),
                'concerns': safe_json_parse(analysis_result_db.concerns, []),
                'purity_flags_triggered': safe_json_parse(analysis_result_db.purity_flags_details, []),
                'positive_themes_identified': safe_json_parse(analysis_result_db.positive_themes_identified, []),
                'biblical_themes': safe_json_parse(analysis_result_db.biblical_themes, []),
                'supporting_scripture': safe_json_parse(analysis_result_db.supporting_scripture, {})
            }
        
        # Use song lyrics if available
        lyrics_to_render = song.lyrics or "Lyrics not available"
        
        # Transform concerns list to purity flags format for template compatibility
        purity_flags_for_template = {}
        if analysis_result_db and analysis_result_db.concerns:
            for i, concern in enumerate(analysis_result_db.concerns):
                purity_flags_for_template[f"flag_{i}"] = {
                    "flag": concern,
                    "description": f"Concern identified: {concern}"
                }
        
        # Check if song is whitelisted
        is_whitelisted = False
        if flask_login_current_user.is_authenticated:
            whitelist_entry = Whitelist.query.filter_by(
                user_id=flask_login_current_user.id,
                spotify_id=song.spotify_id,
                item_type='song'
            ).first()
            is_whitelisted = whitelist_entry is not None
        
        # Get scripture mappings for themes
        scripture_mappings = SCRIPTURE_MAPPINGS
        
        current_app.logger.info(f"Rendering song detail template with analysis: {analysis is not None}")
        
        return render_template('song_detail.html',
                             song=song,
                             analysis=analysis,
                             lyrics=lyrics_to_render,
                             purity_flags=purity_flags_for_template,
                             is_whitelisted=is_whitelisted,
                             scripture_mappings=scripture_mappings,
                             playlist_spotify_id=playlist_id)
                             
    except Exception as e:
        current_app.logger.error(f"Error in song_detail route: {str(e)}", exc_info=True)
        flash(f"Error loading song details: {str(e)}", 'error')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/analyze_playlist_api/<string:playlist_id>', methods=['POST'])
@login_required
@spotify_token_required
def analyze_playlist_api(playlist_id):
    """
    API endpoint to analyze all songs in a playlist.
    This endpoint can be called via AJAX or regular form submission.
    """
    current_app.logger.info(f"analyze_playlist_api called for playlist_id: {playlist_id}")
    
    # Check if the playlist exists and belongs to the current user
    playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=current_user.id).first()
    if not playlist:
        error_msg = "Playlist not found or you don't have permission to access it."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": error_msg}), 404
        flash(error_msg, 'error')
        return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
    
    try:
        # Call the service function to analyze the playlist
        analysis_summary = analyze_playlist_content(playlist_id, current_user.id)

        if analysis_summary.get("error"):
            error_msg = analysis_summary["error"]
            current_app.logger.error(f"Error analyzing playlist {playlist_id}: {error_msg}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": error_msg}), 400
                
            flash(error_msg, 'error')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))

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
        return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        error_msg = f"An unexpected error occurred during playlist analysis: {str(e)}"
        current_app.logger.error(f"Exception in analyze_playlist_api for playlist {playlist_id}: {e}", exc_info=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": error_msg}), 500
            
        flash(error_msg, 'error')
        return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))

@main_bp.route('/api/songs/<int:song_id>/analysis-status', methods=['GET'])
@login_required
def get_song_analysis_status(song_id):
    """
    Endpoint to check the status of a song analysis.
    
    Query Parameters:
        task_id: Optional task ID to check job status
    """
    try:
        # Get the song with proper ownership check
        song = get_by_id(Song, song_id)
        if not song:
            return jsonify({
                'success': False,
                'error': 'song_not_found',
                'message': 'Song not found'
            }), 404
            
        # Check if the song belongs to a playlist owned by the current user
        user_playlist_ids = [p.id for p in current_user.playlists]
        song_playlist_ids = [assoc.playlist_id for assoc in song.playlist_associations]
        
        if not song_playlist_ids or not any(pid in user_playlist_ids for pid in song_playlist_ids):
            return jsonify({
                'success': False,
                'error': 'unauthorized',
                'message': 'You do not have permission to view this song'
            }), 403
            
        task_id = request.args.get('task_id')
        if task_id:
            job = current_app.task_queue.fetch_job(task_id)
            if job:
                if job.is_failed:
                    return jsonify({
                        'success': False,
                        'error': 'analysis_failed',
                        'message': f'Analysis failed: {str(job.exc_info)}',
                        'song_id': song_id
                    })
                elif job.is_finished:
                    # Refresh the song to get updated analysis
                    db.session.refresh(song)
                    # Include both christian_ and non-christian fields for backward compatibility
                    return jsonify({
                        'success': True,
                        'completed': True,
                        'song_id': song_id,
                        'analysis': {
                            'score': song.score,
                            'christian_score': song.score,  # Add christian_ prefixed fields
                            'concern_level': song.concern_level,
                            'christian_concern_level': song.concern_level,  # Add christian_ prefixed fields
                            'updated_at': song.updated_at.isoformat() if song.updated_at else None
                        }
                    })
                else:
                    # Job is still running
                    return jsonify({
                        'success': True,
                        'in_progress': True,
                        'message': 'Analysis in progress...',
                        'song_id': song_id
                    })
        
        # If no task_id or job not found, return current song analysis status
        if song.score is not None:
            # Include both christian_ and non-christian fields for backward compatibility
            analysis_data = {
                'score': song.score,
                'christian_score': song.score,  # Add christian_ prefixed fields
                'concern_level': song.concern_level,
                'christian_concern_level': song.concern_level,  # Add christian_ prefixed fields
                'updated_at': song.updated_at.isoformat() if song.updated_at else None
            }
        else:
            analysis_data = None
            
        return jsonify({
            'success': True,
            'song_id': song_id,
            'has_analysis': song.score is not None,
            'analysis': analysis_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_song_analysis_status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'status_check_error',
            'message': f'Failed to check analysis status: {str(e)}'
        }), 500

@main_bp.route('/api/playlists/<string:playlist_id>/analysis-status/', methods=['GET'])
@main_bp.route('/api/playlists/<string:playlist_id>/analysis-status', methods=['GET'])  # For backward compatibility
@login_required
def get_analysis_status(playlist_id):
    """
    Endpoint to check the status of playlist or song analysis.
    Returns detailed information about the analysis progress.
    
    Query Parameters:
        task_id: Optional task ID to check job status
        song_id: Optional song ID to check status for a specific song
    """
    try:
        if not playlist_id:
            current_app.logger.error("Missing playlist_id in get_analysis_status")
            return jsonify({
                'success': False,
                'error': 'missing_playlist_id',
                'message': 'Playlist ID is required'
            }), 400
            
        task_id = request.args.get('task_id')
        song_id = request.args.get('song_id')
        current_app.logger.info(f"Checking analysis status for playlist {playlist_id}, task_id: {task_id}, song_id: {song_id}")
        
        # If checking status for a specific song
        if song_id:
            song = get_by_id(Song, song_id)
            if not song:
                abort(404)
                
            # If song has a score, return it
            if song.score is not None:
                return jsonify({
                    'success': True,
                    'completed': True,
                    'song_id': song_id,
                    'analysis': {
                        'score': song.score,
                        'concern_level': song.concern_level,
                        'updated_at': song.updated_at.isoformat() if song.updated_at else None
                    }
                })
            
            # If no score but we have a task_id, check job status
            if task_id:
                job = current_app.task_queue.fetch_job(task_id)
                if job:
                    if job.is_failed:
                        error_msg = f'Analysis failed: {str(job.exc_info)}'
                        current_app.logger.error(f"Job {task_id} failed: {error_msg}")
                        return jsonify({
                            'success': False,
                            'error': 'analysis_failed',
                            'message': error_msg,
                            'song_id': song_id
                        }), 500
                    elif job.is_finished:
                        # Refresh the song to get updated analysis
                        db.session.refresh(song)
                        if song.score is not None:
                            return jsonify({
                                'success': True,
                                'completed': True,
                                'song_id': song_id,
                                'analysis': {
                                    'score': song.score,
                                    'concern_level': song.concern_level,
                                    'updated_at': song.updated_at.isoformat() if song.updated_at else None
                                }
                            })
                    
                    # Job is still running
                    return jsonify({
                        'success': True,
                        'in_progress': True,
                        'message': 'Analysis in progress...',
                        'song_id': song_id
                    })
                
            # No task_id or job not found
            return jsonify({
                'success': True,
                'song_id': song_id,
                'has_analysis': song.score is not None,
                'analysis': {
                    'score': song.score,
                    'concern_level': song.concern_level,
                    'updated_at': song.updated_at.isoformat() if song.updated_at else None
                } if song.score is not None else None
            })
        
        # If no song_id but we have a task_id, check job status for the playlist
        if task_id:
            try:
                job = current_app.task_queue.fetch_job(task_id)
                if job:
                    if job.is_failed:
                        error_msg = f'Analysis failed: {str(job.exc_info)}'
                        current_app.logger.error(f"Job {task_id} failed: {error_msg}")
                        return jsonify({
                            'success': False,
                            'error': 'analysis_failed',
                            'message': error_msg,
                            'playlist_id': playlist_id
                        }), 500
                    elif job.is_finished:
                        current_app.logger.info(f"Job {task_id} finished successfully")
                        # Job is done, continue with status check
                        pass
                    else:
                        # Job is still running
                        progress = job.meta.get('progress', 0) if job.meta else 0
                        current_song = job.meta.get('current_song', '') if job.meta else ''
                        current_app.logger.debug(f"Job {task_id} in progress: {progress}%, current_song: {current_song}")
                        
                        return jsonify({
                            'success': True,
                            'in_progress': True,
                            'message': 'Analysis in progress...',
                            'progress': progress,
                            'current_song': current_song,
                            'playlist_id': playlist_id,
                            'task_id': task_id
                        })
            except Exception as e:
                error_msg = f"Error checking job status for task {task_id}: {str(e)}"
                current_app.logger.error(error_msg, exc_info=True)
                # Continue with regular status check if job check fails
        
        # Get the playlist with proper ownership check
        playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=current_user.id).first()
        if not playlist:
            return jsonify({
                'success': False,
                'error': 'Playlist not found or access denied',
                'message': 'The requested playlist could not be found or you do not have permission to access it.'
            }), 404
        
        # Get all songs in the playlist
        songs = Song.query.join(PlaylistSong).filter(PlaylistSong.playlist_id == playlist.id).all()
        
        if not songs:
            return jsonify({
                'success': True,
                'completed': True,
                'message': 'No songs found in this playlist.',
                'progress': 100,
                'analyzed': 0,
                'total': 0,
                'playlist_id': playlist_id,
                'playlist_name': playlist.name
            })
        
        # Count analyzed songs and gather analysis details
        analyzed_count = 0
        analysis_details = []
        
        for song in songs:
            analysis_result = song.analysis_results.first()
            if analysis_result:
                analyzed_count += 1
                analysis_details.append({
                    'song_id': song.id,
                    'title': song.title,
                    'artist': song.artist,
                    'analyzed': True,
                    'concern_level': analysis_result.concern_level,
                    'score': analysis_result.score,
                    'last_analyzed': song.last_analyzed.isoformat() if song.last_analyzed else None
                })
            else:
                analysis_details.append({
                    'song_id': song.id,
                    'title': song.title,
                    'artist': song.artist,
                    'analyzed': False
                })
        
        total_songs = len(songs)
        progress = int((analyzed_count / total_songs) * 100) if total_songs > 0 else 0
        completed = analyzed_count == total_songs
        
        # Get the most recent analysis timestamp
        last_analyzed = max(
            (song.last_analyzed for song in songs if song.last_analyzed is not None),
            default=None
        )
        
        response_data = {
            'success': True,
            'completed': completed,
            'in_progress': not completed and analyzed_count > 0,
            'progress': progress,
            'analyzed': analyzed_count,
            'total': total_songs,
            'message': f'Analyzed {analyzed_count} of {total_songs} songs ({progress}%)',
            'playlist_id': playlist_id,
            'playlist_name': playlist.name,
            'last_analyzed': last_analyzed.isoformat() if last_analyzed else None,
            'analysis_details': analysis_details
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting analysis status for playlist {playlist_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'failed_to_get_status',
            'message': f'Failed to get analysis status: {str(e)}',
            'playlist_id': playlist_id
        }), 500

@main_bp.route('/api/songs/<int:song_id>/analyze/', methods=['POST'])
@main_bp.route('/api/songs/<int:song_id>/analyze', methods=['POST'])  # For backward compatibility
@login_required
@spotify_token_required
def analyze_song_route(song_id):
    """Route handler for analyzing/re-analyzing a single song."""
    current_app.logger.info(f"Starting analysis for song {song_id}")
    
    try:
        # Get the song
        song = get_by_id(Song, song_id)
        if not song:
            abort(404)
        current_app.logger.info(f"Found song: {song.title} by {song.artist}")
        
        # Enqueue the analysis task
        from ..services.analysis_service import perform_christian_song_analysis_and_store
        job = perform_christian_song_analysis_and_store(song_id, current_user.id)
        
        if job:
            current_app.logger.info(f"Song analysis task enqueued for song {song_id} with job ID: {job.id}")
            return jsonify({
                'success': True,
                'message': f'Analysis started for "{song.title}"',
                'job_id': job.id,
                'song_id': song_id
            })
        else:
            current_app.logger.error(f"Failed to enqueue analysis task for song {song_id}")
            return jsonify({
                'success': False,
                'error': 'Failed to start analysis',
                'message': 'Unable to enqueue analysis task'
            }), 500
            
    except Exception as e:
        current_app.logger.exception(f"Error in analyze_song_route for song {song_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'analysis_error',
            'message': f'Error starting analysis: {str(e)}'
        }), 500

@main_bp.route('/api/songs/<int:song_id>/reanalyze/', methods=['POST'])
@main_bp.route('/api/songs/<int:song_id>/reanalyze', methods=['POST'])  # For backward compatibility
@login_required
@spotify_token_required  
def reanalyze_song_route(song_id):
    """Route handler for re-analyzing a single song (alias for analyze_song_route)."""
    return analyze_song_route(song_id)

@main_bp.route('/api/playlists/<string:playlist_id>/analyze-unanalyzed/', methods=['POST'])
@main_bp.route('/api/playlists/<string:playlist_id>/analyze-unanalyzed', methods=['POST'])  # For backward compatibility
@login_required
@spotify_token_required
def analyze_unanalyzed_songs_route(playlist_id):
    """Route handler for analyzing unanalyzed songs in a playlist."""
    if not playlist_id:
        current_app.logger.error("Missing playlist_id in analyze_unanalyzed_songs_route")
        return jsonify({
            'success': False,
            'error': 'missing_playlist_id',
            'message': 'Playlist ID is required'
        }), 400
        
    current_app.logger.info(f"Starting analysis for unanalyzed songs in playlist {playlist_id}")
    try:
        # Get the user ID from the current user and pass it explicitly
        user_id = flask_login_current_user.id
        return analyze_unanalyzed_songs(playlist_id, user_id=user_id)
    except Exception as e:
        current_app.logger.error(f"Error in analyze_unanalyzed_songs_route: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'analysis_error',
            'message': f'Failed to start analysis: {str(e)}'
        }), 500

@main_bp.route('/api/playlists/<string:playlist_id>/reanalyze-all/', methods=['POST'])
@main_bp.route('/api/playlists/<string:playlist_id>/reanalyze-all', methods=['POST'])  # For backward compatibility
@login_required
@spotify_token_required
def reanalyze_all_songs_route(playlist_id):
    """Route handler for re-analyzing ALL songs in a playlist (not just unanalyzed ones)."""
    if not playlist_id:
        current_app.logger.error("Missing playlist_id in reanalyze_all_songs_route")
        return jsonify({
            'success': False,
            'error': 'missing_playlist_id',
            'message': 'Playlist ID is required'
        }), 400
        
    current_app.logger.info(f"Starting re-analysis for ALL songs in playlist {playlist_id}")
    try:
        # Get the user ID from the current user and pass it explicitly
        user_id = flask_login_current_user.id
        return reanalyze_all_songs(playlist_id, user_id=user_id)
    except Exception as e:
        current_app.logger.error(f"Error in reanalyze_all_songs_route: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'analysis_error',
            'message': f'Failed to start re-analysis: {str(e)}'
        }), 500

def analyze_unanalyzed_songs(playlist_id, user_id=None):
    """Analyze only the unanalyzed songs in a playlist.
    
    Args:
        playlist_id (str): The Spotify ID of the playlist to analyze
        user_id (int, optional): The ID of the user who owns the playlist. 
                              Required when called from a background job.
    """
    current_app.logger.info(f"analyze_unanalyzed_songs called for playlist_id: {playlist_id}, user_id: {user_id}")
    
    try:
        # Get the user ID from the current user if not provided
        if user_id is None:
            if not has_request_context() or not hasattr(flask_login_current_user, 'id') or not flask_login_current_user.is_authenticated:
                current_app.logger.error("No user_id provided and no authenticated current_user available")
                if has_request_context() and request and hasattr(request, 'is_json') and request.is_json:
                    return jsonify({"error": "User authentication required"}), 401
                return "User authentication required", 401
            user_id = flask_login_current_user.id
            
        # Get the playlist from the database
        playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=user_id).first()
        if not playlist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": "Playlist not found or access denied"}), 404
            flash("Playlist not found or access denied", 'error')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
            
        # Get all songs in the playlist that don't have analysis results
        unanalyzed_songs = Song.query.join(
            PlaylistSong, 
            Song.id == PlaylistSong.song_id
        ).filter(
            PlaylistSong.playlist_id == playlist.id,
            ~Song.analysis_results.any()
        ).all()
        
        total_songs = len(unanalyzed_songs)
        analyzed_count = 0
        
        if total_songs == 0:
            response_data = {
                "success": True, 
                "message": "No unanalyzed songs found in the playlist.",
                "analyzed_count": 0,
                "total_songs": 0
            }
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(response_data)
            flash(response_data["message"], 'info')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
        
        # Generate a unique task ID for this batch of analyses
        import uuid
        batch_id = str(uuid.uuid4())
        current_app.logger.info(f"Starting batch analysis with ID: {batch_id}")
        
        # Process each unanalyzed song
        for i, song in enumerate(unanalyzed_songs, 1):
            current_app.logger.info(f"Starting analysis for song {song.id} for user {user_id}")
            
            try:
                # Call the analysis service using the background task
                job = perform_christian_song_analysis_and_store(song.id, user_id=user_id)
                if job:
                    # The analysis is happening in the background
                    analyzed_count += 1
                    job_id = job.get_id() if hasattr(job, 'get_id') else str(job.id) if hasattr(job, 'id') else 'unknown'
                    current_app.logger.info(f"Started analysis job {job_id} for song {song.id}")
                    
                    # Update the song's last_analyzed timestamp
                    song.last_analyzed = datetime.utcnow()
                    db.session.add(song)
                    
                    # Commit every 5 songs to avoid long transactions
                    if i % 5 == 0 or i == len(unanalyzed_songs):
                        db.session.commit()
                        current_app.logger.debug(f"Committed database changes after song {i}")
                else:
                    current_app.logger.warning(f"Analysis job for song {song.id} was not created")
                    
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error analyzing song {song.id if song else 'unknown'}: {e}", exc_info=True)
                # Continue with the next song even if one fails
                continue
        
        # Update the playlist's last analyzed timestamp
        try:
            playlist.last_analyzed_at = datetime.utcnow()
            db.session.commit()
            
            response_data = {
                "success": True,
                "message": f"Successfully started analysis for {analyzed_count} out of {total_songs} unanalyzed songs.",
                "analyzed_count": analyzed_count,
                "total_songs": total_songs,
                "status": "started",
                "task_id": batch_id,  # Return the batch ID as task_id
                "progress": 0,
                "current_song": "Starting analysis..."
            }
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(response_data)
                
            flash(response_data["message"], 'success' if analyzed_count > 0 else 'info')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating playlist status: {e}", exc_info=True)
            error_message = f"Analysis completed with {analyzed_count} songs analyzed, but failed to update playlist status."
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    "success": analyzed_count > 0,
                    "message": error_message,
                    "analyzed_count": analyzed_count,
                    "total_songs": total_songs
                }), 207  # 207 Multi-Status
                
            flash(error_message, 'warning' if analyzed_count > 0 else 'error')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in analyze_unanalyzed_songs for playlist {playlist_id}: {e}", exc_info=True)
        error_message = f"An error occurred while analyzing songs: {str(e)}"
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": error_message}), 500
            
        flash(error_message, 'error')
        return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))

def reanalyze_all_songs(playlist_id, user_id=None):
    """Re-analyze all songs in a playlist.
    
    Args:
        playlist_id (str): The Spotify ID of the playlist to re-analyze
        user_id (int, optional): The ID of the user who owns the playlist. 
                              Required when called from a background job.
    """
    current_app.logger.info(f"reanalyze_all_songs called for playlist_id: {playlist_id}, user_id: {user_id}")
    
    try:
        # Get the user ID from the current user if not provided
        if user_id is None:
            if not has_request_context() or not hasattr(flask_login_current_user, 'id') or not flask_login_current_user.is_authenticated:
                current_app.logger.error("No user_id provided and no authenticated current_user available")
                if has_request_context() and request and hasattr(request, 'is_json') and request.is_json:
                    return jsonify({"error": "User authentication required"}), 401
                return "User authentication required", 401
            user_id = flask_login_current_user.id
            
        # Get the playlist from the database
        playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=user_id).first()
        if not playlist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": "Playlist not found or access denied"}), 404
            flash("Playlist not found or access denied", 'error')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
            
        # Get all songs in the playlist
        songs = Song.query.join(PlaylistSong).filter(PlaylistSong.playlist_id == playlist.id).all()
        
        total_songs = len(songs)
        analyzed_count = 0
        
        if total_songs == 0:
            response_data = {
                "success": True, 
                "message": "No songs found in this playlist.",
                "analyzed_count": 0,
                "total_songs": 0
            }
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(response_data)
            flash(response_data["message"], 'info')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
        
        # Generate a unique task ID for this batch of analyses
        import uuid
        batch_id = str(uuid.uuid4())
        current_app.logger.info(f"Starting batch analysis with ID: {batch_id}")
        
        # Process each song
        for i, song in enumerate(songs, 1):
            current_app.logger.info(f"Starting analysis for song {song.id} for user {user_id}")
            
            try:
                # Call the analysis service using the background task
                job = perform_christian_song_analysis_and_store(song.id, user_id=user_id)
                if job:
                    # The analysis is happening in the background
                    analyzed_count += 1
                    job_id = job.get_id() if hasattr(job, 'get_id') else str(job.id) if hasattr(job, 'id') else 'unknown'
                    current_app.logger.info(f"Started analysis job {job_id} for song {song.id}")
                    
                    # Update the song's last_analyzed timestamp
                    song.last_analyzed = datetime.utcnow()
                    db.session.add(song)
                    
                    # Commit every 5 songs to avoid long transactions
                    if i % 5 == 0 or i == len(songs):
                        db.session.commit()
                        current_app.logger.debug(f"Committed database changes after song {i}")
                else:
                    current_app.logger.warning(f"Analysis job for song {song.id} was not created")
                    
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error analyzing song {song.id if song else 'unknown'}: {e}", exc_info=True)
                # Continue with the next song even if one fails
                continue
        
        # Update the playlist's last analyzed timestamp
        try:
            playlist.last_analyzed_at = datetime.utcnow()
            db.session.commit()
            
            response_data = {
                "success": True,
                "message": f"Successfully started re-analysis for {analyzed_count} out of {total_songs} songs.",
                "analyzed_count": analyzed_count,
                "total_songs": total_songs,
                "status": "started",
                "task_id": batch_id,  # Return the batch ID as task_id
                "progress": 0,
                "current_song": "Starting re-analysis..."
            }
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(response_data)
                
            flash(response_data["message"], 'success' if analyzed_count > 0 else 'info')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating playlist status: {e}", exc_info=True)
            error_message = f"Re-analysis completed with {analyzed_count} songs analyzed, but failed to update playlist status."
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    "success": analyzed_count > 0,
                    "message": error_message,
                    "analyzed_count": analyzed_count,
                    "total_songs": total_songs
                }), 207  # 207 Multi-Status
                
            flash(error_message, 'warning' if analyzed_count > 0 else 'error')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in reanalyze_all_songs for playlist {playlist_id}: {e}", exc_info=True)
        error_message = f"An error occurred while re-analyzing songs: {str(e)}"
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "message": error_message}), 500
            
        flash(error_message, 'error')
        return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))

# User Settings and List Management Routes

@main_bp.route('/settings')
@login_required
def user_settings():
    """Display user settings page"""
    return render_template('user_settings.html', user=flask_login_current_user)

@main_bp.route('/settings', methods=['POST'])
@login_required
def update_user_settings():
    """Update user settings"""
    try:
        # Get form data
        display_name = request.form.get('display_name', '').strip()
        email = request.form.get('email', '').strip()
        
        # Basic validation
        if not display_name:
            flash('Display name is required.', 'danger')
            return render_template('user_settings.html', user=flask_login_current_user)
        
        if email and '@' not in email:
            flash('Invalid email address.', 'danger')
            return render_template('user_settings.html', user=flask_login_current_user)
        
        # Update user
        flask_login_current_user.display_name = display_name
        if email:
            flask_login_current_user.email = email
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user settings: {e}")
        flash('An error occurred while updating settings.', 'danger')
    
    return redirect(url_for('main.user_settings'))

@main_bp.route('/blacklist-whitelist')
@login_required
@spotify_token_required
def blacklist_whitelist():
    """Display blacklist/whitelist management page"""
    user_id = flask_login_current_user.id
    
    # Get user's whitelist and blacklist items
    whitelist_items = Whitelist.query.filter_by(user_id=user_id).order_by(Whitelist.added_date.desc()).all()
    blacklist_items = Blacklist.query.filter_by(user_id=user_id).order_by(Blacklist.added_date.desc()).all()
    
    return render_template('blacklist_whitelist.html', 
                         whitelist_items=whitelist_items,
                         blacklist_items=blacklist_items)

@main_bp.route('/add-whitelist-item', methods=['POST'])
@login_required
@spotify_token_required
def add_whitelist_item():
    """Add a new item to whitelist"""
    try:
        item_type = request.form.get('item_type', '').strip()
        spotify_id = request.form.get('spotify_id', '').strip()
        name = request.form.get('name', '').strip()
        reason = request.form.get('reason', '').strip()
        
        # Validation
        if not all([item_type, spotify_id, name]):
            flash('Item type, Spotify ID, and name are required.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        if item_type not in ['song', 'artist', 'playlist']:
            flash('Invalid item type.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        # Check if item already exists
        existing_item = Whitelist.query.filter_by(
            user_id=flask_login_current_user.id,
            spotify_id=spotify_id,
            item_type=item_type
        ).first()
        
        if existing_item:
            flash(f'{item_type.title()} already exists in your whitelist.', 'info')
            return redirect(url_for('main.blacklist_whitelist'))
        
        # Remove from blacklist if it exists there
        blacklist_item = Blacklist.query.filter_by(
            user_id=flask_login_current_user.id,
            spotify_id=spotify_id,
            item_type=item_type
        ).first()
        
        if blacklist_item:
            db.session.delete(blacklist_item)
            flash(f'{item_type.title()} moved from blacklist to whitelist.', 'success')
        
        # Add to whitelist
        new_item = Whitelist(
            user_id=flask_login_current_user.id,
            spotify_id=spotify_id,
            item_type=item_type,
            name=name,
            reason=reason
        )
        
        db.session.add(new_item)
        db.session.commit()
        
        if not blacklist_item:
            flash(f'{item_type.title()} added to whitelist successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding whitelist item: {e}")
        flash('An error occurred while adding the item.', 'danger')
    
    return redirect(url_for('main.blacklist_whitelist'))

@main_bp.route('/add-blacklist-item', methods=['POST'])
@login_required
@spotify_token_required
def add_blacklist_item():
    """Add a new item to blacklist"""
    try:
        item_type = request.form.get('item_type', '').strip()
        spotify_id = request.form.get('spotify_id', '').strip()
        name = request.form.get('name', '').strip()
        reason = request.form.get('reason', '').strip()
        
        # Validation
        if not all([item_type, spotify_id, name]):
            flash('Item type, Spotify ID, and name are required.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        if item_type not in ['song', 'artist', 'playlist']:
            flash('Invalid item type.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        # Check if item already exists
        existing_item = Blacklist.query.filter_by(
            user_id=flask_login_current_user.id,
            spotify_id=spotify_id,
            item_type=item_type
        ).first()
        
        if existing_item:
            flash(f'{item_type.title()} already exists in your blacklist.', 'info')
            return redirect(url_for('main.blacklist_whitelist'))
        
        # Remove from whitelist if it exists there
        whitelist_item = Whitelist.query.filter_by(
            user_id=flask_login_current_user.id,
            spotify_id=spotify_id,
            item_type=item_type
        ).first()
        
        if whitelist_item:
            db.session.delete(whitelist_item)
            flash(f'{item_type.title()} moved from whitelist to blacklist.', 'success')
        
        # Add to blacklist
        new_item = Blacklist(
            user_id=flask_login_current_user.id,
            spotify_id=spotify_id,
            item_type=item_type,
            name=name,
            reason=reason
        )
        
        db.session.add(new_item)
        db.session.commit()
        
        if not whitelist_item:
            flash(f'{item_type.title()} added to blacklist successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding blacklist item: {e}")
        flash('An error occurred while adding the item.', 'danger')
    
    return redirect(url_for('main.blacklist_whitelist'))

@main_bp.route('/remove-whitelist-item/<int:item_id>', methods=['POST'])
@login_required
@spotify_token_required
def remove_whitelist_item(item_id):
    """Remove an item from whitelist"""
    try:
        item = Whitelist.query.filter_by(
            id=item_id,
            user_id=flask_login_current_user.id
        ).first()
        
        if not item:
            flash('Item not found.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        item_name = item.name
        db.session.delete(item)
        db.session.commit()
        
        flash(f'"{item_name}" removed from whitelist.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing whitelist item: {e}")
        flash('An error occurred while removing the item.', 'danger')
    
    return redirect(url_for('main.blacklist_whitelist'))

@main_bp.route('/remove-blacklist-item/<int:item_id>', methods=['POST'])
@login_required
@spotify_token_required
def remove_blacklist_item(item_id):
    """Remove an item from blacklist"""
    try:
        item = Blacklist.query.filter_by(
            id=item_id,
            user_id=flask_login_current_user.id
        ).first()
        
        if not item:
            flash('Item not found.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        item_name = item.name
        db.session.delete(item)
        db.session.commit()
        
        flash(f'"{item_name}" removed from blacklist.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing blacklist item: {e}")
        flash('An error occurred while removing the item.', 'danger')
    
    return redirect(url_for('main.blacklist_whitelist'))

@main_bp.route('/edit-whitelist-item/<int:item_id>', methods=['POST'])
@login_required
@spotify_token_required
def edit_whitelist_item(item_id):
    """Edit a whitelist item"""
    try:
        item = Whitelist.query.filter_by(
            id=item_id,
            user_id=flask_login_current_user.id
        ).first()
        
        if not item:
            flash('Item not found.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        name = request.form.get('name', '').strip()
        reason = request.form.get('reason', '').strip()
        
        if not name:
            flash('Name is required.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        item.name = name
        item.reason = reason
        
        db.session.commit()
        flash('Item updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error editing whitelist item: {e}")
        flash('An error occurred while updating the item.', 'danger')
    
    return redirect(url_for('main.blacklist_whitelist'))

@main_bp.route('/edit-blacklist-item/<int:item_id>', methods=['POST'])
@login_required
@spotify_token_required
def edit_blacklist_item(item_id):
    """Edit a blacklist item"""
    try:
        item = Blacklist.query.filter_by(
            id=item_id,
            user_id=flask_login_current_user.id
        ).first()
        
        if not item:
            flash('Item not found.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        name = request.form.get('name', '').strip()
        reason = request.form.get('reason', '').strip()
        
        if not name:
            flash('Name is required.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        item.name = name
        item.reason = reason
        
        db.session.commit()
        flash('Item updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error editing blacklist item: {e}")
        flash('An error occurred while updating the item.', 'danger')
    
    return redirect(url_for('main.blacklist_whitelist'))

@main_bp.route('/export-whitelist')
@login_required
@spotify_token_required
def export_whitelist():
    """Export whitelist items as CSV"""
    import csv
    from io import StringIO
    from flask import Response
    
    try:
        user_id = flask_login_current_user.id
        items = Whitelist.query.filter_by(user_id=user_id).order_by(Whitelist.added_date.desc()).all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Item Type', 'Spotify ID', 'Name', 'Reason', 'Added Date'])
        
        # Write data
        for item in items:
            writer.writerow([
                item.item_type,
                item.spotify_id,
                item.name,
                item.reason or '',
                item.added_date.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=whitelist.csv'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting whitelist: {e}")
        flash('An error occurred while exporting the whitelist.', 'danger')
        return redirect(url_for('main.blacklist_whitelist'))

@main_bp.route('/export-blacklist')
@login_required
@spotify_token_required
def export_blacklist():
    """Export blacklist items as CSV"""
    import csv
    from io import StringIO
    from flask import Response
    
    try:
        user_id = flask_login_current_user.id
        items = Blacklist.query.filter_by(user_id=user_id).order_by(Blacklist.added_date.desc()).all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Item Type', 'Spotify ID', 'Name', 'Reason', 'Added Date'])
        
        # Write data
        for item in items:
            writer.writerow([
                item.item_type,
                item.spotify_id,
                item.name,
                item.reason or '',
                item.added_date.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=blacklist.csv'}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error exporting blacklist: {e}")
        flash('An error occurred while exporting the blacklist.', 'danger')
        return redirect(url_for('main.blacklist_whitelist'))

@main_bp.route('/bulk-import-whitelist', methods=['POST'])
@login_required
@spotify_token_required
def bulk_import_whitelist():
    """Bulk import whitelist items from CSV"""
    import csv
    from io import StringIO
    
    try:
        if 'csv_file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        # Read CSV content
        csv_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(csv_content))
        
        imported_count = 0
        skipped_count = 0
        
        for row in csv_reader:
            item_type = row.get('item_type', '').strip()
            spotify_id = row.get('spotify_id', '').strip()
            name = row.get('name', '').strip()
            reason = row.get('reason', '').strip()
            
            # Validate required fields
            if not all([item_type, spotify_id, name]):
                skipped_count += 1
                continue
            
            if item_type not in ['song', 'artist', 'playlist']:
                skipped_count += 1
                continue
            
            # Check if item already exists
            existing_item = Whitelist.query.filter_by(
                user_id=flask_login_current_user.id,
                spotify_id=spotify_id,
                item_type=item_type
            ).first()
            
            if existing_item:
                skipped_count += 1
                continue
            
            # Remove from blacklist if it exists there
            blacklist_item = Blacklist.query.filter_by(
                user_id=flask_login_current_user.id,
                spotify_id=spotify_id,
                item_type=item_type
            ).first()
            
            if blacklist_item:
                db.session.delete(blacklist_item)
            
            # Add to whitelist
            new_item = Whitelist(
                user_id=flask_login_current_user.id,
                spotify_id=spotify_id,
                item_type=item_type,
                name=name,
                reason=reason
            )
            
            db.session.add(new_item)
            imported_count += 1
        
        db.session.commit()
        
        flash(f'Import completed! {imported_count} items imported, {skipped_count} items skipped.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error importing whitelist: {e}")
        flash('An error occurred while importing the file.', 'danger')
    
    return redirect(url_for('main.blacklist_whitelist'))

@main_bp.route('/bulk-import-blacklist', methods=['POST'])
@login_required
@spotify_token_required
def bulk_import_blacklist():
    """Bulk import blacklist items from CSV"""
    import csv
    from io import StringIO
    
    try:
        if 'csv_file' not in request.files:
            flash('No file selected.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file.', 'danger')
            return redirect(url_for('main.blacklist_whitelist'))
        
        # Read CSV content
        csv_content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(csv_content))
        
        imported_count = 0
        skipped_count = 0
        
        for row in csv_reader:
            item_type = row.get('item_type', '').strip()
            spotify_id = row.get('spotify_id', '').strip()
            name = row.get('name', '').strip()
            reason = row.get('reason', '').strip()
            
            # Validate required fields
            if not all([item_type, spotify_id, name]):
                skipped_count += 1
                continue
            
            if item_type not in ['song', 'artist', 'playlist']:
                skipped_count += 1
                continue
            
            # Check if item already exists
            existing_item = Blacklist.query.filter_by(
                user_id=flask_login_current_user.id,
                spotify_id=spotify_id,
                item_type=item_type
            ).first()
            
            if existing_item:
                skipped_count += 1
                continue
            
            # Remove from whitelist if it exists there
            whitelist_item = Whitelist.query.filter_by(
                user_id=flask_login_current_user.id,
                spotify_id=spotify_id,
                item_type=item_type
            ).first()
            
            if whitelist_item:
                db.session.delete(whitelist_item)
            
            # Add to blacklist
            new_item = Blacklist(
                user_id=flask_login_current_user.id,
                spotify_id=spotify_id,
                item_type=item_type,
                name=name,
                reason=reason
            )
            
            db.session.add(new_item)
            imported_count += 1
        
        db.session.commit()
        
        flash(f'Import completed! {imported_count} items imported, {skipped_count} items skipped.', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error importing blacklist: {e}")
        flash('An error occurred while importing the file.', 'danger')
    
    return redirect(url_for('main.blacklist_whitelist'))

def calculate_playlist_score(playlist):
    """Calculate the overall score for a playlist based on analyzed songs."""
    try:
        # Get all analysis results for songs in this playlist
        analyzed_songs = []
        for song in playlist.songs:
            analysis_result = song.analysis_results.first()
            if analysis_result and analysis_result.status == 'completed' and analysis_result.score is not None:
                analyzed_songs.append(analysis_result.score)
        
        if not analyzed_songs:
            return None  # No analyzed songs
            
        # Calculate average score (analysis results are 0-100)
        average_score = sum(analyzed_songs) / len(analyzed_songs)
        
        # Update the playlist's overall_alignment_score
        playlist.overall_alignment_score = average_score
        
        return average_score
        
    except Exception as e:
        current_app.logger.error(f"Error calculating playlist score for {playlist.id}: {e}")
        return None


# Lazy Loading API Endpoints

@main_bp.route('/api/analysis/playlist/<string:playlist_id>')
@login_required
def playlist_analysis_data(playlist_id):
    """API endpoint for lazy loading playlist analysis data."""
    try:
        user_id = flask_login_current_user.id
        
        # Get cached data if available
        cache_key = f"playlist_analysis:{user_id}:{playlist_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
        
        # Get playlist data from database
        playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=user_id).first()
        if not playlist:
            abort(404)
        
        # Get songs in the playlist
        songs = db.session.query(Song).join(
            PlaylistSong, Song.id == PlaylistSong.song_id
        ).filter(PlaylistSong.playlist_id == playlist.id).all()
        
        # Format data for frontend
        analysis_data = {
            'songs': [],
            'summary': {
                'total_songs': len(songs),
                'analyzed_songs': 0,
                'pending_analysis': 0,
                'average_score': 0
            }
        }
        
        total_score = 0
        analyzed_count = 0
        
        for song in songs:
            result = AnalysisResult.query.filter_by(song_id=song.id, status='completed').first()
            song_data = {
                'id': song.id,
                'title': song.title,
                'artist': song.artist,
                'album': song.album,
                'status': 'pending'
            }
            
            if result:
                song_data['status'] = 'analyzed'
                song_data['score'] = result.score
                song_data['details'] = {
                    'concern_level': result.concern_level,
                    'explanation': result.explanation
                }
                total_score += result.score
                analyzed_count += 1
            else:
                analysis_data['summary']['pending_analysis'] += 1
            
            analysis_data['songs'].append(song_data)
        
        if analyzed_count > 0:
            analysis_data['summary']['average_score'] = round(total_score / analyzed_count, 1)
        
        analysis_data['summary']['analyzed_songs'] = analyzed_count
        
        # Cache the result
        cache.set(cache_key, analysis_data, timeout=300)  # 5 minutes cache
        
        return jsonify(analysis_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting playlist analysis data for {playlist_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@main_bp.route('/api/analysis/song/<int:song_id>')
@login_required
def song_analysis_data(song_id):
    """API endpoint for lazy loading individual song analysis data."""
    try:
        user_id = flask_login_current_user.id
        
        # Get cached data if available
        cache_key = f"song_analysis:{user_id}:{song_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
        
        # Get song data from database
        song = Song.query.filter_by(id=song_id).first()
        if not song:
            abort(404)
        
        # Verify user has access to this song
        playlist_song = PlaylistSong.query.filter_by(song_id=song.id).first()
        if not playlist_song:
            return jsonify({'error': 'Unauthorized'}), 403
            
        playlist = Playlist.query.filter_by(id=playlist_song.playlist_id, owner_id=user_id).first()
        if not playlist:
            return jsonify({'error': 'Unauthorized'}), 403
        
        result = AnalysisResult.query.filter_by(song_id=song.id, status='completed').first()
        
        if result:
            analysis_data = {
                'id': song.id,
                'title': song.title,
                'artist': song.artist,
                'album': song.album,
                'status': 'analyzed',
                'score': result.score,
                'details': {
                    'concern_level': result.concern_level,
                    'explanation': result.explanation
                }
            }
        else:
            analysis_data = {
                'id': song.id,
                'title': song.title,
                'artist': song.artist,
                'album': song.album,
                'status': 'pending'
            }
        
        # Cache the result
        cache.set(cache_key, analysis_data, timeout=300)  # 5 minutes cache
        
        return jsonify(analysis_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting song analysis data for {song_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
