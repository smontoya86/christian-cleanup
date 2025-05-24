from functools import wraps
from flask import redirect, url_for, session, flash, request, current_app
from flask_login import current_user, login_required

def spotify_token_required(f):
    """
    Ensures that the current user is authenticated with Flask-Login
    and has a valid (or refreshable) Spotify access token.
    Must be applied *after* @login_required if used together, or handle
    login_required logic internally (as done here for simplicity).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_app.logger.debug("spotify_token_required DECORATOR ENTERED")

        # First, ensure the user is actually logged in before checking token
        # This check is needed now that the inner @login_required is removed.
        if not current_user.is_authenticated:
            current_app.logger.warning("spotify_token_required accessed by unauthenticated user.")
            flash('Please log in to access this page.', 'warning')
            session['next_url'] = request.url 
            return redirect(url_for('auth.login'))
            
        # Get user ID safely without triggering database access
        try:
            user_id = getattr(current_user, 'spotify_id', 'unknown') if hasattr(current_user, 'spotify_id') else 'unknown'
        except Exception:
            user_id = 'unknown'
        current_app.logger.debug(f"spotify_token_required: User {user_id} is authenticated.")

        if not hasattr(current_user, 'ensure_token_valid'):
            current_app.logger.error("spotify_token_required: current_user lacks 'ensure_token_valid'. Logging out.")
            # Log error, redirect (unlikely path based on previous logs)
            current_app.logger.error("current_user does not have 'ensure_token_valid' method. Logging out.") # Keep this one as logger for now
            if current_user.is_authenticated:
                 from flask_login import logout_user
                 logout_user()
            flash('Authentication error. Please log in again.', 'danger')
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))

        current_app.logger.debug(f"spotify_token_required: Checking token for user {user_id}. Method exists: {hasattr(current_user, 'ensure_token_valid')}")

        token_is_valid = False # Default
        try:
            token_is_valid = current_user.ensure_token_valid() # Call it explicitly
            current_app.logger.debug(f"spotify_token_required: ensure_token_valid() returned: {token_is_valid}")
        except Exception as e:
             current_app.logger.error(f"spotify_token_required: Exception calling ensure_token_valid: {e}", exc_info=True)

        if not token_is_valid:
            current_app.logger.error("spotify_token_required: Token validation FAILED. Redirecting.")
            flash('Your Spotify session seems to have expired. Please log in again.', 'warning')
            session.clear() 
            session['next_url'] = request.url 
            return redirect(url_for('auth.login'))
        
        current_app.logger.debug(f"Spotify token check passed for user {user_id} for route {request.path}.") # Adjusted user ID attribute
        return f(*args, **kwargs)
    return decorated_function
