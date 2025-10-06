from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Dict

import requests

from app.utils.circuit_breaker import CircuitBreakerOpenError, get_openai_circuit_breaker
from app.utils.openai_rate_limiter import get_rate_limiter
from app.utils.redis_cache import get_redis_cache

logger = logging.getLogger(__name__)

class RouterAnalyzer:
    """
    OpenAI-powered theological music analyzer using fine-tuned GPT-4o-mini.
    
    This analyzer uses the Christian Framework v3.1 to evaluate songs for
    biblical alignment, spiritual formation impact, and theological accuracy.
    """
    
    def __init__(self) -> None:
        # OpenAI API configuration
        self.base_url: str = os.environ.get(
            "LLM_API_BASE_URL", 
            "https://api.openai.com/v1"
        ).rstrip("/")
        
        # Fine-tuned GPT-4o-mini model
        self.model: str = os.environ.get(
            "OPENAI_MODEL",
            "ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav"
        )
        
        # API key (required)
        self.api_key: str = os.environ.get("OPENAI_API_KEY", "")
        if not self.api_key:
            logger.error("OPENAI_API_KEY environment variable is not set")
            raise ValueError("OPENAI_API_KEY is required for OpenAI API access")
        
        # Model parameters
        try:
            self.temperature: float = float(os.environ.get("LLM_TEMPERATURE", "0.2"))
        except Exception:
            self.temperature = 0.2
        try:
            self.max_tokens: int = int(os.environ.get("LLM_MAX_TOKENS", "2000"))
        except Exception:
            self.max_tokens = 2000
        try:
            self.timeout: float = float(os.environ.get("LLM_TIMEOUT", "60"))
        except Exception:
            self.timeout = 60.0
        
        # Rate limiter for API calls
        self.rate_limiter = get_rate_limiter()
        
        # Circuit breaker for graceful degradation
        self.circuit_breaker = get_openai_circuit_breaker()
        
        # Redis cache for fast lookups
        self.redis_cache = get_redis_cache()
        
        logger.info(f"✅ RouterAnalyzer initialized with OpenAI model: {self.model}")

    def analyze_song(self, title: str, artist: str, lyrics: str) -> Dict[str, Any]:
        """
        Analyze a song using the fine-tuned GPT-4o-mini model with caching, rate limiting, and graceful degradation.
        
        Args:
            title: Song title
            artist: Artist name
            lyrics: Full song lyrics
            
        Returns:
            Dictionary containing analysis results with Christian Framework v3.1 schema
        """
        # Cache hierarchy: Redis → Database → API
        lyrics_hash = hashlib.sha256(lyrics.encode('utf-8')).hexdigest()
        
        # 1. Check Redis cache first (fastest)
        redis_result = self.redis_cache.get_analysis(artist, title, lyrics_hash, self.model)
        if redis_result:
            logger.info(f"✅ Redis cache hit for '{title}' by {artist}")
            redis_result['analysis_quality'] = 'cached'
            return redis_result
        
        # 2. Check database cache (persistent)
        try:
            from app import create_app
            from app.models.models import AnalysisCache
            
            # Use app context for database operations
            app = create_app()
            with app.app_context():
                cached = AnalysisCache.find_cached_analysis(artist, title, lyrics_hash)
                
                if cached and cached.model_version == self.model:
                    logger.info(f"✅ Database cache hit for '{title}' by {artist}")
                    result = cached.analysis_result
                    result['cache_hit'] = True
                    result['cache_source'] = 'database'
                    result['analysis_quality'] = 'cached'
                    
                    # Backfill Redis cache
                    self.redis_cache.set_analysis(artist, title, lyrics_hash, self.model, result)
                    
                    return result
                elif cached:
                    logger.info("⚠️  Found cached analysis with different model version. Re-analyzing...")
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}. Proceeding with API call...")
        
        # Check circuit breaker state
        circuit_state = self.circuit_breaker.get_state()
        if circuit_state['state'] == 'open':
            logger.warning(
                f"⚠️  Circuit breaker is OPEN for '{title}' by {artist}. "
                f"Returning degraded response. Last failure: {circuit_state['last_failure_time']}"
            )
            return self._degraded_output(title, artist, "OpenAI API is temporarily unavailable")
        
        url = f"{self.base_url}/chat/completions"
        
        logger.info(f"🎵 Analyzing '{title}' by {artist} with {self.model}")

        system = self._get_comprehensive_system_prompt()
        user = f"Song: {title} — {artist}\n\nLyrics:\n{lyrics or ''}"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        
        # Add top_p only for non-fine-tuned models (fine-tuned models may not support it)
        if not self.model.startswith("ft:"):
            payload["top_p"] = 0.9
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Define the API call function for circuit breaker
        def make_api_call():
            """Wrapped API call for circuit breaker."""
            # Acquire rate limit permission (blocks if needed)
            self.rate_limiter.acquire()
            
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                resp.raise_for_status()
                
                # Success! Parse and return
                data = resp.json()
                content = (data.get("choices", [{}])[0] or {}).get("message", {}).get("content", "{}")
                parsed = self._parse_or_repair_json(content)
                normalized = self._normalize_output(parsed)
                normalized['cache_hit'] = False
                normalized['analysis_quality'] = 'full'  # Mark as full quality
                
                # Cache the result in both Redis and Database
                try:
                    # Cache in Redis (fast tier)
                    self.redis_cache.set_analysis(artist, title, lyrics_hash, self.model, normalized)
                    
                    # Cache in Database (persistent tier)
                    from app import create_app
                    from app.models.models import AnalysisCache
                    
                    app = create_app()
                    with app.app_context():
                        AnalysisCache.cache_analysis(
                            artist=artist,
                            title=title,
                            lyrics_hash=lyrics_hash,
                            analysis_result=normalized,
                            model_version=self.model
                        )
                        logger.info(f"💾 Cached analysis for '{title}' by {artist} (Redis + Database)")
                except Exception as e:
                    logger.warning(f"Failed to cache analysis: {e}")
                
                logger.info(f"✅ Analysis complete: Score={normalized.get('score')}, Verdict={normalized.get('verdict')}")
                return normalized
                
            except requests.exceptions.HTTPError as e:
                # Handle rate limit (429) with exponential backoff
                if e.response.status_code == 429:
                    logger.warning("⏳ Rate limited by OpenAI API")
                    raise  # Let circuit breaker handle it
                
                # Other HTTP errors
                logger.error(f"❌ HTTP error during analysis: {e.response.status_code} - {e.response.text}")
                raise
                
            finally:
                # Always release the rate limiter slot
                self.rate_limiter.release()
        
        # Execute through circuit breaker with retry logic
        for attempt in range(3):  # Max 3 attempts
            try:
                # Execute through circuit breaker
                return self.circuit_breaker.call(make_api_call)
                
            except CircuitBreakerOpenError as e:
                # Circuit opened during our request
                logger.error(f"❌ Circuit breaker opened: {e}")
                return self._degraded_output(title, artist, "Service protection engaged after repeated failures")
                
            except requests.exceptions.HTTPError as e:
                # Rate limit - retry with backoff
                if e.response.status_code == 429 and attempt < 2:
                    backoff_time = self.rate_limiter.handle_rate_limit_error(attempt)
                    logger.warning(f"⏳ Rate limited, retrying in {backoff_time:.1f}s...")
                    time.sleep(backoff_time)
                    continue  # Retry
                
                # Final attempt failed or other HTTP error
                logger.error(f"❌ HTTP error after {attempt + 1} attempts: {e}")
                return self._degraded_output(title, artist, f"Analysis service error: {e.response.status_code}")
                
            except Exception as e:
                logger.error(f"❌ Error during analysis (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt)  # Simple exponential backoff
                    continue
                return self._degraded_output(title, artist, "Unexpected error during analysis")
        
        # Should never reach here, but just in case
        return self._degraded_output(title, artist, "Maximum retry attempts exceeded")

    def _get_comprehensive_system_prompt(self) -> str:
        return """You are a fine-tuned theological music analyst using Christian Framework v3.1.

Apply your trained analysis patterns to evaluate this song. Remember:

## Critical Distinctions (Watch for Subtle Issues):

**Under-detected Concerns:**
- **Humanistic Philosophy**: Self-empowerment, "I can do anything," bootstrap mentality WITHOUT God
  * Flag when success/strength is attributed to self rather than God (Prov 3:5-6)
- **Idolatry**: Elevating ANYTHING above God (romance, success, self, relationships)
  * Flag when ultimate hope/meaning is in created things vs Creator (1 John 2:15-17)
  
**Over-detected (Apply Lament Filter):**
- **Despair/Mental Health**: DON'T flag authentic lament directed toward God (Psalms)
  * Only flag when despair has NO hope or is disconnected from God
- **Pride**: DON'T flag confidence in God's promises or biblical boldness
  * Only flag self-exaltation, boasting in self, arrogance

**Other Edge Cases:**
- **Common Grace**: Secular songs with biblical values (kindness, community, integrity) score 60-75
- **Vague Spirituality Cap**: God/spiritual language with unclear theology = MAX 45 score
- **Character Voice**: Story songs/cautionary tales get 30% penalty reduction
- **Scripture Required**: EVERY analysis needs 1-4 scripture references

## Scoring Guidelines (Use Full 0-100 Scale):
**Avoid clustering at exact boundaries (40, 45, 60, 85). Use the full range:**

- **85-100** (freely_listen): Biblically sound, theologically clear, spiritually edifying
- **70-84** (context_required): Helpful themes with minor theological gaps or ambiguity
- **60-69** (context_required): Mixed content with redeemable elements but requiring careful discernment
- **50-59** (caution_limit): **BORDERLINE** - Significant concerns BUT meaningful positive themes
  * Use 50-59 for songs with BOTH problems AND redeeming value
  * Example: Self-reliance message BUT genuine perseverance theme
  * Example: Vague spirituality BUT authentic hope and community
- **40-49** (caution_limit): More concerns than positive content, limited spiritual value
- **0-39** (avoid_formation): Harmful to spiritual formation, contrary to biblical teaching

## Formation Risk:
- **very_low**: Minimal spiritual concerns
- **low**: Minor concerns, generally safe
- **high**: Significant formation risks
- **critical**: Severe spiritual dangers

Return ONLY this JSON (no prose, no markdown):

{
  "score": 0-100,
  "verdict": "freely_listen|context_required|caution_limit|avoid_formation",
  "formation_risk": "very_low|low|high|critical",
  "narrative_voice": "artist|character|ambiguous",
  "lament_filter_applied": true/false,
  "themes_positive": [{"theme": "name", "points": int, "scripture": "ref"}],
  "themes_negative": [{"theme": "name", "penalty": int, "scripture": "ref"}],
  "concerns": [{"category": "name", "severity": "low|medium|high|critical", "explanation": "brief"}],
  "scripture_references": ["ref1", "ref2"],
  "analysis": "1-2 sentence summary of spiritual core and formation guidance"
}"""

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
            "formation_risk": data.get("formation_risk", "low"),
            "narrative_voice": data.get("narrative_voice", "artist"),
            "lament_filter_applied": data.get("lament_filter_applied", False),
            "themes_positive": data.get("themes_positive", []),
            "themes_negative": data.get("themes_negative", []),
            "concerns": data.get("concerns", []),
            "scripture_references": data.get("scripture_references", []),
            "analysis": data.get("analysis", ""),
        }
        return out

    def _degraded_output(self, title: str, artist: str, reason: str = "Service temporarily unavailable") -> Dict[str, Any]:
        """
        Return a degraded response when full analysis is unavailable.
        
        This provides basic feedback to users instead of a complete failure.
        Marked with analysis_quality='degraded' for tracking.
        """
        return {
            "score": 50,
            "verdict": "context_required",
            "formation_risk": "low",
            "narrative_voice": "artist",
            "lament_filter_applied": False,
            "themes_positive": [],
            "themes_negative": [],
            "concerns": ["Service_Degraded"],
            "scripture_references": ["Proverbs 3:5-6"],
            "analysis": f"⚠️ Analysis service temporarily unavailable. {reason}. "
                       f"Song '{title}' by {artist} requires manual review. "
                       f"Trust in the Lord with all your heart (Proverbs 3:5-6).",
            "analysis_quality": "degraded",  # Mark as degraded for tracking
            "cache_hit": False
        }
    
    def _default_output(self) -> Dict[str, Any]:
        return {
            "score": 50,
            "verdict": "context_required",
            "formation_risk": "low",
            "narrative_voice": "artist",
            "lament_filter_applied": False,
            "themes_positive": [],
            "themes_negative": [],
            "concerns": [],
            "scripture_references": [],
            "analysis": "",
            "analysis_quality": "full",  # Mark as full (default fallback)
            "cache_hit": False
        }

