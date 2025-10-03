"""
Authentication routes for Spotify OAuth integration
"""

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from .. import db
from ..models import User
from ..utils.ga4 import send_event_async

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.before_app_request
def check_user_needs_reauth():
    """Check if authenticated user needs to re-authenticate"""
    if current_user.is_authenticated:
        # Skip check for auth and logout routes
        if request.endpoint and (
            request.endpoint.startswith('auth.') or 
            request.endpoint in ['static', 'main.index']
        ):
            return
        
        # Check if user needs re-authentication (30 days)
        if current_user.needs_reauth(days_threshold=30):
            logout_user()
            session.clear()
            flash("For your security, please log in again. It's been more than 30 days since your last login.", "info")
            return redirect(url_for("auth.login"))


@bp.route("/login")
def login():
    """Initiate Spotify OAuth login"""
    # Force logout if user is already authenticated to ensure fresh OAuth flow
    if current_user.is_authenticated:
        logout_user()
        session.clear()

    # Validate required config before proceeding
    client_id = current_app.config.get("SPOTIFY_CLIENT_ID")
    client_secret = current_app.config.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = current_app.config.get("SPOTIFY_REDIRECT_URI")

    if not client_id:
        flash("Spotify client ID not configured. Please contact the administrator.", "error")
        return redirect(url_for("main.index"))

    if not client_secret or client_secret in [
        "your-spotify-client-secret-here",
        "REQUIRED_SPOTIFY_CLIENT_SECRET_FROM_DEVELOPER_DASHBOARD",
    ]:
        flash(
            "Spotify client secret not configured. Please set SPOTIFY_CLIENT_SECRET in your environment variables.",
            "error",
        )
        return redirect(url_for("main.index"))

    if not redirect_uri:
        flash("Spotify redirect URI not configured. Please contact the administrator.", "error")
        return redirect(url_for("main.index"))

    # Generate state parameter for security
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    # Spotify OAuth parameters
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "user-read-private user-read-email playlist-read-private playlist-modify-private playlist-modify-public",
        "show_dialog": "true",  # Always show auth dialog to ensure user consent
    }

    spotify_url = "https://accounts.spotify.com/authorize?" + urlencode(params)
    return redirect(spotify_url)


@bp.route("/callback")
def callback():
    """Handle Spotify OAuth callback"""
    # Check for errors
    if "error" in request.args:
        flash(f'Spotify login error: {request.args.get("error")}', "error")
        return redirect(url_for("main.index"))

    # Verify state parameter
    if request.args.get("state") != session.get("oauth_state"):
        flash("Invalid state parameter. Please try logging in again.", "error")
        return redirect(url_for("main.index"))

    # Clean up state parameter after validation
    session.pop("oauth_state", None)

    # Exchange code for access token
    code = request.args.get("code")
    if not code:
        flash("No authorization code received from Spotify.", "error")
        return redirect(url_for("main.index"))

    try:
        # Request access token from Spotify
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": current_app.config["SPOTIFY_REDIRECT_URI"],
            "client_id": current_app.config["SPOTIFY_CLIENT_ID"],
            "client_secret": current_app.config["SPOTIFY_CLIENT_SECRET"],
        }

        token_response = requests.post(
            "https://accounts.spotify.com/api/token",
            data=token_data,
            timeout=30,  # Add timeout to prevent hanging
        )
        token_response.raise_for_status()
        token_info = token_response.json()

        # Get user info from Spotify
        headers = {"Authorization": f'Bearer {token_info["access_token"]}'}
        user_response = requests.get(
            "https://api.spotify.com/v1/me",
            headers=headers,
            timeout=30,  # Add timeout to prevent hanging
        )
        user_response.raise_for_status()
        spotify_user = user_response.json()

        # Create or update user in database
        user, is_new_user = _get_or_create_user(spotify_user, token_info)

        # Update last_login timestamp
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        
        # Log the user in with permanent session
        login_user(user, remember=True)
        session.permanent = True
        current_app.logger.info(f"User {user.id} logged in successfully")

        # Handle automatic sync and analysis
        try:
            if is_new_user:
                _handle_new_user_sync(user)
            else:
                _handle_returning_user_sync(user)
        except Exception as e:
            current_app.logger.error(f"Sync/analysis failed for user {user.id}: {e}")
            flash(f"Welcome, {user.display_name}! Please try syncing your playlists from the dashboard.", "warning")

        # Fire GA4 server-side conversion (best-effort, async)
        try:
            send_event_async(
                current_app, "login_success", {"method": "spotify"}, user_id=str(user.id)
            )
        except Exception:
            pass

        # Redirect to dashboard with login success flag for frontend conversion tracking
        return redirect(url_for("main.dashboard", login="success"))

    except requests.RequestException as e:
        error_msg = str(e)
        if "invalid_client" in error_msg.lower():
            current_app.logger.error(f"Spotify invalid client error: {e}")
            flash("Invalid Spotify credentials. Please check your client ID and secret configuration.", "error")
        elif "invalid_grant" in error_msg.lower():
            current_app.logger.error(f"Spotify invalid grant error: {e}")
            flash("Authorization code expired or invalid. Please try logging in again.", "error")
        else:
            current_app.logger.error(f"Spotify API error during authentication: {e}")
            flash("Error communicating with Spotify. Please try again.", "error")
        return redirect(url_for("main.index"))
    except Exception as e:
        current_app.logger.error(f"Authentication error: {e}")
        db.session.rollback()
        flash("An error occurred during login. Please try again.", "error")
        return redirect(url_for("main.index"))


