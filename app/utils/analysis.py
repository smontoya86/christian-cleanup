import re
import json
import torch
import requests # Placeholder, may be used by future models or APIs
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from flask import current_app
from .lyrics import LyricsFetcher # Assuming lyrics.py is in the same utils directory
from .bible_client import BibleClient # Added import
import logging
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

logger = logging.getLogger(__name__)

class SongAnalyzer:
    def __init__(self):
        # Load the model and tokenizer for sensitive content detection / sentiment
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"SongAnalyzer using device: {self.device}")
        
        # Model for inappropriate text classification (can also give sentiment clues)
        self.sentiment_model_name = "michellejieli/inappropriate_text_classifier"
        
        try:
            logger.info(f"Loading tokenizer for {self.sentiment_model_name}")
            self.sentiment_tokenizer = AutoTokenizer.from_pretrained(self.sentiment_model_name)
            logger.info(f"Loading model {self.sentiment_model_name}")
            self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(self.sentiment_model_name).to(self.device)
            logger.info(f"Model {self.sentiment_model_name} loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading sentiment model '{self.sentiment_model_name}': {e}")
            logger.error("Sentiment analysis capabilities will be limited.")
            self.sentiment_tokenizer = None
            self.sentiment_model = None

        # Initialize lyrics fetcher
        self.lyrics_fetcher = LyricsFetcher()
        
        # Initialize Bible client
        self.bible_client = BibleClient() # Added BibleClient instance
        
        # Define theme categories and keywords (simple initial approach)
        self.theme_categories = {
            'faith': ['faith', 'believe', 'trust', 'god', 'jesus', 'christ', 'lord', 'savior', 'holy', 'spirit', 'prayer', 'pray'],
            'love': ['love', 'compassion', 'kindness', 'charity', 'caring', 'affection'],
            'hope': ['hope', 'future', 'promise', 'eternity', 'heaven', 'salvation'],
            'struggle': ['struggle', 'pain', 'hurt', 'sorrow', 'hardship', 'trial', 'broken'],
            'sin_repentance': ['sin', 'temptation', 'evil', 'wrong', 'transgression', 'wickedness', 'repent', 'forgive', 'mercy', 'grace'],
            'redemption': ['redemption', 'forgiveness', 'mercy', 'grace', 'saved', 'redeemed', 'deliverance'],
            'worship_praise': ['worship', 'praise', 'glory', 'adoration', 'exalt', 'honor', 'hallelujah', 'amen'],
            'gratitude': ['thanks', 'grateful', 'thankful', 'gratitude', 'blessing'],
            'peace_joy': ['peace', 'calm', 'tranquility', 'rest', 'serenity', 'joy', 'rejoice', 'gladness'],
            'guidance_wisdom': ['guide', 'lead', 'wisdom', 'truth', 'light', 'path', 'way']
        }
        
        # For sentiment analysis (VADER)
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except nltk.downloader.DownloadError:
            current_app.logger.info("Downloading VADER lexicon for NLTK...")
            nltk.download('vader_lexicon')
        except LookupError: # Fallback for environments where find might not work as expected but download is needed
            current_app.logger.info("VADER lexicon not found, attempting download...")
            nltk.download('vader_lexicon')
            
        self.sentiment_analyzer = SentimentIntensityAnalyzer()

    def _preprocess_lyrics(self, lyrics):
        if not lyrics:
            return ""
        # Lowercase
        lyrics = lyrics.lower()
        # Remove timestamps like [00:00.000]
        lyrics = re.sub(r'\[\d{2}:\d{2}\.\d{3}\]', '', lyrics)
        # Remove common non-alphanumeric characters except spaces and apostrophes
        lyrics = re.sub(r'[^a-z0-9\s\']', '', lyrics)
        # Normalize whitespace
        lyrics = re.sub(r'\s+', ' ', lyrics).strip()
        return lyrics

    def _detect_sensitive_content(self, text):
        if not text or not text.strip():
            return {'label': 'SAFE', 'score': 1.0} # Default to safe if no text
        
        inputs = self.sentiment_tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(self.device)
        with torch.no_grad():
            outputs = self.sentiment_model(**inputs)
        
        probs = torch.softmax(outputs.logits, dim=-1)
        # Assuming the model outputs [inappropriate, appropriate] or similar
        # We need to know the label mapping. For now, let's assume label 0 = inappropriate, 1 = appropriate
        # Based on common practice, higher score for 'inappropriate' if that's the primary class of interest.
        # Let's assume the model output is such that probs[0][0] is 'inappropriate' score, probs[0][1] is 'appropriate' score.
        # Or, more directly, check model.config.id2label
        # For michellejieli/inappropriate_text_classifier, 0 is 'inappropriate', 1 is 'appropriate'
        inappropriate_score = probs[0][0].item()
        appropriate_score = probs[0][1].item()

        label_id = torch.argmax(probs, dim=-1).item()
        label = self.sentiment_model.config.id2label[label_id]

        # We want to return the score for the 'inappropriate' class
        return {'label': label.upper(), 'score': inappropriate_score}

    def _extract_themes_basic(self, lyrics):
        themes = {}
        if not lyrics:
            return themes
        
        words = set(lyrics.lower().split())
        for theme, keywords in self.theme_categories.items():
            # Count occurrences of each keyword for the theme
            # Using regex to match whole words to avoid partial matches (e.g., 'sin' in 'since')
            theme_score = 0
            theme_keywords_found = []
            for keyword in keywords:
                # Create a regex pattern for the whole word
                pattern = r"\b" + re.escape(keyword) + r"\b"
                matches = re.findall(pattern, lyrics.lower())
                if matches:
                    theme_score += len(matches)
                    theme_keywords_found.append(keyword)
            
            if theme_score > 0:
                themes[theme] = {'present': True, 'keyword_matches': theme_score} # Basic count of distinct keywords
        return themes

    def _analyze_sentiment_basic(self, lyrics):
        # Placeholder for basic sentiment analysis or VADER if integrated
        if not lyrics:
            return {'sentiment_label': 'NEUTRAL', 'sentiment_score': 0.0}
        
        # Using self.sentiment_analyzer for VADER
        sentiment_scores = self.sentiment_analyzer.polarity_scores(lyrics)
        # Determine label based on compound score
        compound_score = sentiment_scores['compound']
        if compound_score >= 0.05:
            return {'sentiment_label': 'POSITIVE', 'sentiment_score': compound_score, 'raw_scores': sentiment_scores}
        elif compound_score <= -0.05:
            return {'sentiment_label': 'NEGATIVE', 'sentiment_score': compound_score, 'raw_scores': sentiment_scores}
        else:
            return {'sentiment_label': 'NEUTRAL', 'sentiment_score': compound_score, 'raw_scores': sentiment_scores}

    def find_scriptures_for_themes(self, themes, verses_per_theme=1):
        scriptures_by_theme = {}
        if not themes:
            return scriptures_by_theme

        for theme in themes:
            # Assuming themes are single words or short phrases suitable for search
            results = self.bible_client.search(query=theme, limit=verses_per_theme)
            theme_scriptures = []
            if results:
                for item in results:
                    theme_scriptures.append({
                        "reference": item.get('reference', 'N/A'),
                        "text": item.get('text', item.get('content', 'N/A')),
                        "bible_id": item.get('bibleId', self.bible_client.default_bible_id) # Add which Bible it came from
                    })
            scriptures_by_theme[theme] = theme_scriptures
        return scriptures_by_theme

    def analyze_song(self, title, artist):
        current_app.logger.info(f"Starting analysis for song: {title} by {artist}")
        try:
            lyrics = self.lyrics_fetcher.fetch_lyrics(title, artist)
            if not lyrics:
                current_app.logger.warning(f"No lyrics found for {title} by {artist}")
                return {
                    'title': title,
                    'artist': artist,
                    'lyrics': None,
                    'error': 'Lyrics not found',
                    'analysis_summary': 'Could not analyze: Lyrics not found.'
                }

            preprocessed_lyrics = self._preprocess_lyrics(lyrics)
            current_app.logger.debug(f"Preprocessed lyrics: {preprocessed_lyrics[:200]}...")

            sensitive_content = self._detect_sensitive_content(preprocessed_lyrics)
            current_app.logger.info(f"Sensitive content analysis for {title}: {sensitive_content}")
            
            themes = self._extract_themes_basic(preprocessed_lyrics)
            current_app.logger.info(f"Basic theme extraction for {title}: {themes}")

            sentiment = self._analyze_sentiment_basic(preprocessed_lyrics)
            current_app.logger.info(f"Basic sentiment analysis for {title}: {sentiment}")
            
            scriptures_by_theme = self.find_scriptures_for_themes(themes) # Scripture fetching

            # Combine themes and scriptures
            detailed_theme_analysis = {}
            for theme_name, theme_data in themes.items():
                detailed_theme_analysis[theme_name] = theme_data.copy() # Start with existing theme data
                if theme_name in scriptures_by_theme:
                    detailed_theme_analysis[theme_name]['scriptures'] = scriptures_by_theme[theme_name]
                else:
                    detailed_theme_analysis[theme_name]['scriptures'] = [] # Ensure scriptures key exists

            # Placeholder for overall alignment score logic
            alignment_score = 0.0 
            analysis_summary_parts = []

            if sensitive_content['label'] == 'INAPPROPRIATE' and sensitive_content['score'] > 0.75:
                alignment_score -= 50 # Heavy penalty
                analysis_summary_parts.append(f"High probability of inappropriate content (score: {sensitive_content['score']:.2f}).")
            elif sensitive_content['label'] == 'INAPPROPRIATE' and sensitive_content['score'] > 0.5:
                alignment_score -= 25 # Medium penalty
                analysis_summary_parts.append(f"Potential inappropriate content (score: {sensitive_content['score']:.2f}).")
            else:
                alignment_score += 10 # Base score for safe content
                analysis_summary_parts.append("Content appears appropriate.")

            # Basic theme contribution to score (example)
            positive_themes = ['faith', 'love', 'hope', 'redemption', 'worship_praise', 'gratitude', 'peace_joy', 'guidance_wisdom']
            negative_themes = ['sin_repentance', 'struggle'] # sin_repentance can be complex

            identified_positive_themes = [theme for theme in themes if theme in positive_themes and themes[theme].get('present')]
            identified_negative_themes = [theme for theme in themes if theme in negative_themes and themes[theme].get('present')]

            alignment_score += len(identified_positive_themes) * 5
            alignment_score -= len(identified_negative_themes) * 2 # Minor penalty for struggle/sin if not balanced
            
            if identified_positive_themes:
                analysis_summary_parts.append(f"Identified positive themes: {', '.join(identified_positive_themes)}.")
            if identified_negative_themes:
                analysis_summary_parts.append(f"Identified themes of struggle/repentance: {', '.join(identified_negative_themes)}.")
            if not themes:
                analysis_summary_parts.append("No specific thematic keywords detected with basic analysis.")

            # Clamp score between 0 and 100
            alignment_score = max(0, min(100, alignment_score))
            
            analysis_summary = " ".join(analysis_summary_parts)
            if not analysis_summary.strip():
                analysis_summary = "Analysis complete. Further details pending full implementation."

            return {
                'title': title,
                'artist': artist,
                'lyrics': lyrics, # Original lyrics for display
                'preprocessed_lyrics': preprocessed_lyrics, # For further processing if needed
                'sensitive_content_analysis': sensitive_content,
                'detailed_theme_analysis': detailed_theme_analysis, # Combined themes and scriptures
                'sentiment_analysis': sentiment, # Placeholder
                'alignment_score': alignment_score,
                'analysis_summary': analysis_summary,
                'error': None
            }

        except Exception as e:
            current_app.logger.error(f"Error analyzing song {title} by {artist}: {e}", exc_info=True)
            return {
                'title': title,
                'artist': artist,
                'lyrics': None,
                'error': str(e),
                'analysis_summary': f'Analysis failed due to an error: {str(e)}'
            }

