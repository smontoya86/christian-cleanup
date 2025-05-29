"""
System Blueprint - System health, monitoring, and utility functions.

This blueprint handles:
- System health checks
- Sync status monitoring
- Authentication status checks
- System monitoring dashboard

Routes: 4 total
- /api/sync-status (GET) - Get sync status
- /check_auth (GET) - Check authentication status
- /health (GET) - Health check endpoint
- /monitoring (GET) - System monitoring dashboard
"""

from flask import Blueprint

# Create blueprint with no URL prefix (system routes keep existing paths)
system_bp = Blueprint('system', __name__)

# Import routes to register them with the blueprint
from . import routes 