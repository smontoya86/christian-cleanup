"""
API routes for AJAX requests and JSON responses
"""

from flask import Blueprint, jsonify, request, current_app, Response
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import text

from .. import db
from ..models.models import Playlist, Song, AnalysisResult, PlaylistSong
from ..services.spotify_service import SpotifyService
from ..services.analysis_service import AnalysisService
from ..utils.health_monitor import health_monitor
from ..utils.prometheus_metrics import get_metrics, metrics_collector

bp = Blueprint('api', __name__)


@bp.route('/health')
def health():
    """Basic health check endpoint"""
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f'Health check failed: {e}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@bp.route('/health/detailed')
def detailed_health_check():
    """Comprehensive health check with detailed system status"""
    try:
        # Force refresh for detailed checks
        system_health = health_monitor.get_system_health(force_refresh=True)
        
        # Convert to JSON-serializable format
        health_data = health_monitor.to_dict(system_health)
        
        # Set appropriate HTTP status based on health
        if system_health.status.value == 'healthy':
            status_code = 200
        elif system_health.status.value == 'warning':
            status_code = 200  # Still operational
        else:  # critical
            status_code = 503  # Service unavailable
        
        return jsonify(health_data), status_code
        
    except Exception as e:
        current_app.logger.error(f'Detailed health check failed: {e}')
        return jsonify({
            'status': 'critical',
            'timestamp': datetime.now().isoformat(),
            'error': f'Health monitoring system failed: {str(e)}',
            'checks': []
        }), 503


@bp.route('/health/ready')
def readiness_check():
    """Kubernetes-style readiness probe"""
    try:
        # Check critical dependencies only
        db.session.execute(text('SELECT 1')).scalar()
        
        import redis
        redis_client = redis.from_url(current_app.config.get('RQ_REDIS_URL', 'redis://localhost:6379/0'))
        redis_client.ping()
        
        return jsonify({'status': 'ready'}), 200
        
    except Exception as e:
        current_app.logger.error(f'Readiness check failed: {e}')
        return jsonify({'status': 'not ready', 'error': str(e)}), 503


@bp.route('/health/live')
def liveness_check():
    """Kubernetes-style liveness probe"""
    # Very basic check - just ensure the application is responding
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.now().isoformat()
    }), 200


@bp.route('/playlists')
@login_required
def get_playlists():
    """Get user's playlists as JSON"""
    playlists = Playlist.query.filter_by(owner_id=current_user.id).all()
    
    playlist_data = []
    for playlist in playlists:
        song_count = PlaylistSong.query.filter_by(playlist_id=playlist.id).count()
        analyzed_count = db.session.query(Song).join(AnalysisResult).join(PlaylistSong).filter(
            PlaylistSong.playlist_id == playlist.id,
            AnalysisResult.status == 'completed'
        ).count()
        
        playlist_data.append({
            'id': playlist.id,
            'name': playlist.name,
            'description': playlist.description,
            'song_count': song_count,
            'analyzed_count': analyzed_count,
            'analysis_progress': round((analyzed_count / song_count * 100) if song_count > 0 else 0, 1),
            'image_url': playlist.image_url,
            'spotify_url': f'https://open.spotify.com/playlist/{playlist.spotify_id}' if playlist.spotify_id else None
        })
    
    return jsonify({'playlists': playlist_data})


@bp.route('/playlist/<int:playlist_id>/songs')
@login_required
def get_playlist_songs(playlist_id):
    """Get songs in a playlist with analysis status"""
    playlist = Playlist.query.filter_by(
        id=playlist_id,
        owner_id=current_user.id
    ).first_or_404()
    
    songs_query = db.session.query(Song, AnalysisResult, PlaylistSong).join(
        PlaylistSong, Song.id == PlaylistSong.song_id
    ).outerjoin(
        AnalysisResult, Song.id == AnalysisResult.song_id
    ).filter(
        PlaylistSong.playlist_id == playlist_id
            ).order_by(PlaylistSong.track_position)
    
    songs_data = []
    for song, analysis, playlist_song in songs_query:
        song_data = {
            'id': song.id,
            'name': song.title,
            'artist': song.artist,
            'album': song.album,
            'duration_ms': song.duration_ms,
            'position': playlist_song.track_position,
            'spotify_url': f'https://open.spotify.com/track/{song.spotify_id}' if song.spotify_id else None,
            'analysis_status': analysis.status if analysis else 'pending',
            'analysis_score': analysis.score if analysis else None,
            'concern_level': analysis.concern_level if analysis else None,
            'detected_themes': analysis.themes if analysis else [],
            'analysis_date': analysis.created_at.isoformat() if analysis else None
        }
        songs_data.append(song_data)
    
    return jsonify({
        'playlist': {
            'id': playlist.id,
            'name': playlist.name,
            'description': playlist.description
        },
        'songs': songs_data
    })


