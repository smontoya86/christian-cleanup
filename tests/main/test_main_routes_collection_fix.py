import pytest
from flask import url_for, get_flashed_messages
from flask_login import login_user, current_user, logout_user
from unittest.mock import patch, MagicMock, Mock
from app.models import User, Whitelist, Blacklist, Playlist, Song, AnalysisResult, PlaylistSong
from app.services.whitelist_service import ITEM_ADDED, ITEM_ALREADY_EXISTS as WL_ITEM_ALREADY_EXISTS, ITEM_MOVED_FROM_BLACKLIST
from app.services.blacklist_service import ITEM_ADDED as BL_ITEM_ADDED, ITEM_ALREADY_EXISTS as BL_ITEM_ALREADY_EXISTS, ITEM_MOVED_FROM_WHITELIST, ERROR_OCCURRED as BL_ERROR_OCCURRED
import spotipy
from sqlalchemy.exc import SQLAlchemyError
from app.utils.analysis import SongAnalyzer
from app.services.spotify_service import SpotifyService
# from app.services.cache_service import CacheService # Module not found, temporarily commented out

# Mock Spotify API responses (assuming these are defined elsewhere or similar structure)
MOCK_SPOTIFY_PLAYLISTS = {
    'items': [
        {
            'id': 'playlist1_spotify_id',
            'name': 'Mock Playlist 1',
            'images': [{'url': 'http://example.com/img1.png'}],
            'tracks': {'total': 10},
            'description': 'Desc 1',
            'snapshot_id': 'mock_snapshot_p1'
        },
        {
            'id': 'playlist2_spotify_id',
            'name': 'Mock Playlist 2',
            'images': [], # No image
            'tracks': {'total': 5},
            'description': 'Desc 2',
            'snapshot_id': 'mock_snapshot_p2'
        }
    ]
}

# Mock data for Spotify API response for analysis tests
MOCK_ANALYSIS_SPOTIFY_PLAYLISTS = {
    'items': [
        {
            'id': 'analysis_playlist1_spotify_id',
            'name': 'Analysis Mock Playlist 1',
            'images': [{'url': 'http://example.com/analysis_img1.png'}],
            'tracks': {'total': 3},
            'description': 'Analysis Desc 1',
            'snapshot_id': 'mock_snapshot_1' # Added missing snapshot_id
        }
    ]
}

# Mock data for Spotify API response for playlist_detail analysis tests
MOCK_SPOTIFY_PLAYLIST_DETAIL = {
    'id': 'analysis_detail_playlist_id',
    'name': 'Analysis Detail Mock Playlist',
    'description': 'A mock playlist for detail view analysis.',
    'images': [{'url': 'http://example.com/analysis_detail_img.png'}],
    'owner': {'display_name': 'Mock Owner'},
    'tracks': {'total': 1} # Keep this simple, items fetched separately
}

MOCK_SPOTIFY_PLAYLIST_ITEMS_ANALYSIS = {
    'items': [
        {
            'track': {
                'id': 'analysis_song1_spotify_id',
                'name': 'Analysis Song 1',
                'artists': [{'name': 'Artist A'}],
                'album': {'name': 'Album X', 'images': [{'url': 'http://example.com/albumX.png'}]}
            }
        }
    ]
}

