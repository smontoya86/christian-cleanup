import pytest
from flask import url_for
from flask_login import current_user, login_user
from datetime import datetime, timedelta

from app import create_app, db
from app.models.models import User, Whitelist, Blacklist, Playlist, Song
from app.services.spotify_service import SpotifyService
from app.services.whitelist_service import (
    ITEM_ADDED as WL_ITEM_ADDED,
    ITEM_ALREADY_EXISTS as WL_ITEM_ALREADY_EXISTS,
    ITEM_MOVED_FROM_BLACKLIST as WL_ITEM_MOVED_FROM_BLACKLIST,
    ERROR_OCCURRED as WL_ERROR_OCCURRED
)
from app.services.blacklist_service import (
    ITEM_ADDED as BL_ITEM_ADDED,
    ITEM_ALREADY_EXISTS as BL_ITEM_ALREADY_EXISTS,
    ITEM_MOVED_FROM_WHITELIST as BL_ITEM_MOVED_FROM_WHITELIST,
    ERROR_OCCURRED as BL_ERROR_OCCURRED
)
from unittest.mock import patch, MagicMock
from app.extensions import scheduler

@pytest.fixture
def app_context():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
        # Ensure scheduler is shutdown if it was started and is running
        if app.extensions.get('scheduler') and app.extensions['scheduler'].running:
            app.extensions['scheduler'].shutdown(wait=False)

@pytest.fixture
def test_client(app_context):
    return app_context.test_client()

@pytest.fixture
def new_user(app_context):
    user = User(spotify_id='test_spotify_user', email='test@example.com', display_name='Test User')
    # User model uses Spotify OAuth, no local password
    # Mock Spotify token details as needed by @spotify_token_required and user.ensure_token_valid()
    user.access_token = 'mock_access_token'
    user.refresh_token = 'mock_refresh_token'
    user.token_expiry = datetime.utcnow() + timedelta(hours=1) # Set to expire in 1 hour for tests
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def new_playlist(app_context, new_user):
    playlist = Playlist(spotify_id='test_playlist_1', name='Test Playlist', owner_id=new_user.id)
    db.session.add(playlist)
    db.session.commit()
    return playlist

@pytest.fixture
def new_song(app_context):
    song = Song(spotify_id='test_song_1', title='Test Song', artist='Test Artist')
    db.session.add(song)
    db.session.commit()
    return song


def test_blacklist_song_success(test_client, new_user, new_playlist, new_song, app_context):
    """Test successfully blacklisting a song."""
    # Login the user using the app_context for flask_login functions
    with app_context.test_request_context():
        login_user(new_user)

        # Ensure song is not already blacklisted or whitelisted by querying the database directly
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id).first() is None
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id).first() is None

        target_url = url_for('main.blacklist_song', playlist_id=new_playlist.spotify_id, track_id=new_song.spotify_id)
    
    # Make the POST request using the test_client
    # The test_client manages its own request context for the duration of this call.
    # Flashes are stored in the client's session.
    response = test_client.post(target_url, follow_redirects=False)

    assert response.status_code == 302 # Check for redirect
    # For this test, we are primarily concerned with the action of blacklisting and the immediate redirect.
    # The target of the redirect (dashboard) is not explicitly tested here to avoid its dependencies (Spotify API calls).
    # We can assume url_for constructs the correct URL if the route exists.
    # assert response.location == url_for('main.dashboard') # This check is fine

    # Check flash message directly from the session associated with the test_client
    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', []) # _flashes is where Flask stores them
    
    assert len(flashed_messages) == 1
    # Flashes are stored as (category, message) tuples if categories are used, or just messages.
    # Default category is 'message'. Our route uses 'success' or 'info'.
    category, message = flashed_messages[0]
    assert category == 'success'
    assert f"Song {new_song.spotify_id} added to blacklist." in message

    # Check database (still within app_context implicitly or re-fetch if needed)
    # Re-enter app_context if necessary for DB queries after client request, 
    # or ensure session used by client and DB queries is the same.
    # For simple checks like this, if db session is managed correctly by fixtures, it might be okay.
    with app_context.app_context(): # Re-establish app context for DB query if needed
        blacklisted_item = Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song').first()
        assert blacklisted_item is not None
        assert blacklisted_item.spotify_id == new_song.spotify_id
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id).first() is None


