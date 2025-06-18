"""
Biblical Analysis Engine Module

Provides comprehensive biblical content analysis capabilities for song lyrics,
including theme detection, scripture mapping, and spiritual content classification.
"""

import time
from typing import Dict, Any, List, Optional
from ...logging import get_logger
from .enhanced_detector import EnhancedBiblicalDetector
from .theme_detector import BiblicalThemeDetector
from .scripture_mapper import ScriptureReferenceMapper

logger = get_logger('app.utils.analysis.biblical.analysis_engine')


class BiblicalAnalysisEngine:
    """
    Engine for analyzing biblical and spiritual content in song lyrics.
    
    Coordinates theme detection, scripture mapping, and spiritual content
    classification to provide comprehensive biblical analysis.
    """
    
    def __init__(self, config=None):
        """
        Initialize the biblical analysis engine.
        
        Args:
            config: Analysis configuration object
        """
        self.config = config
        
        # Convert AnalysisConfig to dictionary if needed
        biblical_config = {}
        if config:
            if hasattr(config, 'user_preferences') and hasattr(config.user_preferences, 'get_biblical_preferences'):
                biblical_config = config.user_preferences.get_biblical_preferences()
            elif hasattr(config, 'to_dict'):
                biblical_config = config.to_dict()
            elif isinstance(config, dict):
                biblical_config = config
        
        # Initialize biblical analysis components
        self.enhanced_detector = EnhancedBiblicalDetector(biblical_config)
        self.theme_detector = BiblicalThemeDetector(biblical_config)
        self.scripture_mapper = ScriptureReferenceMapper()
        
        logger.info("BiblicalAnalysisEngine initialized")
    
    def analyze_biblical_content(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        Perform comprehensive biblical analysis on text.
        
        Args:
            text: Text to analyze
            **kwargs: Additional analysis parameters
            
        Returns:
            Dict containing biblical analysis results
        """
        start_time = time.time()
        
        try:
            results = {
                'themes': [],
                'scripture_references': [],
                'spiritual_score': 0.0,
                'biblical_categories': [],
                'processing_time': 0.0
            }
            
            # Detect biblical themes
            themes = self.theme_detector.detect_themes(text)
            results['themes'] = themes
            
            # Map scripture references
            scripture_refs = self.scripture_mapper.find_references(text)
            results['scripture_references'] = scripture_refs
            
            # Calculate spiritual score
            spiritual_score = self._calculate_spiritual_score(themes, scripture_refs)
            results['spiritual_score'] = spiritual_score
            
            # Categorize biblical content
            categories = self._categorize_biblical_content(themes, scripture_refs)
            results['biblical_categories'] = categories
            
            results['processing_time'] = time.time() - start_time
            return results
            
        except Exception as e:
            logger.error(f"Error in biblical analysis: {str(e)}")
            return {
                'themes': [],
                'scripture_references': [],
                'spiritual_score': 0.0,
                'biblical_categories': [],
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
    
    def _calculate_spiritual_score(self, themes: List[Dict], scripture_refs: List[Dict]) -> float:
        """Calculate overall spiritual content score."""
        theme_score = len(themes) * 0.3
        scripture_score = len(scripture_refs) * 0.5
        return min(theme_score + scripture_score, 10.0)
    
    def _categorize_biblical_content(self, themes: List[Dict], scripture_refs: List[Dict]) -> List[str]:
        """Categorize the type of biblical content found."""
        categories = []
        
        if themes:
            categories.append('themes')
        if scripture_refs:
            categories.append('scripture')
        if len(themes) > 3:
            categories.append('heavy_theological')
        
        return categories 