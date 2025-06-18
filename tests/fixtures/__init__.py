"""
Test Fixtures Module

This module provides realistic test data fixtures for external API responses
used in testing. The fixtures are designed to mimic actual API responses
while being deterministic and controllable for testing purposes.

Available Fixtures:
- spotify_fixtures: Mock data for Spotify Web API responses
- genius_fixtures: Mock data for Genius API responses
"""

from .spotify_fixtures import *
from .genius_fixtures import *

__all__ = [
    # Spotify fixtures
    'SPOTIFY_USER_PROFILE',
    'SPOTIFY_PLAYLISTS_RESPONSE',
    'SPOTIFY_PLAYLIST_DETAILS',
    'SPOTIFY_PLAYLIST_TRACKS',
    'SPOTIFY_TRACK_DETAILS',
    'SPOTIFY_ERROR_RESPONSES',
    'create_spotify_playlist',
    'create_spotify_track',
    'create_spotify_user',
    
    # Genius fixtures
    'GENIUS_SONG_SEARCH',
    'GENIUS_LYRICS_RESPONSE',
    'GENIUS_ERROR_RESPONSES',
    'create_genius_song',
    'create_lyrics_response'
] 