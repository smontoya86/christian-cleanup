"""
System Blueprint Routes - System health, monitoring, and utility functions.

This file contains the routes for:
- System health checks
- Sync status monitoring  
- Authentication status checks
- System monitoring dashboard
"""

from flask import render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_required, current_user as flask_login_current_user
from sqlalchemy import text
from datetime import datetime

# Import the blueprint
from . import system_bp

# Import required modules
from app import db
from app.models import User, Song, AnalysisResult, PlaylistSong, Playlist
from app.auth.decorators import spotify_token_required
from app.services.playlist_sync_service import get_sync_status

@system_bp.route('/api/sync-status')
@login_required
def api_sync_status():
    """API endpoint to check playlist sync status."""
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

@system_bp.route('/check_auth')
@login_required
def check_auth_status():
    """Check authentication status for the current user."""
    try:
        user = flask_login_current_user
        
        auth_status = {
            'authenticated': user.is_authenticated,
            'user_id': user.id,
            'email': user.email,
            'has_spotify_token': bool(user.access_token),
            'token_expires_at': user.token_expiry.isoformat() if user.token_expiry else None
        }
        
        return jsonify(auth_status)
        
    except Exception as e:
        current_app.logger.error(f"Error checking auth status: {e}")
        return jsonify({'error': 'Failed to check authentication status'}), 500

@system_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Basic database connectivity check with SQLAlchemy 2.0 compatibility
        db.session.execute(text('SELECT 1'))
        
        health_status = {
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(health_status), 200
        
    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'database': 'disconnected'
        }), 500

@system_bp.route('/monitoring')
@login_required
def monitoring_dashboard():
    """Display the monitoring dashboard for system observability."""
    # For now, allow any authenticated user
    # In production, you might want to check for admin role
    return render_template('monitoring.html')