@bp.route('/song/<int:song_id>/analysis')
@login_required
def get_song_analysis(song_id):
    """Get detailed analysis for a song"""
    # Verify user has access to this song
    song = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Song.id == song_id,
        Playlist.owner_id == current_user.id
    ).first_or_404()
    
    analysis = AnalysisResult.query.filter_by(song_id=song_id).order_by(
        AnalysisResult.created_at.desc()
    ).first()
    
    song_data = {
        'id': song.id,
        'name': song.title,
        'artist': song.artist,
        'album': song.album,
        'lyrics': song.lyrics,
        'spotify_url': f'https://open.spotify.com/track/{song.spotify_id}' if song.spotify_id else None
    }
    
    analysis_data = None
    if analysis:
        analysis_data = {
            'status': analysis.status,
            'score': analysis.score,
            'concern_level': analysis.concern_level,
            'themes': analysis.themes or [],
            'analysis_details': analysis.problematic_content or {},
            'created_at': analysis.created_at.isoformat(),
            'concerns': analysis.concerns or []
        }
    
    return jsonify({
        'song': song_data,
        'analysis': analysis_data
    })


@bp.route('/playlist/<int:playlist_id>/analysis_progress')
@login_required
def get_analysis_progress(playlist_id):
    """Get analysis progress for a playlist"""
    playlist = Playlist.query.filter_by(
        id=playlist_id,
        owner_id=current_user.id
    ).first_or_404()
    
    total_songs = PlaylistSong.query.filter_by(playlist_id=playlist_id).count()
    
    # Count songs by analysis status
    status_counts = db.session.query(
        AnalysisResult.status,
        db.func.count(AnalysisResult.id)
    ).join(Song).join(PlaylistSong).filter(
        PlaylistSong.playlist_id == playlist_id
    ).group_by(AnalysisResult.status).all()
    
    status_dict = dict(status_counts)
    pending_count = total_songs - sum(status_dict.values())
    
    return jsonify({
        'playlist_id': playlist_id,
        'total_songs': total_songs,
        'completed': status_dict.get('completed', 0),
        'failed': status_dict.get('failed', 0),
        'pending': pending_count,
        'in_progress': status_dict.get('in_progress', 0),
        'progress_percent': round((status_dict.get('completed', 0) / total_songs * 100) if total_songs > 0 else 0, 1)
    })


@bp.route('/search_songs')
@login_required
def search_songs():
    """Search user's songs"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'songs': []})
    
    # Search in user's songs
    songs = db.session.query(Song, AnalysisResult).join(PlaylistSong).join(Playlist).outerjoin(
        AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
        Playlist.owner_id == current_user.id,
        db.or_(
            Song.title.ilike(f'%{query}%'),
            Song.artist.ilike(f'%{query}%'),
            Song.album.ilike(f'%{query}%')
        )
    ).limit(20).all()
    
    songs_data = []
    for song, analysis in songs:
        songs_data.append({
            'id': song.id,
            'name': song.title,
            'artist': song.artist,
            'album': song.album,
            'analysis_status': analysis.status if analysis else 'pending',
            'concern_level': analysis.concern_level if analysis else None,
            'spotify_url': f'https://open.spotify.com/track/{song.spotify_id}' if song.spotify_id else None
        })
    
    return jsonify({'songs': songs_data})


@bp.route('/sync-status')
@login_required
def sync_status():
    """Get sync status for user's playlists"""
    try:
        # Count playlists by sync status
        total_playlists = Playlist.query.filter_by(owner_id=current_user.id).count()
        
        return jsonify({
            'status': 'success',
            'total_playlists': total_playlists,
            'sync_active': False,  # Would check for active sync jobs
            'last_sync': None,      # Would get from database
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f'Sync status check failed: {e}')
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@bp.route('/stats')
@login_required
def get_user_stats():
    """Get comprehensive user statistics"""
    total_playlists = Playlist.query.filter_by(owner_id=current_user.id).count()
    
    total_songs = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id
    ).count()
    
    analyzed_songs = db.session.query(Song).join(AnalysisResult).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id,
        AnalysisResult.status == 'completed'
    ).count()
    
    # Count by concern level
    concern_counts = db.session.query(
        AnalysisResult.concern_level,
        db.func.count(AnalysisResult.id)
    ).join(Song).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id,
        AnalysisResult.status == 'completed'
    ).group_by(AnalysisResult.concern_level).all()
    
    concern_dict = dict(concern_counts)
    
    return jsonify({
        'total_playlists': total_playlists,
        'total_songs': total_songs,
        'analyzed_songs': analyzed_songs,
        'analysis_progress': round((analyzed_songs / total_songs * 100) if total_songs > 0 else 0, 1),
        'concern_levels': {
            'low': concern_dict.get('low', 0),
            'medium': concern_dict.get('medium', 0),
            'high': concern_dict.get('high', 0)
        },
        'flagged_songs': concern_dict.get('medium', 0) + concern_dict.get('high', 0)
    })


@bp.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    try:
        metrics_data = get_metrics()
        return Response(metrics_data, mimetype='text/plain')
    except Exception as e:
        current_app.logger.error(f'Error generating metrics: {e}')
        metrics_collector.record_error('metrics_generation_error', 'api')
        return jsonify({'error': 'Metrics unavailable'}), 500


@bp.errorhandler(404)
def api_not_found(error):
    """API 404 handler"""
    return jsonify({'error': 'Endpoint not found'}), 404


@bp.errorhandler(500)
def api_error(error):
    """API 500 handler"""
    current_app.logger.error(f'API error: {error}')
    return jsonify({'error': 'Internal server error'}), 500 