@pytest.mark.usefixtures("new_user", "db_session")
def test_dashboard_renders_playlists(client, app, new_user, db_session):
    """Test that the dashboard correctly renders playlists."""
    with app.test_request_context():
        login_user(new_user) # Log in the user

        # Patch ensure_token_valid to simulate valid token
        with patch('app.models.models.User.ensure_token_valid', return_value=True):
            # Mock spotipy.Spotify instance and its methods
            with patch('spotipy.Spotify') as MockSpotifyConstructor:
                mock_sp_instance = MockSpotifyConstructor.return_value
                mock_sp_instance.current_user_playlists.return_value = MOCK_SPOTIFY_PLAYLISTS
                
                # Mock database interactions
                # Simulate Playlist.query.filter_by().first() returning None so new playlists are 'created'
                with patch('app.models.models.Playlist.query') as mock_playlist_query, \
                     patch('app.db.session.commit') as mock_db_commit: # Patch db.session.commit
                
                    mock_playlist_query.filter_by.return_value.first.return_value = None

                    response = client.get(url_for('main.dashboard'))
                    assert response.status_code == 200
                    response_data = response.get_data(as_text=True)

                    # Check for general dashboard elements inherited from base.html
                    assert "<title>Dashboard - Spotify Cleanup Tool</title>" in response_data
                    assert "<h1>Spotify Cleanup Tool</h1>" in response_data # Header from base
                    assert "<h2>Your Spotify Playlists</h2>" in response_data # Heading from dashboard.html

                    # Check for playlist container
                    assert '<div class="playlists-container">' in response_data

                    # Check for each mock playlist's content
                    assert 'Mock Playlist 1' in response_data
                    assert 'Tracks: 10' in response_data
                    assert '<img src="http://example.com/img1.png"' in response_data
                    assert 'class="playlist-card"' in response_data # Check at least one card exists

                    assert 'Mock Playlist 2' in response_data
                    assert 'Tracks: 5' in response_data
                    assert '<div class="playlist-placeholder-image">No Image</div>' in response_data
                    
                    # Verify mocks were called
                    MockSpotifyConstructor.assert_called_once_with(auth=new_user.access_token)
                    mock_sp_instance.current_user_playlists.assert_called_once_with(limit=50, offset=0) # Update expected limit to 50

                    # Playlist.query.filter_by().first() should be called for each playlist item
                    assert mock_playlist_query.filter_by.call_count == len(MOCK_SPOTIFY_PLAYLISTS['items'])
                    # db.session.commit() should be called once after processing playlists
                    mock_db_commit.assert_called_once()


@pytest.mark.usefixtures("new_user", "db_session")
def test_dashboard_no_playlists(client, app, new_user, db_session):
    """Test dashboard behavior when user has no Spotify playlists."""
    with app.test_request_context():
        login_user(new_user)
        
        with patch('spotipy.Spotify') as MockSpotifyConstructor:
            mock_sp_instance = MockSpotifyConstructor.return_value
            mock_sp_instance.current_user_playlists.return_value = {'items': []} # Empty list
            
            with patch('app.db.session.commit') as mock_db_commit: # No need to mock Playlist query if items are empty
                response = client.get(url_for('main.dashboard'))
                assert response.status_code == 200
                response_data = response.get_data(as_text=True)
                
                assert "<h2>Your Spotify Playlists</h2>" in response_data
                assert "<p>No playlists found, or there was an error fetching them." in response_data
                assert 'class="playlist-card"' not in response_data # No cards should be rendered
                mock_db_commit.assert_called_once() # A commit is expected as spotify_service now always commits

@pytest.mark.usefixtures("new_user", "db_session")
def test_dashboard_spotify_api_error(client, app, new_user, db_session):
    """Test dashboard behavior on Spotify API error (non-401)."""
    with app.test_request_context():
        login_user(new_user)
        
        with patch('spotipy.Spotify') as MockSpotifyConstructor:
            mock_sp_instance = MockSpotifyConstructor.return_value
            mock_sp_instance.current_user_playlists.side_effect = spotipy.SpotifyException(
                http_status=500, code=-1, msg="Spotify API server error"
            )
            
            # Patch ensure_token_valid to simulate valid token
            with patch('app.models.models.User.ensure_token_valid', return_value=True):
                response = client.get(url_for('main.dashboard'))
                assert response.status_code == 200 # Route should handle error gracefully
                response_data = response.get_data(as_text=True)
                
                assert "<h2>Your Spotify Playlists</h2>" in response_data
                assert "Could not retrieve playlists from Spotify. Please try again later." in response_data
                assert 'class="playlist-card"' not in response_data

@patch('app.main.routes.spotipy.Spotify')
def test_whitelist_song_unauthenticated(MockSpotify, client, app):
    """Test whitelist_song for an unauthenticated user."""
    with app.test_request_context():
        logout_user() # Ensure no user is logged in
        playlist_id = 'some_playlist_id'
        track_id = 'some_song_id'
        response = client.post(url_for('main.whitelist_song', playlist_id=playlist_id, track_id=track_id), follow_redirects=False)
        assert response.status_code == 302 # Should redirect to login
        assert url_for('auth.login') in response.location # Check if redirected to login page
        # Check that the mock Spotify client was not called
        MockSpotify.assert_not_called()
        # Ensure no flash message indicates success/failure other than login required (handled by @login_required)

