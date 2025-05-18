import pytest
from datetime import datetime, timezone
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

        # Create test playlists in the database
        playlist1 = Playlist(
            spotify_id='playlist1_spotify_id',
            name='Mock Playlist 1',
            owner_id=new_user.id,
            image_url='http://example.com/img1.png',
            description='Desc 1',
            spotify_snapshot_id='mock_snapshot_p1'
        )
        db_session.add(playlist1)
        
        # Add songs to the playlist to set the track count
        for i in range(10):
            song = Song(
                spotify_id=f'song_{i}_id',
                title=f'Test Song {i}',
                artist='Test Artist',
                album='Test Album',
                duration_ms=180000
            )
            db_session.add(song)
            db_session.flush()
            
            playlist_song = PlaylistSong(
                playlist_id=playlist1.id,
                song_id=song.id,
                track_position=i,
                added_at_spotify=datetime(2023, 1, 1, tzinfo=timezone.utc)
            )
            db_session.add(playlist_song)
        
        playlist2 = Playlist(
            spotify_id='playlist2_spotify_id',
            name='Mock Playlist 2',
            owner_id=new_user.id,
            description='Desc 2',
            spotify_snapshot_id='mock_snapshot_p2'
        )
        db_session.add(playlist2)
        
        # Add songs to the second playlist
        for i in range(5):
            song = Song(
                spotify_id=f'song2_{i}_id',
                title=f'Test Song 2-{i}',
                artist='Test Artist 2',
                album='Test Album 2',
                duration_ms=180000
            )
            db_session.add(song)
            db_session.flush()
            
            playlist_song = PlaylistSong(
                playlist_id=playlist2.id,
                song_id=song.id,
                track_position=i,
                added_at_spotify=datetime(2023, 1, 1, tzinfo=timezone.utc)
            )
            db_session.add(playlist_song)
        
        db_session.commit()

        # Mock Spotify API to return empty playlists since we're using DB data
        with patch('spotipy.Spotify') as MockSpotifyConstructor:
            mock_sp_instance = MockSpotifyConstructor.return_value
            mock_sp_instance.current_user_playlists.return_value = {'items': []}
            
            # Make the request to the dashboard
            response = client.get(url_for('main.dashboard'))
            assert response.status_code == 200
            response_data = response.get_data(as_text=True)
            
            # Debug: Print the response data
            print("\n=== Response Data ===")
            print(response_data)
            print("=== End Response Data ===\n")
            
            # Check for the main dashboard elements
            assert "<title>Dashboard - Spotify Cleanup</title>" in response_data
            
            # Check that the playlists are displayed in the response data
            assert 'Mock Playlist 1' in response_data, f"Expected 'Mock Playlist 1' in response data"
            assert 'Mock Playlist 2' in response_data, f"Expected 'Mock Playlist 2' in response data"
            
            # Check for track counts in the response data
            assert f'Tracks: {len(playlist1.songs)}' in response_data, f"Expected track count for playlist 1 in response data"
            assert f'Tracks: {len(playlist2.songs)}' in response_data, f"Expected track count for playlist 2 in response data" or 'Tracks: 5' in response_data
            
            # Check for playlist images or placeholders
            assert 'http://example.com/img1.png' in response_data or 'No Image' in response_data


@pytest.mark.usefixtures("new_user", "db_session")
def test_dashboard_renders_playlists_from_spotify(client, app, new_user, db_session):
    """Test that the dashboard renders playlists from Spotify."""
    with app.test_request_context():
        login_user(new_user)

        # Mock the Spotify API response
        with patch('spotipy.Spotify') as MockSpotifyConstructor:
            mock_sp_instance = MockSpotifyConstructor.return_value
            mock_sp_instance.current_user_playlists.return_value = {
                'items': [{
                    'id': 'test_playlist_1',
                    'name': 'Test Playlist 1',
                    'description': 'Test description',
                    'tracks': {'total': 10, 'href': 'https://api.spotify.com/v1/playlists/test_playlist_1/tracks'},
                    'images': [{'url': 'http://example.com/image.jpg'}],
                    'owner': {'display_name': 'Test User', 'id': 'test_user'},
                    'snapshot_id': 'test_snapshot_id',
                    'uri': 'spotify:playlist:test_playlist_1',
                    'href': 'https://api.spotify.com/v1/playlists/test_playlist_1',
                    'public': True,
                    'collaborative': False,
                    'type': 'playlist'
                }]
            }

            # Make the request to the dashboard
            response = client.get(url_for('main.dashboard'))
            
            # Check the response
            assert response.status_code == 200
            response_data = response.get_data(as_text=True)
            
            # Check if the playlist name is in the response
            assert 'Test Playlist 1' in response_data
            
            # Check if the track count is in the response
            # The template shows the track count as: <li>Tracks: {{ playlist.songs|length }}</li>
            # Since we didn't add any songs to the playlist, the count should be 0
            assert 'Tracks: 0' in response_data


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
                
                # Check for the no playlists message
                assert 'No Playlists Found' in response_data
                # Check for the help text when no playlists are found
                assert 'It looks like you haven\'t connected any playlists yet' in response_data
                mock_db_commit.assert_called_once()  # A commit is expected as spotify_service now always commits

