"""
Analyzer Cache Service - Singleton pattern for model caching

This service ensures that expensive AI models are loaded only once
and reused across all song analyses, dramatically improving performance.
"""

import logging
import os
import threading
from typing import Optional

from app.services.analyzers.router_analyzer import RouterAnalyzer
from typing import Tuple

import requests

logger = logging.getLogger(__name__)


class AnalyzerCache:
    """Singleton cache for Router analyzer with thread safety"""

    _instance: Optional["AnalyzerCache"] = None
    _lock = threading.Lock()
    _analyzer: Optional[RouterAnalyzer] = None
    _initialization_lock = threading.Lock()
    _is_initializing = False

    def __new__(cls) -> "AnalyzerCache":
        """Ensure only one instance exists (singleton pattern)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_analyzer(self):
        """Get the cached analyzer instance, initializing if necessary"""
        if self._analyzer is None:
            with self._initialization_lock:
                if self._analyzer is None and not self._is_initializing:
                    self._is_initializing = True
                    try:
                        logger.info("🚀 Initializing shared Router analyzer (OpenAI API)...")
                        self._analyzer = RouterAnalyzer()
                        logger.info("✅ Shared Router analyzer initialized successfully")
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

    def preflight(self) -> Tuple[bool, str]:
        """Quick readiness check for OpenAI API."""
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return False, "OPENAI_API_KEY not configured"
            
            # Simple check - just verify API key is set
            # Actual connectivity will be verified on first request
            return True, "OpenAI API configured"
        except Exception as e:
            return False, f"Analyzer preflight error: {e}"

    def is_ready(self) -> bool:
        """Check if analyzer is initialized and ready"""
        return self._analyzer is not None and not self._is_initializing

    def get_model_info(self) -> dict:
        """Get information about the OpenAI analyzer"""
        if self._analyzer is None:
            return {"status": "not_initialized", "provider": "openai"}

        analyzer_type = type(self._analyzer).__name__ if self._analyzer else "unknown"
        api_base = os.environ.get("LLM_API_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("OPENAI_MODEL", "ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav")
        return {
            "status": "ready" if self._analyzer is not None else "loading",
            "analyzer_type": analyzer_type,
            "provider": "openai",
            "endpoint": api_base,
            "model": model,
        }

    def clear_cache(self):
        """Clear the cached analyzer (for testing/debugging)"""
        with self._initialization_lock:
            logger.warning("🔄 Clearing analyzer cache...")
            self._analyzer = None
            self._is_initializing = False


# Global cache instance
_global_cache = AnalyzerCache()


def get_shared_analyzer() -> RouterAnalyzer:
    """
    Get the shared Router analyzer instance.

    This function provides access to a singleton analyzer that uses
    the fine-tuned GPT-4o-mini model via OpenAI API.

    Returns:
        RouterAnalyzer: The shared analyzer instance
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


def initialize_analyzer() -> RouterAnalyzer:
    """
    Initialize the shared analyzer (can be called at worker startup).

    This is useful for pre-initializing the OpenAI connection during
    worker startup rather than waiting for the first analysis request.

    Returns:
        RouterAnalyzer: The initialized analyzer
    """
    logger.info("🔧 Pre-initializing shared analyzer at startup...")
    analyzer = get_shared_analyzer()
    logger.info(f"✅ Analyzer pre-initialization complete. Info: {get_analyzer_info()}")
    return analyzer
