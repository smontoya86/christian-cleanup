"""
Analyzer Cache Service - Singleton pattern for model caching

This service ensures that expensive AI models are loaded only once
and reused across all song analyses, dramatically improving performance.
"""

import threading
import logging
from typing import Optional

from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer

logger = logging.getLogger(__name__)

class AnalyzerCache:
    """Singleton cache for HuggingFace analyzer with thread safety"""
    
    _instance: Optional['AnalyzerCache'] = None
    _lock = threading.Lock()
    _analyzer: Optional[HuggingFaceAnalyzer] = None
    _initialization_lock = threading.Lock()
    _is_initializing = False
    
    def __new__(cls) -> 'AnalyzerCache':
        """Ensure only one instance exists (singleton pattern)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_analyzer(self) -> HuggingFaceAnalyzer:
        """Get the cached analyzer instance, initializing if necessary"""
        if self._analyzer is None:
            with self._initialization_lock:
                if self._analyzer is None and not self._is_initializing:
                    self._is_initializing = True
                    try:
                        logger.info("🚀 Initializing shared HuggingFace analyzer (one-time setup)...")
                        self._analyzer = HuggingFaceAnalyzer()
                        logger.info("✅ Shared analyzer initialized successfully")
                    except Exception as e:
                        logger.error(f"❌ Failed to initialize shared analyzer: {e}")
                        raise
                    finally:
                        self._is_initializing = False
                elif self._is_initializing:
                    # Another thread is initializing, wait for it
                    import time
                    while self._is_initializing and self._analyzer is None:
                        time.sleep(0.1)
        
        if self._analyzer is None:
            raise RuntimeError("Failed to initialize shared analyzer")
        
        return self._analyzer
    
    def is_ready(self) -> bool:
        """Check if analyzer is initialized and ready"""
        return self._analyzer is not None and not self._is_initializing
    
    def get_model_info(self) -> dict:
        """Get information about loaded models"""
        if self._analyzer is None:
            return {"status": "not_initialized", "models": []}
        
        models_info = []
        
        # Check each model property
        if hasattr(self._analyzer, '_sentiment_analyzer') and self._analyzer._sentiment_analyzer:
            models_info.append("sentiment_analyzer")
        if hasattr(self._analyzer, '_safety_analyzer') and self._analyzer._safety_analyzer:
            models_info.append("safety_analyzer")
        if hasattr(self._analyzer, '_emotion_analyzer') and self._analyzer._emotion_analyzer:
            models_info.append("emotion_analyzer")
        if hasattr(self._analyzer, '_theme_analyzer') and self._analyzer._theme_analyzer:
            models_info.append("theme_analyzer")
        
        return {
            "status": "ready" if models_info else "loading",
            "models": models_info,
            "model_count": len(models_info)
        }
    
    def clear_cache(self):
        """Clear the cached analyzer (for testing/debugging)"""
        with self._initialization_lock:
            logger.warning("🔄 Clearing analyzer cache...")
            self._analyzer = None
            self._is_initializing = False


# Global cache instance
_global_cache = AnalyzerCache()


def get_shared_analyzer() -> HuggingFaceAnalyzer:
    """
    Get the shared HuggingFace analyzer instance.
    
    This function provides access to a singleton analyzer that loads
    models once and reuses them across all song analyses.
    
    Returns:
        HuggingFaceAnalyzer: The shared analyzer instance
    """
    return _global_cache.get_analyzer()


def is_analyzer_ready() -> bool:
    """Check if the shared analyzer is ready for use"""
    return _global_cache.is_ready()


def get_analyzer_info() -> dict:
    """Get information about the shared analyzer and its models"""
    return _global_cache.get_model_info()


def clear_analyzer_cache():
    """Clear the analyzer cache (primarily for testing)"""
    _global_cache.clear_cache()


def initialize_analyzer() -> HuggingFaceAnalyzer:
    """
    Initialize the shared analyzer (can be called at worker startup).
    
    This is useful for pre-loading models during worker initialization
    rather than waiting for the first analysis request.
    
    Returns:
        HuggingFaceAnalyzer: The initialized analyzer
    """
    logger.info("🔧 Pre-initializing shared analyzer at startup...")
    analyzer = get_shared_analyzer()
    logger.info(f"✅ Analyzer pre-initialization complete. Models: {get_analyzer_info()}")
    return analyzer 