"""
Blueprints module for organizing routes into logical groups.

This module provides a centralized way to import and register all blueprints
in the Flask application. Each blueprint represents a functional area of the
application (core, playlist, song, analysis, etc.).
"""

# Import all blueprints for easy registration
from .core import core_bp
from .playlist import playlist_bp
from .song import song_bp
from .analysis import analysis_bp
from .whitelist import whitelist_bp
from .user import user_bp
from .admin import admin_bp
from .system import system_bp

# List of all blueprints for registration
ALL_BLUEPRINTS = [
    core_bp,
    playlist_bp,
    song_bp,
    analysis_bp,
    whitelist_bp,
    user_bp,
    admin_bp,
    system_bp
]

def register_blueprints(app):
    """Register all blueprints with the Flask application.
    
    Args:
        app: Flask application instance
    """
    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint) 