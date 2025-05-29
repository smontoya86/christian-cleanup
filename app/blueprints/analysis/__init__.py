"""
Analysis Blueprint - Analysis operations, status checking, and data retrieval.

This blueprint handles:
- Song analysis operations
- Playlist analysis operations  
- Analysis status checking
- Reanalysis functionality
- Analysis data retrieval

Routes: 14 total
- /api/songs/<song_id>/analysis-status (GET) - Get song analysis status
- /api/playlists/<playlist_id>/analysis-status (GET) - Get playlist analysis status
- /api/songs/<song_id>/analyze (POST) - Analyze single song
- /api/songs/<song_id>/reanalyze (POST) - Reanalyze single song
- /api/playlists/<playlist_id>/analyze-unanalyzed (POST) - Analyze unanalyzed songs
- /api/playlists/<playlist_id>/reanalyze-all (POST) - Reanalyze all songs
- /api/analysis/playlist/<playlist_id> (GET) - Get playlist analysis data
- /api/analysis/song/<song_id> (GET) - Get song analysis data
- /comprehensive_reanalyze_all_user_songs/<user_id> (GET) - Comprehensive reanalysis
- Plus backward compatibility variants
"""

from flask import Blueprint

# Create blueprint with no URL prefix (API routes keep existing paths)
analysis_bp = Blueprint('analysis', __name__)

# Import routes to register them with the blueprint
from . import routes 