# Example usage (for testing, not part of the class)
if __name__ == '__main__':
    # This part would need a Flask app context to run current_app.logger
    # and also the actual LyricsFetcher to work.
    # For standalone testing, mock these or adjust.
    class MockApp:
        def __init__(self):
            self.logger = MockLogger()
    class MockLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def warning(self, msg): print(f"WARN: {msg}")
        def error(self, msg, exc_info=False): print(f"ERROR: {msg}")
        def debug(self, msg): print(f"DEBUG: {msg}")

    # Mock current_app for standalone testing
    original_current_app = current_app
    current_app = MockApp() 

    analyzer = SongAnalyzer()
    # Test with a known Christian song
    # results_hillsong = analyzer.analyze_song("What A Beautiful Name", "Hillsong Worship")
    # print("\n--- Hillsong - What A Beautiful Name ---")
    # print(json.dumps(results_hillsong, indent=2))

    # Test with a secular song known to have explicit content
    # results_explicit = analyzer.analyze_song("WAP", "Cardi B") # This will likely trigger sensitive content
    # print("\n--- Cardi B - WAP ---")
    # print(json.dumps(results_explicit, indent=2))

    # Test with a song that might not be found
    # results_not_found = analyzer.analyze_song("NonExistentSong", "NonExistentArtist")
    # print("\n--- NonExistentSong - NonExistentArtist ---")
    # print(json.dumps(results_not_found, indent=2))

    # Test with lyrics that might be empty or very short
    # Mock lyrics fetcher for this test
    class MockLyricsFetcher:
        def fetch_lyrics(self, title, artist):
            if title == "Empty Test Song":
                return ""
            if title == "Short Safe Song":
                return "god is good"
            if title == "Short Bad Song":
                return "bad word here"
            return "Lyrics for " + title + " by " + artist # Default mock
    
    analyzer.lyrics_fetcher = MockLyricsFetcher()
    results_empty = analyzer.analyze_song("Empty Test Song", "Test Artist")
    print("\n--- Empty Test Song ---")
    print(json.dumps(results_empty, indent=2))

    results_short_safe = analyzer.analyze_song("Short Safe Song", "Test Artist")
    print("\n--- Short Safe Song ---")
    print(json.dumps(results_short_safe, indent=2))

    results_short_bad = analyzer.analyze_song("Short Bad Song", "Test Artist")
    print("\n--- Short Bad Song ---")
    print(json.dumps(results_short_bad, indent=2))
    
    # Restore current_app if it was mocked
    current_app = original_current_app
