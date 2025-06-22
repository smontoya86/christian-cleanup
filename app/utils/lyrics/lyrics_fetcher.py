import os
import re
import requests # Will be used by lyricsgenius and potentially for alternative sources
import lyricsgenius
from flask import current_app # Corrected import
import logging # Added standard logging import
import hashlib
import time
import random
from typing import Optional, Dict, Any
from requests.exceptions import RequestException
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

# Import configuration and metrics systems
from app.utils.lyrics_config import get_config, LyricsFetcherConfig
from app.utils.lyrics_metrics import get_metrics_collector, LyricsMetricsCollector

# Import database models for caching
from app.models.models import db, LyricsCache

# Import performance tracking decorators
from app.utils.database_performance_tracking import track_lyrics_call

# Import retry logic and error handling utilities
from ..retry import requests_with_retry, retry_with_config, RetryableHTTPError
from ..api_responses import external_service_error, rate_limit_error, timeout_error

# It's good practice to get a specific logger instance for your module/class
logger = logging.getLogger(__name__)

# Legacy API call tracking (kept for rate limiting)
_last_api_call = 0
_api_call_count = 0


class LyricsProvider(ABC):
    """
    Abstract base class for lyrics providers.
    All lyrics providers must implement the fetch_lyrics method.
    """
    
    @abstractmethod
    def fetch_lyrics(self, artist: str, title: str) -> Optional[str]:
        """
        Fetch lyrics for a song.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Lyrics text or None if not found
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get the name of this provider for logging purposes."""
        return self.__class__.__name__


class LRCLibProvider(LyricsProvider):
    """
    LRCLib provider for time-synced lyrics.
    Primary source with no rate limits and no API key required.
    """
    
    def __init__(self):
        self.base_url = "https://lrclib.net/api/search"
        self.headers = {
            'User-Agent': 'Christian Cleanup App/1.0 (https://github.com/sammontoya/christian-cleanup)'
        }
        self.timeout = 20  # Increased from 10 to 20 seconds
    
    @track_lyrics_call("lrclib_search")
    @retry_with_config(config_prefix='LYRICS_RETRY')
    def fetch_lyrics(self, artist: str, title: str) -> Optional[str]:
        """
        Fetch lyrics from LRCLib API.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Lyrics text (preferring synced lyrics) or None if not found
        """
        try:
            # Clean the search terms
            clean_artist = self._clean_search_term(artist)
            clean_title = self._clean_search_term(title)
            
            # Search parameters
            search_params = {
                'artist_name': clean_artist,
                'track_name': clean_title
            }
            
            logger.debug(f"LRCLibProvider: Searching for '{clean_title}' by '{clean_artist}'")
            
            # Make the API request
            response = requests.get(
                self.base_url,
                params=search_params,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                logger.debug(f"LRCLibProvider: API returned status {response.status_code}")
                return None
            
            data = response.json()
            if not data or len(data) == 0:
                logger.debug(f"LRCLibProvider: No results found")
                return None
            
            # Get the first result with lyrics (prefer synced, fall back to plain)
            for result in data:
                # Try synced lyrics first (time-stamped)
                if result.get('syncedLyrics'):
                    logger.debug(f"LRCLibProvider: Found synced lyrics ({len(result['syncedLyrics'])} chars)")
                    return self._clean_synced_lyrics(result['syncedLyrics'])
                
                # Fall back to plain lyrics
                elif result.get('plainLyrics'):
                    logger.debug(f"LRCLibProvider: Found plain lyrics ({len(result['plainLyrics'])} chars)")
                    return self._clean_lyrics(result['plainLyrics'])
            
            logger.debug(f"LRCLibProvider: Results found but no lyrics available")
            return None
            
        except requests.exceptions.Timeout:
            logger.warning(f"LRCLibProvider: Request timeout for '{title}' by '{artist}'")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"LRCLibProvider: Request error for '{title}' by '{artist}': {e}")
            return None
        except Exception as e:
            logger.error(f"LRCLibProvider: Unexpected error for '{title}' by '{artist}': {e}")
            return None
    
    def _clean_search_term(self, term: str) -> str:
        """Clean search terms for better API matching."""
        if not term:
            return ""
        
        # Remove common suffixes and noise
        term = re.sub(r'\s*\(.*?\)\s*', ' ', term)  # Remove parenthetical content
        term = re.sub(r'\s*\[.*?\]\s*', ' ', term)  # Remove bracketed content
        term = re.sub(r'\s*(feat\.|featuring|ft\.).*$', '', term, flags=re.IGNORECASE)
        term = re.sub(r'\s*-\s*(Remaster|Remix|Live|Acoustic|Demo).*$', '', term, flags=re.IGNORECASE)
        term = re.sub(r'\s+', ' ', term)  # Normalize whitespace
        
        return term.strip()
    
    def _clean_synced_lyrics(self, lyrics: str) -> str:
        """
        Clean synced lyrics by removing timestamps but preserving structure.
        
        Args:
            lyrics: Raw synced lyrics with timestamps
            
        Returns:
            Clean lyrics text without timestamps
        """
        if not lyrics:
            return ""
        
        # Remove LRC timestamps [mm:ss.xx] or [mm:ss]
        lyrics = re.sub(r'\[\d{2}:\d{2}(?:\.\d{2})?\]', '', lyrics)
        
        # Clean up extra whitespace and empty lines
        lyrics = re.sub(r'\n\s*\n', '\n\n', lyrics)  # Normalize paragraph breaks
        lyrics = re.sub(r'[ \t]+', ' ', lyrics)  # Normalize spaces
        
        return lyrics.strip()
    
    def _clean_lyrics(self, lyrics: str) -> str:
        """Clean plain lyrics text."""
        if not lyrics:
            return ""
        
        # Normalize whitespace
        lyrics = re.sub(r'\n\s*\n', '\n\n', lyrics)  # Normalize paragraph breaks
        lyrics = re.sub(r'[ \t]+', ' ', lyrics)  # Normalize spaces
        
        return lyrics.strip()


