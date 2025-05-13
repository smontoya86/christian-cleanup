import os
import re
import requests # Will be used by lyricsgenius and potentially for alternative sources
import lyricsgenius
from flask import current_app # Corrected import
import logging # Added standard logging import

# It's good practice to get a specific logger instance for your module/class
logger = logging.getLogger(__name__)

class LyricsFetcher:
    def __init__(self, genius_token=None):
        self.genius_token = genius_token
        if not self.genius_token:
            try:
                # Try to get from Flask app config first if in app context
                if current_app:
                    self.genius_token = current_app.config.get('LYRICSGENIUS_API_KEY')
                    logger.info("LyricsFetcher: Using LYRICSGENIUS_API_KEY from Flask app config.")
            except RuntimeError: # Not in Flask app context
                logger.info("LyricsFetcher: Not in Flask app context, trying environment variable for LYRICSGENIUS_API_KEY.")
                pass # current_app is not available, proceed to environment variable
        
        if not self.genius_token:
            # Fallback to environment variable if not found in app_config or not in app context
            self.genius_token = os.environ.get('LYRICSGENIUS_API_KEY')
            if self.genius_token:
                logger.info("LyricsFetcher: Using LYRICSGENIUS_API_KEY from environment variable.")

        if not self.genius_token:
            logger.warning(
                "LyricsFetcher: LYRICSGENIUS_API_KEY not found in Flask config or environment. "
                "Lyrics fetching via Genius API will likely fail."
            )
            self.genius = None # Avoid initializing genius if no token
            return

        try:
            self.genius = lyricsgenius.Genius(self.genius_token,
                                              verbose=False,  # Turn off status messages
                                              remove_section_headers=True, # Remove [Verse], [Chorus], etc.
                                              skip_non_songs=True, # Skip things like interviews, etc.
                                              timeout=15) # Set a timeout for API requests
            logger.info("LyricsFetcher: LyricsGenius client initialized successfully.")
        except Exception as e:
            logger.error(f"LyricsFetcher: Error initializing LyricsGenius client: {e}")
            self.genius = None

    def fetch_lyrics(self, song_title, artist_name):
        if not self.genius:
            logger.warning("LyricsGenius client not initialized. Cannot fetch lyrics.")
            return None

        if not song_title or not artist_name:
            logger.warning("Song title and artist name are required to fetch lyrics.")
            return None

        try:
            logger.debug(f"Searching Genius for song: '{song_title}' by '{artist_name}'")
            song = self.genius.search_song(song_title, artist_name)
            logger.info(f"Genius API search_song returned: {type(song)} - {str(song)[:200]}...")
            if song and hasattr(song, 'lyrics') and song.lyrics:
                logger.info(f"Successfully fetched lyrics for '{song_title}' by '{artist_name}' from Genius.")
                # Basic cleaning: remove excessive newlines which Genius sometimes includes
                cleaned_lyrics = re.sub(r'\n{2,}', '\n', song.lyrics).strip()
                return cleaned_lyrics
            else:
                logger.info(f"Song '{song_title}' by '{artist_name}' not found on Genius or lyrics are empty.")
                return None
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching lyrics for '{song_title}' by '{artist_name}' from Genius.")
            return None
        except Exception as e:
            # This will catch errors from lyricsgenius library if it doesn't handle them internally
            logger.error(f"Error fetching lyrics for '{song_title}' by '{artist_name}' from Genius: {str(e)}")
            return None

    # Placeholder for Subtask 6.3, but good to have a basic structure
    def clean_lyrics(self, lyrics_text):
        """
        Basic cleaning of lyrics text.
        More advanced cleaning will be part of Subtask 6.3.
        """
        if not lyrics_text:
            return ""
        
        # Remove common section headers if lyricsgenius didn't catch all
        lyrics_text = re.sub(r'\[(.*?(Verse|Chorus|Intro|Outro|Bridge|Instrumental|Hook|Pre-Chorus|Post-Chorus|Interlude|Skit|Refrain|Ad-libs|Guitar Solo|Piano Solo|Drum Solo|Saxophone Solo|Trumpet Solo|Violin Solo|Cello Solo|Flute Solo|Harmonica Solo|Turntable Solo).*?)\]\s*', '', lyrics_text, flags=re.IGNORECASE)
        
        # Remove any remaining square bracket content (like annotations or non-standard headers)
        lyrics_text = re.sub(r'\[.*?\]', '', lyrics_text)
        
        # Specifically handle patterns like (C) YEAR, (P) YEAR, (C) YEAR, (P) YEAR
        # This aims to remove the entire block, e.g., "(C) 2023" -> ""
        lyrics_text = re.sub(r'\(\s*(?:C|P|©|℗)\s*\)\s*\d{4}\b', '', lyrics_text, flags=re.IGNORECASE)
        # Handle cases where year might be inside with C/P, e.g. (C 2023) or ( 2023)
        lyrics_text = re.sub(r'\(\s*(?:C|P|©|℗)\s+\d{4}\s*\)', '', lyrics_text, flags=re.IGNORECASE)

        # Keywords that trigger removal of the entire parenthetical phrase
        # The \b ensures these are whole words/tokens.
        # Note: 'C' for copyright, ' symbol, ' symbol.
        # Patterns like x\d+ (e.g., x2, x3) are also included.
        paren_removal_keywords_pattern = re.compile(
            r'\b(x\d+|\d+x|C|©|℗|producer|written by|vocals by|guitar by|drums by|bass by|keyboards by|album:|track no:|lyrics:|music by)\b',
            flags=re.IGNORECASE
        )

        def remove_matching_parentheticals(match):
            original_full_match = match.group(0)
            content_within_parentheses = match.group(1) # group(1) is the content *inside* the parentheses
            
            search_result = paren_removal_keywords_pattern.search(content_within_parentheses)
            if search_result:
                return ""
            else:
                return original_full_match

        # Match any text within parentheses (non-greedy to handle nested cases properly, though true nesting is rare in lyrics)
        # Then, use the function to decide whether to remove it.
        lyrics_text = re.sub(r'\((.*?)\)', remove_matching_parentheticals, lyrics_text)
        
        lyrics_text = re.sub(r'\(\s*\)', '', lyrics_text) # Remove any leftover empty parentheses

        # Normalize line breaks and remove leading/trailing whitespace from lines
        lines = [line.strip() for line in lyrics_text.splitlines()]
        
        # Remove empty lines
        non_empty_lines = [line for line in lines if line]
        
        return "\n".join(non_empty_lines).strip()
