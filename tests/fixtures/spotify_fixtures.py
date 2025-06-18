"""
Spotify API Test Fixtures

Provides realistic mock data that matches the structure and content
of actual Spotify Web API responses. These fixtures are used by the
mock Spotify service to provide deterministic test data.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


# Base Spotify User Profile
SPOTIFY_USER_PROFILE = {
    "id": "test_user_123",
    "display_name": "Test User",
    "email": "test@example.com",
    "country": "US",
    "followers": {"href": None, "total": 42},
    "images": [
        {
            "url": "https://i.scdn.co/image/ab6775700000ee85123456789",
            "height": 640,
            "width": 640
        }
    ],
    "external_urls": {
        "spotify": "https://open.spotify.com/user/test_user_123"
    },
    "href": "https://api.spotify.com/v1/users/test_user_123",
    "type": "user",
    "uri": "spotify:user:test_user_123"
}

# Sample playlist data  
SPOTIFY_PLAYLIST_DETAILS = {
    "id": "test_playlist_123",
    "name": "My Christian Music",
    "description": "A collection of worship songs",
    "public": False,
    "collaborative": False,
    "followers": {"href": None, "total": 5},
    "images": [
        {
            "url": "https://i.scdn.co/image/ab67616d0000b273playlist123",
            "height": 640,
            "width": 640
        }
    ],
    "owner": {
        "id": "test_user_123",
        "display_name": "Test User",
        "external_urls": {"spotify": "https://open.spotify.com/user/test_user_123"},
        "href": "https://api.spotify.com/v1/users/test_user_123",
        "type": "user",
        "uri": "spotify:user:test_user_123"
    },
    "tracks": {
        "href": "https://api.spotify.com/v1/playlists/test_playlist_123/tracks",
        "total": 3
    },
    "external_urls": {
        "spotify": "https://open.spotify.com/playlist/test_playlist_123"
    },
    "href": "https://api.spotify.com/v1/playlists/test_playlist_123",
    "snapshot_id": "test_snapshot_123",
    "type": "playlist",
    "uri": "spotify:playlist:test_playlist_123"
}

# Sample track data
SPOTIFY_TRACK_DETAILS = [
    {
        "id": "track_123",
        "name": "Amazing Grace",
        "artists": [
            {
                "id": "artist_123",
                "name": "Chris Tomlin",
                "external_urls": {"spotify": "https://open.spotify.com/artist/artist_123"},
                "href": "https://api.spotify.com/v1/artists/artist_123",
                "type": "artist",
                "uri": "spotify:artist:artist_123"
            }
        ],
        "album": {
            "id": "album_123",
            "name": "Worship Collection",
            "images": [
                {
                    "url": "https://i.scdn.co/image/ab67616d0000b273album123",
                    "height": 640,
                    "width": 640
                }
            ],
            "release_date": "2023-01-15",
            "release_date_precision": "day",
            "type": "album",
            "uri": "spotify:album:album_123"
        },
        "duration_ms": 240000,
        "explicit": False,
        "external_ids": {"isrc": "USRC17607839"},
        "external_urls": {"spotify": "https://open.spotify.com/track/track_123"},
        "href": "https://api.spotify.com/v1/tracks/track_123",
        "is_local": False,
        "popularity": 85,
        "preview_url": "https://p.scdn.co/mp3-preview/track_123",
        "track_number": 1,
        "type": "track",
        "uri": "spotify:track:track_123"
    },
    {
        "id": "track_456",
        "name": "How Great Is Our God",
        "artists": [
            {
                "id": "artist_123",
                "name": "Chris Tomlin",
                "external_urls": {"spotify": "https://open.spotify.com/artist/artist_123"},
                "href": "https://api.spotify.com/v1/artists/artist_123",
                "type": "artist",
                "uri": "spotify:artist:artist_123"
            }
        ],
        "album": {
            "id": "album_456",
            "name": "Arriving",
            "images": [
                {
                    "url": "https://i.scdn.co/image/ab67616d0000b273album456",
                    "height": 640,
                    "width": 640
                }
            ],
            "release_date": "2004-09-21",
            "release_date_precision": "day",
            "type": "album",
            "uri": "spotify:album:album_456"
        },
        "duration_ms": 265000,
        "explicit": False,
        "external_ids": {"isrc": "USRC17607840"},
        "external_urls": {"spotify": "https://open.spotify.com/track/track_456"},
        "href": "https://api.spotify.com/v1/tracks/track_456",
        "is_local": False,
        "popularity": 92,
        "preview_url": "https://p.scdn.co/mp3-preview/track_456",
        "track_number": 3,
        "type": "track",
        "uri": "spotify:track:track_456"
    },
    {
        "id": "track_789",
        "name": "Blessed Be Your Name",
        "artists": [
            {
                "id": "artist_789",
                "name": "Matt Redman",
                "external_urls": {"spotify": "https://open.spotify.com/artist/artist_789"},
                "href": "https://api.spotify.com/v1/artists/artist_789",
                "type": "artist",
                "uri": "spotify:artist:artist_789"
            }
        ],
        "album": {
            "id": "album_789",
            "name": "Where Angels Fear to Tread",
            "images": [
                {
                    "url": "https://i.scdn.co/image/ab67616d0000b273album789",
                    "height": 640,
                    "width": 640
                }
            ],
            "release_date": "2002-08-26",
            "release_date_precision": "day",
            "type": "album",
            "uri": "spotify:album:album_789"
        },
        "duration_ms": 290000,
        "explicit": False,
        "external_ids": {"isrc": "GBUM71506789"},
        "external_urls": {"spotify": "https://open.spotify.com/track/track_789"},
        "href": "https://api.spotify.com/v1/tracks/track_789",
        "is_local": False,
        "popularity": 88,
        "preview_url": "https://p.scdn.co/mp3-preview/track_789",
        "track_number": 5,
        "type": "track",
        "uri": "spotify:track:track_789"
    }
]

# Playlist tracks response
SPOTIFY_PLAYLIST_TRACKS = {
    "href": "https://api.spotify.com/v1/playlists/test_playlist_123/tracks?offset=0&limit=100",
    "items": [
        {
            "added_at": "2023-12-01T10:30:00Z",
            "added_by": {
                "id": "test_user_123",
                "external_urls": {"spotify": "https://open.spotify.com/user/test_user_123"},
                "href": "https://api.spotify.com/v1/users/test_user_123",
                "type": "user",
                "uri": "spotify:user:test_user_123"
            },
            "is_local": False,
            "primary_color": None,
            "track": SPOTIFY_TRACK_DETAILS[0],
            "video_thumbnail": {"url": None}
        },
        {
            "added_at": "2023-12-01T11:15:00Z",
            "added_by": {
                "id": "test_user_123",
                "external_urls": {"spotify": "https://open.spotify.com/user/test_user_123"},
                "href": "https://api.spotify.com/v1/users/test_user_123",
                "type": "user",
                "uri": "spotify:user:test_user_123"
            },
            "is_local": False,
            "primary_color": None,
            "track": SPOTIFY_TRACK_DETAILS[1],
            "video_thumbnail": {"url": None}
        },
        {
            "added_at": "2023-12-01T12:00:00Z",
            "added_by": {
                "id": "test_user_123",
                "external_urls": {"spotify": "https://open.spotify.com/user/test_user_123"},
                "href": "https://api.spotify.com/v1/users/test_user_123",
                "type": "user",
                "uri": "spotify:user:test_user_123"
            },
            "is_local": False,
            "primary_color": None,
            "track": SPOTIFY_TRACK_DETAILS[2],
            "video_thumbnail": {"url": None}
        }
    ],
    "limit": 100,
    "next": None,
    "offset": 0,
    "previous": None,
    "total": 3
}

# Playlists response
SPOTIFY_PLAYLISTS_RESPONSE = {
    "href": "https://api.spotify.com/v1/users/test_user_123/playlists?offset=0&limit=20",
    "items": [
        SPOTIFY_PLAYLIST_DETAILS,
        {
            "id": "test_playlist_456",
            "name": "Worship Favorites",
            "description": "My favorite worship songs",
            "public": True,
            "collaborative": False,
            "followers": {"href": None, "total": 12},
            "images": [
                {
                    "url": "https://i.scdn.co/image/ab67616d0000b273playlist456",
                    "height": 640,
                    "width": 640
                }
            ],
            "owner": {
                "id": "test_user_123",
                "display_name": "Test User",
                "external_urls": {"spotify": "https://open.spotify.com/user/test_user_123"},
                "href": "https://api.spotify.com/v1/users/test_user_123",
                "type": "user",
                "uri": "spotify:user:test_user_123"
            },
            "tracks": {
                "href": "https://api.spotify.com/v1/playlists/test_playlist_456/tracks",
                "total": 8
            },
            "external_urls": {
                "spotify": "https://open.spotify.com/playlist/test_playlist_456"
            },
            "href": "https://api.spotify.com/v1/playlists/test_playlist_456",
            "snapshot_id": "test_snapshot_456",
            "type": "playlist",
            "uri": "spotify:playlist:test_playlist_456"
        }
    ],
    "limit": 20,
    "next": None,
    "offset": 0,
    "previous": None,
    "total": 2
}

# Error responses for different scenarios
SPOTIFY_ERROR_RESPONSES = {
    "unauthorized": {
        "error": {
            "status": 401,
            "message": "Invalid access token"
        }
    },
    "forbidden": {
        "error": {
            "status": 403,
            "message": "Insufficient client scope"
        }
    },
    "not_found": {
        "error": {
            "status": 404,
            "message": "Not found."
        }
    },
    "rate_limit": {
        "error": {
            "status": 429,
            "message": "API rate limit exceeded",
            "retry_after": 60
        }
    },
    "server_error": {
        "error": {
            "status": 500,
            "message": "Internal server error"
        }
    }
}


def create_spotify_user(user_id: str = "test_user", 
                       display_name: str = "Test User",
                       email: str = "test@example.com") -> Dict[str, Any]:
    """Create a custom Spotify user profile fixture."""
    user = SPOTIFY_USER_PROFILE.copy()
    user["id"] = user_id
    user["display_name"] = display_name
    user["email"] = email
    user["external_urls"]["spotify"] = f"https://open.spotify.com/user/{user_id}"
    user["href"] = f"https://api.spotify.com/v1/users/{user_id}"
    user["uri"] = f"spotify:user:{user_id}"
    return user


def create_spotify_playlist(playlist_id: str = "test_playlist",
                           name: str = "Test Playlist",
                           description: str = "A test playlist",
                           owner_id: str = "test_user",
                           public: bool = False,
                           track_count: int = 0) -> Dict[str, Any]:
    """Create a custom Spotify playlist fixture."""
    playlist = SPOTIFY_PLAYLIST_DETAILS.copy()
    playlist["id"] = playlist_id
    playlist["name"] = name
    playlist["description"] = description
    playlist["public"] = public
    playlist["owner"]["id"] = owner_id
    playlist["tracks"]["total"] = track_count
    playlist["snapshot_id"] = f"snapshot_{playlist_id}"
    playlist["external_urls"]["spotify"] = f"https://open.spotify.com/playlist/{playlist_id}"
    playlist["href"] = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    playlist["uri"] = f"spotify:playlist:{playlist_id}"
    return playlist


def create_spotify_track(track_id: str = "test_track",
                        name: str = "Test Song",
                        artist_name: str = "Test Artist",
                        album_name: str = "Test Album",
                        duration_ms: int = 240000,
                        explicit: bool = False) -> Dict[str, Any]:
    """Create a custom Spotify track fixture."""
    track = SPOTIFY_TRACK_DETAILS[0].copy()
    track["id"] = track_id
    track["name"] = name
    track["duration_ms"] = duration_ms
    track["explicit"] = explicit
    track["uri"] = f"spotify:track:{track_id}"
    track["external_urls"]["spotify"] = f"https://open.spotify.com/track/{track_id}"
    track["href"] = f"https://api.spotify.com/v1/tracks/{track_id}"
    
    # Update artist
    track["artists"] = [{
        "id": f"artist_{track_id}",
        "name": artist_name,
        "external_urls": {"spotify": f"https://open.spotify.com/artist/artist_{track_id}"},
        "href": f"https://api.spotify.com/v1/artists/artist_{track_id}",
        "type": "artist",
        "uri": f"spotify:artist:artist_{track_id}"
    }]
    
    # Update album
    track["album"]["name"] = album_name
    track["album"]["id"] = f"album_{track_id}"
    track["album"]["uri"] = f"spotify:album:album_{track_id}"
    
    return track


def create_playlist_tracks_response(playlist_id: str,
                                   tracks: List[Dict[str, Any]],
                                   offset: int = 0,
                                   limit: int = 100) -> Dict[str, Any]:
    """Create a playlist tracks response with custom tracks."""
    items = []
    for i, track in enumerate(tracks):
        item = {
            "added_at": "2023-12-01T10:30:00Z",
            "added_by": {
                "id": "test_user_123",
                "external_urls": {"spotify": "https://open.spotify.com/user/test_user_123"},
                "href": "https://api.spotify.com/v1/users/test_user_123",
                "type": "user",
                "uri": "spotify:user:test_user_123"
            },
            "is_local": False,
            "primary_color": None,
            "track": track,
            "video_thumbnail": {"url": None}
        }
        items.append(item)
    
    return {
        "href": f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={offset}&limit={limit}",
        "items": items,
        "limit": limit,
        "next": None if len(items) < limit else f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={offset + limit}&limit={limit}",
        "offset": offset,
        "previous": None if offset == 0 else f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={max(0, offset - limit)}&limit={limit}",
        "total": len(items)
    }


def create_tracks_response(tracks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a tracks response for multiple track details."""
    return {
        "tracks": tracks
    } 