class LyricsOvhProvider(LyricsProvider):
    """
    Lyrics.ovh provider as secondary fallback.
    Simple API with no authentication required.
    """
    
    def __init__(self):
        self.base_url = "https://api.lyrics.ovh/v1"
        self.headers = {
            'User-Agent': 'Christian Cleanup App/1.0'
        }
        self.timeout = 20  # Increased from 10 to 20 seconds
    
    @track_lyrics_call("lyrics_ovh_search")
    @retry_with_config(config_prefix='LYRICS_RETRY')
    def fetch_lyrics(self, artist: str, title: str) -> Optional[str]:
        """
        Fetch lyrics from Lyrics.ovh API.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Lyrics text or None if not found
        """
        try:
            # Clean the search terms
            clean_artist = self._clean_search_term(artist)
            clean_title = self._clean_search_term(title)
            
            # Format the URL - lyrics.ovh uses path parameters
            url = f"{self.base_url}/{clean_artist}/{clean_title}"
            
            logger.debug(f"LyricsOvhProvider: Fetching from {url}")
            
            # Make the API request
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                logger.debug(f"LyricsOvhProvider: API returned status {response.status_code}")
                return None
            
            data = response.json()
            if 'lyrics' not in data or not data['lyrics']:
                logger.debug(f"LyricsOvhProvider: No lyrics found in response")
                return None
            
            lyrics = data['lyrics'].strip()
            if not lyrics:
                logger.debug(f"LyricsOvhProvider: Empty lyrics returned")
                return None
            
            logger.debug(f"LyricsOvhProvider: Found lyrics ({len(lyrics)} chars)")
            return self._clean_lyrics(lyrics)
            
        except requests.exceptions.Timeout:
            logger.warning(f"LyricsOvhProvider: Request timeout for '{title}' by '{artist}'")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"LyricsOvhProvider: Request error for '{title}' by '{artist}': {e}")
            return None
        except Exception as e:
            logger.error(f"LyricsOvhProvider: Unexpected error for '{title}' by '{artist}': {e}")
            return None
    
    def _clean_search_term(self, term: str) -> str:
        """Clean search terms for URL encoding."""
        if not term:
            return ""
        
        # Remove common suffixes and noise
        term = re.sub(r'\s*\(.*?\)\s*', ' ', term)  # Remove parenthetical content
        term = re.sub(r'\s*\[.*?\]\s*', ' ', term)  # Remove bracketed content
        term = re.sub(r'\s*(feat\.|featuring|ft\.).*$', '', term, flags=re.IGNORECASE)
        term = re.sub(r'\s*-\s*(Remaster|Remix|Live|Acoustic|Demo).*$', '', term, flags=re.IGNORECASE)
        term = re.sub(r'\s+', ' ', term)  # Normalize whitespace
        
        return term.strip()
    
    def _clean_lyrics(self, lyrics: str) -> str:
        """Clean lyrics text."""
        if not lyrics:
            return ""
        
        # Remove common artifacts
        lyrics = re.sub(r'Paroles de la chanson.*?par.*?\n', '', lyrics, flags=re.IGNORECASE)
        
        # Normalize whitespace
        lyrics = re.sub(r'\n\s*\n', '\n\n', lyrics)  # Normalize paragraph breaks
        lyrics = re.sub(r'[ \t]+', ' ', lyrics)  # Normalize spaces
        
        return lyrics.strip()


