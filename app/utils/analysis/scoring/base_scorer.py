"""
Base Scorer

Provides the abstract interface that all scoring classes must implement.
This ensures consistency across different scoring algorithms.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ScoreCategory(Enum):
    """Categories for different types of scores."""
    CONTENT_APPROPRIATENESS = "content_appropriateness"
    BIBLICAL_THEMES = "biblical_themes"
    OVERALL_QUALITY = "overall_quality"
    LYRICAL_CONTENT = "lyrical_content"


@dataclass
class ScoreResult:
    """
    Represents the result of a scoring operation.
    """
    category: ScoreCategory
    score: float  # 0.0 to 100.0
    confidence: float  # 0.0 to 1.0
    details: Dict[str, Any]
    penalties: List[Dict[str, Any]]
    bonuses: List[Dict[str, Any]]
    explanation: str


class BaseScorer(ABC):
    """
    Abstract base class for all scoring implementations.
    
    This interface ensures all scorers provide consistent methods
    and return standardized score results.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the scorer with optional configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.weight = self.config.get('weight', 1.0)
        self.enabled = self.config.get('enabled', True)
    
    @abstractmethod
    def calculate_score(self, text: str, context: Optional[Dict[str, Any]] = None) -> ScoreResult:
        """
        Calculate a score for the given text.
        
        Args:
            text: Text to score
            context: Optional context information
            
        Returns:
            ScoreResult with calculated score and details
        """
        pass
    
    @abstractmethod
    def get_score_category(self) -> ScoreCategory:
        """
        Get the category this scorer handles.
        
        Returns:
            ScoreCategory enum value
        """
        pass
    
    def is_enabled(self) -> bool:
        """
        Check if this scorer is enabled.
        
        Returns:
            True if scorer is enabled
        """
        return self.enabled
    
    def get_weight(self) -> float:
        """
        Get the weight for this scorer.
        
        Returns:
            Weight value for score aggregation
        """
        return self.weight
    
    def validate_score(self, score: float) -> float:
        """
        Validate and clamp score to valid range.
        
        Args:
            score: Raw score value
            
        Returns:
            Validated score (0.0 to 100.0)
        """
        return max(0.0, min(100.0, score))
    
    def create_score_result(
        self,
        score: float,
        confidence: float = 1.0,
        details: Optional[Dict[str, Any]] = None,
        penalties: Optional[List[Dict[str, Any]]] = None,
        bonuses: Optional[List[Dict[str, Any]]] = None,
        explanation: str = ""
    ) -> ScoreResult:
        """
        Create a standardized ScoreResult.
        
        Args:
            score: Calculated score
            confidence: Confidence in the score
            details: Additional scoring details
            penalties: List of penalties applied
            bonuses: List of bonuses applied
            explanation: Human-readable explanation
            
        Returns:
            ScoreResult instance
        """
        return ScoreResult(
            category=self.get_score_category(),
            score=self.validate_score(score),
            confidence=max(0.0, min(1.0, confidence)),
            details=details or {},
            penalties=penalties or [],
            bonuses=bonuses or [],
            explanation=explanation
        )
    
    def calculate_penalty(self, base_score: float, penalty_factor: float, reason: str) -> Dict[str, Any]:
        """
        Calculate a penalty and return penalty information.
        
        Args:
            base_score: Original score before penalty
            penalty_factor: Factor to apply (0.0 to 1.0)
            reason: Reason for the penalty
            
        Returns:
            Penalty information dictionary
        """
        penalty_amount = base_score * penalty_factor
        
        return {
            'type': 'penalty',
            'amount': penalty_amount,
            'factor': penalty_factor,
            'reason': reason,
            'applied_to_score': base_score
        }
    
    def calculate_bonus(self, base_score: float, bonus_amount: float, reason: str) -> Dict[str, Any]:
        """
        Calculate a bonus and return bonus information.
        
        Args:
            base_score: Original score before bonus
            bonus_amount: Amount to add
            reason: Reason for the bonus
            
        Returns:
            Bonus information dictionary
        """
        return {
            'type': 'bonus',
            'amount': bonus_amount,
            'reason': reason,
            'applied_to_score': base_score
        }
    
    def get_scorer_info(self) -> Dict[str, Any]:
        """
        Get information about this scorer.
        
        Returns:
            Dictionary with scorer metadata
        """
        return {
            'name': self.__class__.__name__,
            'category': self.get_score_category().value,
            'weight': self.weight,
            'enabled': self.enabled,
            'config': self.config
        } 