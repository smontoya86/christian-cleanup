"""
Scoring Configuration

Centralized configuration for all scoring algorithms and parameters.
Provides default settings and validation for scoring components.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ScorerConfig:
    """Configuration for individual scorer components."""
    enabled: bool = True
    weight: float = 1.0
    config: Dict[str, Any] = field(default_factory=dict)


class ScoringConfig:
    """
    Centralized configuration for all scoring algorithms.
    
    Manages settings for content scoring, biblical scoring, and
    composite scoring strategies.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize scoring configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Load default configurations
        self._load_default_configs()
        
        # Override with provided config
        if config:
            self._apply_config_overrides(config)
        
        logger.debug("ScoringConfig initialized with all scorer configurations")
    
    def get_content_scorer_config(self) -> Dict[str, Any]:
        """
        Get configuration for content scorer.
        
        Returns:
            Content scorer configuration dictionary
        """
        return self.content_scorer_config
    
    def get_biblical_scorer_config(self) -> Dict[str, Any]:
        """
        Get configuration for biblical scorer.
        
        Returns:
            Biblical scorer configuration dictionary
        """
        return self.biblical_scorer_config
    
    def get_composite_scorer_config(self) -> Dict[str, Any]:
        """
        Get configuration for composite scorer.
        
        Returns:
            Composite scorer configuration dictionary
        """
        return self.composite_scorer_config
    
    def get_scorer_weights(self) -> Dict[str, float]:
        """
        Get weights for all scorers.
        
        Returns:
            Dictionary mapping scorer names to weights
        """
        return {
            'content': self.content_scorer_config.get('weight', 1.0),
            'biblical': self.biblical_scorer_config.get('weight', 1.0)
        }
    
    def is_scorer_enabled(self, scorer_name: str) -> bool:
        """
        Check if a specific scorer is enabled.
        
        Args:
            scorer_name: Name of the scorer ('content' or 'biblical')
            
        Returns:
            True if scorer is enabled
        """
        config_map = {
            'content': self.content_scorer_config,
            'biblical': self.biblical_scorer_config
        }
        
        scorer_config = config_map.get(scorer_name, {})
        return scorer_config.get('enabled', True)
    
    def get_aggregation_strategy(self) -> str:
        """
        Get the score aggregation strategy.
        
        Returns:
            Aggregation strategy name
        """
        return self.composite_scorer_config.get('aggregation_strategy', 'weighted_average')
    
    def get_score_thresholds(self) -> Dict[str, float]:
        """
        Get score thresholds for different quality levels.
        
        Returns:
            Dictionary mapping quality levels to score thresholds
        """
        return self.composite_scorer_config.get('score_thresholds', {
            'excellent': 90.0,
            'good': 75.0,
            'acceptable': 60.0,
            'poor': 40.0
        })
    
    def validate_config(self) -> List[str]:
        """
        Validate the current configuration.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate weights
        for scorer_name, config in [
            ('content', self.content_scorer_config),
            ('biblical', self.biblical_scorer_config)
        ]:
            weight = config.get('weight', 1.0)
            if not isinstance(weight, (int, float)) or weight < 0:
                errors.append(f"{scorer_name} scorer weight must be non-negative number")
        
        # Validate aggregation strategy
        valid_strategies = ['weighted_average', 'max', 'min', 'product']
        strategy = self.get_aggregation_strategy()
        if strategy not in valid_strategies:
            errors.append(f"Invalid aggregation strategy: {strategy}")
        
        # Validate thresholds
        thresholds = self.get_score_thresholds()
        threshold_values = list(thresholds.values())
        if threshold_values != sorted(threshold_values, reverse=True):
            errors.append("Score thresholds must be in descending order")
        
        return errors
    
    def _load_default_configs(self) -> None:
        """Load default configurations for all scorers."""
        
        # Content scorer defaults
        self.content_scorer_config = {
            'enabled': True,
            'weight': 1.0,
            'base_score': 85.0,
            'profanity_penalty': 0.3,
            'violence_penalty': 0.25,
            'substance_penalty': 0.2,
            'pattern_config': {
                'sensitivity': 'medium'
            }
        }
        
        # Biblical scorer defaults
        self.biblical_scorer_config = {
            'enabled': True,
            'weight': 1.0,
            'base_score': 50.0,
            'theme_bonus_multiplier': 2.0,
            'max_biblical_bonus': 25.0,
            'min_themes_for_bonus': 1,
            'biblical_config': {
                'min_confidence_threshold': 0.3,
                'include_scripture_refs': True,
                'weight_multiplier': 1.0
            }
        }
        
        # Composite scorer defaults
        self.composite_scorer_config = {
            'aggregation_strategy': 'weighted_average',
            'normalize_scores': True,
            'apply_quality_bonuses': True,
            'score_thresholds': {
                'excellent': 90.0,
                'good': 75.0,
                'acceptable': 60.0,
                'poor': 40.0
            },
            'quality_bonuses': {
                'excellent': 2.0,
                'good': 1.0,
                'acceptable': 0.0,
                'poor': -1.0
            }
        }
    
    def _apply_config_overrides(self, config: Dict[str, Any]) -> None:
        """
        Apply configuration overrides.
        
        Args:
            config: Configuration overrides to apply
        """
        # Override content scorer config
        if 'content_scorer' in config:
            self._deep_update(self.content_scorer_config, config['content_scorer'])
        
        # Override biblical scorer config
        if 'biblical_scorer' in config:
            self._deep_update(self.biblical_scorer_config, config['biblical_scorer'])
        
        # Override composite scorer config
        if 'composite_scorer' in config:
            self._deep_update(self.composite_scorer_config, config['composite_scorer'])
        
        # Apply global overrides
        for key, value in config.items():
            if key not in ['content_scorer', 'biblical_scorer', 'composite_scorer']:
                # Apply to all scorer configs if applicable
                if key in ['enabled', 'weight']:
                    self.content_scorer_config[key] = value
                    self.biblical_scorer_config[key] = value
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Deep update target dictionary with source values.
        
        Args:
            target: Target dictionary to update
            source: Source dictionary with new values
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current configuration.
        
        Returns:
            Configuration summary dictionary
        """
        return {
            'content_scorer': {
                'enabled': self.content_scorer_config['enabled'],
                'weight': self.content_scorer_config['weight'],
                'base_score': self.content_scorer_config['base_score']
            },
            'biblical_scorer': {
                'enabled': self.biblical_scorer_config['enabled'],
                'weight': self.biblical_scorer_config['weight'],
                'base_score': self.biblical_scorer_config['base_score']
            },
            'composite_scorer': {
                'strategy': self.composite_scorer_config['aggregation_strategy'],
                'normalize_scores': self.composite_scorer_config['normalize_scores']
            },
            'validation_errors': self.validate_config()
        } 