@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.add_to_whitelist') # Patch where it's used
def test_whitelist_song_authenticated_new_item(mock_add_to_whitelist, client, app, new_user, db_session):
    """Test whitelist_song for an authenticated user whitelisting a new song."""
    with app.test_request_context():
        login_user(new_user)
        
        playlist_id = 'test_playlist_123'
        track_id = 'test_song_456'

        # Configure the mock service function's return value for a new item
        mock_add_to_whitelist.return_value = (ITEM_ADDED, MagicMock(spec=Whitelist))

        response = client.post(url_for('main.whitelist_song', playlist_id=playlist_id, track_id=track_id), follow_redirects=False)

        assert response.status_code == 302 
        assert url_for('main.playlist_detail', playlist_id=playlist_id) in response.location

        # Check that the service function was called correctly
        mock_add_to_whitelist.assert_called_once_with(new_user.id, track_id, 'song')
        # Check flashed messages
        with client.session_transaction() as sess:
            flashed_messages = sess.get('_flashes', [])
        assert any(category == 'success' and f'Song {track_id} added to your whitelist.' in message for category, message in flashed_messages)

@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.add_to_whitelist') # Patch where it's used
def test_whitelist_song_authenticated_existing_item(mock_add_to_whitelist, client, app, new_user, db_session):
    """Test whitelist_song for an authenticated user whitelisting an existing song."""
    with app.test_request_context():
        login_user(new_user)

        playlist_id = 'test_playlist_789'
        track_id = 'test_song_101'

        # Configure the mock service function's return value for an existing item
        mock_add_to_whitelist.return_value = (WL_ITEM_ALREADY_EXISTS, MagicMock(spec=Whitelist))

        response = client.post(url_for('main.whitelist_song', playlist_id=playlist_id, track_id=track_id), follow_redirects=False)

        assert response.status_code == 302 
        assert url_for('main.playlist_detail', playlist_id=playlist_id) in response.location

        # Check that the service function was called correctly
        mock_add_to_whitelist.assert_called_once_with(new_user.id, track_id, 'song')
        # Check flashed messages
        with client.session_transaction() as sess:
            flashed_messages = sess.get('_flashes', [])
        assert any(category == 'info' and f'Song {track_id} is already in your whitelist.' in message for category, message in flashed_messages)

@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.add_to_whitelist') # Patch where it's used
def test_whitelist_playlist_authenticated_new_item(mock_add_to_whitelist, client, app, new_user, db_session):
    """Test whitelist_playlist for an authenticated user whitelisting a new playlist."""
    with app.test_request_context():
        login_user(new_user)

        playlist_id = 'test_playlist_789'

        # Configure the mock service function's return value for a new item
        mock_add_to_whitelist.return_value = (ITEM_ADDED, MagicMock(spec=Whitelist))

        response = client.post(url_for('main.whitelist_playlist', playlist_id=playlist_id), follow_redirects=False)

        assert response.status_code == 302 
        assert url_for('main.dashboard') in response.location 

        # Check that the service function was called correctly
        mock_add_to_whitelist.assert_called_once_with(new_user.id, playlist_id, 'playlist')
        with client.session_transaction() as sess:
            flashed_messages = sess.get('_flashes', [])
        assert any(category == 'success' and f'Playlist {playlist_id} added to your whitelist.' in message for category, message in flashed_messages)

@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.add_to_whitelist') # Patch where it's used
def test_whitelist_playlist_authenticated_existing_item(mock_add_to_whitelist, client, app, new_user, db_session):
    """Test whitelist_playlist for an authenticated user whitelisting an existing playlist."""
    with app.test_request_context():
        login_user(new_user)

        playlist_id = 'existing_playlist_id'

        # Configure the mock service function's return value for an existing item
        mock_add_to_whitelist.return_value = (WL_ITEM_ALREADY_EXISTS, MagicMock(spec=Whitelist))

        response = client.post(url_for('main.whitelist_playlist', playlist_id=playlist_id), follow_redirects=False)

        assert response.status_code == 302 
        assert url_for('main.dashboard') in response.location

        mock_add_to_whitelist.assert_called_once_with(new_user.id, playlist_id, 'playlist')
        with client.session_transaction() as sess:
            flashed_messages = sess.get('_flashes', [])
        assert any(category == 'info' and f'Playlist {playlist_id} is already in your whitelist.' in message for category, message in flashed_messages)

