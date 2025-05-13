from flask import url_for, session
from flask_login import current_user, login_user
from app.models.models import User
import pytest
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import time

def test_login_redirects_to_spotify(client):
    """Test that /login redirects to Spotify's authorization URL."""
    response = client.get(url_for('auth.login'))
    assert response.status_code == 302
    # We expect a redirect to a Spotify URL
    assert 'accounts.spotify.com/authorize' in response.location

@pytest.mark.usefixtures("new_user", "db_session") 
def test_logout_logs_user_out(client, new_user, app): 
    """Test that logging out clears the session and de-authenticates the user."""
    
    with app.test_request_context(): 
        # Log in the user using Flask-Login's utility
        login_user(new_user) 

    with client: 
        # Verify user is initially considered logged in by querying the /check_auth endpoint
        auth_check_response_before_logout = client.get(url_for('main.check_auth_status'))
        
        assert auth_check_response_before_logout.status_code == 200
        auth_data_before = auth_check_response_before_logout.json
        assert auth_data_before['is_authenticated'] is True
        assert auth_data_before['user_id'] == new_user.id
        assert auth_data_before['is_anonymous'] is False

    # Perform logout (outside the 'with client' block if it re-establishes its own context, or inside if preferred)
    # For logout, it's usually fine as it makes its own request.
    logout_response = client.get(url_for('auth.logout'), follow_redirects=True)
    assert logout_response.status_code == 200 # Should redirect to index
    assert b"You have been logged out." in logout_response.data # Check for flash message

    # Verify user is logged out and session is cleared
    with client.session_transaction() as sess:
        assert '_user_id' not in sess 
        assert '_fresh' not in sess

    # Verify current_user is anonymous after logout by querying /check_auth again
    # The /check_auth route is @login_required, so it should redirect to login if not authenticated
    auth_check_response_after_logout = client.get(url_for('main.check_auth_status'), follow_redirects=False)
    assert auth_check_response_after_logout.status_code == 302 # Expect redirect to login
    assert url_for('auth.login') in auth_check_response_after_logout.location


# For now, if the @spotify_token_required decorator primarily checks for login
# and presence of token fields (without immediate validation), we can test that.

def test_dashboard_access_authenticated_no_token(client, new_user, db_session, app):
    """Test dashboard access for authenticated user but missing Spotify token info."""
    # Set up user with expired token and no refresh token
    user = db_session.get(User, new_user.id)
    assert user is not None, "User should be found in the database"
    user.access_token = "dummy_expired_access_token"
    user.token_expiry = datetime.utcnow() - timedelta(hours=1)
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

        # Assert redirect comes from @spotify_token_required (no 'next' param)
        assert dashboard_response.status_code == 302
        assert dashboard_response.location == url_for('auth.login')

    # Check the redirect from /login to Spotify (rest of the test remains similar)
    login_redirect_response = client.get(dashboard_response.location, follow_redirects=False) # Get the actual /login URL
    assert login_redirect_response.status_code == 302 # Expecting another redirect

    # Verify the redirect location is Spotify's authorization URL
    spotify_redirect_location = login_redirect_response.location
    assert spotify_redirect_location is not None

    parsed_url = urlparse(spotify_redirect_location)
    query_params = parse_qs(parsed_url.query)

    assert parsed_url.scheme == 'https'
    assert parsed_url.netloc == 'accounts.spotify.com'
    assert parsed_url.path == '/authorize'
    
    assert 'client_id' in query_params
    assert query_params['client_id'][0] == app.config['SPOTIPY_CLIENT_ID']
    assert 'response_type' in query_params
    assert query_params['response_type'][0] == 'code'
    assert 'redirect_uri' in query_params
    assert query_params['redirect_uri'][0] == app.config['SPOTIPY_REDIRECT_URI']
    assert 'scope' in query_params
    assert query_params['scope'][0] == app.config['SPOTIFY_SCOPES'] # Assuming SPOTIFY_SCOPES is set in config
    assert 'state' in query_params # Check for presence of state, value is dynamic
    assert len(query_params['state'][0]) > 10 # State should be a reasonably long string


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

