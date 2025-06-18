"""
Composite Scorer

Aggregates results from multiple scoring algorithms to produce final scores.
Provides different aggregation strategies and quality assessment.
"""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum

from .base_scorer import BaseScorer, ScoreResult, ScoreCategory
from .content_scorer import ContentScorer
from .biblical_scorer import BiblicalScorer
from .scoring_config import ScoringConfig

logger = logging.getLogger(__name__)


class AggregationStrategy(Enum):
    """Available score aggregation strategies."""
    WEIGHTED_AVERAGE = "weighted_average"
    MAX = "max"
    MIN = "min"
    PRODUCT = "product"


class CompositeScorer(BaseScorer):
    """
    Aggregates results from multiple scoring algorithms.
    
    Combines content appropriateness and biblical theme scores
    using configurable aggregation strategies.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the composite scorer.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        
        # Initialize scoring configuration
        self.scoring_config = ScoringConfig(config)
        
        # Initialize individual scorers
        self.content_scorer = None
        self.biblical_scorer = None
        self._initialize_scorers()
        
        # Aggregation configuration
        self.aggregation_strategy = AggregationStrategy(
            self.scoring_config.get_aggregation_strategy()
        )
        self.normalize_scores = self.scoring_config.composite_scorer_config.get('normalize_scores', True)
        self.apply_quality_bonuses = self.scoring_config.composite_scorer_config.get('apply_quality_bonuses', True)
        
        logger.debug(f"CompositeScorer initialized with {self.aggregation_strategy.value} strategy")
    
    def get_score_category(self) -> ScoreCategory:
        """Get the score category for composite scoring."""
        return ScoreCategory.OVERALL_QUALITY
    
    def calculate_score(self, text: str, context: Optional[Dict[str, Any]] = None) -> ScoreResult:
        """
        Calculate composite score from all enabled scorers.
        
        Args:
            text: Text to score
            context: Optional context information
            
        Returns:
            ScoreResult with aggregated score
        """
        if not text:
            return self._create_empty_result()
        
        try:
            # Collect scores from all enabled scorers
            individual_scores = self._collect_individual_scores(text, context)
            
            if not individual_scores:
                return self._create_no_scorers_result()
            
            # Aggregate scores using selected strategy
            aggregated_score = self._aggregate_scores(individual_scores)
            
            # Apply quality bonuses if enabled
            if self.apply_quality_bonuses:
                aggregated_score = self._apply_quality_bonuses(aggregated_score)
            
            # Calculate overall confidence
            confidence = self._calculate_overall_confidence(individual_scores)
            
            # Collect all penalties and bonuses
            all_penalties = []
            all_bonuses = []
            for score_result in individual_scores.values():
                all_penalties.extend(score_result.penalties)
                all_bonuses.extend(score_result.bonuses)
            
            # Generate explanation
            explanation = self._generate_explanation(aggregated_score, individual_scores)
            
            # Create detailed results
            details = {
                'aggregation_strategy': self.aggregation_strategy.value,
                'individual_scores': {
                    name: {
                        'score': result.score,
                        'confidence': result.confidence,
                        'category': result.category.value
                    }
                    for name, result in individual_scores.items()
                },
                'final_score': aggregated_score,
                'quality_level': self._determine_quality_level(aggregated_score)
            }
            
            return self.create_score_result(
                score=aggregated_score,
                confidence=confidence,
                details=details,
                penalties=all_penalties,
                bonuses=all_bonuses,
                explanation=explanation
            )
            
        except Exception as e:
            logger.error(f"Error calculating composite score: {e}", exc_info=True)
            return self._create_error_result(str(e))
    
    def _initialize_scorers(self) -> None:
        """Initialize individual scorer instances."""
        # Initialize content scorer if enabled
        if self.scoring_config.is_scorer_enabled('content'):
            content_config = self.scoring_config.get_content_scorer_config()
            self.content_scorer = ContentScorer(content_config)
        
        # Initialize biblical scorer if enabled
        if self.scoring_config.is_scorer_enabled('biblical'):
            biblical_config = self.scoring_config.get_biblical_scorer_config()
            self.biblical_scorer = BiblicalScorer(biblical_config)
    
    def _collect_individual_scores(self, text: str, context: Optional[Dict[str, Any]]) -> Dict[str, ScoreResult]:
        """
        Collect scores from all enabled individual scorers.
        
        Args:
            text: Text to score
            context: Optional context information
            
        Returns:
            Dictionary mapping scorer names to their results
        """
        scores = {}
        
        # Get content score
        if self.content_scorer:
            try:
                content_result = self.content_scorer.calculate_score(text, context)
                scores['content'] = content_result
            except Exception as e:
                logger.warning(f"Content scorer failed: {e}")
        
        # Get biblical score
        if self.biblical_scorer:
            try:
                biblical_result = self.biblical_scorer.calculate_score(text, context)
                scores['biblical'] = biblical_result
            except Exception as e:
                logger.warning(f"Biblical scorer failed: {e}")
        
        return scores
    
    def _aggregate_scores(self, individual_scores: Dict[str, ScoreResult]) -> float:
        """
        Aggregate individual scores using the selected strategy.
        
        Args:
            individual_scores: Dictionary of individual score results
            
        Returns:
            Aggregated score
        """
        if not individual_scores:
            return 0.0
        
        scores = [result.score for result in individual_scores.values()]
        weights = self.scoring_config.get_scorer_weights()
        
        if self.aggregation_strategy == AggregationStrategy.WEIGHTED_AVERAGE:
            return self._weighted_average(individual_scores, weights)
        elif self.aggregation_strategy == AggregationStrategy.MAX:
            return max(scores)
        elif self.aggregation_strategy == AggregationStrategy.MIN:
            return min(scores)
        elif self.aggregation_strategy == AggregationStrategy.PRODUCT:
            return self._product_aggregation(scores)
        else:
            # Default to weighted average
            return self._weighted_average(individual_scores, weights)
    
    def _weighted_average(self, individual_scores: Dict[str, ScoreResult], weights: Dict[str, float]) -> float:
        """Calculate weighted average of scores."""
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for name, result in individual_scores.items():
            weight = weights.get(name, 1.0)
            total_weighted_score += result.score * weight
            total_weight += weight
        
        return total_weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _product_aggregation(self, scores: List[float]) -> float:
        """Calculate product-based aggregation (geometric mean)."""
        if not scores:
            return 0.0
        
        # Normalize scores to 0-1 range for product calculation
        # This prevents overflow and ensures meaningful geometric mean calculation
        # Example: [80, 90] becomes [0.8, 0.9]
        normalized_scores = [score / 100.0 for score in scores]
        
        # Calculate geometric mean using the formula: (a₁ × a₂ × ... × aₙ)^(1/n)
        # Step 1: Calculate the product of all normalized scores
        product = 1.0
        for score in normalized_scores:
            product *= score  # Multiply each score into the running product
        
        # Step 2: Take the nth root where n = number of scores
        # This gives us the geometric mean, which is more conservative than arithmetic mean
        # and heavily penalizes low scores (if any score is 0, result is 0)
        geometric_mean = product ** (1.0 / len(scores))
        
        # Convert back to 0-100 range by scaling up
        # Example: 0.85 becomes 85.0
        return geometric_mean * 100.0
    
    def _apply_quality_bonuses(self, score: float) -> float:
        """
        Apply quality bonuses based on score thresholds.
        
        Args:
            score: Base aggregated score
            
        Returns:
            Score with quality bonuses applied
        """
        thresholds = self.scoring_config.get_score_thresholds()
        bonuses = self.scoring_config.composite_scorer_config.get('quality_bonuses', {})
        
        # Determine quality level and apply bonus
        if score >= thresholds.get('excellent', 90.0):
            bonus = bonuses.get('excellent', 2.0)
        elif score >= thresholds.get('good', 75.0):
            bonus = bonuses.get('good', 1.0)
        elif score >= thresholds.get('acceptable', 60.0):
            bonus = bonuses.get('acceptable', 0.0)
        else:
            bonus = bonuses.get('poor', -1.0)
        
        return min(100.0, max(0.0, score + bonus))
    
    def _calculate_overall_confidence(self, individual_scores: Dict[str, ScoreResult]) -> float:
        """
        Calculate overall confidence from individual scorer confidences.
        
        Args:
            individual_scores: Dictionary of individual score results
            
        Returns:
            Overall confidence score
        """
        if not individual_scores:
            return 0.0
        
        confidences = [result.confidence for result in individual_scores.values()]
        
        # Use weighted average of confidences
        weights = self.scoring_config.get_scorer_weights()
        total_weighted_confidence = 0.0
        total_weight = 0.0
        
        for name, result in individual_scores.items():
            weight = weights.get(name, 1.0)
            total_weighted_confidence += result.confidence * weight
            total_weight += weight
        
        return total_weighted_confidence / total_weight if total_weight > 0 else 0.0
    
    def _determine_quality_level(self, score: float) -> str:
        """
        Determine quality level based on score.
        
        Args:
            score: Final score
            
        Returns:
            Quality level string
        """
        thresholds = self.scoring_config.get_score_thresholds()
        
        if score >= thresholds.get('excellent', 90.0):
            return 'excellent'
        elif score >= thresholds.get('good', 75.0):
            return 'good'
        elif score >= thresholds.get('acceptable', 60.0):
            return 'acceptable'
        else:
            return 'poor'
    
    def _generate_explanation(self, final_score: float, individual_scores: Dict[str, ScoreResult]) -> str:
        """
        Generate human-readable explanation of the composite score.
        
        Args:
            final_score: Final aggregated score
            individual_scores: Individual scorer results
            
        Returns:
            Explanation string
        """
        quality_level = self._determine_quality_level(final_score)
        explanation_parts = [
            f"Overall quality score: {final_score:.1f}/100 ({quality_level})"
        ]
        
        # Add individual score summaries
        for name, result in individual_scores.items():
            explanation_parts.append(f"{name.title()}: {result.score:.1f}/100")
        
        explanation_parts.append(f"Aggregation: {self.aggregation_strategy.value}")
        
        return ". ".join(explanation_parts)
    
    def _create_empty_result(self) -> ScoreResult:
        """Create result for empty text."""
        return self.create_score_result(
            score=0.0,
            confidence=1.0,
            explanation="No text provided for composite scoring"
        )
    
    def _create_no_scorers_result(self) -> ScoreResult:
        """Create result when no scorers are enabled."""
        return self.create_score_result(
            score=50.0,
            confidence=0.0,
            explanation="No scoring algorithms enabled"
        )
    
    def _create_error_result(self, error_message: str) -> ScoreResult:
        """Create result for error cases."""
        return self.create_score_result(
            score=50.0,
            confidence=0.0,
            explanation=f"Error in composite scoring: {error_message}"
        ) 