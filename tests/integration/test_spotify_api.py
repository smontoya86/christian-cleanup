"""
Integration tests for Spotify API interactions.
Tests the SpotifyService class with mocked API responses to ensure proper handling
of various API scenarios including token refresh, playlist sync, and error handling.
"""

import pytest
import responses
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from requests.exceptions import RequestException, Timeout

from app.services.spotify_service import SpotifyService
from app.models.models import User, Playlist, Song, PlaylistSong, AnalysisResult
from app.extensions import db


class TestSpotifyAPIIntegration:
    """Test suite for Spotify API integration functionality."""

    @pytest.fixture
    def spotify_service(self, app, new_user):
        """Create a SpotifyService instance with test user."""
        with app.app_context():
            return SpotifyService(new_user)

    @pytest.fixture
    def mock_spotify_user_profile(self):
        """Mock Spotify user profile response."""
        return {
            'id': 'test_spotify_id',
            'display_name': 'Test User',
            'email': 'test@example.com',
            'images': [{'url': 'http://example.com/avatar.jpg'}]
        }

    @pytest.fixture
    def mock_spotify_playlists_response(self):
        """Mock Spotify playlists response."""
        return {
            'items': [
                {
                    'id': 'playlist_1',
                    'name': 'Christian Favorites',
                    'description': 'My favorite Christian songs',
                    'owner': {'id': 'test_spotify_id'},
                    'public': True,
                    'snapshot_id': 'snapshot_123',
                    'tracks': {'total': 2},
                    'images': [{'url': 'http://example.com/playlist.jpg'}]
                },
                {
                    'id': 'playlist_2',
                    'name': 'Worship Mix',
                    'description': 'Songs for worship',
                    'owner': {'id': 'test_spotify_id'},
                    'public': False,
                    'snapshot_id': 'snapshot_456',
                    'tracks': {'total': 3},
                    'images': []
                }
            ],
            'total': 2,
            'limit': 50,
            'offset': 0,
            'next': None
        }

    @pytest.fixture
    def mock_spotify_tracks_response(self):
        """Mock Spotify playlist tracks response."""
        return {
            'items': [
                {
                    'track': {
                        'id': 'track_1',
                        'name': 'Amazing Grace',
                        'artists': [
                            {'id': 'artist_1', 'name': 'Chris Tomlin'}
                        ],
                        'album': {
                            'id': 'album_1',
                            'name': 'How Great Is Our God',
                            'images': [{'url': 'http://example.com/album.jpg'}]
                        },
                        'duration_ms': 240000,
                        'explicit': False,
                        'preview_url': 'http://example.com/preview.mp3'
                    },
                    'added_at': '2024-01-01T00:00:00Z',
                    'added_by': {'id': 'test_spotify_id'}
                },
                {
                    'track': {
                        'id': 'track_2',
                        'name': 'How Great Thou Art',
                        'artists': [
                            {'id': 'artist_2', 'name': 'Carrie Underwood'}
                        ],
                        'album': {
                            'id': 'album_2',
                            'name': 'My Savior',
                            'images': [{'url': 'http://example.com/album2.jpg'}]
                        },
                        'duration_ms': 280000,
                        'explicit': False,
                        'preview_url': None
                    },
                    'added_at': '2024-01-02T00:00:00Z',
                    'added_by': {'id': 'test_spotify_id'}
                }
            ],
            'total': 2,
            'limit': 100,
            'offset': 0,
            'next': None
        }

    @pytest.mark.integration
    @responses.activate
    def test_successful_user_playlists_fetch(self, spotify_service, mock_spotify_playlists_response):
        """Test successful fetching of user playlists from Spotify."""
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json=mock_spotify_playlists_response,
            status=200
        )

        playlists = spotify_service.get_user_playlists()

        assert len(playlists) == 2
        assert playlists[0]['name'] == 'Christian Favorites'
        assert playlists[1]['name'] == 'Worship Mix'
        assert len(responses.calls) == 1

    @pytest.mark.integration
    @responses.activate
    def test_playlist_tracks_fetch(self, spotify_service, mock_spotify_tracks_response):
        """Test fetching tracks from a specific playlist."""
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/playlists/playlist_1/tracks',
            json=mock_spotify_tracks_response,
            status=200
        )

        tracks = spotify_service.get_playlist_tracks('playlist_1')

        assert len(tracks) == 2
        assert tracks[0]['track']['name'] == 'Amazing Grace'
        assert tracks[1]['track']['name'] == 'How Great Thou Art'
        assert len(responses.calls) == 1

    @pytest.mark.integration
    @responses.activate
    def test_token_refresh_on_expired_token(self, spotify_service):
        """Test automatic token refresh when access token is expired."""
        # First request returns 401 (token expired)
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json={'error': {'status': 401, 'message': 'The access token expired'}},
            status=401
        )

        # Token refresh request
        responses.add(
            responses.POST,
            'https://accounts.spotify.com/api/token',
            json={
                'access_token': 'new_access_token',
                'token_type': 'Bearer',
                'expires_in': 3600,
                'refresh_token': 'new_refresh_token'
            },
            status=200
        )

        # Retry request with new token
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json={'items': [], 'total': 0},
            status=200
        )

        playlists = spotify_service.get_user_playlists()

        assert len(responses.calls) == 3  # Initial request + token refresh + retry
        assert playlists == []

    @pytest.mark.integration
    @responses.activate
    def test_rate_limiting_handling(self, spotify_service):
        """Test handling of Spotify API rate limiting."""
        # First request returns rate limit error
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json={'error': {'status': 429, 'message': 'rate limit exceeded'}},
            status=429,
            headers={'Retry-After': '1'}
        )

        # Second request succeeds
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json={'items': [], 'total': 0},
            status=200
        )

        with patch('time.sleep') as mock_sleep:
            playlists = spotify_service.get_user_playlists()

        assert len(responses.calls) == 2
        assert playlists == []
        mock_sleep.assert_called_once_with(1)

    @pytest.mark.integration
    @responses.activate
    def test_playlist_sync_with_database(self, spotify_service, mock_spotify_playlists_response, 
                                       mock_spotify_tracks_response, db_session):
        """Test syncing playlists from Spotify to database."""
        # Mock playlists response
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json=mock_spotify_playlists_response,
            status=200
        )

        # Mock tracks responses for each playlist
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/playlists/playlist_1/tracks',
            json=mock_spotify_tracks_response,
            status=200
        )

        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/playlists/playlist_2/tracks',
            json={'items': [], 'total': 0},
            status=200
        )

        # Perform sync
        spotify_service.sync_user_playlists_with_db()

        # Verify database state
        playlists = db_session.query(Playlist).all()
        assert len(playlists) == 2
        
        playlist_1 = db_session.query(Playlist).filter_by(spotify_id='playlist_1').first()
        assert playlist_1.name == 'Christian Favorites'
        assert playlist_1.snapshot_id == 'snapshot_123'

        songs = db_session.query(Song).all()
        assert len(songs) == 2

    @pytest.mark.integration
    @responses.activate
    def test_paginated_playlists_fetch(self, spotify_service):
        """Test fetching paginated playlists from Spotify."""
        # First page
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json={
                'items': [
                    {
                        'id': 'playlist_1',
                        'name': 'Playlist 1',
                        'owner': {'id': 'test_spotify_id'},
                        'snapshot_id': 'snap_1',
                        'tracks': {'total': 0},
                        'images': []
                    }
                ],
                'total': 2,
                'limit': 1,
                'offset': 0,
                'next': 'https://api.spotify.com/v1/me/playlists?offset=1&limit=1'
            },
            status=200
        )

        # Second page
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json={
                'items': [
                    {
                        'id': 'playlist_2',
                        'name': 'Playlist 2',
                        'owner': {'id': 'test_spotify_id'},
                        'snapshot_id': 'snap_2',
                        'tracks': {'total': 0},
                        'images': []
                    }
                ],
                'total': 2,
                'limit': 1,
                'offset': 1,
                'next': None
            },
            status=200
        )

        playlists = spotify_service.get_user_playlists()

        assert len(playlists) == 2
        assert len(responses.calls) == 2  # Should make two paginated requests

    @pytest.mark.integration
    @responses.activate
    def test_paginated_tracks_fetch(self, spotify_service):
        """Test fetching paginated tracks from a playlist."""
        # First page
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/playlists/playlist_1/tracks',
            json={
                'items': [
                    {
                        'track': {
                            'id': 'track_1',
                            'name': 'Track 1',
                            'artists': [{'id': 'artist_1', 'name': 'Artist 1'}],
                            'album': {'id': 'album_1', 'name': 'Album 1', 'images': []},
                            'duration_ms': 240000,
                            'explicit': False
                        },
                        'added_at': '2024-01-01T00:00:00Z',
                        'added_by': {'id': 'test_spotify_id'}
                    }
                ],
                'total': 2,
                'limit': 1,
                'offset': 0,
                'next': 'https://api.spotify.com/v1/playlists/playlist_1/tracks?offset=1&limit=1'
            },
            status=200
        )

        # Second page
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/playlists/playlist_1/tracks',
            json={
                'items': [
                    {
                        'track': {
                            'id': 'track_2',
                            'name': 'Track 2',
                            'artists': [{'id': 'artist_2', 'name': 'Artist 2'}],
                            'album': {'id': 'album_2', 'name': 'Album 2', 'images': []},
                            'duration_ms': 280000,
                            'explicit': False
                        },
                        'added_at': '2024-01-02T00:00:00Z',
                        'added_by': {'id': 'test_spotify_id'}
                    }
                ],
                'total': 2,
                'limit': 1,
                'offset': 1,
                'next': None
            },
            status=200
        )

        tracks = spotify_service.get_playlist_tracks('playlist_1')

        assert len(tracks) == 2
        assert len(responses.calls) == 2  # Should make two paginated requests

    @pytest.mark.integration
    @responses.activate
    def test_api_server_error_handling(self, spotify_service):
        """Test handling of server errors from Spotify API."""
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json={'error': {'status': 500, 'message': 'internal server error'}},
            status=500
        )

        playlists = spotify_service.get_user_playlists()
        assert playlists == []

    @pytest.mark.integration
    @responses.activate
    def test_network_timeout_handling(self, spotify_service):
        """Test handling of network timeouts."""
        def timeout_callback(request):
            raise Timeout("Request timed out")

        responses.add_callback(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            callback=timeout_callback
        )

        playlists = spotify_service.get_user_playlists()
        assert playlists == []

    @pytest.mark.integration
    @responses.activate
    def test_invalid_playlist_id_handling(self, spotify_service):
        """Test handling of invalid playlist IDs."""
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/playlists/invalid_id/tracks',
            json={'error': {'status': 404, 'message': 'Not found'}},
            status=404
        )

        tracks = spotify_service.get_playlist_tracks('invalid_id')
        assert tracks == []

    @pytest.mark.integration
    @responses.activate
    def test_deleted_playlist_handling(self, spotify_service, db_session):
        """Test handling of playlists that were deleted from Spotify."""
        # Create existing playlist in database
        playlist = Playlist(
            spotify_id='deleted_playlist',
            name='Deleted Playlist',
            user_id=spotify_service.user.id,
            snapshot_id='old_snapshot'
        )
        db_session.add(playlist)
        db_session.commit()

        # Mock empty playlists response (playlist no longer exists)
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json={'items': [], 'total': 0},
            status=200
        )

        spotify_service.sync_user_playlists_with_db()

        # Playlist should be removed from database
        remaining_playlists = db_session.query(Playlist).all()
        assert len(remaining_playlists) == 0

    @pytest.mark.integration
    @responses.activate
    def test_snapshot_id_change_detection(self, spotify_service, db_session):
        """Test detection of playlist changes via snapshot_id."""
        # Create existing playlist in database
        playlist = Playlist(
            spotify_id='playlist_1',
            name='Old Name',
            user_id=spotify_service.user.id,
            snapshot_id='old_snapshot'
        )
        db_session.add(playlist)
        db_session.commit()

        # Mock playlists response with updated snapshot_id
        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json={
                'items': [
                    {
                        'id': 'playlist_1',
                        'name': 'Updated Name',
                        'owner': {'id': 'test_spotify_id'},
                        'snapshot_id': 'new_snapshot',
                        'tracks': {'total': 0},
                        'images': []
                    }
                ],
                'total': 1
            },
            status=200
        )

        responses.add(
            responses.GET,
            'https://api.spotify.com/v1/playlists/playlist_1/tracks',
            json={'items': [], 'total': 0},
            status=200
        )

        spotify_service.sync_user_playlists_with_db()

        # Playlist should be updated
        updated_playlist = db_session.query(Playlist).filter_by(spotify_id='playlist_1').first()
        assert updated_playlist.name == 'Updated Name'
        assert updated_playlist.snapshot_id == 'new_snapshot'

    @pytest.mark.integration
    @responses.activate
    def test_concurrent_api_requests(self, spotify_service, mock_spotify_playlists_response):
        """Test handling of concurrent API requests."""
        import concurrent.futures

        # Set up responses for multiple requests
        for i in range(5):
            responses.add(
                responses.GET,
                'https://api.spotify.com/v1/me/playlists',
                json=mock_spotify_playlists_response,
                status=200
            )

        def get_playlists():
            return spotify_service.get_user_playlists()

        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_playlists) for _ in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert all(len(result) == 2 for result in results)
        assert all(result[0]['name'] == 'Christian Favorites' for result in results) 