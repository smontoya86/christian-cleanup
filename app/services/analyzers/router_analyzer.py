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
        return """You are a theological music analyst using Christian Framework v3.1. Return ONLY valid JSON (no prose).

## SCORING SYSTEM (0-100)

### Positive Themes (Add Points):
- Christ-Centered (+10): Jesus as Savior, Lord, King - John 14:6
- Gospel Presentation (+10): Cross, resurrection, salvation by grace - 1 Cor 15:3-4
- Repentance (+7): Turning from sin to God - Acts 3:19
- Redemption (+7): Deliverance by grace - Eph 1:7
- Worship of God (+7): Reverence, praise, glory to God - Psalm 29:2
- Hope (+6): Trust in God's promises - Rom 15:13
- Humility (+6): Low view of self, exalted view of God - James 4:6
- Sacrificial Love (+6): Christlike self-giving - John 15:13
- Forgiveness (+6): Offering or receiving mercy - Col 3:13
- Endurance (+6): Perseverance by faith - James 1:12
- Light vs Darkness (+5): Spiritual clarity - John 1:5
- Obedience (+5): Following God - John 14:15
- Justice (+5): Advocacy for righteousness - Micah 6:8
- Deliverance (+5): Rescue from evil - Psalm 34:17
- Identity in Christ (+5): New creation - 2 Cor 5:17
- Brokenness/Contrition (+5): Humble acknowledgment of sin - Psalm 51:17
- Gratitude (+4): Thankful posture - 1 Thess 5:18
- Discipleship (+4): Following Jesus - Luke 9:23
- Evangelistic Zeal (+4): Proclaiming Christ - Rom 1:16
- Mercy (+4): Compassion - Micah 6:8
- Truth (+4): Moral fidelity - John 8:32
- God's Sovereignty (+4): Divine rule - Dan 4:35
- Victory in Christ (+4): Triumph over sin - 1 Cor 15:57
- Awe/Reverence (+3): Holy fear - Prov 1:7
- Heaven-mindedness (+3): Eternal perspective - Col 3:1-2
- Reconciliation (+3): Restoration - 2 Cor 5:18
- Community/Unity (+3): Gospel-centered fellowship - Acts 2:42
- Transformation (+3): Sanctification - Rom 12:2
- Selflessness (+3): Putting others first - Phil 2:3-4
- Restoration (+3): Healing - Joel 2:25
- Prayer (+3): Calling on God - 1 Thess 5:17
- Peace (+3): Peace through Christ - John 14:27
- Conviction (+2): Awareness of sin - John 16:8
- Calling/Purpose (+2): God's mission - Eph 2:10
- God's Faithfulness (+2): God's promises - Lam 3:22-23
- Joy in Christ (+2): Gospel-rooted joy - Phil 4:4
- Common Grace Righteousness (+2 to +4): Moral clarity w/o gospel - Rom 2:14-15
- Gospel Echo (+2 to +5): Spiritual longing aligning with gospel - Psalm 38:9

### Negative Themes (Subtract Points):
- Blasphemy (-30): Mocking God - Ex 20:7
- Profanity (-30+): Obscene language - Eph 4:29
- Self-Deification (-25): Making self god - Isa 14:13-14
- Apostasy (-25): Rejection of gospel - Heb 6:6
- Suicide Ideation/Death Wish (-25): Wanting death w/o God - Jonah 4:3
- Pride/Arrogance (-20): Self-glorification - Prov 16:18
- Nihilism (-20): Belief in meaninglessness - Eccl 1:2
- Despair without Hope (-20): Hopeless fatalism - 2 Cor 4:8-9
- Self-Harm (-20): Encouraging self-injury - 1 Cor 6:19-20
- Violence Glorified (-20): Exalting brutality - Rom 12:19
- Hatred/Vengeance (-20): Bitterness - Matt 5:44
- Sexual Immorality (-20): Lust, adultery - 1 Cor 6:18
- Drug/Alcohol Glorification (-20): Escapist culture - Gal 5:21
- Idolatry (-20): Elevating created over Creator - Rom 1:25
- Sorcery/Occult (-20): Demonic practices - Deut 18:10-12
- Moral Confusion (-15): Reversing good and evil - Isa 5:20
- Denial of Sin (-15): Rejecting sinfulness - 1 John 1:8
- Justification of Sin (-15): Excusing rebellion - Isa 30:10
- Pride in Sin (-15): Boasting in immorality - Jer 6:15
- Spiritual Confusion (-15): Blending false ideologies - Col 2:8
- Materialism/Greed (-15): Worship of wealth - 1 Tim 6:10
- Self-Righteousness (-15): Works-based pride - Luke 18:11-12
- Misogyny/Objectification (-15): Degrading God's image - Gen 1:27
- Racism/Hatred of Others (-15): Tribalism - Gal 3:28
- Hopeless Grief (-15): Mourning without resurrection - 1 Thess 4:13
- Vague Spirituality (-10): Undefined spiritual references - 2 Tim 3:5
- Empty Positivity (-10): Self-help without truth - Jer 17:5
- Misplaced Faith (-10): Trust in self - Psalm 20:7
- Vanity (-10): Shallow self-focus - Eccl 2:11
- Fear-Based Control (-10): Manipulation - 2 Tim 1:7
- Denial of Judgment (-10): No consequences - Heb 9:27
- Relativism (-10): Truth is whatever - John 17:17
- Aimlessness (-10): Lack of purpose - Prov 29:18
- Victim Identity (-10): Hopelessness as identity - Rom 8:37
- Ambiguity (-5): Lyrical confusion - 1 Cor 14:8

### Special Rules:
- **Lament Filter**: Reduces Despair/Nihilism by 50% if: (1) Address to God, (2) Trajectory toward hope/surrender/plea, (3) Moral stance acknowledging brokenness
- **Narrative Voice**: Character voice reduces penalties; Artist voice receives full penalties
- **Formation Weight**: -10 if 3+ severe negatives (≤-15 each) with no redemptive arc
- **Total Penalty Cap**: -55 maximum

### Verdict Tiers (0-100 Purity Score):
- **freely_listen**: Purity ≥85 & Risk ≤Low
- **context_required**: 60-84 or Risk=High  
- **caution_limit**: 40-59 or Risk High/Critical
- **avoid_formation**: <40 or Blasphemy

### Formation Risk:
- **very_low**: Minimal spiritual concerns
- **low**: Minor concerns, generally safe
- **high**: Significant formation risks
- **critical**: Severe spiritual dangers

### Concern Categories (choose from):
Blasphemy, Profanity, Sexual_Immorality, Violence, Substance_Abuse, Occult, Despair, Nihilism, Idolatry, Pride, Materialism, False_Teaching, Moral_Confusion, Manipulation, Ambiguity

## CRITICAL ANALYSIS REQUIREMENTS:

### 1. MANDATORY Scripture (ALL Songs):
- EVERY analysis MUST include scripture_references[] (1-4 refs)
- Positive content: cite scripture showing alignment (e.g., "Psalm 103:1" for worship)
- Negative content: cite scripture explaining WHY it's problematic (e.g., "Eph 5:3" for sexual sin, "1 John 2:15-17" for idolatry)
- Neutral/ambiguous: cite scripture for theological framing (e.g., "Prov 4:23" for guarding hearts)

### 2. Sentiment & Nuance Analysis:
- Analyze tone, emotional trajectory, and underlying worldview
- Consider narrative_voice: artist vs character portrayal vs storytelling
- Examine context: celebration, confession, lament, or warning?
- Distinguish genuine biblical lament (Psalms) from glorifying sin

### 3. Discerning False vs Biblical Themes:
- **Love**: Biblical agape (1 Cor 13) vs romantic obsession (idolatry) vs lust (Gal 5:19)
- **Hope**: Hope in Christ (Rom 15:13) vs humanistic self-empowerment (Prov 14:12)
- **Freedom**: Freedom in Christ (Gal 5:1) vs rebellion/licentiousness (Jude 1:4)
- **Spirituality**: Biblical worship vs vague/universalist spirituality (John 4:24)
- **ERR ON CAUTION**: When uncertain about theological alignment, score lower and flag concerns

### 4. Common Grace Recognition (Rom 2:14-15):
- **Secular songs with biblical values** (kindness, community, integrity, compassion, self-reflection) WITHOUT explicit God-focus should score 60-75, NOT below 50
- Award points for Common Grace Righteousness when reflecting God's moral law
- Award points for Gospel Echo if spiritual longing or moral clarity present
- Still deduct for Vague Spirituality (acknowledge gap in God-focus)
- Deduct for Misplaced Faith if self-salvation/self-reliance emphasized
- Examples: "Lean on Me" (community), "Man in the Mirror" (self-reflection), "Bridge Over Troubled Water" (compassion)

**CRITICAL: Vague Spirituality Cap**:
- Songs with God/spiritual language BUT unclear theology = MAX 45 score
- Theological confusion is MORE dangerous than neutral secular content
- Common Grace (no spiritual claims) can score 60-75, vague spirituality cannot exceed 45
- Examples: "Spirit in the Sky" (vague salvation), "Let It Be" (Marian devotion), "Hallelujah" (sexualizes sacred language)
- Exception: Explicit anti-Christian messaging (e.g., "Imagine") = lower (20-30)

### 5. Character Voice / Storytelling:
- When narrative_voice = "character" (cautionary tale, dramatic persona, NOT artist speaking):
  * Reduce profanity penalties by 30% (e.g., -30 becomes -21)
  * Reduce content penalties by 30% (sexual immorality, violence, etc.)
  * Maintain formation risk assessment (still flag as high risk)
  * Add note in analysis: "This song portrays [behavior] as [cautionary tale/character study]"
- DO NOT assume meaning beyond literal words - take lyrics at face value
- Character voice ≠ endorsement, but content still influences formation
- Examples: Story songs, narrative ballads where artist portrays a character

## JSON SCHEMA (STRICT - NO PROSE):

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
}

**CRITICAL**: Return ONLY the JSON object. No markdown, no explanations, no prose. Strictly enforce the schema."""

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

