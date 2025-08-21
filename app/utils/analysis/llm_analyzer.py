"""
LLMAnalyzer (Apple MLX / OpenAI-compatible local server)

Provides a single-call JSON-emitting LLM analysis aligned to the Christian framework.
Designed to work with a local OpenAI-compatible endpoint (e.g., llama.cpp server or
mlx-lm OpenAI server) using an M1/M2 Mac.

Environment variables:
  - LLM_API_BASE_URL: Base URL to the OpenAI-compatible API (default: http://localhost:8080/v1)
  - LLM_MODEL: Model name to use (default: llama-3.1-8b-instruct)
  - LLM_API_KEY: Optional; not required for local servers
  - PROMPT_VERSION: String to embed for cache/versioning (default: v1)

Notes:
  - We enforce strict JSON via a post-parse validation and a repair attempt.
  - A tiny RAG retrieves relevant theme cards to ground outputs.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests
from flask import current_app
from pydantic import BaseModel, Field, ValidationError, confloat

from app.services.framework_loader import get_rules
from app.services.rules_rag import retrieve_rules
from app.utils.scripture.bsb_client import BsbClient

from .analysis_result import AnalysisResult
from .theology_kb import TheologyKB


class LLMAnalyzer:
    def __init__(self) -> None:
        self.base_url: str = os.environ.get("LLM_API_BASE_URL", "http://localhost:8080/v1")
        self.model: str = os.environ.get("LLM_MODEL", "llama-3.1-8b-instruct")
        self.api_key: Optional[str] = os.environ.get("LLM_API_KEY")
        self.prompt_version: str = os.environ.get("PROMPT_VERSION", "v1")

        # RAG KB and Bible client
        self.kb = TheologyKB()
        self.bible = BsbClient()

        # Request parameters tuned for JSON tasks
        self.temperature: float = float(os.environ.get("LLM_TEMPERATURE", "0.3"))
        self.top_p: float = float(os.environ.get("LLM_TOP_P", "0.9"))
        self.max_tokens: int = int(os.environ.get("LLM_MAX_TOKENS", "900"))

    # Public API expected by SimplifiedChristianAnalysisService
    def analyze_song(
        self, title: str, artist: str, lyrics: str, user_id: Optional[int] = None
    ) -> AnalysisResult:
        start = time.time()

        # Simple guardrails
        text = lyrics or ""
        if len(text.strip()) < 10:
            return AnalysisResult(
                title=title,
                artist=artist,
                lyrics_text=lyrics,
                processed_text=f"{title} {artist}".lower(),
                biblical_analysis={"themes": [], "supporting_scripture": []},
                content_analysis={
                    "concern_flags": [],
                    "safety_assessment": {"is_safe": True, "toxicity_score": 0.0},
                },
                scoring_results={"final_score": 50.0, "quality_level": "Unknown"},
                model_analysis={},
                processing_time=time.time() - start,
                user_id=user_id,
                configuration_snapshot={"model": self.model, "prompt_version": self.prompt_version},
            )

        # Possibly chunk long lyrics for context-aware aggregation
        if self._should_chunk(text):
            partials: List[Dict[str, Any]] = []
            for chunk in self._split_text(text):
                theme_cards = self.kb.retrieve_theme_cards(chunk, top_k=5)
                # Retrieve relevant framework rule chunks via RAG (if enabled)
                rag_chunks = retrieve_rules(chunk, top_k=6) or []
                system_prompt = self._build_system_prompt()
                user_prompt = self._build_user_prompt(title, artist, chunk, theme_cards, rag_chunks)
                raw = self._chat_completion(system_prompt, user_prompt)
                data = self._parse_or_repair_json(raw)
                partials.append(data if isinstance(data, dict) else {})
            data = self._merge_partials(partials)
        else:
            # Single-shot
            theme_cards = self.kb.retrieve_theme_cards(text, top_k=5)
            rag_chunks = retrieve_rules(text, top_k=6) or []
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(title, artist, text, theme_cards, rag_chunks)
            raw = self._chat_completion(system_prompt, user_prompt)
            data = self._parse_or_repair_json(raw)

        # Resolve scripture references via BSB API when available
        if isinstance(data, dict):
            scriptures = data.get("supporting_scripture") or []
            resolved = []
            for s in scriptures:
                ref = (s or {}).get("reference")
                if not ref:
                    continue
                fetched = self.bible.fetch(ref)
                if fetched:
                    resolved.append(
                        {
                            "reference": fetched["reference"],
                            "text": fetched["text"],
                            "theme": (s or {}).get("theme", ""),
                        }
                    )
                else:
                    # Keep reference only if not resolvable
                    resolved.append({"reference": ref, "theme": (s or {}).get("theme", "")})
            data["supporting_scripture"] = resolved

        # Validate/normalize JSON strictly via schema, then map
        valid = self._validate_or_default(data)
        analysis = self._to_analysis_result(title, artist, lyrics, valid)
        analysis.processing_time = time.time() - start
        analysis.configuration_snapshot = {
            "model": self.model,
            "prompt_version": self.prompt_version,
            "schema_version": "1.0",
            "kb_version": os.environ.get("KB_VERSION", "builtin-v1"),
        }
        analysis.user_id = user_id
        return analysis

    def analyze_songs_batch(self, songs_data: List[Dict[str, Any]]) -> List[AnalysisResult]:
        results: List[AnalysisResult] = []
        for song in songs_data:
            results.append(
                self.analyze_song(
                    song.get("title", ""),
                    song.get("artist", ""),
                    song.get("lyrics", ""),
                    song.get("user_id"),
                )
            )
        return results

    # Internal helpers
    def _build_system_prompt(self) -> str:
        # Inject compact rules from docs to ground the model
        rules = get_rules()
        pos = ", ".join([r.get("theme", "") for r in rules.get("positive_themes", [])][:25])
        neg = ", ".join([r.get("theme", "") for r in rules.get("negative_themes", [])][:25])
        return (
            "You are a theological music analyst. Classify lyrics per the Christian framework. "
            "Return ONLY strict JSON with fields: score, concern_level, biblical_themes[], supporting_scripture[], "
            "concerns[], narrative_voice, lament_filter_applied, doctrinal_clarity, confidence, needs_review, verdict. "
            "concern_level in [Very Low, Low, Medium, High]. narrative_voice in [artist, character, ambiguous]. "
            "doctrinal_clarity in [sound, thin, confused, null]. "
            f"Themes+ examples: {pos}. Themes- examples: {neg}. Use contextual BSB scripture; avoid repeating the same verse when context differs."
        )

    def _build_user_prompt(
        self,
        title: str,
        artist: str,
        lyrics: str,
        theme_cards: List[Dict[str, Any]],
        rag_chunks: List[Dict[str, Any]],
    ) -> str:
        schema = self._json_shape()
        examples = self._few_shot_examples()
        kb_str = json.dumps(theme_cards, ensure_ascii=False)
        rag_str = json.dumps(
            [
                {
                    "header": c.get("header", ""),
                    "source": c.get("source", ""),
                    "text": c.get("text", "")[:1000],
                }
                for c in (rag_chunks or [])
            ],
            ensure_ascii=False,
        )
        return (
            f"Song: {title} — {artist}\n\n"
            f"Lyrics:\n{lyrics[:8000]}\n\n"  # safety cap
            f"Theme cards (context): {kb_str}\n\n"
            f"Relevant Framework Rules (retrieved): {rag_str}\n\n"
            f"JSON schema (shape, not types): {json.dumps(schema)}\n"
            "Return ONLY valid JSON matching the schema."
            f"\n\nExamples:\n{examples}"
        )

    def _chat_completion(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "stream": False,
            "max_tokens": self.max_tokens,
        }
        t0 = time.time()
        try:
            try:
                current_app.logger.info(
                    f"[LLM] call -> model={self.model} max_tokens={self.max_tokens} sys={len(system_prompt)} usr={len(user_prompt)}"
                )
            except Exception:
                pass
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
        except Exception as e:
            try:
                current_app.logger.error(f"[LLM] call failed: {e}")
            except Exception:
                pass
            raise
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            current_app.logger.info(f"[LLM] ok in {time.time()-t0:.2f}s")
        except Exception:
            pass
        return content or "{}"

    def _parse_or_repair_json(self, text: str) -> Dict[str, Any]:
        # Try direct parse
        try:
            return json.loads(text)
        except Exception:
            pass
        # Extract largest JSON object between braces
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            snippet = match.group(0)
            try:
                return json.loads(snippet)
            except Exception:
                pass
        # Fallback
        return {
            "score": 50,
            "concern_level": "Unknown",
            "biblical_themes": [],
            "supporting_scripture": [],
            "concerns": [],
            "verdict": {"summary": "Unable to parse", "guidance": "Retry analysis"},
        }

    def _json_shape(self) -> Dict[str, Any]:
        return {
            "score": 0,
            "concern_level": "Very Low|Low|Medium|High|Critical|Unknown",
            "biblical_themes": [{"theme": "", "confidence": 0.0}],
            "supporting_scripture": [{"reference": "", "theme": ""}],
            "concerns": [
                {"category": "", "severity": "low|medium|high|critical", "explanation": ""}
            ],
            "narrative_voice": "artist|character|ambiguous",
            "lament_filter_applied": False,
            "doctrinal_clarity": "sound|thin|confused|null",
            "confidence": "high|medium|low",
            "needs_review": False,
            "verdict": {"summary": "", "guidance": ""},
        }

    # --- Strict schema ---
    class _Theme(BaseModel):
        theme: str
        confidence: confloat(ge=0, le=1) = 0.0

    class _Scripture(BaseModel):
        reference: str
        theme: str = ""
        text: Optional[str] = ""

    class _Concern(BaseModel):
        category: str
        severity: str = Field(pattern=r"^(low|medium|high|critical)$")
        explanation: str = ""

    class _Output(BaseModel):
        score: float = 50
        concern_level: str = Field(pattern=r"^(Very Low|Low|Medium|High|Critical|Unknown)$")
        biblical_themes: list  # of _Theme
        supporting_scripture: list  # of _Scripture
        concerns: list  # of _Concern
        narrative_voice: Optional[str] = None
        lament_filter_applied: Optional[bool] = None
        doctrinal_clarity: Optional[str] = None
        confidence: Optional[str] = None
        needs_review: Optional[bool] = None
        verdict: Dict[str, str] = Field(default_factory=dict)

    def _validate_or_default(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            model = LLMAnalyzer._Output.model_validate(data)
            return model.model_dump()
        except ValidationError:
            # Provide a safe default if validation fails
            return {
                "score": 50,
                "concern_level": "Unknown",
                "biblical_themes": [],
                "supporting_scripture": [],
                "concerns": [],
                "verdict": {"summary": "Unable to parse", "guidance": "Retry analysis"},
            }

    def _few_shot_examples(self) -> str:
        # Keep compact; illustrative only
        return (
            'Example (positive): {"score": 95, "concern_level": "Very Low", "biblical_themes": [{"theme": "Gospel Presentation", "confidence": 0.9}], '
            '"supporting_scripture": [{"reference": "John 3:16", "theme": "Gospel Presentation"}], "concerns": [], '
            '"verdict": {"summary": "Gospel-rich and edifying", "guidance": "Safe for repeated listening"}}\n'
            'Example (negative): {"score": 35, "concern_level": "High", "biblical_themes": [], "supporting_scripture": [], '
            '"concerns": [{"category": "Profanity", "severity": "high", "explanation": "Obscene language"}], '
            '"verdict": {"summary": "Spiritually harmful themes", "guidance": "Avoid for formation"}}'
        )

    def _to_analysis_result(
        self, title: str, artist: str, lyrics: str, data: Dict[str, Any]
    ) -> AnalysisResult:
        # Normalize fields with defaults
        score = float(data.get("score", 50))
        concern_level = str(data.get("concern_level", "Unknown"))
        themes = data.get("biblical_themes", []) or []
        scriptures = data.get("supporting_scripture", []) or []
        concerns = data.get("concerns", []) or []
        verdict = data.get("verdict", {}) or {}
        # Optional framework fields
        narrative_voice = data.get("narrative_voice")
        lament_filter_applied = data.get("lament_filter_applied")
        doctrinal_clarity = data.get("doctrinal_clarity")
        confidence = data.get("confidence")
        needs_review = data.get("needs_review")
        # Derive a simple formation risk from concern_level if not provided
        level_map = {
            "Very Low": "very_low",
            "Low": "low",
            "Medium": "high",
            "High": "critical",
            "Critical": "critical",
        }
        formation_risk = level_map.get(concern_level, None)

        # Compose AnalysisResult
        return AnalysisResult(
            title=title,
            artist=artist,
            lyrics_text=lyrics,
            processed_text=f"{title} {artist} {lyrics}".lower().strip()
            if lyrics
            else f"{title} {artist}".lower().strip(),
            biblical_analysis={
                "themes": themes,
                "supporting_scripture": scriptures,
                "educational_summary": verdict.get("summary", ""),
            },
            content_analysis={
                "concern_flags": [
                    {
                        "type": c.get("category", "General"),
                        "severity": c.get("severity", "medium"),
                        "description": c.get("explanation", ""),
                    }
                    for c in concerns
                ],
                "safety_assessment": {
                    "is_safe": concern_level in ("Very Low", "Low"),
                    "toxicity_score": 0.0,
                },
                "concern_level": concern_level,
            },
            scoring_results={
                "final_score": score,
                "quality_level": concern_level,
                "component_scores": {},
            },
            model_analysis={
                "framework": {
                    "narrative_voice": narrative_voice,
                    "lament_filter_applied": lament_filter_applied,
                    "doctrinal_clarity": doctrinal_clarity,
                    "confidence": confidence,
                    "needs_review": needs_review,
                    "formation_risk": formation_risk,
                    "verdict": verdict,
                }
            },
        )

    # Chunking/merge helpers
    def _should_chunk(self, text: str) -> bool:
        max_chars = int(os.environ.get("LLM_CHUNK_CHAR_LIMIT", "3500"))
        return len(text) > max_chars

    def _split_text(self, text: str) -> List[str]:
        max_chars = int(os.environ.get("LLM_CHUNK_CHAR_LIMIT", "3500"))
        chunks: List[str] = []
        current = []
        size = 0
        for line in text.splitlines():
            line = line.strip()
            if size + len(line) + 1 > max_chars and current:
                chunks.append("\n".join(current))
                current = []
                size = 0
            current.append(line)
            size += len(line) + 1
        if current:
            chunks.append("\n".join(current))
        return chunks or [text]

    def _merge_partials(self, partials: List[Dict[str, Any]]) -> Dict[str, Any]:
        severity_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        concern_rank = {
            "Very Low": 1,
            "Low": 2,
            "Medium": 3,
            "High": 4,
            "Critical": 5,
            "Unknown": 0,
        }

        agg_themes: Dict[str, float] = {}
        agg_concerns: Dict[str, Dict[str, Any]] = {}
        final_score = 0.0
        final_count = 0
        worst_concern_level = "Unknown"
        scriptures: List[Dict[str, Any]] = []
        verdicts: List[str] = []

        for p in partials:
            # themes
            for t in p.get("biblical_themes", []) or []:
                name = (t or {}).get("theme")
                conf = float((t or {}).get("confidence", 0.0))
                if not name:
                    continue
                agg_themes[name] = max(agg_themes.get(name, 0.0), conf)
            # concerns
            for c in p.get("concerns", []) or []:
                cat = (c or {}).get("category") or "General"
                sev = str((c or {}).get("severity", "medium")).lower()
                if cat not in agg_concerns or severity_rank.get(sev, 0) > severity_rank.get(
                    agg_concerns[cat].get("severity", "low"), 0
                ):
                    agg_concerns[cat] = {
                        "category": cat,
                        "severity": sev,
                        "explanation": (c or {}).get("explanation", ""),
                    }
            # score/concern level
            s = p.get("score")
            if isinstance(s, (int, float)):
                final_score += float(s)
                final_count += 1
            lvl = p.get("concern_level", "Unknown")
            if concern_rank.get(lvl, 0) > concern_rank.get(worst_concern_level, 0):
                worst_concern_level = lvl
            # scripture & verdict
            for sc in p.get("supporting_scripture", []) or []:
                if sc not in scriptures:
                    scriptures.append(sc)
            v = (p.get("verdict") or {}).get("summary")
            if v:
                verdicts.append(v)

        avg_score = (final_score / final_count) if final_count else 50.0
        merged = {
            "score": round(avg_score, 1),
            "concern_level": worst_concern_level,
            "biblical_themes": [
                {"theme": n, "confidence": c}
                for n, c in sorted(agg_themes.items(), key=lambda x: x[1], reverse=True)
            ],
            "supporting_scripture": scriptures,
            "concerns": list(agg_concerns.values()),
            "verdict": {"summary": "; ".join(verdicts[:2]), "guidance": ""},
        }
        return merged
