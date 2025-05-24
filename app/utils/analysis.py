import logging
import os
import re
from typing import Optional, Dict, Any, List, Tuple

import torch
from dotenv import load_dotenv

from ..config.christian_rubric import get_christian_rubric
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)

# Fallback/Dummy implementations if main imports fail (e.g. running standalone for basic tests)
# Actual classes are expected to be imported from .lyrics and .bible_client
try:
    from .lyrics import LyricsFetcher
    from .bible_client import BibleClient
except ImportError:
    logger.warning("Could not import LyricsFetcher or BibleClient from .lyrics/.bible_client. Using dummy fallbacks.")
    class LyricsFetcher:
        def fetch_lyrics(self, title, artist):
            logger.info(f"Dummy LyricsFetcher: fetch_lyrics for {title} by {artist}")
            return None

    class BibleClient:
        BSB_ID = "dummy_bsb_id"
        KJV_ID = "dummy_kjv_id"
        def __init__(self, preferred_bible_id=None):
            logger.info("Dummy BibleClient initialized")
            self.api_key = os.getenv("BIBLE_API_KEY")
            if not self.api_key:
                logger.warning("BIBLE_API_KEY not found for Dummy BibleClient, scripture fetching will fail.")
            self.default_bible_id = preferred_bible_id if preferred_bible_id else self.BSB_ID
            self.fallback_bible_id = self.KJV_ID

        def get_scripture_passage(self, reference: str, bible_id: Optional[str] = None) -> Dict[str, Any]:
            logger.info(f"Dummy BibleClient: get_scripture_passage for {reference}")
            return {"content": "Dummy scripture not found.", "reference": reference, "error": "Dummy client"}

        def get_verses_for_theme(self, theme_name: str, scripture_refs: List[str]) -> List[Dict[str, Any]]:
            logger.info(f"Dummy BibleClient: get_verses_for_theme for {theme_name}")
            return []

