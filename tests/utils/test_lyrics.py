"""
Tests for LyricsFetcher with enhanced rate limiting and caching functionality
"""
import pytest
import time
from unittest.mock import patch, Mock, MagicMock
from app.utils.lyrics import LyricsFetcher

# Define the default cache TTL for testing
DEFAULT_CACHE_TTL = 3600


class MockGeniusSong:
    """Mock Genius song object for testing"""
    def __init__(self, lyrics):
        self.lyrics = lyrics


class TestLyricsFetcher:
    """Test suite for LyricsFetcher"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.fetcher = LyricsFetcher()
        # Clear cache before each test
        self.fetcher.clear_cache()
    
    def test_initialization_with_token(self):
        """Test LyricsFetcher initialization with token"""
        with patch('app.utils.lyrics.lyricsgenius.Genius') as mock_genius:
            mock_genius_instance = Mock()
            mock_genius.return_value = mock_genius_instance
            
            fetcher = LyricsFetcher(genius_token="test_token")
            
            # Verify Genius client was initialized with correct parameters
            mock_genius.assert_called_once_with(
                "test_token",
                timeout=5,
                sleep_time=0.1,
                retries=2,
                remove_section_headers=True,
                skip_non_songs=True,
                excluded_terms=["(Remix)", "(Live)", "(Acoustic)", "(Demo)"],
                verbose=False
            )
            assert fetcher.genius == mock_genius_instance
    
    def test_initialization_without_token(self):
        """Test LyricsFetcher initialization without token"""
        with patch.dict('os.environ', {}, clear=True):
            fetcher = LyricsFetcher()
            assert fetcher.genius is None
    
    def test_initialization_from_environment(self):
        """Test LyricsFetcher initialization from environment variable"""
        with patch.dict('os.environ', {'GENIUS_ACCESS_TOKEN': 'env_token'}):
            with patch('app.utils.lyrics.lyricsgenius.Genius') as mock_genius:
                mock_genius_instance = Mock()
                mock_genius.return_value = mock_genius_instance
                
                fetcher = LyricsFetcher()
                
                mock_genius.assert_called_once()
                assert fetcher.genius == mock_genius_instance
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        key1 = self.fetcher._get_cache_key("Amazing Grace", "John Newton")
        key2 = self.fetcher._get_cache_key("amazing grace", "john newton")
        key3 = self.fetcher._get_cache_key("  Amazing Grace  ", "  John Newton  ")
        
        # Should be the same regardless of case and whitespace
        assert key1 == key2 == key3
        assert len(key1) == 32  # MD5 hash length
    
    def test_title_cleaning(self):
        """Test title cleaning functionality"""
        assert self.fetcher._clean_title("Song Title (Remaster)") == "Song Title"
        assert self.fetcher._clean_title("Song Title [Live Version]") == "Song Title"
        assert self.fetcher._clean_title("Song Title - Remix Version") == "Song Title"
        assert self.fetcher._clean_title("  Song Title  ") == "Song Title"
    
    def test_artist_cleaning(self):
        """Test artist cleaning functionality"""
        assert self.fetcher._clean_artist("Artist feat. Other Artist") == "Artist"
        assert self.fetcher._clean_artist("Artist featuring Other") == "Artist"
        assert self.fetcher._clean_artist("Artist ft. Other") == "Artist"
        assert self.fetcher._clean_artist("Artist & Other") == "Artist"
        assert self.fetcher._clean_artist("  Artist  ") == "Artist"
    
    def test_lyrics_cleaning(self):
        """Test lyrics cleaning functionality"""
        raw_lyrics = "[Verse 1]\nLine 1\n[Chorus]\nLine 2\n\n\nLine 3\n123Embed"
        expected = "Line 1\n\nLine 2\n\nLine 3"
        
        cleaned = self.fetcher._clean_lyrics(raw_lyrics)
        assert cleaned == expected
    
    @patch('app.utils.lyrics.time.sleep')  # Mock sleep to speed up tests
    def test_fetch_lyrics_success(self, mock_sleep):
        """Test successful lyrics fetching"""
        # Mock genius client and song
        mock_song = MockGeniusSong("Amazing grace, how sweet the sound")
        mock_genius = Mock()
        mock_genius.search_song.return_value = mock_song
        self.fetcher.genius = mock_genius
        
        result = self.fetcher.fetch_lyrics("Amazing Grace", "John Newton")
        
        # Verify API call was made with correct parameters
        mock_genius.search_song.assert_called_once_with(
            title="Amazing Grace",
            artist="John Newton",
            get_full_info=False
        )
        assert result == "Amazing grace, how sweet the sound"
    
    @patch('app.utils.lyrics.time.sleep')
    def test_fetch_lyrics_not_found(self, mock_sleep):
        """Test lyrics fetching when song not found"""
        mock_genius = Mock()
        mock_genius.search_song.return_value = None
        self.fetcher.genius = mock_genius
        
        result = self.fetcher.fetch_lyrics("Unknown Song", "Unknown Artist")
        
        assert result is None
        mock_genius.search_song.assert_called_once()
    
    @patch('app.utils.lyrics.time.sleep')
    def test_fetch_lyrics_empty_lyrics(self, mock_sleep):
        """Test lyrics fetching when song has empty lyrics"""
        mock_song = MockGeniusSong("")
        mock_genius = Mock()
        mock_genius.search_song.return_value = mock_song
        self.fetcher.genius = mock_genius
        
        result = self.fetcher.fetch_lyrics("Empty Song", "Test Artist")
        
        assert result is None
    
    def test_fetch_lyrics_no_genius_client(self):
        """Test lyrics fetching without Genius client"""
        self.fetcher.genius = None
        
        result = self.fetcher.fetch_lyrics("Some Song", "Some Artist")
        
        assert result is None
    
    @patch('app.utils.lyrics.time.sleep')
    def test_fetch_lyrics_with_caching(self, mock_sleep):
        """Test that lyrics are cached after fetching"""
        # Mock genius client and song
        mock_song = MockGeniusSong("Test lyrics content")
        mock_genius = Mock()
        mock_genius.search_song.return_value = mock_song
        self.fetcher.genius = mock_genius
        
        # First call should hit API
        result1 = self.fetcher.fetch_lyrics("Test Song", "Test Artist")
        assert result1 == "Test lyrics content"
        assert mock_genius.search_song.call_count == 1
        
        # Second call should use cache
        result2 = self.fetcher.fetch_lyrics("Test Song", "Test Artist")
        assert result2 == "Test lyrics content"
        assert mock_genius.search_song.call_count == 1  # No additional API call
    
    @patch('app.utils.lyrics.time.sleep')
    def test_fetch_lyrics_exception_handling(self, mock_sleep):
        """Test exception handling during lyrics fetching"""
        mock_genius = Mock()
        mock_genius.search_song.side_effect = Exception("API Error")
        self.fetcher.genius = mock_genius
        
        result = self.fetcher.fetch_lyrics("Error Song", "Test Artist")
        
        assert result is None
    
    def test_cache_stats(self):
        """Test cache statistics"""
        # Add some entries to cache
        self.fetcher._store_in_cache("key1", "lyrics1")
        self.fetcher._store_in_cache("key2", None)  # Negative result
        
        stats = self.fetcher.get_cache_stats()
        
        assert 'cache_size' in stats
        assert 'cache_valid_entries' in stats
        assert 'cache_expired_entries' in stats
        assert 'api_calls_this_minute' in stats
        assert 'rate_limit_remaining' in stats
        assert 'tokens_available' in stats
        assert 'token_bucket_capacity' in stats
        
        assert stats['cache_size'] == 2
        assert stats['cache_valid_entries'] == 2
        assert stats['cache_expired_entries'] == 0
    
    def test_rate_limiting_integration(self):
        """Test that rate limiting components are properly initialized"""
        assert hasattr(self.fetcher, 'rate_tracker')
        assert hasattr(self.fetcher, 'token_bucket')
        assert self.fetcher.rate_tracker.max_requests == 60
        assert self.fetcher.token_bucket.capacity == 10
    
    def test_fetch_with_retry_success(self):
        """Test fetch_with_retry with successful response"""
        with patch('app.utils.lyrics.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = self.fetcher.fetch_with_retry("http://test.com")
            
            assert result == mock_response
            mock_get.assert_called_once()
    
    def test_fetch_with_retry_rate_limit(self):
        """Test fetch_with_retry with rate limiting"""
        with patch('app.utils.lyrics.requests.get') as mock_get:
            with patch('app.utils.lyrics.time.sleep') as mock_sleep:
                # First call returns 429, second call succeeds
                mock_response_429 = Mock()
                mock_response_429.status_code = 429
                mock_response_429.headers = {'Retry-After': '1'}
                
                mock_response_200 = Mock()
                mock_response_200.status_code = 200
                
                mock_get.side_effect = [mock_response_429, mock_response_200]
                
                result = self.fetcher.fetch_with_retry("http://test.com", max_retries=2)
                
                assert result == mock_response_200
                assert mock_get.call_count == 2
                mock_sleep.assert_called_once()
    
    def test_is_rate_limited_detection(self):
        """Test rate limit detection"""
        # Test 429 status code
        response_429 = Mock()
        response_429.status_code = 429
        assert self.fetcher.is_rate_limited(response_429) is True
        
        # Test rate limit header
        response_header = Mock()
        response_header.status_code = 200
        response_header.headers = {'X-RateLimit-Remaining': '0'}
        assert self.fetcher.is_rate_limited(response_header) is True
        
        # Test normal response
        response_ok = Mock()
        response_ok.status_code = 200
        response_ok.headers = {'X-RateLimit-Remaining': '10'}
        assert self.fetcher.is_rate_limited(response_ok) is False
    
    def test_approaching_rate_limit(self):
        """Test approaching rate limit detection"""
        # Fill tracker to 80% (48 out of 60 requests)
        for _ in range(48):
            self.fetcher.rate_tracker.record_request()
        
        assert self.fetcher.is_approaching_rate_limit() is True
        
        # Reset and test below threshold
        self.fetcher.rate_tracker.reset()
        for _ in range(30):
            self.fetcher.rate_tracker.record_request()
        
        assert self.fetcher.is_approaching_rate_limit() is False
    
    def test_cache_ttl_functionality(self):
        """Test cache TTL functionality"""
        # Store with short TTL
        self.fetcher._store_in_cache("test_key", "test_lyrics", ttl=1)
        
        # Should be available immediately
        assert self.fetcher._get_from_cache("test_key") == "test_lyrics"
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be None after expiration
        assert self.fetcher._get_from_cache("test_key") is None
    
    def test_cache_cleanup(self):
        """Test cache cleanup functionality"""
        # Add entries with different TTLs
        with patch('app.utils.lyrics.time.time', return_value=1000.0):
            self.fetcher._store_in_cache("key1", "lyrics1", ttl=100)
            self.fetcher._store_in_cache("key2", "lyrics2", ttl=200)
        
        # Move time forward to expire key1 but not key2
        with patch('app.utils.lyrics.time.time', return_value=1150.0):
            removed_count = self.fetcher.cleanup_expired_cache()
            # Also check key2 with the same time context
            key2_result = self.fetcher._get_from_cache("key2")
        
        assert removed_count == 1
        assert self.fetcher._get_from_cache("key1") is None
        assert key2_result == "lyrics2"
    
    def test_input_validation(self):
        """Test input validation for fetch_lyrics"""
        # Test with None values - should handle gracefully
        result = self.fetcher.fetch_lyrics(None, "Artist")
        assert result is None
        
        result = self.fetcher.fetch_lyrics("Title", None)
        assert result is None
        
        result = self.fetcher.fetch_lyrics("", "")
        assert result is None
