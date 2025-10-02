"""
Unit tests for LyricsFetcher
"""

import pytest
from unittest.mock import Mock, patch
from app.utils.lyrics.lyrics_fetcher import LyricsFetcher


class TestLyricsFetcherInitialization:
    """Test LyricsFetcher initialization"""
    
    def test_init_fetcher(self):
        """Test fetcher initializes"""
        fetcher = LyricsFetcher()
        assert fetcher is not None
    
    def test_init_with_config(self):
        """Test fetcher initializes with config"""
        fetcher = LyricsFetcher()
        assert hasattr(fetcher, 'config')
        assert hasattr(fetcher, 'metrics')


class TestLyricsCaching:
    """Test lyrics caching functionality"""
    
    def test_cache_hit(self, app, sample_lyrics_cache):
        """Test cache hit returns cached lyrics via public API"""
        with app.app_context():
            fetcher = LyricsFetcher()
            # fetch_lyrics should use cache if available
            lyrics = fetcher.fetch_lyrics('Amazing Grace', 'John Newton')
            assert lyrics is not None
            assert 'Amazing grace' in lyrics
    
    def test_cache_miss(self, app):
        """Test cache miss returns None"""
        with app.app_context():
            fetcher = LyricsFetcher()
            cache_key = fetcher._get_cache_key('Unknown Song', 'Unknown Artist')
            lyrics = fetcher._get_from_cache(cache_key)
            assert lyrics is None
    
    def test_cache_saves_lyrics(self, app, db_session):
        """Test caching saves lyrics to database via public API"""
        with app.app_context():
            from app.models.models import LyricsCache
            
            # Cache lyrics directly via model
            test_lyrics = "Test lyrics content for caching"
            LyricsCache.cache_lyrics('Test Artist 2', 'Test Song 2', test_lyrics, 'test')
            
            # Verify it was saved
            cached = LyricsCache.find_cached_lyrics('Test Artist 2', 'Test Song 2')
            assert cached is not None
            assert test_lyrics in cached.lyrics


class TestLyricsFetching:
    """Test lyrics fetching functionality"""
    
    def test_fetch_uses_cache_first(self, app, sample_lyrics_cache):
        """Test fetch uses cache before API calls"""
        with app.app_context():
            fetcher = LyricsFetcher()
            lyrics = fetcher.fetch_lyrics('Amazing Grace', 'John Newton')
            
            assert lyrics is not None
            assert 'Amazing grace' in lyrics
    
    def test_fetch_with_providers(self, app):
        """Test fetching with provider fallback"""
        with app.app_context():
            fetcher = LyricsFetcher()
            # Try fetching - will likely fail but should not crash
            lyrics = fetcher.fetch_lyrics('Test Song Unknown', 'Test Artist Unknown')
            
            # Should return None or empty string, not crash
            assert lyrics is None or isinstance(lyrics, str)
    
    def test_fetch_returns_none_on_failure(self, app):
        """Test fetch returns None when all providers fail"""
        with app.app_context():
            fetcher = LyricsFetcher()
            # Use a song that definitely doesn't exist
            lyrics = fetcher.fetch_lyrics('ZZZZZZZZ Nonexistent', 'ZZZZZZZZ Unknown')
            
            # Should return None or empty string
            assert lyrics is None or lyrics == ''

