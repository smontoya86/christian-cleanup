import logging
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from typing import Dict, List, Optional, Tuple
import re
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

logger = logging.getLogger(__name__)

class HuggingFaceAnalyzer:
    """
    Free AI-powered song analysis using Hugging Face models.
    Uses local models with no API calls required.
    """
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Initializing HuggingFace analyzer on device: {self.device}")
        
        # Load all models during initialization to avoid lazy loading issues
        self._load_models()
        
        # Christian theme keywords (expanded)
        self.christian_keywords = {
            'jesus', 'christ', 'god', 'lord', 'faith', 'holy', 'praise', 'worship', 
            'hallelujah', 'amen', 'blessed', 'salvation', 'heaven', 'prayer', 'bible',
            'savior', 'grace', 'mercy', 'gospel', 'church', 'congregation', 'divine',
            'almighty', 'eternal', 'sacred', 'blessed', 'righteous', 'shepherd',
            'resurrection', 'crucifixion', 'trinity', 'apostle', 'disciple', 'angel'
        }
        
        # Concern keywords (expanded)
        self.concern_keywords = {
            'damn', 'hell', 'shit', 'fuck', 'bitch', 'ass', 'bastard', 'crap',
            'piss', 'whore', 'slut', 'retard', 'faggot', 'nigger', 'goddamn',
            'motherfucker', 'asshole', 'dickhead', 'pussy', 'cock', 'penis',
            'sex', 'sexual', 'drugs', 'cocaine', 'heroin', 'marijuana', 'weed',
            'drunk', 'alcohol', 'beer', 'vodka', 'whiskey', 'violence', 'kill',
            'murder', 'death', 'suicide', 'hate', 'racist', 'nazi'
        }
        
        logger.info("HuggingFace analyzer initialization complete - all models loaded successfully")

    def _load_models(self):
        """Load all models during initialization to avoid lazy loading delays and rate limits."""
        try:
            logger.info("Loading sentiment analysis model...")
            # Load tokenizer and model separately to use local_files_only
            tokenizer = AutoTokenizer.from_pretrained(
                "cardiffnlp/twitter-roberta-base-sentiment-latest",
                local_files_only=True
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                "cardiffnlp/twitter-roberta-base-sentiment-latest",
                local_files_only=True
            )
            self._sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model=model,
                tokenizer=tokenizer,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True
            )
            logger.info("Sentiment analysis model loaded successfully")
            
            logger.info("Loading content safety model...")
            tokenizer = AutoTokenizer.from_pretrained(
                "unitary/toxic-bert",
                local_files_only=True
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                "unitary/toxic-bert",
                local_files_only=True
            )
            self._safety_analyzer = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True
            )
            logger.info("Content safety model loaded successfully")
            
            logger.info("Loading emotion analysis model...")
            tokenizer = AutoTokenizer.from_pretrained(
                "j-hartmann/emotion-english-distilroberta-base",
                local_files_only=True
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                "j-hartmann/emotion-english-distilroberta-base",
                local_files_only=True
            )
            self._emotion_analyzer = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                device=0 if self.device == "cuda" else -1,
                return_all_scores=True
            )
            logger.info("Emotion analysis model loaded successfully")
            
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
            return_all_scores=True
        )
        logger.info("Sentiment analysis model loaded successfully")
        
        logger.info("Loading content safety model (with download)...")
        self._safety_analyzer = pipeline(
            "text-classification",
            model="unitary/toxic-bert",
            device=0 if self.device == "cuda" else -1,
            return_all_scores=True
        )
        logger.info("Content safety model loaded successfully")
        
        logger.info("Loading emotion analysis model (with download)...")
        self._emotion_analyzer = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            device=0 if self.device == "cuda" else -1,
            return_all_scores=True
        )
        logger.info("Emotion analysis model loaded successfully")

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
        if '. ' in truncated:
            last_sentence = truncated.rfind('. ')
            if last_sentence > safety_chars * 0.7:  # Don't lose too much content
                truncated = truncated[:last_sentence + 1]
        # Fall back to word boundary
        elif ' ' in truncated:
            last_space = truncated.rfind(' ')
            if last_space > safety_chars * 0.8:  # Don't lose too much text
                truncated = truncated[:last_space]
        
        return truncated

    def analyze_song(self, title: str, artist: str, lyrics: str, user_id: Optional[int] = None) -> AnalysisResult:
        """
        Comprehensive song analysis using free Hugging Face models
        """
        # Check rate limits before processing
        identifier = f"user_{user_id}" if user_id else "anonymous"
        rate_check = rate_monitor.check_rate_limit(identifier)
        
        if not rate_check['allowed']:
            logger.warning(f"Rate limit exceeded for {identifier}: {rate_check['reason']}")
            # Use proper RateLimitException instead of generic Exception
            raise RateLimitException(
                message=f"Rate limit exceeded: {rate_check['reason']}",
                service_name="HuggingFaceAnalyzer",
                retry_after=rate_check['retry_after']
            )
        
        # Record the request
        rate_monitor.record_request(identifier)
        
        try:
            logger.info(f"Starting HuggingFace analysis for '{title}' by {artist}")
            
            # Combine all text for analysis
            full_text = f"{title} {artist} {lyrics}".lower().strip()
            
            # Safe token-based truncation for AI models
            all_text = self._safe_truncate_text(full_text)
            # 1. Keyword-based theme detection (fast)
            christian_themes = self._detect_christian_themes(all_text)
            concern_flags = self._detect_concerns(all_text)
            
            # 2. AI-powered sentiment analysis
            sentiment_result = self._analyze_sentiment(all_text)
            
            # 3. AI-powered content safety
            safety_result = self._analyze_content_safety(all_text)
            
            # 4. AI-powered emotion detection
            emotion_result = self._analyze_emotions(all_text)
            
            # Calculate final score
            final_score = self._calculate_final_score(
                christian_themes, concern_flags, sentiment_result, 
                safety_result, emotion_result
            )
            
            # Determine concern level
            concern_level = self._determine_concern_level(final_score, concern_flags, safety_result)
            
            # Generate explanation
            explanation = self._generate_explanation(
                christian_themes, concern_flags, sentiment_result, 
                safety_result, emotion_result, final_score
            )
            
            # Get supporting scripture for Christian themes
            supporting_scripture = self._get_supporting_scripture(christian_themes)
            
            logger.info(f"HuggingFace analysis completed for '{title}' - Score: {final_score}, Concern: {concern_level}")
            
            # Create compatible AnalysisResult structure
            result = AnalysisResult(
                title=title,
                artist=artist,
                lyrics_text=lyrics,
                processed_text=all_text,
                content_analysis={
                    'concern_flags': concern_flags,
                    'safety_assessment': safety_result,
                    'total_penalty': sum(30 for flag in concern_flags)
                },
                biblical_analysis={
                    'themes': [{'theme': theme, 'score': 1.0} for theme in christian_themes],
                    'supporting_scripture': supporting_scripture,
                    'biblical_themes_count': len(christian_themes)
                },
                model_analysis={
                    'sentiment': sentiment_result,
                    'emotions': emotion_result,
                    'content_safety': safety_result
                },
                scoring_results={
                    'final_score': final_score,
                    'quality_level': concern_level,
                    'component_scores': {
                        'christian_themes': min(len(christian_themes) * 10, 50),
                        'sentiment_score': sentiment_result.get('primary', {}).get('score', 0) * 20 if sentiment_result else 0,
                        'safety_penalty': -40 if safety_result and safety_result.get('is_toxic') else 0,
                        'concern_penalty': -sum(30 for flag in concern_flags)
                    },
                    'explanation': explanation
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in HuggingFace analysis: {str(e)}")
            # Fallback to keyword-based analysis
            return self._fallback_analysis(title, artist, lyrics)
        finally:
            # Always mark the request as complete to free up concurrent slots
            rate_monitor.complete_request(identifier)

    def _detect_christian_themes(self, text: str) -> List[str]:
        """Detect Christian themes using keyword matching"""
        found_themes = []
        logger.info(f"🔍 Detecting Christian themes in text (length: {len(text)})")
        logger.info(f"📝 Text content: {text[:200]}...")  # Log first 200 chars
        
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
        
        logger.info(f"⚠️ Detecting concerns in text (length: {len(text)})")
        logger.info(f"📝 Text content: {text[:200]}...")  # Log first 200 chars
        
        for keyword in self.concern_keywords:
            if keyword in text:
                found_concerns.append(keyword)
                logger.info(f"🚨 Found concerning keyword: '{keyword}'")
        
        if found_concerns:
            concern_flags.append({
                'type': 'explicit_language',
                'confidence': 0.9,
                'keywords': found_concerns
            })
            
        logger.info(f"⚠️ Total concern flags: {len(concern_flags)} - Keywords: {found_concerns}")
        return concern_flags

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
                    'scores': result[0] if isinstance(result[0], list) else result,
                    'primary': max(result[0] if isinstance(result[0], list) else result, 
                                 key=lambda x: x['score'])
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
                    'scores': result[0] if isinstance(result[0], list) else result,
                    'is_toxic': any(score['score'] > 0.5 and 'toxic' in score['label'].lower() 
                                  for score in (result[0] if isinstance(result[0], list) else result))
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
                    'scores': result[0] if isinstance(result[0], list) else result,
                    'primary': max(result[0] if isinstance(result[0], list) else result,
                                 key=lambda x: x['score'])
                }
        except Exception as e:
            logger.warning(f"Emotion analysis failed: {e}")
            return None

    def _calculate_final_score(self, christian_themes: List[str], concern_flags: List[Dict],
                             sentiment_result: Optional[Dict], safety_result: Optional[Dict],
                             emotion_result: Optional[Dict]) -> float:
        """Calculate final score starting at 100% and deducting for concerning content"""
        base_score = 100.0  # Start at perfect score
        
        # Concern penalties - significant deductions
        if concern_flags:
            penalty = sum(15 for flag in concern_flags)  # -15 per concern type (was -30)
            base_score -= penalty
        
        # Safety penalty - major deduction for toxic content
        if safety_result and safety_result.get('is_toxic'):
            base_score -= 25  # Heavy penalty for toxic content (was -40)
        
        # Sentiment adjustment - minor penalties for negative sentiment
        if sentiment_result and sentiment_result.get('primary'):
            sentiment = sentiment_result['primary']
            if sentiment['label'].upper() == 'NEGATIVE':
                base_score -= sentiment['score'] * 10  # Up to -10 for strong negative sentiment
            # No bonus for positive sentiment - that's expected
        
        # Emotion adjustment - small penalties for very negative emotions
        if emotion_result and emotion_result.get('primary'):
            emotion = emotion_result['primary']
            very_negative_emotions = ['anger', 'fear', 'disgust']  # Removed sadness as it's often artistic
            
            if any(neg_emotion in emotion['label'].lower() for neg_emotion in very_negative_emotions):
                base_score -= emotion['score'] * 8  # Small penalty for negative emotions
        
        # Christian theme bonus - small bonus for explicitly Christian content
        if christian_themes:
            bonus = min(len(christian_themes) * 3, 10)  # Up to +10 for Christian themes (much smaller)
            base_score += bonus
        
        return max(0.0, min(100.0, base_score))

    def _determine_concern_level(self, score: float, concern_flags: List[Dict], 
                               safety_result: Optional[Dict]) -> str:
        """Determine concern level based on analysis (scores now start at 100%)"""
        if safety_result and safety_result.get('is_toxic'):
            return 'High'
        elif score < 70:  # Significant concerns
            return 'High'
        elif score < 85:  # Moderate concerns
            return 'Medium'
        elif score < 95:  # Minor concerns
            return 'Low'
        else:  # Excellent content
            return 'Very Low'

    def _generate_explanation(self, christian_themes: List[str], concern_flags: List[Dict],
                            sentiment_result: Optional[Dict], safety_result: Optional[Dict],
                            emotion_result: Optional[Dict], final_score: float) -> str:
        """Generate human-readable explanation"""
        explanations = []
        
        if christian_themes:
            explanations.append(f"Contains Christian themes: {', '.join(christian_themes[:5])}")
        
        if concern_flags:
            for flag in concern_flags:
                if 'keywords' in flag and flag['keywords']:
                    explanations.append(f"Contains concerning language: {', '.join(flag['keywords'][:3])}")
                else:
                    explanations.append(f"Contains concerning content: {flag.get('type', 'unspecified')}")
        
        # More user-friendly sentiment description
        if sentiment_result and sentiment_result.get('primary'):
            sentiment = sentiment_result['primary']
            score = sentiment['score']
            label = sentiment['label'].lower()
            
            # Convert to user-friendly descriptions
            if label == 'positive':
                if score > 0.8:
                    sentiment_desc = "very positive"
                elif score > 0.6:
                    sentiment_desc = "positive"
                else:
                    sentiment_desc = "slightly positive"
            elif label == 'negative':
                if score > 0.8:
                    sentiment_desc = "very negative"
                elif score > 0.6:
                    sentiment_desc = "negative"
                else:
                    sentiment_desc = "slightly negative"
            else:  # neutral
                sentiment_desc = "neutral"
            
            explanations.append(f"Overall sentiment: {sentiment_desc}")
        
        if safety_result and safety_result.get('is_toxic'):
            explanations.append("Content flagged as potentially inappropriate")
        
        # More user-friendly emotion description
        if emotion_result and emotion_result.get('primary'):
            emotion = emotion_result['primary']
            score = emotion['score']
            label = emotion['label'].lower()
            
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

    def _get_supporting_scripture(self, christian_themes: List[str]) -> Optional[str]:
        """Get supporting scripture for detected Christian themes"""
        if not christian_themes:
            return None
            
        # Simple mapping of themes to scriptures
        scripture_map = {
            'jesus': "John 3:16 - For God so loved the world that he gave his one and only Son",
            'christ': "Philippians 2:9 - Therefore God exalted him to the highest place",
            'god': "Psalm 46:1 - God is our refuge and strength, an ever-present help in trouble",
            'lord': "Psalm 23:1 - The Lord is my shepherd, I lack nothing",
            'faith': "Hebrews 11:1 - Now faith is confidence in what we hope for",
            'grace': "Ephesians 2:8 - For it is by grace you have been saved, through faith"
        }
        
        for theme in christian_themes:
            if theme in scripture_map:
                return scripture_map[theme]
        
        return "Psalm 100:1 - Shout for joy to the Lord, all the earth"

    def _fallback_analysis(self, title: str, artist: str, lyrics: str) -> AnalysisResult:
        """Fallback analysis when AI models fail"""
        all_text = f"{title} {artist} {lyrics}".lower()
        
        christian_themes = self._detect_christian_themes(all_text)
        concern_flags = self._detect_concerns(all_text)
        
        base_score = 100.0  # Start at perfect score
        if concern_flags:
            base_score -= 15 * len(concern_flags)  # -15 per concern
        if christian_themes:
            base_score += min(len(christian_themes) * 3, 10)  # Small bonus for Christian themes
        
        score = max(0.0, min(100.0, base_score))
        
        # Determine concern level using new thresholds
        if score < 70:
            concern_level = 'High'
        elif score < 85:
            concern_level = 'Medium'
        elif score < 95:
            concern_level = 'Low'
        else:
            concern_level = 'Very Low'
        
        explanation = "Keyword-based analysis completed"
        if christian_themes:
            explanation += f" - Contains Christian themes: {', '.join(christian_themes[:3])}"
        if concern_flags:
            explanation += " - Contains concerning content"
        
        return AnalysisResult(
            title=title,
            artist=artist,
            lyrics_text=lyrics,
            processed_text=all_text,
            content_analysis={
                'concern_flags': concern_flags,
                'total_penalty': sum(30 for flag in concern_flags)
            },
            biblical_analysis={
                'themes': [{'theme': theme, 'score': 1.0} for theme in christian_themes],
                'supporting_scripture': self._get_supporting_scripture(christian_themes),
                'biblical_themes_count': len(christian_themes)
            },
            scoring_results={
                'final_score': score,
                'quality_level': concern_level,
                'explanation': explanation
            }
        ) 