class SongAnalyzer:
    def __init__(self, device: Optional[str] = None, user_id: Optional[int] = None):
        """
        Initialize the SongAnalyzer.
        
        Args:
            device: The device to use for model inference (e.g., 'cuda' or 'cpu').
                   If None, will use CUDA if available, otherwise CPU.
            user_id: Optional ID of the user who requested the analysis.
        """
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.user_id = user_id
        logger.info(f"SongAnalyzer using device: {self.device}")

        self.christian_rubric = get_christian_rubric()
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
        self.content_moderation_model_name = "KoalaAI/Text-Moderation"
        
        # Initialize model pipeline
        self.content_moderation_classifier = None  # Will hold the content moderation pipeline
        
        self._load_models() # Load all necessary models

        # Initialize services with proper configuration
        try:
            # Try to get the API keys from the environment or Flask config
            genius_token = os.environ.get('LYRICSGENIUS_API_KEY')
            bible_api_key = os.environ.get('BIBLE_API_KEY')
            
            # If we're in a Flask app context, try to get from config
            try:
                from flask import current_app
                if current_app:
                    if not genius_token and 'LYRICSGENIUS_API_KEY' in current_app.config:
                        genius_token = current_app.config['LYRICSGENIUS_API_KEY']
                    if not bible_api_key and 'BIBLE_API_KEY' in current_app.config:
                        bible_api_key = current_app.config['BIBLE_API_KEY']
            except (RuntimeError, ImportError):  # Not in Flask app context or Flask not available
                pass
            
            # Initialize services with the API keys
            self.lyrics_fetcher = LyricsFetcher(genius_token=genius_token)
            self.bible_client = BibleClient()  # It will use the environment variable we set
            self.bsb_bible_id = BibleClient.BSB_ID
            self.kjv_bible_id = BibleClient.KJV_ID
            
        except Exception as e:
            logger.error(f"Error initializing SongAnalyzer services: {e}", exc_info=True)
            # Initialize with None values if there's an error
            self.lyrics_fetcher = None
            self.bible_client = None
            self.bsb_bible_id = None
            self.kjv_bible_id = None
        
    def _load_models(self):
        """Load all necessary models for analysis with progress tracking."""
        import time
        from tqdm import tqdm
        
        logger.info("Loading content moderation model...")
        start_time = time.time()
        
        try:
            # Show progress while downloading/loading the model
            with tqdm(desc="Downloading model", unit="B", unit_scale=True, unit_divisor=1024) as pbar:
                def update_progress(block_num, block_size, total_size):
                    if pbar.total != total_size:
                        pbar.total = total_size
                    pbar.update(block_size)
                
                # Load content moderation model with progress tracking
                logger.info(f"Loading content moderation model: {self.content_moderation_model_name}")
                self.content_moderation_classifier = pipeline(
                    "text-classification",
                    model=self.content_moderation_model_name,
                    device=self.device,
                    framework="pt"
                )
                
            load_time = time.time() - start_time
            logger.info(f"Content moderation model loaded successfully in {load_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error loading content moderation model: {e}", exc_info=True)
            # Provide more helpful error message
            logger.error("If the model fails to load, you may need to manually download it first:")
            logger.error(f"from transformers import AutoModelForSequenceClassification, AutoTokenizer")
            logger.error(f"model = AutoModelForSequenceClassification.from_pretrained('{self.content_moderation_model_name}')")
            logger.error(f"tokenizer = AutoTokenizer.from_pretrained('{self.content_moderation_model_name}')")
            # Set to None to indicate loading failed
            self.content_moderation_classifier = None

    def _get_sensitive_content_score_bert(self, text: str) -> Dict[str, float]:
        # This method seems to be from an older Bert-based sensitivity scorer.
        # For now, it's not directly used by the main purity flag logic, which relies on CardiffNLP.
        # If it's needed for an 'alternative_model_raw_predictions', it would be implemented here.
        logger.debug("Stub: _get_sensitive_content_score_bert called. Returning empty dict.")
        return {}

    def _preprocess_lyrics(self, lyrics: str) -> str:
        logger.debug("Executing full _preprocess_lyrics")
        if not lyrics:
            return ""
        # Convert to lowercase
        processed_lyrics = lyrics.lower()
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

    def _get_content_moderation_predictions(self, text: str, chunk_size: int = 500) -> List[Dict[str, Any]]:
        """
        Get content moderation predictions using the KoalaAI/Text-Moderation model.
        
        Args:
            text: The text to analyze
            chunk_size: Maximum number of tokens per chunk (default: 500)
            
        Returns:
            List of prediction dictionaries with 'label' and 'score' keys,
            sorted by score in descending order
        """
        logger.debug("Executing _get_content_moderation_predictions")
        if not self.content_moderation_classifier or not text:
            logger.warning("Content moderation classifier not loaded or empty text, returning empty predictions.")
            return []
        
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
            sentences = re.split(r'(?<=[.!?])\s+', text)
            current_chunk = []
            chunks = []
            current_length = 0
            
            # Create chunks of text that are roughly chunk_size tokens
            for sentence in sentences:
                sentence_length = len(sentence.split())
                if current_length + sentence_length > chunk_size and current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                current_chunk.append(sentence)
                current_length += sentence_length
            
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            
            # Process each chunk and collect results
            all_predictions = []
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
            relevant_predictions = {}
            for pred in all_predictions:
                if not isinstance(pred, dict) or 'label' not in pred or 'score' not in pred:
                    continue
                    
                label = pred.get('label', '').lower()
                score = float(pred.get('score', 0))
                
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
            sorted_predictions = sorted(
                relevant_predictions.values(), 
                key=lambda x: x['score'], 
                reverse=True
            )
            
            return sorted_predictions
            
        except Exception as e:
            logger.error(f"Error getting content moderation predictions: {e}", exc_info=True)
            return []

    def _get_content_moderation_predictions(self, text: str) -> List[Dict[str, Any]]:
        """
        Get predictions using the KoalaAI content moderation model.
        
        Args:
            text: The text to analyze
            
        Returns:
            List of prediction dictionaries with 'label' and 'score' keys
        """
        if not text or not self.content_moderation_classifier:
            return []
            
        try:
            # Get predictions from the model
            predictions = self.content_moderation_classifier(text, truncation=True, max_length=512)
            
            # Process the predictions to match expected format
            if predictions and isinstance(predictions, list):
                # Handle case where predictions is a list of lists (batch of inputs)
                if len(predictions) > 0 and isinstance(predictions[0], list):
                    predictions = predictions[0]
                    
                # Convert to list of dicts with label and score
                processed = []
                for pred in predictions:
                    if isinstance(pred, dict) and 'label' in pred and 'score' in pred:
                        processed.append({
                            'label': pred['label'],
                            'score': float(pred['score'])
                        })
                return processed
                
        except Exception as e:
            logger.error(f"Error getting content moderation predictions: {e}", exc_info=True)
            
        return []

    def _get_explicit_patterns(self):
        """Return comprehensive patterns for explicit content detection."""
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

    def _load_koalaai_label_map(self) -> Dict[str, Dict[str, Any]]:
        """
        Load the mapping from KoalaAI model labels to our internal flag system.
        This maps the model's output labels to our flag names, penalties, and categories.
        
        Returns:
            Dict[str, Dict[str, Any]]: Mapping of KoalaAI labels to flag information
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

        # Add common explicit phrases
        explicit_phrases = [
            # General explicit
            (r'suck (?:my|it|this|that|a|your)', 'explicit'),
            (r'eat (?:my|it|this|that|a|your)', 'explicit'),
            (r'fuck (?:you|off|that|this|it|me)', 'explicit'),
            # Sexual
            (r'suck (?:dick|cock|pussy)', 'sexual'),
            (r'eat (?:pussy|ass)', 'sexual'),
            (r'blow ?job', 'sexual'),
            (r'hand ?job', 'sexual'),
            (r'jerk ?off', 'sexual'),
            # Violence
            (r'kill (?:you|him|her|them|myself|yourself)', 'violence'),
            (r'shoot (?:you|him|her|them|myself|yourself)', 'violence'),
            (r'beat (?:you|him|her|them|myself|yourself)', 'violence'),
            # Drugs
            (r'shoot up', 'drugs'),
            (r'snort (?:lines|coke)', 'drugs'),
            (r'smoke (?:weed|pot)', 'drugs'),
            (r'do (?:drugs|lines)', 'drugs'),
            (r'drop acid', 'drugs'),
            (r'pop pills', 'drugs'),
            # Hate
            (r'white (?:power|pride|trash)', 'hate'),
            (r'nazi party', 'hate'),
            (r'hitler youth', 'hate'),
            (r'lynch mob', 'hate')
        ]

        # Compile phrase patterns
        for phrase, category in explicit_phrases:
            try:
                pattern = re.compile(phrase, re.IGNORECASE)
                patterns.append((pattern, category))
            except re.error as e:
                logger.warning(f"Invalid regex phrase pattern '{phrase}': {e}")

        return patterns
        
    def _process_flag(self, label, score, flag_info, triggered_flags_details, total_penalty):
        """Process a single flag and update the triggered flags and total penalty.
        
        Args:
            label: The label of the flag (e.g., 'hate', 'explicit', 'sexual')
            score: Confidence score from the model (0.0 to 1.0)
            flag_info: Dictionary containing flag metadata
            triggered_flags_details: List of already triggered flags
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
        
        # Initialize default values
        triggered_flags_details = []
        total_penalty = 0
        
        try:
            # If no predictions provided, try to get them
            if content_moderation_predictions is None and lyrics_text:
                logger.debug("No content moderation predictions provided, running analysis")
                content_moderation_predictions = self._get_content_moderation_predictions(lyrics_text)
            
            # If we still don't have predictions, check for explicit patterns as a fallback
            if not content_moderation_predictions and lyrics_text:
                logger.warning("No content moderation predictions available, falling back to pattern matching")
                explicit_patterns = self._get_explicit_patterns()
                for pattern in explicit_patterns:
                    if re.search(pattern, lyrics_text, re.IGNORECASE):
                        # Add explicit language flag with high confidence
                        penalty = 50
                        triggered_flags_details.append({
                            'flag': 'Explicit Language / Corrupting Talk',
                            'penalty_applied': penalty,
                            'confidence': 0.9,
                            'details': f'Matched explicit pattern after model failure: {pattern}'
                        })
                        total_penalty += penalty
                        logger.warning(f"Applied penalty of {penalty} for explicit pattern match after model failure")
                        break  # Only need one match
                
                if total_penalty > 0:
                    return triggered_flags_details, min(total_penalty, 100)
                return [], 0
                
            logger.info(f"Processing {len(content_moderation_predictions)} content moderation predictions")
            
            # Get the label mapping from the rubric
            label_map = self.christian_rubric.get("purity_flag_definitions", {}).get("cardiffnlp_model_map", {})
            
            # Add explicit label mapping if not present
            if 'explicit' not in label_map:
                label_map['explicit'] = {
                    'flag_name': 'Explicit Language / Corrupting Talk',
                    'penalty': 50
                }
            
            # Process each prediction
            for pred in content_moderation_predictions:
                if not isinstance(pred, dict) or 'label' not in pred or 'score' not in pred:
                    continue
                    
                label = pred.get('label', '').lower()
                score = float(pred.get('score', 0))
                
                # Log the prediction for debugging
                logger.debug(f"Processing prediction - Label: {label}, Score: {score:.4f}")
                
                # Skip 'OK' label as it's handled in _get_content_moderation_predictions
                if label == 'ok':
                    # Only log OK if it's the only prediction
                    if len(content_moderation_predictions) == 1:
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
            
            # Define category penalties based on severity
            category_penalties = {
                'hate': 75,        # Most severe penalty for hate speech (-75 points)
                'explicit': 50,     # Standard penalty for explicit language (-50 points)
                'sexual': 50,       # Same as explicit for sexual content (-50 points)
                'violence': 25,     # Lower penalty for violence (-25 points)
                'drugs': 25,        # Same as violence for drug references (-25 points)
                'offensive': 50,    # Alias for explicit (-50 points)
                'self_harm': 75     # Severe penalty for self-harm references (-75 points)
            }
            
            # Minimum match counts to trigger each category
            min_match_counts = {
                'hate': 1,         # Even a single instance of hate speech is severe
                'explicit': 1,      # Even a single explicit word is a concern
                'sexual': 1,        # Even a single sexual reference is a concern
                'violence': 2,      # Require at least 2 violence references
                'drugs': 2,         # Require at least 2 drug references
                'offensive': 1,     # Even a single offensive word is a concern
                'self_harm': 1      # Even a single self-harm reference is severe
            }
        
            # Apply penalties for each category with matches
            for category, matches in matches_by_category.items():
                match_count = len(matches)
                min_matches = min_match_counts.get(category, 1)
                
                if match_count >= min_matches:
                    penalty = category_penalties.get(category, 25)
                    
                    # Calculate penalty based on number of matches (capped at 2x base penalty)
                    severity_multiplier = min(2.0, 1.0 + ((match_count - min_matches) * 0.1))  # 10% increase per match over minimum, max 2x
                    total_category_penalty = min(100, int(penalty * severity_multiplier))
                    
                    # Get flag name and penalty from the category mapping
                    category_mapping = {
                        'hate': {
                            'flag_name': 'Hate Speech Detected',
                            'penalty': 75
                        },
                        'explicit': {
                            'flag_name': 'Explicit Language / Corrupting Talk',
                            'penalty': 50
                        },
                        'sexual': {
                            'flag_name': 'Sexual Content / Impurity (overt)',
                            'penalty': 50
                        },
                        'violence': {
                            'flag_name': 'Glorification of Violence',
                            'penalty': 25
                        },
                        'drugs': {
                            'flag_name': 'Glorification of Drugs / Substance Abuse',
                            'penalty': 25
                        },
                        'offensive': {
                            'flag_name': 'Explicit Language / Corrupting Talk',
                            'penalty': 50
                        },
                        'self_harm': {
                            'flag_name': 'Self-Harm References',
                            'penalty': 75
                        }
                    }
                    
                    # Get the flag info for this category, or use defaults
                    flag_info = category_mapping.get(category, {
                        'flag_name': f'Inappropriate Content ({category})',
                        'penalty': 25
                    })
                    flag_name = flag_info['flag_name']
                    penalty = flag_info['penalty']
                    
                    # Skip if we already have this flag from content moderation
                    existing_flag = next((f for f in triggered_flags_details 
                                       if f["flag"] == flag_name and f["source"] == "content_moderation"), None)
                    if existing_flag:
                        logger.debug(f"Skipping pattern-based {flag_name} as it was already detected by content moderation")
                        continue
                    
                    # Check if we already have this flag type from pattern matching
                    existing_pattern_flag = next((f for f in triggered_flags_details 
                                               if f["flag"] == flag_name and f["source"] == "pattern_analysis"), None)
                    
                    # Calculate confidence based on number of matches (capped at 0.9)
                    confidence = min(0.9, 0.5 + (match_count * 0.05))
                    
                    if not existing_pattern_flag or confidence > existing_pattern_flag.get('confidence', 0):
                        # If flag exists but with lower confidence, update it
                        if existing_pattern_flag:
                            total_penalty -= existing_pattern_flag["penalty_applied"]
                            triggered_flags_details.remove(existing_pattern_flag)
                        
                        # Add sample matches (up to 3) to details
                        sample_matches = sorted(list(matches))[:3]  # Sort for consistent ordering
                        details = f"Detected {match_count} instance(s) of {category} content"
                        
                        # Add sample matches if available
                        if sample_matches:
                            details += f" (e.g., '{sample_matches[0]}'"
                            if len(sample_matches) > 1:
                                details += f", '{sample_matches[1]}'"
                                if len(sample_matches) > 2:
                                    details += f", '{sample_matches[2]}'"
                            details += ")"
                            
                        # Add penalty information
                        details += f" [Penalty: -{total_category_penalty} points]"
                        
                        triggered_flags_details.append({
                            "flag": flag_name,
                            "details": details,
                            "penalty_applied": total_category_penalty,
                            "confidence": confidence,
                            "source": "pattern_analysis",
                            "category": category,
                            "match_count": match_count
                        })
                        total_penalty += total_category_penalty
                        logger.info(f"Applied penalty of {total_category_penalty} for {flag_name} (found {match_count} matches)")
                    else:
                        logger.debug(f"Skipping duplicate flag {flag_name} with lower confidence {confidence:.2f} <= {existing_pattern_flag['confidence']:.2f}")
    
            # Process other flags defined in the rubric if needed
            # (This section can be used for additional custom flag processing)
            
            # Apply maximum penalty cap (100%)
            total_penalty = min(total_penalty, 100)
            
            # Sort flags by penalty (highest first) for consistent output
            triggered_flags_details.sort(key=lambda x: x.get('penalty_applied', 0), reverse=True)
            
            logger.info(f"Detected {len(triggered_flags_details)} purity flags with total penalty {total_penalty}")
            logger.debug(f"Flag details: {triggered_flags_details}")
            
            return triggered_flags_details, total_penalty

    def _detect_christian_themes(self, lyrics_text: Optional[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Detect Christian themes in song lyrics.
        
        Args:
            lyrics_text: The lyrics text to analyze for Christian themes
            
        Returns:
            Tuple of (positive_themes, negative_themes) where each is a list of theme dicts
        """
        logger.debug("Detecting Christian themes in lyrics")
        positive_themes = []
        negative_themes = []
        
        if not lyrics_text:
            logger.debug("No lyrics provided for theme detection")
            return positive_themes, negative_themes
            
        # Convert to lowercase for case-insensitive matching
        lyrics_lower = lyrics_text.lower()
        
        # Debug: Print the rubric config
        logger.debug(f"Positive themes config: {self.christian_rubric.get('positive_themes_config', [])}")
        logger.debug(f"Negative themes config: {self.christian_rubric.get('negative_themes_config', [])}")
        
        # Check positive themes
        for theme_config in self.christian_rubric.get("positive_themes_config", []):
            theme_name = theme_config.get("name", "Unknown")
            keywords = theme_config.get("keywords", [])
            
            # Check if any keyword is in the lyrics
            matches = [kw for kw in keywords if kw.lower() in lyrics_lower]
            if matches:
                theme = {
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
        # Log the start of analysis with user context if available
        log_prefix = f"[User {self.user_id}] " if self.user_id else ""
        logger.info(f"{log_prefix}--- Starting Song Analysis for '{title}' by '{artist}' ---")
        
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
                logger.info(f"Lyrics not provided for '{title}'. Fetching...")
                try:
                    lyrics_text = self.lyrics_fetcher.fetch_lyrics(title, artist)
                    if lyrics_text:
                        logger.info(f"Lyrics fetched successfully for '{title}'. Length: {len(lyrics_text)}")
                        analysis_results["lyrics_fetched_successfully"] = True
                    else:
                        logger.warning(f"Could not fetch lyrics for '{title}'.")
                        analysis_results["warnings"].append("Failed to fetch lyrics. Analysis will be limited.")
                except Exception as e:
                    logger.error(f"Error fetching lyrics for '{title}': {e}", exc_info=True)
                    error_msg = f"Error fetching lyrics: {str(e)}"
                    analysis_results["warnings"].append(error_msg)
                    analysis_results["errors"].append(error_msg)
            
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
                    explicit_flag = {
                        "flag": "Explicit Content (Spotify Flag)",
                        "category": "explicit",
                        "penalty": 50,  # Same as other explicit content
                        "confidence": 1.0,  # 100% confident since it's from Spotify
                        "source": "spotify_explicit_flag"
                    }
                    purity_flags_details.append(explicit_flag)
                    total_purity_penalty += explicit_flag["penalty"]
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
            positive_themes = []
            negative_themes = []
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
            except Exception as e:
                logger.error(f"Error getting supporting scripture: {e}", exc_info=True)
                analysis_results["warnings"].append("Error retrieving supporting scripture references.")
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
            
        logger.info(f"--- Completed Song Analysis for '{title}' by '{artist}' ---")
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
    test_songs = [
        {"title": "WAP", "artist": "Cardi B", "lyrics": "Yeah, you fuckin' with some wet-ass pussy"},
        {"title": "Short Safe Song", "artist": "Test Artist", "lyrics": "god is good jesus is lord glory hallelujah"},
        {"title": "Short Bad Song", "artist": "Test Artist", "lyrics": "This is damn offensive shit and drugs"},
        {"title": "Song with Hate Speech", "artist": "Test Artist", "lyrics": "i hate all those people they are scum"},
        {"title": "Empty Lyrics Song", "artist": "Test Artist", "lyrics": ""},
        {"title": "No Lyrics Provided Song", "artist": "Test Artist", "lyrics": None}
    ]

    for song_data in test_songs:
        if song_data["lyrics"] is not None:
            result = analyzer.analyze_song(song_data["title"], song_data["artist"], lyrics_text=song_data["lyrics"])
        else:
            # Test fetching if lyrics are None (will fail if LYRICSGENIUS_API_KEY not set or song not found)
            logger.info(f"\nAttempting to fetch lyrics for {song_data['title']} (ensure API key is set if testing this)...")
            result = analyzer.analyze_song(song_data["title"], song_data["artist"], fetch_lyrics_if_missing=True)
        
        print(f"\n--- {song_data['artist']} - {song_data['title']} ---")
        import json
        print(json.dumps(result, indent=2))

    # Example of fetching lyrics for a known song if API key is available
    logger.info("\nAttempting to fetch lyrics for a song (ensure API key is set)...")
    fetched_result = analyzer.analyze_song("Stairway to Heaven", "Led Zeppelin", fetch_lyrics_if_missing=True)
    print(f"\n--- Led Zeppelin - Stairway to Heaven (Fetched) ---")
    print(json.dumps(fetched_result, indent=2))
