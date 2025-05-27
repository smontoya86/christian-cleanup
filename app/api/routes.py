# app/api/routes.py
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from . import api_bp
from app import db
from app.models.models import Whitelist
from app.services.whitelist_service import (
    add_to_whitelist, remove_from_whitelist, get_user_whitelist,
    get_whitelist_entry_by_id, is_whitelisted,
    ITEM_ADDED, ITEM_ALREADY_EXISTS, REASON_UPDATED,
    ITEM_REMOVED, ITEM_NOT_FOUND, INVALID_INPUT, ERROR_OCCURRED,
    ITEM_MOVED_FROM_BLACKLIST
)
from app.services.blacklist_service import (
    add_to_blacklist, remove_from_blacklist, get_user_blacklist,
    get_blacklist_entry_by_id, is_blacklisted,
    ITEM_ADDED as BL_ITEM_ADDED, ITEM_ALREADY_EXISTS as BL_ITEM_ALREADY_EXISTS,
    ITEM_MOVED_FROM_WHITELIST as BL_ITEM_MOVED, ERROR_OCCURRED as BL_ERROR_OCCURRED,
    ITEM_REMOVED as BL_ITEM_REMOVED, ITEM_NOT_FOUND as BL_ITEM_NOT_FOUND,
    INVALID_INPUT as BL_INVALID_INPUT
)
from sqlalchemy.exc import SQLAlchemyError
import json
import time
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_, or_
from app.models import Song, AnalysisResult, Playlist, PlaylistSong, User
from app.extensions import rq
from app.services.spotify_service import SpotifyService

# Enhanced Redis connectivity imports
from app.utils.redis_manager import redis_manager, test_redis_connection
from app.utils.job_retry import get_job_retry_stats

# --- Whitelist API Endpoints ---

