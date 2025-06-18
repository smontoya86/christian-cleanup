"""
Prediction Result

Standardized data structure for model prediction outputs.
Provides consistent interface for all model predictions.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from enum import Enum


class PredictionType(Enum):
    """Types of predictions supported by the system."""
    CONTENT_MODERATION = "content_moderation"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    THEME_DETECTION = "theme_detection"
    LANGUAGE_DETECTION = "language_detection"


@dataclass
class PredictionResult:
    """
    Standardized result format for all model predictions.
    
    This ensures consistent data structure across different
    models and prediction types.
    """
    prediction_type: PredictionType
    confidence: float  # 0.0 to 1.0
    predictions: List[Dict[str, Any]]
    raw_output: Optional[Dict[str, Any]] = None
    model_name: Optional[str] = None
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def get_top_prediction(self) -> Optional[Dict[str, Any]]:
        """
        Get the prediction with highest confidence.
        
        Returns:
            Top prediction dictionary or None if no predictions
        """
        if not self.predictions:
            return None
        
        return max(self.predictions, key=lambda p: p.get('score', 0.0))
    
    def get_predictions_above_threshold(self, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Get all predictions above confidence threshold.
        
        Args:
            threshold: Minimum confidence threshold
            
        Returns:
            List of predictions above threshold
        """
        return [
            pred for pred in self.predictions 
            if pred.get('score', 0.0) >= threshold
        ]
    
    def has_high_confidence_prediction(self, threshold: float = 0.8) -> bool:
        """
        Check if any prediction has high confidence.
        
        Args:
            threshold: High confidence threshold
            
        Returns:
            True if any prediction exceeds threshold
        """
        return any(
            pred.get('score', 0.0) >= threshold 
            for pred in self.predictions
        )
    
    def get_labels_with_scores(self) -> Dict[str, float]:
        """
        Get mapping of labels to their scores.
        
        Returns:
            Dictionary mapping labels to confidence scores
        """
        return {
            pred.get('label', ''): pred.get('score', 0.0)
            for pred in self.predictions
            if 'label' in pred
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert PredictionResult to dictionary.
        
        Returns:
            Dictionary representation of the prediction result
        """
        return {
            'prediction_type': self.prediction_type.value,
            'confidence': self.confidence,
            'predictions': self.predictions,
            'raw_output': self.raw_output,
            'model_name': self.model_name,
            'processing_time': self.processing_time,
            'metadata': self.metadata
        } 