@pytest.mark.usefixtures("new_user", "db_session")
def test_automatic_token_refresh(client, new_user, db_session, monkeypatch, app):
    """Test that an expired Spotify token is automatically refreshed."""
    with app.test_request_context():
        login_user(new_user)
    
    # Manually expire the token in the database
    new_user.token_expiry = datetime.utcnow() - timedelta(hours=1)
    db_session.add(new_user)
    db_session.commit()

    # Mock app config values required for token refresh
    monkeypatch.setitem(app.config, 'SPOTIFY_CLIENT_ID', 'test_client_id')
    monkeypatch.setitem(app.config, 'SPOTIFY_CLIENT_SECRET', 'test_client_secret')

    # Prepare mock for requests.post
    # ensure_token_valid calculates expires_at from expires_in, so our mock should provide expires_in or a future expires_at
    # The User.ensure_token_valid method uses token_info['expires_at']
    new_access_token = 'refreshed_mock_access_token'
    # Simulate a new expiry time, e.g., 1 hour from now
    mock_new_expires_at = int((datetime.utcnow() + timedelta(hours=1)).timestamp())

    mock_refreshed_token_info = { # Corrected to provide expires_in
        'access_token': new_access_token,
        'refresh_token': new_user.refresh_token, # Assuming refresh token doesn't change
        'scope': 'playlist-read-private user-library-read', # Example scope, ensure it matches or is compatible
        'expires_in': 3600,  # Standard expiry time in seconds
        'token_type': 'Bearer'
    }

    # The User.ensure_token_valid method uses requests.post directly
    # So we patch 'app.models.models.requests.post'
    with patch('app.models.models.requests.post') as mock_post, \
         patch('app.services.spotify_service.SpotifyService.sync_user_playlists_with_db') as mock_sync_playlists:
        
        # Configure the mock response object for requests.post
        mock_response = MagicMock()
        mock_response.json.return_value = mock_refreshed_token_info
        mock_response.raise_for_status.return_value = None # Simulate successful status
        mock_post.return_value = mock_response

        with client:
            response = client.get(url_for('main.dashboard'))
        
        # Assertions
        mock_post.assert_called_once()
        expected_url = 'https://accounts.spotify.com/api/token'
        expected_payload = {
            'grant_type': 'refresh_token',
            'refresh_token': new_user.refresh_token,
        }
        expected_auth_correct = (app.config['SPOTIFY_CLIENT_ID'], app.config['SPOTIFY_CLIENT_SECRET'])
        mock_post.assert_called_once_with(expected_url, auth=expected_auth_correct, data=expected_payload)

        mock_sync_playlists.assert_called_once() # Assert that playlist sync was attempted
        assert response.status_code == 200

        # Fetch user from DB to check updated token details
        updated_user = db_session.get(User, new_user.id)
        assert updated_user.access_token == new_access_token
        # Check if expiry is correctly updated (allowing for minor differences in timestamp handling if any)
        assert abs((updated_user.token_expiry - datetime.fromtimestamp(mock_new_expires_at)).total_seconds()) < 5


@pytest.mark.usefixtures("new_user", "db_session")
def test_dashboard_access_authenticated_no_token(client, new_user, db_session, app):
    """Test dashboard access for authenticated user but missing Spotify token info."""
    # Log in the user (simplified for this specific redirect test)
    with client.session_transaction() as sess:
        sess['user_id'] = new_user.id
        sess['_fresh'] = True

    # Ensure user has an expired token and no refresh token for this test
    user = db_session.get(User, new_user.id)
    assert user is not None, "User should be found in the database"
    user.access_token = "dummy_expired_access_token" # Must be non-null
    user.token_expiry = datetime.utcnow() - timedelta(hours=1) # Set to 1 hour ago
    user.refresh_token = None # Ensure no refresh token to force re-auth
    db_session.commit()

    # Access dashboard - expect a redirect to /login first
    dashboard_response = client.get(url_for('main.dashboard'), follow_redirects=False)

    assert dashboard_response.status_code == 302 # Expecting a redirect
    assert url_for('auth.login') in dashboard_response.location # Should redirect to login
    
    # Now, check the redirect from /login to Spotify
    login_redirect_response = client.get(dashboard_response.location, follow_redirects=False) # Get the actual /login URL
    assert login_redirect_response.status_code == 302 # Expecting another redirect

    # Verify the redirect location is Spotify's authorization URL
    spotify_redirect_location = login_redirect_response.location
    assert spotify_redirect_location is not None

    parsed_url = urlparse(spotify_redirect_location)
    query_params = parse_qs(parsed_url.query)

    assert parsed_url.scheme == 'https'
    assert parsed_url.netloc == 'accounts.spotify.com'
    assert parsed_url.path == '/authorize'
    
    assert 'client_id' in query_params
    assert query_params['client_id'][0] == app.config['SPOTIPY_CLIENT_ID']
    assert 'response_type' in query_params
    assert query_params['response_type'][0] == 'code'
    assert 'redirect_uri' in query_params
    assert query_params['redirect_uri'][0] == app.config['SPOTIPY_REDIRECT_URI']
    assert 'scope' in query_params
    assert query_params['scope'][0] == app.config['SPOTIFY_SCOPES'] # Assuming SPOTIFY_SCOPES is set in config
    assert 'state' in query_params # Check for presence of state, value is dynamic
    assert len(query_params['state'][0]) > 10 # State should be a reasonably long string
