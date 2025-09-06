"""
Service layer for business logic
"""

# Ensure submodule attributes exist for patch targets like
# "app.services.spotify_service.SpotifyService" in tests
from . import spotify_service as spotify_service  # noqa: F401

from .spotify_service import SpotifyService
from .unified_analysis_service import UnifiedAnalysisService

__all__ = ["SpotifyService", "UnifiedAnalysisService", "spotify_service"]
