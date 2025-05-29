"""
Core Blueprint - Main application entry points and dashboard functionality.

This blueprint handles:
- Home page and main entry points (/)
- Dashboard views and functionality
- Test routes

Routes: 4 total
- / (GET) - Home page/entry point
- /test_base_render (GET) - Testing route
- /dashboard (GET) - Main dashboard view
- /dashboard (POST) - Dashboard POST actions
"""

from flask import Blueprint

# Create blueprint with no URL prefix (core routes)
core_bp = Blueprint('core', __name__)

# Import routes to register them with the blueprint
from . import routes 