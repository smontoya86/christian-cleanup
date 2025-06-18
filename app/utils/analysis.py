import logging
import os
import re
import time
from typing import Optional, Dict, Any, List, Tuple, Union, Callable

import torch
from dotenv import load_dotenv

from ..config.christian_rubric import get_christian_rubric
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

# Type aliases for better code readability
DeviceType = str
UserId = Optional[int]
AnalysisResult = Dict[str, Any]
LyricsText = Optional[str]
ContentModerationPrediction = Dict[str, Any]
ContentModerationPredictions = List[ContentModerationPrediction]
FlagDetails = Dict[str, Any]
FlagDetailsList = List[FlagDetails]
ThemeDetails = Dict[str, Any]
ThemeDetailsList = List[ThemeDetails]
ScoreRange = int  # 0-100
ConfidenceScore = float  # 0.0-1.0
PenaltyScore = int
PatternList = List[str]
LabelMap = Dict[str, Dict[str, Any]]
ScriptureRef = Dict[str, Any]
ChristianRubric = Dict[str, Any]

logger = logging.getLogger(__name__)

# Fallback/Dummy implementations if main imports fail (e.g. running standalone for basic tests)
# Actual classes are expected to be imported from .lyrics and .bible_client
try:
    from .lyrics import LyricsFetcher
    from .bible_client import BibleClient
except ImportError:
    logger.warning("Could not import LyricsFetcher or BibleClient from .lyrics/.bible_client. Using dummy fallbacks.")
    class DummyLyricsFetcher:
        def fetch_lyrics(self, title: str, artist: str) -> Optional[str]:
            logger.info(f"Dummy LyricsFetcher: fetch_lyrics for {title} by {artist}")
            return None

    class DummyBibleClient:
        BSB_ID: str = "dummy_bsb_id"
        KJV_ID: str = "dummy_kjv_id"
        
        def __init__(self, preferred_bible_id: Optional[str] = None) -> None:
            logger.info("Dummy BibleClient initialized")
            self.api_key: Optional[str] = os.getenv("BIBLE_API_KEY")
            if not self.api_key:
                logger.warning("BIBLE_API_KEY not found for Dummy BibleClient, scripture fetching will fail.")
            self.default_bible_id: str = preferred_bible_id if preferred_bible_id else self.BSB_ID
            self.fallback_bible_id: str = self.KJV_ID

        def get_scripture_passage(self, reference: str, bible_id: Optional[str] = None) -> Dict[str, Any]:
            logger.info(f"Dummy BibleClient: get_scripture_passage for {reference}")
            return {"content": "Dummy scripture not found.", "reference": reference, "error": "Dummy client"}

        def get_verses_for_theme(self, theme_name: str, scripture_refs: List[str]) -> List[Dict[str, Any]]:
            logger.info(f"Dummy BibleClient: get_verses_for_theme for {theme_name}")
            return []

