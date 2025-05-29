"""
Base Pattern Detector

Provides the abstract interface that all pattern detection classes must implement.
This ensures consistency across different detection algorithms.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class DetectionResult:
    """
    Represents the result of a pattern detection operation.
    """
    detected: bool
    confidence: float  # 0.0 to 1.0
    matches: List[str]
    category: str
    subcategory: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class BasePatternDetector(ABC):
    """
    Abstract base class for all pattern detection implementations.
    
    This interface ensures all detectors provide consistent methods
    and return standardized results.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the detector with optional configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.sensitivity = self.config.get('sensitivity', 'medium')
        self.enabled = self.config.get('enabled', True)
    
    @abstractmethod
    def detect(self, text: str) -> DetectionResult:
        """
        Detect patterns in the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            DetectionResult with findings
        """
        pass
    
    @abstractmethod
    def get_category_name(self) -> str:
        """
        Get the category name this detector handles.
        
        Returns:
            Category name string
        """
        pass
    
    def is_enabled(self) -> bool:
        """
        Check if this detector is enabled.
        
        Returns:
            True if detector is enabled
        """
        return self.enabled
    
    def get_sensitivity_level(self) -> str:
        """
        Get the current sensitivity level.
        
        Returns:
            Sensitivity level (low, medium, high)
        """
        return self.sensitivity
    
    def set_sensitivity(self, level: str) -> None:
        """
        Set the sensitivity level for detection.
        
        Args:
            level: Sensitivity level (low, medium, high)
        """
        if level in ['low', 'medium', 'high']:
            self.sensitivity = level
        else:
            raise ValueError(f"Invalid sensitivity level: {level}")
    
    def _create_result(self, detected: bool, confidence: float, 
                      matches: List[str], subcategory: str = None,
                      context: Dict[str, Any] = None) -> DetectionResult:
        """
        Helper method to create standardized detection results.
        
        Args:
            detected: Whether patterns were detected
            confidence: Confidence level (0.0 to 1.0)
            matches: List of matched patterns/words
            subcategory: Optional subcategory classification
            context: Optional additional context information
            
        Returns:
            DetectionResult instance
        """
        return DetectionResult(
            detected=detected,
            confidence=confidence,
            matches=matches,
            category=self.get_category_name(),
            subcategory=subcategory,
            context=context or {}
        ) 