"""
RouterAnalyzer: Minimal OpenAI-compatible analyzer wrapper

Interface: analyze_song(title, artist, lyrics) -> dict

Env variables:
- LLM_API_BASE_URL (default: http://localhost:11434/v1)
- LLM_MODEL (default: llama3.1:8b)
- LLM_TEMPERATURE (default: 0.2)
- LLM_TOP_P (default: 0.9)
- LLM_MAX_TOKENS (default: 512)
- LLM_TIMEOUT (default: 30)
- LLM_CONCURRENCY (default: 1)  # not used here, reserved for future batching
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

import requests


class RouterAnalyzer:
    def __init__(self) -> None:
        # Import the intelligent router
        from ..intelligent_llm_router import get_intelligent_router
        
        self.router = get_intelligent_router()
        
        # Fallback configuration for when router fails
        self.fallback_base_url: str = os.environ.get("LLM_API_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        self.fallback_model: str = os.environ.get("LLM_MODEL", "llama3.1:8b")
        
        # LLM parameters
        try:
            self.temperature: float = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
        except Exception:
            self.temperature = 0.2
        try:
            self.top_p: float = float(os.environ.get("LLM_TOP_P", "0.9"))
        except Exception:
            self.top_p = 0.9
        try:
            self.max_tokens: int = int(os.environ.get("LLM_MAX_TOKENS", "512"))
        except Exception:
            self.max_tokens = 512
        try:
            self.timeout: float = float(os.environ.get("LLM_TIMEOUT", "30"))
        except Exception:
            self.timeout = 30.0
        # Reserved for future usage
        _ = os.environ.get("LLM_CONCURRENCY", "1")
    
    def _get_current_provider_config(self):
        """Get the current provider configuration from the intelligent router"""
        provider = self.router.get_optimal_provider()
        
        if provider:
            return {
                "base_url": provider.endpoint.rstrip("/"),
                "model": provider.model,
                "timeout": provider.timeout,
                "provider_name": provider.name
            }
        else:
            # Fallback to environment configuration
            return {
                "base_url": self.fallback_base_url,
                "model": self.fallback_model,
                "timeout": self.timeout,
                "provider_name": "fallback"
            }

    def analyze_song(self, title: str, artist: str, lyrics: str) -> Dict[str, Any]:
        # Get the current provider configuration
        config = self._get_current_provider_config()
        
        url = f"{config['base_url']}/chat/completions"
        model = config['model']
        timeout = config['timeout']
        provider_name = config['provider_name']
        system = (
            "You are a theological music analyst. Return ONLY strict JSON with fields: score, concern_level, "
            "biblical_themes[], supporting_scripture[], concerns[], narrative_voice, lament_filter_applied, "
            "doctrinal_clarity, confidence, needs_review, verdict."
        )
        user = f"Song: {title} — {artist}\n\nLyrics:\n{(lyrics or '')[:16000]}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        try:
            resp = requests.post(url, json=payload, timeout=timeout)
            # raise_for_status may not exist on some mocked objects
            if hasattr(resp, "raise_for_status"):
                resp.raise_for_status()
            data = resp.json() if hasattr(resp, "json") else {}
            # OpenAI-style
            if isinstance(data, dict) and "choices" in data:
                content = (data.get("choices", [{}])[0] or {}).get("message", {}).get("content", "{}")
                parsed = self._parse_or_repair_json(content)
                return self._normalize_output(parsed)
            # Direct JSON response containing our target fields
            if isinstance(data, dict):
                return self._normalize_output(data)
            return self._default_output()
        except Exception:
            # On any error (timeout, network, parse), return safe default
            return self._default_output()

    def _parse_or_repair_json(self, text: Any) -> Dict[str, Any]:
        if isinstance(text, dict):
            return text
        if not isinstance(text, str):
            return {}
        try:
            return json.loads(text)
        except Exception:
            pass
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {}
        return {}

    def _normalize_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure required fields exist with sane defaults
        if not isinstance(data, dict):
            data = {}
        out: Dict[str, Any] = {
            "score": data.get("score", 50),
            "concern_level": data.get("concern_level", "Unknown"),
            "biblical_themes": data.get("biblical_themes", []) or [],
            "supporting_scripture": data.get("supporting_scripture", []) or [],
            "concerns": data.get("concerns", []) or [],
            "narrative_voice": data.get("narrative_voice"),
            "lament_filter_applied": data.get("lament_filter_applied"),
            "doctrinal_clarity": data.get("doctrinal_clarity"),
            "confidence": data.get("confidence"),
            "needs_review": data.get("needs_review"),
            "verdict": data.get("verdict") or {"summary": "context_required", "guidance": ""},
        }
        return out

    def _default_output(self) -> Dict[str, Any]:
        return {
            "score": 50,
            "concern_level": "Unknown",
            "biblical_themes": [],
            "supporting_scripture": [],
            "concerns": [],
            "narrative_voice": None,
            "lament_filter_applied": None,
            "doctrinal_clarity": None,
            "confidence": None,
            "needs_review": False,
            "verdict": {"summary": "context_required", "guidance": ""},
        }