def _get_or_create_user(spotify_user, token_info):
    """Create or update user with Spotify data and tokens"""
    user = User.query.filter_by(spotify_id=spotify_user["id"]).first()
    is_new_user = False
    
    if not user:
        user = User(
            spotify_id=spotify_user["id"],
            display_name=spotify_user.get("display_name", spotify_user["id"]),
            email=spotify_user.get("email"),
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(user)
        is_new_user = True

    # Update tokens and user info (tokens are automatically encrypted via setters)
    user.set_access_token(token_info["access_token"])
    user.set_refresh_token(token_info.get("refresh_token"))
    user.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=token_info["expires_in"])
    user.display_name = spotify_user.get("display_name", spotify_user["id"])
    user.email = spotify_user.get("email")
    user.updated_at = datetime.now(timezone.utc)

    # Commit user data before login
    db.session.commit()
    return user, is_new_user


def _handle_new_user_sync(user):
    """Handle full sync for new users and prepare modal confirmation"""
    from ..services.playlist_sync_service import PlaylistSyncService
    
    current_app.logger.info(f"Starting automatic sync for new user {user.id}")
    
    sync_service = PlaylistSyncService()
    sync_result = sync_service.sync_user_playlists(user)
    
    if sync_result["status"] == "completed":
        playlists_count = sync_result.get("playlists_synced", 0)
        tracks_count = sync_result.get("total_tracks", 0)
        
        current_app.logger.info(f'Synced {playlists_count} playlists with {tracks_count} tracks for new user {user.id}')
        
        # Store sync info in session for modal display
        session['show_analysis_modal'] = True
        session['sync_info'] = {
            'playlists_count': playlists_count,
            'tracks_count': tracks_count,
            'is_new_user': True
        }
        
        flash(f"Welcome, {user.display_name}! Successfully synced {playlists_count} playlists with {tracks_count} songs.", "success")
    else:
        current_app.logger.error(f'Sync failed for new user {user.id}: {sync_result.get("error")}')
        flash(f"Welcome, {user.display_name}! There was an issue syncing your playlists. You can try again from the dashboard.", "warning")


