"""
Mock Integration Helpers

Provides utilities for integrating mock services into tests, including
patching real services and components with mocks to ensure predictable
test behavior.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from typing import Any, Dict, List, Optional, Generator
from contextlib import contextmanager

from ..mocks import MockServiceFactory, MockSpotifyService, MockAnalysisService
from ..mocks.analysis_mocks import (
    MockAnalysisResult, MockSongAnalyzer, MockUnifiedAnalysisService,
    create_mock_analysis_result, create_mock_song_analyzer
)
from ..fixtures.spotify_fixtures import create_spotify_track, create_spotify_playlist


@contextmanager
def setup_spotify_mocks(test_data: Optional[Dict[str, Any]] = None) -> Generator[MockSpotifyService, None, None]:
    """
    Context manager to set up Spotify service mocks.
    
    Args:
        test_data: Custom test data for the mock service
        
    Yields:
        MockSpotifyService instance
    """
    mock_service = MockServiceFactory.create_spotify_service(test_data=test_data)
    
    with patch('app.services.spotify_service.SpotifyService', return_value=mock_service):
        yield mock_service


@contextmanager
def setup_analysis_mocks(test_data: Optional[Dict[str, Any]] = None) -> Generator[Dict[str, Any], None, None]:
    """
    Context manager to set up analysis service mocks.
    
    This patches all the analysis components that the failing tests expect.
    
    Args:
        test_data: Custom test data for the mock service
        
    Yields:
        Dictionary of mock components
    """
    # Create mock instances
    mock_analysis_service = MockServiceFactory.create_analysis_service(test_data=test_data)
    mock_song_analyzer = create_mock_song_analyzer()
    mock_unified_service = MockUnifiedAnalysisService()
    
    mocks = {
        'analysis_service': mock_analysis_service,
        'song_analyzer': mock_song_analyzer,
        'unified_service': mock_unified_service
    }
    
    # Patch the analysis components
    with patch('app.utils.analysis.legacy_adapter.SongAnalyzer', return_value=mock_song_analyzer), \
         patch('app.services.unified_analysis_service.UnifiedAnalysisService', return_value=mock_unified_service), \
         patch('app.utils.analysis.orchestrator.AnalysisOrchestrator') as mock_orchestrator:
        
        # Configure the orchestrator mock to return proper analysis results
        mock_orchestrator.return_value.analyze_song.return_value = create_mock_analysis_result()
        mocks['orchestrator'] = mock_orchestrator
        
        yield mocks


@contextmanager
def setup_all_mocks(spotify_data: Optional[Dict[str, Any]] = None,
                   analysis_data: Optional[Dict[str, Any]] = None) -> Generator[Dict[str, Any], None, None]:
    """
    Context manager to set up all mock services.
    
    Args:
        spotify_data: Custom test data for Spotify service
        analysis_data: Custom test data for analysis service
        
    Yields:
        Dictionary of all mock services
    """
    with setup_spotify_mocks(spotify_data) as spotify_mock, \
         setup_analysis_mocks(analysis_data) as analysis_mocks:
        
        yield {
            'spotify': spotify_mock,
            **analysis_mocks
        }


def create_mock_user(user_id: int = 1, 
                    spotify_id: str = "test_user_123",
                    access_token: str = "mock_access_token") -> Mock:
    """
    Create a mock User object with required attributes.
    
    Args:
        user_id: Database user ID
        spotify_id: Spotify user ID
        access_token: Mock access token
        
    Returns:
        Mock User object
    """
    mock_user = Mock()
    mock_user.id = user_id
    mock_user.spotify_id = spotify_id
    mock_user.access_token = access_token
    mock_user.get_access_token.return_value = access_token
    mock_user.ensure_token_valid.return_value = True
    
    return mock_user


def create_mock_song(song_id: int = 1,
                    title: str = "Test Song",
                    artist: str = "Test Artist",
                    spotify_id: str = "track_123") -> Mock:
    """
    Create a mock Song object with required attributes.
    
    Args:
        song_id: Database song ID
        title: Song title
        artist: Artist name
        spotify_id: Spotify track ID
        
    Returns:
        Mock Song object
    """
    mock_song = Mock()
    mock_song.id = song_id
    mock_song.title = title
    mock_song.artist = artist
    mock_song.spotify_id = spotify_id
    mock_song.explicit = False
    mock_song.album = "Test Album"
    mock_song.album_art_url = "https://example.com/album_art.jpg"
    
    return mock_song


def create_mock_playlist(playlist_id: int = 1,
                        name: str = "Test Playlist",
                        spotify_id: str = "test_playlist_123",
                        user_id: int = 1) -> Mock:
    """
    Create a mock Playlist object with required attributes.
    
    Args:
        playlist_id: Database playlist ID
        name: Playlist name
        spotify_id: Spotify playlist ID
        user_id: Owner user ID
        
    Returns:
        Mock Playlist object
    """
    mock_playlist = Mock()
    mock_playlist.id = playlist_id
    mock_playlist.name = name
    mock_playlist.spotify_id = spotify_id
    mock_playlist.user_id = user_id
    mock_playlist.description = "Test playlist description"
    mock_playlist.public = False
    mock_playlist.snapshot_id = f"snapshot_{spotify_id}"
    
    return mock_playlist


# Pytest fixtures for common mock setups
@pytest.fixture
def mock_spotify_service():
    """Pytest fixture for MockSpotifyService."""
    return MockServiceFactory.create_spotify_service()


@pytest.fixture
def mock_analysis_service():
    """Pytest fixture for MockAnalysisService."""
    return MockServiceFactory.create_analysis_service()


@pytest.fixture
def mock_song_analyzer():
    """Pytest fixture for MockSongAnalyzer."""
    return create_mock_song_analyzer()


@pytest.fixture
def mock_user():
    """Pytest fixture for mock User."""
    return create_mock_user()


@pytest.fixture
def mock_song():
    """Pytest fixture for mock Song."""
    return create_mock_song()


@pytest.fixture
def mock_playlist():
    """Pytest fixture for mock Playlist."""
    return create_mock_playlist()


@pytest.fixture
def all_mocks():
    """Pytest fixture that provides all mocks in a context manager."""
    @contextmanager
    def _all_mocks(spotify_data=None, analysis_data=None):
        with setup_all_mocks(spotify_data, analysis_data) as mocks:
            yield mocks
    
    return _all_mocks


# Decorator for easy test mocking
def with_mocks(spotify_data: Optional[Dict[str, Any]] = None,
              analysis_data: Optional[Dict[str, Any]] = None):
    """
    Decorator to automatically set up mocks for a test function.
    
    Args:
        spotify_data: Custom test data for Spotify service
        analysis_data: Custom test data for analysis service
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            with setup_all_mocks(spotify_data, analysis_data) as mocks:
                return test_func(*args, mocks=mocks, **kwargs)
        return wrapper
    return decorator 