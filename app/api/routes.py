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

@api_bp.route('/analysis/progress')
def get_analysis_progress():
    """Get current analysis progress for visual indicators"""
    try:
        from ..models import Song, AnalysisResult
        from ..extensions import db
        
        # Get total song count
        total_songs = db.session.query(Song).count()
        
        # Get analyzed song count
        analyzed_songs = db.session.query(AnalysisResult).filter(
            AnalysisResult.status == 'completed'
        ).count()
        
        # Calculate pending
        pending_songs = total_songs - analyzed_songs
        
        # Get recent analysis results for activity feed
        recent_results = db.session.query(AnalysisResult, Song).join(Song).filter(
            AnalysisResult.status == 'completed'
        ).order_by(AnalysisResult.analyzed_at.desc()).limit(5).all()
        
        recent_songs = []
        for result, song in recent_results:
            recent_songs.append({
                'title': song.title,
                'artist': song.artist,
                'status': 'completed',
                'score': result.score,
                'analyzed_at': result.analyzed_at.isoformat() if result.analyzed_at else None
            })
        
        # Check if analysis is actively running
        from ..extensions import rq
        queue = rq.get_queue()
        active_jobs = len(queue.jobs)
        
        return jsonify({
            'total': total_songs,
            'analyzed': analyzed_songs,
            'pending': pending_songs,
            'percentage': round((analyzed_songs / total_songs * 100), 1) if total_songs > 0 else 0,
            'recent_songs': recent_songs,
            'active_jobs': active_jobs,
            'in_progress': pending_songs > 0 and active_jobs > 0
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting analysis progress: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/analysis/status')
def get_analysis_status():
    """Get overall analysis status"""
    try:
        from ..models import Song, AnalysisResult
        from ..extensions import db, rq
        
        # Get basic counts
        total_songs = db.session.query(Song).count()
        analyzed_songs = db.session.query(AnalysisResult).filter(
            AnalysisResult.status == 'completed'
        ).count()
        pending_songs = total_songs - analyzed_songs
        
        # Check queue status
        queue = rq.get_queue()
        active_jobs = len(queue.jobs)
        failed_jobs = len(queue.failed_job_registry)
        
        # Determine if analysis is in progress
        in_progress = pending_songs > 0 and active_jobs > 0
        
        return jsonify({
            'in_progress': in_progress,
            'total_songs': total_songs,
            'analyzed_songs': analyzed_songs,
            'pending_songs': pending_songs,
            'active_jobs': active_jobs,
            'failed_jobs': failed_jobs,
            'completion_percentage': round((analyzed_songs / total_songs * 100), 1) if total_songs > 0 else 0
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting analysis status: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/analysis/performance')
def get_analysis_performance():
    """Get detailed performance metrics for analysis"""
    try:
        from ..models import Song, AnalysisResult
        from ..extensions import db
        from datetime import datetime, timedelta
        
        # Get analysis results from last hour for rate calculation
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_analyses = db.session.query(AnalysisResult).filter(
            AnalysisResult.analyzed_at >= one_hour_ago,
            AnalysisResult.status == 'completed'
        ).count()
        
        # Get analysis results from last 10 minutes for current rate
        ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
        very_recent_analyses = db.session.query(AnalysisResult).filter(
            AnalysisResult.analyzed_at >= ten_minutes_ago,
            AnalysisResult.status == 'completed'
        ).count()
        
        # Calculate rates
        hourly_rate = recent_analyses  # songs per hour
        current_rate = very_recent_analyses * 6  # extrapolate to songs per hour
        
        # Get worker information
        from ..extensions import rq
        queue = rq.get_queue()
        worker_count = len(queue.connection.smembers('rq:workers'))
        
        return jsonify({
            'hourly_rate': hourly_rate,
            'current_rate': current_rate,
            'songs_per_minute': round(current_rate / 60, 1),
            'worker_count': worker_count,
            'queue_length': len(queue.jobs),
            'performance_status': 'optimal' if current_rate > 100 else 'normal' if current_rate > 50 else 'slow'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': str(e)}), 500