def _handle_returning_user_sync(user):
    """Handle change detection and incremental sync for returning users"""
    from ..services.playlist_sync_service import PlaylistSyncService
    from ..services.unified_analysis_service import UnifiedAnalysisService
    
    current_app.logger.info(f"Checking for playlist changes for returning user {user.id}")
    
    sync_service = PlaylistSyncService()
    analysis_service = UnifiedAnalysisService()
    
    try:
        # Check for changes first
        change_result = analysis_service.detect_playlist_changes(user.id)
        
        if change_result.get("success") and change_result.get("total_changed", 0) > 0:
            # Changes detected - sync changed playlists
            current_app.logger.info(f'Detected {change_result["total_changed"]} changed playlists for user {user.id}')
            
            sync_result = sync_service.sync_user_playlists(user)
            
            if sync_result["status"] == "completed":
                tracks_count = sync_result.get("total_tracks", 0)
                
                # Store sync info in session for modal display
                session['show_analysis_modal'] = True
                session['sync_info'] = {
                    'playlists_count': change_result["total_changed"],
                    'tracks_count': tracks_count,
                    'is_new_user': False,
                    'is_update': True
                }
                
                flash(f'Welcome back, {user.display_name}! Updated {change_result["total_changed"]} playlists with changes.', "success")
            else:
                flash(f"Welcome back, {user.display_name}! Detected playlist changes but sync failed.", "warning")
        else:
            # No changes detected - check for unanalyzed songs
            try:
                unanalyzed_count = analysis_service.get_unanalyzed_songs_count(user.id)
                if unanalyzed_count > 0:
                    # Store info for modal
                    session['show_analysis_modal'] = True
                    session['sync_info'] = {
                        'unanalyzed_count': unanalyzed_count,
                        'is_new_user': False,
                        'is_resume': True
                    }
                    flash(f"Welcome back, {user.display_name}! Found {unanalyzed_count} unanalyzed songs.", "success")
                else:
                    flash(f"Welcome back, {user.display_name}! Everything is up to date.", "success")
            except Exception as e:
                current_app.logger.warning(f"Background analysis check failed for user {user.id}: {e}")
                flash(f"Welcome back, {user.display_name}! No playlist changes detected.", "success")
    except Exception as e:
        current_app.logger.warning(f"Change detection failed for user {user.id}: {e}")
        flash(f"Welcome back, {user.display_name}! Unable to check for changes. You can manually sync from the dashboard.", "warning")




    except requests.RequestException as e:
        error_msg = str(e)
        if "invalid_client" in error_msg.lower():
            current_app.logger.error(f"Spotify invalid client error: {e}")
            flash(
                "Invalid Spotify credentials. Please check your client ID and secret configuration.",
                "error",
            )
        elif "invalid_grant" in error_msg.lower():
            current_app.logger.error(f"Spotify invalid grant error: {e}")
            flash("Authorization code expired or invalid. Please try logging in again.", "error")
        elif "400" in error_msg:
            current_app.logger.error(f"Spotify API 400 error: {e}")
            flash(
                "Bad request to Spotify API. Please check your configuration and try again.",
                "error",
            )
        elif "401" in error_msg:
            current_app.logger.error(f"Spotify API 401 error: {e}")
            flash(
                "Unauthorized Spotify API request. Please check your client credentials.", "error"
            )
        else:
            current_app.logger.error(f"Spotify API error during authentication: {e}")
            flash("Error communicating with Spotify. Please try again.", "error")
        return redirect(url_for("main.index"))
    except Exception as e:
        current_app.logger.error(f"Authentication error: {e}")
        db.session.rollback()
        flash("An error occurred during login. Please try again.", "error")
        return redirect(url_for("main.index"))


@bp.route("/logout")
def logout():
    """Log out the current user"""
    from flask import make_response
    
    was_authenticated = current_user.is_authenticated
    
    # Revoke Spotify tokens before logging out
    if was_authenticated and current_user.get_access_token():
        try:
            _revoke_spotify_tokens(current_user)
        except Exception as e:
            current_app.logger.warning(f"Failed to revoke Spotify tokens for user {current_user.id}: {e}")
    
    if was_authenticated:
        logout_user()
    
    # Clear server-side session data completely
    session.clear()
    
    # Create response and clear all cookies
    response = make_response(redirect(url_for("auth.logout_success")))
    
    # Clear Flask-Login session cookie
    response.set_cookie('session', '', expires=0, path='/')
    response.set_cookie('remember_token', '', expires=0, path='/')
    
    # Clear any other session-related cookies
    for cookie_name in request.cookies:
        response.set_cookie(cookie_name, '', expires=0, path='/')
    
    if was_authenticated:
        flash("You have been logged out successfully.", "info")
    else:
        flash("You are not currently logged in.", "info")
    
    return response


@bp.route("/logout-success")
def logout_success():
    """Logout success page - ensures clean logged-out state"""
    from flask import make_response
    
    # Double-check that user is actually logged out
    if current_user.is_authenticated:
        logout_user()
        session.clear()
    
    # Create response and ensure no caching
    response = make_response(render_template("auth/logout_success.html"))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@bp.route("/refresh_token")