@pytest.mark.usefixtures("new_user", "db_session")
def test_dashboard_spotify_api_error(client, app, new_user, db_session):
    """Test dashboard behavior on Spotify API error (non-401)."""
    with app.test_request_context():
        login_user(new_user)
        
        # Mock the Spotify API to raise an exception
        with patch('spotipy.Spotify') as MockSpotifyConstructor:
            mock_sp_instance = MockSpotifyConstructor.return_value
            mock_sp_instance.current_user_playlists.side_effect = spotipy.SpotifyException(
                http_status=500, code=-1, msg="Spotify API server error"
            )
            
            # Make the request to the dashboard
            response = client.get(url_for('main.dashboard'))
            
            # Check the response
            assert response.status_code == 200  # Route should handle error gracefully
            response_data = response.get_data(as_text=True)
            
            # Check for the error message in the alert div
            assert '<div class="alert alert-danger"' in response_data

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
def test_dashboard_shows_analysis_score(client, app, new_user, db_session, tmp_path, mocker):
    """Test that the dashboard displays the analysis score for playlists."""
    # Create a debug log file
    debug_file = tmp_path / "debug_log.txt"
    
    with debug_file.open('w') as f:
        f.write("=== Starting Test ===\n")
    
    def debug_log(msg):
        with debug_file.open('a') as f:
            f.write(f"[DEBUG] {msg}\n")
    
    with app.test_request_context():
        login_user(new_user)
        debug_log(f"User ID: {new_user.id}")
        debug_log(f"Initial playlists in DB: {db_session.query(Playlist).all()}")

        # Create a playlist with a score in the database
        test_playlist = Playlist(
            spotify_id='test_playlist_123',
            name='Test Playlist',
            owner_id=new_user.id,
            overall_alignment_score=75.0,  # Test score as percentage (0-100)
            image_url='http://example.com/image.jpg',
            spotify_snapshot_id='test_snapshot_123',
            last_synced_from_spotify=datetime.utcnow(),
            description='Test description'
        )
        
        # Add some test songs to the playlist
        for i in range(3):
            song = Song(
                spotify_id=f'test_song_{i}',
                title=f'Test Song {i}',
                artist='Test Artist',
                album='Test Album'
            )
            db_session.add(song)
            db_session.flush()  # Flush to get the song ID
            
            # Create playlist-song association
            playlist_song = PlaylistSong(
                playlist=test_playlist,
                song=song,
                track_position=i,
                added_at_spotify=datetime.utcnow()
            )
            db_session.add(playlist_song)
        
        db_session.add(test_playlist)
        db_session.commit()
        debug_log(f"Created playlist: {test_playlist.id}, {test_playlist.spotify_id}, {test_playlist.name}")
        debug_log(f"Playlists after creation: {db_session.query(Playlist).all()}")

        # Mock the Spotify service and its methods
        with patch('app.main.routes.SpotifyService') as mock_spotify_service:
            # Create a mock SpotifyService instance
            mock_service_instance = MagicMock()
            mock_spotify_service.return_value = mock_service_instance
            
            # Mock the sync method to return our test playlist
            mock_service_instance.sync_user_playlists_with_db.return_value = [test_playlist]
            
            # Mock the Spotify API response for the dashboard route
            mock_service_instance.get_user_playlists.return_value = {
                'items': [{
                    'id': 'test_playlist_123',
                    'name': 'Test Playlist',
                    'owner': {'display_name': 'Test User'},
                    'tracks': {'total': 10},
                    'images': [{'url': 'http://example.com/image.jpg'}],
                    'description': 'Test description',
                    'snapshot_id': 'test_snapshot_123'
                }]
            }
            
            # Mock the Spotify API client
            mock_spotify_client = MagicMock()
            mock_service_instance.sp = mock_spotify_client

            # Make the request to the dashboard
            debug_log("Making request to dashboard")
            response = client.get(url_for('main.dashboard'))
            debug_log(f"Response status code: {response.status_code}")
            
            # Check the response
            assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
            response_data = response.get_data(as_text=True)
            
            # Write response to file for inspection
            with (tmp_path / "response.html").open('w') as f:
                f.write(response_data)
            
            # Verify the playlist was saved to the database with the correct score
            saved_playlist = db_session.get(Playlist, test_playlist.id)
            debug_log(f"Retrieved playlist from DB: {saved_playlist}")
            
            assert saved_playlist is not None, "Playlist was not saved to the database"
            assert saved_playlist.overall_alignment_score == 75.0, f"Expected score 75.0, got {saved_playlist.overall_alignment_score}"
            
            # Debug: Print all playlists in the database
            all_playlists = db_session.query(Playlist).all()
            debug_log(f"All playlists in DB: {all_playlists}")
            debug_log(f"Response contains 'Test Playlist': {'Test Playlist' in response_data}")
            debug_log(f"Response length: {len(response_data)}")
            
            # Print debug file path for manual inspection
            print(f"\n[DEBUG] Debug log written to: {debug_file}")
            print(f"[DEBUG] Response HTML written to: {tmp_path}/response.html")
            
            # Verify the dashboard shows the playlist and score
            assert 'Test Playlist' in response_data, f"Playlist name not found in response. Check {debug_file} and {tmp_path}/response.html for details"
            assert '75.0%' in response_data, f"Score '75.0%' not found in response. Check {debug_file} and {tmp_path}/response.html for details"

