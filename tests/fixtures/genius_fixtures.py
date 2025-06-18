"""
Genius API Test Fixtures

Provides realistic mock data that matches the structure and content
of actual Genius API responses. These fixtures are used by the
mock Genius service to provide deterministic test data.
"""

from typing import Any, Dict, List, Optional

# Basic Genius API responses - will be expanded in subtask 57.3
GENIUS_SONG_SEARCH = {
    "response": {
        "songs": [
            {
                "id": 123456,
                "title": "Amazing Grace",
                "artist_names": "Chris Tomlin",
                "url": "https://genius.com/chris-tomlin-amazing-grace-lyrics"
            }
        ]
    }
}

GENIUS_LYRICS_RESPONSE = {
    "lyrics": "Amazing grace, how sweet the sound\nThat saved a wretch like me"
}

GENIUS_ERROR_RESPONSES = {
    "not_found": {
        "error": "Song not found"
    }
}

def create_genius_song(song_id: int = 123456, 
                      title: str = "Test Song",
                      artist: str = "Test Artist") -> Dict[str, Any]:
    """Create a custom Genius song fixture."""
    return {
        "id": song_id,
        "title": title,
        "artist_names": artist,
        "url": f"https://genius.com/{artist.lower().replace(' ', '-')}-{title.lower().replace(' ', '-')}-lyrics"
    }

def create_lyrics_response(lyrics: str) -> Dict[str, Any]:
    """Create a custom lyrics response fixture."""
    return {
        "lyrics": lyrics
    } 