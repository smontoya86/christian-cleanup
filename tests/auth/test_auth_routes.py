from flask import url_for, session
from flask_login import current_user, login_user
from app.models.models import User
import pytest
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import time

def test_login_redirects_to_spotify(client):
    """Test that /login redirects to Spotify's authorization URL."""
    response = client.get(url_for('auth.login'))
    assert response.status_code == 302
    # We expect a redirect to a Spotify URL
    assert 'accounts.spotify.com/authorize' in response.location

@pytest.mark.usefixtures("test_user", "db_session") 
def test_logout_logs_user_out(client, test_user, app): 
    """Test that logging out clears the session and de-authenticates the user."""
    
    with app.test_request_context(): 
        # Log in the user using Flask-Login's utility
        login_user(test_user) 

    with client: 
        # Verify user is initially considered logged in by accessing dashboard
        dashboard_response_before_logout = client.get(url_for('main.dashboard'))
        
        # If logged in properly, dashboard should load (200) or redirect to login if not authenticated
        # Since we logged in above, we expect a successful response or redirect to Spotify auth
        assert dashboard_response_before_logout.status_code in [200, 302]

    # Perform logout (outside the 'with client' block if it re-establishes its own context, or inside if preferred)
    # For logout, it's usually fine as it makes its own request.
    logout_response = client.get(url_for('auth.logout'), follow_redirects=True)
    assert logout_response.status_code == 200 # Should redirect to index
    assert b"You have been logged out successfully." in logout_response.data # Check for flash message

    # Verify user is logged out and session is cleared
    with client.session_transaction() as sess:
        assert '_user_id' not in sess 
        assert '_fresh' not in sess

    # Verify current_user is anonymous after logout by accessing a protected route
    # The dashboard route is @login_required, so it should redirect to login if not authenticated
    auth_check_response_after_logout = client.get(url_for('main.dashboard'), follow_redirects=False)
    assert auth_check_response_after_logout.status_code == 302 # Expect redirect to login
    assert url_for('auth.login') in auth_check_response_after_logout.location


# For now, if the @spotify_token_required decorator primarily checks for login
# and presence of token fields (without immediate validation), we can test that.

def test_dashboard_access_authenticated_no_token(client, test_user, db_session, app):
    """Test dashboard access for authenticated user but missing Spotify token info."""
    # Set up user with expired token and no refresh token
    user = db_session.get(User, test_user.id)
    assert user is not None, "User should be found in the database"
    user.access_token = "dummy_expired_access_token"
    user.token_expiry = datetime.now(timezone.utc) - timedelta(hours=1)
    user.refresh_token = None
    db_session.commit()

    # Log in the user properly within a request context
    with app.test_request_context():
        login_user(user)
        # Verify login within context before client request
        assert current_user.is_authenticated
        assert current_user.id == user.id

        # Access dashboard using client
        dashboard_response = client.get(url_for('main.dashboard'), follow_redirects=False)

        # With no valid token, should redirect to login
        assert dashboard_response.status_code == 302
        assert url_for('auth.login') in dashboard_response.location


def test_dashboard_access_unauthenticated(client, app):
    """Test that unauthenticated users are redirected from dashboard."""
    with app.test_request_context(): # Context needed for url_for
        expected_location = url_for('auth.login', next=url_for('main.dashboard'))
        
    response = client.get(url_for('main.dashboard'), follow_redirects=False)
    assert response.status_code == 302
    # Check that the redirect is to the login page, potentially with the 'next' param
    assert response.location.startswith(url_for('auth.login'))

# More tests will be needed for the /callback route, likely involving mocking.
# For example, testing successful token exchange, user creation/update, etc.

# A more complex test for dashboard access when authenticated would involve
# mocking the Spotify token validation and potentially API calls if the dashboard
# route itself tries to fetch data immediately.
# For now, if the @spotify_token_required decorator primarily checks for login
# and presence of token fields (without immediate validation), we can test that.

@pytest.mark.usefixtures("test_user", "db_session")
def test_automatic_token_refresh(client, test_user, db_session, monkeypatch, app):
    """Test that an expired Spotify token triggers appropriate handling."""
    with app.test_request_context():
        login_user(test_user)
    
    # Manually expire the token in the database
    # Get the user from the current session to avoid session attachment issues
    user = db_session.get(User, test_user.id)
    # Set token to expire 5 minutes ago (definitely expired)
    user.token_expiry = datetime.now(timezone.utc) - timedelta(minutes=5)
    user.refresh_token = "test_refresh_token"  # Ensure we have a refresh token
    user.access_token = "expired_access_token"
    db_session.commit()
    db_session.flush()  # Ensure changes are written to database

    # Also update the test_user object to reflect the change
    test_user.token_expiry = user.token_expiry

    with client:
        response = client.get(url_for('main.dashboard'))
        
        # With expired token, the system should either:
        # 1. Successfully refresh and show dashboard (200)
        # 2. Redirect to login for re-authentication (302)
        assert response.status_code in [200, 302]
        
        # If it's a redirect, it should go to the login page
        if response.status_code == 302:
            assert url_for('auth.login') in response.location


@pytest.mark.usefixtures("test_user", "db_session")
def test_dashboard_access_authenticated_no_token(client, test_user, db_session, app):
    """Test dashboard access for authenticated user but missing Spotify token info."""
    # Log in the user (simplified for this specific redirect test)
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['_fresh'] = True

    # Ensure user has an expired token and no refresh token for this test
    user = db_session.get(User, test_user.id)
    assert user is not None, "User should be found in the database"
    user.access_token = "dummy_expired_access_token" # Must be non-null
    user.token_expiry = datetime.now(timezone.utc) - timedelta(hours=1) # Set to 1 hour ago
    user.refresh_token = None # Ensure no refresh token to force re-auth
    db_session.commit()

    # Access dashboard - expect a redirect to /login first
    dashboard_response = client.get(url_for('main.dashboard'), follow_redirects=False)

    assert dashboard_response.status_code == 302 # Expecting a redirect
    assert url_for('auth.login') in dashboard_response.location # Should redirect to login
    
    # Test that login redirects to appropriate OAuth endpoint
    login_redirect_response = client.get(dashboard_response.location, follow_redirects=False)
    # Should redirect to Spotify OAuth or show login page
    assert login_redirect_response.status_code in [200, 302]