@api_bp.route('/whitelist', methods=['GET'])
@login_required
def get_whitelist():
    """Get the current user's whitelist entries."""
    item_type = request.args.get('type') # Optional filter by type (song, artist, album)
    try:
        whitelist_items = get_user_whitelist(current_user.id, item_type=item_type)
        return jsonify([item.to_dict() for item in whitelist_items]), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error fetching whitelist for user {current_user.id}: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        current_app.logger.error(f"Error fetching whitelist for user {current_user.id}: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@api_bp.route('/whitelist', methods=['POST'])
@login_required
def add_whitelist_item():
    """Add an item to the current user's whitelist."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data'}), 400

    spotify_id = data.get('spotify_id')
    item_type = data.get('item_type')
    name = data.get('name') # Optional but recommended
    reason = data.get('reason') # Optional

    if not spotify_id or not item_type:
        return jsonify({'error': 'Missing required fields: spotify_id and item_type'}), 400

    # Basic validation for item_type
    if item_type not in ['song', 'artist', 'album']:
        return jsonify({'error': 'Invalid item_type. Must be song, artist, or album.'}), 400

    try:
        status_code, result_or_error = add_to_whitelist(
            user_id=current_user.id,
            spotify_id=spotify_id,
            item_type=item_type,
            name=name,
            reason=reason
        )

        if status_code == ITEM_ADDED:
            return jsonify({'message': 'Item added to whitelist', 'item': result_or_error.to_dict()}), 201
        elif status_code == ITEM_ALREADY_EXISTS:
             return jsonify({'message': 'Item already in whitelist', 'item': result_or_error.to_dict()}), 200
        elif status_code == REASON_UPDATED:
             return jsonify({'message': 'Whitelist item reason updated', 'item': result_or_error.to_dict()}), 200
        elif status_code == ITEM_MOVED_FROM_BLACKLIST:
             return jsonify({'message': 'Item moved from blacklist to whitelist', 'item': result_or_error.to_dict()}), 200
        elif status_code == ERROR_OCCURRED:
             return jsonify({'error': result_or_error}), 500
        else:
             current_app.logger.error(f"Unknown status code {status_code} from add_to_whitelist service")
             return jsonify({'error': 'Unknown result from service'}), 500

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error adding to whitelist for user {current_user.id}: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        current_app.logger.error(f"Error adding to whitelist for user {current_user.id}: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@api_bp.route('/whitelist/<int:entry_id>', methods=['DELETE'])
@login_required
def remove_whitelist_item(entry_id):
    """Remove an item from the current user's whitelist by its database ID."""
    try:
        status_code, message = remove_from_whitelist(user_id=current_user.id, whitelist_entry_id=entry_id)

        if status_code == ITEM_REMOVED:
            return jsonify({'message': message}), 200
        elif status_code == ITEM_NOT_FOUND:
            return jsonify({'error': message}), 404
        elif status_code == INVALID_INPUT:
             return jsonify({'error': message}), 400 # Bad request due to invalid input
        elif status_code == ERROR_OCCURRED:
            return jsonify({'error': message}), 500
        else:
             current_app.logger.error(f"Unknown status code {status_code} from remove_from_whitelist service")
             return jsonify({'error': 'Unknown result from service'}), 500

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error removing whitelist entry {entry_id} for user {current_user.id}: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        current_app.logger.error(f"Error removing whitelist entry {entry_id} for user {current_user.id}: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

# --- Blacklist API Endpoints ---

@api_bp.route('/blacklist', methods=['GET'])
@login_required
def get_blacklist():
    """Get the current user's blacklist entries."""
    item_type = request.args.get('type') # Optional filter by type
    try:
        blacklist_items = get_user_blacklist(current_user.id, item_type=item_type)
        # Need to ensure Blacklist model has to_dict method
        return jsonify([item.to_dict() for item in blacklist_items]), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error fetching blacklist for user {current_user.id}: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        current_app.logger.error(f"Error fetching blacklist for user {current_user.id}: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@api_bp.route('/blacklist', methods=['POST'])
@login_required
def add_blacklist_item():
    """Add an item to the current user's blacklist."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data'}), 400

    spotify_id = data.get('spotify_id')
    item_type = data.get('item_type')
    name = data.get('name')
    reason = data.get('reason')

    if not spotify_id or not item_type:
        return jsonify({'error': 'Missing required fields: spotify_id and item_type'}), 400

    if item_type not in ['song', 'artist', 'album']:
        return jsonify({'error': 'Invalid item_type. Must be song, artist, or album.'}), 400

    try:
        status_code, result_or_error = add_to_blacklist(
            user_id=current_user.id,
            spotify_id=spotify_id,
            item_type=item_type,
            name=name,
            reason=reason
        )

        if status_code == BL_ITEM_ADDED:
            return jsonify({'message': 'Item added to blacklist', 'item': result_or_error.to_dict()}), 201
        elif status_code == BL_ITEM_ALREADY_EXISTS:
             return jsonify({'message': 'Item already in blacklist', 'item': result_or_error.to_dict()}), 200
        elif status_code == BL_ITEM_MOVED:
             return jsonify({'message': 'Item moved from whitelist to blacklist', 'item': result_or_error.to_dict()}), 200
        elif status_code == BL_ERROR_OCCURRED:
             return jsonify({'error': result_or_error}), 500
        else:
             current_app.logger.error(f"Unknown status code {status_code} from add_to_blacklist service")
             return jsonify({'error': 'Unknown result from service'}), 500

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error adding to blacklist for user {current_user.id}: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        current_app.logger.error(f"Error adding to blacklist for user {current_user.id}: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@api_bp.route('/blacklist/<int:entry_id>', methods=['DELETE'])
@login_required
def remove_blacklist_item(entry_id):
    """Remove an item from the current user's blacklist by its database ID."""
    try:
        status_code, message = remove_from_blacklist(user_id=current_user.id, blacklist_entry_id=entry_id)

        if status_code == BL_ITEM_REMOVED:
            return jsonify({'message': message}), 200
        elif status_code == BL_ITEM_NOT_FOUND:
            return jsonify({'error': message}), 404
        elif status_code == BL_INVALID_INPUT:
             return jsonify({'error': message}), 400
        elif status_code == BL_ERROR_OCCURRED:
            return jsonify({'error': message}), 500
        else:
             current_app.logger.error(f"Unknown status code {status_code} from remove_from_blacklist service")
             return jsonify({'error': 'Unknown result from service'}), 500

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error removing blacklist entry {entry_id} for user {current_user.id}: {e}")
        return jsonify({'error': 'Database error occurred'}), 500
    except Exception as e:
        current_app.logger.error(f"Error removing blacklist entry {entry_id} for user {current_user.id}: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

def get_cache_key(endpoint, user_id=None, **kwargs):
    """Generate a cache key for API endpoints"""
    key_parts = [f'api:{endpoint}']
    if user_id:
        key_parts.append(f'user:{user_id}')
    for k, v in sorted(kwargs.items()):
        key_parts.append(f'{k}:{v}')
    return ':'.join(key_parts)

def cache_response(key, data, ttl=300):
    """Cache response data with TTL (default 5 minutes)"""
    try:
        # Try to get Redis connection from RQ
        try:
            redis_conn = rq.get_connection()
        except AttributeError:
            # Fallback to RQ connection attribute
            redis_conn = rq.connection
        
        redis_conn.setex(key, ttl, json.dumps(data, default=str))
    except Exception as e:
        current_app.logger.warning(f"Failed to cache response: {e}")

def get_cached_response(key):
    """Get cached response data"""
    try:
        # Try to get Redis connection from RQ
        try:
            redis_conn = rq.get_connection()
        except AttributeError:
            # Fallback to RQ connection attribute
            redis_conn = rq.connection
            
        cached = redis_conn.get(key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        current_app.logger.warning(f"Failed to get cached response: {e}")
    return None

@api_bp.route('/analysis/progress')
@login_required
def analysis_progress():
    """Get analysis progress with caching"""
    # Check cache first (cache for 2 minutes since this changes frequently)
    cache_key = get_cache_key('progress', current_user.id)
    cached_response = get_cached_response(cache_key)
    if cached_response:
        cached_response['cached'] = True
        return jsonify(cached_response)
    
    try:
        # Get total songs count
        total_songs = db.session.query(Song).count()
        
        # Get completed analysis count using our optimized index
        completed_count = db.session.query(AnalysisResult).filter(
            AnalysisResult.status == 'completed'
        ).count()
        
        # Get recent analysis results (limited to 5 for performance)
        recent_results = db.session.query(AnalysisResult, Song)\
            .join(Song)\
            .filter(AnalysisResult.status == 'completed')\
            .order_by(AnalysisResult.analyzed_at.desc())\
            .limit(5).all()
        
        # Calculate progress
        progress_percentage = (completed_count / total_songs * 100) if total_songs > 0 else 0
        remaining_count = total_songs - completed_count
        
        # Format recent results
        recent_songs = []
        for analysis, song in recent_results:
            recent_songs.append({
                'title': song.title,
                'artist': song.artist,
                'score': analysis.score,
                'analyzed_at': analysis.analyzed_at.isoformat() if analysis.analyzed_at else None
            })
        
        response_data = {
            'total_songs': total_songs,
            'analyzed_songs': completed_count,
            'remaining_songs': remaining_count,
            'progress_percentage': round(progress_percentage, 1),
            'recent_songs': recent_songs,
            'cached': False
        }
        
        # Cache the response for 2 minutes
        cache_response(cache_key, response_data, ttl=120)
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in analysis_progress: {e}")
        return jsonify({'error': 'Failed to get analysis progress'}), 500

@api_bp.route('/analysis/status')
@login_required
def analysis_status():
    """Get enhanced analysis status with active job monitoring for current user"""
    from ..services.background_analysis_service import BackgroundAnalysisService
    
    # For active analysis monitoring, use shorter cache (30 seconds)
    cache_key = get_cache_key('status', current_user.id)
    cached_response = get_cached_response(cache_key)
    if cached_response:
        cached_response['cached'] = True
        return jsonify(cached_response)
    
    try:
        # Use the background analysis service to get user-specific progress
        progress_data = BackgroundAnalysisService.get_analysis_progress_for_user(current_user.id)
        
        # Format response to match expected structure
        response_data = {
            'user_id': current_user.id,
            'has_active_analysis': progress_data['has_active_analysis'],
            'total_songs': progress_data['total_songs'],
            'completed': progress_data['completed'],
            'in_progress': progress_data['in_progress'],
            'pending': progress_data['pending'],
            'failed': progress_data['failed'],
            'status_counts': {
                'completed': progress_data['completed'],
                'in_progress': progress_data['in_progress'],
                'pending': progress_data['pending'],
                'failed': progress_data['failed']
            },
            'progress_percentage': progress_data['progress_percentage'],
            'current_song': progress_data['current_analysis'],  # JavaScript expects 'current_song'
            'recent_completed': progress_data['recent_analyses'],
            'cached': False
        }
        
        # Cache for 30 seconds during active analysis, 2 minutes otherwise
        cache_ttl = 30 if progress_data['has_active_analysis'] else 120
        cache_response(cache_key, response_data, ttl=cache_ttl)
        
        current_app.logger.debug(f"Analysis status for user {current_user.id}: {progress_data['completed']}/{progress_data['total_songs']} completed, {progress_data['in_progress']} in progress")
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in analysis_status for user {current_user.id}: {e}")
        return jsonify({'error': 'Failed to get analysis status'}), 500

@api_bp.route('/analysis/performance')
@login_required
def analysis_performance():
    """Get analysis performance metrics with caching"""
    # Check cache first (cache for 5 minutes since this changes less frequently)
    cache_key = get_cache_key('performance', current_user.id)
    cached_response = get_cached_response(cache_key)
    if cached_response:
        cached_response['cached'] = True
        return jsonify(cached_response)
    
    try:
        # Get analysis performance over last 24 hours
        since_time = datetime.utcnow() - timedelta(hours=24)
        
        # Count analyses completed in last 24 hours using our optimized index
        recent_analyses = db.session.query(AnalysisResult).filter(
            and_(
                AnalysisResult.status == 'completed',
                AnalysisResult.analyzed_at >= since_time
            )
        ).count()
        
        # Calculate songs per minute (assuming even distribution)
        hours_elapsed = 24
        songs_per_hour = recent_analyses / hours_elapsed if hours_elapsed > 0 else 0
        songs_per_minute = songs_per_hour / 60
        
        # Get total pending count
        total_songs = db.session.query(Song).count()
        completed_total = db.session.query(AnalysisResult).filter(
            AnalysisResult.status == 'completed'
        ).count()
        pending_count = total_songs - completed_total
        
        # Calculate ETA
        eta_minutes = pending_count / songs_per_minute if songs_per_minute > 0 else 0
        
        response_data = {
            'songs_per_minute': round(songs_per_minute, 1),
            'recent_analyses_24h': recent_analyses,
            'pending_count': pending_count,
            'eta_minutes': round(eta_minutes, 1),
            'cached': False
        }
        
        # Cache the response for 5 minutes
        cache_response(cache_key, response_data, ttl=300)
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in analysis_performance: {e}")
        return jsonify({'error': 'Failed to get performance metrics'}), 500

@api_bp.route('/playlists/<playlist_id>/analysis-status')
@login_required
def playlist_analysis_status(playlist_id):
    """Get analysis status for a specific playlist with caching"""
    # Check cache first (cache for 3 minutes)
    cache_key = get_cache_key('playlist_status', current_user.id, playlist_id=playlist_id)
    cached_response = get_cached_response(cache_key)
    if cached_response:
        cached_response['cached'] = True
        return jsonify(cached_response)
    
    try:
        # Get playlist
        playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=current_user.id).first()
        if not playlist:
            return jsonify({'error': 'Playlist not found'}), 404
        
        # Get playlist songs with analysis status using our optimized indexes
        playlist_songs = db.session.query(Song, AnalysisResult)\
            .join(PlaylistSong, Song.id == PlaylistSong.song_id)\
            .outerjoin(AnalysisResult, Song.id == AnalysisResult.song_id)\
            .filter(PlaylistSong.playlist_id == playlist.id)\
            .order_by(PlaylistSong.track_position)\
            .all()
        
        # Calculate statistics
        total_songs = len(playlist_songs)
        analyzed_songs = sum(1 for _, analysis in playlist_songs if analysis and analysis.status == 'completed')
        pending_songs = total_songs - analyzed_songs
        
        # Calculate average score for analyzed songs
        scores = [analysis.score for _, analysis in playlist_songs 
                 if analysis and analysis.status == 'completed' and analysis.score is not None]
        avg_score = sum(scores) / len(scores) if scores else None
        
        response_data = {
            'playlist_id': playlist_id,
            'playlist_name': playlist.name,
            'total_songs': total_songs,
            'analyzed_songs': analyzed_songs,
            'pending_songs': pending_songs,
            'analysis_percentage': round((analyzed_songs / total_songs * 100), 1) if total_songs > 0 else 0,
            'average_score': round(avg_score, 1) if avg_score is not None else None,
            'cached': False
        }
        
        # Cache for 3 minutes
        cache_response(cache_key, response_data, ttl=180)
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in playlist_analysis_status: {e}")
        return jsonify({'error': 'Failed to get playlist analysis status'}), 500

# Cache invalidation helper
def invalidate_user_cache(user_id):
    """Invalidate all cached responses for a user"""
    try:
        # Get all keys for this user
        redis_conn = rq.get_connection()
        pattern = f'api:*:user:{user_id}*'
        keys = redis_conn.keys(pattern)
        if keys:
            redis_conn.delete(*keys)
            current_app.logger.info(f"Invalidated {len(keys)} cache entries for user {user_id}")
    except Exception as e:
        current_app.logger.warning(f"Failed to invalidate cache for user {user_id}: {e}")


# --- Health Check and Monitoring API Endpoints ---

@api_bp.route('/health/redis', methods=['GET'])
def redis_health():
    """Test Redis connection and return detailed health information."""
    try:
        result = test_redis_connection()
        
        if result['success']:
            return jsonify({
                'status': 'healthy',
                'message': 'Redis connection successful',
                'response_time_ms': result['response_time_ms'],
                'redis_info': result.get('redis_info', {}),
                'pool_info': result.get('pool_info', {}),
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'unhealthy',
                'message': f'Redis connection failed: {result["error"]}',
                'response_time_ms': result['response_time_ms'],
                'timestamp': datetime.utcnow().isoformat()
            }), 503
            
    except Exception as e:
        current_app.logger.error(f"Error in redis health check: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Health check failed: {str(e)}',
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@api_bp.route('/health/queues', methods=['GET'])
def queue_health():
    """Monitor health of RQ queues and return detailed statistics."""
    try:
        health_data = redis_manager.monitor_queue_health()
        
        # Determine HTTP status based on overall health
        if health_data['overall_status'] == 'healthy':
            status_code = 200
        elif health_data['overall_status'] == 'degraded':
            status_code = 206  # Partial Content - degraded but functional
        else:
            status_code = 503  # Service Unavailable
        
        return jsonify(health_data), status_code
        
    except Exception as e:
        current_app.logger.error(f"Error in queue health check: {e}")
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'error',
            'error': str(e),
            'queues': {}
        }), 500


@api_bp.route('/health/redis/stats', methods=['GET'])
def redis_stats():
    """Get comprehensive Redis connection statistics."""
    try:
        stats = redis_manager.get_health_stats()
        
        return jsonify({
            'status': 'success',
            'timestamp': datetime.utcnow().isoformat(),
            'connection_stats': stats
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting Redis stats: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@api_bp.route('/health/jobs/<job_id>', methods=['GET'])
def job_retry_stats(job_id):
    """Get retry statistics for a specific job."""
    try:
        stats = get_job_retry_stats(job_id)
        
        if stats:
            return jsonify({
                'status': 'success',
                'job_stats': stats,
                'timestamp': datetime.utcnow().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'not_found',
                'message': f'Job {job_id} not found or has no retry stats',
                'timestamp': datetime.utcnow().isoformat()
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error getting job retry stats for {job_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@api_bp.route('/health', methods=['GET'])
def overall_health():
    """Comprehensive health check combining all system components."""
    try:
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'healthy',
            'components': {}
        }
        
        # Test Redis connection
        try:
            redis_result = test_redis_connection()
            health_status['components']['redis'] = {
                'status': 'healthy' if redis_result['success'] else 'unhealthy',
                'response_time_ms': redis_result['response_time_ms'],
                'error': redis_result.get('error')
            }
            if not redis_result['success']:
                health_status['overall_status'] = 'degraded'
        except Exception as e:
            health_status['components']['redis'] = {
                'status': 'error',
                'error': str(e)
            }
            health_status['overall_status'] = 'unhealthy'
        
        # Test database connection
        try:
            db.session.execute('SELECT 1')
            health_status['components']['database'] = {
                'status': 'healthy'
            }
        except Exception as e:
            health_status['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['overall_status'] = 'unhealthy'
        
        # Test queue health
        try:
            queue_health_data = redis_manager.monitor_queue_health()
            health_status['components']['queues'] = {
                'status': queue_health_data['overall_status'],
                'queue_count': len(queue_health_data.get('queues', {}))
            }
            if queue_health_data['overall_status'] != 'healthy':
                if health_status['overall_status'] == 'healthy':
                    health_status['overall_status'] = 'degraded'
        except Exception as e:
            health_status['components']['queues'] = {
                'status': 'error',
                'error': str(e)
            }
            health_status['overall_status'] = 'unhealthy'
        
        # Determine HTTP status code
        if health_status['overall_status'] == 'healthy':
            status_code = 200
        elif health_status['overall_status'] == 'degraded':
            status_code = 206
        else:
            status_code = 503
        
        return jsonify(health_status), status_code
        
    except Exception as e:
        current_app.logger.error(f"Error in overall health check: {e}")
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'error',
            'error': str(e)
        }), 500
