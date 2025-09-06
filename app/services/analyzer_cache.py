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
                        # Router-only initialization
                        base = os.environ.get("LLM_API_BASE_URL")
                        candidates = []
                        if base:
                            candidates.append(base)
                        # Common in-docker endpoints (auto-detect) - prefer vLLM, then Ollama
                        candidates.append("http://llm:8000/v1")
                        candidates.append("http://ollama:11434/v1")
                        # Host fallback for Docker Desktop
                        candidates.append("http://host.docker.internal:11434/v1")
                        reachable = None
                        for url in candidates:
                            try:
                                r = requests.get(f"{url.rstrip('/')}/models", timeout=1.5)
                                if r.status_code == 200:
                                    reachable = url
                                    break
                            except Exception:
                                continue
                        if reachable and not base:
                            os.environ["LLM_API_BASE_URL"] = reachable

                        logger.info("🚀 Initializing shared Router analyzer (OpenAI-compatible)…")
                        self._analyzer = RouterAnalyzer()

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

    def preflight(self) -> Tuple[bool, str]:
        """Quick readiness check. Verifies LLM endpoint when selected."""
        try:
            forced_llm = os.environ.get("USE_LLM_ANALYZER")
            if forced_llm is not None:
                use_llm = forced_llm in ("1", "true", "True")
            else:
                # Mirror auto-detect logic
                base = os.environ.get("LLM_API_BASE_URL")
                candidates = []
                if base:
                    candidates.append(base)
                # Prefer vLLM first for readiness, then Ollama
                candidates.append("http://llm:8000/v1")
                candidates.append("http://ollama:11434/v1")
                candidates.append("http://host.docker.internal:11434/v1")
                reachable = None
                for url in candidates:
                    try:
                        r = requests.get(f"{url.rstrip('/')}/models", timeout=1.5)
                        if r.status_code == 200:
                            reachable = url
                            break
                    except Exception:
                        continue
                use_llm = reachable is not None

            if not use_llm:
                return True, "Router analyzer not enabled (endpoint not detected)"

            base = os.environ.get("LLM_API_BASE_URL") or "http://host.docker.internal:11434/v1"
            try:
                resp = requests.get(f"{base.rstrip('/')}/models", timeout=2.5)
                if resp.status_code != 200:
                    return False, f"LLM endpoint responded {resp.status_code}"
                models = (
                    resp.json()
                    if resp.headers.get("content-type", "").startswith("application/json")
                    else {}
                )
                target = os.environ.get("LLM_MODEL")
                if target:
                    # Ollama returns objects with 'name'; vLLM returns 'id'
                    names = set()
                    if isinstance(models, dict) and "data" in models:
                        names = {m.get("id") or m.get("name") for m in models["data"]}
                    elif isinstance(models, list):
                        names = {m.get("name") or m.get("id") for m in models}
                    if target not in names:
                        return False, f"Model {target} not available at endpoint"
                return True, "Router LLM endpoint ready"
            except Exception as e:
                return False, f"LLM preflight failed: {e}"
        except Exception as e:
            return False, f"Analyzer preflight error: {e}"

    def is_ready(self) -> bool:
        """Check if analyzer is initialized and ready"""
        return self._analyzer is not None and not self._is_initializing

    def get_model_info(self) -> dict:
        """Get information about loaded models"""
        if self._analyzer is None:
            return {"status": "not_initialized", "models": []}

        # Router-only: report endpoint/model info rather than HF internals
        analyzer_type = type(self._analyzer).__name__ if self._analyzer else "unknown"
        api_base = os.environ.get("LLM_API_BASE_URL")
        model = os.environ.get("LLM_MODEL")
        return {
            "status": "ready" if self._analyzer is not None else "loading",
            "analyzer_type": analyzer_type,
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


def initialize_analyzer() -> RouterAnalyzer:
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