@login_required
def refresh_token():
    """Refresh the user's Spotify access token"""
    if not current_user.refresh_token:
        flash("No refresh token available. Please log in again.", "error")
        return redirect(url_for("auth.logout"))

    try:
        token_data = {
            "grant_type": "refresh_token",
            "refresh_token": current_user.refresh_token,
            "client_id": current_app.config["SPOTIFY_CLIENT_ID"],
            "client_secret": current_app.config["SPOTIFY_CLIENT_SECRET"],
        }

        token_response = requests.post(
            "https://accounts.spotify.com/api/token", data=token_data, timeout=30
        )
        token_response.raise_for_status()
        token_info = token_response.json()

        # Update tokens
        current_user.access_token = token_info["access_token"]
        if "refresh_token" in token_info:
            current_user.refresh_token = token_info["refresh_token"]
        current_user.token_expiry = datetime.now(timezone.utc) + timedelta(
            seconds=token_info["expires_in"]
        )
        current_user.updated_at = datetime.now(timezone.utc)

        db.session.commit()
        flash("Token refreshed successfully.", "success")

    except requests.RequestException as e:
        current_app.logger.error(f"Token refresh error: {e}")
        flash("Error refreshing token. Please log in again.", "error")
        return redirect(url_for("auth.logout"))
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {e}")
        flash("An error occurred refreshing your token. Please log in again.", "error")
        return redirect(url_for("auth.logout"))

    return redirect(request.referrer or url_for("main.dashboard"))


@bp.route("/mock-login/<user_id>")
def mock_login(user_id):
    """Mock login for testing purposes - only works in development"""
    if not current_app.debug:
        flash("Mock login is only available in development mode", "error")
        return redirect(url_for("main.dashboard"))

    # Find the test user
    user = User.query.filter_by(spotify_id=user_id).first()
    if not user:
        flash(f"Test user {user_id} not found. Please run the mock data script first.", "error")
        return redirect(url_for("main.index"))

    # Log in the user
    login_user(user)
    flash(f"Logged in as test user: {user.display_name}", "success")
    return redirect(url_for("main.dashboard"))


@bp.route("/config-status")
def config_status():
    """Show configuration status for debugging (development only)"""
    if not current_app.debug:
        flash("Configuration status is only available in development mode", "error")
        return redirect(url_for("main.index"))

    client_id = current_app.config.get("SPOTIFY_CLIENT_ID")
    client_secret = current_app.config.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = current_app.config.get("SPOTIFY_REDIRECT_URI")

    config_status = {
        "client_id": {
            "status": "SET" if client_id else "MISSING",
            "length": len(client_id) if client_id else 0,
            "value": client_id[:8] + "..." if client_id and len(client_id) > 8 else client_id,
        },
        "client_secret": {
            "status": "SET" if client_secret else "MISSING",
            "length": len(client_secret) if client_secret else 0,
            "is_placeholder": client_secret
            in [
                "your-spotify-client-secret-here",
                "REQUIRED_SPOTIFY_CLIENT_SECRET_FROM_DEVELOPER_DASHBOARD",
            ]
            if client_secret
            else False,
            "value": "***HIDDEN***"
            if client_secret and not client_secret.startswith(("your-", "REQUIRED_"))
            else client_secret,
        },
        "redirect_uri": {"status": "SET" if redirect_uri else "MISSING", "value": redirect_uri},
    }

    return jsonify(
        {
            "spotify_config": config_status,
            "ready_for_oauth": all(
                [
                    client_id,
                    client_secret,
                    client_secret
                    not in [
                        "your-spotify-client-secret-here",
                        "REQUIRED_SPOTIFY_CLIENT_SECRET_FROM_DEVELOPER_DASHBOARD",
                    ],
                    redirect_uri,
                ]
            ),
        }
    )


def _revoke_spotify_tokens(user):
    """Revoke Spotify access and refresh tokens"""
    try:
        access_token = user.get_access_token()
        
        if not access_token:
            return
        
        # Revoke access token
        revoke_data = {
            "token": access_token,
            "token_type_hint": "access_token",
            "client_id": current_app.config["SPOTIFY_CLIENT_ID"],
            "client_secret": current_app.config["SPOTIFY_CLIENT_SECRET"],
        }
        
        requests.post(
            "https://accounts.spotify.com/api/token/revoke",
            data=revoke_data,
            timeout=10,
        )
        
        # Note: Spotify's revoke endpoint may return 200 even if token is already invalid
        # This is expected behavior - we don't need to check the response
        current_app.logger.info(f"Revoked Spotify tokens for user {user.id}")
        
    except Exception as e:
        current_app.logger.error(f"Error revoking Spotify tokens for user {user.id}: {e}")
        raise


@bp.route("/mock-users")
def mock_users():
    """Show available mock users for testing"""
    if not current_app.debug:
        flash("Mock login is only available in development mode", "error")
        return redirect(url_for("main.dashboard"))

    # Get all test users
    test_users = User.query.filter(User.spotify_id.like("test_user_%")).all()

    if not test_users:
        flash("No test users found. Please run the mock data script first.", "info")
        return redirect(url_for("main.index"))

    return render_template("auth/mock_users.html", users=test_users)
