"""
Analyzer Cache Service - Singleton pattern for model caching

This service ensures that expensive AI models are loaded only once
and reused across all song analyses, dramatically improving performance.
"""

import logging
import os
import threading
from typing import Optional

from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer

try:
    from app.utils.analysis.llm_analyzer import LLMAnalyzer
except Exception:
    # Avoid hard import failure during early imports (e.g., regression_test.py import order)
    LLMAnalyzer = None  # type: ignore
from typing import Tuple

import requests

logger = logging.getLogger(__name__)


class AnalyzerCache:
    """Singleton cache for HuggingFace analyzer with thread safety"""

    _instance: Optional["AnalyzerCache"] = None
    _lock = threading.Lock()
    _analyzer: Optional[HuggingFaceAnalyzer] = None
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
                        # Auto-select analyzer unless explicitly forced
                        forced_llm = os.environ.get("USE_LLM_ANALYZER")
                        if forced_llm is not None:
                            use_llm = forced_llm in ("1", "true", "True")
                        else:
                            # Auto-detect: prefer external LLM if reachable; fallback to HF/MLX
                            base = os.environ.get("LLM_API_BASE_URL")
                            candidates = []
                            if base:
                                candidates.append(base)
                            # Ollama on host (dev on Mac)
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
                            if reachable and not base:
                                # Set base URL for the process so LLMAnalyzer picks it up
                                os.environ["LLM_API_BASE_URL"] = reachable

                        if use_llm and LLMAnalyzer is not None:
                            logger.info(
                                "🚀 Initializing shared LLM analyzer (OpenAI-compatible endpoint)…"
                            )
                            try:
                                self._analyzer = LLMAnalyzer()
                            except Exception as llm_err:
                                logger.error(
                                    f"❌ LLM analyzer init failed, falling back to HuggingFace: {llm_err}"
                                )
                                self._analyzer = HuggingFaceAnalyzer.get_instance()
                        else:
                            logger.info("🚀 Initializing shared HuggingFace/MLX analyzer (local)…")
                            self._analyzer = HuggingFaceAnalyzer.get_instance()

                        logger.info("✅ Shared analyzer initialized successfully")
                    except Exception as e:
                        logger.error(
                            f"❌ Failed to initialize shared analyzer: {e}. Falling back to HuggingFace if possible."
                        )
                        try:
                            self._analyzer = HuggingFaceAnalyzer.get_instance()
                            logger.info("✅ Fallback HuggingFace analyzer initialized")
                        except Exception as hf_err:
                            logger.error(f"❌ HuggingFace fallback initialization failed: {hf_err}")
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
                return True, "Using local HF/MLX analyzer"

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
                return True, "LLM endpoint ready"
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

        models_info = []

        # Report analyzer type
        analyzer_type = type(self._analyzer).__name__ if self._analyzer else "unknown"
        if analyzer_type == "LLMAnalyzer":
            models_info.append("llm_analyzer")
        else:
            # Check each HF model property
            if (
                hasattr(self._analyzer, "_sentiment_analyzer")
                and self._analyzer._sentiment_analyzer
            ):
                models_info.append("sentiment_analyzer")
            if hasattr(self._analyzer, "_safety_analyzer") and self._analyzer._safety_analyzer:
                models_info.append("safety_analyzer")
            if hasattr(self._analyzer, "_emotion_analyzer") and self._analyzer._emotion_analyzer:
                models_info.append("emotion_analyzer")
            if hasattr(self._analyzer, "_theme_analyzer") and self._analyzer._theme_analyzer:
                models_info.append("theme_analyzer")

        return {
            "status": "ready" if models_info else "loading",
            "models": models_info,
            "model_count": len(models_info),
            "analyzer_type": analyzer_type,
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
