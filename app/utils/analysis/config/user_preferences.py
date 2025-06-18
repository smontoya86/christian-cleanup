"""
User Preferences

Manages user-specific settings and preferences for analysis.
Handles denominational preferences, content filtering levels, and personalization.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Denomination(Enum):
    """Supported denominational preferences."""
    CATHOLIC = "catholic"
    PROTESTANT = "protestant"
    EVANGELICAL = "evangelical"
    PENTECOSTAL = "pentecostal"
    ORTHODOX = "orthodox"
    GENERAL = "general"


class ContentFilterLevel(Enum):
    """Content filtering sensitivity levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    RELAXED = "relaxed"
    MINIMAL = "minimal"


@dataclass
class UserPreferences:
    """
    User-specific preferences for content analysis.
    
    Manages denominational preferences, filtering levels,
    and other personalization settings.
    """
    user_id: Optional[int] = None
    denomination: Denomination = Denomination.GENERAL
    content_filter_level: ContentFilterLevel = ContentFilterLevel.MODERATE
    preferred_bible_translation: str = "NIV"
    language: str = "en"
    
    # Content preferences
    enable_profanity_filter: bool = True
    enable_substance_filter: bool = True
    enable_violence_filter: bool = True
    enable_sexual_content_filter: bool = True
    
    # Analysis preferences
    include_biblical_themes: bool = True
    include_supporting_scripture: bool = True
    detailed_analysis: bool = True
    
    # Display preferences
    show_confidence_scores: bool = False
    show_raw_predictions: bool = False
    max_scripture_references: int = 5
    
    def update(self, **kwargs) -> None:
        """
        Update user preferences.
        
        Args:
            **kwargs: Preference updates
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                # Handle enum conversions
                if key == 'denomination' and isinstance(value, str):
                    try:
                        value = Denomination(value.lower())
                    except ValueError:
                        logger.warning(f"Invalid denomination: {value}, keeping current")
                        continue
                
                elif key == 'content_filter_level' and isinstance(value, str):
                    try:
                        value = ContentFilterLevel(value.lower())
                    except ValueError:
                        logger.warning(f"Invalid content filter level: {value}, keeping current")
                        continue
                
                setattr(self, key, value)
                logger.debug(f"Updated user preference: {key} = {value}")
            else:
                logger.warning(f"Unknown user preference: {key}")
    
    def get_content_thresholds(self) -> Dict[str, float]:
        """
        Get content detection thresholds based on filter level.
        
        Returns:
            Dictionary of content type to threshold mappings
        """
        thresholds = {
            ContentFilterLevel.STRICT: {
                'profanity': 0.3,
                'substance': 0.3,
                'violence': 0.3,
                'sexual': 0.3,
                'general_offensive': 0.2
            },
            ContentFilterLevel.MODERATE: {
                'profanity': 0.5,
                'substance': 0.5,
                'violence': 0.5,
                'sexual': 0.5,
                'general_offensive': 0.4
            },
            ContentFilterLevel.RELAXED: {
                'profanity': 0.7,
                'substance': 0.7,
                'violence': 0.7,
                'sexual': 0.7,
                'general_offensive': 0.6
            },
            ContentFilterLevel.MINIMAL: {
                'profanity': 0.8,
                'substance': 0.8,
                'violence': 0.8,
                'sexual': 0.8,
                'general_offensive': 0.8
            }
        }
        
        return thresholds.get(self.content_filter_level, thresholds[ContentFilterLevel.MODERATE])
    
    def get_enabled_filters(self) -> List[str]:
        """
        Get list of enabled content filters.
        
        Returns:
            List of enabled filter names
        """
        enabled = []
        
        if self.enable_profanity_filter:
            enabled.append('profanity')
        if self.enable_substance_filter:
            enabled.append('substance')
        if self.enable_violence_filter:
            enabled.append('violence')
        if self.enable_sexual_content_filter:
            enabled.append('sexual')
        
        return enabled
    
    def get_biblical_preferences(self) -> Dict[str, Any]:
        """
        Get biblical analysis preferences.
        
        Returns:
            Dictionary of biblical analysis settings
        """
        return {
            'denomination': self.denomination.value,
            'preferred_translation': self.preferred_bible_translation,
            'include_themes': self.include_biblical_themes,
            'include_scripture': self.include_supporting_scripture,
            'max_references': self.max_scripture_references
        }
    
    def is_content_filter_enabled(self, filter_type: str) -> bool:
        """
        Check if a specific content filter is enabled.
        
        Args:
            filter_type: Type of filter to check
            
        Returns:
            True if filter is enabled, False otherwise
        """
        filter_mapping = {
            'profanity': self.enable_profanity_filter,
            'substance': self.enable_substance_filter,
            'violence': self.enable_violence_filter,
            'sexual': self.enable_sexual_content_filter
        }
        
        return filter_mapping.get(filter_type, False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """
        Create UserPreferences from dictionary.
        
        Args:
            data: Preferences data dictionary
            
        Returns:
            UserPreferences instance
        """
        try:
            prefs = cls()
            prefs.update(**data)
            return prefs
        except Exception as e:
            logger.error(f"Error creating UserPreferences from dict: {str(e)}")
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert UserPreferences to dictionary.
        
        Returns:
            Preferences dictionary
        """
        return {
            'user_id': self.user_id,
            'denomination': self.denomination.value,
            'content_filter_level': self.content_filter_level.value,
            'preferred_bible_translation': self.preferred_bible_translation,
            'language': self.language,
            'enable_profanity_filter': self.enable_profanity_filter,
            'enable_substance_filter': self.enable_substance_filter,
            'enable_violence_filter': self.enable_violence_filter,
            'enable_sexual_content_filter': self.enable_sexual_content_filter,
            'include_biblical_themes': self.include_biblical_themes,
            'include_supporting_scripture': self.include_supporting_scripture,
            'detailed_analysis': self.detailed_analysis,
            'show_confidence_scores': self.show_confidence_scores,
            'show_raw_predictions': self.show_raw_predictions,
            'max_scripture_references': self.max_scripture_references
        }
    
    def validate(self) -> bool:
        """
        Validate user preferences.
        
        Returns:
            True if preferences are valid, False otherwise
        """
        try:
            # Validate max scripture references
            if self.max_scripture_references <= 0:
                logger.error("max_scripture_references must be positive")
                return False
            
            # Validate enum values
            if not isinstance(self.denomination, Denomination):
                logger.error("Invalid denomination value")
                return False
            
            if not isinstance(self.content_filter_level, ContentFilterLevel):
                logger.error("Invalid content filter level")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating user preferences: {str(e)}")
            return False 