import logging
import os
import threading
from typing import Dict, List, Optional

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

from .analysis_result import AnalysisResult
from .rate_limit_monitor import rate_monitor

# Import RateLimitException locally to avoid circular imports
try:
    from app.services.exceptions import RateLimitException
except ImportError:
    # Fallback definition to avoid circular import issues
    class RateLimitException(Exception):
        def __init__(self, message, service_name=None, retry_after=None):
            super().__init__(message)
            self.service_name = service_name
            self.retry_after = retry_after


import time  # Added for batch processing timing

logger = logging.getLogger(__name__)


class HuggingFaceAnalyzer:
    """
    Free AI-powered song analysis using Hugging Face models.
    Uses local models with no API calls required.
    Supports both single song and batch processing for optimal performance.

    Implements singleton pattern to prevent multiple model loading operations.
    """

    # Singleton implementation
    _instance = None
    _lock = threading.Lock()
    _models_loaded = False

    def __new__(cls):
        """Singleton pattern - return same instance to prevent duplicate model loading"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(HuggingFaceAnalyzer, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls):
        """
        Get the singleton instance of HuggingFaceAnalyzer.
        This is the preferred way to get an analyzer instance.
        """
        return cls()

    @classmethod
    def reset_cache(cls):
        """
        Reset the singleton cache for testing purposes.
        This should only be used in tests.
        """
        with cls._lock:
            cls._instance = None
            cls._models_loaded = False

    def __init__(self):
        # Only initialize once for singleton pattern
        if self._models_loaded:
            return

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(
            f"Initializing HuggingFace analyzer on device: {self.device} (CACHED SINGLETON)"
        )

        # Batch processing configuration
        self.batch_size = 8 if self.device == "cuda" else 4  # Adjust based on GPU/CPU
        self.max_batch_wait_time = 2.0  # Maximum time to wait for batch completion
        # Concurrency limit for inference to prevent resource contention
        try:
            max_conc = int(os.environ.get("ANALYSIS_MAX_CONCURRENCY", "2"))
        except ValueError:
            max_conc = 2
        import threading

        self._concurrency_sem = threading.BoundedSemaphore(max(1, max_conc))

        # Christian theme keywords (expanded)
        self.christian_keywords = {
            "jesus",
            "christ",
            "god",
            "lord",
            "faith",
            "holy",
            "praise",
            "worship",
            "hallelujah",
            "amen",
            "blessed",
            "salvation",
            "heaven",
            "prayer",
            "bible",
            "savior",
            "grace",
            "mercy",
            "gospel",
            "church",
            "congregation",
            "divine",
            "almighty",
            "eternal",
            "sacred",
            "blessed",
            "righteous",
            "shepherd",
            "resurrection",
            "crucifixion",
            "trinity",
            "apostle",
            "disciple",
            "angel",
        }

        # Concern keywords (focused on actual profanity and inappropriate content)
        # Removed words that have legitimate Christian usage: "hell", "damn", "ass", "death", "kill"
        self.concern_keywords = {
            "shit",
            "fuck",
            "bitch",
            "bastard",
            "crap",
            "piss",
            "whore",
            "slut",
            "retard",
            "faggot",
            "nigger",
            "motherfucker",
            "asshole",
            "dickhead",
            "pussy",
            "cock",
            "penis",
            "sexual",
            "cocaine",
            "heroin",
            "marijuana",
            "weed",
            "drunk",
            "vodka",
            "whiskey",
            "racist",
            "nazi",
        }
        # Note: Removed "hell", "damn", "ass", "death", "kill", "murder", "hate", "sex",
        # "drugs", "alcohol", "beer", "violence", "suicide" as these can appear in
        # legitimate Christian/spiritual contexts

        # Load models only if HF is explicitly enabled or no LLM is reachable (acts as backup)
        hf_enabled = os.environ.get("ENABLE_HF_ANALYZER", "0") in ("1", "true", "True")
        use_llm = os.environ.get("USE_LLM_ANALYZER") in ("1", "true", "True") or bool(
            os.environ.get("LLM_API_BASE_URL")
        )
        if hf_enabled or not use_llm:
            self._load_models()
        else:
            # Defer HF heavy model loading; methods will fallback-safe but may be limited
            self._sentiment_analyzer = None
            self._safety_analyzer = None
            self._emotion_analyzer = None
            self._theme_analyzer = None

        # Mark models as loaded
        HuggingFaceAnalyzer._models_loaded = True

        logger.info("HuggingFace analyzer initialization complete - all models loaded successfully")

    def _load_models(self):
        """Load all models during initialization to avoid lazy loading delays and rate limits."""
        try:
            logger.info("Loading sentiment analysis model...")
            # Load tokenizer and model separately to use local_files_only
            tokenizer = AutoTokenizer.from_pretrained(
                "cardiffnlp/twitter-roberta-base-sentiment-latest", local_files_only=True
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                "cardiffnlp/twitter-roberta-base-sentiment-latest", local_files_only=True
            )
            self._sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model=model,
                tokenizer=tokenizer,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True,
            )
            logger.info("Sentiment analysis model loaded successfully")

            logger.info("Loading content safety model...")
            tokenizer = AutoTokenizer.from_pretrained("unitary/toxic-bert", local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(
                "unitary/toxic-bert", local_files_only=True
            )
            self._safety_analyzer = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True,
            )
            logger.info("Content safety model loaded successfully")

            logger.info("Loading emotion analysis model...")
            tokenizer = AutoTokenizer.from_pretrained(
                "j-hartmann/emotion-english-distilroberta-base", local_files_only=True
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                "j-hartmann/emotion-english-distilroberta-base", local_files_only=True
            )
            self._emotion_analyzer = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True,
            )
            logger.info("Emotion analysis model loaded successfully")

            # Optionally skip heavy zero-shot model in constrained/test environments
            if (
                os.environ.get("DISABLE_ZERO_SHOT", "0") in ("1", "true", "True")
                or os.environ.get("FLASK_ENV") == "testing"
            ):
                self._theme_analyzer = None
                logger.info("Skipping zero-shot theme classifier (disabled in env/testing)")
            else:
                logger.info("Loading zero-shot theme classification model...")
                # Load BART model for semantic theme detection (temporarily back to large model)
                self._theme_analyzer = pipeline(
                    "zero-shot-classification",
                    model="facebook/bart-large-mnli",  # Back to reliable large model while we optimize differently
                    device=0 if self.device == "cuda" else -1,
                )
                logger.info("Zero-shot theme classification model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load HuggingFace models: {e}")
            # If local_files_only fails, try without it (for initial download)
            logger.warning("Retrying model loading without local_files_only restriction...")
            try:
                self._load_models_with_download()
            except Exception as retry_error:
                logger.error(f"Model loading failed even with download: {retry_error}")
                raise RuntimeError(f"Cannot start analyzer without models: {e}")

    def _load_models_with_download(self):
        """Fallback method to load models with download capability."""
        logger.info("Loading sentiment analysis model (with download)...")
        self._sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            device=0 if self.device == "cuda" else -1,
            return_all_scores=True,
        )
        logger.info("Sentiment analysis model loaded successfully")

        logger.info("Loading content safety model (with download)...")
        self._safety_analyzer = pipeline(
            "text-classification",
            model="unitary/toxic-bert",
            device=0 if self.device == "cuda" else -1,
            return_all_scores=True,
        )
        logger.info("Content safety model loaded successfully")

        logger.info("Loading emotion analysis model (with download)...")
        self._emotion_analyzer = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            device=0 if self.device == "cuda" else -1,
            return_all_scores=True,
        )
        logger.info("Emotion analysis model loaded successfully")

        logger.info("Loading zero-shot theme classification model (with download)...")
        self._theme_analyzer = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=0 if self.device == "cuda" else -1,
        )
        logger.info("Zero-shot theme classification model loaded successfully")

    @property
    def sentiment_analyzer(self):
        """Return the pre-loaded sentiment analysis model"""
        return self._sentiment_analyzer

    @property
    def safety_analyzer(self):
        """Return the pre-loaded content safety model"""
        return self._safety_analyzer

    @property
    def emotion_analyzer(self):
        """Return the pre-loaded emotion analysis model"""
        return self._emotion_analyzer

    @property
    def theme_analyzer(self):
        """Return the pre-loaded zero-shot theme classification model"""
        return self._theme_analyzer

    # Legacy property for backward compatibility
    @property
    def content_classifier(self):
        """Legacy property - returns safety_analyzer for backward compatibility"""
        return self._safety_analyzer

    def _safe_truncate_text(self, text: str, max_tokens: int = 500) -> str:
        """
        Safely truncate text to ensure it fits within model token limits.
        Uses improved token estimation and handles edge cases.

        Args:
            text: Input text to truncate
            max_tokens: Maximum tokens (default 500, safe margin under 512)

        Returns:
            Truncated text that should fit within token limits
        """
        if not text:
            return ""

        # Quick check for very short text
        if len(text) <= 200:
            return text

        # Improved estimation: ~4 characters per token on average for English
        # But use 3.5 for safety with mixed content
        estimated_chars = int(max_tokens * 3.5)

        if len(text) <= estimated_chars:
            return text

        # Truncate to estimated character limit with extra safety margin
        safety_chars = int(estimated_chars * 0.9)  # 10% safety margin
        truncated = text[:safety_chars]

        # Try to truncate at sentence boundary first
        if ". " in truncated:
            last_sentence = truncated.rfind(". ")
            if last_sentence > safety_chars * 0.7:  # Don't lose too much content
                truncated = truncated[: last_sentence + 1]
        # Fall back to word boundary
        elif " " in truncated:
            last_space = truncated.rfind(" ")
            if last_space > safety_chars * 0.8:  # Don't lose too much text
                truncated = truncated[:last_space]

        return truncated

    def analyze_song(
        self, title: str, artist: str, lyrics: str, user_id: Optional[int] = None
    ) -> AnalysisResult:
        """
        Comprehensive song analysis using free Hugging Face models
        """
        # Check rate limits before processing
        identifier = f"user_{user_id}" if user_id else "anonymous"
        rate_check = rate_monitor.check_rate_limit(identifier)

        if not rate_check["allowed"]:
            logger.warning(f"Rate limit exceeded for {identifier}: {rate_check['reason']}")
            # Use proper RateLimitException instead of generic Exception
            raise RateLimitException(
                message=f"Rate limit exceeded: {rate_check['reason']}",
                service_name="HuggingFaceAnalyzer",
                retry_after=rate_check["retry_after"],
            )

        # Record the request
        rate_monitor.record_request(identifier)

        try:
            # Concurrency guard
            self._concurrency_sem.acquire()
            logger.info(f"Starting HuggingFace analysis for '{title}' by {artist}")

            # Combine all text for analysis
            full_text = f"{title} {artist} {lyrics}".lower().strip()

            # Safe token-based truncation for AI models
            all_text = self._safe_truncate_text(full_text)

            # 1. Enhanced theme detection (keyword + semantic)
            christian_themes = self._detect_enhanced_christian_themes(all_text)
            concern_flags = self._detect_concerns(all_text)

            # 2. AI-powered sentiment analysis
            sentiment_result = self._analyze_sentiment(all_text)

            # 3. AI-powered content safety
            safety_result = self._analyze_content_safety(all_text)

            # 4. AI-powered emotion detection
            emotion_result = self._analyze_emotions(all_text)

            # Calculate final score using enhanced Phase 4 scoring system
            scoring_metadata = self._calculate_final_score(
                christian_themes, concern_flags, sentiment_result, safety_result, emotion_result
            )
            final_score = scoring_metadata["final_score"]

            # Determine concern level
            concern_level = self._determine_concern_level(final_score, concern_flags, safety_result)

            # Generate Phase 4 structured verdict
            verdict_data = self._generate_structured_verdict(
                christian_themes, scoring_metadata, concern_level
            )

            # Generate explanation
            explanation = self._generate_explanation(
                christian_themes,
                concern_flags,
                sentiment_result,
                safety_result,
                emotion_result,
                final_score,
            )

            # Get supporting scripture for Christian themes
            supporting_scripture = self._get_supporting_scripture(christian_themes)

            logger.info(
                f"HuggingFace analysis completed for '{title}' - Score: {final_score}, Concern: {concern_level}"
            )

            # Create compatible AnalysisResult structure
            result = AnalysisResult(
                title=title,
                artist=artist,
                lyrics_text=lyrics,
                processed_text=all_text,
                content_analysis={
                    "concern_flags": concern_flags,
                    "safety_assessment": safety_result,
                    "total_penalty": sum(
                        5 for flag in concern_flags
                    ),  # Updated penalty (reduced from 15)
                },
                biblical_analysis={
                    "themes": christian_themes,  # Now includes enhanced theme structure
                    "supporting_scripture": supporting_scripture,
                    "biblical_themes_count": len(christian_themes),
                },
                model_analysis={
                    "sentiment": sentiment_result,
                    "emotions": emotion_result,
                    "content_safety": safety_result,
                },
                scoring_results={
                    "final_score": final_score,
                    "quality_level": concern_level,
                    "component_scores": {
                        "christian_themes": sum(
                            theme.get("points", 3) * theme.get("score", 0.5)
                            for theme in christian_themes
                        ),
                        "sentiment_score": sentiment_result.get("primary", {}).get("score", 0) * 5
                        if sentiment_result
                        else 0,
                        "safety_penalty": -25
                        if safety_result and safety_result.get("is_toxic")
                        else 0,
                        "concern_penalty": -sum(5 for flag in concern_flags),
                    },
                    "explanation": explanation,
                    # Phase 4 Enhanced Scoring Metadata
                    "base_theme_points": scoring_metadata.get("base_theme_points", 0),
                    "theological_weighting": scoring_metadata.get("theological_weighting", 1.0),
                    "formational_penalty": scoring_metadata.get("formational_penalty", 0),
                    # Phase 4 Structured Verdict Format
                    "verdict_summary": verdict_data.get("verdict_summary", ""),
                    "formation_guidance": verdict_data.get("formation_guidance", ""),
                },
            )

            return result

        except Exception as e:
            logger.error(f"Error in HuggingFace analysis: {str(e)}")
            # Fallback to keyword-based analysis
            return self._fallback_analysis(title, artist, lyrics)
        finally:
            # Always mark the request as complete to free up concurrent slots
            rate_monitor.complete_request(identifier)
            try:
                self._concurrency_sem.release()
            except Exception:
                pass

    def analyze_songs_batch(self, songs_data: List[Dict]) -> List[AnalysisResult]:
        """
        Analyze multiple songs in batch for optimal performance.

        Args:
            songs_data: List of dicts with keys: 'title', 'artist', 'lyrics', 'user_id' (optional)

        Returns:
            List of AnalysisResult objects corresponding to input songs
        """
        if not songs_data:
            return []

        # Concurrency guard for batch execution
        self._concurrency_sem.acquire()
        batch_size = min(len(songs_data), self.batch_size)
        logger.info(
            f"🚀 Starting batch analysis of {len(songs_data)} songs (batch_size: {batch_size})"
        )

        results = []
        start_time = time.time()

        # Process in batches
        for i in range(0, len(songs_data), batch_size):
            batch = songs_data[i : i + batch_size]
            batch_results = self._analyze_batch_internal(batch)
            results.extend(batch_results)

            # Log progress
            processed = min(i + batch_size, len(songs_data))
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            logger.info(
                f"📊 Batch progress: {processed}/{len(songs_data)} songs ({rate:.1f} songs/sec)"
            )

        total_time = time.time() - start_time
        final_rate = len(songs_data) / total_time if total_time > 0 else 0
        logger.info(
            f"✅ Batch analysis complete: {len(songs_data)} songs in {total_time:.1f}s ({final_rate:.1f} songs/sec)"
        )

        try:
            return results
        finally:
            try:
                self._concurrency_sem.release()
            except Exception:
                pass

    def _analyze_batch_internal(self, batch: List[Dict]) -> List[AnalysisResult]:
        """Internal batch processing with optimized model inference."""
        try:
            # Prepare all texts for batch processing
            batch_texts = []
            for song in batch:
                title = song.get("title", "")
                artist = song.get("artist", "")
                lyrics = song.get("lyrics", "")
                full_text = f"{title} {artist} {lyrics}".lower().strip()
                safe_text = self._safe_truncate_text(full_text)
                batch_texts.append(safe_text)

            # Batch AI model processing (most expensive operations)
            sentiment_results = self._analyze_sentiment_batch(batch_texts)
            safety_results = self._analyze_content_safety_batch(batch_texts)
            emotion_results = self._analyze_emotions_batch(batch_texts)
            theme_results = self._classify_core_gospel_themes_batch(batch_texts)

            # Process individual songs with batch results
            results = []
            for i, song in enumerate(batch):
                # Rate limiting check per song
                user_id = song.get("user_id")
                identifier = f"user_{user_id}" if user_id else "anonymous"
                rate_check = rate_monitor.check_rate_limit(identifier)

                if not rate_check["allowed"]:
                    logger.warning(f"Rate limit exceeded for {identifier}: {rate_check['reason']}")
                    raise RateLimitException(
                        message=f"Rate limit exceeded: {rate_check['reason']}",
                        service_name="HuggingFaceAnalyzer",
                        retry_after=rate_check["retry_after"],
                    )

                rate_monitor.record_request(identifier)

                try:
                    # Get batch results for this song
                    processed_text = batch_texts[i]
                    sentiment_result = sentiment_results[i] if i < len(sentiment_results) else None
                    safety_result = safety_results[i] if i < len(safety_results) else None
                    emotion_result = emotion_results[i] if i < len(emotion_results) else None
                    theme_result = theme_results[i] if i < len(theme_results) else []

                    # Enhanced theme detection (keyword + semantic from batch)
                    christian_themes = self._detect_enhanced_christian_themes_with_batch(
                        processed_text, theme_result
                    )
                    concern_flags = self._detect_concerns(processed_text)

                    # Calculate final score using enhanced Phase 4 scoring system
                    scoring_metadata = self._calculate_final_score(
                        christian_themes,
                        concern_flags,
                        sentiment_result,
                        safety_result,
                        emotion_result,
                    )
                    final_score = scoring_metadata["final_score"]

                    # Determine concern level
                    concern_level = self._determine_concern_level(
                        final_score, concern_flags, safety_result
                    )

                    # Generate Phase 4 structured verdict
                    verdict_data = self._generate_structured_verdict(
                        christian_themes, scoring_metadata, concern_level
                    )

                    # Generate explanation
                    explanation = self._generate_explanation(
                        christian_themes,
                        concern_flags,
                        sentiment_result,
                        safety_result,
                        emotion_result,
                        final_score,
                    )

                    # Get supporting scripture for Christian themes
                    supporting_scripture = self._get_supporting_scripture(christian_themes)

                    # Create compatible AnalysisResult structure
                    result = AnalysisResult(
                        title=song.get("title", ""),
                        artist=song.get("artist", ""),
                        lyrics_text=song.get("lyrics", ""),
                        processed_text=processed_text,
                        content_analysis={
                            "concern_flags": concern_flags,
                            "safety_assessment": safety_result,
                            "total_penalty": sum(5 for flag in concern_flags),
                        },
                        biblical_analysis={
                            "themes": christian_themes,
                            "supporting_scripture": supporting_scripture,
                            "biblical_themes_count": len(christian_themes),
                        },
                        model_analysis={
                            "sentiment": sentiment_result,
                            "emotions": emotion_result,
                            "content_safety": safety_result,
                        },
                        scoring_results={
                            "final_score": final_score,
                            "quality_level": concern_level,
                            "component_scores": {
                                "christian_themes": sum(
                                    theme.get("points", 3) * theme.get("score", 0.5)
                                    for theme in christian_themes
                                ),
                                "sentiment_score": sentiment_result.get("primary", {}).get(
                                    "score", 0
                                )
                                * 5
                                if sentiment_result
                                else 0,
                                "safety_penalty": -25
                                if safety_result and safety_result.get("is_toxic")
                                else 0,
                                "concern_penalty": -sum(5 for flag in concern_flags),
                            },
                            "explanation": explanation,
                            "base_theme_points": scoring_metadata.get("base_theme_points", 0),
                            "theological_weighting": scoring_metadata.get(
                                "theological_weighting", 1.0
                            ),
                            "formational_penalty": scoring_metadata.get("formational_penalty", 0),
                            "verdict_summary": verdict_data.get("verdict_summary", ""),
                            "formation_guidance": verdict_data.get("formation_guidance", ""),
                        },
                    )

                    results.append(result)

                except Exception as e:
                    logger.error(f"Error in batch song analysis: {str(e)}")
                    # Fallback to individual analysis for this song
                    fallback_result = self._fallback_analysis(
                        song.get("title", ""), song.get("artist", ""), song.get("lyrics", "")
                    )
                    results.append(fallback_result)
                finally:
                    rate_monitor.complete_request(identifier)

            return results

        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            # Fallback to individual processing
            return [
                self.analyze_song(
                    song.get("title", ""),
                    song.get("artist", ""),
                    song.get("lyrics", ""),
                    song.get("user_id"),
                )
                for song in batch
            ]

    def _analyze_sentiment_batch(self, texts: List[str]) -> List[Optional[Dict]]:
        """Batch sentiment analysis for improved performance."""
        if not self.sentiment_analyzer or not texts:
            return [None] * len(texts)

        try:
            # Process all texts at once
            results = self.sentiment_analyzer(texts)

            # Convert to individual results
            processed_results = []
            for result in results:
                if result:
                    processed_results.append(
                        {
                            "scores": result if isinstance(result, list) else [result],
                            "primary": max(
                                result if isinstance(result, list) else [result],
                                key=lambda x: x["score"],
                            ),
                        }
                    )
                else:
                    processed_results.append(None)

            return processed_results

        except Exception as e:
            logger.warning(f"Batch sentiment analysis failed: {e}")
            return [None] * len(texts)

    def _analyze_content_safety_batch(self, texts: List[str]) -> List[Optional[Dict]]:
        """Batch content safety analysis for improved performance."""
        if not self.safety_analyzer or not texts:
            return [None] * len(texts)

        try:
            # Process all texts at once
            results = self.safety_analyzer(texts)

            # Convert to individual results
            processed_results = []
            for result in results:
                if result:
                    processed_results.append(
                        {
                            "scores": result if isinstance(result, list) else [result],
                            "is_toxic": any(
                                score["score"] > 0.5 and "toxic" in score["label"].lower()
                                for score in (result if isinstance(result, list) else [result])
                            ),
                        }
                    )
                else:
                    processed_results.append(None)

            return processed_results

        except Exception as e:
            logger.warning(f"Batch content safety analysis failed: {e}")
            return [None] * len(texts)

    def _analyze_emotions_batch(self, texts: List[str]) -> List[Optional[Dict]]:
        """Batch emotion analysis for improved performance."""
        if not self.emotion_analyzer or not texts:
            return [None] * len(texts)

        try:
            # Process all texts at once
            results = self.emotion_analyzer(texts)

            # Convert to individual results
            processed_results = []
            for result in results:
                if result:
                    processed_results.append(
                        {
                            "scores": result if isinstance(result, list) else [result],
                            "primary": max(
                                result if isinstance(result, list) else [result],
                                key=lambda x: x["score"],
                            ),
                        }
                    )
                else:
                    processed_results.append(None)

            return processed_results

        except Exception as e:
            logger.warning(f"Batch emotion analysis failed: {e}")
            return [None] * len(texts)

    def _classify_core_gospel_themes_batch(self, texts: List[str]) -> List[List[Dict]]:
        """Batch zero-shot theme classification for improved performance."""
        if not self.theme_analyzer or not texts:
            return [[] for _ in texts]

        try:
            # Define Phase 1 + Phase 2 + Phase 3 themes for classification
            gospel_theme_labels = [
                # Phase 1: Core Gospel Themes (5 themes)
                "Christ-centered worship - Jesus as Savior, Lord, or King",
                "Gospel presentation - Cross, resurrection, salvation by grace",
                "Redemption and deliverance - Grace and mercy from sin",
                "Sacrificial love - Christlike self-giving and laying down life",
                "Light versus darkness - Spiritual victory and overcoming evil",
                # Phase 2: Character & Spiritual Themes (10 themes)
                "Perseverance and endurance - Faith through trials and spiritual growth",
                "Obedience to God - Willingness to follow divine commands and will",
                "Justice and righteousness - Advocacy for truth and biblical morality",
                "Mercy and compassion - Showing kindness and grace to others",
                "Biblical truth and doctrine - Sound teaching and theological fidelity",
                "Identity in Christ - New creation reality and child of God status",
                "Victory in Christ - Triumph over sin, death, and spiritual forces",
                "Gratitude and thanksgiving - Thankful heart and praise to God",
                "Discipleship and following Jesus - Spiritual growth and commitment",
                "Evangelism and mission - Sharing the gospel and Great Commission",
                "Worship and praise - Adoration and reverence for God",
                "Faith and trust - Belief and confidence in God",
                "Hope in God - Confident expectation and future assurance",
                "Divine love - God's love and Christian love for others",
                "Peace in Christ - Inner peace and harmony through God",
                "Prayer and communion - Communication and relationship with God",
                # Phase 3: Negative Themes (15+ themes) - HIGH SEVERITY
                "Blasphemy and mocking God - Deliberate disrespect toward the sacred",
                "Self-deification and pride - Making oneself god or ultimate authority",
                "Apostasy and faith rejection - Abandoning or rejecting Christian beliefs",
                "Suicide ideation and death wish - Wanting death without hope in God",
                # Phase 3: Negative Themes - MEDIUM SEVERITY
                "Pride and arrogance - Self-glorification and superiority complex",
                "Idolatry and false worship - Elevating created things over Creator",
                "Occult practices and sorcery - Witchcraft, magic, and demonic spirituality",
                "Sexual immorality and lust - Adultery, objectification, and moral compromise",
                "Glorification of violence - Celebrating brutality and harm to others",
                "Hatred and vengeance - Bitterness, retaliation, and malice toward others",
                # Phase 3: Negative Themes - LOWER SEVERITY
                "Materialism and greed - Worship of wealth and material possessions",
                "Self-righteousness and works-based pride - Earning salvation through deeds",
                "Moral confusion and relativism - Reversing good and evil standards",
                "Vague spirituality without foundation - Generic spiritual concepts without Christ",
                "Empty positivity and self-help - Motivation without biblical truth",
            ]

            # Process all texts in batch
            batch_results = []
            for text in texts:
                try:
                    safe_text = self._safe_truncate_text(text, max_tokens=400)
                    result = self.theme_analyzer(safe_text, gospel_theme_labels)
                    batch_results.append(result)
                except Exception as e:
                    logger.warning(f"Individual theme classification failed: {e}")
                    batch_results.append({"labels": [], "scores": []})

            # Convert results to our theme format
            all_themes = []
            for results in batch_results:
                themes = self._convert_theme_results_to_format(results)
                all_themes.append(themes)

            return all_themes

        except Exception as e:
            logger.warning(f"Batch theme classification failed: {e}")
            return [[] for _ in texts]

    def _convert_theme_results_to_format(self, results) -> List[Dict]:
        """Convert theme classification results to our standard format."""
        themes = []

        # Handle different result formats from zero-shot classifier
        if isinstance(results, dict):
            labels = results.get("labels", [])
            scores = results.get("scores", [])
        elif isinstance(results, list) and len(results) > 0:
            labels = [item.get("label", "") for item in results]
            scores = [item.get("score", 0.0) for item in results]
        else:
            return themes

        for label, score in zip(labels, scores):
            # Only include themes with reasonable confidence
            if score > 0.3:
                # Map to simplified theme names and point values
                theme_info = self._map_theme_label_to_info(label)
                if theme_info:
                    themes.append(
                        {
                            "theme": theme_info["name"],
                            "score": float(score),
                            "detection_method": "semantic",
                            "category": theme_info["category"],
                            "points": theme_info["points"],
                        }
                    )

        return themes

    def _map_theme_label_to_info(self, label: str) -> Optional[Dict]:
        """Map theme label to theme info with name, category, and points."""
        theme_mapping = {
            # Phase 1: Core Gospel Themes
            "Christ-centered worship": {
                "name": "Christ-centered",
                "points": 10,
                "category": "core_gospel",
            },
            "Gospel presentation": {
                "name": "Gospel presentation",
                "points": 10,
                "category": "core_gospel",
            },
            "Redemption and deliverance": {
                "name": "Redemption",
                "points": 7,
                "category": "core_gospel",
            },
            "Sacrificial love": {
                "name": "Sacrificial love",
                "points": 6,
                "category": "core_gospel",
            },
            "Light versus darkness": {
                "name": "Light vs darkness",
                "points": 5,
                "category": "core_gospel",
            },
            # Phase 2: Character & Spiritual Themes
            "Perseverance and endurance": {
                "name": "Endurance",
                "points": 6,
                "category": "character_spiritual",
            },
            "Obedience to God": {
                "name": "Obedience",
                "points": 5,
                "category": "character_spiritual",
            },
            "Justice and righteousness": {
                "name": "Justice",
                "points": 5,
                "category": "character_spiritual",
            },
            "Mercy and compassion": {
                "name": "Mercy",
                "points": 4,
                "category": "character_spiritual",
            },
            "Biblical truth and doctrine": {
                "name": "Truth",
                "points": 4,
                "category": "character_spiritual",
            },
            "Identity in Christ": {
                "name": "Identity in Christ",
                "points": 5,
                "category": "character_spiritual",
            },
            "Victory in Christ": {
                "name": "Victory in Christ",
                "points": 4,
                "category": "character_spiritual",
            },
            "Gratitude and thanksgiving": {
                "name": "Gratitude",
                "points": 4,
                "category": "character_spiritual",
            },
            "Discipleship and following Jesus": {
                "name": "Discipleship",
                "points": 4,
                "category": "character_spiritual",
            },
            "Evangelism and mission": {
                "name": "Evangelistic Zeal",
                "points": 4,
                "category": "character_spiritual",
            },
            "Worship and praise": {
                "name": "Worship",
                "points": 4,
                "category": "character_spiritual",
            },
            "Faith and trust": {"name": "Faith", "points": 4, "category": "character_spiritual"},
            "Hope in God": {"name": "Hope", "points": 4, "category": "character_spiritual"},
            "Divine love": {"name": "Love", "points": 4, "category": "character_spiritual"},
            "Peace in Christ": {"name": "Peace", "points": 4, "category": "character_spiritual"},
            "Prayer and communion": {
                "name": "Prayer",
                "points": 4,
                "category": "character_spiritual",
            },
            # Phase 3: Negative Themes - HIGH SEVERITY
            "Blasphemy and mocking God": {
                "name": "Blasphemy",
                "points": -30,
                "category": "negative",
            },
            "Self-deification and pride": {
                "name": "Self-deification",
                "points": -25,
                "category": "negative",
            },
            "Apostasy and faith rejection": {
                "name": "Apostasy",
                "points": -25,
                "category": "negative",
            },
            "Suicide ideation and death wish": {
                "name": "Suicide ideation",
                "points": -25,
                "category": "negative",
            },
            # Phase 3: Negative Themes - MEDIUM SEVERITY
            "Pride and arrogance": {"name": "Pride", "points": -20, "category": "negative"},
            "Idolatry and false worship": {
                "name": "Idolatry",
                "points": -20,
                "category": "negative",
            },
            "Occult practices and sorcery": {
                "name": "Occult",
                "points": -20,
                "category": "negative",
            },
            "Sexual immorality and lust": {
                "name": "Sexual immorality",
                "points": -20,
                "category": "negative",
            },
            "Glorification of violence": {
                "name": "Violence",
                "points": -20,
                "category": "negative",
            },
            "Hatred and vengeance": {"name": "Hatred", "points": -20, "category": "negative"},
            # Phase 3: Negative Themes - LOWER SEVERITY
            "Materialism and greed": {"name": "Materialism", "points": -15, "category": "negative"},
            "Self-righteousness and works-based pride": {
                "name": "Self-righteousness",
                "points": -15,
                "category": "negative",
            },
            "Moral confusion and relativism": {
                "name": "Moral confusion",
                "points": -15,
                "category": "negative",
            },
            "Vague spirituality without foundation": {
                "name": "Vague spirituality",
                "points": -10,
                "category": "negative",
            },
            "Empty positivity and self-help": {
                "name": "Empty positivity",
                "points": -10,
                "category": "negative",
            },
        }

        # Find matching theme
        for key, value in theme_mapping.items():
            if key.lower() in label.lower():
                return value

        return None

    def _detect_enhanced_christian_themes_with_batch(
        self, text: str, batch_themes: List[Dict]
    ) -> List[Dict]:
        """Enhanced theme detection combining keywords and batch semantic results."""
        # Start with keyword-based detection
        keyword_themes = self._detect_christian_themes(text)

        # Convert keyword themes to enhanced format
        all_themes = []
        for theme in keyword_themes:
            all_themes.append(
                {
                    "theme": theme,
                    "score": 1.0,
                    "detection_method": "keyword",
                    "category": "general_christian",
                    "points": 3,  # Default points for keyword themes
                }
            )

        # Add batch semantic themes
        all_themes.extend(batch_themes)

        return all_themes

    def _detect_christian_themes(self, text: str) -> List[str]:
        """Detect Christian themes using keyword matching"""
        found_themes = []
        logger.debug(f"🔍 Detecting Christian themes (length: {len(text)})")

        for keyword in self.christian_keywords:
            if keyword in text:
                found_themes.append(keyword)
                logger.info(f"✅ Found Christian theme: '{keyword}'")

        logger.info(f"🎯 Total Christian themes found: {len(found_themes)} - {found_themes}")
        return found_themes

    def _detect_concerns(self, text: str) -> List[Dict]:
        """Detect concerning content using keyword matching"""
        concern_flags = []
        found_concerns = []

        logger.debug(f"⚠️ Detecting concerns (length: {len(text)})")

        for keyword in self.concern_keywords:
            if keyword in text:
                found_concerns.append(keyword)
                logger.info(f"🚨 Found concerning keyword: '{keyword}'")

        if found_concerns:
            concern_flags.append(
                {"type": "explicit_language", "confidence": 0.9, "keywords": found_concerns}
            )

        logger.info(f"⚠️ Total concern flags: {len(concern_flags)} - Keywords: {found_concerns}")
        return concern_flags

    def _detect_enhanced_christian_themes(self, text: str) -> List[Dict]:
        """
        Enhanced Christian theme detection using both keywords and zero-shot classification.

        Detects the 5 Core Gospel Themes:
        - Christ-Centered: Jesus as Savior, Lord, or King (+10 points)
        - Gospel Presentation: Cross, resurrection, salvation by grace (+10 points)
        - Redemption: Deliverance by grace (+7 points)
        - Sacrificial Love: Christlike self-giving (+6 points)
        - Light vs Darkness: Spiritual clarity and contrast (+5 points)
        """
        logger.info(f"🔍 Enhanced theme detection for text (length: {len(text)})")

        # 1. Start with keyword-based detection (fast baseline)
        keyword_themes = self._detect_christian_themes(text)

        # 2. Add zero-shot semantic classification for Core Gospel Themes
        core_gospel_themes = self._classify_core_gospel_themes(text)

        # 3. Combine and deduplicate results
        all_themes = []

        # Add keyword themes as themes with scores
        for theme in keyword_themes:
            all_themes.append(
                {
                    "theme": theme,
                    "score": 1.0,  # High confidence for explicit keywords
                    "detection_method": "keyword",
                    "category": "general_christian",
                }
            )

        # Add semantic themes
        all_themes.extend(core_gospel_themes)

        logger.info(f"🎯 Enhanced themes detected: {len(all_themes)} total themes")
        return all_themes

    def _classify_core_gospel_themes(self, text: str) -> List[Dict]:
        """Use zero-shot classification to detect Core Gospel Themes."""
        if not self.theme_analyzer:
            return []

        try:
            # Define Phase 1 + Phase 2 + Phase 3 themes for classification
            gospel_theme_labels = [
                # Phase 1: Core Gospel Themes (5 themes)
                "Christ-centered worship - Jesus as Savior, Lord, or King",
                "Gospel presentation - Cross, resurrection, salvation by grace",
                "Redemption and deliverance - Grace and mercy from sin",
                "Sacrificial love - Christlike self-giving and laying down life",
                "Light versus darkness - Spiritual victory and overcoming evil",
                # Phase 2: Character & Spiritual Themes (10 themes)
                "Perseverance and endurance - Faith through trials and spiritual growth",
                "Obedience to God - Willingness to follow divine commands and will",
                "Justice and righteousness - Advocacy for truth and biblical morality",
                "Mercy and compassion - Showing kindness and grace to others",
                "Biblical truth and doctrine - Sound teaching and theological fidelity",
                "Identity in Christ - New creation reality and child of God status",
                "Victory in Christ - Triumph over sin, death, and spiritual forces",
                "Gratitude and thanksgiving - Thankful heart and praise to God",
                "Discipleship and following Jesus - Spiritual growth and commitment",
                "Evangelism and mission - Sharing the gospel and Great Commission",
                "Worship and praise - Adoration and reverence for God",
                "Faith and trust - Belief and confidence in God",
                "Hope in God - Confident expectation and future assurance",
                "Divine love - God's love and Christian love for others",
                "Peace in Christ - Inner peace and harmony through God",
                "Prayer and communion - Communication and relationship with God",
                # Phase 3: Negative Themes (15+ themes) - HIGH SEVERITY
                "Blasphemy and mocking God - Deliberate disrespect toward the sacred",
                "Self-deification and pride - Making oneself god or ultimate authority",
                "Apostasy and faith rejection - Abandoning or rejecting Christian beliefs",
                "Suicide ideation and death wish - Wanting death without hope in God",
                # Phase 3: Negative Themes - MEDIUM SEVERITY
                "Pride and arrogance - Self-glorification and superiority complex",
                "Idolatry and false worship - Elevating created things over Creator",
                "Occult practices and sorcery - Witchcraft, magic, and demonic spirituality",
                "Sexual immorality and lust - Adultery, objectification, and moral compromise",
                "Glorification of violence - Celebrating brutality and harm to others",
                "Hatred and vengeance - Bitterness, retaliation, and malice toward others",
                # Phase 3: Negative Themes - LOWER SEVERITY
                "Materialism and greed - Worship of wealth and material possessions",
                "Self-righteousness and works-based pride - Earning salvation through deeds",
                "Moral confusion and relativism - Reversing good and evil standards",
                "Vague spirituality without foundation - Generic spiritual concepts without Christ",
                "Empty positivity and self-help - Motivation without biblical truth",
            ]

            # Safe truncation for the classifier
            safe_text = self._safe_truncate_text(text, max_tokens=400)

            # Perform zero-shot classification
            results = self.theme_analyzer(safe_text, gospel_theme_labels)

            # Convert results to our theme format - handle different result formats
            themes = []

            # Debug: log the structure type only (avoid large payloads)
            logger.debug(f"🔬 Zero-shot results type: {type(results)}")

            # Handle different result formats from zero-shot classifier
            if isinstance(results, dict):
                # Standard format: {'labels': [...], 'scores': [...]}
                labels = results.get("labels", [])
                scores = results.get("scores", [])
            elif isinstance(results, list) and len(results) > 0:
                # Alternative format: [{'label': '...', 'score': ...}, ...]
                labels = [item.get("label", "") for item in results]
                scores = [item.get("score", 0.0) for item in results]
            else:
                logger.warning(f"Unexpected zero-shot result format: {type(results)}")
                return themes

            for i, (label, score) in enumerate(zip(labels, scores)):
                # Only include themes with reasonable confidence
                if score > 0.3:  # 30% confidence threshold
                    # Map to simplified theme names and point values (Phase 1 + Phase 2)
                    theme_mapping = {
                        # Phase 1: Core Gospel Themes
                        "Christ-centered worship": {"name": "Christ-centered", "points": 10},
                        "Gospel presentation": {"name": "Gospel presentation", "points": 10},
                        "Redemption and deliverance": {"name": "Redemption", "points": 7},
                        "Sacrificial love": {"name": "Sacrificial love", "points": 6},
                        "Light versus darkness": {"name": "Light vs darkness", "points": 5},
                        "Light overcoming darkness": {
                            "name": "Light vs darkness",
                            "points": 5,
                        },  # Additional mapping
                        # Phase 2: Character & Spiritual Themes
                        "Perseverance and endurance": {"name": "Endurance", "points": 6},
                        "Faith through trials": {
                            "name": "Endurance",
                            "points": 6,
                        },  # Additional mapping
                        "Spiritual perseverance": {
                            "name": "Endurance",
                            "points": 6,
                        },  # Additional mapping
                        "Obedience to God": {"name": "Obedience", "points": 5},
                        "Submission to divine will": {
                            "name": "Obedience",
                            "points": 5,
                        },  # Additional mapping
                        "Following Gods commands": {
                            "name": "Obedience",
                            "points": 5,
                        },  # Additional mapping
                        "Justice and righteousness": {"name": "Justice", "points": 5},
                        "Defending the oppressed": {
                            "name": "Justice",
                            "points": 5,
                        },  # Additional mapping
                        "Gods justice": {"name": "Justice", "points": 5},  # Additional mapping
                        "Mercy and compassion": {"name": "Mercy", "points": 4},
                        "Showing kindness": {"name": "Mercy", "points": 4},  # Additional mapping
                        "Gods mercy": {"name": "Mercy", "points": 4},  # Additional mapping
                        "Biblical truth and doctrine": {"name": "Truth", "points": 4},
                        "Gods Word as truth": {"name": "Truth", "points": 4},  # Additional mapping
                        "Sound doctrine": {"name": "Truth", "points": 4},  # Additional mapping
                        "Identity in Christ": {"name": "Identity in Christ", "points": 5},
                        "New creation in Christ": {
                            "name": "Identity in Christ",
                            "points": 5,
                        },  # Additional mapping
                        "Child of God identity": {
                            "name": "Identity in Christ",
                            "points": 5,
                        },  # Additional mapping
                        "Victory in Christ": {"name": "Victory in Christ", "points": 4},
                        "Triumph over sin and death": {
                            "name": "Victory in Christ",
                            "points": 4,
                        },  # Additional mapping
                        "Spiritual victory": {
                            "name": "Victory in Christ",
                            "points": 4,
                        },  # Additional mapping (updated from Light vs darkness)
                        "Gratitude and thanksgiving": {"name": "Gratitude", "points": 4},
                        "Thankful heart": {"name": "Gratitude", "points": 4},  # Additional mapping
                        "Counting blessings": {
                            "name": "Gratitude",
                            "points": 4,
                        },  # Additional mapping
                        "Discipleship and following Jesus": {"name": "Discipleship", "points": 4},
                        "Spiritual growth": {
                            "name": "Discipleship",
                            "points": 4,
                        },  # Additional mapping
                        "Take up your cross": {
                            "name": "Discipleship",
                            "points": 4,
                        },  # Additional mapping
                        "Evangelism and mission": {"name": "Evangelistic Zeal", "points": 4},
                        "Great Commission": {
                            "name": "Evangelistic Zeal",
                            "points": 4,
                        },  # Additional mapping
                        "Sharing the gospel": {
                            "name": "Evangelistic Zeal",
                            "points": 4,
                        },  # Additional mapping
                        "Worship and praise": {"name": "Worship", "points": 4},
                        "Faith and trust": {"name": "Faith", "points": 4},
                        "Hope in God": {"name": "Hope", "points": 4},
                        "Divine love": {"name": "Love", "points": 4},
                        "Peace in Christ": {"name": "Peace", "points": 4},
                        "Prayer and communion": {"name": "Prayer", "points": 4},
                        # Phase 3: Negative Themes - HIGH SEVERITY (-25 to -30 points)
                        "Blasphemy and mocking God": {"name": "Blasphemy", "points": -30},
                        "Deliberate disrespect": {
                            "name": "Blasphemy",
                            "points": -30,
                        },  # Additional mapping
                        "Mocking the sacred": {
                            "name": "Blasphemy",
                            "points": -30,
                        },  # Additional mapping
                        "Self-deification and pride": {"name": "Self-deification", "points": -25},
                        "Making oneself god": {
                            "name": "Self-deification",
                            "points": -25,
                        },  # Additional mapping
                        "Ultimate authority": {
                            "name": "Self-deification",
                            "points": -25,
                        },  # Additional mapping
                        "Apostasy and faith rejection": {"name": "Apostasy", "points": -25},
                        "Abandoning Christian beliefs": {
                            "name": "Apostasy",
                            "points": -25,
                        },  # Additional mapping
                        "Rejecting faith": {
                            "name": "Apostasy",
                            "points": -25,
                        },  # Additional mapping
                        "Suicide ideation and death wish": {
                            "name": "Suicide ideation",
                            "points": -25,
                        },
                        "Wanting death": {
                            "name": "Suicide ideation",
                            "points": -25,
                        },  # Additional mapping
                        "Death wish": {
                            "name": "Suicide ideation",
                            "points": -25,
                        },  # Additional mapping
                        # Phase 3: Negative Themes - MEDIUM SEVERITY (-15 to -20 points)
                        "Pride and arrogance": {"name": "Pride", "points": -20},
                        "Self-glorification": {
                            "name": "Pride",
                            "points": -20,
                        },  # Additional mapping
                        "Superiority complex": {
                            "name": "Pride",
                            "points": -20,
                        },  # Additional mapping
                        "Idolatry and false worship": {"name": "Idolatry", "points": -20},
                        "Elevating created things": {
                            "name": "Idolatry",
                            "points": -20,
                        },  # Additional mapping
                        "False worship": {"name": "Idolatry", "points": -20},  # Additional mapping
                        "Occult practices and sorcery": {"name": "Occult", "points": -20},
                        "Witchcraft and magic": {
                            "name": "Occult",
                            "points": -20,
                        },  # Additional mapping
                        "Demonic spirituality": {
                            "name": "Occult",
                            "points": -20,
                        },  # Additional mapping
                        "Sexual immorality and lust": {"name": "Sexual immorality", "points": -20},
                        "Adultery and unfaithfulness": {
                            "name": "Sexual immorality",
                            "points": -20,
                        },  # Additional mapping
                        "Objectification of others": {
                            "name": "Sexual immorality",
                            "points": -20,
                        },  # Additional mapping
                        "Glorification of violence": {"name": "Violence", "points": -20},
                        "Celebrating brutality": {
                            "name": "Violence",
                            "points": -20,
                        },  # Additional mapping
                        "Harm to others": {"name": "Violence", "points": -20},  # Additional mapping
                        "Hatred and vengeance": {"name": "Hatred", "points": -20},
                        "Bitterness and retaliation": {
                            "name": "Hatred",
                            "points": -20,
                        },  # Additional mapping
                        "Malice toward others": {
                            "name": "Hatred",
                            "points": -20,
                        },  # Additional mapping
                        # Phase 3: Negative Themes - LOWER SEVERITY (-10 to -15 points)
                        "Materialism and greed": {"name": "Materialism", "points": -15},
                        "Worship of wealth": {
                            "name": "Materialism",
                            "points": -15,
                        },  # Additional mapping
                        "Material possessions": {
                            "name": "Materialism",
                            "points": -15,
                        },  # Additional mapping
                        "Self-righteousness and works-based pride": {
                            "name": "Self-righteousness",
                            "points": -15,
                        },
                        "Earning salvation": {
                            "name": "Self-righteousness",
                            "points": -15,
                        },  # Additional mapping
                        "Works-based pride": {
                            "name": "Self-righteousness",
                            "points": -15,
                        },  # Additional mapping
                        "Moral confusion and relativism": {
                            "name": "Moral confusion",
                            "points": -15,
                        },
                        "Reversing good and evil": {
                            "name": "Moral confusion",
                            "points": -15,
                        },  # Additional mapping
                        "Ethical relativism": {
                            "name": "Moral confusion",
                            "points": -15,
                        },  # Additional mapping
                        "Vague spirituality without foundation": {
                            "name": "Vague spirituality",
                            "points": -10,
                        },
                        "Generic spiritual concepts": {
                            "name": "Vague spirituality",
                            "points": -10,
                        },  # Additional mapping
                        "Undefined divine references": {
                            "name": "Vague spirituality",
                            "points": -10,
                        },  # Additional mapping
                        "Empty positivity and self-help": {
                            "name": "Empty positivity",
                            "points": -10,
                        },
                        "Motivation without truth": {
                            "name": "Empty positivity",
                            "points": -10,
                        },  # Additional mapping
                        "Self-help without foundation": {
                            "name": "Empty positivity",
                            "points": -10,
                        },  # Additional mapping
                    }

                    # Find the matching theme
                    for key, value in theme_mapping.items():
                        if key.lower() in label.lower():
                            # Determine category based on theme name and point value
                            phase1_themes = [
                                "Christ-centered",
                                "Gospel presentation",
                                "Redemption",
                                "Sacrificial love",
                                "Light vs darkness",
                            ]
                            negative_themes = [
                                "Blasphemy",
                                "Self-deification",
                                "Apostasy",
                                "Suicide ideation",
                                "Pride",
                                "Idolatry",
                                "Occult",
                                "Sexual immorality",
                                "Violence",
                                "Hatred",
                                "Materialism",
                                "Self-righteousness",
                                "Moral confusion",
                                "Vague spirituality",
                                "Empty positivity",
                            ]

                            if value["name"] in phase1_themes:
                                category = "core_gospel"
                            elif value["name"] in negative_themes or value["points"] < 0:
                                category = "negative"
                            else:
                                category = "character_spiritual"

                            themes.append(
                                {
                                    "theme": value["name"],
                                    "score": float(score),
                                    "detection_method": "semantic",
                                    "category": category,
                                    "points": value["points"],
                                }
                            )
                            break

            logger.info(f"🔬 Semantic gospel themes: {[t['theme'] for t in themes]}")
            return themes

        except Exception as e:
            logger.warning(f"Zero-shot theme classification failed: {e}")
            return []

    def _analyze_sentiment(self, text: str) -> Optional[Dict]:
        """Analyze sentiment using Hugging Face model"""
        if not self.sentiment_analyzer:
            return None

        try:
            # Safe token-based truncation
            safe_text = self._safe_truncate_text(text)
            result = self.sentiment_analyzer(safe_text)
            if result:
                return {
                    "scores": result[0] if isinstance(result[0], list) else result,
                    "primary": max(
                        result[0] if isinstance(result[0], list) else result,
                        key=lambda x: x["score"],
                    ),
                }
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            return None

    def _analyze_content_safety(self, text: str) -> Optional[Dict]:
        """Analyze content safety using Hugging Face model"""
        if not self.safety_analyzer:
            return None

        try:
            # Safe token-based truncation
            safe_text = self._safe_truncate_text(text)
            result = self.safety_analyzer(safe_text)
            if result:
                return {
                    "scores": result[0] if isinstance(result[0], list) else result,
                    "is_toxic": any(
                        score["score"] > 0.5 and "toxic" in score["label"].lower()
                        for score in (result[0] if isinstance(result[0], list) else result)
                    ),
                }
        except Exception as e:
            logger.warning(f"Content safety analysis failed: {e}")
            return None

    def _analyze_emotions(self, text: str) -> Optional[Dict]:
        """Analyze emotions using Hugging Face model"""
        if not self.emotion_analyzer:
            return None

        try:
            # Safe token-based truncation
            safe_text = self._safe_truncate_text(text)
            result = self.emotion_analyzer(safe_text)
            if result:
                return {
                    "scores": result[0] if isinstance(result[0], list) else result,
                    "primary": max(
                        result[0] if isinstance(result[0], list) else result,
                        key=lambda x: x["score"],
                    ),
                }
        except Exception as e:
            logger.warning(f"Emotion analysis failed: {e}")
            return None

    def _calculate_final_score(
        self,
        christian_themes: List[Dict],
        concern_flags: List[Dict],
        sentiment_result: Optional[Dict],
        safety_result: Optional[Dict],
        emotion_result: Optional[Dict],
    ) -> Dict[str, float]:
        """
        Calculate final score with Phase 4 enhancements:
        - Start at 100 points and adjust based on content
        - Theological Significance Weighting (Core Gospel 1.5x, Character 1.2x)
        - Formational Weight Multiplier (-10 for severe content)
        - Enhanced scoring metadata for structured verdict
        """
        score = 100.0  # Start at 100 and adjust based on content
        positive_theme_points = 0.0  # Track positive theme contributions
        negative_theme_points = 0.0  # Track negative theme penalties

        # Process all themes (positive and negative)
        if christian_themes:
            for theme in christian_themes:
                theme_name = theme.get("theme", "").lower()
                confidence = theme.get("score", 0.5)
                points = theme.get("points", 0)
                category = theme.get("category", "")

                if points > 0 and confidence > 0.3:  # Positive themes - add bonus points
                    # Calculate theme points with confidence weighting
                    if confidence > 0.8:
                        theme_points = points * 1.5  # 50% bonus for high confidence (80%+)
                    else:
                        # Standard scaling for medium confidence
                        theme_points = points * confidence

                    positive_theme_points += theme_points
                    score += theme_points  # Add bonus points to the base 100

                elif points < 0 and confidence > 0.3:  # Negative themes - subtract points
                    # Apply penalties for negative themes based on confidence
                    if confidence > 0.7:  # High confidence negative themes get full penalty
                        penalty_points = abs(points)  # Convert negative to positive for subtraction
                        negative_theme_points += penalty_points
                        score -= penalty_points
                    else:  # Lower confidence gets reduced penalty
                        penalty_points = abs(points) * confidence
                        negative_theme_points += penalty_points
                        score -= penalty_points

                elif not points:  # Keyword-based themes get modest bonuses
                    keyword_points = 5 * confidence  # 5 points per keyword theme
                    positive_theme_points += keyword_points
                    score += keyword_points

        # Phase 4 Enhancement: Apply Theological Significance Weighting to positive themes
        theological_weighting = self._calculate_theological_weighting(christian_themes)
        if theological_weighting > 1.0 and positive_theme_points > 0:
            # Apply weighting boost to positive theme points only
            weighting_boost = positive_theme_points * (theological_weighting - 1.0)
            score += weighting_boost

        # Sentiment adjustments (more moderate since we start at 100)
        if sentiment_result and sentiment_result.get("primary"):
            sentiment = sentiment_result["primary"]
            if sentiment["label"].upper() == "POSITIVE":
                score += sentiment["score"] * 5  # Modest positive bonus
            elif sentiment["label"].upper() == "NEGATIVE":
                score -= sentiment["score"] * 8  # Moderate negative penalty

        # Emotion adjustments
        if emotion_result and emotion_result.get("primary"):
            emotion = emotion_result["primary"]
            positive_emotions = ["joy", "love", "optimism", "gratitude"]
            negative_emotions = ["anger", "fear", "disgust"]

            if any(pos_emotion in emotion["label"].lower() for pos_emotion in positive_emotions):
                score += emotion["score"] * 3  # Small positive emotion bonus
            elif any(neg_emotion in emotion["label"].lower() for neg_emotion in negative_emotions):
                score -= emotion["score"] * 5  # Moderate negative emotion penalty

        # Deduct points for concerning content (reduced impact since we start higher)
        if concern_flags:
            penalty = sum(3 for flag in concern_flags)  # -3 per concern type (reduced from -5)
            score -= penalty

        # Major penalty for toxic content
        if safety_result and safety_result.get("is_toxic"):
            score -= 20  # Significant but not devastating penalty for toxic content

        # Phase 4 Enhancement: Apply Formational Weight Multiplier for severe content
        formational_penalty = self._check_formational_penalty(
            christian_themes, sentiment_result, emotion_result, safety_result
        )
        if formational_penalty < 0:
            score += formational_penalty  # Apply the -10 penalty (formational_penalty is negative)

        final_score = max(0.0, min(100.0, score))

        # Return enhanced scoring metadata
        return {
            "final_score": final_score,
            "positive_theme_points": positive_theme_points,
            "negative_theme_points": negative_theme_points,
            "theological_weighting": theological_weighting,
            "formational_penalty": formational_penalty,
        }

    def _calculate_theological_weighting(self, christian_themes: List[Dict]) -> float:
        """
        Calculate theological significance weighting based on theme categories.

        Returns:
        - 1.5x for content with Core Gospel themes
        - 1.2x for content with Character/Spiritual themes
        - 1.0x for secular content or negative-only content
        """
        if not christian_themes:
            return 1.0

        # Check for Core Gospel themes (highest priority)
        has_core_gospel = any(
            t.get("category") == "core_gospel" and t.get("points", 0) > 0 for t in christian_themes
        )
        if has_core_gospel:
            return 1.5

        # Check for Character/Spiritual themes
        has_character_spiritual = any(
            t.get("category") == "character_spiritual" and t.get("points", 0) > 0
            for t in christian_themes
        )
        if has_character_spiritual:
            return 1.2

        # No positive Christian themes detected
        return 1.0

    def _check_formational_penalty(
        self,
        christian_themes: List[Dict],
        sentiment_result: Optional[Dict],
        emotion_result: Optional[Dict],
        safety_result: Optional[Dict],
    ) -> float:
        """
        Check if formational weight multiplier should be applied.

        Criteria for -10 penalty:
        - 3+ negative themes each -15 or worse
        - Emotionally immersive negative tone (anger/fear + negative sentiment)
        - No redemptive elements (no positive themes)

        Returns: -10 if criteria met, 0 otherwise
        """
        if not christian_themes:
            return 0.0

        # Count severe negative themes (-15 or worse)
        severe_negative_themes = [
            t
            for t in christian_themes
            if t.get("category") == "negative" and t.get("points", 0) <= -15
        ]

        # Check for 3+ severe negative themes
        if len(severe_negative_themes) < 3:
            return 0.0

        # Check for emotionally immersive negative tone
        has_negative_sentiment = (
            sentiment_result
            and sentiment_result.get("primary", {}).get("label", "").upper() == "NEGATIVE"
            and sentiment_result.get("primary", {}).get("score", 0) > 0.8
        )

        has_negative_emotion = (
            emotion_result
            and any(
                neg_emotion in emotion_result.get("primary", {}).get("label", "").lower()
                for neg_emotion in ["anger", "fear", "disgust", "rage"]
            )
            and emotion_result.get("primary", {}).get("score", 0) > 0.8
        )

        # Check for toxic content
        is_toxic = safety_result and safety_result.get("is_toxic", False)

        # Require strong emotional negativity
        if not (has_negative_sentiment and (has_negative_emotion or is_toxic)):
            return 0.0

        # Check for no redemptive elements (no positive themes)
        has_positive_themes = any(t.get("points", 0) > 0 for t in christian_themes)

        if has_positive_themes:
            return 0.0  # Has some redemptive content

        # All criteria met - apply formational penalty
        return -10.0

    def _generate_structured_verdict(
        self, christian_themes: List[Dict], scoring_metadata: Dict[str, float], concern_level: str
    ) -> Dict[str, str]:
        """
        Generate structured verdict with summary and formation guidance.

        Returns:
        - verdict_summary: 1-line statement about spiritual core
        - formation_guidance: 1-2 sentences about spiritual impact and approach
        """
        final_score = scoring_metadata.get("final_score", 0)
        theological_weighting = scoring_metadata.get("theological_weighting", 1.0)
        formational_penalty = scoring_metadata.get("formational_penalty", 0)

        # Categorize content type
        positive_themes = [t for t in christian_themes if t.get("points", 0) > 0]
        negative_themes = [t for t in christian_themes if t.get("points", 0) < 0]

        if final_score >= 70 and theological_weighting >= 1.2:
            # Excellent Christian content
            summary = "Gospel-rich, theologically sound, spiritually edifying content."
            guidance = "Safe for regular listening and worship. Encourages spiritual growth and strengthens faith through biblical truth."

        elif final_score >= 50 and len(positive_themes) > len(negative_themes):
            # Good Christian content with some issues
            summary = "Positive Christian content with good spiritual foundation."
            guidance = "Generally safe for listening. Contains biblical truth that can encourage faith and spiritual development."

        elif final_score >= 30 and len(positive_themes) > 0:
            # Mixed content
            summary = "Mixed spiritual content with both positive and concerning elements."
            guidance = "Use with discernment. Contains both beneficial and potentially harmful spiritual content that requires careful consideration."

        elif formational_penalty < 0:
            # Severe negative content with formational penalty
            summary = "Spiritually destructive content that forms listeners toward darkness."
            guidance = "Avoid for spiritual formation. This content immerses listeners in harmful themes without redemptive truth or hope."

        elif final_score <= 20:
            # Generally harmful content
            summary = "Spiritually concerning content with harmful influences."
            guidance = "Not recommended for regular listening. Contains themes that may negatively impact spiritual formation and biblical worldview."

        else:
            # Secular or neutral content
            summary = "Secular content with limited spiritual significance."
            guidance = "Spiritually neutral content. While not harmful, offers little spiritual formation or biblical truth for growth."

        return {"verdict_summary": summary, "formation_guidance": guidance}

    def _determine_concern_level(
        self, score: float, concern_flags: List[Dict], safety_result: Optional[Dict]
    ) -> str:
        """Determine concern level based on analysis (scores now start at 100%)"""
        if safety_result and safety_result.get("is_toxic"):
            return "High"
        elif score >= 90:  # Excellent content
            return "Very Low"
        elif score >= 75:  # Good content with minor issues
            return "Low"
        elif score >= 50:  # Moderate concerns
            return "Medium"
        else:  # Significant concerns
            return "High"

    def _generate_explanation(
        self,
        christian_themes: List[Dict],
        concern_flags: List[Dict],
        sentiment_result: Optional[Dict],
        safety_result: Optional[Dict],
        emotion_result: Optional[Dict],
        final_score: float,
    ) -> str:
        """Generate human-readable explanation"""
        explanations = []

        if christian_themes:
            # Handle enhanced theme structure
            theme_names = []
            for theme in christian_themes:
                if isinstance(theme, dict):
                    theme_names.append(theme.get("theme", "unknown"))
                else:
                    theme_names.append(str(theme))
            explanations.append(f"Contains Christian themes: {', '.join(theme_names[:5])}")

        if concern_flags:
            for flag in concern_flags:
                if "keywords" in flag and flag["keywords"]:
                    explanations.append(
                        f"Contains concerning language: {', '.join(flag['keywords'][:3])}"
                    )
                else:
                    explanations.append(
                        f"Contains concerning content: {flag.get('type', 'unspecified')}"
                    )

        # More user-friendly sentiment description
        if sentiment_result and sentiment_result.get("primary"):
            sentiment = sentiment_result["primary"]
            score = sentiment["score"]
            label = sentiment["label"].lower()

            # Convert to user-friendly descriptions
            if label == "positive":
                if score > 0.8:
                    sentiment_desc = "very positive"
                elif score > 0.6:
                    sentiment_desc = "positive"
                else:
                    sentiment_desc = "slightly positive"
            elif label == "negative":
                if score > 0.8:
                    sentiment_desc = "very negative"
                elif score > 0.6:
                    sentiment_desc = "negative"
                else:
                    sentiment_desc = "slightly negative"
            else:  # neutral
                sentiment_desc = "neutral"

            explanations.append(f"Overall sentiment: {sentiment_desc}")

        if safety_result and safety_result.get("is_toxic"):
            explanations.append("Content flagged as potentially inappropriate")

        # More user-friendly emotion description
        if emotion_result and emotion_result.get("primary"):
            emotion = emotion_result["primary"]
            score = emotion["score"]
            label = emotion["label"].lower()

            # Convert to user-friendly descriptions
            if score > 0.7:
                emotion_desc = f"strongly {label}"
            elif score > 0.5:
                emotion_desc = f"moderately {label}"
            else:
                emotion_desc = f"slightly {label}"

            explanations.append(f"Primary emotion: {emotion_desc}")

        if not explanations:
            explanations.append("Standard content analysis completed")

        return ". ".join(explanations)

    def _get_supporting_scripture(self, christian_themes) -> Optional[str]:
        """Get supporting scripture for detected Christian themes"""
        if not christian_themes:
            return None

        # Enhanced mapping for both keyword and semantic themes
        scripture_map = {
            # Keyword themes
            "jesus": "John 3:16 - For God so loved the world that he gave his one and only Son",
            "christ": "Philippians 2:9 - Therefore God exalted him to the highest place",
            "god": "Psalm 46:1 - God is our refuge and strength, an ever-present help in trouble",
            "lord": "Psalm 23:1 - The Lord is my shepherd, I lack nothing",
            "faith": "Hebrews 11:1 - Now faith is confidence in what we hope for",
            "grace": "Ephesians 2:8 - For it is by grace you have been saved, through faith",
            # Core Gospel Themes (Phase 1)
            "christ-centered": "Colossians 1:18 - And he is the head of the body, the church; he is the beginning and the firstborn from among the dead",
            "gospel presentation": "1 Corinthians 15:3-4 - For what I received I passed on to you as of first importance: that Christ died for our sins according to the Scriptures",
            "redemption": "Ephesians 1:7 - In him we have redemption through his blood, the forgiveness of sins",
            "sacrificial love": "John 15:13 - Greater love has no one than this: to lay down one's life for one's friends",
            "light vs darkness": "John 1:5 - The light shines in the darkness, and the darkness has not overcome it",
        }

        # Handle both old format (list of strings) and new format (list of dicts)
        theme_names = []
        if christian_themes and isinstance(christian_themes[0], dict):
            # New enhanced format
            theme_names = [theme.get("theme", "").lower() for theme in christian_themes]
        else:
            # Old string format
            theme_names = [str(theme).lower() for theme in christian_themes]

        # Look for matching scripture
        for theme_name in theme_names:
            if theme_name in scripture_map:
                return scripture_map[theme_name]

        return "Psalm 100:1 - Shout for joy to the Lord, all the earth"

    def _fallback_analysis(self, title: str, artist: str, lyrics: str) -> AnalysisResult:
        """Fallback analysis when AI models fail"""
        all_text = f"{title} {artist} {lyrics}".lower()

        keyword_themes = self._detect_christian_themes(all_text)
        concern_flags = self._detect_concerns(all_text)

        # Convert keyword themes to enhanced structure
        christian_themes = [
            {
                "theme": theme,
                "score": 1.0,
                "detection_method": "keyword",
                "category": "general_christian",
                "points": 3,  # Default points for keyword themes
            }
            for theme in keyword_themes
        ]

        # Calculate score using new system (start at 100, adjust based on content)
        score = 100.0  # Start at 100 points
        if christian_themes:
            score += len(christian_themes) * 2  # Small bonus for keyword themes
        if concern_flags:
            score -= 3 * len(concern_flags)  # -3 per concern (consistent with main system)

        score = max(0.0, min(100.0, score))

        # Determine concern level using 100-point starting system thresholds
        if score >= 90:
            concern_level = "Very Low"
        elif score >= 75:
            concern_level = "Low"
        elif score >= 50:
            concern_level = "Medium"
        else:
            concern_level = "High"

        explanation = "Keyword-based fallback analysis completed"
        if christian_themes:
            explanation += f" - Contains Christian themes: {', '.join([t['theme'] for t in christian_themes[:3]])}"
        if concern_flags:
            explanation += " - Contains concerning content"

        return AnalysisResult(
            title=title,
            artist=artist,
            lyrics_text=lyrics,
            processed_text=all_text,
            content_analysis={
                "concern_flags": concern_flags,
                "total_penalty": sum(
                    5 for flag in concern_flags
                ),  # Updated penalty (reduced from 15)
            },
            biblical_analysis={
                "themes": christian_themes,  # Now uses enhanced structure
                "supporting_scripture": self._get_supporting_scripture(
                    [t["theme"] for t in christian_themes]
                ),
                "biblical_themes_count": len(christian_themes),
            },
            scoring_results={
                "final_score": score,
                "quality_level": concern_level,
                "explanation": explanation,
            },
        )
