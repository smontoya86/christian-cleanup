"""
Content Moderation Model

Specialized model wrapper for content moderation tasks.
Handles text chunking, preprocessing, and result aggregation.
"""

import logging
import time
from typing import List, Dict, Any, Optional
import re

from .prediction_result import PredictionResult, PredictionType
from .model_manager import ModelManager

logger = logging.getLogger(__name__)


class ContentModerationModel:
    """
    Specialized wrapper for content moderation models.
    
    Handles text preprocessing, chunking for long texts,
    and aggregation of predictions across chunks.
    """
    
    def __init__(self, model_manager: ModelManager, model_name: str = "cardiffnlp/twitter-roberta-base-offensive"):
        """
        Initialize content moderation model.
        
        Args:
            model_manager: ModelManager instance
            model_name: HuggingFace model identifier
        """
        self.model_manager = model_manager
        self.model_name = model_name
        self._ensure_model_loaded()
    
    def _ensure_model_loaded(self) -> None:
        """Ensure the model is loaded."""
        if not self.model_manager.is_model_loaded(self.model_name):
            self.model_manager.load_content_moderation_model(self.model_name)
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text for content moderation.
        
        Args:
            text: Input text
            
        Returns:
            Preprocessed text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove section headers like [Chorus], [Verse]
        text = re.sub(r'\[[^\]]+\]', '', text)
        
        # Remove extra whitespace again
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _chunk_text(self, text: str, max_chunk_size: int = 500) -> List[str]:
        """
        Split text into chunks for processing.
        
        Args:
            text: Input text
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if len(text) <= max_chunk_size:
            return [text]
        
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = len(word)
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _predict_chunk(self, chunk: str) -> List[Dict[str, Any]]:
        """
        Get predictions for a single text chunk.
        
        Args:
            chunk: Text chunk
            
        Returns:
            List of predictions
        """
        try:
            pipeline = self.model_manager.get_pipeline(self.model_name)
            if not pipeline:
                logger.error(f"Pipeline not found for model: {self.model_name}")
                return []
            
            results = pipeline(chunk)
            
            # Normalize results format
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], list):
                    # Multiple predictions per input
                    return results[0]
                else:
                    # Single prediction per input
                    return results
            
            return []
            
        except Exception as e:
            logger.error(f"Error in chunk prediction: {str(e)}")
            return []
    
    def _aggregate_predictions(self, chunk_predictions: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Aggregate predictions across chunks.
        
        Args:
            chunk_predictions: List of prediction lists from each chunk
            
        Returns:
            Aggregated predictions
        """
        if not chunk_predictions:
            return []
        
        # Collect all labels and their scores
        label_scores = {}
        label_counts = {}
        
        for chunk_preds in chunk_predictions:
            for pred in chunk_preds:
                label = pred.get('label', '')
                score = pred.get('score', 0.0)
                
                if label not in label_scores:
                    label_scores[label] = 0.0
                    label_counts[label] = 0
                
                label_scores[label] += score
                label_counts[label] += 1
        
        # Calculate average scores
        aggregated = []
        for label, total_score in label_scores.items():
            avg_score = total_score / label_counts[label]
            aggregated.append({
                'label': label,
                'score': avg_score
            })
        
        # Sort by score descending
        aggregated.sort(key=lambda x: x['score'], reverse=True)
        
        return aggregated
    
    def predict(self, text: str, chunk_size: int = 500) -> PredictionResult:
        """
        Predict content moderation labels for text.
        
        Args:
            text: Input text
            chunk_size: Maximum size per chunk
            
        Returns:
            PredictionResult with predictions
        """
        start_time = time.time()
        
        try:
            # Preprocess text
            processed_text = self._preprocess_text(text)
            
            if not processed_text:
                return PredictionResult(
                    prediction_type=PredictionType.CONTENT_MODERATION,
                    confidence=0.0,
                    predictions=[],
                    model_name=self.model_name,
                    processing_time=time.time() - start_time
                )
            
            # Chunk text
            chunks = self._chunk_text(processed_text, chunk_size)
            
            # Get predictions for each chunk
            chunk_predictions = []
            for chunk in chunks:
                chunk_preds = self._predict_chunk(chunk)
                if chunk_preds:
                    chunk_predictions.append(chunk_preds)
            
            # Aggregate predictions
            aggregated_predictions = self._aggregate_predictions(chunk_predictions)
            
            # Calculate overall confidence
            confidence = 0.0
            if aggregated_predictions:
                confidence = max(pred['score'] for pred in aggregated_predictions)
            
            processing_time = time.time() - start_time
            
            return PredictionResult(
                prediction_type=PredictionType.CONTENT_MODERATION,
                confidence=confidence,
                predictions=aggregated_predictions,
                model_name=self.model_name,
                processing_time=processing_time,
                metadata={
                    'num_chunks': len(chunks),
                    'original_length': len(text),
                    'processed_length': len(processed_text)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in content moderation prediction: {str(e)}")
            
            return PredictionResult(
                prediction_type=PredictionType.CONTENT_MODERATION,
                confidence=0.0,
                predictions=[],
                model_name=self.model_name,
                processing_time=time.time() - start_time,
                metadata={'error': str(e)}
            )
    
    def is_ready(self) -> bool:
        """
        Check if the model is ready for predictions.
        
        Returns:
            True if model is loaded and ready
        """
        return self.model_manager.is_model_loaded(self.model_name) 