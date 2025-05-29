"""
Pattern Registry

Manages and coordinates all pattern detection classes.
Provides a unified interface for running multiple detectors.
"""

import logging
from typing import Dict, List, Any, Optional, Type

from .base_detector import BasePatternDetector, DetectionResult
from .profanity_detector import ProfanityDetector
from .drug_detector import SubstanceDetector
from .violence_detector import ViolenceDetector

logger = logging.getLogger(__name__)


class PatternRegistry:
    """
    Registry that manages all pattern detection classes.
    
    Provides a centralized way to run multiple detectors and
    aggregate their results.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the pattern registry.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.detectors = {}
        
        # Register default detectors
        self._register_default_detectors()
        
        logger.debug(f"PatternRegistry initialized with {len(self.detectors)} detectors")
    
    def register_detector(self, name: str, detector_class: Type[BasePatternDetector], 
                         config: Optional[Dict[str, Any]] = None) -> None:
        """
        Register a new pattern detector.
        
        Args:
            name: Name to register the detector under
            detector_class: The detector class to instantiate
            config: Optional configuration for the detector
        """
        try:
            detector_config = config or self.config.get(name, {})
            detector_instance = detector_class(detector_config)
            self.detectors[name] = detector_instance
            logger.debug(f"Registered detector: {name}")
        except Exception as e:
            logger.error(f"Failed to register detector {name}: {e}")
    
    def unregister_detector(self, name: str) -> None:
        """
        Remove a detector from the registry.
        
        Args:
            name: Name of the detector to remove
        """
        if name in self.detectors:
            del self.detectors[name]
            logger.debug(f"Unregistered detector: {name}")
    
    def get_detector(self, name: str) -> Optional[BasePatternDetector]:
        """
        Get a specific detector by name.
        
        Args:
            name: Name of the detector
            
        Returns:
            Detector instance or None if not found
        """
        return self.detectors.get(name)
    
    def detect_all(self, text: str, enabled_only: bool = True) -> Dict[str, DetectionResult]:
        """
        Run all registered detectors on the given text.
        
        Args:
            text: Text to analyze
            enabled_only: Only run enabled detectors
            
        Returns:
            Dictionary mapping detector names to results
        """
        results = {}
        
        for name, detector in self.detectors.items():
            if enabled_only and not detector.is_enabled():
                continue
                
            try:
                result = detector.detect(text)
                results[name] = result
                logger.debug(f"Detector {name}: detected={result.detected}, confidence={result.confidence}")
            except Exception as e:
                logger.error(f"Error running detector {name}: {e}", exc_info=True)
                # Create empty result for failed detector
                results[name] = DetectionResult(
                    detected=False,
                    confidence=0.0,
                    matches=[],
                    category=detector.get_category_name(),
                    context={'error': str(e)}
                )
        
        return results
    
    def detect_categories(self, text: str, categories: List[str]) -> Dict[str, DetectionResult]:
        """
        Run detectors for specific categories only.
        
        Args:
            text: Text to analyze
            categories: List of category names to run
            
        Returns:
            Dictionary mapping detector names to results
        """
        results = {}
        
        for name, detector in self.detectors.items():
            if detector.get_category_name() in categories and detector.is_enabled():
                try:
                    result = detector.detect(text)
                    results[name] = result
                except Exception as e:
                    logger.error(f"Error running detector {name}: {e}", exc_info=True)
        
        return results
    
    def get_summary(self, results: Dict[str, DetectionResult]) -> Dict[str, Any]:
        """
        Generate a summary of detection results.
        
        Args:
            results: Results from detect_all or detect_categories
            
        Returns:
            Summary dictionary with aggregated information
        """
        summary = {
            'total_detectors': len(results),
            'detected_categories': [],
            'highest_confidence': 0.0,
            'total_matches': 0,
            'category_breakdown': {}
        }
        
        for name, result in results.items():
            if result.detected:
                summary['detected_categories'].append(result.category)
                summary['highest_confidence'] = max(summary['highest_confidence'], result.confidence)
                summary['total_matches'] += len(result.matches)
                
                if result.category not in summary['category_breakdown']:
                    summary['category_breakdown'][result.category] = {
                        'detectors': [],
                        'total_matches': 0,
                        'max_confidence': 0.0
                    }
                
                summary['category_breakdown'][result.category]['detectors'].append(name)
                summary['category_breakdown'][result.category]['total_matches'] += len(result.matches)
                summary['category_breakdown'][result.category]['max_confidence'] = max(
                    summary['category_breakdown'][result.category]['max_confidence'],
                    result.confidence
                )
        
        # Remove duplicates and sort
        summary['detected_categories'] = sorted(list(set(summary['detected_categories'])))
        
        return summary
    
    def set_global_sensitivity(self, sensitivity: str) -> None:
        """
        Set sensitivity level for all registered detectors.
        
        Args:
            sensitivity: Sensitivity level (low, medium, high)
        """
        for detector in self.detectors.values():
            try:
                detector.set_sensitivity(sensitivity)
            except Exception as e:
                logger.warning(f"Failed to set sensitivity for detector: {e}")
    
    def enable_detector(self, name: str) -> None:
        """
        Enable a specific detector.
        
        Args:
            name: Name of the detector to enable
        """
        if name in self.detectors:
            self.detectors[name].enabled = True
    
    def disable_detector(self, name: str) -> None:
        """
        Disable a specific detector.
        
        Args:
            name: Name of the detector to disable
        """
        if name in self.detectors:
            self.detectors[name].enabled = False
    
    def list_detectors(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registered detectors.
        
        Returns:
            Dictionary with detector information
        """
        detector_info = {}
        
        for name, detector in self.detectors.items():
            detector_info[name] = {
                'category': detector.get_category_name(),
                'enabled': detector.is_enabled(),
                'sensitivity': detector.get_sensitivity_level(),
                'class': detector.__class__.__name__
            }
        
        return detector_info
    
    def _register_default_detectors(self) -> None:
        """Register the default set of pattern detectors."""
        default_detectors = [
            ('profanity', ProfanityDetector),
            ('substance', SubstanceDetector),
            ('violence', ViolenceDetector)
        ]
        
        for name, detector_class in default_detectors:
            self.register_detector(name, detector_class) 