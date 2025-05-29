"""
Playlist Blueprint - Playlist viewing, management, and synchronization.

This blueprint handles:
- Playlist detail viewing
- Playlist updates and management
- Spotify synchronization
- Song removal from playlists
- Playlist analysis

Routes: 5 total
- /playlist/<playlist_id> (GET) - View playlist details
- /playlist/<playlist_id>/update (POST) - Update playlist info
- /sync-playlists (POST) - Sync with Spotify
- /remove_song/<playlist_id>/<track_id> (POST) - Remove song from playlist
- /analyze_playlist_api/<playlist_id> (POST) - Analyze playlist
"""

from flask import Blueprint

# Create blueprint with no URL prefix (playlist routes keep existing paths)
playlist_bp = Blueprint('playlist', __name__)

# Import routes to register them with the blueprint
from . import routes 