"""
Content Scorer

Handles scoring based on content appropriateness and pattern detection.
Integrates with pattern detection domain to calculate content scores.
"""

import logging
from typing import Dict, List, Any, Optional

from .base_scorer import BaseScorer, ScoreResult, ScoreCategory
from ..patterns.pattern_registry import PatternRegistry

logger = logging.getLogger(__name__)


class ContentScorer(BaseScorer):
    """
    Scores content based on appropriateness and detected patterns.
    
    Uses pattern detection results to calculate penalties for
    inappropriate content and bonuses for positive content.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the content scorer.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Initialize pattern registry
        pattern_config = self.config.get('pattern_config', {})
        self.pattern_registry = PatternRegistry(pattern_config)
        
        # Scoring configuration
        self.base_score = self.config.get('base_score', 85.0)
        self.profanity_penalty = self.config.get('profanity_penalty', 0.3)
        self.violence_penalty = self.config.get('violence_penalty', 0.25)
        self.substance_penalty = self.config.get('substance_penalty', 0.2)
        
        logger.debug("ContentScorer initialized with pattern detection")
    
    def get_score_category(self) -> ScoreCategory:
        """Get the score category for content scoring."""
        return ScoreCategory.CONTENT_APPROPRIATENESS
    
    def calculate_score(self, text: str, context: Optional[Dict[str, Any]] = None) -> ScoreResult:
        """
        Calculate content appropriateness score.
        
        Args:
            text: Text to score
            context: Optional context information
            
        Returns:
            ScoreResult with content appropriateness score
        """
        if not text:
            return self._create_empty_result()
        
        try:
            # Run pattern detection
            detection_results = self.pattern_registry.detect_all_patterns(text)
            
            # Start with base score
            current_score = self.base_score
            penalties = []
            bonuses = []
            details = {
                'base_score': self.base_score,
                'detection_results': detection_results
            }
            
            # Apply penalties for inappropriate content
            current_score, content_penalties = self._apply_content_penalties(
                current_score, detection_results
            )
            penalties.extend(content_penalties)
            
            # Apply bonuses for positive indicators
            current_score, content_bonuses = self._apply_content_bonuses(
                current_score, detection_results, text
            )
            bonuses.extend(content_bonuses)
            
            # Calculate confidence based on detection quality
            confidence = self._calculate_confidence(detection_results)
            
            # Generate explanation
            explanation = self._generate_explanation(current_score, penalties, bonuses)
            
            details.update({
                'final_score': current_score,
                'penalties_applied': len(penalties),
                'bonuses_applied': len(bonuses)
            })
            
            return self.create_score_result(
                score=current_score,
                confidence=confidence,
                details=details,
                penalties=penalties,
                bonuses=bonuses,
                explanation=explanation
            )
            
        except Exception as e:
            logger.error(f"Error calculating content score: {e}", exc_info=True)
            return self._create_error_result(str(e))
    
    def _apply_content_penalties(self, score: float, detection_results: Dict[str, Any]) -> tuple[float, List[Dict[str, Any]]]:
        """
        Apply penalties based on detected inappropriate content.
        
        Args:
            score: Current score
            detection_results: Pattern detection results
            
        Returns:
            Tuple of (updated_score, penalties_list)
        """
        penalties = []
        current_score = score
        
        # Check profanity detection
        profanity_result = detection_results.get('profanity')
        if profanity_result and profanity_result.detected:
            penalty = self.calculate_penalty(
                current_score, 
                self.profanity_penalty,
                f"Profanity detected: {len(profanity_result.matches)} instances"
            )
            penalties.append(penalty)
            current_score -= penalty['amount']
        
        # Check violence detection
        violence_result = detection_results.get('violence')
        if violence_result and violence_result.detected:
            penalty = self.calculate_penalty(
                current_score,
                self.violence_penalty,
                f"Violent content detected: {len(violence_result.matches)} instances"
            )
            penalties.append(penalty)
            current_score -= penalty['amount']
        
        # Check substance detection
        substance_result = detection_results.get('substance')
        if substance_result and substance_result.detected:
            penalty = self.calculate_penalty(
                current_score,
                self.substance_penalty,
                f"Substance references detected: {len(substance_result.matches)} instances"
            )
            penalties.append(penalty)
            current_score -= penalty['amount']
        
        return current_score, penalties
    
    def _apply_content_bonuses(self, score: float, detection_results: Dict[str, Any], text: str) -> tuple[float, List[Dict[str, Any]]]:
        """
        Apply bonuses for positive content indicators.
        
        Args:
            score: Current score
            detection_results: Pattern detection results
            text: Original text for additional analysis
            
        Returns:
            Tuple of (updated_score, bonuses_list)
        """
        bonuses = []
        current_score = score
        
        # Bonus for clean content (no inappropriate patterns detected)
        has_inappropriate = any(
            result.detected for result in detection_results.values()
            if hasattr(result, 'detected')
        )
        
        if not has_inappropriate:
            bonus = self.calculate_bonus(
                current_score,
                5.0,
                "Clean content with no inappropriate patterns detected"
            )
            bonuses.append(bonus)
            current_score += bonus['amount']
        
        # Bonus for positive language patterns
        positive_patterns = self._detect_positive_patterns(text)
        if positive_patterns:
            bonus = self.calculate_bonus(
                current_score,
                min(len(positive_patterns) * 1.0, 3.0),
                f"Positive language patterns detected: {', '.join(positive_patterns[:3])}"
            )
            bonuses.append(bonus)
            current_score += bonus['amount']
        
        return current_score, bonuses
    
    def _detect_positive_patterns(self, text: str) -> List[str]:
        """
        Detect positive language patterns in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected positive patterns
        """
        positive_words = [
            'love', 'hope', 'peace', 'joy', 'faith', 'trust', 'believe',
            'inspire', 'encourage', 'uplift', 'comfort', 'heal', 'bless',
            'grateful', 'thankful', 'amazing', 'wonderful', 'beautiful'
        ]
        
        detected = []
        text_lower = text.lower()
        
        for word in positive_words:
            if word in text_lower:
                detected.append(word)
        
        return detected
    
    def _calculate_confidence(self, detection_results: Dict[str, Any]) -> float:
        """
        Calculate confidence based on detection quality.
        
        Args:
            detection_results: Pattern detection results
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not detection_results:
            return 0.5  # Medium confidence for no detection
        
        # Higher confidence when patterns are clearly detected or clearly absent
        total_confidence = 0.0
        result_count = 0
        
        for result in detection_results.values():
            if hasattr(result, 'confidence'):
                total_confidence += result.confidence
                result_count += 1
        
        if result_count == 0:
            return 0.7  # Good confidence for successful detection run
        
        avg_confidence = total_confidence / result_count
        return min(max(avg_confidence, 0.6), 1.0)  # Ensure reasonable range
    
    def _generate_explanation(self, score: float, penalties: List[Dict[str, Any]], bonuses: List[Dict[str, Any]]) -> str:
        """
        Generate human-readable explanation of the score.
        
        Args:
            score: Final score
            penalties: Applied penalties
            bonuses: Applied bonuses
            
        Returns:
            Explanation string
        """
        explanation_parts = [f"Content appropriateness score: {score:.1f}/100"]
        
        if penalties:
            penalty_reasons = [p['reason'] for p in penalties]
            explanation_parts.append(f"Penalties applied: {'; '.join(penalty_reasons)}")
        
        if bonuses:
            bonus_reasons = [b['reason'] for b in bonuses]
            explanation_parts.append(f"Bonuses applied: {'; '.join(bonus_reasons)}")
        
        if not penalties and not bonuses:
            explanation_parts.append("No significant content issues detected")
        
        return ". ".join(explanation_parts)
    
    def _create_empty_result(self) -> ScoreResult:
        """Create result for empty text."""
        return self.create_score_result(
            score=0.0,
            confidence=1.0,
            explanation="No text provided for content scoring"
        )
    
    def _create_error_result(self, error_message: str) -> ScoreResult:
        """Create result for error cases."""
        return self.create_score_result(
            score=50.0,  # Neutral score for errors
            confidence=0.0,
            explanation=f"Error in content scoring: {error_message}"
        ) 