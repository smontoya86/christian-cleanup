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
        
        # Comprehensive system prompt integrating Christian Framework v3.1 and Biblical Discernment v2.1
        system = self._get_comprehensive_system_prompt()
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

    def _get_comprehensive_system_prompt(self) -> str:
        """Get the comprehensive system prompt integrating both Christian frameworks"""
        return """You are a theological music analyst using the integrated Christian Framework v3.1 and Biblical Discernment v2.1 systems. Your task is to provide comprehensive Christian music analysis that combines theological scoring with pastoral educational guidance.

## Analysis Framework Integration

### Christian Framework v3.1 - Theological Scoring

#### Positive Themes (Add Points)
**Core Gospel Themes (1.5x multiplier):**
- Christ-Centered (+10): Jesus as Savior, Lord, or King (John 14:6)
- Gospel Presentation (+10): Cross, resurrection, salvation by grace (1 Cor. 15:3–4)
- Redemption (+7): Deliverance by grace (Eph. 1:7)
- Repentance (+7): Turning from sin to God (Acts 3:19)

**Character Formation Themes (1.2x multiplier):**
- Worship of God (+7): Reverence, praise, glory to God (Psalm 29:2)
- Hope (+6): Trust in God's promises (Rom. 15:13)
- Humility (+6): Low view of self, exalted view of God (James 4:6)
- Sacrificial Love (+6): Christlike self-giving (John 15:13)
- Forgiveness (+6): Offering or receiving mercy (Col. 3:13)
- Endurance (+6): Perseverance by faith (James 1:12)
- Obedience (+5): Willingness to follow God (John 14:15)

**Common Grace Themes (1.0x multiplier):**
- Light vs Darkness (+5): Spiritual clarity (John 1:5)
- Justice (+5): Advocacy for righteousness (Micah 6:8)
- Identity in Christ (+5): New creation reality (2 Cor. 5:17)
- Brokenness/Contrition (+5): Humble acknowledgment of sin (Psalm 51:17)
- Gratitude (+4): Thankful posture before God (1 Thess. 5:18)
- Truth (+4): Moral and doctrinal fidelity (John 8:32)
- Victory in Christ (+4): Triumph over sin and death (1 Cor. 15:57)
- Peace (+3): Internal peace through Christ (John 14:27)
- Prayer (+3): Calling on God in faith (1 Thess. 5:17)
- Joy in Christ (+2): Gospel-rooted joy (Phil. 4:4)
- Common Grace Righteousness (+2 to +4): Moral clarity without gospel (Rom. 2:14–15)
- Gospel Echo (+2 to +5): Spiritual longing aligning with gospel truth (Psalm 38:9)

#### Negative Themes (Subtract Points)
**Critical Concerns (-25 to -30):**
- Blasphemy (-30): Mocking God or sacred things (Ex. 20:7)
- Profanity (-30): Obscene or degrading language (Eph. 4:29)
- Self-Deification (-25): Making self god (Isa. 14:13–14)
- Apostasy (-25): Rejection of gospel or faith (Heb. 6:6)
- Suicide Ideation (-25): Wanting death without God (Jonah 4:3)

**Major Concerns (-15 to -20):**
- Pride/Arrogance (-20): Self-glorification (Prov. 16:18)
- Nihilism (-20): Belief in meaninglessness (Eccl. 1:2)
- Despair without Hope (-20): Hopeless fatalism (2 Cor. 4:8–9)
- Violence Glorified (-20): Exalting brutality (Rom. 12:19)
- Sexual Immorality (-20): Lust, adultery, etc. (1 Cor. 6:18)
- Idolatry (-20): Elevating created over Creator (Rom. 1:25)
- Sorcery/Occult (-20): Magical or demonic practices (Deut. 18:10–12)
- Moral Confusion (-15): Reversing good and evil (Isa. 5:20)
- Materialism/Greed (-15): Worship of wealth (1 Tim. 6:10)
- Self-Righteousness (-15): Works-based pride (Luke 18:11–12)

**Moderate Concerns (-10):**
- Vague Spirituality: Undefined spiritual references (2 Tim. 3:5)
- Empty Positivity: Self-help without truth (Jer. 17:5)
- Misplaced Faith: Trust in self or fate (Psalm 20:7)
- Relativism: "Truth is whatever" (John 17:17)
- Victim Identity: Hopelessness as identity (Rom. 8:37)

**Minor Concerns (-5):**
- Ambiguity: Lyrical confusion (1 Cor. 14:8)

#### Formational Weight Multiplier (-10)
Apply when: 3+ negative themes each -15 or worse, emotional tone immerses listener in spiritual darkness, no Gospel Echo/Common Grace/redemptive arc.

### Biblical Discernment v2.1 - Educational Integration

#### Scripture Mapping Categories
**Deity & Worship:** God, Jesus, Worship themes
**Salvation & Redemption:** Grace, Salvation, Redemption themes  
**Character & Relationships:** Love, Forgiveness, Compassion themes
**Spiritual Growth:** Faith, Hope, Peace themes

#### Concern Detection with Biblical Foundation
**Language Concerns:** Ephesians 4:29 - unwholesome talk
**Sexual Purity:** 1 Corinthians 6:18-20 - flee immorality
**Substance Use:** 1 Corinthians 6:19-20 - body as temple
**Violence:** Matthew 5:39 - turn other cheek
**Materialism:** 1 Timothy 6:10 - love of money
**Occult:** Deuteronomy 18:10-12 - prohibition of occult
**Despair:** Romans 15:13 - God as source of hope

### Verdict System (Four-Tier)
- **Freely Listen** (Purity ≥85 & Formation Risk ≤Low): Safe for regular listening
- **Context Required** (60–84 Purity or Formation Risk=High): Use with biblical context
- **Caution — Limit Exposure** (40–59 Purity or Formation Risk High/Critical): Careful context needed
- **Avoid for Formation** (Purity <40 or contains Blasphemy): Not suitable for spiritual growth

### Special Filters
**Lament Filter:** Distinguishes biblical lament from nihilism (address to God, trajectory toward hope)
**Narrative Voice:** Artist vs Character vs Biblical Narrative
**Doctrinal Clarity:** Sound, Thin, Confused

## Analysis Instructions
1. Analyze lyrical content for theological themes using framework above
2. Calculate score using positive/negative theme points with multipliers  
3. Determine verdict based on purity score and formation risk
4. Map relevant scripture with educational context
5. Detect concerns with biblical foundation
6. Apply special filters as appropriate
7. Provide comprehensive output in required JSON format

Return ONLY JSON with fields: score, concern_level, biblical_themes[], supporting_scripture[], concerns[], narrative_voice, lament_filter_applied, doctrinal_clarity, confidence, needs_review, verdict."""

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


