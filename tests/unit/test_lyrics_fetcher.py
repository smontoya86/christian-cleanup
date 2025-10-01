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
    
    def test_cache_hit(self, sample_lyrics_cache):
        """Test cache hit returns cached lyrics"""
        fetcher = LyricsFetcher()
        lyrics = fetcher._get_from_cache('John Newton', 'Amazing Grace')
        assert lyrics is not None
        assert 'Amazing grace' in lyrics
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        fetcher = LyricsFetcher()
        lyrics = fetcher._get_from_cache('Unknown Artist', 'Unknown Song')
        assert lyrics is None
    
    def test_cache_saves_lyrics(self, db_session):
        """Test caching saves lyrics to database"""
        fetcher = LyricsFetcher()
        
        test_lyrics = "Test lyrics content"
        fetcher._add_to_cache_batch(
            [('Test Artist', 'Test Song', test_lyrics, 'test')]
        )
        
        # Verify it was saved
        from app.models.models import LyricsCache
        cached = LyricsCache.find_cached_lyrics('Test Artist', 'Test Song')
        assert cached is not None
        assert cached.lyrics == test_lyrics


class TestLyricsFetching:
    """Test lyrics fetching functionality"""
    
    @patch('app.utils.lyrics.lyrics_fetcher.LyricsFetcher._fetch_from_lrclib')
    def test_fetch_from_lrclib(self, mock_lrclib):
        """Test fetching from LRCLib"""
        mock_lrclib.return_value = "Test lyrics from LRCLib"
        
        fetcher = LyricsFetcher()
        lyrics = fetcher.fetch_lyrics('Test Song', 'Test Artist')
        
        assert lyrics is not None
        mock_lrclib.assert_called_once()
    
    @patch('app.utils.lyrics.lyrics_fetcher.LyricsFetcher._fetch_from_genius')
    def test_fetch_from_genius(self, mock_genius):
        """Test fetching from Genius"""
        mock_genius.return_value = "Test lyrics from Genius"
        
        fetcher = LyricsFetcher()
        lyrics = fetcher.fetch_lyrics('Test Song', 'Test Artist')
        
        # Should try Genius if LRCLib fails
        assert lyrics is not None
    
    def test_fetch_uses_cache_first(self, sample_lyrics_cache):
        """Test fetch uses cache before API calls"""
        fetcher = LyricsFetcher()
        lyrics = fetcher.fetch_lyrics('Amazing Grace', 'John Newton')
        
        assert lyrics is not None
        assert 'Amazing grace' in lyrics

