"""
Admin routes for cache management and system administration.
Provides endpoints for managing the lyrics cache and monitoring system health.
"""

from flask import jsonify, request, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from functools import wraps
import logging

from . import admin_bp
from app.utils.cache_management import (
    clear_old_cache_entries,
    clear_cache_by_source,
    clear_all_cache,
    get_cache_stats,
    get_cache_entries_by_artist,
    get_cache_entries_by_source,
    optimize_cache_storage,
    validate_cache_integrity,
    get_cache_usage_report
)
from app.models.models import User

logger = logging.getLogger(__name__)


def admin_required(f):
    """
    Decorator to require admin privileges for accessing admin routes.
    For now, this checks if the user is authenticated. In the future,
    this could be extended to check for specific admin roles.
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # For now, any authenticated user can access admin functions
        # In production, you might want to add role-based access control
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
            flash('Admin access required.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_required
def admin_dashboard():
    """Admin dashboard with system overview."""
    try:
        # Get cache statistics
        cache_stats = get_cache_stats()
        
        # Get cache integrity status
        integrity_status = validate_cache_integrity()
        
        # Get recent usage report (last 7 days)
        usage_report = get_cache_usage_report(days=7)
        
        dashboard_data = {
            'cache_stats': cache_stats,
            'integrity_status': integrity_status,
            'usage_report': usage_report,
            'user_count': User.query.count()
        }
        
        if request.is_json:
            return jsonify(dashboard_data)
        
        # For HTML requests, you could render a template
        # return render_template('admin/dashboard.html', data=dashboard_data)
        return jsonify(dashboard_data)  # For now, return JSON
        
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        if request.is_json:
            return jsonify({'error': 'Failed to load dashboard data'}), 500
        flash('Failed to load dashboard data.', 'error')
        return redirect(url_for('main.index'))


@admin_bp.route('/cache/stats')
@admin_required
def cache_stats():
    """Get comprehensive cache statistics."""
    try:
        stats = get_cache_stats()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logger.error(f"Error getting cache statistics: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve cache statistics'
        }), 500


@admin_bp.route('/cache/integrity')
@admin_required
def cache_integrity():
    """Check cache data integrity."""
    try:
        integrity_report = validate_cache_integrity()
        return jsonify({
            'success': True,
            'data': integrity_report
        })
    except Exception as e:
        logger.error(f"Error validating cache integrity: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to validate cache integrity'
        }), 500


@admin_bp.route('/cache/usage-report')
@admin_required
def cache_usage_report():
    """Get cache usage report for a specified period."""
    try:
        days = request.args.get('days', 30, type=int)
        if days < 1 or days > 365:
            return jsonify({
                'success': False,
                'error': 'Days parameter must be between 1 and 365'
            }), 400
        
        report = get_cache_usage_report(days=days)
        return jsonify({
            'success': True,
            'data': report
        })
    except Exception as e:
        logger.error(f"Error generating cache usage report: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to generate usage report'
        }), 500


@admin_bp.route('/cache/entries/by-artist')
@admin_required
def cache_entries_by_artist():
    """Get cache entries for a specific artist."""
    try:
        artist = request.args.get('artist')
        if not artist:
            return jsonify({
                'success': False,
                'error': 'Artist parameter is required'
            }), 400
        
        limit = request.args.get('limit', 50, type=int)
        if limit < 1 or limit > 200:
            return jsonify({
                'success': False,
                'error': 'Limit must be between 1 and 200'
            }), 400
        
        entries = get_cache_entries_by_artist(artist, limit=limit)
        return jsonify({
            'success': True,
            'data': {
                'artist': artist,
                'entries': entries,
                'count': len(entries)
            }
        })
    except Exception as e:
        logger.error(f"Error getting cache entries by artist: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve cache entries'
        }), 500


@admin_bp.route('/cache/entries/by-source')
@admin_required
def cache_entries_by_source():
    """Get cache entries from a specific source provider."""
    try:
        source = request.args.get('source')
        if not source:
            return jsonify({
                'success': False,
                'error': 'Source parameter is required'
            }), 400
        
        limit = request.args.get('limit', 50, type=int)
        if limit < 1 or limit > 200:
            return jsonify({
                'success': False,
                'error': 'Limit must be between 1 and 200'
            }), 400
        
        entries = get_cache_entries_by_source(source, limit=limit)
        return jsonify({
            'success': True,
            'data': {
                'source': source,
                'entries': entries,
                'count': len(entries)
            }
        })
    except Exception as e:
        logger.error(f"Error getting cache entries by source: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve cache entries'
        }), 500


@admin_bp.route('/cache/clear/old', methods=['POST'])
@admin_required
def clear_old_cache():
    """Clear cache entries older than specified days."""
    try:
        data = request.get_json() or {}
        days = data.get('days', 30)
        
        if not isinstance(days, int) or days < 1 or days > 365:
            return jsonify({
                'success': False,
                'error': 'Days must be an integer between 1 and 365'
            }), 400
        
        removed_count = clear_old_cache_entries(days=days)
        
        logger.info(f"Admin user {current_user.id} cleared {removed_count} old cache entries (older than {days} days)")
        
        return jsonify({
            'success': True,
            'data': {
                'removed_count': removed_count,
                'days': days,
                'message': f'Successfully removed {removed_count} cache entries older than {days} days'
            }
        })
    except Exception as e:
        logger.error(f"Error clearing old cache entries: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear old cache entries'
        }), 500


@admin_bp.route('/cache/clear/source', methods=['POST'])
@admin_required
def clear_cache_source():
    """Clear all cache entries from a specific source provider."""
    try:
        data = request.get_json() or {}
        source = data.get('source')
        
        if not source:
            return jsonify({
                'success': False,
                'error': 'Source parameter is required'
            }), 400
        
        removed_count = clear_cache_by_source(source=source)
        
        logger.info(f"Admin user {current_user.id} cleared {removed_count} cache entries from source '{source}'")
        
        return jsonify({
            'success': True,
            'data': {
                'removed_count': removed_count,
                'source': source,
                'message': f'Successfully removed {removed_count} cache entries from source "{source}"'
            }
        })
    except Exception as e:
        logger.error(f"Error clearing cache entries by source: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear cache entries by source'
        }), 500


@admin_bp.route('/cache/clear/all', methods=['POST'])
@admin_required
def clear_all_cache_entries():
    """Clear all cache entries. Use with caution!"""
    try:
        # Require explicit confirmation for this destructive operation
        data = request.get_json() or {}
        confirm = data.get('confirm', False)
        
        if not confirm:
            return jsonify({
                'success': False,
                'error': 'This operation requires explicit confirmation. Set "confirm": true in the request body.'
            }), 400
        
        removed_count = clear_all_cache()
        
        logger.warning(f"Admin user {current_user.id} cleared ALL {removed_count} cache entries")
        
        return jsonify({
            'success': True,
            'data': {
                'removed_count': removed_count,
                'message': f'Successfully removed all {removed_count} cache entries'
            }
        })
    except Exception as e:
        logger.error(f"Error clearing all cache entries: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear all cache entries'
        }), 500


@admin_bp.route('/cache/optimize', methods=['POST'])
@admin_required
def optimize_cache():
    """Optimize cache storage by removing duplicates and cleaning up data."""
    try:
        optimization_result = optimize_cache_storage()
        
        logger.info(f"Admin user {current_user.id} optimized cache storage: {optimization_result['duplicates_removed']} duplicates removed")
        
        return jsonify({
            'success': True,
            'data': optimization_result
        })
    except Exception as e:
        logger.error(f"Error optimizing cache storage: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to optimize cache storage'
        }), 500


@admin_bp.route('/system/health')
@admin_required
def system_health():
    """Get overall system health status."""
    try:
        from app.models.models import db, User, Song, Analysis
        
        # Basic database connectivity check
        user_count = User.query.count()
        song_count = Song.query.count()
        analysis_count = Analysis.query.count()
        
        # Cache health
        cache_stats = get_cache_stats()
        cache_integrity = validate_cache_integrity()
        
        health_data = {
            'database': {
                'status': 'healthy',
                'users': user_count,
                'songs': song_count,
                'analyses': analysis_count
            },
            'cache': {
                'status': 'healthy' if cache_integrity['integrity_status'] == 'healthy' else 'issues_detected',
                'total_entries': cache_stats['total_entries'],
                'issues': cache_integrity.get('issues', [])
            },
            'overall_status': 'healthy'
        }
        
        # Determine overall status
        if cache_integrity['integrity_status'] != 'healthy':
            health_data['overall_status'] = 'degraded'
        
        return jsonify({
            'success': True,
            'data': health_data
        })
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to check system health',
            'data': {
                'overall_status': 'error'
            }
        }), 500


# Error handlers for the admin blueprint
@admin_bp.errorhandler(403)
def admin_forbidden(error):
    """Handle 403 Forbidden errors in admin routes."""
    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Access forbidden - admin privileges required'
        }), 403
    flash('Access forbidden - admin privileges required.', 'error')
    return redirect(url_for('auth.login'))


@admin_bp.errorhandler(404)
def admin_not_found(error):
    """Handle 404 Not Found errors in admin routes."""
    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Admin endpoint not found'
        }), 404
    flash('Admin page not found.', 'error')
    return redirect(url_for('main.index'))


@admin_bp.errorhandler(500)
def admin_internal_error(error):
    """Handle 500 Internal Server errors in admin routes."""
    logger.error(f"Internal error in admin route: {error}")
    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
    flash('An internal error occurred.', 'error')
    return redirect(url_for('main.index')) 