@pytest.mark.usefixtures("new_user", "db_session")
def test_remove_song_unauthenticated(client, app):
    """Test remove_song route when user is not authenticated."""
    with app.test_request_context():
        logout_user() # Ensure no user is logged in
        response = client.post(url_for('main.remove_song', playlist_id='test_playlist_id', track_id='test_song_id'))
        assert response.status_code == 302
        assert url_for('auth.login') in response.location


@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.spotipy.Spotify')
@patch('app.models.models.User.ensure_token_valid', return_value=True) # Class-level patch
def test_remove_song_authenticated_successful_removal(mock_ensure_token, MockSpotify, client, app, new_user, db_session):
    """Test remove_song for an authenticated user with a successful Spotify API call."""
    with app.test_request_context():
        login_user(new_user)

        playlist_spotify_id = 'owned_playlist_id'
        song_spotify_id = 'song_to_remove_id'
        song_title = 'Test Song To Remove'

        # Create a playlist in DB owned by the user
        db_playlist = Playlist(owner_id=new_user.id, spotify_id=playlist_spotify_id, name='My Test Playlist')
        db_session.add(db_playlist)
        db_session.commit() # Commit to get db_playlist.id

        # Create a song in DB
        db_song = Song(spotify_id=song_spotify_id, title=song_title, artist='Test Artist')
        db_session.add(db_song)
        db_session.commit() # Commit to get db_song.id

        # Create a PlaylistSong association
        ps_assoc = PlaylistSong(playlist_id=db_playlist.id, song_id=db_song.id, track_position=1)
        db_session.add(ps_assoc)
        db_session.commit()
        # Store composite keys for verification later, as PlaylistSong has no single 'id' PK
        verify_playlist_id = db_playlist.id
        verify_song_id = db_song.id

        # Configure the mock Spotify instance
        mock_sp_instance = MockSpotify.return_value
        # Ensure new_user.spotify_id is set, or mock sp.me() if it might be None
        if not new_user.spotify_id:
            new_user.spotify_id = 'mock_spotify_user_id' # Ensure it's set for the test
            mock_sp_instance.me.return_value = {'id': new_user.spotify_id}
        else:
            # If spotify_id is already on new_user, sp.me() shouldn't be called by the primary path
            # but if it were, this would be its mock if required.
            mock_sp_instance.me.return_value = {'id': new_user.spotify_id}

        # Mock sp.playlist() to return data indicating current_user owns it
        mock_sp_instance.playlist.return_value = {
            'id': playlist_spotify_id,
            'owner': {'id': new_user.spotify_id}, # Critical for ownership check
            'name': 'Mocked Spotify Playlist Name'
        }
        # Mock sp.playlist_remove_all_occurrences_of_items() for success (no return value needed usually)
        mock_sp_instance.playlist_remove_all_occurrences_of_items.return_value = None 
        
        response = client.post(url_for('main.remove_song', playlist_id=playlist_spotify_id, track_id=song_spotify_id), follow_redirects=False)

        assert response.status_code == 302
        assert url_for('main.playlist_detail', playlist_id=playlist_spotify_id) in response.location
        mock_ensure_token.assert_called_once()
        MockSpotify.assert_called_once_with(auth=new_user.access_token)
        mock_sp_instance.playlist.assert_called_once_with(playlist_spotify_id, fields='owner.id')
        mock_sp_instance.playlist_remove_all_occurrences_of_items.assert_called_once_with(playlist_spotify_id, [song_spotify_id])

        # Verify the PlaylistSong association was deleted
        deleted_assoc = PlaylistSong.query.filter_by(playlist_id=verify_playlist_id, song_id=verify_song_id).first()
        assert deleted_assoc is None

        with client.session_transaction() as sess:
            flashed_messages = sess.get('_flashes', [])
        flashed_messages = [msg for cat, msg in flashed_messages]
        assert f'Song removed from playlist {playlist_spotify_id}.' in flashed_messages # Updated flash message

