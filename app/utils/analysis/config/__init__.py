"""
Configuration Domain

Manages user preferences, analysis settings, and system configuration.
Provides centralized configuration management for all analysis components.
"""

from .analysis_config import AnalysisConfig
from .user_preferences import UserPreferences
from .sensitivity_settings import SensitivitySettings
from .scoring_weights import ScoringWeights

__all__ = [
    'AnalysisConfig',
    'UserPreferences', 
    'SensitivitySettings',
    'ScoringWeights'
] 