"""
Pytest configuration and shared fixtures for all test suites.
Provides common setup, teardown, and utilities for testing.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
import responses
from flask import Flask
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

# Set environment variables before importing the app
os.environ.setdefault('SPOTIPY_CLIENT_ID', 'test_client_id')
os.environ.setdefault('SPOTIPY_CLIENT_SECRET', 'test_client_secret') 
os.environ.setdefault('SPOTIPY_REDIRECT_URI', 'http://localhost:5001/auth/spotify/callback')
os.environ.setdefault('SPOTIFY_SCOPES', 'user-read-email playlist-read-private user-library-read user-top-read')
os.environ.setdefault('GENIUS_ACCESS_TOKEN', 'test_genius_token')
os.environ.setdefault('OPENAI_API_KEY', 'test_openai_key')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test_anthropic_key')
os.environ.setdefault('TEST_DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('RQ_TEST_REDIS_URL', 'redis://localhost:6379/15')  # Use DB 15 for tests

from app import create_app
from app.extensions import db
from app.models.models import User, Playlist, Song, AnalysisResult, PlaylistSong, LyricsCache


@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    # Create the Flask application with testing configuration
    app = create_app('testing')
    
    # Create application context
    with app.app_context():
        # Import db from extensions within the app context
        from app.extensions import db as database
        # Create all database tables
        database.create_all()
        
        yield app
        
        # Cleanup
        database.session.remove()
        database.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """Create a test runner for the Flask application's Click commands."""
    return app.test_cli_runner()


@pytest.fixture(scope='function', autouse=True)
def mock_redis():
    """Mock Redis connections for all tests."""
    with patch('redis.Redis') as mock_redis_class:
        # Create a mock Redis instance
        mock_redis_instance = MagicMock()
        mock_redis_class.return_value = mock_redis_instance
        
        # Mock common Redis methods
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.get.return_value = None
        mock_redis_instance.set.return_value = True
        mock_redis_instance.delete.return_value = 1
        mock_redis_instance.exists.return_value = False
        mock_redis_instance.expire.return_value = True
        mock_redis_instance.ttl.return_value = -1
        mock_redis_instance.keys.return_value = []
        mock_redis_instance.flushdb.return_value = True
        
        # Mock pipeline operations
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [True, True, True]
        mock_redis_instance.pipeline.return_value = mock_pipeline
        
        yield mock_redis_instance


@pytest.fixture(scope='function', autouse=True)
def clean_db(app):
    """Clean the database before each test."""
    with app.app_context():
        from app.extensions import db as database
        
        # Ensure all tables are created first
        database.create_all()
        
        # Clear all data from tables (using try-except for robustness)
        try:
            database.session.query(AnalysisResult).delete()
        except Exception:
            pass
        try:
            database.session.query(LyricsCache).delete()
        except Exception:
            pass
        try:
            database.session.query(PlaylistSong).delete()
        except Exception:
            pass
        try:
            database.session.query(Song).delete()
        except Exception:
            pass
        try:
            database.session.query(Playlist).delete()
        except Exception:
            pass
        try:
            database.session.query(User).delete()
        except Exception:
            pass
        
        database.session.commit()
        
        yield
        
        # Clean up after test
        database.session.rollback()


@pytest.fixture
def sample_user(app):
    """Create a sample user for testing."""
    with app.app_context():
        from app.extensions import db as database
        user = User(
            spotify_id='test_spotify_user_123',
            email='test@example.com',
            display_name='Test User',
            access_token='test_access_token',
            refresh_token='test_refresh_token',
            token_expiry=datetime.utcnow() + timedelta(hours=1)
        )
        database.session.add(user)
        database.session.commit()
        yield user


@pytest.fixture
def sample_playlist(app, sample_user):
    """Create a sample playlist for testing."""
    with app.app_context():
        from app.extensions import db as database
        playlist = Playlist(
            spotify_id='test_playlist_123',
            name='Test Christian Playlist',
            description='A test playlist for Christian music',
            owner_id=sample_user.id,
            spotify_snapshot_id='test_snapshot_123'
        )
        database.session.add(playlist)
        database.session.commit()
        yield playlist


