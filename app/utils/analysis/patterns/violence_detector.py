"""
Violence Detector

Handles detection of violent content and aggressive themes in text.
Extracted and refactored from original analysis utilities.
"""

import re
import logging
from typing import Dict, List, Any, Optional

from .base_detector import BasePatternDetector, DetectionResult

logger = logging.getLogger(__name__)


class ViolenceDetector(BasePatternDetector):
    """
    Detects violent content and aggressive themes in text.
    
    Distinguishes between different types of violence and considers context
    to avoid false positives in metaphorical or defensive contexts.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the violence detector.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Load violence patterns
        self._load_violence_patterns()
        
        # Acceptable contexts (defensive, metaphorical, spiritual warfare)
        self.acceptable_contexts = self.config.get('acceptable_contexts', [
            r'\b(defend|defense|protect|protection|guard)\b',
            r'\b(metaphor|symbolic|spiritual|battle|warfare)\b',
            r'\b(against|fight\s+against|stand\s+against)\b',
            r'\b(evil|sin|temptation|devil|satan)\b',
            r'\b(never|not|don\'t|won\'t|avoid)\b'
        ])
        
        # Concerning contexts (graphic, celebratory)
        self.concerning_contexts = self.config.get('concerning_contexts', [
            r'\b(love|enjoy|want|need|blood|gore)\b',
            r'\b(kill|murder|shoot|stab|beat)\b',
            r'\b(revenge|payback|hurt|pain)\b'
        ])
        
        logger.debug(f"ViolenceDetector initialized with {len(self.violence_patterns)} pattern categories")
    
    def detect(self, text: str) -> DetectionResult:
        """
        Detect violent content in the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            DetectionResult with violence findings
        """
        if not text or not self.is_enabled():
            return self._create_result(False, 0.0, [])
        
        try:
            matches = []
            total_confidence = 0.0
            category_analysis = {}
            
            for category, patterns in self.violence_patterns.items():
                category_matches = []
                
                for pattern, severity in patterns.items():
                    pattern_matches = self._find_pattern_matches(text, pattern)
                    if pattern_matches:
                        # Analyze context for each match
                        for match in pattern_matches:
                            context_score = self._analyze_context(text, match)
                            if context_score > 0.3:  # Only include concerning contexts
                                category_matches.append(match)
                                total_confidence += severity * context_score
                
                if category_matches:
                    matches.extend(category_matches)
                    category_analysis[category] = len(category_matches)
            
            # Calculate overall confidence
            confidence = min(total_confidence / 8.0, 1.0) if matches else 0.0
            
            # Determine subcategory
            subcategory = self._determine_subcategory(category_analysis)
            
            context_info = {
                'category_breakdown': category_analysis,
                'total_matches': len(matches),
                'sensitivity': self.sensitivity,
                'context_analyzed': True
            }
            
            return self._create_result(
                detected=len(matches) > 0,
                confidence=confidence,
                matches=matches,
                subcategory=subcategory,
                context=context_info
            )
            
        except Exception as e:
            logger.error(f"Error in violence detection: {e}", exc_info=True)
            return self._create_result(False, 0.0, [])
    
    def get_category_name(self) -> str:
        """Get the category name this detector handles."""
        return "violence"
    
    def _load_violence_patterns(self) -> None:
        """Load violence detection patterns by category."""
        # Physical violence patterns
        physical_violence = {
            r'\b(kill|murder|shoot|shot|gun|knife)\b': 0.9,
            r'\b(beat|punch|hit|strike|slam)\b': 0.7,
            r'\b(blood|bleed|bleeding|gore|wound)\b': 0.8,
            r'\b(fight|fighting|battle|war)\b': 0.5,
            r'\b(attack|assault|violence|violent)\b': 0.8
        }
        
        # Threatening language
        threatening_language = {
            r'\b(threat|threaten|intimidate|scare)\b': 0.7,
            r'\b(hurt|harm|damage|destroy)\b': 0.6,
            r'\b(revenge|payback|get\s+back)\b': 0.8,
            r'\b(die|death|dead|corpse)\b': 0.7
        }
        
        # Weapons references
        weapons = {
            r'\b(gun|rifle|pistol|weapon|blade)\b': 0.8,
            r'\b(bullet|bullets|ammo|ammunition)\b': 0.8,
            r'\b(sword|knife|dagger|axe)\b': 0.6,
            r'\b(bomb|explosive|grenade)\b': 0.9
        }
        
        # Aggressive behavior
        aggressive_behavior = {
            r'\b(rage|fury|anger|hate|hatred)\b': 0.5,
            r'\b(destroy|demolish|crush|smash)\b': 0.6,
            r'\b(dominate|conquer|defeat|crush)\b': 0.4,
            r'\b(aggressive|hostile|brutal)\b': 0.7
        }
        
        # Adjust patterns based on sensitivity
        if self.sensitivity == 'low':
            # Only include high-severity patterns
            physical_violence = {k: v for k, v in physical_violence.items() if v >= 0.8}
            threatening_language = {k: v for k, v in threatening_language.items() if v >= 0.7}
            weapons = {k: v for k, v in weapons.items() if v >= 0.8}
            aggressive_behavior = {k: v for k, v in aggressive_behavior.items() if v >= 0.7}
        elif self.sensitivity == 'medium':
            # Include medium and high severity patterns
            physical_violence = {k: v for k, v in physical_violence.items() if v >= 0.6}
            threatening_language = {k: v for k, v in threatening_language.items() if v >= 0.6}
            weapons = {k: v for k, v in weapons.items() if v >= 0.6}
            aggressive_behavior = {k: v for k, v in aggressive_behavior.items() if v >= 0.5}
        
        self.violence_patterns = {
            'physical_violence': physical_violence,
            'threatening': threatening_language,
            'weapons': weapons,
            'aggressive': aggressive_behavior
        }
    
    def _find_pattern_matches(self, text: str, pattern: str) -> List[str]:
        """Find all matches for a pattern in text."""
        try:
            matches = re.findall(pattern, text, re.IGNORECASE)
            return matches
        except re.error as e:
            logger.warning(f"Invalid regex pattern {pattern}: {e}")
            return []
    
    def _analyze_context(self, text: str, match: str) -> float:
        """
        Analyze the context around a violence match.
        
        Args:
            text: Full text for context analysis
            match: The violence match to analyze
            
        Returns:
            Context score (0.0 = acceptable, 1.0 = very concerning)
        """
        # Get context window around the match
        match_index = text.lower().find(match.lower())
        if match_index == -1:
            return 0.6  # Default moderate concern
        
        start = max(0, match_index - 100)
        end = min(len(text), match_index + len(match) + 100)
        context_window = text[start:end]
        
        # Check for acceptable contexts
        acceptable_score = 0
        for pattern in self.acceptable_contexts:
            if re.search(pattern, context_window, re.IGNORECASE):
                acceptable_score += 1
        
        # Check for concerning contexts
        concerning_score = 0
        for pattern in self.concerning_contexts:
            if re.search(pattern, context_window, re.IGNORECASE):
                concerning_score += 1
        
        # Calculate final context score
        if acceptable_score > 0:
            # Reduce concern for defensive/metaphorical contexts
            return max(0.0, 0.4 - (acceptable_score * 0.15))
        elif concerning_score > 0:
            # Increase concern for graphic/celebratory contexts
            return min(1.0, 0.8 + (concerning_score * 0.1))
        else:
            return 0.6  # Neutral context - still concerning
    
    def _determine_subcategory(self, category_analysis: Dict[str, int]) -> str:
        """
        Determine subcategory based on violence types found.
        
        Args:
            category_analysis: Breakdown of matches by category
            
        Returns:
            Subcategory string
        """
        if not category_analysis:
            return "none"
        
        # Prioritize by severity
        if category_analysis.get('physical_violence', 0) > 0:
            return "physical_violence"
        elif category_analysis.get('weapons', 0) > 0:
            return "weapons_references"
        elif category_analysis.get('threatening', 0) > 0:
            return "threatening_language"
        elif category_analysis.get('aggressive', 0) > 1:
            return "aggressive_behavior"
        else:
            return "general_violence" 