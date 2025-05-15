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
    def __init__(self, device: Optional[str] = None):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
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

        self.lyrics_fetcher = LyricsFetcher()
        self.bible_client = BibleClient()
        self.bsb_bible_id = BibleClient.BSB_ID
        self.kjv_bible_id = BibleClient.KJV_ID
        
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

    def _get_cardiffnlp_predictions(self, text: str) -> List[Dict[str, Any]]:
        logger.debug("Executing full _get_cardiffnlp_predictions")
        if not self.cardiffnlp_offensive_classifier or not text:
            logger.warning("CardiffNLP offensive classifier not loaded or empty text, returning empty predictions.")
            return []
        
        try:
            # The pipeline handles tokenization, truncation to model's max_length, and prediction.
            # It returns a list of dictionaries, even for single input.
            # e.g., [{'label': 'hate', 'score': 0.88}] or [{'label': 'LABEL_2', 'score': 0.88}]
            # The default max_length for roberta-base is 512 tokens.
            predictions = self.cardiffnlp_offensive_classifier(text, truncation=True) # max_length is often implicit
            
            logger.debug(f"CardiffNLP raw predictions from pipeline: {predictions}")
            
            # The 'text-classification' pipeline for models like cardiffnlp/twitter-roberta-base-offensive
            # uses the model's config.id2label to return human-readable labels (e.g., 'offensive', 'hate').
            # So, no explicit mapping from 'LABEL_X' should be needed here if model config is standard.
            
            # We are interested in 'offensive' and 'hate' labels.
            relevant_predictions = []
            for pred in predictions: # predictions is a list e.g. [{'label': 'offensive', 'score': 0.9}]
                label = pred.get('label', '').lower() # Ensure lowercase for consistent matching
                if label in ["offensive", "hate"]:
                    relevant_predictions.append({'label': label, 'score': pred.get('score')})
            
            return relevant_predictions
            
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
        # Placeholder for theme detection logic (e.g., using keyword matching, topic modeling, or another LLM)
        logger.debug("Stub: _detect_christian_themes called. Returning no themes.")
        # For now, returns empty lists for positive and negative themes
        # Actual implementation would populate these based on analysis
        # Example structure for a theme: {"theme_name": "Faith / Trust in God", "details": "Keyword 'faith' found", "associated_scripture_keywords": ["faith", "trust"]}
        identified_positive_themes = []
        identified_negative_themes = [] 
        return identified_positive_themes, identified_negative_themes

    def _calculate_christian_score_and_concern(self, purity_flags_details: List[Dict[str, Any]], total_purity_penalty: int, positive_themes: List[Dict[str, Any]], negative_themes: List[Dict[str, Any]]) -> Tuple[int, str]:
        logger.debug("Executing full _calculate_christian_score_and_concern")

        rubric = self.christian_rubric
        score = rubric.get("baseline_score", 100)

        # Apply purity penalty (already calculated by _detect_christian_purity_flags)
        score -= total_purity_penalty

        # Apply negative theme penalties
        num_negative_themes = len(negative_themes) # Assumes negative_themes list contains unique identified themes
        score -= num_negative_themes * rubric.get("negative_theme_penalty", 10)

        # Apply positive theme points
        num_positive_themes = len(positive_themes) # Assumes positive_themes list contains unique identified themes
        score += num_positive_themes * rubric.get("positive_theme_points", 5)

        # Cap the score
        score = max(rubric.get("score_min_cap", 0), min(score, rubric.get("score_max_cap", 100)))

        # Determine concern level
        concern_level = "Low" # Default
        thresholds = rubric.get("concern_thresholds", {})
        low_starts_at = thresholds.get("low_starts_at", 70)
        medium_starts_at = thresholds.get("medium_starts_at", 40) # Corresponds to 40-69 for Medium

        if purity_flags_details: # Any purity flag automatically makes it High concern
            concern_level = "High"
        # If no purity flags, concern is based on score
        elif score < medium_starts_at: # Score 0-39
            concern_level = "High" 
        elif score < low_starts_at: # Score 40-69
            concern_level = "Medium"
        # else: score >= 70, remains Low
        
        logger.info(f"Calculated score: {score}, Concern level: {concern_level}")
        return int(score), concern_level

    def _get_christian_supporting_scripture(self, triggered_components: Dict[str, List[str]]) -> Dict[str, Any]:
        logger.debug("Stub: _get_christian_supporting_scripture called. Returning empty scripture dict.")
        # Actual implementation would use self.bible_client and mappings from self.christian_rubric
        # to find and format scripture for triggered themes and flags.
        # triggered_components might be like: {"positive_themes": ["Faith / Trust in God"], "purity_flags": ["Explicit Language"]}
        return {}

    def analyze_song(self, title: str, artist: str, lyrics_text: Optional[str] = None, fetch_lyrics_if_missing: bool = True) -> Dict[str, Any]:
        logger.info(f"--- Starting Song Analysis for '{title}' by '{artist}' ---")
        
        analysis_results = {
            "title": title,
            "artist": artist,
            "lyrics_provided": lyrics_text is not None,
            "lyrics_fetched_successfully": False,
            "lyrics_used_for_analysis": "",
            "cardiffnlp_raw_predictions": [],
            "alternative_model_raw_predictions": {},
            "christian_purity_flags_details": [],
            "christian_positive_themes_detected": [],
            "christian_negative_themes_detected": [],
            "christian_score": self.christian_rubric.get("baseline_score", 100),
            "christian_concern_level": "Low", # Default, will be updated
            "christian_supporting_scripture": {},
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
                        analysis_results["errors"].append("Failed to fetch lyrics.")
                except Exception as e:
                    logger.error(f"Error fetching lyrics for '{title}': {e}", exc_info=True)
                    analysis_results["errors"].append(f"Exception during lyrics fetching: {str(e)}")
            
            if not lyrics_text:
                logger.warning(f"No lyrics available for '{title}' by '{artist}'. Analysis will be limited.")
                analysis_results["errors"].append("No lyrics available for analysis.")
                # Still return results, but score might be baseline, concern low, etc.
                # Or decide on a specific handling for no-lyrics cases (e.g. specific score/concern)
                # For now, it will proceed with empty lyrics_text if none found/provided.

            # 2. Preprocess Lyrics
            processed_lyrics = self._preprocess_lyrics(lyrics_text if lyrics_text else "")
            analysis_results["lyrics_used_for_analysis"] = processed_lyrics

            # 3. Sensitive Content Detection (CardiffNLP)
            # Only run if there are lyrics to analyze
            cardiffnlp_predictions = []
            if processed_lyrics:
                cardiffnlp_predictions = self._get_cardiffnlp_predictions(processed_lyrics)
            analysis_results["cardiffnlp_raw_predictions"] = cardiffnlp_predictions

            # 4. Alternative/Additional Sensitive Content Models (if any)
            # N/A for now with current stubs, but structure is here.
            # alternative_model_predictions = self._get_alternative_model_predictions(processed_lyrics)
            # analysis_results["alternative_model_raw_predictions"] = alternative_model_predictions

            # 5. Detect Christian Purity Flags (based on model outputs)
            purity_flags_details, total_purity_penalty = self._detect_christian_purity_flags(cardiffnlp_predictions, processed_lyrics)
            analysis_results["christian_purity_flags_details"] = purity_flags_details

            # 6. Detect Christian Themes (Positive and Negative)
            # This is still a stub and will return empty lists
            positive_themes, negative_themes = self._detect_christian_themes(processed_lyrics)
            analysis_results["christian_positive_themes_detected"] = positive_themes
            analysis_results["christian_negative_themes_detected"] = negative_themes

            # 7. Calculate Christian Score and Concern Level
            score, concern_level = self._calculate_christian_score_and_concern(
                purity_flags_details, total_purity_penalty, positive_themes, negative_themes
            )
            analysis_results["christian_score"] = score
            analysis_results["christian_concern_level"] = concern_level

            # 8. Get Supporting Scripture (based on triggered flags/themes)
            # This is still a stub
            # First, compile what was triggered:
            # triggered_components_for_scripture = {
            #     "purity_flags": [flag['flag'] for flag in purity_flags_details],
            #     "positive_themes": [theme['theme_name'] for theme in positive_themes],
            #     "negative_themes": [theme['theme_name'] for theme in negative_themes]
            # }
            # supporting_scripture = self._get_christian_supporting_scripture(triggered_components_for_scripture)
            # analysis_results["christian_supporting_scripture"] = supporting_scripture

        except Exception as e:
            logger.error(f"Critical error during song analysis for '{title}': {e}", exc_info=True)
            analysis_results["errors"].append(f"Overall analysis error: {str(e)}")
            # Ensure score/concern reflect an error state if desired, or use defaults
            analysis_results["christian_score"] = 0 # Example error score
            analysis_results["christian_concern_level"] = "Error"

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
