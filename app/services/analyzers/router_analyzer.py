from __future__ import annotations

import json
import os
import re
import logging
from typing import Any, Dict

import requests

from ..intelligent_llm_router import get_intelligent_router

logger = logging.getLogger(__name__)

class RouterAnalyzer:
    def __init__(self) -> None:
        self.router = get_intelligent_router()
        
        provider_config = self.router.get_optimal_provider()
        self.base_url: str = provider_config.get("api_base", "http://localhost:11434/v1").rstrip("/")
        self.model: str = provider_config.get("model", "llama3.1:8b")
        
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

    def analyze_song(self, title: str, artist: str, lyrics: str) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        
        logger.info(f"Analyzing song with {self.model} at {url}")

        system = self._get_comprehensive_system_prompt()
        user = f"Song: {title} — {artist}\n\nLyrics:\n{lyrics or ''}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            logger.info(f"Response status code: {resp.status_code}")
            logger.info(f"Response text: {resp.text}")
            resp.raise_for_status()
            data = resp.json()
            content = (data.get("choices", [{}])[0] or {}).get("message", {}).get("content", "{}")
            parsed = self._parse_or_repair_json(content)
            return self._normalize_output(parsed)
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            return self._default_output()

    def _get_comprehensive_system_prompt(self) -> str:
        return """You are a theological music analyst applying a refined version of the Berean Test. Your goal is to provide a clear, biblically-grounded analysis of Christian music.

**Analysis Framework**

1.  **Message (What is the song about?):**
    *   Summarize the song's central message.
    *   Identify the main theological themes.

2.  **Biblical Alignment (Does the song align with Scripture?):**
    *   Provide specific biblical references that support or contradict the lyrics.
    *   Explain the biblical context of the references.
    *   Explicitly penalize for the absence of God/Jesus/Holy Spirit.

3.  **Outsider Interpretation (How would a non-Christian interpret the song?):**
    *   Assess the song's potential for misinterpretation.
    *   Consider the song's evangelistic potential.

4.  **Glorification of God (Does the song glorify God?):**
    *   Evaluate whether the song's primary focus is on God's character and actions.
    *   Assess the song's ability to lead listeners to worship.

**Scoring and Verdict**

*   **Score (0-10):** Based on the four criteria above.
*   **Verdict:**
    *   **Green (8-10):** Recommended for all listeners.
    *   **Purple (6-7.9):** Recommended with discernment.
    *   **Red (0-5.9):** Not recommended.

**JSON Output**

Your response MUST be a single, valid JSON object. Do NOT include any other text, explanations, or markdown formatting. The JSON object must have the following fields:
*   `score`: The overall score (0-10).
*   `verdict`: "Green", "Purple", or "Red".
*   `analysis`: An object containing the analysis with the following keys: `message`, `biblical_alignment`, `outsider_interpretation`, `glorification_of_god`.
"""

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
        if not isinstance(data, dict):
            data = {}
        out: Dict[str, Any] = {
            "score": data.get("score", 50),
            "verdict": data.get("verdict", "context_required"),
            "analysis": data.get("analysis", {}),
        }
        return out

    def _default_output(self) -> Dict[str, Any]:
        return {
            "score": 50,
            "verdict": "context_required",
            "analysis": {},
        }

