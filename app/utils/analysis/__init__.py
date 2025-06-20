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

from .analysis_result import AnalysisResult

# Main analysis function used by production code
def analyze_song_content(lyrics, title, artist):
    """Analyze song content using the orchestrator."""
    # Import here to avoid circular imports
    from .orchestrator import AnalysisOrchestrator
    orchestrator = AnalysisOrchestrator()
    return orchestrator.analyze(title, artist, lyrics)

__all__ = [
    'AnalysisResult',
    'analyze_song_content'  # Main production function
]

__version__ = '2.0.0' 