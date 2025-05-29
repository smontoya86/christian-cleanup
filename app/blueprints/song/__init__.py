"""
Song Blueprint - Individual song viewing and details.

This blueprint handles:
- Song detail viewing
- Song information display

Routes: 3 total
- /songs/<song_id> (GET) - View song details
- /songs/<song_id>/ (GET) - View song details (with trailing slash)
"""

from flask import Blueprint

# Create blueprint with no URL prefix (song routes keep existing paths)
song_bp = Blueprint('song', __name__)

# Import routes to register them with the blueprint
from . import routes 