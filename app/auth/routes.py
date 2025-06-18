from flask import flash, redirect, url_for, render_template
from flask_login import login_user
from flask_app import auth_bp
from flask_app.models.user import User
from flask_app.utils import current_app

@auth_bp.route('/mock-login/<user_id>')
def mock_login(user_id):
    """Mock login for testing purposes - only works in development"""
    if not current_app.debug:
        flash('Mock login is only available in development mode', 'error')
        return redirect(url_for('core.dashboard'))
    
    # Find the test user
    user = User.query.filter_by(spotify_id=user_id).first()
    if not user:
        flash(f'Test user {user_id} not found. Please run the mock data script first.', 'error')
        return redirect(url_for('core.index'))
    
    # Log in the user
    login_user(user)
    flash(f'Logged in as test user: {user.display_name}', 'success')
    return redirect(url_for('core.dashboard'))

@auth_bp.route('/mock-users')
def mock_users():
    """Show available mock users for testing"""
    if not current_app.debug:
        flash('Mock login is only available in development mode', 'error')
        return redirect(url_for('core.dashboard'))
    
    # Get all test users
    test_users = User.query.filter(User.spotify_id.like('test_user_%')).all()
    
    if not test_users:
        flash('No test users found. Please run the mock data script first.', 'info')
        return redirect(url_for('core.index'))
    
    return render_template('auth/mock_users.html', users=test_users) 