@pytest.fixture
def sample_song(app):
    """Create a sample song for testing."""
    with app.app_context():
        from app.extensions import db as database
        song = Song(
            spotify_id='test_song_123',
            title='Amazing Grace',
            artist='Test Christian Artist',
            album='Test Christian Album',
            duration_ms=240000,
            lyrics='Amazing grace, how sweet the sound\nThat saved a wretch like me',
            explicit=False
        )
        database.session.add(song)
        database.session.commit()
        yield song


@pytest.fixture
def sample_lyrics(app, sample_song):
    """Create sample lyrics for testing."""
    with app.app_context():
        from app.extensions import db as database
        lyrics = LyricsCache(
            artist=sample_song.artist,
            title=sample_song.title,
            lyrics='Amazing grace, how sweet the sound\nThat saved a wretch like me',
            source='genius'
        )
        database.session.add(lyrics)
        database.session.commit()
        yield lyrics


@pytest.fixture
def sample_analysis(app, sample_song):
    """Create sample analysis for testing."""
    with app.app_context():
        from app.extensions import db as database
        analysis = AnalysisResult(
            song_id=sample_song.id,
            status='completed',
            score=85.5,
            concern_level='Low',
            themes=['worship', 'salvation', 'grace'],
            concerns=[],
            explanation='This song contains strong Christian themes and is appropriate for worship.',
            biblical_themes=['Grace', 'Salvation', 'Redemption'],
            supporting_scripture=[{'reference': 'Ephesians 2:8-9', 'text': 'For by grace you have been saved...'}]
        )
        database.session.add(analysis)
        database.session.commit()
        yield analysis


@pytest.fixture(scope='function')
def mock_spotify_service():
    """Mock Spotify service for testing."""
    with patch('app.services.spotify_service.SpotifyService') as mock_service:
        # Create a mock instance
        mock_instance = Mock()
        mock_service.return_value = mock_instance
        
        # Mock common methods
        mock_instance.get_user_playlists.return_value = []
        mock_instance.get_playlist_tracks.return_value = []
        mock_instance.search_track.return_value = None
        mock_instance.get_track.return_value = None
        
        yield mock_instance


@pytest.fixture(scope='function')
def mock_genius_service():
    """Mock Genius service for testing."""
    with patch('app.services.lyrics_service.LyricsService') as mock_service:
        mock_instance = Mock()
        mock_service.return_value = mock_instance
        
        # Mock lyrics fetching
        mock_instance.get_lyrics.return_value = "Sample lyrics for testing"
        mock_instance.search_genius.return_value = {
            'id': 123,
            'title': 'Test Song',
            'artist': 'Test Artist',
            'lyrics': 'Sample lyrics for testing'
        }
        
        yield mock_instance


@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls."""
    with patch('openai.ChatCompletion.create') as mock_create:
        mock_create.return_value = Mock(
            choices=[Mock(
                message=Mock(
                    content='{"christian_score": 8.5, "themes": "salvation, grace", "explanation": "Test analysis"}'
                )
            )]
        )
        yield mock_create


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic API calls."""
    with patch('anthropic.Anthropic') as mock_anthropic:
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        
        mock_response = Mock()
        mock_response.content = [Mock(text='{"christian_score": 8.5, "themes": "salvation, grace", "explanation": "Test analysis"}')]
        mock_client.messages.create.return_value = mock_response
        
        yield mock_client


@pytest.fixture(scope='function')
def mock_external_apis():
    """Mock all external API calls."""
    with responses.RequestsMock() as rsps:
        # Mock Spotify API endpoints
        rsps.add(
            responses.POST,
            'https://accounts.spotify.com/api/token',
            json={'access_token': 'test_token', 'token_type': 'Bearer', 'expires_in': 3600},
            status=200
        )
        
        rsps.add(
            responses.GET,
            'https://api.spotify.com/v1/me',
            json={
                'id': 'test_user',
                'display_name': 'Test User',
                'email': 'test@example.com'
            },
            status=200
        )
        
        rsps.add(
            responses.GET,
            'https://api.spotify.com/v1/me/playlists',
            json={
                'items': [],
                'total': 0,
                'limit': 50,
                'offset': 0
            },
            status=200
        )
        
        # Mock Genius API endpoints
        rsps.add(
            responses.GET,
            'https://api.genius.com/search',
            json={
                'response': {
                    'hits': [{
                        'result': {
                            'id': 123,
                            'title': 'Test Song',
                            'primary_artist': {'name': 'Test Artist'},
                            'url': 'https://genius.com/test-song'
                        }
                    }]
                }
            },
            status=200
        )
        
        yield rsps


