"""
Profanity Detector

Handles detection of profane language and inappropriate content.
Extracted and refactored from original analysis utilities.
"""

import re
import logging
from typing import Dict, List, Any, Optional

from .base_detector import BasePatternDetector, DetectionResult

logger = logging.getLogger(__name__)


class ProfanityDetector(BasePatternDetector):
    """
    Detects profane language and inappropriate content in text.
    
    Uses pattern matching with context awareness to reduce false positives.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the profanity detector.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Load profanity patterns based on sensitivity
        self._load_profanity_patterns()
        
        # Context patterns that might indicate acceptable usage
        self.context_patterns = self.config.get('context_patterns', [
            r'\b(quote|quoting|lyrics|song)\b',
            r'\b(not|never|don\'t|won\'t)\s+\w*',
            r'\b(avoid|avoiding|against)\b'
        ])
        
        logger.debug(f"ProfanityDetector initialized with {len(self.profanity_patterns)} patterns")
    
    def detect(self, text: str) -> DetectionResult:
        """
        Detect profanity in the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            DetectionResult with profanity findings
        """
        if not text or not self.is_enabled():
            return self._create_result(False, 0.0, [])
        
        try:
            matches = []
            total_confidence = 0.0
            
            for pattern, severity in self.profanity_patterns.items():
                pattern_matches = self._find_pattern_matches(text, pattern)
                if pattern_matches:
                    # Apply context filtering
                    filtered_matches = self._filter_by_context(text, pattern_matches)
                    if filtered_matches:
                        matches.extend(filtered_matches)
                        total_confidence += severity * len(filtered_matches)
            
            # Calculate overall confidence
            confidence = min(total_confidence / 10.0, 1.0) if matches else 0.0
            
            # Determine subcategory based on severity
            subcategory = self._determine_subcategory(matches)
            
            context_info = {
                'total_matches': len(matches),
                'sensitivity': self.sensitivity,
                'context_filtered': True
            }
            
            return self._create_result(
                detected=len(matches) > 0,
                confidence=confidence,
                matches=matches,
                subcategory=subcategory,
                context=context_info
            )
            
        except Exception as e:
            logger.error(f"Error in profanity detection: {e}", exc_info=True)
            return self._create_result(False, 0.0, [])
    
    def get_category_name(self) -> str:
        """Get the category name this detector handles."""
        return "profanity"
    
    def _load_profanity_patterns(self) -> None:
        """Load profanity patterns based on sensitivity level."""
        # Base patterns for all sensitivity levels
        base_patterns = {
            r'\bf[*]+k\b': 0.9,
            r'\bs[*]+t\b': 0.8,
            r'\bd[*]+n\b': 0.7,
            r'\bb[*]+ch\b': 0.6,
            r'\ba[*]+s\b': 0.5
        }
        
        # High sensitivity patterns
        high_sensitivity_patterns = {
            r'\bcrap\b': 0.4,
            r'\bhell\b': 0.3,
            r'\bdamn\b': 0.3,
            r'\bpiss\b': 0.4
        }
        
        # Medium sensitivity patterns  
        medium_sensitivity_patterns = {
            r'\bcrap\b': 0.4,
            r'\bhell\b': 0.2
        }
        
        # Build final pattern set based on sensitivity
        if self.sensitivity == 'high':
            self.profanity_patterns = {**base_patterns, **high_sensitivity_patterns}
        elif self.sensitivity == 'medium':
            self.profanity_patterns = {**base_patterns, **medium_sensitivity_patterns}
        else:  # low sensitivity
            self.profanity_patterns = base_patterns
    
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
    
    def _filter_by_context(self, text: str, matches: List[str]) -> List[str]:
        """
        Filter matches based on context to reduce false positives.
        
        Args:
            text: Full text for context analysis
            matches: Potential matches to filter
            
        Returns:
            Filtered list of matches
        """
        filtered_matches = []
        
        for match in matches:
            # Check if the match appears in an acceptable context
            is_acceptable_context = False
            
            for context_pattern in self.context_patterns:
                # Look for context patterns near the match
                context_search = re.search(
                    rf'{context_pattern}.{{0,50}}{re.escape(match)}|{re.escape(match)}.{{0,50}}{context_pattern}',
                    text, re.IGNORECASE
                )
                if context_search:
                    is_acceptable_context = True
                    break
            
            if not is_acceptable_context:
                filtered_matches.append(match)
        
        return filtered_matches
    
    def _determine_subcategory(self, matches: List[str]) -> str:
        """
        Determine subcategory based on types of matches found.
        
        Args:
            matches: List of matched profane terms
            
        Returns:
            Subcategory string
        """
        if not matches:
            return "none"
        
        # Count different severity levels
        severe_count = len([m for m in matches if any(
            re.search(pattern, m, re.IGNORECASE) 
            for pattern, severity in self.profanity_patterns.items() 
            if severity >= 0.8
        )])
        
        moderate_count = len([m for m in matches if any(
            re.search(pattern, m, re.IGNORECASE) 
            for pattern, severity in self.profanity_patterns.items() 
            if 0.5 <= severity < 0.8
        )])
        
        if severe_count > 0:
            return "severe"
        elif moderate_count > 2:
            return "moderate"
        else:
            return "mild" 