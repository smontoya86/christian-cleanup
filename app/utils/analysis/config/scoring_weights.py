"""
Scoring Weights

Manages scoring configuration, penalties, bonuses, and weight adjustments.
Controls how different analysis components contribute to final scores.
"""

import logging
from typing import Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScoringWeights:
    """
    Configuration for analysis scoring weights and penalties.
    
    Manages how different components (biblical themes, content flags,
    etc.) contribute to the final analysis score.
    """
    # Base scoring weights (0.0 to 1.0)
    biblical_themes_weight: float = 0.4
    content_appropriateness_weight: float = 0.4
    sentiment_weight: float = 0.2
    
    # Penalty weights for content flags
    profanity_penalty_weight: float = 15.0
    substance_penalty_weight: float = 20.0
    violence_penalty_weight: float = 18.0
    sexual_content_penalty_weight: float = 25.0
    general_offensive_penalty_weight: float = 10.0
    
    # Bonus weights for positive themes
    worship_bonus_weight: float = 15.0
    faith_bonus_weight: float = 12.0
    salvation_bonus_weight: float = 18.0
    love_bonus_weight: float = 10.0
    prayer_bonus_weight: float = 8.0
    hope_bonus_weight: float = 10.0
    service_bonus_weight: float = 8.0
    scripture_reference_bonus_weight: float = 12.0
    
    # Score scaling factors
    max_penalty_cap: float = 80.0  # Maximum total penalty
    max_bonus_cap: float = 40.0    # Maximum total bonus
    base_score: float = 50.0       # Starting score
    
    # Quality thresholds
    excellent_threshold: float = 85.0
    good_threshold: float = 70.0
    acceptable_threshold: float = 50.0
    
    def update(self, **kwargs) -> None:
        """
        Update scoring weights.
        
        Args:
            **kwargs: Weight updates
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                if isinstance(value, (int, float)):
                    # Validate weight ranges
                    if key.endswith('_weight') and 'penalty' not in key and 'bonus' not in key:
                        if not 0.0 <= value <= 1.0:
                            logger.warning(f"Weight {key} should be between 0.0 and 1.0, got {value}")
                    
                    setattr(self, key, float(value))
                    logger.debug(f"Updated scoring weight: {key} = {value}")
                else:
                    logger.warning(f"Invalid value type for {key}: {type(value)}")
            else:
                logger.warning(f"Unknown scoring weight: {key}")
    
    def get_content_penalty_weights(self) -> Dict[str, float]:
        """
        Get penalty weights for content flags.
        
        Returns:
            Dictionary mapping content types to penalty weights
        """
        return {
            'profanity': self.profanity_penalty_weight,
            'substance': self.substance_penalty_weight,
            'violence': self.violence_penalty_weight,
            'sexual': self.sexual_content_penalty_weight,
            'offensive': self.general_offensive_penalty_weight
        }
    
    def get_theme_bonus_weights(self) -> Dict[str, float]:
        """
        Get bonus weights for biblical themes.
        
        Returns:
            Dictionary mapping theme types to bonus weights
        """
        return {
            'worship': self.worship_bonus_weight,
            'faith': self.faith_bonus_weight,
            'salvation': self.salvation_bonus_weight,
            'love': self.love_bonus_weight,
            'prayer': self.prayer_bonus_weight,
            'hope': self.hope_bonus_weight,
            'service': self.service_bonus_weight,
            'scripture_references': self.scripture_reference_bonus_weight
        }
    
    def get_component_weights(self) -> Dict[str, float]:
        """
        Get weights for main analysis components.
        
        Returns:
            Dictionary mapping components to weights
        """
        return {
            'biblical_themes': self.biblical_themes_weight,
            'content_appropriateness': self.content_appropriateness_weight,
            'sentiment': self.sentiment_weight
        }
    
    def normalize_component_weights(self) -> None:
        """Normalize component weights to sum to 1.0."""
        total = (self.biblical_themes_weight + 
                self.content_appropriateness_weight + 
                self.sentiment_weight)
        
        if total > 0:
            self.biblical_themes_weight /= total
            self.content_appropriateness_weight /= total
            self.sentiment_weight /= total
            
            logger.info("Component weights normalized to sum to 1.0")
        else:
            logger.warning("Cannot normalize weights - total is zero")
    
    def get_penalty_for_content(self, content_type: str, score: float = 1.0) -> float:
        """
        Calculate penalty for specific content type.
        
        Args:
            content_type: Type of content detected
            score: Confidence score (0.0 to 1.0)
            
        Returns:
            Penalty value
        """
        penalty_weights = self.get_content_penalty_weights()
        base_penalty = penalty_weights.get(content_type, 0.0)
        
        # Scale penalty by confidence score
        return base_penalty * score
    
    def get_bonus_for_theme(self, theme_type: str, score: float = 1.0) -> float:
        """
        Calculate bonus for specific biblical theme.
        
        Args:
            theme_type: Type of theme detected
            score: Confidence score (0.0 to 1.0)
            
        Returns:
            Bonus value
        """
        bonus_weights = self.get_theme_bonus_weights()
        base_bonus = bonus_weights.get(theme_type, 0.0)
        
        # Scale bonus by confidence score
        return base_bonus * score
    
    def cap_penalty(self, total_penalty: float) -> float:
        """
        Apply penalty cap to total penalty.
        
        Args:
            total_penalty: Uncapped penalty value
            
        Returns:
            Capped penalty value
        """
        return min(total_penalty, self.max_penalty_cap)
    
    def cap_bonus(self, total_bonus: float) -> float:
        """
        Apply bonus cap to total bonus.
        
        Args:
            total_bonus: Uncapped bonus value
            
        Returns:
            Capped bonus value
        """
        return min(total_bonus, self.max_bonus_cap)
    
    def calculate_final_score(self, component_scores: Dict[str, float], 
                            penalties: float = 0.0, bonuses: float = 0.0) -> float:
        """
        Calculate final weighted score.
        
        Args:
            component_scores: Scores for each component
            penalties: Total penalties to apply
            bonuses: Total bonuses to apply
            
        Returns:
            Final weighted score (0-100)
        """
        # Get component weights
        weights = self.get_component_weights()
        
        # Calculate weighted component score
        weighted_score = 0.0
        for component, score in component_scores.items():
            weight = weights.get(component, 0.0)
            weighted_score += score * weight
        
        # Start with base score and add weighted components
        final_score = self.base_score + (weighted_score - 50.0)
        
        # Apply capped penalties and bonuses
        final_score -= self.cap_penalty(penalties)
        final_score += self.cap_bonus(bonuses)
        
        # Ensure score is within 0-100 range
        return max(0.0, min(100.0, final_score))
    
    def get_quality_level(self, score: float) -> str:
        """
        Get quality level based on score.
        
        Args:
            score: Analysis score (0-100)
            
        Returns:
            Quality level string
        """
        if score >= self.excellent_threshold:
            return "excellent"
        elif score >= self.good_threshold:
            return "good"
        elif score >= self.acceptable_threshold:
            return "acceptable"
        else:
            return "poor"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScoringWeights':
        """
        Create ScoringWeights from dictionary.
        
        Args:
            data: Weights data dictionary
            
        Returns:
            ScoringWeights instance
        """
        try:
            weights = cls()
            weights.update(**data)
            return weights
        except Exception as e:
            logger.error(f"Error creating ScoringWeights from dict: {str(e)}")
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ScoringWeights to dictionary.
        
        Returns:
            Weights dictionary
        """
        return {
            'biblical_themes_weight': self.biblical_themes_weight,
            'content_appropriateness_weight': self.content_appropriateness_weight,
            'sentiment_weight': self.sentiment_weight,
            'profanity_penalty_weight': self.profanity_penalty_weight,
            'substance_penalty_weight': self.substance_penalty_weight,
            'violence_penalty_weight': self.violence_penalty_weight,
            'sexual_content_penalty_weight': self.sexual_content_penalty_weight,
            'general_offensive_penalty_weight': self.general_offensive_penalty_weight,
            'worship_bonus_weight': self.worship_bonus_weight,
            'faith_bonus_weight': self.faith_bonus_weight,
            'salvation_bonus_weight': self.salvation_bonus_weight,
            'love_bonus_weight': self.love_bonus_weight,
            'prayer_bonus_weight': self.prayer_bonus_weight,
            'hope_bonus_weight': self.hope_bonus_weight,
            'service_bonus_weight': self.service_bonus_weight,
            'scripture_reference_bonus_weight': self.scripture_reference_bonus_weight,
            'max_penalty_cap': self.max_penalty_cap,
            'max_bonus_cap': self.max_bonus_cap,
            'base_score': self.base_score,
            'excellent_threshold': self.excellent_threshold,
            'good_threshold': self.good_threshold,
            'acceptable_threshold': self.acceptable_threshold
        }
    
    def validate(self) -> bool:
        """
        Validate scoring weights.
        
        Returns:
            True if weights are valid, False otherwise
        """
        try:
            # Validate component weights sum
            component_sum = (self.biblical_themes_weight + 
                           self.content_appropriateness_weight + 
                           self.sentiment_weight)
            
            if abs(component_sum - 1.0) > 0.1:  # Allow some tolerance
                logger.warning(f"Component weights sum to {component_sum}, should be close to 1.0")
            
            # Validate threshold ordering
            if not (0 <= self.acceptable_threshold <= self.good_threshold <= self.excellent_threshold <= 100):
                logger.error("Quality thresholds are not properly ordered")
                return False
            
            # Validate caps are positive
            if self.max_penalty_cap <= 0 or self.max_bonus_cap <= 0:
                logger.error("Penalty and bonus caps must be positive")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating scoring weights: {str(e)}")
            return False 