# Test data factories
class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_spotify_track_data(track_id='test_track_123', name='Test Song', artist='Test Artist'):
        """Create mock Spotify track data."""
        return {
            'id': track_id,
            'name': name,
            'artists': [{'name': artist}],
            'album': {'name': 'Test Album'},
            'duration_ms': 180000,
            'popularity': 75,
            'track_number': 1,
            'disc_number': 1,
            'explicit': False,
            'preview_url': 'https://example.com/preview.mp3',
            'external_urls': {'spotify': f'https://open.spotify.com/track/{track_id}'}
        }
    
    @staticmethod
    def create_spotify_playlist_data(playlist_id='test_playlist_123', name='Test Playlist'):
        """Create mock Spotify playlist data."""
        return {
            'id': playlist_id,
            'name': name,
            'description': 'A test playlist',
            'public': True,
            'collaborative': False,
            'tracks': {'total': 5},
            'external_urls': {'spotify': f'https://open.spotify.com/playlist/{playlist_id}'}
        }
    
    @staticmethod
    def create_genius_song_data(song_id=123, title='Test Song', artist='Test Artist'):
        """Create mock Genius song data."""
        return {
            'id': song_id,
            'title': title,
            'primary_artist': {'name': artist},
            'url': f'https://genius.com/test-song-{song_id}',
            'lyrics_state': 'complete'
        }


# Custom pytest markers and assertions
def assert_redis_key_exists(redis_client, key):
    """Assert that a Redis key exists."""
    assert redis_client.exists(key), f"Redis key '{key}' does not exist"


def assert_redis_key_not_exists(redis_client, key):
    """Assert that a Redis key does not exist."""
    assert not redis_client.exists(key), f"Redis key '{key}' should not exist"


def assert_analysis_score_valid(score):
    """Assert that an analysis score is valid (between 0 and 10)."""
    assert 0 <= score <= 10, f"Analysis score {score} is not between 0 and 10"


def assert_song_has_required_fields(song_data):
    """Assert that song data has all required fields."""
    required_fields = ['id', 'name', 'artists']
    for field in required_fields:
        assert field in song_data, f"Song data missing required field: {field}"


def assert_api_response_format(response_data, expected_keys):
    """Assert that API response has expected format."""
    for key in expected_keys:
        assert key in response_data, f"API response missing expected key: {key}"


# Performance testing utilities
@pytest.fixture
def performance_timer():
    """Fixture for timing test execution."""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = time.time()
        
        def stop(self):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer()


# Test configuration and markers
pytest_plugins = [
    'pytest_asyncio',
    'pytest_mock'
]

# Custom test markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "regression: marks tests as regression tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API tests"
    )
    config.addinivalue_line(
        "markers", "database: marks tests as database tests"
    )
    config.addinivalue_line(
        "markers", "auth: marks tests as authentication tests"
    )
    config.addinivalue_line(
        "markers", "worker: marks tests as worker/background task tests"
    )
    config.addinivalue_line(
        "markers", "cache: marks tests as cache-related tests"
    )
    config.addinivalue_line(
        "markers", "smoke: marks tests as smoke tests"
    )


@pytest.fixture(scope='session')
def database():
    """Create a test database."""
    with tempfile.NamedTemporaryFile() as tmp:
        db_path = tmp.name
        yield f'sqlite:///{db_path}'


@pytest.fixture
def db(app):
    """Provide database instance."""
    from app.extensions import db as database
    with app.app_context():
        database.create_all()
        yield database
        database.drop_all()


@pytest.fixture
def db_session(app):
    """Provide database session."""
    from app.extensions import db as database
    with app.app_context():
        # Use the existing database session but ensure it's clean
        database.create_all()
        yield database.session
        # Clean up after test
        database.session.rollback()
        database.drop_all()
