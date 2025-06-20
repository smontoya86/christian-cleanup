"""
Authentication routes for Spotify OAuth integration
"""

from flask import Blueprint, request, redirect, url_for, session, flash, current_app, render_template
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlencode
import secrets
import requests
from datetime import datetime, timezone, timedelta

from .. import db
from ..models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login')
def login():
    """Initiate Spotify OAuth login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # Generate state parameter for security
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Spotify OAuth parameters
    params = {
        'client_id': current_app.config['SPOTIFY_CLIENT_ID'],
        'response_type': 'code',
        'redirect_uri': current_app.config['SPOTIFY_REDIRECT_URI'],
        'state': state,
        'scope': 'user-read-private user-read-email playlist-read-private playlist-modify-private playlist-modify-public',
        'show_dialog': 'false'
    }
    
    spotify_url = 'https://accounts.spotify.com/authorize?' + urlencode(params)
    return redirect(spotify_url)


@bp.route('/callback')
def callback():
    """Handle Spotify OAuth callback"""
    # Check for errors
    if 'error' in request.args:
        flash(f'Spotify login error: {request.args.get("error")}', 'error')
        return redirect(url_for('main.index'))
    
    # Verify state parameter
    if request.args.get('state') != session.get('oauth_state'):
        flash('Invalid state parameter. Please try logging in again.', 'error')
        return redirect(url_for('main.index'))
    
    # Exchange code for access token
    code = request.args.get('code')
    if not code:
        flash('No authorization code received from Spotify.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Request access token from Spotify
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': current_app.config['SPOTIFY_REDIRECT_URI'],
            'client_id': current_app.config['SPOTIFY_CLIENT_ID'],
            'client_secret': current_app.config['SPOTIFY_CLIENT_SECRET']
        }
        
        token_response = requests.post(
            'https://accounts.spotify.com/api/token',
            data=token_data,
            timeout=30  # Add timeout to prevent hanging
        )
        token_response.raise_for_status()
        token_info = token_response.json()
        
        # Get user info from Spotify
        headers = {'Authorization': f'Bearer {token_info["access_token"]}'}
        user_response = requests.get(
            'https://api.spotify.com/v1/me', 
            headers=headers,
            timeout=30  # Add timeout to prevent hanging
        )
        user_response.raise_for_status()
        spotify_user = user_response.json()
        
        # Create or update user in database
        user = User.query.filter_by(spotify_id=spotify_user['id']).first()
        if not user:
            user = User(
                spotify_id=spotify_user['id'],
                display_name=spotify_user.get('display_name', spotify_user['id']),
                email=spotify_user.get('email'),
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(user)
        
        # Update tokens and user info
        user.access_token = token_info['access_token']
        user.refresh_token = token_info.get('refresh_token')
        user.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=token_info['expires_in'])
        user.display_name = spotify_user.get('display_name', spotify_user['id'])
        user.email = spotify_user.get('email')
        user.updated_at = datetime.now(timezone.utc)
        
        # Commit user data before login
        db.session.commit()
        
        # Log the user in
        login_user(user, remember=True)
        current_app.logger.info(f'User {user.id} logged in successfully')
        
        # Queue playlist sync as background job instead of synchronous sync
        try:
            from ..services.playlist_sync_service import enqueue_user_playlist_sync
            job_info = enqueue_user_playlist_sync(user.id, priority='high')
            
            if job_info['status'] == 'queued':
                current_app.logger.info(f'Queued playlist sync job {job_info["job_id"]} for user {user.id}')
                flash(f'Welcome, {user.display_name}! Your playlists are being synced in the background. This may take a few minutes.', 'success')
            else:
                current_app.logger.error(f'Failed to queue playlist sync for user {user.id}: {job_info.get("error")}')
                # Fall back to synchronous sync
                try:
                    from ..services.spotify_service import SpotifyService
                    spotify = SpotifyService(user)
                    count = spotify.sync_user_playlists()
                    flash(f'Welcome, {user.display_name}! Successfully synced {count} playlists from Spotify.', 'success')
                except Exception as sync_e:
                    current_app.logger.error(f'Synchronous playlist sync failed for user {user.id}: {sync_e}')
                    flash(f'Welcome, {user.display_name}! Login successful. You can manually sync playlists from the dashboard.', 'warning')
                
        except Exception as e:
            current_app.logger.error(f'Error queueing playlist sync for user {user.id}: {e}')
            # Fall back to synchronous sync
            try:
                from ..services.spotify_service import SpotifyService
                spotify = SpotifyService(user)
                count = spotify.sync_user_playlists()
                flash(f'Welcome, {user.display_name}! Successfully synced {count} playlists from Spotify.', 'success')
            except Exception as sync_e:
                current_app.logger.error(f'Synchronous playlist sync failed for user {user.id}: {sync_e}')
                flash(f'Welcome, {user.display_name}! Login successful. You can manually sync playlists from the dashboard.', 'warning')
        
        # Redirect to dashboard
        return redirect(url_for('main.dashboard'))
        
    except requests.RequestException as e:
        current_app.logger.error(f'Spotify API error during authentication: {e}')
        flash('Error communicating with Spotify. Please try again.', 'error')
        return redirect(url_for('main.index'))
    except Exception as e:
        current_app.logger.error(f'Authentication error: {e}')
        db.session.rollback()
        flash('An error occurred during login. Please try again.', 'error')
        return redirect(url_for('main.index'))


@bp.route('/logout')
def logout():
    """Log out the current user"""
    if current_user.is_authenticated:
        logout_user()
        flash('You have been logged out successfully.', 'info')
    else:
        flash('You are not currently logged in.', 'info')
    return redirect(url_for('main.index'))


@bp.route('/refresh_token')
@login_required
def refresh_token():
    """Refresh the user's Spotify access token"""
    if not current_user.refresh_token:
        flash('No refresh token available. Please log in again.', 'error')
        return redirect(url_for('auth.logout'))
    
    try:
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': current_user.refresh_token,
            'client_id': current_app.config['SPOTIFY_CLIENT_ID'],
            'client_secret': current_app.config['SPOTIFY_CLIENT_SECRET']
        }
        
        token_response = requests.post(
            'https://accounts.spotify.com/api/token',
            data=token_data,
            timeout=30
        )
        token_response.raise_for_status()
        token_info = token_response.json()
        
        # Update tokens
        current_user.access_token = token_info['access_token']
        if 'refresh_token' in token_info:
            current_user.refresh_token = token_info['refresh_token']
        current_user.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=token_info['expires_in'])
        current_user.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        flash('Token refreshed successfully.', 'success')
        
    except requests.RequestException as e:
        current_app.logger.error(f'Token refresh error: {e}')
        flash('Error refreshing token. Please log in again.', 'error')
        return redirect(url_for('auth.logout'))
    except Exception as e:
        current_app.logger.error(f'Token refresh error: {e}')
        flash('An error occurred refreshing your token. Please log in again.', 'error')
        return redirect(url_for('auth.logout'))
    
    return redirect(request.referrer or url_for('main.dashboard'))


@bp.route('/mock-login/<user_id>')
def mock_login(user_id):
    """Mock login for testing purposes - only works in development"""
    if not current_app.debug:
        flash('Mock login is only available in development mode', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Find the test user
    user = User.query.filter_by(spotify_id=user_id).first()
    if not user:
        flash(f'Test user {user_id} not found. Please run the mock data script first.', 'error')
        return redirect(url_for('main.index'))
    
    # Log in the user
    login_user(user)
    flash(f'Logged in as test user: {user.display_name}', 'success')
    return redirect(url_for('main.dashboard'))


@bp.route('/mock-users')
def mock_users():
    """Show available mock users for testing"""
    if not current_app.debug:
        flash('Mock login is only available in development mode', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Get all test users
    test_users = User.query.filter(User.spotify_id.like('test_user_%')).all()
    
    if not test_users:
        flash('No test users found. Please run the mock data script first.', 'info')
        return redirect(url_for('main.index'))
    
    return render_template('auth/mock_users.html', users=test_users)