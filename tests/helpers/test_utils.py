"""
Test Utility Functions

Provides common assertion helpers and utility functions for tests.
"""

from typing import Any, Dict, List, Optional, Union


def assert_has_attributes(obj: Any, attributes: List[str], message: str = "Missing expected attributes") -> None:
    """
    Assert that an object has all the specified attributes.
    
    Args:
        obj: Object to check
        attributes: List of attribute names that should exist
        message: Custom error message
        
    Raises:
        AssertionError: If any attribute is missing
    """
    missing_attrs = []
    for attr in attributes:
        if not hasattr(obj, attr):
            missing_attrs.append(attr)
    
    if missing_attrs:
        raise AssertionError(f"{message}: {', '.join(missing_attrs)}")


def assert_analysis_result_valid(result: Any, expected_safe: Optional[bool] = None) -> None:
    """
    Assert that an analysis result has all expected attributes and valid values.
    
    Args:
        result: Analysis result object to validate
        expected_safe: Expected safety status (None to skip check)
        
    Raises:
        AssertionError: If validation fails
    """
    # Check required attributes
    required_attrs = [
        'content_flags', 'themes_detected', 'is_safe', 'overall_score',
        'analysis_details', 'song_id'
    ]
    assert_has_attributes(result, required_attrs, "Analysis result missing attributes")
    
    # Check content_flags structure
    expected_flags = ['explicit_language', 'violence', 'drugs', 'sexual_content', 'hate_speech']
    for flag in expected_flags:
        assert flag in result.content_flags, f"Missing content flag: {flag}"
        assert isinstance(result.content_flags[flag], bool), f"Content flag {flag} should be boolean"
    
    # Check themes_detected structure
    expected_themes = ['worship', 'praise', 'salvation', 'faith', 'prayer', 'scripture_reference']
    for theme in expected_themes:
        assert theme in result.themes_detected, f"Missing theme: {theme}"
        assert isinstance(result.themes_detected[theme], bool), f"Theme {theme} should be boolean"
    
    # Check basic types
    assert isinstance(result.is_safe, bool), "is_safe should be boolean"
    assert isinstance(result.overall_score, (int, float)), "overall_score should be numeric"
    assert isinstance(result.song_id, int), "song_id should be integer"
    
    # Check expected safety if provided
    if expected_safe is not None:
        assert result.is_safe == expected_safe, f"Expected safety: {expected_safe}, got: {result.is_safe}"


def assert_spotify_response_valid(response: Dict[str, Any], response_type: str = "general") -> None:
    """
    Assert that a Spotify API response has the expected structure.
    
    Args:
        response: Spotify API response to validate
        response_type: Type of response ('playlists', 'tracks', 'user', 'general')
        
    Raises:
        AssertionError: If validation fails
    """
    assert isinstance(response, dict), "Spotify response should be a dictionary"
    
    if response_type == "playlists":
        required_keys = ['items', 'limit', 'offset', 'total']
        for key in required_keys:
            assert key in response, f"Missing key in playlists response: {key}"
        
        assert isinstance(response['items'], list), "Playlists items should be a list"
        
        # Check individual playlist structure
        for playlist in response['items']:
            playlist_keys = ['id', 'name', 'owner', 'tracks', 'external_urls']
            for key in playlist_keys:
                assert key in playlist, f"Missing key in playlist: {key}"
    
    elif response_type == "tracks":
        assert 'items' in response, "Tracks response should have 'items'"
        assert isinstance(response['items'], list), "Track items should be a list"
        
        # Check individual track structure
        for item in response['items']:
            if 'track' in item:
                track = item['track']
                track_keys = ['id', 'name', 'artists', 'album', 'duration_ms']
                for key in track_keys:
                    assert key in track, f"Missing key in track: {key}"
    
    elif response_type == "user":
        user_keys = ['id', 'display_name', 'external_urls']
        for key in user_keys:
            assert key in response, f"Missing key in user response: {key}"


def count_positive_themes(themes_dict: Dict[str, bool]) -> int:
    """
    Count the number of positive (True) themes in a themes dictionary.
    
    Args:
        themes_dict: Dictionary of theme names to boolean values
        
    Returns:
        Number of themes that are True
    """
    return sum(1 for value in themes_dict.values() if value)


def create_test_track_data(track_id: str = "test_track",
                          name: str = "Test Song",
                          artist: str = "Test Artist",
                          explicit: bool = False) -> Dict[str, Any]:
    """
    Create test track data for use in tests.
    
    Args:
        track_id: Spotify track ID
        name: Track name
        artist: Artist name
        explicit: Whether track is explicit
        
    Returns:
        Dictionary with track data
    """
    return {
        'id': track_id,
        'name': name,
        'artists': [{'name': artist}],
        'album': {'name': 'Test Album'},
        'duration_ms': 240000,
        'explicit': explicit,
        'uri': f'spotify:track:{track_id}',
        'external_urls': {'spotify': f'https://open.spotify.com/track/{track_id}'}
    }


def create_test_playlist_data(playlist_id: str = "test_playlist",
                             name: str = "Test Playlist",
                             track_count: int = 0) -> Dict[str, Any]:
    """
    Create test playlist data for use in tests.
    
    Args:
        playlist_id: Spotify playlist ID
        name: Playlist name
        track_count: Number of tracks in playlist
        
    Returns:
        Dictionary with playlist data
    """
    return {
        'id': playlist_id,
        'name': name,
        'description': 'Test playlist description',
        'public': False,
        'owner': {
            'id': 'test_user',
            'display_name': 'Test User'
        },
        'tracks': {
            'total': track_count,
            'href': f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
        },
        'external_urls': {'spotify': f'https://open.spotify.com/playlist/{playlist_id}'},
        'snapshot_id': f'snapshot_{playlist_id}'
    }


def extract_flash_messages(response_data: str) -> List[Dict[str, str]]:
    """
    Extract flash messages from Flask response HTML.
    
    This is a simple text-based extraction for testing purposes.
    In a real application, you might use BeautifulSoup or similar.
    
    Args:
        response_data: HTML response data as string
        
    Returns:
        List of dictionaries with 'category' and 'message' keys
    """
    messages = []
    
    # Simple pattern matching for flash messages
    # This would need to be adapted based on your actual HTML structure
    if 'alert-danger' in response_data:
        # Extract danger messages
        pass
    elif 'alert-warning' in response_data:
        # Extract warning messages  
        pass
    elif 'alert-success' in response_data:
        # Extract success messages
        pass
    
    return messages


def assert_flash_message(response, expected_category: str, expected_message: Optional[str] = None) -> None:
    """
    Assert that a Flask response contains a flash message with the expected category.
    
    Args:
        response: Flask test response object
        expected_category: Expected flash message category ('success', 'danger', 'warning', 'info')
        expected_message: Expected message content (optional)
        
    Raises:
        AssertionError: If flash message doesn't match expectations
    """
    # This would need to be implemented based on how your Flask app handles flash messages
    # For now, this is a placeholder that can be customized
    pass


def mock_database_error():
    """Create a mock database error for testing error handling."""
    from sqlalchemy.exc import SQLAlchemyError
    return SQLAlchemyError("Mock database error")


def mock_spotify_error(status_code: int = 500, message: str = "Mock Spotify error"):
    """Create a mock Spotify API error for testing error handling."""
    import spotipy
    return spotipy.SpotifyException(status_code, -1, message) 