@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.spotipy.Spotify')
@patch('app.models.models.User.ensure_token_valid', return_value=True) # Class-level patch
def test_remove_song_unowned_playlist(mock_ensure_token, MockSpotify, client, app, new_user, db_session):
    """Test removing a song from a playlist not owned by the user."""
    with app.test_request_context():
        login_user(new_user)

        playlist_spotify_id = 'not_owned_playlist_id'
        song_spotify_id = 'song_to_remove_id'

        # Playlist in DB, but Spotify API will indicate different owner
        db_playlist = Playlist(owner_id=new_user.id, spotify_id=playlist_spotify_id, name='Not My Playlist in DB')
        db_session.add(db_playlist)
        db_session.commit()

        mock_sp_instance = MockSpotify.return_value
        mock_sp_instance.playlist.return_value = {
            'id': playlist_spotify_id,
            'owner': {'id': 'another_spotify_user_id'}, # Different owner
            'name': 'Mocked Spotify Playlist (Not Owned)'
        }
        
        response = client.post(url_for('main.remove_song', playlist_id=playlist_spotify_id, track_id=song_spotify_id), follow_redirects=False)

        assert response.status_code == 302 # Redirects to playlist detail
        assert url_for('main.playlist_detail', playlist_id=playlist_spotify_id) in response.location
        mock_ensure_token.assert_called_once()
        mock_sp_instance.playlist.assert_called_once_with(playlist_spotify_id, fields='owner.id')
        # Ensure remove item was NOT called
        mock_sp_instance.playlist_remove_all_occurrences_of_items.assert_not_called()

        with client.session_transaction() as sess:
            flashed_messages_tuples = sess.get('_flashes', [])
        flashed_messages = [msg for cat, msg in flashed_messages_tuples]
        assert 'You can only remove songs from playlists you own.' in flashed_messages


@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.spotipy.Spotify')
@patch('app.models.models.User.ensure_token_valid', return_value=True) # Class-level patch
def test_remove_song_spotify_api_error(mock_ensure_token, MockSpotify, client, app, new_user, db_session):
    """Test remove_song when Spotify API returns an error."""
    with app.test_request_context():
        login_user(new_user)

        playlist_spotify_id = 'owned_playlist_error_case_id'
        song_spotify_id = 'song_to_remove_id_error'

        db_playlist = Playlist(owner_id=new_user.id, spotify_id=playlist_spotify_id, name='My Error Test Playlist')
        db_session.add(db_playlist)
        db_session.commit()

        mock_sp_instance = MockSpotify.return_value
        mock_sp_instance.current_user.return_value = {'id': new_user.spotify_id} # Ensure ownership check can pass
        mock_sp_instance.playlist.return_value = {
            'id': playlist_spotify_id,
            'owner': {'id': new_user.spotify_id}, 
            'name': 'Mocked Playlist for Error Case'
        }
        # Simulate Spotify API error
        mock_sp_instance.playlist_remove_all_occurrences_of_items.side_effect = spotipy.SpotifyException(
            http_status=500, code=-1, msg="Spotify API server error"
        )
        
        response = client.post(url_for('main.remove_song', playlist_id=playlist_spotify_id, track_id=song_spotify_id), follow_redirects=False)

        assert response.status_code == 302
        assert url_for('main.playlist_detail', playlist_id=playlist_spotify_id) in response.location
        
        mock_ensure_token.assert_called_once()
        mock_sp_instance.playlist.assert_called_once_with(playlist_spotify_id, fields='owner.id')
        mock_sp_instance.playlist_remove_all_occurrences_of_items.assert_called_once()

        with client.session_transaction() as sess:
            flashed_messages_tuples = sess.get('_flashes', [])
        flashed_messages = [msg for cat, msg in flashed_messages_tuples]
        # The SpotifyException object e, when str(e) is used, includes http_status, code, msg, and reason.
        # The mock was created with: spotipy.SpotifyException(http_status=500, code=-1, msg="Spotify API server error")
        # Assuming reason will be None by default for the exception object.
        assert 'Could not remove song from Spotify: http status: 500, code: -1 - Spotify API server error, reason: None' in flashed_messages

