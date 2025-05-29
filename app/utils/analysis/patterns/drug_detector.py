"""
Substance Detector

Handles detection of drug and alcohol references in text.
Extracted and refactored from original analysis utilities.
"""

import re
import logging
from typing import Dict, List, Any, Optional

from .base_detector import BasePatternDetector, DetectionResult

logger = logging.getLogger(__name__)


class SubstanceDetector(BasePatternDetector):
    """
    Detects references to drugs, alcohol, and substance abuse in text.
    
    Uses context-aware pattern matching to distinguish between problematic
    content and acceptable references (e.g., medical, educational).
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the substance detector.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Load substance patterns
        self._load_substance_patterns()
        
        # Acceptable context patterns (medical, educational, recovery)
        self.acceptable_contexts = self.config.get('acceptable_contexts', [
            r'\b(medical|medicine|prescription|doctor|treatment)\b',
            r'\b(recovery|rehab|rehabilitation|sober|sobriety)\b',
            r'\b(avoid|avoiding|quit|quitting|stop|stopping)\b',
            r'\b(addiction|addicted|problem|help|support)\b',
            r'\b(against|anti|oppose|opposed)\b'
        ])
        
        # Positive/negative context indicators
        self.negative_contexts = self.config.get('negative_contexts', [
            r'\b(love|loving|need|want|enjoy|party|fun)\b',
            r'\b(high|stoned|wasted|drunk|buzzed)\b',
            r'\b(more|another|pass|share)\b'
        ])
        
        logger.debug(f"SubstanceDetector initialized with {len(self.substance_patterns)} patterns")
    
    def detect(self, text: str) -> DetectionResult:
        """
        Detect substance references in the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            DetectionResult with substance findings
        """
        if not text or not self.is_enabled():
            return self._create_result(False, 0.0, [])
        
        try:
            matches = []
            total_confidence = 0.0
            context_analysis = {}
            
            for category, patterns in self.substance_patterns.items():
                category_matches = []
                
                for pattern, severity in patterns.items():
                    pattern_matches = self._find_pattern_matches(text, pattern)
                    if pattern_matches:
                        # Analyze context for each match
                        for match in pattern_matches:
                            context_score = self._analyze_context(text, match)
                            if context_score > 0:  # Only include concerning contexts
                                category_matches.append(match)
                                total_confidence += severity * context_score
                
                if category_matches:
                    matches.extend(category_matches)
                    context_analysis[category] = len(category_matches)
            
            # Calculate overall confidence
            confidence = min(total_confidence / 5.0, 1.0) if matches else 0.0
            
            # Determine subcategory
            subcategory = self._determine_subcategory(context_analysis)
            
            context_info = {
                'category_breakdown': context_analysis,
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
            logger.error(f"Error in substance detection: {e}", exc_info=True)
            return self._create_result(False, 0.0, [])
    
    def get_category_name(self) -> str:
        """Get the category name this detector handles."""
        return "substance_abuse"
    
    def _load_substance_patterns(self) -> None:
        """Load substance detection patterns by category."""
        # Alcohol patterns
        alcohol_patterns = {
            r'\b(beer|wine|vodka|whiskey|rum|gin|tequila)\b': 0.6,
            r'\b(drunk|drinking|drink|alcohol|booze)\b': 0.7,
            r'\b(bar|pub|club|party)\b': 0.3,
            r'\b(shot|shots|bottle|bottles)\b': 0.4
        }
        
        # Drug patterns
        drug_patterns = {
            r'\b(weed|marijuana|cannabis|pot|grass|herb)\b': 0.8,
            r'\b(cocaine|coke|crack|heroin|meth)\b': 0.9,
            r'\b(pills|drugs|dope|smoke|smoking)\b': 0.7,
            r'\b(high|stoned|blazed|lit|trippy)\b': 0.6
        }
        
        # Prescription drug abuse patterns
        prescription_patterns = {
            r'\b(xanax|adderall|oxy|percocet|vicodin)\b': 0.8,
            r'\b(poppin|popping|pill)\s*(pills?)\b': 0.7
        }
        
        # Adjust patterns based on sensitivity
        if self.sensitivity == 'low':
            # Only include high-severity patterns
            alcohol_patterns = {k: v for k, v in alcohol_patterns.items() if v >= 0.6}
            drug_patterns = {k: v for k, v in drug_patterns.items() if v >= 0.8}
        elif self.sensitivity == 'medium':
            # Include medium and high severity patterns
            alcohol_patterns = {k: v for k, v in alcohol_patterns.items() if v >= 0.4}
            drug_patterns = {k: v for k, v in drug_patterns.items() if v >= 0.6}
        
        self.substance_patterns = {
            'alcohol': alcohol_patterns,
            'drugs': drug_patterns,
            'prescription': prescription_patterns
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
        Analyze the context around a substance match.
        
        Args:
            text: Full text for context analysis
            match: The substance match to analyze
            
        Returns:
            Context score (0.0 = acceptable, 1.0 = concerning)
        """
        # Get context window around the match
        match_index = text.lower().find(match.lower())
        if match_index == -1:
            return 0.5  # Default moderate concern
        
        start = max(0, match_index - 100)
        end = min(len(text), match_index + len(match) + 100)
        context_window = text[start:end]
        
        # Check for acceptable contexts
        acceptable_score = 0
        for pattern in self.acceptable_contexts:
            if re.search(pattern, context_window, re.IGNORECASE):
                acceptable_score += 1
        
        # Check for negative contexts
        negative_score = 0
        for pattern in self.negative_contexts:
            if re.search(pattern, context_window, re.IGNORECASE):
                negative_score += 1
        
        # Calculate final context score
        if acceptable_score > 0:
            return max(0.0, 0.3 - (acceptable_score * 0.1))  # Reduce concern
        elif negative_score > 0:
            return min(1.0, 0.7 + (negative_score * 0.1))  # Increase concern
        else:
            return 0.5  # Neutral context
    
    def _determine_subcategory(self, context_analysis: Dict[str, int]) -> str:
        """
        Determine subcategory based on substance types found.
        
        Args:
            context_analysis: Breakdown of matches by category
            
        Returns:
            Subcategory string
        """
        if not context_analysis:
            return "none"
        
        # Prioritize by severity
        if context_analysis.get('drugs', 0) > 0:
            return "illegal_drugs"
        elif context_analysis.get('prescription', 0) > 0:
            return "prescription_abuse"
        elif context_analysis.get('alcohol', 0) > 2:
            return "alcohol_heavy"
        elif context_analysis.get('alcohol', 0) > 0:
            return "alcohol_mention"
        else:
            return "general" 