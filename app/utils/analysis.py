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

        # Model names
        self.cardiffnlp_offensive_model_name = "cardiffnlp/twitter-roberta-base-offensive"
        
        # Initialize models and tokenizers (or pipelines) to None
        self.cardiffnlp_offensive_classifier = None # Will hold the Hugging Face pipeline
        
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
        logger.info("Loading NLP models...")
        try:
            # Load CardiffNLP Offensive Speech model using Hugging Face pipeline
            logger.info(f"Loading offensive speech model: {self.cardiffnlp_offensive_model_name} to device: {self.device}")
            # pipeline device mapping: 0 for cuda:0, 1 for cuda:1, -1 for CPU
            pipeline_device = 0 if self.device == "cuda" else -1 # Adjust if multi-GPU specific index needed
            self.cardiffnlp_offensive_classifier = pipeline(
                "text-classification",
                model=self.cardiffnlp_offensive_model_name,
                tokenizer=self.cardiffnlp_offensive_model_name,
                device=pipeline_device
            )
            logger.info("Offensive speech model loaded successfully.")
            
            # Placeholder for loading other models (e.g., theme detection, alternative sensitivity)
            # self.theme_model = pipeline(...) 
            # logger.info("Theme detection model loaded successfully.")

        except Exception as e:
            logger.error(f"Error loading NLP models: {e}", exc_info=True)
            # Depending on criticality, might raise error or allow fallback to stubs
            # For now, methods using models should check if they are None.

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

    def _get_cardiffnlp_predictions(self, text: str, chunk_size: int = 500) -> List[Dict[str, Any]]:
        logger.debug("Executing full _get_cardiffnlp_predictions")
        if not self.cardiffnlp_offensive_classifier or not text:
            logger.warning("CardiffNLP offensive classifier not loaded or empty text, returning empty predictions.")
            return []
        
        try:
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
                    chunk_predictions = self.cardiffnlp_offensive_classifier(chunk, truncation=True, max_length=512)
                    if isinstance(chunk_predictions, dict):
                        chunk_predictions = [chunk_predictions]
                    all_predictions.extend(chunk_predictions)
                except Exception as chunk_error:
                    logger.warning(f"Error processing chunk: {chunk_error}")
                    continue
            
            if not all_predictions:
                return []
                
            logger.debug(f"CardiffNLP raw predictions from pipeline: {all_predictions}")
            
            # Process and deduplicate predictions
            relevant_predictions = {}
            for pred in all_predictions:
                label = pred.get('label', '').lower()
                score = pred.get('score', 0)
                if label in ["offensive", "hate"]:
                    # Keep the highest score for each label
                    if label not in relevant_predictions or score > relevant_predictions[label]['score']:
                        relevant_predictions[label] = {'label': label, 'score': score}
            
            return list(relevant_predictions.values())
            
        except Exception as e:
            logger.error(f"Error getting CardiffNLP predictions: {e}", exc_info=True)
            return []

    def _get_alternative_model_predictions(self, text: str) -> Dict[str, Any]:
        # This could be a placeholder for another model or different type of analysis
        logger.debug("Stub: _get_alternative_model_predictions called. Returning empty dict.")
        return {}

    def _detect_christian_purity_flags(self, cardiffnlp_predictions: List[Dict[str, Any]], lyrics_text: str) -> Tuple[List[Dict[str, Any]], int]:
        logger.debug("Executing full _detect_christian_purity_flags")
        triggered_flags_details = []
        total_penalty = 0
        
        # Retrieve purity flag definitions from the rubric
        definitions = self.christian_rubric.get("purity_flag_definitions", {})
        cardiffnlp_map = definitions.get("cardiffnlp_model_map", {})

        # Process CardiffNLP predictions, prioritizing 'hate' over 'offensive'
        has_hate = False
        for pred in cardiffnlp_predictions:
            label = pred.get('label') # Should be 'offensive' or 'hate' from _get_cardiffnlp_predictions
            score = pred.get('score', 0.0)

            if label == 'hate' and 'hate' in cardiffnlp_map:
                flag_info = cardiffnlp_map['hate']
                triggered_flags_details.append({
                    "flag": flag_info["flag_name"],
                    "details": f"Detected '{label}' with confidence {score:.2f}",
                    "penalty_applied": flag_info["penalty"]
                })
                total_penalty += flag_info["penalty"]
                has_hate = True
                break # Hate is the most severe from this model; apply its penalty and stop.
        
        if not has_hate: # Only consider 'offensive' if 'hate' was not flagged
            for pred in cardiffnlp_predictions:
                label = pred.get('label')
                score = pred.get('score', 0.0)

                if label == 'offensive' and 'offensive' in cardiffnlp_map:
                    flag_info = cardiffnlp_map['offensive']
                    triggered_flags_details.append({
                        "flag": flag_info["flag_name"],
                        "details": f"Detected '{label}' with confidence {score:.2f}",
                        "penalty_applied": flag_info["penalty"]
                    })
                    total_penalty += flag_info["penalty"]
                    # Unlike hate, we don't 'break' here, in case 'offensive' could trigger multiple specific flags
                    # However, current cardiffnlp_map for 'offensive' is singular.
                    # For MVP, one 'offensive' flag from cardiffnlp is sufficient.
                    break 

        # MVP Note on stacking for 'Sexual Content' or 'Drugs/Violence' based on 'offensive' + keywords:
        # The current logic correctly applies penalties from direct 'hate' or 'offensive' labels.
        # The memory mentions: 
        #   'Sexual Content...': -50 points (MVP: if `offensive` and context implies sexual content... Stacks if applicable).
        #   'Glorification of Drugs...': -25 points (MVP: if `offensive` and context implies this... Stacks if applicable).
        # This advanced stacking logic (checking 'offensive' + context/keywords) is not yet implemented here.
        # The `total_penalty` currently reflects only the direct penalties from 'hate' or 'offensive' labels.
        # The rubric structure under `other_flags` is a placeholder for when such logic is added.
        
        logger.info(f"Detected purity flags: {triggered_flags_details}, Total penalty: {total_penalty}")
        return triggered_flags_details, total_penalty

    def _detect_christian_themes(self, lyrics_text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Detect Christian themes in the lyrics using keyword matching.
        
        Args:
            lyrics_text: The preprocessed lyrics text to analyze
            
        Returns:
            Tuple of (positive_themes, negative_themes) where each is a list of theme dicts
        """
        logger.debug("Detecting Christian themes in lyrics")
        positive_themes = []
        negative_themes = []
        
        if not lyrics_text:
            return positive_themes, negative_themes
            
        # Convert to lowercase for case-insensitive matching
        lyrics_lower = lyrics_text.lower()
        
        # Check positive themes
        for theme_config in self.christian_rubric["positive_themes_config"]:
            theme_name = theme_config["name"]
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
                logger.debug(f"Detected positive theme: {theme_name}")
        
        # Check negative themes
        for theme_config in self.christian_rubric["negative_themes_config"]:
            theme_name = theme_config["name"]
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
                negative_themes.append(theme)
                logger.debug(f"Detected negative theme: {theme_name}")
        
        logger.info(f"Detected {len(positive_themes)} positive and {len(negative_themes)} negative themes")
        return positive_themes, negative_themes

    def _calculate_christian_score_and_concern(self, purity_flags_details: List[Dict[str, Any]], total_purity_penalty: int, positive_themes: List[Dict[str, Any]], negative_themes: List[Dict[str, Any]]) -> Tuple[int, str]:
        logger.debug("Executing full _calculate_christian_score_and_concern")

        rubric = self.christian_rubric
        score = rubric.get("baseline_score", 100)
        
        # Log initial values
        logger.info(f"Initial score: {score}")
        logger.info(f"Purity flags: {[f['flag'] for f in purity_flags_details] if purity_flags_details else 'None'}")
        logger.info(f"Positive themes: {[t['theme'] for t in positive_themes] if positive_themes else 'None'}")
        logger.info(f"Negative themes: {[t['theme'] for t in negative_themes] if negative_themes else 'None'}")

        # Apply purity penalty (already calculated by _detect_christian_purity_flags)
        score -= total_purity_penalty
        logger.info(f"After purity penalty (-{total_purity_penalty}): {score}")

        # Apply negative theme penalties
        num_negative_themes = len(negative_themes)
        negative_penalty = num_negative_themes * rubric.get("negative_theme_penalty", 10)
        score -= negative_penalty
        logger.info(f"After negative themes (-{negative_penalty}): {score}")

        # Apply positive theme points (capped at 20 points max to prevent gaming the system)
        num_positive_themes = len(positive_themes)
        positive_points = min(num_positive_themes * rubric.get("positive_theme_points", 5), 20)  # Cap at +20
        score += positive_points
        logger.info(f"After positive themes (+{positive_points}): {score}")

        # Cap the score
        score = max(rubric.get("score_min_cap", 0), min(score, rubric.get("score_max_cap", 100)))
        logger.info(f"After capping: {score}")

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

    def analyze_song(self, title: str, artist: str, lyrics_text: Optional[str] = None, fetch_lyrics_if_missing: bool = True) -> Dict[str, Any]:
        # Log the start of analysis with user context if available
        log_prefix = f"[User {self.user_id}] " if self.user_id else ""
        logger.info(f"{log_prefix}--- Starting Song Analysis for '{title}' by '{artist}' ---")
        
        # Default analysis results with safe defaults
        analysis_results = {
            "title": title,
            "artist": artist,
            "analyzed_by_user_id": self.user_id,
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

            # 3. Sensitive Content Detection (CardiffNLP)
            cardiffnlp_predictions = []
            try:
                if processed_lyrics:
                    cardiffnlp_predictions = self._get_cardiffnlp_predictions(processed_lyrics)
                    analysis_results["cardiffnlp_raw_predictions"] = cardiffnlp_predictions
            except Exception as e:
                logger.error(f"Error in CardiffNLP analysis: {e}", exc_info=True)
                analysis_results["warnings"].append("Content analysis may be incomplete due to processing error.")
                # Continue with empty predictions rather than failing completely

            # 4. Detect Christian Purity Flags (based on model outputs)
            try:
                purity_flags_details, total_purity_penalty = self._detect_christian_purity_flags(
                    cardiffnlp_predictions, processed_lyrics
                )
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