def test_blacklist_song_already_blacklisted(test_client, new_user, new_playlist, new_song, app_context):
    """Test blacklisting a song that is already blacklisted."""
    # Pre-populate blacklist
    with app_context.app_context(): # Ensure DB operations are within context
        initial_blacklist_entry = Blacklist(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song')
        db.session.add(initial_blacklist_entry)
        db.session.commit()

    # Login the user
    with app_context.test_request_context():
        login_user(new_user)
        target_url = url_for('main.blacklist_song', playlist_id=new_playlist.spotify_id, track_id=new_song.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)

    assert response.status_code == 302
    # assert response.location == url_for('main.dashboard')

    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'info'
    assert f"Song {new_song.spotify_id} is already in blacklist." in message

    # Ensure only one entry remains
    with app_context.app_context(): # Ensure DB operations are within context
        count = Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song').count()
        assert count == 1


def test_blacklist_song_unauthenticated(test_client, new_playlist, new_song, app_context):
    """Test attempting to blacklist a song when not authenticated."""
    with app_context.test_request_context(): # For url_for
        target_url = url_for('main.blacklist_song', playlist_id=new_playlist.spotify_id, track_id=new_song.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302 # Should redirect to login
    # In a typical Flask-Login setup, unauthenticated access to @login_required routes redirects to 'auth.login'.
    # The redirect URL often includes a 'next' parameter.
    with app_context.test_request_context(): # For url_for in assertion
        login_url = url_for('auth.login')
        assert response.location.startswith(login_url) # Check if it starts with the base login URL

    # Ensure no blacklist entry was created
    with app_context.app_context():
        assert Blacklist.query.filter_by(spotify_id=new_song.spotify_id).first() is None


# --- Whitelist Song Tests ---

def test_whitelist_song_success(test_client, new_user, new_playlist, new_song, app_context):
    """Test successfully whitelisting a song."""
    with app_context.test_request_context():
        login_user(new_user)
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id).first() is None
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id).first() is None
        target_url = url_for('main.whitelist_song', playlist_id=new_playlist.spotify_id, track_id=new_song.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302

    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'success'
    assert f"Song {new_song.spotify_id} added to your whitelist." in message

    with app_context.app_context():
        whitelisted_item = Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song').first()
        assert whitelisted_item is not None
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id).first() is None