@pytest.mark.usefixtures("new_user", "db_session")
def test_playlist_detail_shows_analysis_data(client, app, new_user, db_session):
    """Test that playlist_detail correctly displays song analysis scores and explanations."""
    with app.test_request_context():
        login_user(new_user)

        playlist_spotify_id = MOCK_SPOTIFY_PLAYLIST_DETAIL['id']
        song_spotify_id = MOCK_SPOTIFY_PLAYLIST_ITEMS_ANALYSIS['items'][0]['track']['id']

        # Create Playlist, Song, and AnalysisResult in DB
        # Create the playlist
        db_playlist = Playlist(
            spotify_id=playlist_spotify_id,
            name='Analysis Detail DB Playlist',
            owner_id=new_user.id,
            image_url='http://example.com/analysis_detail_img.png',
            description='A mock playlist for detail view analysis.',
            spotify_snapshot_id='mock_snapshot_analysis'
        )
        db_session.add(db_playlist)
        db_session.flush()  # Get the playlist ID without committing

        # Create the song
        db_song = Song(
            spotify_id=song_spotify_id,
            title='Analysis Song 1 DB',
            artist='Artist A DB',
            album='Test Album',
            duration_ms=180000
        )
        db_session.add(db_song)
        db_session.flush()  # Get the song ID without committing

        # Create a playlist-song association
        playlist_song = PlaylistSong(
            playlist_id=db_playlist.id,
            song_id=db_song.id,
            track_position=0,
            added_at_spotify=datetime(2023, 1, 1, tzinfo=timezone.utc)  # Using timezone-aware datetime for PostgreSQL
        )
        db_session.add(playlist_song)
        db_session.flush()

        # Create analysis result with the current model structure
        db_analysis_result = AnalysisResult(
            song_id=db_song.id,
            status='completed',
            score=95,  # Score is stored as a percentage (0-100)
            concern_level='low',
            themes=["Worship / Glorifying God", "Faith / Trust in God"],
            concerns=[],
            explanation="This song is highly aligned with Christian values.",
            analyzed_at=datetime(2023, 1, 1, tzinfo=timezone.utc)  # Using timezone-aware datetime for PostgreSQL
        )
        db_session.add(db_analysis_result)
        db_session.commit()

        # Mock Spotify API responses
        with patch('spotipy.Spotify') as MockSpotifyConstructor:
            mock_sp = MockSpotifyConstructor.return_value
            mock_sp.playlist.return_value = MOCK_SPOTIFY_PLAYLIST_DETAIL
            mock_sp.playlist_items.return_value = MOCK_SPOTIFY_PLAYLIST_ITEMS_ANALYSIS

            # Make the request to the playlist detail page
            response = client.get(url_for('main.playlist_detail', playlist_id=playlist_spotify_id))
            
            # Check for successful response
            assert response.status_code == 200
            response_data = response.get_data(as_text=True)
            
            # Check for the playlist title
            assert 'Analysis Detail Mock Playlist' in response_data
            
            # Check for the song title and artist in the table
            assert 'Analysis Song 1 DB' in response_data
            assert 'Artist A DB' in response_data
            
            # Check for the analysis score (95)
            assert '95' in response_data
            
            # Check for the badge color class (bg-success for low concern)
            assert 'bg-success' in response_data
            
            # The explanation and themes are displayed in the song detail view, not the playlist view
            # So we won't check for them here

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
