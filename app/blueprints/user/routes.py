"""
User Blueprint Routes - User settings and profile management.

This file contains the routes for:
- User settings viewing and updating
- User preferences management
- Whitelist/blacklist management page
"""

from flask import render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_required, current_user as flask_login_current_user

# Import the blueprint
from . import user_bp

# Import required modules
from app import db
from app.models import User, Whitelist, Blacklist
from app.auth.decorators import spotify_token_required

@user_bp.route('/settings')
@login_required
def user_settings():
    """Display user settings page."""
    try:
        user = flask_login_current_user
        
        # Get user preferences/settings
        settings_data = {
            'user_id': user.id,
            'email': user.email,
            'display_name': user.display_name,
            'created_at': user.created_at,
            'last_login': getattr(user, 'last_login', None),
            'preferences': {
                # Add any user preference fields here
                # These might be stored in the user model or a separate preferences table
            }
        }
        
        return render_template('user_settings.html', user=settings_data)
        
    except Exception as e:
        current_app.logger.error(f"Error loading user settings: {e}")
        flash(f"Error loading settings: {str(e)}", 'error')
        return redirect(url_for('core.dashboard'))

@user_bp.route('/settings', methods=['POST'])
@login_required
def update_user_settings():
    """Update user settings and preferences."""
    try:
        user = flask_login_current_user
        
        # Get form data
        display_name = request.form.get('display_name', '').strip()
        
        # Validate inputs
        if display_name and len(display_name) > 100:
            flash('Display name too long (max 100 characters)', 'error')
            return redirect(url_for('user.user_settings'))
        
        # Update user fields
        if display_name:
            user.display_name = display_name
        
        # Add any other preference updates here
        # For example:
        # user.preference_field = request.form.get('preference_field')
        
        db.session.commit()
        
        current_app.logger.info(f"Updated settings for user {user.id}")
        flash('Settings updated successfully!', 'success')
        
        return redirect(url_for('user.user_settings'))
        
    except Exception as e:
        current_app.logger.error(f"Error updating user settings: {e}")
        db.session.rollback()
        flash(f"Error updating settings: {str(e)}", 'error')
        return redirect(url_for('user.user_settings'))

@user_bp.route('/blacklist-whitelist')
@login_required
@spotify_token_required
def blacklist_whitelist():
    """Display the blacklist and whitelist management page."""
    try:
        user_id = flask_login_current_user.id
        
        # Get whitelist items for the user
        whitelist_items = Whitelist.query.filter_by(user_id=user_id).order_by(Whitelist.created_at.desc()).all()
        
        # Get blacklist items for the user
        blacklist_items = Blacklist.query.filter_by(user_id=user_id).order_by(Blacklist.created_at.desc()).all()
        
        # Format items for template
        whitelist_data = []
        for item in whitelist_items:
            whitelist_data.append({
                'id': item.id,
                'type': item.item_type,
                'name': item.name,
                'artist': item.artist,
                'spotify_id': item.spotify_id,
                'created_at': item.created_at
            })
        
        blacklist_data = []
        for item in blacklist_items:
            blacklist_data.append({
                'id': item.id,
                'type': item.item_type,
                'name': item.name,
                'artist': item.artist,
                'spotify_id': item.spotify_id,
                'created_at': item.created_at
            })
        
        return render_template(
            'blacklist_whitelist.html',
            whitelist_items=whitelist_data,
            blacklist_items=blacklist_data,
            whitelist_count=len(whitelist_data),
            blacklist_count=len(blacklist_data)
        )
        
    except Exception as e:
        current_app.logger.error(f"Error loading blacklist/whitelist page: {e}")
        flash(f"Error loading page: {str(e)}", 'error')
        return redirect(url_for('core.dashboard'))
