"""
Sensitivity Settings

Manages content detection sensitivity thresholds and pattern matching.
Configures how strictly different types of content are detected.
"""

import logging
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SensitivityLevel(Enum):
    """Content detection sensitivity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SensitivitySettings:
    """
    Configuration for content detection sensitivity.
    
    Manages thresholds and settings for different types
    of content detection (profanity, substance, violence, etc.).
    """
    # Global sensitivity level
    global_sensitivity: SensitivityLevel = SensitivityLevel.MEDIUM
    
    # Individual detection thresholds (0.0 to 1.0)
    profanity_threshold: float = 0.5
    substance_threshold: float = 0.5
    violence_threshold: float = 0.5
    sexual_content_threshold: float = 0.5
    general_offensive_threshold: float = 0.4
    
    # Pattern detection settings
    enable_context_filtering: bool = True
    enable_metaphor_detection: bool = True
    strict_biblical_context: bool = False
    
    # AI model thresholds
    content_moderation_threshold: float = 0.6
    sentiment_threshold: float = 0.5
    
    def update(self, **kwargs) -> None:
        """
        Update sensitivity settings.
        
        Args:
            **kwargs: Setting updates
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                # Handle enum conversions
                if key == 'global_sensitivity' and isinstance(value, str):
                    try:
                        value = SensitivityLevel(value.lower())
                    except ValueError:
                        logger.warning(f"Invalid sensitivity level: {value}, keeping current")
                        continue
                
                # Validate threshold values
                if key.endswith('_threshold') and isinstance(value, (int, float)):
                    if not 0.0 <= value <= 1.0:
                        logger.warning(f"Threshold {key} must be between 0.0 and 1.0, got {value}")
                        continue
                
                setattr(self, key, value)
                logger.debug(f"Updated sensitivity setting: {key} = {value}")
            else:
                logger.warning(f"Unknown sensitivity setting: {key}")
    
    def get_threshold(self, content_type: str) -> float:
        """
        Get threshold for specific content type.
        
        Args:
            content_type: Type of content
            
        Returns:
            Threshold value (0.0 to 1.0)
        """
        threshold_mapping = {
            'profanity': self.profanity_threshold,
            'substance': self.substance_threshold,
            'violence': self.violence_threshold,
            'sexual': self.sexual_content_threshold,
            'offensive': self.general_offensive_threshold,
            'content_moderation': self.content_moderation_threshold,
            'sentiment': self.sentiment_threshold
        }
        
        return threshold_mapping.get(content_type, 0.5)
    
    def get_all_thresholds(self) -> Dict[str, float]:
        """
        Get all content detection thresholds.
        
        Returns:
            Dictionary mapping content types to thresholds
        """
        return {
            'profanity': self.profanity_threshold,
            'substance': self.substance_threshold,
            'violence': self.violence_threshold,
            'sexual': self.sexual_content_threshold,
            'offensive': self.general_offensive_threshold,
            'content_moderation': self.content_moderation_threshold,
            'sentiment': self.sentiment_threshold
        }
    
    def apply_global_sensitivity(self) -> None:
        """Apply global sensitivity level to all thresholds."""
        if self.global_sensitivity == SensitivityLevel.LOW:
            # Higher thresholds = less sensitive
            self.profanity_threshold = 0.8
            self.substance_threshold = 0.8
            self.violence_threshold = 0.8
            self.sexual_content_threshold = 0.8
            self.general_offensive_threshold = 0.7
            self.content_moderation_threshold = 0.8
            
        elif self.global_sensitivity == SensitivityLevel.MEDIUM:
            # Moderate thresholds
            self.profanity_threshold = 0.5
            self.substance_threshold = 0.5
            self.violence_threshold = 0.5
            self.sexual_content_threshold = 0.5
            self.general_offensive_threshold = 0.4
            self.content_moderation_threshold = 0.6
            
        elif self.global_sensitivity == SensitivityLevel.HIGH:
            # Lower thresholds = more sensitive
            self.profanity_threshold = 0.3
            self.substance_threshold = 0.3
            self.violence_threshold = 0.3
            self.sexual_content_threshold = 0.3
            self.general_offensive_threshold = 0.2
            self.content_moderation_threshold = 0.4
        
        logger.info(f"Applied global sensitivity level: {self.global_sensitivity.value}")
    
    def get_pattern_settings(self) -> Dict[str, Any]:
        """
        Get pattern detection settings.
        
        Returns:
            Dictionary of pattern detection configurations
        """
        return {
            'enable_context_filtering': self.enable_context_filtering,
            'enable_metaphor_detection': self.enable_metaphor_detection,
            'strict_biblical_context': self.strict_biblical_context,
            'global_sensitivity': self.global_sensitivity.value
        }
    
    def is_high_sensitivity(self) -> bool:
        """
        Check if operating in high sensitivity mode.
        
        Returns:
            True if high sensitivity, False otherwise
        """
        return self.global_sensitivity == SensitivityLevel.HIGH
    
    def is_low_sensitivity(self) -> bool:
        """
        Check if operating in low sensitivity mode.
        
        Returns:
            True if low sensitivity, False otherwise
        """
        return self.global_sensitivity == SensitivityLevel.LOW
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SensitivitySettings':
        """
        Create SensitivitySettings from dictionary.
        
        Args:
            data: Settings data dictionary
            
        Returns:
            SensitivitySettings instance
        """
        try:
            settings = cls()
            settings.update(**data)
            return settings
        except Exception as e:
            logger.error(f"Error creating SensitivitySettings from dict: {str(e)}")
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert SensitivitySettings to dictionary.
        
        Returns:
            Settings dictionary
        """
        return {
            'global_sensitivity': self.global_sensitivity.value,
            'profanity_threshold': self.profanity_threshold,
            'substance_threshold': self.substance_threshold,
            'violence_threshold': self.violence_threshold,
            'sexual_content_threshold': self.sexual_content_threshold,
            'general_offensive_threshold': self.general_offensive_threshold,
            'enable_context_filtering': self.enable_context_filtering,
            'enable_metaphor_detection': self.enable_metaphor_detection,
            'strict_biblical_context': self.strict_biblical_context,
            'content_moderation_threshold': self.content_moderation_threshold,
            'sentiment_threshold': self.sentiment_threshold
        }
    
    def validate(self) -> bool:
        """
        Validate sensitivity settings.
        
        Returns:
            True if settings are valid, False otherwise
        """
        try:
            # Validate all threshold values
            thresholds = [
                self.profanity_threshold,
                self.substance_threshold,
                self.violence_threshold,
                self.sexual_content_threshold,
                self.general_offensive_threshold,
                self.content_moderation_threshold,
                self.sentiment_threshold
            ]
            
            for threshold in thresholds:
                if not 0.0 <= threshold <= 1.0:
                    logger.error(f"Invalid threshold value: {threshold}, must be between 0.0 and 1.0")
                    return False
            
            # Validate enum values
            if not isinstance(self.global_sensitivity, SensitivityLevel):
                logger.error("Invalid global sensitivity level")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating sensitivity settings: {str(e)}")
            return False 