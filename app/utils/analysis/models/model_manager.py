"""
Model Manager

Centralized management for AI models used in content analysis.
Handles model loading, caching, and lifecycle management.
"""

import logging
import time
from typing import Dict, Optional, Any, List
from enum import Enum
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

from .prediction_result import PredictionResult, PredictionType

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Types of models supported by the system."""
    CONTENT_MODERATION = "content_moderation"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    TOXICITY_DETECTION = "toxicity_detection"


class ModelManager:
    """
    Centralized manager for AI models.
    
    Handles loading, caching, and lifecycle management of
    machine learning models used throughout the application.
    """
    
    def __init__(self, device: Optional[str] = None):
        """
        Initialize the model manager.
        
        Args:
            device: Device to use for model inference ('cpu', 'cuda', etc.)
        """
        self.device = device or self._get_default_device()
        self._models: Dict[str, Any] = {}
        self._tokenizers: Dict[str, Any] = {}
        self._pipelines: Dict[str, Any] = {}
        
        logger.info(f"ModelManager initialized with device: {self.device}")
    
    def _get_default_device(self) -> str:
        """
        Get the default device for model inference.
        
        Returns:
            Device string ('cuda' if available, otherwise 'cpu')
        """
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    def load_content_moderation_model(self, model_name: str = "cardiffnlp/twitter-roberta-base-offensive") -> bool:
        """
        Load content moderation model.
        
        Args:
            model_name: HuggingFace model identifier
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            start_time = time.time()
            
            logger.info(f"Loading content moderation model: {model_name}")
            
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Move model to device
            model.to(self.device)
            
            # Create pipeline
            pipeline_obj = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True
            )
            
            # Cache components
            self._tokenizers[model_name] = tokenizer
            self._models[model_name] = model
            self._pipelines[model_name] = pipeline_obj
            
            load_time = time.time() - start_time
            logger.info(f"Content moderation model loaded in {load_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load content moderation model: {str(e)}")
            return False
    
    def load_sentiment_model(self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest") -> bool:
        """
        Load sentiment analysis model.
        
        Args:
            model_name: HuggingFace model identifier
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            start_time = time.time()
            
            logger.info(f"Loading sentiment model: {model_name}")
            
            pipeline_obj = pipeline(
                "sentiment-analysis",
                model=model_name,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True
            )
            
            self._pipelines[model_name] = pipeline_obj
            
            load_time = time.time() - start_time
            logger.info(f"Sentiment model loaded in {load_time:.2f} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load sentiment model: {str(e)}")
            return False
    
    def get_model(self, model_name: str) -> Optional[Any]:
        """
        Get a loaded model.
        
        Args:
            model_name: Model identifier
            
        Returns:
            Model object or None if not loaded
        """
        return self._models.get(model_name)
    
    def get_pipeline(self, model_name: str) -> Optional[Any]:
        """
        Get a loaded pipeline.
        
        Args:
            model_name: Model identifier
            
        Returns:
            Pipeline object or None if not loaded
        """
        return self._pipelines.get(model_name)
    
    def is_model_loaded(self, model_name: str) -> bool:
        """
        Check if a model is loaded.
        
        Args:
            model_name: Model identifier
            
        Returns:
            True if model is loaded, False otherwise
        """
        return model_name in self._models or model_name in self._pipelines
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_name: Model identifier
            
        Returns:
            True if unloaded successfully, False otherwise
        """
        try:
            if model_name in self._models:
                del self._models[model_name]
            if model_name in self._tokenizers:
                del self._tokenizers[model_name]
            if model_name in self._pipelines:
                del self._pipelines[model_name]
            
            logger.info(f"Model {model_name} unloaded from memory")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload model {model_name}: {str(e)}")
            return False
    
    def get_loaded_models(self) -> List[str]:
        """
        Get list of currently loaded models.
        
        Returns:
            List of model names that are currently loaded
        """
        all_models = set(self._models.keys())
        all_models.update(self._pipelines.keys())
        return list(all_models)
    
    def clear_cache(self) -> None:
        """Clear all loaded models from memory."""
        self._models.clear()
        self._tokenizers.clear()
        self._pipelines.clear()
        logger.info("Model cache cleared")
    
    def get_memory_info(self) -> Dict[str, Any]:
        """
        Get memory usage information.
        
        Returns:
            Dictionary with memory usage statistics
        """
        info = {
            'device': self.device,
            'loaded_models': len(self._models),
            'loaded_pipelines': len(self._pipelines),
            'model_names': self.get_loaded_models()
        }
        
        if torch.cuda.is_available():
            info['cuda_memory_allocated'] = torch.cuda.memory_allocated()
            info['cuda_memory_cached'] = torch.cuda.memory_reserved()
        
        return info
    
    def get_model_status(self, model_type: str) -> Dict[str, Any]:
        """
        Get the status of a specific model type.
        
        Args:
            model_type: Type of model to check
            
        Returns:
            Dictionary with model status information
        """
        status = {
            'loaded': False,
            'model_name': None,
            'last_used': None,
            'memory_usage': 0
        }
        
        # Check if any models of this type are loaded
        for model_name in self.get_loaded_models():
            if model_type.lower() in model_name.lower():
                status['loaded'] = True
                status['model_name'] = model_name
                break
        
        return status 