class GeniusProvider(LyricsProvider):
    """
    Genius provider wrapper for the existing LyricsGenius integration.
    This maintains backward compatibility with the current implementation.
    """
    
    def __init__(self, genius_client=None):
        self.genius = genius_client
    
    @track_lyrics_call("genius_search")
    @retry_with_config(config_prefix='LYRICS_RETRY')
    def fetch_lyrics(self, artist: str, title: str) -> Optional[str]:
        """
        Fetch lyrics using the existing Genius client.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Lyrics text or None if not found
        """
        if not self.genius:
            logger.debug("GeniusProvider: No Genius client available")
            return None
        
        try:
            # Clean the search terms
            clean_title = self._clean_title(title)
            clean_artist = self._clean_artist(artist)
            
            logger.debug(f"GeniusProvider: Searching for '{clean_title}' by '{clean_artist}'")
            
            # Search for the song
            song = self.genius.search_song(
                title=clean_title,
                artist=clean_artist,
                get_full_info=False  # Faster search
            )
            
            if song and song.lyrics:
                lyrics = self._clean_lyrics(song.lyrics)
                logger.debug(f"GeniusProvider: Found lyrics ({len(lyrics)} chars)")
                return lyrics
            else:
                logger.debug(f"GeniusProvider: No lyrics found")
                return None
                
        except Exception as e:
            logger.warning(f"GeniusProvider: Error fetching lyrics for '{title}' by '{artist}': {e}")
            return None
    
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


class TokenBucket:
    """
    Token bucket algorithm for request throttling.
    Tokens refill at a constant rate and are consumed by requests.
    """
    
    def __init__(self, capacity: int = 10, refill_rate: float = 1.0):
        """
        Initialize the token bucket.
        
        Args:
            capacity: Maximum number of tokens in the bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity  # Start with full bucket
        self.last_refill = time.time()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        current_time = time.time()
        elapsed = current_time - self.last_refill
        
        if elapsed > 0:
            tokens_to_add = elapsed * self.refill_rate
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = current_time
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        if tokens < 0:
            return False
        
        if tokens == 0:
            return True
        
        self._refill()
        
        # Check if we have enough tokens (fractional tokens allowed)
        if int(self.tokens) >= tokens:
            self.tokens -= tokens
            return True
        
        return False
    
    def get_available_tokens(self) -> int:
        """
        Get current number of available tokens (includes refill).
        
        Returns:
            Number of tokens currently available
        """
        self._refill()
        return int(self.tokens)
    
    def time_until_available(self, tokens: int) -> float:
        """
        Calculate time until specified number of tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Time in seconds until tokens are available, 0 if available now
        """
        self._refill()
        
        if int(self.tokens) >= tokens:
            return 0.0
        
        # Can't have more tokens than capacity
        tokens_needed = min(tokens, self.capacity) - int(self.tokens)
        return tokens_needed / self.refill_rate
    
    def reset(self) -> None:
        """Reset bucket to full capacity."""
        self.tokens = self.capacity
        self.last_refill = time.time()


class RateLimitTracker:
    """
    Tracks API request rates within a sliding time window to detect when approaching rate limits.
    """
    
    def __init__(self, window_size: int = 60, max_requests: int = 50):
        """
        Initialize the rate limit tracker.
        
        Args:
            window_size: Time window in seconds (default: 60)
            max_requests: Maximum requests allowed in the window (default: 50)
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.request_timestamps = []
    
    def can_make_request(self) -> bool:
        """
        Check if a new request can be made without exceeding the rate limit.
        
        Returns:
            True if request can be made, False if rate limit would be exceeded
        """
        self._cleanup_old_timestamps()
        return len(self.request_timestamps) < self.max_requests
    
    def record_request(self) -> None:
        """Record that a request was made at the current time."""
        self.request_timestamps.append(time.time())
    
    def get_current_request_count(self) -> int:
        """
        Get the current number of requests in the time window.
        
        Returns:
            Number of requests in the current window
        """
        self._cleanup_old_timestamps()
        return len(self.request_timestamps)
    
    def time_until_next_available(self) -> float:
        """
        Calculate the time until the next request can be made.
        
        Returns:
            Time in seconds until next request is available, 0 if available now
        """
        if self.can_make_request():
            return 0.0
        
        if not self.request_timestamps:
            return 0.0
        
        # Time until the oldest request expires from the window
        oldest_timestamp = min(self.request_timestamps)
        current_time = time.time()
        time_until_expire = self.window_size - (current_time - oldest_timestamp)
        
        return max(0.0, time_until_expire)
    
    def reset(self) -> None:
        """Reset the tracker, clearing all recorded timestamps."""
        self.request_timestamps = []
    
    def _cleanup_old_timestamps(self) -> None:
        """Remove timestamps that are outside the current time window."""
        current_time = time.time()
        cutoff_time = current_time - self.window_size
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > cutoff_time]

