"""
Biblical Scorer

Handles scoring based on biblical themes and Christian content.
Integrates with biblical analysis domain to calculate theme-based scores.
"""

import logging
from typing import Dict, List, Any, Optional

from .base_scorer import BaseScorer, ScoreResult, ScoreCategory
from ..biblical.theme_detector import BiblicalThemeDetector

logger = logging.getLogger(__name__)


class BiblicalScorer(BaseScorer):
    """
    Scores content based on biblical themes and Christian content.
    
    Uses biblical theme detection to calculate bonuses for
    positive Christian content and themes.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the biblical scorer.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Initialize biblical theme detector
        biblical_config = self.config.get('biblical_config', {})
        self.theme_detector = BiblicalThemeDetector(biblical_config)
        
        # Scoring configuration
        self.base_score = self.config.get('base_score', 50.0)
        self.theme_bonus_multiplier = self.config.get('theme_bonus_multiplier', 2.0)
        self.max_biblical_bonus = self.config.get('max_biblical_bonus', 25.0)
        self.min_themes_for_bonus = self.config.get('min_themes_for_bonus', 1)
        
        logger.debug("BiblicalScorer initialized with theme detection")
    
    def get_score_category(self) -> ScoreCategory:
        """Get the score category for biblical scoring."""
        return ScoreCategory.BIBLICAL_THEMES
    
    def calculate_score(self, text: str, context: Optional[Dict[str, Any]] = None) -> ScoreResult:
        """
        Calculate biblical themes score.
        
        Args:
            text: Text to score
            context: Optional context information
            
        Returns:
            ScoreResult with biblical themes score
        """
        if not text:
            return self._create_empty_result()
        
        try:
            # Detect biblical themes
            theme_matches = self.theme_detector.detect_themes(text)
            
            # Start with base score
            current_score = self.base_score
            bonuses = []
            penalties = []
            details = {
                'base_score': self.base_score,
                'themes_detected': len(theme_matches),
                'theme_details': []
            }
            
            # Apply bonuses for detected themes
            if len(theme_matches) >= self.min_themes_for_bonus:
                current_score, theme_bonuses = self._apply_theme_bonuses(
                    current_score, theme_matches
                )
                bonuses.extend(theme_bonuses)
            
            # Calculate additional biblical score bonus
            biblical_bonus = self.theme_detector.calculate_biblical_score_bonus(theme_matches)
            if biblical_bonus > 0:
                bonus = self.calculate_bonus(
                    current_score,
                    min(biblical_bonus * self.theme_bonus_multiplier, self.max_biblical_bonus),
                    f"Biblical content bonus: {biblical_bonus:.1f} points"
                )
                bonuses.append(bonus)
                current_score += bonus['amount']
            
            # Add theme details
            for theme_match in theme_matches:
                details['theme_details'].append({
                    'theme': theme_match.theme_name,
                    'confidence': theme_match.confidence,
                    'patterns_matched': len(theme_match.matched_patterns),
                    'scriptures_available': len(theme_match.supporting_scriptures)
                })
            
            # Calculate confidence based on theme detection quality
            confidence = self._calculate_confidence(theme_matches)
            
            # Generate explanation
            explanation = self._generate_explanation(current_score, theme_matches, bonuses)
            
            details.update({
                'final_score': current_score,
                'biblical_bonus_applied': biblical_bonus,
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
            logger.error(f"Error calculating biblical score: {e}", exc_info=True)
            return self._create_error_result(str(e))
    
    def _apply_theme_bonuses(self, score: float, theme_matches: List[Any]) -> tuple[float, List[Dict[str, Any]]]:
        """
        Apply bonuses based on detected biblical themes.
        
        Args:
            score: Current score
            theme_matches: Detected theme matches
            
        Returns:
            Tuple of (updated_score, bonuses_list)
        """
        bonuses = []
        current_score = score
        
        # Group themes by strength
        strong_themes = [t for t in theme_matches if t.confidence >= 0.7]
        medium_themes = [t for t in theme_matches if 0.4 <= t.confidence < 0.7]
        
        # Bonus for strong themes
        if strong_themes:
            bonus_amount = len(strong_themes) * 3.0
            bonus = self.calculate_bonus(
                current_score,
                bonus_amount,
                f"Strong biblical themes detected: {', '.join([t.theme_name for t in strong_themes[:3]])}"
            )
            bonuses.append(bonus)
            current_score += bonus['amount']
        
        # Bonus for medium themes
        if medium_themes:
            bonus_amount = len(medium_themes) * 1.5
            bonus = self.calculate_bonus(
                current_score,
                bonus_amount,
                f"Biblical themes detected: {', '.join([t.theme_name for t in medium_themes[:3]])}"
            )
            bonuses.append(bonus)
            current_score += bonus['amount']
        
        # Bonus for theme diversity
        if len(theme_matches) >= 3:
            bonus = self.calculate_bonus(
                current_score,
                2.0,
                f"Diverse biblical themes: {len(theme_matches)} different themes detected"
            )
            bonuses.append(bonus)
            current_score += bonus['amount']
        
        return current_score, bonuses
    
    def _calculate_confidence(self, theme_matches: List[Any]) -> float:
        """
        Calculate confidence based on theme detection quality.
        
        Args:
            theme_matches: Detected theme matches
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not theme_matches:
            return 0.8  # High confidence in absence of themes
        
        # Calculate average confidence of detected themes
        total_confidence = sum(match.confidence for match in theme_matches)
        avg_confidence = total_confidence / len(theme_matches)
        
        # Adjust based on number of themes (more themes = higher confidence)
        theme_count_factor = min(len(theme_matches) / 5.0, 1.0)
        
        final_confidence = (avg_confidence * 0.7) + (theme_count_factor * 0.3)
        
        return min(max(final_confidence, 0.5), 1.0)
    
    def _generate_explanation(self, score: float, theme_matches: List[Any], bonuses: List[Dict[str, Any]]) -> str:
        """
        Generate human-readable explanation of the biblical score.
        
        Args:
            score: Final score
            theme_matches: Detected themes
            bonuses: Applied bonuses
            
        Returns:
            Explanation string
        """
        explanation_parts = [f"Biblical themes score: {score:.1f}/100"]
        
        if theme_matches:
            theme_names = [match.theme_name.replace('_', ' ').title() for match in theme_matches[:3]]
            explanation_parts.append(f"Detected themes: {', '.join(theme_names)}")
            
            if len(theme_matches) > 3:
                explanation_parts.append(f"Plus {len(theme_matches) - 3} additional themes")
        else:
            explanation_parts.append("No biblical themes detected")
        
        if bonuses:
            total_bonus = sum(b['amount'] for b in bonuses)
            explanation_parts.append(f"Total biblical bonus: +{total_bonus:.1f} points")
        
        return ". ".join(explanation_parts)
    
    def get_theme_summary(self, theme_matches: List[Any]) -> Dict[str, Any]:
        """
        Get a summary of detected themes for external use.
        
        Args:
            theme_matches: Detected theme matches
            
        Returns:
            Theme summary dictionary
        """
        return self.theme_detector.get_theme_summary(theme_matches)
    
    def get_scripture_references(self, theme_matches: List[Any]) -> Dict[str, List[str]]:
        """
        Get scripture references for detected themes.
        
        Args:
            theme_matches: Detected theme matches
            
        Returns:
            Dictionary mapping themes to scripture references
        """
        references = {}
        
        for match in theme_matches:
            if match.supporting_scriptures:
                references[match.theme_name] = match.supporting_scriptures
        
        return references
    
    def _create_empty_result(self) -> ScoreResult:
        """Create result for empty text."""
        return self.create_score_result(
            score=self.base_score,
            confidence=1.0,
            explanation="No text provided for biblical scoring"
        )
    
    def _create_error_result(self, error_message: str) -> ScoreResult:
        """Create result for error cases."""
        return self.create_score_result(
            score=self.base_score,
            confidence=0.0,
            explanation=f"Error in biblical scoring: {error_message}"
        ) 