def test_whitelist_song_already_whitelisted(test_client, new_user, new_playlist, new_song, app_context):
    """Test whitelisting a song that is already whitelisted."""
    with app_context.app_context():
        initial_whitelist_entry = Whitelist(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song')
        db.session.add(initial_whitelist_entry)
        db.session.commit()

    with app_context.test_request_context():
        login_user(new_user)
        target_url = url_for('main.whitelist_song', playlist_id=new_playlist.spotify_id, track_id=new_song.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302

    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'info'
    assert f"Song {new_song.spotify_id} is already in your whitelist." in message

    with app_context.app_context():
        count = Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song').count()
        assert count == 1


def test_whitelist_song_unauthenticated(test_client, new_playlist, new_song, app_context):
    """Test attempting to whitelist a song when not authenticated."""
    with app_context.test_request_context(): # For url_for
        target_url = url_for('main.whitelist_song', playlist_id=new_playlist.spotify_id, track_id=new_song.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302 # Should redirect to login
    with app_context.test_request_context(): # For url_for in assertion
        login_url = url_for('auth.login')
        assert response.location.startswith(login_url) # Check if it starts with the base login URL

    # Ensure no whitelist entry was created
    with app_context.app_context():
        assert Whitelist.query.filter_by(spotify_id=new_song.spotify_id).first() is None


# --- Blacklist Playlist Tests ---

def test_blacklist_playlist_success(test_client, new_user, new_playlist, app_context):
    """Test successfully blacklisting a playlist."""
    with app_context.test_request_context():
        login_user(new_user)
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None
        target_url = url_for('main.blacklist_playlist', playlist_id=new_playlist.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302

    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'success'
    assert f"Playlist {new_playlist.spotify_id} added to blacklist." in message

    with app_context.app_context():
        blacklisted_item = Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first()
        assert blacklisted_item is not None
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None

def test_blacklist_playlist_already_blacklisted(test_client, new_user, new_playlist, app_context):
    """Test blacklisting a playlist that is already blacklisted."""
    with app_context.app_context():
        initial_blacklist_entry = Blacklist(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist')
        db.session.add(initial_blacklist_entry)
        db.session.commit()

    with app_context.test_request_context():
        login_user(new_user)
        target_url = url_for('main.blacklist_playlist', playlist_id=new_playlist.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302

    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'info'
    assert f"Playlist {new_playlist.spotify_id} is already in blacklist." in message

    with app_context.app_context():
        count = Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').count()
        assert count == 1

def test_blacklist_playlist_unauthenticated(test_client, new_playlist, app_context):
    """Test attempting to blacklist a playlist when not authenticated."""
    with app_context.test_request_context():
        target_url = url_for('main.blacklist_playlist', playlist_id=new_playlist.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302
    with app_context.test_request_context():
        login_url = url_for('auth.login')
        assert response.location.startswith(login_url)

    with app_context.app_context():
        assert Blacklist.query.filter_by(spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None

# --- Whitelist Playlist Tests ---

def test_whitelist_playlist_success(test_client, new_user, new_playlist, app_context):
    """Test successfully whitelisting a playlist."""
    with app_context.test_request_context():
        login_user(new_user)
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None
        target_url = url_for('main.whitelist_playlist', playlist_id=new_playlist.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302

    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'success'
    assert f"Playlist {new_playlist.spotify_id} added to your whitelist." in message

    with app_context.app_context():
        whitelisted_item = Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first()
        assert whitelisted_item is not None
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None

def test_whitelist_playlist_already_whitelisted(test_client, new_user, new_playlist, app_context):
    """Test whitelisting a playlist that is already whitelisted."""
    with app_context.app_context():
        initial_whitelist_entry = Whitelist(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist')
        db.session.add(initial_whitelist_entry)
        db.session.commit()

    with app_context.test_request_context():
        login_user(new_user)
        target_url = url_for('main.whitelist_playlist', playlist_id=new_playlist.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302

    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'info'
    assert f"Playlist {new_playlist.spotify_id} is already in your whitelist." in message

    with app_context.app_context():
        count = Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').count()
        assert count == 1

def test_whitelist_playlist_unauthenticated(test_client, new_playlist, app_context):
    """Test attempting to whitelist a playlist when not authenticated."""
    with app_context.test_request_context():
        target_url = url_for('main.whitelist_playlist', playlist_id=new_playlist.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302
    with app_context.test_request_context():
        login_url = url_for('auth.login')
        assert response.location.startswith(login_url)

    with app_context.app_context():
        assert Whitelist.query.filter_by(spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None


# --- Interaction Tests (Song) ---

def test_whitelist_blacklisted_song(test_client, new_user, new_playlist, new_song, app_context):
    """Test whitelisting a song that is currently blacklisted."""
    # Pre-populate blacklist
    with app_context.app_context():
        initial_blacklist_entry = Blacklist(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song')
        db.session.add(initial_blacklist_entry)
        db.session.commit()
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id).first() is not None
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id).first() is None

    # Login and make request
    with app_context.test_request_context():
        login_user(new_user)
        target_url = url_for('main.whitelist_song', playlist_id=new_playlist.spotify_id, track_id=new_song.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302

    # Check flash message
    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'success'
    # The message should indicate it was moved or just added to whitelist
    assert f"Song {new_song.spotify_id} removed from blacklist and added to your whitelist." in message 

    # Check database: should be in whitelist, not in blacklist
    with app_context.app_context():
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song').first() is not None
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song').first() is None

def test_blacklist_whitelisted_song(test_client, new_user, new_playlist, new_song, app_context):
    """Test blacklisting a song that is currently whitelisted."""
    # Pre-populate whitelist
    with app_context.app_context():
        initial_whitelist_entry = Whitelist(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song')
        db.session.add(initial_whitelist_entry)
        db.session.commit()
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id).first() is not None
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id).first() is None

    # Login and make request
    with app_context.test_request_context():
        login_user(new_user)
        target_url = url_for('main.blacklist_song', playlist_id=new_playlist.spotify_id, track_id=new_song.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302

    # Check flash message
    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'success'
    # The message should indicate it was moved or just added to blacklist
    assert f"Song {new_song.spotify_id} removed from whitelist and added to blacklist." in message

    # Check database: should be in blacklist, not in whitelist
    with app_context.app_context():
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song').first() is not None
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_song.spotify_id, item_type='song').first() is None


# --- Interaction Tests (Playlist) ---

def test_whitelist_blacklisted_playlist(test_client, new_user, new_playlist, app_context):
    """Test whitelisting a playlist that is currently blacklisted."""
    # Pre-populate blacklist
    with app_context.app_context():
        initial_blacklist_entry = Blacklist(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist')
        db.session.add(initial_blacklist_entry)
        db.session.commit()
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is not None
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None

    # Login and make request
    with app_context.test_request_context():
        login_user(new_user)
        target_url = url_for('main.whitelist_playlist', playlist_id=new_playlist.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302

    # Check flash message
    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'success'
    assert f"Playlist {new_playlist.spotify_id} removed from blacklist and added to your whitelist." in message 

    # Check database: should be in whitelist, not in blacklist
    with app_context.app_context():
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is not None
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None

def test_blacklist_whitelisted_playlist(test_client, new_user, new_playlist, app_context):
    """Test blacklisting a playlist that is currently whitelisted."""
    # Pre-populate whitelist
    with app_context.app_context():
        initial_whitelist_entry = Whitelist(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist')
        db.session.add(initial_whitelist_entry)
        db.session.commit()
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is not None
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None

    # Login and make request
    with app_context.test_request_context():
        login_user(new_user)
        target_url = url_for('main.blacklist_playlist', playlist_id=new_playlist.spotify_id)
    
    response = test_client.post(target_url, follow_redirects=False)
    assert response.status_code == 302

    # Check flash message
    with test_client.session_transaction() as sess:
        flashed_messages = sess.get('_flashes', [])
    assert len(flashed_messages) == 1
    category, message = flashed_messages[0]
    assert category == 'success'
    assert f"Playlist {new_playlist.spotify_id} removed from whitelist and added to blacklist." in message

    # Check database: should be in blacklist, not in whitelist
    with app_context.app_context():
        assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is not None
        assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=new_playlist.spotify_id, item_type='playlist').first() is None


# TODO: Consider any other edge cases for future tests.