class SongAnalyzer:
    """
    Comprehensive song analysis service for Christian content evaluation.
    
    This analyzer performs multi-layered analysis including:
    - Content moderation using ML models
    - Christian theme detection (positive and negative)
    - Purity flag detection for content concerns
    - Scripture-based scoring and recommendations
    
    Attributes:
        device: Computing device for ML model inference ('cuda' or 'cpu')
        user_id: Optional ID of the requesting user for tracking
        christian_rubric: Configuration dictionary for scoring rules
        content_moderation_classifier: ML pipeline for content analysis
        lyrics_fetcher: Service for fetching song lyrics
        bible_client: Service for scripture references
    """
    
    def __init__(self, device: Optional[DeviceType] = None, user_id: UserId = None) -> None:
        """
        Initialize the SongAnalyzer.
        
        Args:
            device: The device to use for model inference (e.g., 'cuda' or 'cpu').
                   If None, will use CUDA if available, otherwise CPU.
            user_id: Optional ID of the user who requested the analysis.
        """
        self.device: DeviceType = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.user_id: UserId = user_id
        logger.info(f"SongAnalyzer using device: {self.device}")

        self.christian_rubric: ChristianRubric = get_christian_rubric()
        # Add or update purity flag definitions for cardiffnlp mapping
        # This structure helps map model outputs to specific flags and penalties.
        self.christian_rubric["purity_flag_definitions"] = {
            "cardiffnlp_model_map": {
                "hate": { 
                    "flag_name": "Hate Speech Detected", 
                    "penalty": 75
                },
                "offensive": { 
                    "flag_name": "Explicit Language / Corrupting Talk",
                    "penalty": 50
                }
                # 'not-offensive' typically carries no penalty and isn't listed here
            },
            # Placeholder for other flags that might be detected by other means or future models
            "other_flags": {
                 "sexual_content_overt": {
                    "flag_name": "Sexual Content / Impurity (overt)",
                    "penalty": 50 # Example, actual penalty might vary or stack
                },
                "glorification_drugs_violence": {
                    "flag_name": "Glorification of Drugs / Violence / Works of Flesh (overt)",
                    "penalty": 25 # Example
                }
            }
        }

        # Model name
        self.content_moderation_model_name: str = "cardiffnlp/twitter-roberta-base-offensive"
        
        # Initialize model pipeline
        self.content_moderation_classifier: Optional[Any] = None  # Will hold the content moderation pipeline
        
        self._load_models() # Load all necessary models

        # Initialize services with proper configuration
        try:
            # Use centralized config first
            from app.config import config
            genius_token: Optional[str] = config.LYRICSGENIUS_API_KEY
            bible_api_key: Optional[str] = config.BIBLE_API_KEY
            
            # If we're in a Flask app context, try to get from config as fallback
            try:
                from flask import current_app
                if current_app:
                    if not genius_token and 'LYRICSGENIUS_API_KEY' in current_app.config:
                        genius_token = current_app.config['LYRICSGENIUS_API_KEY']
                    if not bible_api_key and 'BIBLE_API_KEY' in current_app.config:
                        bible_api_key = current_app.config['BIBLE_API_KEY']
            except (RuntimeError, ImportError):  # Not in Flask app context or Flask not available
                pass
            
            # Final fallback to environment variables for backwards compatibility
            if not genius_token:
                genius_token = os.environ.get('LYRICSGENIUS_API_KEY')
            if not bible_api_key:
                bible_api_key = os.environ.get('BIBLE_API_KEY')
            
            # Initialize services with the API keys
            self.lyrics_fetcher: Optional[LyricsFetcher] = LyricsFetcher(genius_token=genius_token)
            self.bible_client: Optional[BibleClient] = BibleClient()  # It will use the centralized config we set
            self.bsb_bible_id: Optional[str] = BibleClient.BSB_ID
            self.kjv_bible_id: Optional[str] = BibleClient.KJV_ID
            
        except Exception as e:
            logger.error(f"Error initializing SongAnalyzer services: {e}", exc_info=True)
            # Initialize with None values if there's an error
            self.lyrics_fetcher = None
            self.bible_client = None
            self.bsb_bible_id = None
            self.kjv_bible_id = None
        
    def _load_models(self) -> None:
        """Load all necessary models for analysis with progress tracking."""
        import time
        from tqdm import tqdm
        
        logger.info("Loading content moderation model...")
        start_time: float = time.time()
        
        # Try multiple models with fallback options
        model_options = [
            self.content_moderation_model_name,  # Primary model
            "cardiffnlp/twitter-roberta-base-hate",  # Fallback 1
            "distilbert-base-uncased-finetuned-sst-2-english"  # Fallback 2 (basic sentiment)
        ]
        
        self.content_moderation_classifier = None
        
        for model_name in model_options:
            try:
                logger.info(f"Attempting to load content moderation model: {model_name}")
                
                # Show progress while downloading/loading the model
                with tqdm(desc=f"Loading {model_name}", unit="B", unit_scale=True, unit_divisor=1024) as pbar:
                    def update_progress(block_num: int, block_size: int, total_size: int) -> None:
                        if pbar.total != total_size:
                            pbar.total = total_size
                        pbar.update(block_size)
                    
                    # Load content moderation model with progress tracking
                    self.content_moderation_classifier = pipeline(
                        "text-classification",
                        model=model_name,
                        device=self.device,
                        framework="pt"
                    )
                    
                load_time: float = time.time() - start_time
                logger.info(f"Content moderation model '{model_name}' loaded successfully in {load_time:.2f} seconds")
                self.content_moderation_model_name = model_name  # Update to actual loaded model
                
                # Test the pipeline with a simple example to verify it's working
                try:
                    test_prediction = self.content_moderation_classifier("Hello world")
                    logger.info(f"Model test successful. Sample prediction: {test_prediction}")
                except Exception as test_error:
                    logger.warning(f"Model {model_name} loaded but failed test: {test_error}")
                    self.content_moderation_classifier = None
                    continue
                    
                break  # Successfully loaded and tested
                
            except Exception as e:
                logger.warning(f"Failed to load model {model_name}: {e}")
                continue
        
        if self.content_moderation_classifier is None:
            logger.error("All content moderation models failed to load. Analysis will use rule-based fallback only.")
            logger.error("Consider installing the transformers library with: pip install transformers torch")
            logger.error("Or check your internet connection for model downloads.")

    def _get_sensitive_content_score_bert(self, text: str) -> Dict[str, float]:
        """
        Legacy BERT-based sensitivity scorer (placeholder for backward compatibility).
        
        Args:
            text: Text to analyze for sensitive content
            
        Returns:
            Dictionary of sensitivity scores (currently empty as this is deprecated)
        """
        # This method seems to be from an older Bert-based sensitivity scorer.
        # For now, it's not directly used by the main purity flag logic, which relies on CardiffNLP.
        # If it's needed for an 'alternative_model_raw_predictions', it would be implemented here.
        logger.debug("Stub: _get_sensitive_content_score_bert called. Returning empty dict.")
        return {}

    def _preprocess_lyrics(self, lyrics: str) -> str:
        """
        Preprocess lyrics text for analysis by cleaning and normalizing.
        
        Args:
            lyrics: Raw lyrics text
            
        Returns:
            Processed lyrics text with timestamps removed, 
            punctuation cleaned, and whitespace normalized
        """
        logger.debug("Executing full _preprocess_lyrics")
        if not lyrics:
            return ""
        # Convert to lowercase
        processed_lyrics: str = lyrics.lower()
        # Remove timestamps (e.g., [00:12.345] or [00:01:12.345] if hours are present)
        processed_lyrics = re.sub(r'\[\d{2}:\d{2}(?:\.\d{1,3})?\]', '', processed_lyrics) # Handles [MM:SS.mmm] and [MM:SS]
        processed_lyrics = re.sub(r'\[\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?\]', '', processed_lyrics) # Handles [HH:MM:SS.mmm] and [HH:MM:SS]
        
        # Remove punctuation (retain apostrophes for contractions, hyphens for compound words)
        # This regex keeps letters, numbers, spaces, apostrophes, and hyphens.
        # It removes other punctuation like .,!?;:()[]{} etc.
        processed_lyrics = re.sub(r"[^a-z0-9\s'-]", '', processed_lyrics)
        # Normalize whitespace (replace multiple spaces/newlines with a single space)
        processed_lyrics = re.sub(r'\s+', ' ', processed_lyrics).strip()
        return processed_lyrics

    def _get_content_moderation_predictions(self, text: str, chunk_size: int = 500) -> ContentModerationPredictions:
        """
        Get content moderation predictions using the cardiffnlp/twitter-roberta-base-offensive-latest model.
        
        Args:
            text: The text to analyze
            chunk_size: Maximum number of tokens per chunk (default: 500)
            
        Returns:
            List of prediction dictionaries with 'label' and 'score' keys,
            sorted by score in descending order
        """
        logger.debug("Executing _get_content_moderation_predictions")
        if not text:
            logger.warning("Empty text provided for content moderation, returning empty predictions.")
            return []
            
        if not self.content_moderation_classifier:
            logger.warning("Content moderation classifier not loaded, using rule-based fallback.")
            # Fallback to rule-based analysis using explicit patterns
            return self._get_rule_based_content_predictions(text)
        
        try:
            # First, check for explicit patterns in the text
            explicit_patterns = self._get_explicit_patterns()
            explicit_matches = []
            
            for pattern in explicit_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    explicit_matches.append({
                        'label': 'explicit',
                        'score': 0.95,  # High confidence for explicit pattern matches
                        'pattern': pattern
                    })
            
            if explicit_matches:
                logger.warning(f"Found {len(explicit_matches)} explicit pattern matches in text")
                # Return a high-confidence explicit flag if we found explicit patterns
                return [{
                    'label': 'explicit',
                    'score': 0.95
                }]
            
            # If no explicit patterns found, proceed with model prediction
            # Split the text into sentences first
            sentences: List[str] = re.split(r'(?<=[.!?])\s+', text)
            current_chunk: List[str] = []
            chunks: List[str] = []
            current_length: int = 0
            
            # Create chunks of text that are roughly chunk_size tokens
            for sentence in sentences:
                sentence_length: int = len(sentence.split())
                if current_length + sentence_length > chunk_size and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                current_chunk.append(sentence)
                current_length += sentence_length
            
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # Process each chunk and collect results
            all_predictions: ContentModerationPredictions = []
            for chunk in chunks:
                try:
                    # Get predictions for all categories
                    chunk_results = self.content_moderation_classifier(chunk, truncation=True, max_length=512)
                    
                    # The result is a list of lists (one list per input, with each containing dicts for each label)
                    if chunk_results and isinstance(chunk_results, list):
                        # Flatten the results if needed (should be a list of lists)
                        if len(chunk_results) > 0 and isinstance(chunk_results[0], list):
                            chunk_results = chunk_results[0]
                        all_predictions.extend(chunk_results)
                except Exception as chunk_error:
                    logger.warning(f"Error processing chunk: {chunk_error}")
                    continue
            
            if not all_predictions:
                return []
                
            logger.debug(f"Content moderation raw predictions: {all_predictions}")
            
            # Process and deduplicate predictions, keeping the highest score for each label
            relevant_predictions: Dict[str, ContentModerationPrediction] = {}
            for pred in all_predictions:
                if not isinstance(pred, dict) or 'label' not in pred or 'score' not in pred:
                    continue
                    
                label: str = pred.get('label', '').lower()
                score: float = float(pred.get('score', 0))
                
                # For 'OK' label, we'll be more careful about overriding other flags
                if label == 'ok':
                    # Only consider 'OK' if we don't have other flags yet
                    if not relevant_predictions and score > 0.7:  # Only if we're very confident
                        relevant_predictions[label] = {'label': label, 'score': score}
                    continue
                    
                # For other labels, be more aggressive in flagging
                if label not in relevant_predictions or score > relevant_predictions[label]['score']:
                    # Lower the threshold for flagging potentially problematic content
                    if score >= 0.4:  # Lowered from 0.5 to catch more cases
                        relevant_predictions[label] = {'label': label, 'score': score}
            
            # If we have any non-OK predictions, remove the OK prediction
            if len(relevant_predictions) > 1 and 'ok' in relevant_predictions:
                del relevant_predictions['ok']
            
            # Convert to list and sort by score in descending order
            sorted_predictions: ContentModerationPredictions = sorted(
                relevant_predictions.values(), 
                key=lambda x: x['score'], 
                reverse=True
            )
            
            return sorted_predictions
            
        except Exception as e:
            logger.error(f"Error getting content moderation predictions: {e}", exc_info=True)
            # Fallback to rule-based analysis if model fails
            logger.info("Falling back to rule-based content analysis")
            return self._get_rule_based_content_predictions(text)
    
    def _get_rule_based_content_predictions(self, text: str) -> ContentModerationPredictions:
        """
        Rule-based content moderation fallback when ML models fail to load.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of prediction dictionaries based on pattern matching
        """
        try:
            # Check for explicit patterns
            explicit_patterns = self._get_explicit_patterns()
            predictions = []
            
            text_lower = text.lower()
            
            # Check for offensive/explicit content
            explicit_score = 0.0
            for pattern in explicit_patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    explicit_score = 0.9  # High confidence for pattern matches
                    break
            
            if explicit_score > 0:
                predictions.append({
                    'label': 'offensive',
                    'score': explicit_score
                })
            else:
                predictions.append({
                    'label': 'not-offensive',
                    'score': 0.8  # Moderate confidence when no patterns found
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error in rule-based content predictions: {e}")
            # Return safe default
            return [{
                'label': 'not-offensive',
                'score': 0.5
            }]

    def _get_explicit_patterns(self) -> PatternList:
        """
        Return comprehensive patterns for explicit content detection.
        
        Returns:
            List of regex patterns for detecting explicit content including
            profanity, sexual content, violence, drugs, and hate speech
        """
        return [
            # Base profanity with common variations and leetspeak
            r'\b(?:f+u+c+k+|f+u+k+|f+c+k+|ph+u+c+k+|ph+u+k+|ph+c+k+|ph+[a@]g+[o0]t+|f+[a@]g+[o0]t+)\b',
            r'\b(?:sh+i+t+|sh+[i1]t+|s+h+i+t+|s+h+[i1]t+|[$]h[i1]t+|[$]h[!]t+|[$]h[!]\*+)\b',
            r'\b(?:b+i+t+c+h+|b+i+t+c+h+e+s+|b+i+t+c+h+i+n+g+|b+i+t+c+h+[e3]s+|b+i+t+c+h+[i!]n+g+)\b',
            r'\b(?:a+s+s+(?:h+[o0]l+e+|h+[o0]l+[e3]s*|w+i+p+e*|m+[u]n+[c*]h+[e3]r*|f+a+c+e*|c+l+[o0]w+n+[e3]*|w+a+d+))\b',
            r'\b(?:d+a+m+n+|d+a+m+[i!]t*|d+[a@]m+[i!]t*|d+[a@]m+[i!]t+)\b',
            r'\b(?:g+[o0]d+d+a+m+n+|g+[o0]d+d+a+m+[i!]t*|g+[o0]d+d+[a@]m+[i!]t*|g+[o0]d+d+[a@]m+[i!]t+)\b',
            r'\b(?:c+u+n+t+|c+u+n+[t7]s*|c+[o0]c+k+[s5]*|c+[o0]k+[s5]*|c+[o0]c+k+h+e*a*d*|k+[o0]c+k+[s5]*|k+[o0]k+[s5]*)\b',
            r'\b(?:p+u+s+s+y*|p+u+s+y*|p+u+z+y*|p+u+z+z+y*|p+u+s+i+e*|p+u+s+s+i+e*|p+u+z+z+i+e*|p+u+z+i+e*)\b',
            r'\b(?:w+h+[o0]r+[e3]+s*|h+[o0]e+s*|s+l+u+t+s*|s+l+u+t+t+y*|s+l+u+t+[i!]e*|s+l+u+t+[i!]e+s*|s+l+u+t+[i!]n+g*)\b',
            r'\b(?:b+a+s+t+a+r+d+|b+a+s+t+e+r+d+|b+a+s+t+[a@]r+d+)\b',
            
            # Sexual content patterns
            r'\b(?:s+e+x+u*a*l*|s+e+x+u*a*l*s*|s+e+x+u*a*l*[s5]*|s+e+x+u*a*l*[s5]*e*|s+e+x+u*a*l*[s5]*e*s*|s+e+x+u*a*l*[s5]*e*d*|s+e+x+u*a*l*[s5]*e*r*|s+e+x+u*a*l*[s5]*e*s*)\b',
            r'\b(?:p+o+r+n+o*|p+o+r+n+o*s*|p+o+r+n+o*[s5]*|p+o+r+n+o*[s5]*e*|p+o+r+n+o*[s5]*e*s*|p+o+r+n+o*[s5]*e*d*|p+o+r+n+o*[s5]*e*r*|p+o+r+n+o*[s5]*e*s*)\b',
            r'\b(?:x+[x]+[x]*|x+[x]+[x]*[s5]*|x+[x]+[x]*[s5]*e*|x+[x]+[x]*[s5]*e*s*|x+[x]+[x]*[s5]*e*d*|x+[x]+[x]*[s5]*e*r*|x+[x]+[x]*[s5]*e*s*)\b',
            
            # Violence-related patterns
            r'\b(?:k+i+l+l+|k+i+l+[i!]n+g*|k+i+l+[e3]d*|k+i+l+[e3]r*|k+i+l+[i!]e*s*|k+i+l+[i!]n*g+[s5]*|k+i+l+[e3]d+[s5]*|k+i+l+[e3]r+[s5]*|k+i+l+[i!]e*[s5]*)\b',
            r'\b(?:m+u+r+d+e+r+|m+u+r+d+e+r+s*|m+u+r+d+e+r+[s5]*|m+u+r+d+e+r+[s5]*e*|m+u+r+d+e+r+[s5]*e*s*|m+u+r+d+e+r+[s5]*e*d*|m+u+r+d+e+r+[s5]*e*r*|m+u+r+d+e+r+[s5]*e*s*)\b',
            r'\b(?:v+i+o+l+e+n+t+|v+i+o+l+e+n+c+e*|v+i+o+l+e+n+t+[s5]*|v+i+o+l+e+n+t+[s5]*e*|v+i+o+l+e+n+t+[s5]*e*s*|v+i+o+l+e+n+t+[s5]*e*d*|v+i+o+l+e+n+t+[s5]*e*r*|v+i+o+l+e+n+t+[s5]*e*s*)\b',
            
            # Drug-related patterns
            r'\b(?:d+r+u+g+s*|d+r+u+g+[s5]*|d+r+u+g+[s5]*e*|d+r+u+g+[s5]*e*s*|d+r+u+g+[s5]*e*d*|d+r+u+g+[s5]*e*r*|d+r+u+g+[s5]*e*s*)\b',
            r'\b(?:c+o+c+a+i+n+e*|c+o+k+e*|h+e+r+o+i+n*|m+e+t+h*|m+e+t+h+a+m+p+h+e+t+a+m+i+n+e*|e+c+s+t+a+s+y*|m+o+l+l+y*|m+d+m+a*|l+s+d*|a+c+i+d*|s+h+r+o+o+m+s*|m+u+s+h+r+o+o+m+s*|w+e+e+d*|m+a+r+i+j+u+a+n+a*|c+a+n+n+a+b+i+s*|p+o+t*|d+o+p+e*|g+a+n+j+a*|h+a+s+h*|o+p+i+u+m*|o+x+y*|o+x+y+c+o+n+t+i+n*|p+e+r+c+o+c+e+t*|v+i+c+o+d+i+n*|x+a+n+a+x*|v+a+l+i+u+m*|a+d+d+e+r+a+l+l*|r+i+t+a+l+i+n*|v+y+v+a+n+s+e*|c+o+d+e+i+n+e*|m+o+r+p+h+i+n+e*|f+e+n+t+a+n+y+l*)\b',
            
            # Racial and ethnic slurs
            r'\b(?:n+i+g+[e3]r+|n+i+g+g+[a@]|n+i+g+g+[a@]s*|n+i+g+g+[a@]z*|n+i+g+g+[a@]z+[s5]*|n+i+g+g+[a@]z+[s5]*e*|n+i+g+g+[a@]z+[s5]*e*s*|n+i+g+g+[a@]z+[s5]*e*d*|n+i+g+g+[a@]z+[s5]*e*r*|n+i+g+g+[a@]z+[s5]*e*s*)\b',
            r'\b(?:s+p+i+c*|s+p+i+k*|s+p+i+c+[s5]*|s+p+i+k+[s5]*|s+p+i+c+[s5]*e*|s+p+i+k+[s5]*e*|s+p+i+c+[s5]*e*s*|s+p+i+k+[s5]*e*s*|s+p+i+c+[s5]*e*d*|s+p+i+k+[s5]*e*d*|s+p+i+c+[s5]*e*r*|s+p+i+k+[s5]*e*r*|s+p+i+c+[s5]*e*s*|s+p+i+k+[s5]*e*s*)\b',
            r'\b(?:k+i+k+e*|k+y+k+e*|k+i+k+e*s*|k+y+k+e*s*|k+i+k+e*[s5]*|k+y+k+e*[s5]*|k+i+k+e*[s5]*e*|k+y+k+e*[s5]*e*|k+i+k+e*[s5]*e*s*|k+y+k+e*[s5]*e*s*|k+i+k+e*[s5]*e*d*|k+y+k+e*[s5]*e*d*|k+i+k+e*[s5]*e*r*|k+y+k+e*[s5]*e*r*|k+i+k+e*[s5]*e*s*|k+y+k+e*[s5]*e*s*)\b',
            r'\b(?:c+h+i+n+k*|c+h+i+n+q*|c+h+i+n+k+[s5]*|c+h+i+n+q+[s5]*|c+h+i+n+k+[s5]*e*|c+h+i+n+q+[s5]*e*|c+h+i+n+k+[s5]*e*s*|c+h+i+n+q+[s5]*e*s*|c+h+i+n+k+[s5]*e*d*|c+h+i+n+q+[s5]*e*d*|c+h+i+n+k+[s5]*e*r*|c+h+i+n+q+[s5]*e*r*|c+h+i+n+k+[s5]*e*s*|c+h+i+n+q+[s5]*e*s*)\b',
            r'\b(?:g+o+o+k*|g+o+o+q*|g+o+o+k+[s5]*|g+o+o+q+[s5]*|g+o+o+k+[s5]*e*|g+o+o+q+[s5]*e*|g+o+o+k+[s5]*e*s*|g+o+o+q+[s5]*e*s*|g+o+o+k+[s5]*e*d*|g+o+o+q+[s5]*e*d*|g+o+o+k+[s5]*e*r*|g+o+o+q+[s5]*e*r*|g+o+o+k+[s5]*e*s*|g+o+o+q+[s5]*e*s*)\b',
            r'\b(?:w+e+t+b+a+c+k*|w+e+t+b+a+c+k+s*|w+e+t+b+a+c+k+[s5]*|w+e+t+b+a+c+k+[s5]*e*|w+e+t+b+a+c+k+[s5]*e*s*|w+e+t+b+a+c+k+[s5]*e*d*|w+e+t+b+a+c+k+[s5]*e*r*|w+e+t+b+a+c+k+[s5]*e*s*)\b',
            r'\b(?:b+e+a+n+e*r*|b+e+a+n+e*r+s*|b+e+a+n+e*r+[s5]*|b+e+a+n+e*r+[s5]*e*|b+e+a+n+e*r+[s5]*e*s*|b+e+a+n+e*r+[s5]*e*d*|b+e+a+n+e*r+[s5]*e*r*|b+e+a+n+e*r+[s5]*e*s*)\b',
            r'\b(?:r+e+t+a+r+d*|r+e+t+a+r+d+s*|r+e+t+a+r+d+[s5]*|r+e+t+a+r+d+[s5]*e*|r+e+t+a+r+d+[s5]*e*s*|r+e+t+a+r+d+[s5]*e*d*|r+e+t+a+r+d+[s5]*e*r*|r+e+t+a+r+d+[s5]*e*s*)\b',
        ]

    def _load_koalaai_label_map(self) -> LabelMap:
        """
        Load the mapping from KoalaAI model labels to our internal flag system.
        This maps the model's output labels to our flag names, penalties, and categories.
        
        Returns:
            Mapping of KoalaAI labels to flag information including
            flag_name, penalty, and category for each label type
        """
        return {
            # Hate speech (HR, H2, hate, hate_speech, racism) - most severe (-75 points)
            'HR': {'flag_name': 'Hate Speech Detected', 'penalty': 75, 'category': 'hate'},
            'H2': {'flag_name': 'Hate Speech Detected', 'penalty': 75, 'category': 'hate'},
            'hate': {'flag_name': 'Hate Speech Detected', 'penalty': 75, 'category': 'hate'},
            'hate_speech': {'flag_name': 'Hate Speech Detected', 'penalty': 75, 'category': 'hate'},
            'racism': {'flag_name': 'Hate Speech Detected', 'penalty': 75, 'category': 'hate'},
            'harassment': {'flag_name': 'Hate Speech Detected', 'penalty': 75, 'category': 'hate'},
            'discrimination': {'flag_name': 'Hate Speech Detected', 'penalty': 75, 'category': 'hate'},
            'intolerance': {'flag_name': 'Hate Speech Detected', 'penalty': 75, 'category': 'hate'},
            
            # Offensive language (OR, OFF, offensive, profanity) - general profanity (-50 points)
            'OR': {'flag_name': 'Explicit Language / Corrupting Talk', 'penalty': 50, 'category': 'offensive'},
            'OFF': {'flag_name': 'Explicit Language / Corrupting Talk', 'penalty': 50, 'category': 'offensive'},
            'offensive': {'flag_name': 'Explicit Language / Corrupting Talk', 'penalty': 50, 'category': 'offensive'},
            'profanity': {'flag_name': 'Explicit Language / Corrupting Talk', 'penalty': 50, 'category': 'offensive'},
            'explicit': {'flag_name': 'Explicit Language / Corrupting Talk', 'penalty': 50, 'category': 'explicit'},
            'vulgar': {'flag_name': 'Explicit Language / Corrupting Talk', 'penalty': 50, 'category': 'offensive'},
            'obscene': {'flag_name': 'Explicit Language / Corrupting Talk', 'penalty': 50, 'category': 'offensive'},
            'inappropriate': {'flag_name': 'Explicit Language / Corrupting Talk', 'penalty': 50, 'category': 'offensive'},
            'abusive': {'flag_name': 'Explicit Language / Corrupting Talk', 'penalty': 50, 'category': 'offensive'},
            
            # Sexual content (S1, S2, S3, sexual, sex, pornography) (-50 points)
            'S1': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'S2': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'S3': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'sexual': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'sex': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'pornography': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'porn': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'xxx': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'nudity': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'nude': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'explicit_sexual': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            'sex_act': {'flag_name': 'Sexual Content / Impurity (overt)', 'penalty': 50, 'category': 'sexual'},
            
            # Violence (V1, V2, V3, violence, violent, assault) (-25 points)
            'V1': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'V2': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'V3': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'violence': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'violent': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'assault': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'harm': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'hurt': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'attack': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'fight': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'war': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'murder': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'kill': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'weapon': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            'gun': {'flag_name': 'Glorification of Violence', 'penalty': 25, 'category': 'violence'},
            
            # Drugs (D1, D2, drugs, drug, substance_abuse) (-25 points)
            'D1': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'D2': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'drugs': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'drug': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'substance_abuse': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'alcohol': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'marijuana': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'cocaine': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'heroin': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'meth': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'ecstasy': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'lsd': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'mdma': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'opioid': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'prescription_drugs': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'substance': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'intoxication': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'intoxicated': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'under_influence': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'getting_high': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            'getting_drunk': {'flag_name': 'Glorification of Drugs / Substance Abuse', 'penalty': 25, 'category': 'drugs'},
            
            # Self-harm (SH1, SH2, self_harm, suicide, self_injury) (-75 points)
            'SH1': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'SH2': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'self_harm': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'suicide': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'self_injury': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'self_hurt': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'self_destructive': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'suicidal': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'cutting': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'self_abuse': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'self_loathing': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'self_hatred': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'depression': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'hopelessness': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'despair': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            'giving_up': {'flag_name': 'Self-Harm References', 'penalty': 75, 'category': 'self_harm'},
            
            # OK - no penalty
            'OK': {'flag_name': 'Clean Content', 'penalty': 0, 'category': 'clean'},
            'clean': {'flag_name': 'Clean Content', 'penalty': 0, 'category': 'clean'},
            'safe': {'flag_name': 'Clean Content', 'penalty': 0, 'category': 'clean'},
            'appropriate': {'flag_name': 'Clean Content', 'penalty': 0, 'category': 'clean'},
            'family_friendly': {'flag_name': 'Clean Content', 'penalty': 0, 'category': 'clean'},
            'child_safe': {'flag_name': 'Clean Content', 'penalty': 0, 'category': 'clean'},
            'wholesome': {'flag_name': 'Clean Content', 'penalty': 0, 'category': 'clean'}
        }

    def _process_flag(self, label: str, score: ConfidenceScore, flag_info: Dict[str, Any], 
                     triggered_flags_details: FlagDetailsList, total_penalty: PenaltyScore) -> PenaltyScore:
        """
        Process a single flag and update the triggered flags and total penalty.
        
        Args:
            label: The label of the flag (e.g., 'hate', 'explicit', 'sexual')
            score: Confidence score from the model (0.0 to 1.0)
            flag_info: Dictionary containing flag metadata
            triggered_flags_details: List of already triggered flags (modified in place)
            total_penalty: Current total penalty score
            
        Returns:
            Updated total penalty score
        """
        # Map categories to their corresponding flag names and penalties
        # Lowered confidence thresholds to catch more explicit content
        category_mapping = {
            'hate': {
                'flag_name': 'Hate Speech Detected', 
                'penalty': 75,
                'confidence_threshold': 0.55  # Lowered from 0.7
            },
            'explicit': {
                'flag_name': 'Explicit Language / Corrupting Talk',
                'penalty': 50,
                'confidence_threshold': 0.5  # Lowered from 0.6
            },
            'sexual': {
                'flag_name': 'Sexual Content / Impurity (overt)',
                'penalty': 50,
                'confidence_threshold': 0.55  # Lowered from 0.65
            },
            'violence': {
                'flag_name': 'Glorification of Violence',
                'penalty': 25,
                'confidence_threshold': 0.5  # Lowered from 0.6
            },
            'drugs': {
                'flag_name': 'Glorification of Drugs / Substance Abuse',
                'penalty': 25,
                'confidence_threshold': 0.5  # Lowered from 0.6
            },
            'offensive': {
                'flag_name': 'Explicit Language / Corrupting Talk',
                'penalty': 50,
                'confidence_threshold': 0.5  # Lowered from 0.6
            },
            'self_harm': {
                'flag_name': 'Self-Harm References',
                'penalty': 75,
                'confidence_threshold': 0.6  # Lowered from 0.7
            }
        }
        
        # Get category info or use defaults
        category = flag_info.get('category', 'other')
        category_info = category_mapping.get(category, {
            'flag_name': f"Content Flagged as {label}",
            'penalty': 25,
            'confidence_threshold': 0.7
        })
        
        flag_name = flag_info.get('flag_name', category_info['flag_name'])
        penalty = flag_info.get('penalty', category_info['penalty'])
        confidence_threshold = flag_info.get('confidence_threshold', category_info['confidence_threshold'])
        
        logger.debug(f"Processing flag: {flag_name}, Penalty: {penalty}, Category: {category}, Confidence: {score:.2f}")
        
        if score >= confidence_threshold:
            # Check if we already have this flag type to avoid duplicates
            existing_flag = next((f for f in triggered_flags_details 
                               if f["flag"] == flag_name), None)
            
            if not existing_flag or score > existing_flag.get('confidence', 0):
                # If flag exists but with lower confidence, update it
                if existing_flag:
                    total_penalty -= existing_flag["penalty_applied"]
                    triggered_flags_details.remove(existing_flag)
                
                # Add the flag with the highest confidence score
                triggered_flags_details.append({
                    "flag": flag_name,
                    "details": f"Detected '{label}' with confidence {score:.2f}",
                    "penalty_applied": penalty,
                    "confidence": score,
                    "source": "content_moderation",
                    "category": category
                })
                total_penalty += penalty
                logger.info(f"Applied penalty of {penalty} for {flag_name} (confidence: {score:.2f})")
            else:
                logger.debug(f"Skipping duplicate flag {flag_name} with lower confidence {score:.2f} < {existing_flag['confidence']:.2f}")
        else:
            logger.debug(f"Skipping {label} due to low confidence: {score:.2f} < {confidence_threshold}")
        
        return total_penalty
        
    def _detect_christian_purity_flags(self, content_moderation_predictions: Optional[List[Dict[str, Any]]] = None, lyrics_text: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        """
        Detect Christian purity flags based on content moderation predictions and pattern matching.
        
        Args:
            content_moderation_predictions: List of prediction dictionaries from content moderation
            lyrics_text: The lyrics text to analyze for explicit content
            
        Returns:
            Tuple of (triggered_flags_details, total_penalty) where:
                - triggered_flags_details: List of dicts with flag details
                - total_penalty: Total penalty score (0-100)
        """
        logger.debug("Detecting Christian purity flags")
        triggered_flags_details: FlagDetailsList = []
        total_penalty: PenaltyScore = 0
        
        try:
            # Explicit type annotation to fix mypy error
            predictions_list: Optional[List[Dict[str, Any]]] = content_moderation_predictions
            
            # Check if we have predictions to process
            if predictions_list is None or len(predictions_list) == 0:
                logger.info("No content moderation predictions to process")
                return triggered_flags_details, total_penalty
            
            logger.info(f"Processing {len(predictions_list)} content moderation predictions")
            
            # Get the label mapping from the rubric
            label_map = self.christian_rubric.get("purity_flag_definitions", {}).get("cardiffnlp_model_map", {})
            
            # Add explicit label mapping if not present
            if 'explicit' not in label_map:
                label_map['explicit'] = {
                    'flag_name': 'Explicit Language / Corrupting Talk',
                    'penalty': 50
                }
            
            # Process each prediction
            for pred in predictions_list:
                if not isinstance(pred, dict) or 'label' not in pred or 'score' not in pred:
                    continue
                    
                label = pred.get('label', '').lower()
                score = float(pred.get('score', 0))
                
                # Log the prediction for debugging
                logger.debug(f"Processing prediction - Label: {label}, Score: {score:.4f}")
                
                # Skip 'OK' label as it's handled in _get_content_moderation_predictions
                if label == 'ok':
                    # Only log OK if it's the only prediction
                    if len(predictions_list) == 1:
                        logger.info(f"Only 'OK' prediction with score {score:.4f}")
                    continue
                
                # Check if this label maps to a flag
                flag_info = label_map.get(label)
                if flag_info:
                    logger.info(f"Processing flag: {label} (score: {score:.4f})")
                    total_penalty = self._process_flag(
                        label=label,
                        score=score,
                        flag_info=flag_info,
                        triggered_flags_details=triggered_flags_details,
                        total_penalty=total_penalty
                    )
            
            # Additional check for explicit patterns if we have lyrics text and no flags yet
            if lyrics_text and not triggered_flags_details:
                explicit_patterns = self._get_explicit_patterns()
                for pattern in explicit_patterns:
                    if re.search(pattern, lyrics_text, re.IGNORECASE):
                        # Add explicit language flag with high confidence
                        penalty = 50
                        triggered_flags_details.append({
                            'flag': 'Explicit Language / Corrupting Talk',
                            'penalty_applied': penalty,
                            'confidence': 0.95,
                            'details': f'Matched explicit pattern: {pattern}'
                        })
                        total_penalty += penalty
                        logger.warning(f"Applied penalty of {penalty} for explicit pattern match")
                        break  # Only need one match
            
            # Ensure we don't exceed 100% penalty
            total_penalty = min(total_penalty, 100)
            
            # Log the results
            if triggered_flags_details:
                logger.warning(f"Detected {len(triggered_flags_details)} purity flags with total penalty {total_penalty}")
                for flag in triggered_flags_details:
                    logger.warning(f"Flag: {flag['flag']}, Penalty: {flag.get('penalty_applied', 0)}, Confidence: {flag.get('confidence', 0):.2f}")
            else:
                logger.info("No purity flags detected")
            
            return triggered_flags_details, total_penalty
            
        except Exception as e:
            logger.error(f"Error detecting Christian purity flags: {e}", exc_info=True)
            # On error, be conservative and flag as potentially explicit
            return [{
                'flag': 'Potential Explicit Content',
                'penalty_applied': 30,
                'confidence': 0.5,
                'details': f'Error during analysis: {str(e)}'
            }], 30
    def _detect_christian_themes(self, lyrics_text: Optional[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Detect Christian themes in song lyrics.
        
        Args:
            lyrics_text: The lyrics text to analyze for Christian themes
            
        Returns:
            Tuple of (positive_themes, negative_themes) where each is a list of theme dicts
        """
        logger.debug("Detecting Christian themes in lyrics")
        positive_themes: ThemeDetailsList = []
        negative_themes: ThemeDetailsList = []
        
        if not lyrics_text:
            logger.debug("No lyrics provided for theme detection")
            return positive_themes, negative_themes
            
        # Convert to lowercase for case-insensitive matching
        lyrics_lower: str = lyrics_text.lower()
        
        # Debug: Print the rubric config
        logger.debug(f"Positive themes config: {self.christian_rubric.get('positive_themes_config', [])}")
        logger.debug(f"Negative themes config: {self.christian_rubric.get('negative_themes_config', [])}")
        
        # Check positive themes
        for theme_config in self.christian_rubric.get("positive_themes_config", []):
            theme_name: str = theme_config.get("name", "Unknown")
            keywords: List[str] = theme_config.get("keywords", [])
            
            # Check if any keyword is in the lyrics
            matches: List[str] = [kw for kw in keywords if kw.lower() in lyrics_lower]
            if matches:
                theme: ThemeDetails = {
                    "theme": theme_name,
                    "details": f"Keywords found: {', '.join(matches)}",
                    "scripture_references": theme_config.get("scripture_keywords", []),
                    "matched_keywords": matches
                }
                positive_themes.append(theme)
                logger.debug(f"Detected positive theme: {theme_name} with keywords: {matches}")
        
        # Check negative themes
        for theme_config in self.christian_rubric.get("negative_themes_config", []):
            theme_name = theme_config.get("name", "Unknown")
            keywords = theme_config.get("keywords", [])
            
            # Debug: Print the theme being checked
            logger.debug(f"Checking negative theme: {theme_name} with keywords: {keywords}")
            
            # Check if any keyword is in the lyrics
            matches = [kw for kw in keywords if kw.lower() in lyrics_lower]
            if matches:
                theme = {
                    "theme": theme_name,
                    "details": f"Keywords found: {', '.join(matches)}",
                    "scripture_references": theme_config.get("scripture_keywords", []),
                    "matched_keywords": matches
                }
                negative_themes.append(theme)
                logger.info(f"Detected negative theme: {theme_name} with keywords: {matches}")
            else:
                logger.debug(f"No matches found for negative theme: {theme_name}")
        
        logger.info(f"Detected {len(positive_themes)} positive and {len(negative_themes)} negative themes")
        return positive_themes, negative_themes

    def _calculate_christian_score_and_concern(self, purity_flags_details: List[Dict[str, Any]], total_purity_penalty: int, positive_themes: List[Dict[str, Any]], negative_themes: List[Dict[str, Any]]) -> Tuple[int, str]:
        logger.debug("Executing full _calculate_christian_score_and_concern")

        rubric = self.christian_rubric
        score = rubric.get("baseline_score", 100)
        
        # Log initial values
        logger.info("=== Starting Score Calculation ===")
        logger.info(f"Initial score: {score}")
        logger.info(f"Purity flags: {[f['flag'] for f in purity_flags_details] if purity_flags_details else 'None'}")
        logger.info(f"Positive themes: {[t['theme'] for t in positive_themes] if positive_themes else 'None'}")
        logger.info(f"Negative themes: {[t['theme'] for t in negative_themes] if negative_themes else 'None'}")

        # Debug: Print all rubric values
        logger.info("=== Rubric Values ===")
        for key, value in rubric.items():
            if key not in ["positive_themes_config", "negative_themes_config", "purity_flag_definitions"]:
                logger.info(f"{key}: {value}")
        
        logger.info("=== Score Calculation Steps ===")
        logger.info(f"1. Starting score: {score}")

        # Apply purity penalty (already calculated by _detect_christian_purity_flags)
        score_before = score
        score -= total_purity_penalty
        logger.info(f"2. After purity penalty (-{total_purity_penalty}): {score_before} -> {score}")

        # Apply negative theme penalties
        num_negative_themes = len(negative_themes)
        negative_theme_penalty = rubric.get("negative_theme_penalty", 10)
        negative_penalty = num_negative_themes * negative_theme_penalty
        score_before = score
        score -= negative_penalty
        logger.info(f"3. After negative themes (-{negative_penalty} = {num_negative_themes} themes * {negative_theme_penalty}): {score_before} -> {score}")
        logger.info(f"   Negative themes: {[t['theme'] for t in negative_themes] if negative_themes else 'None'}")

        # Apply positive theme points (capped at 20 points max to prevent gaming the system)
        num_positive_themes = len(positive_themes)
        positive_theme_points = rubric.get("positive_theme_points", 5)
        positive_points = min(num_positive_themes * positive_theme_points, 20)  # Cap at +20
        score_before = score
        score += positive_points
        logger.info(f"4. After positive themes (+{positive_points} = {num_positive_themes} themes * {positive_theme_points}, capped at 20): {score_before} -> {score}")

        # Cap the score
        min_cap = rubric.get("score_min_cap", 0)
        max_cap = rubric.get("score_max_cap", 100)
        score_before = score
        score = max(min_cap, min(score, max_cap))
        logger.info(f"5. After capping (min: {min_cap}, max: {max_cap}): {score_before} -> {score}")
        
        logger.info("=== Final Score ===")
        logger.info(f"Final score: {score}")
        logger.info("===================")

        # Determine concern level based on score thresholds
        thresholds = rubric.get("concern_thresholds", {})
        low_starts_at = thresholds.get("low_starts_at", 80)
        medium_starts_at = thresholds.get("medium_starts_at", 60)
        high_starts_at = thresholds.get("high_starts_at", 40)

        # Determine level based on score first
        if score >= low_starts_at:  # 80-100
            concern_level = "Low"
            reason = f"Score ({score}) in Low concern range (80-100)"
        elif score >= medium_starts_at:  # 60-79
            concern_level = "Medium"
            reason = f"Score ({score}) in Medium concern range (60-79)"
        elif score >= high_starts_at:  # 40-59
            concern_level = "High"
            reason = f"Score ({score}) in High concern range (40-59)"
        else:  # 0-39
            concern_level = "Extreme"
            reason = f"Score ({score}) in Extreme concern range (0-39)"
            
        # Purity flags can only increase concern level, not decrease it
        if purity_flags_details:
            if concern_level == "Low":
                concern_level = "High"
                reason = "Purity flag detected, increasing concern level to High"
            elif concern_level == "Medium" and concern_level != "High" and concern_level != "Extreme":
                concern_level = "High"
                reason = "Purity flag detected, increasing concern level to High"
            # If already High or Extreme, keep it as is
        
        logger.info(f"Final score: {score}, Concern level: {concern_level} - {reason}")
        return int(score), concern_level

    def _get_christian_supporting_scripture(self, triggered_components: Dict[str, List[str]]) -> Dict[str, Any]:
        logger.debug("Stub: _get_christian_supporting_scripture called. Returning empty scripture dict.")
        # Actual implementation would use self.bible_client and mappings from self.christian_rubric
        # to find and format scripture for triggered themes and flags.
        # triggered_components might be like: {"positive_themes": ["Faith / Trust in God"], "purity_flags": ["Explicit Language"]}
        return {}

    def analyze_song(self, title: str, artist: str, lyrics_text: Optional[str] = None, 
                    fetch_lyrics_if_missing: bool = True, is_explicit: bool = False) -> Dict[str, Any]:
        # Import metrics tracking
        from ..utils.metrics import metrics_collector
        from ..utils.logging import log_analysis_metrics
        
        start_time = time.time()
        log_prefix = f"[User {self.user_id}] " if self.user_id else ""
        
        # Log the start of analysis with comprehensive context
        logger.info(f"{log_prefix}🔍 Starting Song Analysis", extra={
            'extra_fields': {
                'song_title': title,
                'song_artist': artist,
                'user_id': self.user_id,
                'is_explicit': is_explicit,
                'lyrics_provided': lyrics_text is not None,
                'fetch_lyrics_enabled': fetch_lyrics_if_missing,
                'analysis_type': 'comprehensive'
            }
        })
        
        # Default analysis results with safe defaults
        analysis_results = {
            "title": title,
            "artist": artist,
            "analyzed_by_user_id": self.user_id,
            "is_explicit": is_explicit,
            "lyrics_provided": lyrics_text is not None,
            "lyrics_fetched_successfully": False,
            "lyrics_used_for_analysis": "",
            "cardiffnlp_raw_predictions": [],
            "alternative_model_raw_predictions": {},
            "christian_purity_flags_details": [],
            "christian_positive_themes_detected": [],
            "christian_negative_themes_detected": [],
            "christian_score": self.christian_rubric.get("baseline_score", 100),
            "christian_concern_level": "Low",  # Default, will be updated
            "christian_supporting_scripture": {},
            "warnings": [],
            "errors": []
        }

        try:
            # 1. Get Lyrics
            if not lyrics_text and fetch_lyrics_if_missing:
                logger.info(f"{log_prefix}📝 Fetching lyrics", extra={
                    'extra_fields': {
                        'song_title': title,
                        'song_artist': artist,
                        'lyrics_source': 'external_fetch'
                    }
                })
                try:
                    fetch_start = time.time()
                    # Add null check for lyrics_fetcher
                    if self.lyrics_fetcher is not None:
                        lyrics_text = self.lyrics_fetcher.fetch_lyrics(title, artist)
                    else:
                        logger.warning(f"{log_prefix}❌ Lyrics fetcher not available")
                        lyrics_text = None
                        
                    fetch_duration = time.time() - fetch_start
                    
                    if lyrics_text:
                        logger.info(f"{log_prefix}✅ Lyrics fetched successfully", extra={
                            'extra_fields': {
                                'song_title': title,
                                'lyrics_length': len(lyrics_text),
                                'fetch_duration_ms': round(fetch_duration * 1000, 2),
                                'lyrics_source': 'genius_api'
                            }
                        })
                        analysis_results["lyrics_fetched_successfully"] = True
                        
                        # Track lyrics fetch metrics
                        metrics_collector.track_api_request(
                            endpoint='lyrics_fetch',
                            method='GET',
                            status_code=200,
                            duration=fetch_duration * 1000
                        )
                    else:
                        logger.warning(f"{log_prefix}❌ No lyrics found", extra={
                            'extra_fields': {
                                'song_title': title,
                                'song_artist': artist,
                                'fetch_duration_ms': round(fetch_duration * 1000, 2),
                                'reason': 'not_found'
                            }
                        })
                        analysis_results["warnings"].append("Failed to fetch lyrics. Analysis will be limited.")
                        
                        # Track failed lyrics fetch
                        metrics_collector.track_api_request(
                            endpoint='lyrics_fetch',
                            method='GET',
                            status_code=404,
                            duration=fetch_duration * 1000
                        )
                except Exception as e:
                    fetch_duration = time.time() - fetch_start if 'fetch_start' in locals() else 0
                    logger.error(f"{log_prefix}💥 Error fetching lyrics", extra={
                        'extra_fields': {
                            'song_title': title,
                            'song_artist': artist,
                            'error_type': type(e).__name__,
                            'error_message': str(e),
                            'fetch_duration_ms': round(fetch_duration * 1000, 2)
                        }
                    }, exc_info=True)
                    error_msg = f"Error fetching lyrics: {str(e)}"
                    analysis_results["warnings"].append(error_msg)
                    analysis_results["errors"].append(error_msg)
                    
                    # Track error metrics
                    metrics_collector.track_api_request(
                        endpoint='lyrics_fetch',
                        method='GET',
                        status_code=500,
                        duration=fetch_duration * 1000
                    )
            
            if not lyrics_text:
                error_msg = "No lyrics available for analysis. Using default scoring."
                logger.warning(f"No lyrics available for '{title}' by '{artist}'. Analysis will be limited.")
                analysis_results["warnings"].append(error_msg)
                analysis_results["errors"].append(error_msg)
                # Set default values for required fields
                analysis_results.update({
                    "christian_score": self.christian_rubric.get("baseline_score", 100),
                    "christian_concern_level": "Low",
                    "christian_purity_flags_details": [],
                    "christian_positive_themes_detected": [],
                    "christian_negative_themes_detected": [],
                    "christian_supporting_scripture": {}
                })
                return analysis_results

            # 2. Preprocess Lyrics
            try:
                processed_lyrics = self._preprocess_lyrics(lyrics_text)
                analysis_results["lyrics_used_for_analysis"] = processed_lyrics
            except Exception as e:
                logger.error(f"Error preprocessing lyrics: {e}", exc_info=True)
                analysis_results["errors"].append(f"Error preprocessing lyrics: {str(e)}")
                return analysis_results

            # 3. Content Moderation Analysis
            content_moderation_predictions = []
            try:
                if processed_lyrics:
                    content_moderation_predictions = self._get_content_moderation_predictions(processed_lyrics)
                    analysis_results["content_moderation_raw_predictions"] = content_moderation_predictions
            except Exception as e:
                logger.error(f"Error in content moderation analysis: {e}", exc_info=True)
                analysis_results["warnings"].append("Content analysis may be incomplete due to processing error.")
                # Continue with empty predictions rather than failing completely

            # 4. Detect Christian Purity Flags (based on model outputs)
            try:
                purity_flags_details, total_purity_penalty = self._detect_christian_purity_flags(
                    content_moderation_predictions, processed_lyrics
                )
                
                # Add explicit content flag if song is marked as explicit in Spotify
                if is_explicit:
                    explicit_flag: Dict[str, Any] = {
                        "flag": "Explicit Content (Spotify Flag)",
                        "category": "explicit",
                        "penalty": 50,  # Same as other explicit content
                        "confidence": 1.0,  # 100% confident since it's from Spotify
                        "source": "spotify_explicit_flag"
                    }
                    purity_flags_details.append(explicit_flag)
                    total_purity_penalty += int(explicit_flag["penalty"])
                    logger.info(f"Added explicit content flag based on Spotify's explicit flag")
                
                analysis_results["christian_purity_flags_details"] = purity_flags_details
                
                # Log the flags for user context
                if purity_flags_details and self.user_id:
                    flag_names = ", ".join([f.get("flag", "Unknown") for f in purity_flags_details])
                    logger.info(f"User {self.user_id}: Detected purity flags: {flag_names}")
                    
            except Exception as e:
                logger.error(f"Error detecting purity flags: {e}", exc_info=True)
                analysis_results["warnings"].append("Error during purity flag detection. Using default flags.")
                purity_flags_details = []
                total_purity_penalty = 0

            # 5. Detect Christian Themes (Positive and Negative)
            positive_themes: List[Dict[str, Any]] = []
            negative_themes: List[Dict[str, Any]] = []
            try:
                positive_themes, negative_themes = self._detect_christian_themes(processed_lyrics)
                analysis_results["christian_positive_themes_detected"] = positive_themes
                analysis_results["christian_negative_themes_detected"] = negative_themes
                
                # Log theme detection results with user context
                if positive_themes and self.user_id:
                    theme_names = ", ".join([t.get("theme", "Unknown") for t in positive_themes])
                    logger.info(f"{log_prefix}Detected positive themes: {theme_names}")
                if negative_themes and self.user_id:
                    theme_names = ", ".join([t.get("theme", "Unknown") for t in negative_themes])
                    logger.info(f"{log_prefix}Detected negative themes: {theme_names}")
                    
            except Exception as e:
                logger.error(f"{log_prefix}Error detecting themes: {e}", exc_info=True)
                analysis_results["warnings"].append("Error during theme detection. Using default themes.")
                # Use empty lists as defaults
                positive_themes = []
                negative_themes = []

            # 6. Calculate Christian Score and Concern Level
            try:
                christian_score, concern_level = self._calculate_christian_score_and_concern(
                    purity_flags_details, total_purity_penalty, positive_themes, negative_themes
                )
                analysis_results["christian_score"] = christian_score
                analysis_results["christian_concern_level"] = concern_level
            except Exception as e:
                logger.error(f"Error calculating score: {e}", exc_info=True)
                analysis_results["warnings"].append("Error calculating score. Using default scoring.")
                # Use baseline score from rubric if calculation fails
                analysis_results["christian_score"] = self.christian_rubric.get("baseline_score", 100)
                analysis_results["christian_concern_level"] = "Low"

            # 7. Get Supporting Scripture (if any flags or themes were detected)
            try:
                if purity_flags_details or positive_themes or negative_themes:
                    triggered_components = {
                        "purity_flags": [flag.get("flag", "") for flag in purity_flags_details],
                        "positive_themes": [theme.get("theme", "") for theme in positive_themes],
                        "negative_themes": [theme.get("theme", "") for theme in negative_themes]
                    }
                    supporting_scripture = self._get_christian_supporting_scripture(triggered_components)
                    analysis_results["christian_supporting_scripture"] = supporting_scripture
                else:
                    # Provide default scripture structure
                    analysis_results["christian_supporting_scripture"] = {
                        'verses': [],
                        'themes_covered': [theme.get('theme', '') for theme in positive_themes[:3]],  # Top 3 themes
                        'recommendation_basis': [f"Score: {analysis_results.get('christian_score', 100)}, Level: {analysis_results.get('christian_concern_level', 'Low')}"]
                    }
            except Exception as e:
                logger.error(f"Error getting supporting scripture: {e}", exc_info=True)
                analysis_results["warnings"].append("Error retrieving supporting scripture references.")
                # Provide fallback scripture structure
                analysis_results["christian_supporting_scripture"] = {
                    'verses': [],
                    'themes_covered': [theme.get('theme', '') for theme in positive_themes[:3]],
                    'recommendation_basis': [f"Score: {analysis_results.get('christian_score', 100)}, Level: {analysis_results.get('christian_concern_level', 'Low')}"]
                }
            
            # 8. Add explanation field based on analysis results
            try:
                num_positive = len(positive_themes)
                num_flags = len(purity_flags_details)
                concern_level = analysis_results.get('christian_concern_level', 'Low')
                christian_score = analysis_results.get('christian_score', 100)
                
                if concern_level == 'Low':
                    analysis_results['explanation'] = f"This song is well-aligned with Christian values, featuring {num_positive} positive Christian themes with minimal concerning content."
                elif concern_level == 'Medium':
                    analysis_results['explanation'] = f"This song has {num_positive} positive Christian themes but also contains {num_flags} areas of concern requiring discretion."
                else:
                    analysis_results['explanation'] = f"This song contains significant content concerns ({num_flags} flags detected) that may not align with Christian values despite {num_positive} positive themes."
                
                # Add explicit flag context if provided
                if is_explicit:
                    analysis_results['explicit_flag'] = True
                    analysis_results['recommendation'] = f"Analysis complete (Song marked as explicit)"
                    
            except Exception as e:
                logger.error(f"Error generating explanation: {e}", exc_info=True)
                analysis_results['explanation'] = "Analysis completed successfully."
        except Exception as e:
            logger.error(f"{log_prefix}Unexpected error during song analysis: {e}", exc_info=True)
            analysis_results["errors"].append(f"Unexpected error during analysis: {str(e)}")

        # Ensure we always have required fields even in case of error
        analysis_results.setdefault("christian_score", self.christian_rubric.get("baseline_score", 100))
        analysis_results.setdefault("christian_concern_level", "Medium")
            
        # Ensure errors key is always present (empty list if no errors)
        if "errors" not in analysis_results:
            analysis_results["errors"] = []
            
        # Clean up warnings list if empty (but keep the key if it exists with an empty list)
        if not analysis_results.get("warnings"):
            analysis_results["warnings"] = []
            
        # Calculate total analysis duration
        total_duration = time.time() - start_time
        
        # Log comprehensive completion details
        logger.info(f"{log_prefix}✅ Song Analysis Complete", extra={
            'extra_fields': {
                'song_title': title,
                'song_artist': artist,
                'user_id': self.user_id,
                'analysis_duration_ms': round(total_duration * 1000, 2),
                'christian_score': analysis_results.get('christian_score', 0),
                'concern_level': analysis_results.get('christian_concern_level', 'Unknown'),
                'purity_flags_count': len(analysis_results.get('christian_purity_flags_details', [])),
                'positive_themes_count': len(analysis_results.get('christian_positive_themes_detected', [])),
                'negative_themes_count': len(analysis_results.get('christian_negative_themes_detected', [])),
                'warnings_count': len(analysis_results.get('warnings', [])),
                'errors_count': len(analysis_results.get('errors', [])),
                'lyrics_available': bool(analysis_results.get('lyrics_used_for_analysis')),
                'analysis_success': len(analysis_results.get('errors', [])) == 0
            }
        })
        
        # Track analysis metrics
        success = len(analysis_results.get('errors', [])) == 0
        log_analysis_metrics(
            song_id=0,  # We don't have song ID at this level
            duration=total_duration,
            success=success,
            christian_score=analysis_results.get('christian_score', 0),
            concern_level=analysis_results.get('christian_concern_level', 'Unknown'),
            purity_flags_count=len(analysis_results.get('christian_purity_flags_details', [])),
            user_id=self.user_id
        )
        
        return analysis_results


if __name__ == '__main__':
    # Configure basic logging for standalone script execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # Set transformers pipeline logging to WARNING to reduce noise, unless debugging
    logging.getLogger("transformers.pipelines").setLevel(logging.WARNING)

    # Initialize analyzer
    # Pass 'cpu' explicitly if CUDA is available but not desired for this test, or to ensure consistency.
    # analyzer = SongAnalyzer(device='cpu') 
    analyzer = SongAnalyzer() # Auto-detects device

    # Test cases
    test_songs: List[Dict[str, Optional[str]]] = [
        {"title": "WAP", "artist": "Cardi B", "lyrics": "Yeah, you fuckin' with some wet-ass pussy"},
        {"title": "Short Safe Song", "artist": "Test Artist", "lyrics": "god is good jesus is lord glory hallelujah"},
        {"title": "Short Bad Song", "artist": "Test Artist", "lyrics": "This is damn offensive shit and drugs"},
        {"title": "Song with Hate Speech", "artist": "Test Artist", "lyrics": "i hate all those people they are scum"},
        {"title": "Empty Lyrics Song", "artist": "Test Artist", "lyrics": ""},
        {"title": "No Lyrics Provided Song", "artist": "Test Artist", "lyrics": None}
    ]

    for song_data in test_songs:
        song_title = song_data.get("title", "Unknown")
        song_artist = song_data.get("artist", "Unknown")
        song_lyrics = song_data.get("lyrics")
        
        if song_lyrics is not None:
            result = analyzer.analyze_song(song_title, song_artist, lyrics_text=song_lyrics)
        else:
            # Test fetching if lyrics are None (will fail if LYRICSGENIUS_API_KEY not set or song not found)
            logger.info(f"\nAttempting to fetch lyrics for {song_title} (ensure API key is set if testing this)...")
            result = analyzer.analyze_song(song_title, song_artist, fetch_lyrics_if_missing=True)
        
        logger.info(f"\n--- {song_artist} - {song_title} ---")
        import json
        logger.info(json.dumps(result, indent=2))

    # Example of fetching lyrics for a known song if API key is available
    logger.info("\nAttempting to fetch lyrics for a song (ensure API key is set)...")
    fetched_result = analyzer.analyze_song("Stairway to Heaven", "Led Zeppelin", fetch_lyrics_if_missing=True)
    logger.info(f"\n--- Led Zeppelin - Stairway to Heaven (Fetched) ---")
    logger.info(json.dumps(fetched_result, indent=2))
