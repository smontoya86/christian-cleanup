"""
Core Blueprint Routes - Main application entry points and dashboard functionality.

This file contains the routes for:
- Home page (/)
- Test base render
- Dashboard views and functionality
"""

from flask import render_template, flash, redirect, url_for, request, current_app, jsonify, session
from flask_login import login_required, current_user as flask_login_current_user

# Import the blueprint
from . import core_bp

# Import required modules
from app import db
from app.models import User, Song, AnalysisResult, PlaylistSong, Playlist
from app.auth.decorators import spotify_token_required

# Constants
PLAYLISTS_PER_PAGE = 25

def get_dashboard_data(user_id, page=1):
    """Get dashboard data for a user. 
    
    Note: Caching temporarily disabled due to SQLAlchemy object serialization issues.
    The @cached decorator converts Playlist objects to strings via json.dumps(default=str).
    """
    from app.services.playlist_sync_service import get_sync_status
    from app.models import AnalysisResult
    
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
    from app.blueprints.shared.utils import calculate_playlist_score
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

@core_bp.route('/')
def index():
    """Home page - redirects to dashboard if authenticated."""
    if flask_login_current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    return render_template('index.html')

@core_bp.route('/test_base_render')
def test_base_render_route():
    """Test route for base template rendering."""
    return render_template('test_page.html')

@core_bp.route('/dashboard')
@login_required
@spotify_token_required # Re-enabled
def dashboard():
    """Main dashboard view showing user's playlists and stats."""
    from app.services.background_analysis_service import BackgroundAnalysisService
    
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

@core_bp.route('/dashboard', methods=['POST'])
@login_required  
def dashboard_post():
    """Handle POST requests to dashboard (like clearing auto_sync flag)"""
    if request.form.get('clear_auto_sync'):
        session.pop('auto_sync_started', None)
        return jsonify({"status": "success"})
    
    # Redirect to GET dashboard for other POST requests
    return redirect(url_for('core.dashboard'))
