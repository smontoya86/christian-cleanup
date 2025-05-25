import os
import re
import requests # Will be used by lyricsgenius and potentially for alternative sources
import lyricsgenius
from flask import current_app # Corrected import
import logging # Added standard logging import
import hashlib
import time
from typing import Optional, Dict

# It's good practice to get a specific logger instance for your module/class
logger = logging.getLogger(__name__)

# Global cache for lyrics to avoid re-fetching identical songs
_lyrics_cache: Dict[str, Optional[str]] = {}
_last_api_call = 0
_api_call_count = 0

class LyricsFetcher:
    def __init__(self, genius_token=None):
        self.genius_token = genius_token
        
        # Try to get the token from the environment first
        if not self.genius_token:
            self.genius_token = os.getenv('GENIUS_ACCESS_TOKEN')
        
        # Initialize the Genius client with optimized settings
        self.genius = None
        if self.genius_token:
            try:
                self.genius = lyricsgenius.Genius(
                    self.genius_token,
                    timeout=5,  # Optimized timeout for better performance
                    sleep_time=0.1,  # Optimized sleep time between requests
                    retries=2,  # Fewer retries for faster processing
                    remove_section_headers=True,
                    skip_non_songs=True,
                    excluded_terms=["(Remix)", "(Live)", "(Acoustic)", "(Demo)"],
                    verbose=False
                )
                logger.info("LyricsFetcher: LyricsGenius client initialized successfully.")
            except Exception as e:
                logger.error(f"LyricsFetcher: Failed to initialize LyricsGenius client: {e}")
                self.genius = None
        else:
            logger.warning("LyricsFetcher: No Genius token provided. Lyrics fetching will be disabled.")

    def _get_cache_key(self, title: str, artist: str) -> str:
        """Generate a cache key for a song"""
        content = f"{title.lower().strip()}|{artist.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()

    def _clean_title(self, title: str) -> str:
        """Clean song title for better matching"""
        # Remove common suffixes that might interfere with search
        title = re.sub(r'\s*\(.*?\)\s*$', '', title)  # Remove parenthetical suffixes
        title = re.sub(r'\s*\[.*?\]\s*$', '', title)  # Remove bracketed suffixes
        title = re.sub(r'\s*-\s*(Remaster|Remix|Live|Acoustic|Demo).*$', '', title, flags=re.IGNORECASE)
        return title.strip()

    def _clean_artist(self, artist: str) -> str:
        """Clean artist name for better matching"""
        # Remove featuring artists and other noise
        artist = re.sub(r'\s*(feat\.|featuring|ft\.).*$', '', artist, flags=re.IGNORECASE)
        artist = re.sub(r'\s*&.*$', '', artist)  # Remove secondary artists
        return artist.strip()

    def _respect_rate_limit(self):
        """Implement smart rate limiting"""
        global _last_api_call, _api_call_count
        
        current_time = time.time()
        
        # Reset counter every minute
        if current_time - _last_api_call > 60:
            _api_call_count = 0
        
        # Limit to 60 requests per minute (optimized) (well within Genius limits)
        if _api_call_count >= 60:
            sleep_time = 60 - (current_time - _last_api_call)
            if sleep_time > 0:
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.1f}s")
                time.sleep(sleep_time)
                _api_call_count = 0
        
        _last_api_call = current_time
        _api_call_count += 1

    def fetch_lyrics(self, title: str, artist: str) -> Optional[str]:
        """
        Fetch lyrics for a song with caching and rate limiting.
        Optimized for speed while maintaining thoroughness.
        """
        if not self.genius:
            logger.debug("LyricsFetcher: No Genius client available")
            return None

        # Check cache first
        cache_key = self._get_cache_key(title, artist)
        if cache_key in _lyrics_cache:
            logger.debug(f"Cache hit for '{title}' by '{artist}'")
            return _lyrics_cache[cache_key]

        # Clean the search terms
        clean_title = self._clean_title(title)
        clean_artist = self._clean_artist(artist)
        
        logger.debug(f"Fetching lyrics for '{clean_title}' by '{clean_artist}'")
        
        try:
            # Respect rate limits
            self._respect_rate_limit()
            
            # Search for the song with optimized parameters
            song = self.genius.search_song(
                title=clean_title,
                artist=clean_artist,
                get_full_info=False  # Faster search
            )
            
            if song and song.lyrics:
                # Clean up the lyrics
                lyrics = self._clean_lyrics(song.lyrics)
                
                # Cache the result
                _lyrics_cache[cache_key] = lyrics
                
                logger.debug(f"Successfully fetched lyrics for '{title}' ({len(lyrics)} chars)")
                return lyrics
            else:
                logger.debug(f"No lyrics found for '{title}' by '{artist}'")
                # Cache the negative result to avoid repeated searches
                _lyrics_cache[cache_key] = None
                return None
                
        except Exception as e:
            logger.warning(f"Error fetching lyrics for '{title}' by '{artist}': {e}")
            # Cache the negative result
            _lyrics_cache[cache_key] = None
            return None

    def _clean_lyrics(self, lyrics: str) -> str:
        """Clean and normalize lyrics text"""
        if not lyrics:
            return ""
        
        # Remove Genius-specific annotations and metadata
        lyrics = re.sub(r'\[.*?\]', '', lyrics)  # Remove [Verse 1], [Chorus], etc.
        lyrics = re.sub(r'\d+Embed$', '', lyrics)  # Remove trailing "123Embed"
        lyrics = re.sub(r'You might also like.*$', '', lyrics, flags=re.MULTILINE)
        
        # Normalize whitespace
        lyrics = re.sub(r'\n\s*\n', '\n\n', lyrics)  # Normalize paragraph breaks
        lyrics = re.sub(r'[ \t]+', ' ', lyrics)  # Normalize spaces
        
        return lyrics.strip()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for monitoring"""
        return {
            "cache_size": len(_lyrics_cache),
            "api_calls_this_minute": _api_call_count
        }
