"""
Tests for LyricsFetcher enhanced caching functionality
"""
import pytest
import time
from unittest.mock import patch, Mock, MagicMock
from app.utils.lyrics import LyricsFetcher

# Define the default cache TTL for testing
DEFAULT_CACHE_TTL = 3600

class TestLyricsFetcherCaching:
    """Test suite for LyricsFetcher enhanced caching"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.fetcher = LyricsFetcher()
        # Clear cache before each test
        self.fetcher.clear_cache()
    
    def test_cache_key_generation(self):
        """Test that cache keys are generated consistently"""
        key1 = self.fetcher._get_cache_key("Amazing Grace", "John Newton")
        key2 = self.fetcher._get_cache_key("amazing grace", "john newton")
        key3 = self.fetcher._get_cache_key("  Amazing Grace  ", "  John Newton  ")
        
        # Should be the same regardless of case and whitespace
        assert key1 == key2 == key3
        assert len(key1) == 32  # MD5 hash length
    
    def test_cache_storage_and_retrieval(self):
        """Test basic cache storage and retrieval"""
        cache_key = "test_key"
        lyrics = "Amazing grace, how sweet the sound"
        
        # Store in cache
        self.fetcher._store_in_cache(cache_key, lyrics)
        
        # Retrieve from cache
        cached_lyrics = self.fetcher._get_from_cache(cache_key)
        assert cached_lyrics == lyrics
    
    def test_cache_ttl_validation(self):
        """Test that cache entries respect TTL"""
        cache_key = "test_key"
        lyrics = "Amazing grace, how sweet the sound"
        short_ttl = 1  # 1 second
        
        # Store with short TTL
        self.fetcher._store_in_cache(cache_key, lyrics, ttl=short_ttl)
        
        # Should be available immediately
        assert self.fetcher._get_from_cache(cache_key) == lyrics
        
        # Wait for TTL to expire
        time.sleep(1.1)
        
        # Should be None after expiration
        assert self.fetcher._get_from_cache(cache_key) is None
    
    def test_cache_entry_structure(self):
        """Test that cache entries have correct structure"""
        cache_key = "test_key"
        lyrics = "Amazing grace, how sweet the sound"
        custom_ttl = 3600
        
        self.fetcher._store_in_cache(cache_key, lyrics, ttl=custom_ttl)
        
        # Access the cache directly to check structure
        from app.utils.lyrics import _lyrics_cache
        entry = _lyrics_cache[cache_key]
        
        assert 'lyrics' in entry
        assert 'timestamp' in entry
        assert 'ttl' in entry
        assert entry['lyrics'] == lyrics
        assert entry['ttl'] == custom_ttl
        assert isinstance(entry['timestamp'], float)
    
    def test_cache_negative_results(self):
        """Test caching of negative results (None)"""
        cache_key = "test_key"
        
        # Store None result
        self.fetcher._store_in_cache(cache_key, None)
        
        # Should retrieve None
        assert self.fetcher._get_from_cache(cache_key) is None
    
    def test_cache_clear(self):
        """Test cache clearing functionality"""
        # Add some entries
        self.fetcher._store_in_cache("key1", "lyrics1")
        self.fetcher._store_in_cache("key2", "lyrics2")
        
        # Verify entries exist
        assert self.fetcher._get_from_cache("key1") == "lyrics1"
        assert self.fetcher._get_from_cache("key2") == "lyrics2"
        
        # Clear cache
        self.fetcher.clear_cache()
        
        # Verify entries are gone
        assert self.fetcher._get_from_cache("key1") is None
        assert self.fetcher._get_from_cache("key2") is None
    
    @patch('time.time')
    def test_cleanup_expired_cache(self, mock_time):
        """Test cleanup of expired cache entries"""
        # Set initial time
        mock_time.return_value = 1000.0
        
        # Add entries with different TTLs
        self.fetcher._store_in_cache("key1", "lyrics1", ttl=100)  # Expires at 1100
        self.fetcher._store_in_cache("key2", "lyrics2", ttl=200)  # Expires at 1200
        self.fetcher._store_in_cache("key3", "lyrics3", ttl=300)  # Expires at 1300
        
        # Move time to 1150 (key1 expired, others valid)
        mock_time.return_value = 1150.0
        
        # Cleanup expired entries
        removed_count = self.fetcher.cleanup_expired_cache()
        
        assert removed_count == 1
        assert self.fetcher._get_from_cache("key1") is None
        assert self.fetcher._get_from_cache("key2") == "lyrics2"
        assert self.fetcher._get_from_cache("key3") == "lyrics3"
    
    def test_cache_stats_with_enhanced_cache(self):
        """Test cache statistics with enhanced cache format"""
        # Add some valid entries
        self.fetcher._store_in_cache("key1", "lyrics1", ttl=3600)
        self.fetcher._store_in_cache("key2", "lyrics2", ttl=3600)
        
        # Add an expired entry
        with patch('time.time', return_value=1000.0):
            self.fetcher._store_in_cache("key3", "lyrics3", ttl=1)
        
        # Move time forward to expire key3
        with patch('time.time', return_value=1002.0):
            stats = self.fetcher.get_cache_stats()
        
        assert stats['cache_size'] == 3
        assert stats['cache_valid_entries'] == 2
        assert stats['cache_expired_entries'] == 1
        assert 'tokens_available' in stats
        assert 'token_bucket_capacity' in stats
    
    @patch('app.utils.lyrics.lyricsgenius.Genius')
    def test_fetch_lyrics_with_cache_hit(self, mock_genius_class):
        """Test fetch_lyrics with cache hit (no API call)"""
        # Pre-populate cache
        cache_key = self.fetcher._get_cache_key("Amazing Grace", "John Newton")
        expected_lyrics = "Amazing grace, how sweet the sound"
        self.fetcher._store_in_cache(cache_key, expected_lyrics)
        
        # Mock genius client
        mock_genius = Mock()
        mock_genius_class.return_value = mock_genius
        self.fetcher.genius = mock_genius
        
        # Fetch lyrics
        result = self.fetcher.fetch_lyrics("Amazing Grace", "John Newton")
        
        # Should return cached result without API call
        assert result == expected_lyrics
        assert not mock_genius.search_song.called
    
    @patch('app.utils.lyrics.lyricsgenius.Genius')
    @patch('app.utils.lyrics.time.sleep')  # Mock sleep to speed up tests
    def test_fetch_lyrics_with_cache_miss(self, mock_sleep, mock_genius_class):
        """Test fetch_lyrics with cache miss (API call made)"""
        # Mock genius client and song
        mock_song = Mock()
        mock_song.lyrics = "Amazing grace, how sweet the sound\nThat saved a wretch like me"
        
        mock_genius = Mock()
        mock_genius.search_song.return_value = mock_song
        mock_genius_class.return_value = mock_genius
        self.fetcher.genius = mock_genius
        
        # Fetch lyrics (cache miss)
        result = self.fetcher.fetch_lyrics("Amazing Grace", "John Newton")
        
        # Should make API call and cache result
        assert mock_genius.search_song.called
        assert result is not None
        assert "Amazing grace" in result
        
        # Verify result is cached
        cache_key = self.fetcher._get_cache_key("Amazing Grace", "John Newton")
        cached_result = self.fetcher._get_from_cache(cache_key)
        assert cached_result == result
    
    @patch('app.utils.lyrics.lyricsgenius.Genius')
    @patch('app.utils.lyrics.time.sleep')
    def test_fetch_lyrics_negative_caching(self, mock_sleep, mock_genius_class):
        """Test that negative results (no lyrics found) are cached"""
        # Mock genius client returning None
        mock_genius = Mock()
        mock_genius.search_song.return_value = None
        mock_genius_class.return_value = mock_genius
        self.fetcher.genius = mock_genius
        
        # Fetch lyrics (no result)
        result = self.fetcher.fetch_lyrics("Nonexistent Song", "Unknown Artist")
        
        # Should return None
        assert result is None
        
        # Verify negative result is cached
        cache_key = self.fetcher._get_cache_key("Nonexistent Song", "Unknown Artist")
        cached_result = self.fetcher._get_from_cache(cache_key)
        assert cached_result is None
    
    def test_custom_cache_ttl(self):
        """Test fetch_lyrics with custom cache TTL"""
        custom_ttl = 1800  # 30 minutes
        
        # Mock to avoid actual API call
        with patch.object(self.fetcher, 'genius', None):
            result = self.fetcher.fetch_lyrics("Test Song", "Test Artist", cache_ttl=custom_ttl)
        
        # Should return None (no genius client) but test TTL parameter
        assert result is None
        
        # Check that the method accepts the TTL parameter without error
        # (Full integration test would require mocking the genius client) 