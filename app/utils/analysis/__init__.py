"""
Modular Analysis Utilities

This module provides a refactored, domain-driven architecture for song analysis.
The analysis functionality is split into focused domains:

- text: Text processing and preprocessing
- patterns: Pattern detection (profanity, drugs, violence)
- biblical: Biblical theme and scripture analysis  
- scoring: Score calculation and concern level determination
- models: AI model integration and management
- config: Configuration and user preferences

The main entry point is the AnalysisOrchestrator which coordinates
between domains while maintaining backward compatibility.
"""

from .orchestrator import AnalysisOrchestrator
from .legacy_adapter import BackwardCompatibilityAdapter
from .analysis_result import AnalysisResult

# For backward compatibility
from .legacy_adapter import SongAnalyzer, analyze_song_legacy

# Alias for backward compatibility
def analyze_song_content(lyrics, title, artist):
    """Backward compatibility wrapper for analyze_song_legacy."""
    return analyze_song_legacy(title, artist, lyrics)

__all__ = [
    'AnalysisOrchestrator',
    'BackwardCompatibilityAdapter', 
    'AnalysisResult',
    'SongAnalyzer',  # Legacy compatibility
    'analyze_song_content'  # Function compatibility
]

__version__ = '2.0.0' 