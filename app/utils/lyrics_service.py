import logging
from typing import Optional

logger = logging.getLogger(__name__)

class LyricsService:
    """Enhanced lyrics fetching service with multiple sources and error handling."""
    
    def __init__(self):
        self.genius_client_id = "kkoMEis9fiik4w4ZaI3Dn5ZmPVH7iZGeoOqXENWp1hZ8A3dajhUHfAHD8WSIziON"
        self.genius_secret = "o5AOPZW_-Fhs84DUbZwkCOzBtTu_bo0vDsYWD_99BrnNa7KRUi3FH41n1C2DyGfp3H-cNawUBPq0MPwviPmfgg"
        
    def fetch_lyrics(self, artist: str, title: str) -> Optional[str]:
        """
        Fetch lyrics from multiple sources with fallback.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Lyrics text or None if not found
        """
        logger.info(f"Fetching lyrics for '{title}' by {artist}")
        
        # Try azlyrics first
        lyrics = self._try_azlyrics(artist, title)
        if lyrics:
            return lyrics
            
        # Try Genius API
        lyrics = self._try_genius(artist, title)
        if lyrics:
            return lyrics
            
        # Try web scraping as last resort
        lyrics = self._try_web_scraping(artist, title)
        if lyrics:
            return lyrics
            
        logger.warning(f"Could not fetch lyrics for '{title}' by {artist}")
        return None
        
    def _try_azlyrics(self, artist: str, title: str) -> Optional[str]:
        """Try fetching from azlyrics library."""
        try:
            from azlyrics import lyrics
            result = lyrics.get_lyrics(artist, title)
            if result and len(result.strip()) > 50:  # Basic validation
                logger.info("Successfully fetched lyrics from azlyrics")
                return result.strip()
        except Exception as e:
            logger.debug(f"azlyrics failed: {e}")
        return None
        
    def _try_genius(self, artist: str, title: str) -> Optional[str]:
        """Try fetching from Genius API."""
        try:
            # This would require implementing Genius API integration
            # For now, return None to fall back to other methods
            logger.debug("Genius API not implemented yet")
            return None
        except Exception as e:
            logger.debug(f"Genius API failed: {e}")
        return None
        
    def _try_web_scraping(self, artist: str, title: str) -> Optional[str]:
        """Try web scraping as last resort."""
        try:
            # This would require implementing web scraping
            # For now, return None
            logger.debug("Web scraping not implemented yet")
            return None
        except Exception as e:
            logger.debug(f"Web scraping failed: {e}")
        return None

# Global instance
lyrics_service = LyricsService()

def get_song_lyrics(artist: str, title: str) -> Optional[str]:
    """
    Convenience function to fetch lyrics.
    
    Args:
        artist: Artist name
        title: Song title
        
    Returns:
        Lyrics text or None if not found
    """
    return lyrics_service.fetch_lyrics(artist, title)