@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.spotipy.Spotify')
@patch('app.models.models.User.ensure_token_valid', return_value=True) # Class-level patch
def test_remove_song_authenticated_sqlalchemy_error(mock_ensure_token, MockSpotifyConstructor, client, app, new_user, db_session):
    """Test remove_song when a SQLAlchemyError occurs during local DB update."""
    with app.test_request_context():
        login_user(new_user)

        playlist_spotify_id = 'owned_playlist_db_error_id'
        song_spotify_id = 'song_to_remove_db_error_id'
        song_title = 'Test Song DB Error'

        # Actual db_session for setup, MockDbSession for inside the route context
        # Create a playlist in actual db_session owned by the user
        db_playlist = Playlist(owner_id=new_user.id, spotify_id=playlist_spotify_id, name='My DB Error Test Playlist')
        db_session.add(db_playlist)
        db_session.commit()

        # Create a song in actual db_session
        db_song = Song(spotify_id=song_spotify_id, title=song_title, artist='Test Artist DB Error')
        db_session.add(db_song)
        db_session.commit()

        # Create a PlaylistSong association in actual db_session
        ps_assoc = PlaylistSong(playlist_id=db_playlist.id, song_id=db_song.id, track_position=1)
        db_session.add(ps_assoc)
        db_session.commit()

        # Configure the mock Spotify instance for successful removal
        mock_sp_instance = MockSpotifyConstructor.return_value
        if not new_user.spotify_id:
            new_user.spotify_id = 'mock_spotify_user_id_db_error' 
            mock_sp_instance.me.return_value = {'id': new_user.spotify_id}
        else:
            mock_sp_instance.me.return_value = {'id': new_user.spotify_id}
        
        mock_sp_instance.playlist.return_value = {
            'id': playlist_spotify_id,
            'owner': {'id': new_user.spotify_id},
            'name': 'Mocked Playlist for DB Error Case'
        }
        mock_sp_instance.playlist_remove_all_occurrences_of_items.return_value = None

        # Mock db_session.commit specifically to raise SQLAlchemyError
        with patch.object(db_session, 'commit', side_effect=SQLAlchemyError("Mocked DB commit error")) as mock_db_commit:
            response = client.post(url_for('main.remove_song', playlist_id=playlist_spotify_id, track_id=song_spotify_id), follow_redirects=False)

        assert response.status_code == 302
        assert url_for('main.playlist_detail', playlist_id=playlist_spotify_id) in response.location

        mock_ensure_token.assert_called_once() # Re-added assertion
        mock_db_commit.assert_called() # Ensure the mocked commit was reached
        MockSpotifyConstructor.assert_called_once_with(auth=new_user.access_token)
        mock_sp_instance.playlist_remove_all_occurrences_of_items.assert_called_once()

        with client.session_transaction() as sess:
            flashed_messages_tuples = sess.get('_flashes', [])
        flashed_messages = [msg for cat, msg in flashed_messages_tuples]
        assert 'A database error occurred while removing the song.' in flashed_messages

# Example of a test that might use the dashboard (adjust as needed)

