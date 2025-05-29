"""
Whitelist Blueprint - Whitelist and blacklist management operations.

This blueprint handles:
- Adding/removing items to/from whitelist and blacklist
- Playlist and song list management
- List item editing
- Bulk import/export functionality
- API endpoints for list management

Routes: 18 total
- /whitelist_playlist/<playlist_id> (POST) - Add playlist to whitelist
- /blacklist_song/<playlist_id>/<track_id> (POST) - Add song to blacklist
- /blacklist_playlist/<playlist_id> (POST) - Add playlist to blacklist
- /whitelist_song/<playlist_id>/<track_id> (POST) - Add song to whitelist
- /remove_whitelist_playlist/<playlist_id> (POST) - Remove playlist from whitelist
- /remove_blacklist_playlist/<playlist_id> (POST) - Remove playlist from blacklist
- /remove_whitelist_song/<playlist_id>/<track_id> (POST) - Remove song from whitelist
- /remove_blacklist_song/<playlist_id>/<track_id> (POST) - Remove song from blacklist
- /api/song/<song_db_id>/whitelist (POST) - API: Add song to whitelist
- /api/song/<song_db_id>/blacklist (POST) - API: Add song to blacklist
- /add-whitelist-item (POST) - Add whitelist item
- /add-blacklist-item (POST) - Add blacklist item
- /remove-whitelist-item/<item_id> (POST) - Remove whitelist item
- /remove-blacklist-item/<item_id> (POST) - Remove blacklist item
- /edit-whitelist-item/<item_id> (POST) - Edit whitelist item
- /edit-blacklist-item/<item_id> (POST) - Edit blacklist item
- /export-whitelist (GET) - Export whitelist
- /export-blacklist (GET) - Export blacklist
- /bulk-import-whitelist (POST) - Bulk import whitelist
- /bulk-import-blacklist (POST) - Bulk import blacklist
"""

from flask import Blueprint

# Create blueprint with no URL prefix (whitelist routes keep existing paths)
whitelist_bp = Blueprint('whitelist', __name__)

# Import routes to register them with the blueprint
from . import routes 