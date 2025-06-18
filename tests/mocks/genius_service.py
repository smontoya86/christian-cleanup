"""
Mock Genius Service for Testing

Provides a mock implementation of the Genius API service that returns
controlled, deterministic responses for testing purposes.
"""

from typing import Any, Dict, List, Optional
from .base import BaseMockService
from ..fixtures.genius_fixtures import GENIUS_SONG_SEARCH, GENIUS_LYRICS_RESPONSE


class MockGeniusService(BaseMockService):
    """
    Mock implementation of Genius API service for testing.
    
    This is a minimal implementation that will be expanded in subtask 57.3.
    """
    
    def _default_test_data(self) -> Dict[str, Any]:
        """Return default test data for Genius service."""
        return {
            'song_search': GENIUS_SONG_SEARCH,
            'lyrics': GENIUS_LYRICS_RESPONSE
        }
    
    def search_song(self, query: str) -> Dict[str, Any]:
        """Mock song search."""
        self._simulate_network_call('search_song', query=query)
        return self.test_data['song_search']
    
    def get_lyrics(self, song_id: int) -> Dict[str, Any]:
        """Mock lyrics retrieval."""
        self._simulate_network_call('get_lyrics', song_id=song_id)
        return self.test_data['lyrics'] 