class LyricsFetcher:
    def __init__(self, genius_token=None, config: Optional[LyricsFetcherConfig] = None):
        self.genius_token = genius_token
        
        # Load configuration
        self.config = config or get_config()
        
        # Initialize metrics collector
        self.metrics = get_metrics_collector()
        
        # Try to get the token from the environment first
        if not self.genius_token:
            self.genius_token = os.getenv('GENIUS_ACCESS_TOKEN')
        
        # Initialize rate limit tracker using configuration
        self.rate_tracker = RateLimitTracker(
            window_size=self.config.rate_limit_window_size,
            max_requests=self.config.rate_limit_max_requests
        )
        
        # Initialize token bucket using configuration
        self.token_bucket = TokenBucket(
            capacity=self.config.token_bucket_capacity,
            refill_rate=self.config.token_bucket_refill_rate
        )
        
        # Initialize the Genius client with optimized settings
        self.genius = None
        if self.genius_token:
            try:
                self.genius = lyricsgenius.Genius(
                    self.genius_token,
                    timeout=self.config.genius_timeout,
                    sleep_time=self.config.genius_sleep_time,
                    retries=self.config.genius_retries,
                    remove_section_headers=True,
                    skip_non_songs=True,
                    excluded_terms=self.config.genius_excluded_terms,
                    verbose=False
                )
                if self.config.log_api_calls:
                    logger.info("LyricsFetcher: LyricsGenius client initialized successfully.")
                self.metrics.record_event('client_initialized', success=True)
            except Exception as e:
                logger.error(f"LyricsFetcher: Failed to initialize LyricsGenius client: {e}")
                self.genius = None
                self.metrics.record_error('client_initialization_failed', error=str(e))
        else:
            logger.warning("LyricsFetcher: No Genius token provided. Genius lyrics fetching will be disabled.")
            self.metrics.record_event('client_initialization_skipped', reason='no_token')
        
        # Initialize the provider chain in order of preference
        self.providers = []
        
        # 1. LRCLib - Primary source (free, time-synced lyrics, no rate limits)
        try:
            self.providers.append(LRCLibProvider())
            logger.debug("LyricsFetcher: LRCLibProvider initialized")
        except Exception as e:
            logger.warning(f"LyricsFetcher: Failed to initialize LRCLibProvider: {e}")
        
        # 2. Lyrics.ovh - Secondary source (free, simple API)
        try:
            self.providers.append(LyricsOvhProvider())
            logger.debug("LyricsFetcher: LyricsOvhProvider initialized")
        except Exception as e:
            logger.warning(f"LyricsFetcher: Failed to initialize LyricsOvhProvider: {e}")
        
        # 3. Genius - Tertiary source (requires API key, but comprehensive)
        if self.genius:
            try:
                self.providers.append(GeniusProvider(self.genius))
                logger.debug("LyricsFetcher: GeniusProvider initialized")
            except Exception as e:
                logger.warning(f"LyricsFetcher: Failed to initialize GeniusProvider: {e}")
        
        if self.config.log_api_calls:
            provider_names = [provider.get_provider_name() for provider in self.providers]
            logger.info(f"LyricsFetcher: Initialized with {len(self.providers)} providers: {', '.join(provider_names)}")
        
        # Track provider usage statistics
        self.provider_stats = {provider.get_provider_name(): {'attempts': 0, 'successes': 0} for provider in self.providers}

    def _get_cache_key(self, title: str, artist: str) -> str:
        """Generate a cache key for a song"""
        # Use artist:title format for database lookup compatibility
        artist_clean = artist.lower().strip()
        title_clean = title.lower().strip()
        return f"{artist_clean}:{title_clean}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Get lyrics from database cache if available"""
        try:
            # Extract artist and title from cache key for database lookup
            # Cache key format is typically "artist:title" or similar
            parts = cache_key.split(':')
            if len(parts) >= 2:
                artist = parts[0]
                title = parts[1]
            else:
                # Fallback: try to parse from the cache key
                # This shouldn't happen with our current implementation
                if self.config.log_cache_operations:
                    logger.warning(f"Invalid cache key format: {cache_key[:8]}...")
                return None
            
            # Look up in database cache
            cache_entry = LyricsCache.find_cached_lyrics(artist, title)
            
            if cache_entry:
                if self.config.log_cache_operations:
                    logger.debug(f"Database cache hit for '{artist}' - '{title}' (source: {cache_entry.source})")
                self.metrics.record_cache_operation('lookup', hit=True, key=cache_key[:8])
                return cache_entry.lyrics
            else:
                if self.config.log_cache_operations:
                    logger.debug(f"Database cache miss for '{artist}' - '{title}'")
                self.metrics.record_cache_operation('lookup', hit=False, key=cache_key[:8])
                return None
                
        except Exception as e:
            if self.config.log_cache_operations:
                logger.error(f"Error accessing database cache: {e}")
            self.metrics.record_error('cache_lookup_error', error=str(e))
            return None
    
    def _store_in_cache(self, cache_key: str, lyrics: Optional[str], ttl: int = None) -> None:
        """Store lyrics in database cache"""
        try:
            # Extract artist and title from cache key
            parts = cache_key.split(':')
            if len(parts) >= 2:
                artist = parts[0]
                title = parts[1]
            else:
                if self.config.log_cache_operations:
                    logger.warning(f"Invalid cache key format for storage: {cache_key[:8]}...")
                return
            
            # Don't cache None/empty lyrics
            if not lyrics:
                if self.config.log_cache_operations:
                    logger.debug(f"Skipping cache storage for empty lyrics: '{artist}' - '{title}'")
                return
            
            # Determine the source provider (use the last successful provider)
            source = 'unknown'
            for provider_name, stats in self.provider_stats.items():
                if stats.get('successes', 0) > 0:
                    source = provider_name
                    break
            
            # Store in database cache
            cache_entry = LyricsCache.cache_lyrics(artist, title, lyrics, source)
            db.session.commit()
            
            if self.config.log_cache_operations:
                logger.debug(f"Cached lyrics in database for '{artist}' - '{title}' (source: {source}, {len(lyrics)} chars)")
            self.metrics.record_cache_operation('store', key=cache_key[:8], source=source)
            
        except Exception as e:
            db.session.rollback()
            if self.config.log_cache_operations:
                logger.error(f"Error storing lyrics in database cache: {e}")
            self.metrics.record_error('cache_store_error', error=str(e))
    
    def clear_cache(self) -> None:
        """Clear all cached lyrics from database"""
        try:
            count = LyricsCache.query.count()
            LyricsCache.query.delete()
            db.session.commit()
            logger.info(f"Database lyrics cache cleared ({count} entries removed)")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing database cache: {e}")
    
    def cleanup_expired_cache(self) -> int:
        """Remove old entries from database cache and return count of removed entries"""
        try:
            # Remove entries older than the configured max age
            max_age_days = current_app.config.get('LYRICS_CACHE_MAX_AGE_DAYS', 30)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            
            old_entries = LyricsCache.query.filter(LyricsCache.updated_at < cutoff_date).all()
            count = len(old_entries)
            
            for entry in old_entries:
                db.session.delete(entry)
            
            db.session.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {count} old database cache entries")
            
            return count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error cleaning up database cache: {e}")
            return 0

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

    def fetch_with_retry(self, url: str, headers: Optional[Dict[str, str]] = None, max_retries: int = None):
        """
        Fetch URL with exponential backoff retry mechanism for handling rate limits.
        
        Args:
            url: URL to fetch
            headers: Optional headers to include in request
            max_retries: Total number of attempts (including initial attempt, default from config)
            
        Returns:
            requests.Response object
            
        Raises:
            RequestException: If all retries are exhausted or non-retryable error occurs
        """
        if max_retries is None:
            max_retries = self.config.max_retries
        
        attempt = 0
        start_time = time.time()
        
        while attempt < max_retries:
            try:
                if self.config.log_api_calls:
                    logger.debug(f"Making request to {url} (attempt {attempt + 1}/{max_retries})")
                
                request_start = time.time()
                response = requests.get(url, headers=headers, timeout=10)
                request_duration = time.time() - request_start
                
                # Record API call metrics
                self.metrics.record_api_call(
                    duration=request_duration,
                    success=response.status_code < 400,
                    status_code=response.status_code,
                    attempt=attempt + 1
                )
                
                if response.status_code == 429:  # Too Many Requests
                    self.metrics.record_rate_limit_event('hit', attempt=attempt + 1)
                    
                    if attempt >= max_retries - 1:  # Last attempt
                        if self.config.log_retry_attempts:
                            logger.warning(f"Rate limit exceeded after {max_retries} attempts for {url}")
                        self.metrics.record_error('max_retries_exceeded', url=url, attempts=max_retries)
                        return response  # Return the 429 response
                    
                    # Get retry delay from header, or use exponential backoff
                    retry_after = int(response.headers.get('Retry-After', 0))
                    exponential_delay = (self.config.base_delay ** (attempt + 1)) + random.uniform(0, self.config.jitter_factor)
                    sleep_time = min(max(exponential_delay, retry_after), self.config.max_delay)
                    
                    if self.config.log_retry_attempts:
                        logger.info(f"Rate limited (429). Sleeping for {sleep_time:.2f}s before retry {attempt + 1}")
                    
                    self.metrics.record_retry_attempt(attempt + 1, sleep_time, reason='rate_limit')
                    time.sleep(sleep_time)
                    attempt += 1
                    continue
                
                # Success or non-retryable error
                total_duration = time.time() - start_time
                self.metrics.record_event('request_completed', duration=total_duration, attempts=attempt + 1, success=True)
                return response
                
            except RequestException as e:
                self.metrics.record_error('request_exception', error=str(e), attempt=attempt + 1)
                
                if attempt >= max_retries - 1:  # Last attempt
                    if self.config.log_retry_attempts:
                        logger.error(f"Request failed after {max_retries} attempts: {e}")
                    total_duration = time.time() - start_time
                    self.metrics.record_event('request_failed', duration=total_duration, attempts=max_retries, error=str(e))
                    raise e
                
                # Exponential backoff for network errors
                sleep_time = min((self.config.base_delay ** (attempt + 1)) + random.uniform(0, self.config.jitter_factor), self.config.max_delay)
                
                if self.config.log_retry_attempts:
                    logger.warning(f"Request error: {e}. Retrying in {sleep_time:.2f}s (attempt {attempt + 1})")
                
                self.metrics.record_retry_attempt(attempt + 1, sleep_time, reason='network_error', error=str(e))
                time.sleep(sleep_time)
                attempt += 1
        
        # This shouldn't be reached, but just in case
        total_duration = time.time() - start_time
        self.metrics.record_error('unexpected_retry_exhaustion', attempts=max_retries, duration=total_duration)
        raise RequestException(f"Exhausted all {max_retries} attempts for {url}")

    def _respect_rate_limit(self):
        """Implement smart rate limiting using both RateLimitTracker and TokenBucket"""
        # First check token bucket throttling
        if not self.token_bucket.consume(1):
            sleep_time = self.token_bucket.time_until_available(1)
            if sleep_time > 0:
                if self.config.log_rate_limit_events:
                    logger.info(f"Token bucket throttling: Sleeping for {sleep_time:.1f}s before next request")
                self.metrics.record_rate_limit_event('token_bucket_wait', sleep_time)
                time.sleep(sleep_time)
                # Try to consume token again after waiting
                if not self.token_bucket.consume(1):
                    logger.warning("Failed to consume token even after waiting")
                    self.metrics.record_error('token_bucket_failure')
        
        # Then check sliding window rate limit
        if not self.rate_tracker.can_make_request():
            sleep_time = self.rate_tracker.time_until_next_available()
            if sleep_time > 0:
                if self.config.log_rate_limit_events:
                    logger.info(f"Rate limit reached. Sleeping for {sleep_time:.1f}s before next request")
                self.metrics.record_rate_limit_event('sliding_window_wait', sleep_time)
                time.sleep(sleep_time)
        
        # Record that we're about to make a request
        self.rate_tracker.record_request()
        
        # Log current rate limit status
        if self.config.log_rate_limit_events:
            current_count = self.rate_tracker.get_current_request_count()
            available_tokens = self.token_bucket.get_available_tokens()
            logger.debug(f"Rate limiting: {current_count}/{self.rate_tracker.max_requests} requests in window, {available_tokens} tokens available")

    def fetch_lyrics(self, title: str, artist: str, cache_ttl: int = None) -> Optional[str]:
        """
        Fetch lyrics for a song using the provider chain with enhanced caching and rate limiting.
        Tries each provider in sequence until lyrics are found.
        
        Args:
            title: Song title
            artist: Artist name
            cache_ttl: Cache time-to-live in seconds (default from config)
            
        Returns:
            Lyrics text or None if not found
        """
        if cache_ttl is None:
            cache_ttl = self.config.default_cache_ttl
        
        start_time = time.time()
        
        # Validate input parameters
        if not title or not artist:
            if self.config.log_api_calls:
                logger.debug("LyricsFetcher: Title and artist are required")
            self.metrics.record_error('invalid_input', title=bool(title), artist=bool(artist))
            return None

        # Check if we have any providers available
        if not self.providers:
            if self.config.log_api_calls:
                logger.debug("LyricsFetcher: No providers available")
            self.metrics.record_error('no_providers_available')
            return None

        # Check enhanced cache first
        cache_key = self._get_cache_key(title, artist)
        cached_lyrics = self._get_from_cache(cache_key)
        if cached_lyrics is not None:
            if self.config.log_cache_operations:
                logger.debug(f"Cache hit for '{title}' by '{artist}'")
            duration = time.time() - start_time
            self.metrics.record_event('lyrics_fetch_completed', duration, source='cache', success=True)
            return cached_lyrics

        if self.config.log_api_calls:
            logger.debug(f"Fetching lyrics for '{title}' by '{artist}' using {len(self.providers)} providers")
        
        # Try each provider in sequence
        for i, provider in enumerate(self.providers):
            provider_name = provider.get_provider_name()
            
            try:
                # Update provider stats
                self.provider_stats[provider_name]['attempts'] += 1
                
                if self.config.log_api_calls:
                    logger.debug(f"Trying provider {i+1}/{len(self.providers)}: {provider_name}")
                
                # For Genius provider, respect rate limits
                if isinstance(provider, GeniusProvider):
                    self._respect_rate_limit()
                
                # Attempt to fetch lyrics
                api_start = time.time()
                lyrics = provider.fetch_lyrics(artist, title)
                api_duration = time.time() - api_start
                
                # Record API call metrics
                self.metrics.record_api_call(
                    api_duration, 
                    success=bool(lyrics), 
                    title=title, 
                    artist=artist,
                    provider=provider_name
                )
                
                if lyrics:
                    # Success! Update stats and cache result
                    self.provider_stats[provider_name]['successes'] += 1
                    
                    # Cache the result with TTL
                    self._store_in_cache(cache_key, lyrics, cache_ttl)
                    
                    if self.config.log_api_calls:
                        logger.debug(f"Successfully fetched lyrics using {provider_name} ({len(lyrics)} chars)")
                    
                    total_duration = time.time() - start_time
                    self.metrics.record_event(
                        'lyrics_fetch_completed', 
                        duration=total_duration, 
                        source=provider_name, 
                        success=True, 
                        lyrics_length=len(lyrics),
                        provider_index=i
                    )
                    return lyrics
                else:
                    if self.config.log_api_calls:
                        logger.debug(f"No lyrics found using {provider_name}")
                    
                    # Continue to next provider
                    continue
                    
            except Exception as e:
                if self.config.log_api_calls:
                    logger.warning(f"Error with provider {provider_name} for '{title}' by '{artist}': {e}")
                
                self.metrics.record_error(
                    'provider_error', 
                    error=str(e), 
                    provider=provider_name, 
                    title=title, 
                    artist=artist
                )
                
                # Continue to next provider
                continue
        
        # All providers failed
        if self.config.log_api_calls:
            logger.debug(f"No lyrics found for '{title}' by '{artist}' after trying all {len(self.providers)} providers")
        
        # Cache the negative result with shorter TTL to allow retries
        self._store_in_cache(cache_key, None, self.config.negative_cache_ttl)
        
        total_duration = time.time() - start_time
        self.metrics.record_event(
            'lyrics_fetch_completed', 
            duration=total_duration, 
            source='all_providers', 
            success=False, 
            reason='not_found_any_provider'
        )
        return None
    
    def get_synced_lyrics(self, title: str, artist: str) -> Optional[str]:
        """
        Specifically try to get time-synced lyrics from LRCLib.
        This method bypasses the provider chain and goes directly to LRCLib.
        
        Args:
            title: Song title
            artist: Artist name
            
        Returns:
            Time-synced lyrics or None if not found
        """
        try:
            # Find LRCLib provider
            lrclib_provider = None
            for provider in self.providers:
                if isinstance(provider, LRCLibProvider):
                    lrclib_provider = provider
                    break
            
            if not lrclib_provider:
                logger.debug("get_synced_lyrics: LRCLibProvider not available")
                return None
            
            if self.config.log_api_calls:
                logger.debug(f"Fetching synced lyrics for '{title}' by '{artist}' from LRCLib")
            
            lyrics = lrclib_provider.fetch_lyrics(artist, title)
            
            if lyrics:
                if self.config.log_api_calls:
                    logger.debug(f"Found synced lyrics from LRCLib ({len(lyrics)} chars)")
                return lyrics
            else:
                if self.config.log_api_calls:
                    logger.debug("No synced lyrics found in LRCLib")
                return None
                
        except Exception as e:
            logger.warning(f"Error getting synced lyrics: {e}")
            return None
    
    def get_provider_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about provider usage and success rates.
        
        Returns:
            Dictionary with provider names as keys and stats as values
        """
        stats = {}
        for provider_name, provider_stats in self.provider_stats.items():
            attempts = provider_stats['attempts']
            successes = provider_stats['successes']
            success_rate = (successes / attempts * 100) if attempts > 0 else 0
            
            stats[provider_name] = {
                'attempts': attempts,
                'successes': successes,
                'success_rate': round(success_rate, 2)
            }
        
        return stats

    def is_rate_limited(self, response) -> bool:
        """
        Check if a response indicates rate limiting.
        
        Args:
            response: HTTP response object
            
        Returns:
            True if response indicates rate limiting, False otherwise
        """
        if hasattr(response, 'status_code') and response.status_code == 429:
            return True
        
        # Check for common rate limit headers
        if hasattr(response, 'headers'):
            rate_limit_headers = [
                'X-RateLimit-Remaining',
                'X-Rate-Limit-Remaining', 
                'RateLimit-Remaining',
                'Rate-Limit-Remaining'
            ]
            
            for header in rate_limit_headers:
                if header in response.headers:
                    try:
                        remaining = int(response.headers[header])
                        if remaining <= 0:
                            logger.warning(f"Rate limit detected via header {header}: {remaining} remaining")
                            return True
                    except (ValueError, TypeError):
                        continue
        
        return False
    
    def is_approaching_rate_limit(self, threshold: float = 0.8) -> bool:
        """
        Check if we're approaching the rate limit threshold.
        
        Args:
            threshold: Percentage of limit to consider "approaching" (default: 0.8 = 80%)
            
        Returns:
            True if approaching rate limit, False otherwise
        """
        current_count = self.rate_tracker.get_current_request_count()
        limit_threshold = int(self.rate_tracker.max_requests * threshold)
        
        approaching = current_count >= limit_threshold
        if approaching:
            logger.warning(f"Approaching rate limit: {current_count}/{self.rate_tracker.max_requests} requests ({threshold*100:.0f}% threshold)")
        
        return approaching
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache and performance statistics for monitoring"""
        try:
            # Get database cache statistics
            total_cache_entries = LyricsCache.query.count()
            
            # Get source breakdown
            source_stats = {}
            sources = db.session.query(
                LyricsCache.source, 
                db.func.count(LyricsCache.id)
            ).group_by(LyricsCache.source).all()
            
            for source, count in sources:
                source_stats[source] = count
            
            # Get oldest and newest entries
            oldest_entry = LyricsCache.query.order_by(LyricsCache.created_at.asc()).first()
            newest_entry = LyricsCache.query.order_by(LyricsCache.created_at.desc()).first()
            
            # Calculate cache age statistics
            cache_age_stats = {}
            if oldest_entry and newest_entry:
                cache_age_stats = {
                    "oldest_entry": oldest_entry.created_at.isoformat(),
                    "newest_entry": newest_entry.created_at.isoformat(),
                    "cache_span_days": (newest_entry.created_at - oldest_entry.created_at).days
                }
            
        except Exception as e:
            logger.error(f"Error getting database cache stats: {e}")
            total_cache_entries = 0
            source_stats = {}
            cache_age_stats = {}
        
        # Get metrics summary
        metrics_summary = self.metrics.get_summary(time_window=3600)  # Last hour
        
        stats = {
            # Database cache statistics
            "cache_size": total_cache_entries,
            "cache_sources": source_stats,
            "cache_age_stats": cache_age_stats,
            
            # Provider statistics
            "provider_stats": self.get_provider_stats(),
            "providers_available": [provider.get_provider_name() for provider in self.providers],
            
            # Rate limiting statistics
            "api_calls_this_minute": self.rate_tracker.get_current_request_count(),
            "rate_limit_remaining": self.rate_tracker.max_requests - self.rate_tracker.get_current_request_count(),
            "tokens_available": self.token_bucket.get_available_tokens(),
            "token_bucket_capacity": self.token_bucket.capacity,
            
            # Performance metrics (last hour)
            "metrics_summary": {
                "total_events": metrics_summary.total_events,
                "events_per_minute": metrics_summary.events_per_minute,
                "success_rate": metrics_summary.success_rate,
                "average_response_time": metrics_summary.average_response_time,
                "cache_hit_rate": metrics_summary.cache_hit_rate,
                "rate_limit_events": metrics_summary.rate_limit_events,
                "retry_events": metrics_summary.retry_events,
                "error_events": metrics_summary.error_events
            },
            
            # Configuration information
            "configuration": {
                "rate_limit_max_requests": self.config.rate_limit_max_requests,
                "rate_limit_window_size": self.config.rate_limit_window_size,
                "token_bucket_capacity": self.config.token_bucket_capacity,
                "token_bucket_refill_rate": self.config.token_bucket_refill_rate,
                "max_retries": self.config.max_retries,
                "default_cache_ttl": self.config.default_cache_ttl,
                "cache_max_age_days": current_app.config.get('LYRICS_CACHE_MAX_AGE_DAYS', 30)
            }
        }
        
        return stats

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics for comprehensive monitoring and debugging"""
        return self.metrics.get_detailed_stats()
    
    def reset_metrics(self):
        """Reset all collected metrics"""
        self.metrics.reset_metrics()
        if self.config.log_performance_metrics:
            logger.info("LyricsFetcher metrics have been reset")
    
    def export_configuration(self) -> Dict[str, Any]:
        """Export current configuration as dictionary"""
        return self.config.to_dict()
    
    def update_configuration(self, config: LyricsFetcherConfig):
        """Update configuration and reinitialize components that depend on it"""
        old_config = self.config
        self.config = config
        
        # Reinitialize rate tracker if settings changed
        if (old_config.rate_limit_window_size != config.rate_limit_window_size or 
            old_config.rate_limit_max_requests != config.rate_limit_max_requests):
            self.rate_tracker = RateLimitTracker(
                window_size=config.rate_limit_window_size,
                max_requests=config.rate_limit_max_requests
            )
            if config.log_rate_limit_events:
                logger.info("Rate tracker reinitialized with new configuration")
        
        # Reinitialize token bucket if settings changed
        if (old_config.token_bucket_capacity != config.token_bucket_capacity or 
            old_config.token_bucket_refill_rate != config.token_bucket_refill_rate):
            self.token_bucket = TokenBucket(
                capacity=config.token_bucket_capacity,
                refill_rate=config.token_bucket_refill_rate
            )
            if config.log_rate_limit_events:
                logger.info("Token bucket reinitialized with new configuration")
        
        self.metrics.record_event('configuration_updated')
        if config.log_performance_metrics:
            logger.info("LyricsFetcher configuration updated successfully")