@pytest.mark.usefixtures("new_user", "db_session")
def test_dashboard_shows_analysis_score(client, app, new_user, db_session):
    """Test that the dashboard correctly displays playlist analysis scores."""
    with app.test_request_context():
        login_user(new_user)

        # Create a playlist in the database with a specific score
        test_score = 0.75
        db_playlist = Playlist(
            spotify_id='analysis_playlist1_spotify_id',
            name='Analysis Mock Playlist 1 DB',
            owner_id=new_user.id,
            overall_alignment_score=test_score
        )
        db_session.add(db_playlist)
        db_session.commit()
        # Get the primary key AFTER committing, needed for direct query later
        db_playlist_id = db_playlist.id 

        with patch('spotipy.Spotify') as MockSpotifyConstructor, \
             patch('app.main.routes.render_template') as mock_render_template, \
             patch('app.models.models.User.ensure_token_valid', return_value=True):
            
            mock_sp_instance = MockSpotifyConstructor.return_value
            mock_sp_instance.current_user_playlists.return_value = MOCK_ANALYSIS_SPOTIFY_PLAYLISTS
            mock_render_template.return_value = "OK" # Prevent template rendering issues

            response = client.get(url_for('main.dashboard'))

            assert response.status_code == 200
            mock_render_template.assert_called_once()

            args, kwargs = mock_render_template.call_args
            assert 'playlists' in kwargs
            passed_playlists = kwargs['playlists']
            assert len(passed_playlists) == 1
            
            rendered_playlist = passed_playlists[0]
            assert rendered_playlist['id'] == 'analysis_playlist1_spotify_id'
            assert rendered_playlist['name'] == 'Analysis Mock Playlist 1' # Name from Spotify mock
            assert 'score' in rendered_playlist
            assert rendered_playlist['score'] == test_score

            # --- DEBUGGING STEP: Check score directly from DB after route call ---
            # Use db_session directly, which should be the same session used by the app context
            playlist_after_sync = db_session.get(Playlist, db_playlist_id)
            assert playlist_after_sync is not None, "Playlist not found in DB after sync!"
            print(f"DEBUG: Score in DB object after route: {playlist_after_sync.overall_alignment_score}")
            # ----------------------------------------------------------------------

@pytest.mark.usefixtures("new_user", "db_session")
def test_playlist_detail_shows_analysis_data(client, app, new_user, db_session):
    """Test that playlist_detail correctly displays song analysis scores and explanations."""
    with app.test_request_context():
        login_user(new_user)

        playlist_spotify_id = MOCK_SPOTIFY_PLAYLIST_DETAIL['id']
        song_spotify_id = MOCK_SPOTIFY_PLAYLIST_ITEMS_ANALYSIS['items'][0]['track']['id']

        # Create Playlist, Song, and AnalysisResult in DB
        db_playlist = Playlist(
            spotify_id=playlist_spotify_id,
            name='Analysis Detail DB Playlist',
            owner_id=new_user.id
        )
        db_session.add(db_playlist)
        db_session.commit() # Commit to get db_playlist.id

        db_song = Song(
            spotify_id=song_spotify_id,
            title='Analysis Song 1 DB',
            artist='Artist A DB' # Changed from artist_name
        )
        db_session.add(db_song)
        db_session.commit() # Commit to get db_song.id

        test_song_score = 0.95
        test_explanation = "This song is highly aligned."
        db_analysis_result = AnalysisResult(
            song_id=db_song.id,
            alignment_score=test_song_score,
            explanation=test_explanation,
            themes={'positive': 0.9},
            problematic_content=None
        )
        db_session.add(db_analysis_result)
        db_session.commit()

        with patch('spotipy.Spotify') as MockSpotifyConstructor, \
             patch('app.main.routes.render_template') as mock_render_template:
            
            mock_sp_instance = MockSpotifyConstructor.return_value
            mock_sp_instance.playlist.return_value = MOCK_SPOTIFY_PLAYLIST_DETAIL
            mock_sp_instance.playlist_items.return_value = MOCK_SPOTIFY_PLAYLIST_ITEMS_ANALYSIS
            mock_render_template.return_value = "OK"

            response = client.get(url_for('main.playlist_detail', playlist_id=playlist_spotify_id))

            assert response.status_code == 200
            mock_render_template.assert_called_once()

            args, kwargs = mock_render_template.call_args
            assert 'playlist' in kwargs
            assert 'songs' in kwargs

            rendered_songs = kwargs['songs']
            assert len(rendered_songs) == 1
            song_data = rendered_songs[0]

            assert song_data['id'] == song_spotify_id
            assert song_data['title'] == 'Analysis Song 1 DB' # Changed from Spotify mock to DB value
            assert 'score' in song_data
            assert song_data['score'] == test_song_score
            assert 'explanation' in song_data
            assert song_data['explanation'] == test_explanation

