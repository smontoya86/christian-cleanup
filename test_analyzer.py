import sys
import os
from pprint import pprint
import nltk # Import NLTK
from dotenv import load_dotenv # Import load_dotenv
import logging # Import logging

load_dotenv() # Load .env file at the beginning

# Configure basic logging to see INFO messages during the test
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add the project root to the Python path to allow direct import of app modules
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.utils.analysis import SongAnalyzer
from flask import Flask

def download_nltk_data_if_needed():
    """Checks for vader_lexicon and downloads if not found."""
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
        print("NLTK 'vader_lexicon' found.")
    except LookupError: # Corrected exception type
        print("NLTK 'vader_lexicon' not found. Attempting to download...")
        try:
            nltk.download('vader_lexicon')
            print("NLTK 'vader_lexicon' downloaded successfully.")
        except Exception as e:
            print(f"Failed to download 'vader_lexicon'. Error: {e}")
            print("Please try manually running: python -m nltk.downloader vader_lexicon")
    except Exception as e: # Catch any other NLTK data path issues
        print(f"An unexpected error occurred while checking NLTK data: {e}")
        print("Attempting to download 'vader_lexicon' anyway...")
        try:
            nltk.download('vader_lexicon')
            print("NLTK 'vader_lexicon' downloaded successfully.")
        except Exception as download_e:
            print(f"Failed to download 'vader_lexicon' during fallback. Error: {download_e}")
            print("Please try manually running: python -m nltk.downloader vader_lexicon")


if __name__ == '__main__':
    download_nltk_data_if_needed() # Call the download helper

    # Create a minimal Flask app context
    # This is often needed if components within SongAnalyzer (or its dependencies)
    # use Flask's current_app (e.g., for logging or config)
    app = Flask(__name__)
    
    # Mock common Flask app configurations if needed by your SongAnalyzer or its components
    # For example, if LyricsFetcher or BibleClient tries to access app.config:
    app.config['LYRICSGENIUS_API_KEY'] = os.getenv('LYRICSGENIUS_API_KEY') 
    # Add a quick check for debugging
    if not app.config['LYRICSGENIUS_API_KEY']:
        print("Test Script Warning: LYRICSGENIUS_API_KEY is NOT set in environment after load_dotenv(). Check .env file.")
    else:
        # Mask most of the key for security in logs
        key_preview = app.config['LYRICSGENIUS_API_KEY'][:5] + '...' if app.config['LYRICSGENIUS_API_KEY'] and len(app.config['LYRICSGENIUS_API_KEY']) > 5 else app.config['LYRICSGENIUS_API_KEY']
        print(f"Test Script: LYRICSGENIUS_API_KEY found in environment (preview: {key_preview}) and set in app.config.")
    # Add other necessary configs if your app components expect them.
    # If .env is used by components, ensure it's loaded (BibleClient does this)

    with app.app_context():
        print("Initializing SongAnalyzer...")
        try:
            analyzer = SongAnalyzer()
            print("SongAnalyzer initialized.")
            
            song_title = "Begin Again"
            song_artist = "Andy Shauf" 
            
            logging.info(f"Starting analysis for song: {song_title} by {song_artist}")
            print(f"\nAnalyzing '{song_title}' by {song_artist}...")
            analysis_result = analyzer.analyze_song(song_title, song_artist)
            
            print("\n--- Full Analysis Result ---")
            pprint(analysis_result)

        except Exception as e:
            print(f"An error occurred during the test: {e}")
            import traceback
            traceback.print_exc()
