"""
Analysis Configuration

Central configuration manager for all analysis components.
Handles settings, preferences, and system-wide configuration.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json

from .user_preferences import UserPreferences
from .sensitivity_settings import SensitivitySettings
from .scoring_weights import ScoringWeights

logger = logging.getLogger(__name__)


@dataclass
class AnalysisConfig:
    """
    Central configuration manager for analysis system.
    
    Consolidates all configuration aspects including user preferences,
    sensitivity settings, scoring weights, and system settings.
    """
    user_preferences: UserPreferences = field(default_factory=UserPreferences)
    sensitivity_settings: SensitivitySettings = field(default_factory=SensitivitySettings)
    scoring_weights: ScoringWeights = field(default_factory=ScoringWeights)
    
    # Model settings
    default_model_device: str = "auto"
    content_moderation_model: str = "cardiffnlp/twitter-roberta-base-offensive"
    sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    
    # Processing settings
    max_chunk_size: int = 500
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    
    # Logging settings
    log_predictions: bool = False
    log_performance: bool = True
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AnalysisConfig':
        """
        Create AnalysisConfig from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            AnalysisConfig instance
        """
        try:
            # Extract nested configurations
            user_prefs_data = config_dict.get('user_preferences', {})
            sensitivity_data = config_dict.get('sensitivity_settings', {})
            scoring_data = config_dict.get('scoring_weights', {})
            
            # Create nested objects
            user_preferences = UserPreferences.from_dict(user_prefs_data)
            sensitivity_settings = SensitivitySettings.from_dict(sensitivity_data)
            scoring_weights = ScoringWeights.from_dict(scoring_data)
            
            # Create main config
            config = cls(
                user_preferences=user_preferences,
                sensitivity_settings=sensitivity_settings,
                scoring_weights=scoring_weights
            )
            
            # Set direct attributes
            for key, value in config_dict.items():
                if key not in ['user_preferences', 'sensitivity_settings', 'scoring_weights']:
                    if hasattr(config, key):
                        setattr(config, key, value)
            
            return config
            
        except Exception as e:
            logger.error(f"Error creating AnalysisConfig from dict: {str(e)}")
            return cls()  # Return default config
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert AnalysisConfig to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {
            'user_preferences': self.user_preferences.to_dict(),
            'sensitivity_settings': self.sensitivity_settings.to_dict(),
            'scoring_weights': self.scoring_weights.to_dict(),
            'default_model_device': self.default_model_device,
            'content_moderation_model': self.content_moderation_model,
            'sentiment_model': self.sentiment_model,
            'max_chunk_size': self.max_chunk_size,
            'enable_caching': self.enable_caching,
            'cache_ttl_seconds': self.cache_ttl_seconds,
            'log_predictions': self.log_predictions,
            'log_performance': self.log_performance
        }
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'AnalysisConfig':
        """
        Load configuration from JSON file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            AnalysisConfig instance
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Config file not found: {file_path}, using defaults")
                return cls()
            
            with open(path, 'r') as f:
                config_dict = json.load(f)
            
            return cls.from_dict(config_dict)
            
        except Exception as e:
            logger.error(f"Error loading config from file {file_path}: {str(e)}")
            return cls()
    
    def save_to_file(self, file_path: str) -> bool:
        """
        Save configuration to JSON file.
        
        Args:
            file_path: Path to save configuration file
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
            
            logger.info(f"Configuration saved to: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config to file {file_path}: {str(e)}")
            return False
    
    def update_user_preferences(self, **kwargs) -> None:
        """
        Update user preferences.
        
        Args:
            **kwargs: User preference updates
        """
        self.user_preferences.update(**kwargs)
    
    def update_sensitivity_settings(self, **kwargs) -> None:
        """
        Update sensitivity settings.
        
        Args:
            **kwargs: Sensitivity setting updates
        """
        self.sensitivity_settings.update(**kwargs)
    
    def update_scoring_weights(self, **kwargs) -> None:
        """
        Update scoring weights.
        
        Args:
            **kwargs: Scoring weight updates
        """
        self.scoring_weights.update(**kwargs)
    
    def get_model_config(self) -> Dict[str, Any]:
        """
        Get model-specific configuration.
        
        Returns:
            Model configuration dictionary
        """
        return {
            'device': self.default_model_device,
            'content_moderation_model': self.content_moderation_model,
            'sentiment_model': self.sentiment_model,
            'max_chunk_size': self.max_chunk_size
        }
    
    def get_processing_config(self) -> Dict[str, Any]:
        """
        Get processing-specific configuration.
        
        Returns:
            Processing configuration dictionary
        """
        return {
            'enable_caching': self.enable_caching,
            'cache_ttl_seconds': self.cache_ttl_seconds,
            'log_predictions': self.log_predictions,
            'log_performance': self.log_performance,
            'max_chunk_size': self.max_chunk_size
        }
    
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Validate chunk size
            if self.max_chunk_size <= 0:
                logger.error("max_chunk_size must be positive")
                return False
            
            # Validate cache TTL
            if self.cache_ttl_seconds <= 0:
                logger.error("cache_ttl_seconds must be positive")
                return False
            
            # Validate nested configurations
            if not self.user_preferences.validate():
                logger.error("Invalid user preferences")
                return False
            
            if not self.sensitivity_settings.validate():
                logger.error("Invalid sensitivity settings")
                return False
            
            if not self.scoring_weights.validate():
                logger.error("Invalid scoring weights")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating configuration: {str(e)}")
            return False 