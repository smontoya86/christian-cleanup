from flask import redirect, url_for, request, session, current_app, flash
from . import auth 
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime
import os

from app.extensions import db
from app.models.models import User
from flask_login import login_user, logout_user, login_required, current_user

def get_spotify_oauth():
    client_id = current_app.config.get('SPOTIPY_CLIENT_ID')
    client_secret = current_app.config.get('SPOTIPY_CLIENT_SECRET')
    redirect_uri = current_app.config.get('SPOTIPY_REDIRECT_URI')
    scopes = current_app.config.get('SPOTIFY_SCOPES')

    # Debugging: Log the values
    current_app.logger.debug(f"SPOTIPY_CLIENT_ID: {client_id}")
    current_app.logger.debug(f"SPOTIPY_CLIENT_SECRET: {'*' * 5 + client_secret[-5:] if client_secret else None}") # Mask most of secret
    current_app.logger.debug(f"SPOTIPY_REDIRECT_URI: {redirect_uri}")
    current_app.logger.debug(f"SPOTIFY_SCOPES: {scopes}")

    if not all([client_id, client_secret, redirect_uri, scopes]):
        current_app.logger.error("Spotify API credentials, redirect URI, or scopes not configured.")
        return None

    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scopes,
        cache_path=None 
    )

@auth.route('/login')
def login():
    sp_oauth = get_spotify_oauth()
    if not sp_oauth:
        flash('Spotify authentication is not configured correctly. Please contact support.', 'danger')
        return redirect(url_for('main.index')) 

    if current_user.is_authenticated:
        logout_user() 
        session.clear() 
        current_app.logger.debug("User logged out and session cleared before new login attempt.")

    # Generate and store state for CSRF protection
    state = os.urandom(16).hex()
    session['spotify_auth_state'] = state

    # Enhanced Debugging for OAuth object
    current_app.logger.debug(f"[AUTH LOGIN] SpotifyOAuth object state before get_authorize_url:")
    current_app.logger.debug(f"[AUTH LOGIN]   Client ID: {getattr(sp_oauth, 'client_id', 'N/A')}")
    current_app.logger.debug(f"[AUTH LOGIN]   Client Secret: {'SET' if getattr(sp_oauth, 'client_secret', None) else 'NOT SET'}") # Don't log secret itself
    current_app.logger.debug(f"[AUTH LOGIN]   Redirect URI: {getattr(sp_oauth, 'redirect_uri', 'N/A')}")
    current_app.logger.debug(f"[AUTH LOGIN]   Scope: {getattr(sp_oauth, 'scope', 'N/A')}")
    current_app.logger.debug(f"[AUTH LOGIN]   State being sent: {state}")

    auth_url = sp_oauth.get_authorize_url(state=state)
    current_app.logger.info(f"Redirecting to Spotify for authorization (state: {state}, url: {auth_url})")
    return redirect(auth_url)

@auth.route('/callback')
def callback():
    sp_oauth = get_spotify_oauth()
    if not sp_oauth:
        flash('Spotify authentication is not configured correctly.', 'danger')
        return redirect(url_for('main.index'))

    error = request.args.get('error')
    if error:
        current_app.logger.error(f"Spotify authorization error: {error}")
        flash(f"Spotify authorization failed: {error}. Please try again.", 'danger')
        return redirect(url_for('auth.login'))

    # Verify state parameter for CSRF protection
    received_state = request.args.get('state')
    expected_state = session.pop('spotify_auth_state', None)

    if not received_state or received_state != expected_state:
        current_app.logger.error(f"State mismatch. Received: {received_state}, Expected: {expected_state}")
        flash('Authentication failed due to state mismatch. Please try logging in again.', 'danger')
        return redirect(url_for('auth.login'))

    code = request.args.get('code')
    if not code:
        current_app.logger.error("No authorization code received from Spotify.")
        flash('Authorization code not received from Spotify. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    try:
        token_info = sp_oauth.get_access_token(code, check_cache=False)
    except Exception as e:
        current_app.logger.error(f"Error getting access token from Spotify: {e}")
        flash('Failed to get access token from Spotify. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    if not token_info or 'access_token' not in token_info:
        current_app.logger.error("Failed to retrieve valid token_info from Spotify.")
        flash('Authentication failed: Could not retrieve valid token information.', 'danger')
        return redirect(url_for('auth.login'))

    current_app.logger.debug(f"Token info received from Spotify: { {k: v for k, v in token_info.items() if k != 'access_token' and k != 'refresh_token'} }")

    try:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        spotify_user_profile = sp.current_user()
    except Exception as e:
        current_app.logger.error(f"Error fetching user profile from Spotify: {e}")
        flash('Failed to fetch user profile from Spotify.', 'danger')
        return redirect(url_for('auth.login'))

    spotify_id = spotify_user_profile['id']
    email = spotify_user_profile.get('email') 
    display_name = spotify_user_profile.get('display_name') or spotify_id

    user = User.query.filter_by(spotify_id=spotify_id).first()

    token_expiry_timestamp = token_info['expires_at']
    token_expiry_datetime = datetime.fromtimestamp(token_expiry_timestamp)

    if user:
        user.access_token = token_info['access_token']
        user.refresh_token = token_info.get('refresh_token', user.refresh_token) 
        user.token_expiry = token_expiry_datetime
        user.email = email 
        user.display_name = display_name
        user.updated_at = datetime.utcnow()
        current_app.logger.info(f"Existing user {user.id} ({user.spotify_id}) tokens and info updated.")
    else:
        user = User(
            spotify_id=spotify_id,
            email=email,
            display_name=display_name,
            access_token=token_info['access_token'],
            refresh_token=token_info.get('refresh_token'),
            token_expiry=token_expiry_datetime
        )
        db.session.add(user)
        current_app.logger.info(f"New user {user.spotify_id} created.")
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Database error during user upsert: {e}")
        flash('An error occurred while saving user data. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    login_user(user, remember=True)
    current_app.logger.info(f"User {user.id} ({user.spotify_id}) logged in successfully.")
    flash('Successfully logged in with Spotify!', 'success')
    
    next_url = session.pop('next_url', None) 
    return redirect(next_url or url_for('main.index'))

@auth.route('/logout')
@login_required
def logout():
    user_spotify_id = current_user.spotify_id if current_user.is_authenticated else "Unknown"
    
    logout_user()
    current_app.logger.info(f"User {user_spotify_id} logged out successfully.")
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))

@auth.route('/register')
def register():
    flash('To register, please log in with Spotify.', 'info')
    return redirect(url_for('auth.login'))
