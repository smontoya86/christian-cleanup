"""
Admin Blueprint - Administrative functions and operations.

This blueprint handles:
- Administrative playlist resyncing
- Administrative song reanalysis
- Admin status monitoring

Routes: 3 total
- /admin/resync-all-playlists (POST) - Admin: Resync all playlists
- /admin/reanalyze-all-songs (POST) - Admin: Reanalyze all songs
- /api/admin/reanalysis-status (GET) - Admin: Get reanalysis status
"""

from flask import Blueprint

# Create blueprint with no URL prefix (admin routes keep existing paths)
admin_bp = Blueprint('admin', __name__)

# Import routes to register them with the blueprint
from . import routes 