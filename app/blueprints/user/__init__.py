"""
User Blueprint - User settings and profile management.

This blueprint handles:
- User settings viewing and updating
- User preferences management
- Whitelist/blacklist management page

Routes: 3 total
- /settings (GET) - View user settings
- /settings (POST) - Update user settings  
- /blacklist-whitelist (GET) - Whitelist/blacklist management page
"""

from flask import Blueprint

# Create blueprint with no URL prefix (user routes keep existing paths)
user_bp = Blueprint('user', __name__)

# Import routes to register them with the blueprint
from . import routes 