# Test cases for /blacklist_song route
@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.add_to_blacklist') # Patch the service function
def test_blacklist_song_authenticated_new_item(mock_add_to_blacklist, client, app, new_user, db_session):
    """Test blacklist_song for an authenticated user blacklisting a new song."""
    with app.test_request_context():
        login_user(new_user)
        playlist_id = 'some_playlist_id' # Needed for url_for, actual value might not be critical if not used by route logic beyond URL generation
        track_id = 'test_song_blacklist_new'

        # Configure mock for new item added to blacklist (possibly moved from whitelist)
        mock_add_to_blacklist.return_value = (BL_ITEM_ADDED, MagicMock(spec=Blacklist))

        response = client.post(url_for('main.blacklist_song', playlist_id=playlist_id, track_id=track_id), follow_redirects=False)

        assert response.status_code == 302
        assert url_for('main.playlist_detail', playlist_id=playlist_id) in response.location
        mock_add_to_blacklist.assert_called_once_with(new_user.id, track_id, 'song')
        with client.session_transaction() as sess:
            flashed_messages = sess.get('_flashes', [])
        assert any(category == 'success' and f'Song {track_id} added to blacklist.' in message for category, message in flashed_messages)

@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.add_to_blacklist') # Patch the service function
def test_blacklist_song_authenticated_existing_item(mock_add_to_blacklist, client, app, new_user, db_session):
    """Test blacklist_song for an authenticated user blacklisting an existing song."""
    with app.test_request_context():
        login_user(new_user)
        playlist_id = 'some_playlist_id'
        track_id = 'test_song_blacklist_existing'

        mock_add_to_blacklist.return_value = (BL_ITEM_ALREADY_EXISTS, MagicMock(spec=Blacklist))

        response = client.post(url_for('main.blacklist_song', playlist_id=playlist_id, track_id=track_id), follow_redirects=False)

        assert response.status_code == 302
        assert url_for('main.playlist_detail', playlist_id=playlist_id) in response.location
        mock_add_to_blacklist.assert_called_once_with(new_user.id, track_id, 'song')
        with client.session_transaction() as sess:
            flashed_messages = sess.get('_flashes', [])
        assert any(category == 'info' and f'Song {track_id} is already in blacklist.' in message for category, message in flashed_messages)

# Test cases for /blacklist_playlist route
@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.add_to_blacklist') # Patch the service function
def test_blacklist_playlist_authenticated_new_item(mock_add_to_blacklist, client, app, new_user, db_session):
    """Test blacklist_playlist for an authenticated user blacklisting a new playlist."""
    with app.test_request_context():
        login_user(new_user)
        playlist_id = 'test_playlist_blacklist_new'

        mock_add_to_blacklist.return_value = (BL_ITEM_ADDED, MagicMock(spec=Blacklist))

        response = client.post(url_for('main.blacklist_playlist', playlist_id=playlist_id), follow_redirects=False)

        assert response.status_code == 302
        assert url_for('main.dashboard') in response.location
        mock_add_to_blacklist.assert_called_once_with(new_user.id, playlist_id, 'playlist')
        with client.session_transaction() as sess:
            flashed_messages = sess.get('_flashes', [])
        assert any(category == 'success' and f'Playlist {playlist_id} added to blacklist.' in message for category, message in flashed_messages)

@pytest.mark.usefixtures("new_user", "db_session")
@patch('app.main.routes.add_to_blacklist') # Patch the service function
def test_blacklist_playlist_authenticated_existing_item(mock_add_to_blacklist, client, app, new_user, db_session):
    """Test blacklist_playlist for an authenticated user blacklisting an existing playlist."""
    with app.test_request_context():
        login_user(new_user)
        playlist_id = 'test_playlist_blacklist_existing'

        mock_add_to_blacklist.return_value = (BL_ITEM_ALREADY_EXISTS, MagicMock(spec=Blacklist))

        response = client.post(url_for('main.blacklist_playlist', playlist_id=playlist_id), follow_redirects=False)

        assert response.status_code == 302
        assert url_for('main.dashboard') in response.location
        mock_add_to_blacklist.assert_called_once_with(new_user.id, playlist_id, 'playlist')
        with client.session_transaction() as sess:
            flashed_messages = sess.get('_flashes', [])
        assert any(category == 'info' and f'Playlist {playlist_id} is already in blacklist.' in message for category, message in flashed_messages)

# Test cases for removing items (ensure these are also updated if they call services)

# test_remove_song_from_playlist requires careful review of its current patches
