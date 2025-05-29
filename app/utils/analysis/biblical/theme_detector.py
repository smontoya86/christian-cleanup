"""
Biblical Theme Detector

Handles detection of biblical themes and Christian content in text.
Extracted and refactored from original analysis utilities.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

from .themes_config import BiblicalThemesConfig

logger = logging.getLogger(__name__)


@dataclass
class ThemeMatch:
    """Represents a detected biblical theme."""
    theme_name: str
    confidence: float
    matched_patterns: List[str]
    supporting_scriptures: List[str]
    context: Dict[str, Any]


class BiblicalThemeDetector:
    """
    Detects biblical themes and Christian content in text.
    
    Uses pattern matching against known biblical themes and concepts
    to identify positive Christian content.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the biblical theme detector.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.themes_config = BiblicalThemesConfig()
        
        # Configuration options
        self.min_confidence_threshold = self.config.get('min_confidence_threshold', 0.3)
        self.include_scripture_refs = self.config.get('include_scripture_refs', True)
        self.weight_multiplier = self.config.get('weight_multiplier', 1.0)
        
        logger.debug(f"BiblicalThemeDetector initialized with {len(self.themes_config.get_theme_list())} themes")
    
    def detect_themes(self, text: str) -> List[ThemeMatch]:
        """
        Detect biblical themes in the given text.
        
        Args:
            text: Text to analyze for biblical themes
            
        Returns:
            List of detected theme matches
        """
        if not text:
            return []
        
        try:
            theme_matches = []
            
            for theme_name in self.themes_config.get_theme_list():
                theme_match = self._analyze_theme(text, theme_name)
                if theme_match and theme_match.confidence >= self.min_confidence_threshold:
                    theme_matches.append(theme_match)
            
            # Sort by confidence (highest first)
            theme_matches.sort(key=lambda x: x.confidence, reverse=True)
            
            logger.debug(f"Detected {len(theme_matches)} biblical themes")
            return theme_matches
            
        except Exception as e:
            logger.error(f"Error detecting biblical themes: {e}", exc_info=True)
            return []
    
    def get_theme_summary(self, theme_matches: List[ThemeMatch]) -> Dict[str, Any]:
        """
        Generate a summary of detected themes.
        
        Args:
            theme_matches: List of detected themes
            
        Returns:
            Summary dictionary with theme information
        """
        if not theme_matches:
            return {
                'total_themes': 0,
                'average_confidence': 0.0,
                'strongest_theme': None,
                'theme_categories': [],
                'has_biblical_content': False
            }
        
        total_confidence = sum(match.confidence for match in theme_matches)
        average_confidence = total_confidence / len(theme_matches)
        
        return {
            'total_themes': len(theme_matches),
            'average_confidence': average_confidence,
            'strongest_theme': theme_matches[0].theme_name,
            'theme_categories': [match.theme_name for match in theme_matches],
            'has_biblical_content': True,
            'total_pattern_matches': sum(len(match.matched_patterns) for match in theme_matches)
        }
    
    def calculate_biblical_score_bonus(self, theme_matches: List[ThemeMatch]) -> float:
        """
        Calculate a bonus score based on detected biblical themes.
        
        Args:
            theme_matches: List of detected themes
            
        Returns:
            Bonus score (0.0 to 15.0)
        """
        if not theme_matches:
            return 0.0
        
        # Calculate weighted score based on theme strength and quantity
        total_score = 0.0
        
        for match in theme_matches:
            # Base score from confidence
            theme_score = match.confidence * 3.0  # Max 3 points per theme
            
            # Bonus for multiple pattern matches
            pattern_bonus = min(len(match.matched_patterns) * 0.5, 2.0)
            
            total_score += theme_score + pattern_bonus
        
        # Apply weight multiplier and cap at 15.0
        final_score = min(total_score * self.weight_multiplier, 15.0)
        
        return final_score
    
    def _analyze_theme(self, text: str, theme_name: str) -> Optional[ThemeMatch]:
        """
        Analyze text for a specific biblical theme.
        
        Args:
            text: Text to analyze
            theme_name: Name of the theme to check
            
        Returns:
            ThemeMatch if theme is detected, None otherwise
        """
        theme_patterns = self.themes_config.get_theme_pattern(theme_name)
        if not theme_patterns:
            return None
        
        matched_patterns = []
        total_confidence = 0.0
        
        for pattern, weight in theme_patterns.items():
            matches = self._find_pattern_matches(text, pattern)
            if matches:
                matched_patterns.extend(matches)
                # Weight can be negative for patterns that reduce confidence
                total_confidence += weight * len(matches)
        
        if not matched_patterns:
            return None
        
        # Normalize confidence (prevent negative values)
        confidence = max(0.0, min(total_confidence / 5.0, 1.0))
        
        # Get supporting scriptures if enabled
        scriptures = []
        if self.include_scripture_refs:
            all_refs = self.themes_config.get_scripture_references()
            scriptures = all_refs.get(theme_name, [])
        
        # Create context information
        context = {
            'pattern_count': len(matched_patterns),
            'unique_patterns': len(set(matched_patterns)),
            'raw_confidence': total_confidence,
            'theme_category': theme_name
        }
        
        return ThemeMatch(
            theme_name=theme_name,
            confidence=confidence,
            matched_patterns=matched_patterns,
            supporting_scriptures=scriptures,
            context=context
        )
    
    def _find_pattern_matches(self, text: str, pattern: str) -> List[str]:
        """
        Find all matches for a given pattern in text.
        
        Args:
            text: Text to search
            pattern: Regex pattern to match
            
        Returns:
            List of matched strings
        """
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            return matches
        except re.error as e:
            logger.warning(f"Invalid regex pattern {pattern}: {e}")
            return []
    
    def get_theme_explanation(self, theme_name: str) -> str:
        """
        Get a human-readable explanation of a biblical theme.
        
        Args:
            theme_name: Name of the theme
            
        Returns:
            Explanation string
        """
        explanations = {
            'worship_praise': 'Content expressing worship, praise, and adoration of God',
            'faith_trust': 'Themes of faith, trust, and confidence in God',
            'salvation_redemption': 'References to salvation, redemption, and eternal life',
            'love_grace': 'Expressions of God\'s love, grace, and mercy',
            'prayer_communion': 'Content about prayer, communion, and relationship with God',
            'hope_encouragement': 'Messages of hope, encouragement, and comfort',
            'service_discipleship': 'Themes of Christian service and discipleship',
            'biblical_references': 'Direct or indirect references to biblical content'
        }
        
        return explanations.get(theme_name, f'Biblical theme: {theme_name}') 