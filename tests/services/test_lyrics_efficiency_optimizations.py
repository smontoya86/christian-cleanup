"""
TDD tests for lyrics fetching efficiency optimizations.

This test suite verifies the performance improvements for lyrics fetching:
1. Failed lookup caching (prevents repeated API calls for unavailable lyrics)
2. Request deduplication (skips songs already processed)
3. Batch database operations (reduces DB overhead)
4. Better retry logic (handles rate limits more efficiently)
"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timezone, timedelta
from app.utils.lyrics.lyrics_fetcher import LyricsFetcher, LyricsFetcherConfig
from app.models.models import LyricsCache, Song, AnalysisResult, db


class TestLyricsEfficiencyOptimizations:
    """TDD tests for lyrics fetching efficiency optimizations"""
    
    def test_failed_lookups_are_cached_and_reused(self, app, db_session):
        """
        CRITICAL BUG TEST: Failed lyrics lookups should be cached to prevent repeated API calls.
        
        Current bug: _store_in_cache() skips None values, so failed lookups hit ALL providers EVERY time.
        Expected fix: Cache failed lookups with empty string and 'negative_cache' source.
        """
        # Arrange
        config = LyricsFetcherConfig(log_cache_operations=True, log_api_calls=True)
        fetcher = LyricsFetcher(config=config)
        artist = "Unknown Artist"
        title = "Nonexistent Song"
        
        # Ensure no existing cache
        existing = LyricsCache.find_cached_lyrics(artist, title)
        if existing:
            db.session.delete(existing)
            db.session.commit()
        
        # Mock all providers to return None (failed lookup)
        with patch.object(fetcher, 'providers') as mock_providers:
            mock_provider = MagicMock()
            mock_provider.fetch_lyrics.return_value = None
            mock_provider.get_provider_name.return_value = "TestProvider"
            mock_providers.__iter__ = MagicMock(return_value=iter([mock_provider]))
            mock_providers.__len__ = MagicMock(return_value=1)
            
            # Act: First fetch (should hit API and cache negative result)
            result1 = fetcher.fetch_lyrics(title, artist)
            
            # Assert: Should return None (failed)
            assert result1 is None
            
            # Assert: Should have cached the negative result
            cache_entry = LyricsCache.find_cached_lyrics(artist, title)
            assert cache_entry is not None, "Failed lookup should be cached"
            assert cache_entry.lyrics == "", "Failed lookup should have empty lyrics"
            assert cache_entry.source in ["negative_cache", "failed_lookup"], f"Expected negative_cache, got {cache_entry.source}"
            
            # Act: Second fetch (should use cache, not hit API)
            result2 = fetcher.fetch_lyrics(title, artist)
            
            # Assert: Should still return None but from cache
            assert result2 is None
            
            # Assert: Provider should only be called once (first time)
            assert mock_provider.fetch_lyrics.call_count == 1, "Provider should only be called once, then cached"

    def test_negative_cache_respects_ttl(self, app, db_session):
        """Test that negative cache entries respect TTL and can be retried after expiration"""
        # Arrange
        config = LyricsFetcherConfig(negative_cache_ttl=1)  # 1 second TTL
        fetcher = LyricsFetcher(config=config)
        artist = "Test Artist"
        title = "Test Song"
        
        # Create expired negative cache entry
        old_entry = LyricsCache.cache_lyrics(artist, title, "", "negative_cache")
        old_entry.created_at = datetime.now(timezone.utc) - timedelta(seconds=2)  # Expired
        db.session.commit()
        
        # Mock provider to return success on retry
        with patch.object(fetcher, 'providers') as mock_providers:
            mock_provider = MagicMock()
            mock_provider.fetch_lyrics.return_value = "Found lyrics on retry"
            mock_provider.get_provider_name.return_value = "TestProvider"
            mock_providers.__iter__ = MagicMock(return_value=iter([mock_provider]))
            mock_providers.__len__ = MagicMock(return_value=1)
            
            # Act: Fetch should retry because cache is expired
            result = fetcher.fetch_lyrics(title, artist)
            
            # Assert: Should get lyrics (retry worked)
            assert result == "Found lyrics on retry"
            
            # Assert: Provider was called (cache was bypassed due to expiration)
            assert mock_provider.fetch_lyrics.call_count == 1

    def test_successful_lyrics_still_cached_normally(self, app, db_session):
        """Test that successful lyrics fetching still works and caches properly"""
        # Arrange
        config = LyricsFetcherConfig(log_cache_operations=True)
        fetcher = LyricsFetcher(config=config)
        artist = "Chris Tomlin"
        title = "Amazing Grace"
        lyrics_text = "Amazing grace, how sweet the sound..."
        
        # Ensure no existing cache
        existing = LyricsCache.find_cached_lyrics(artist, title)
        if existing:
            db.session.delete(existing)
            db.session.commit()
        
        # Mock provider to return successful lyrics
        with patch.object(fetcher, 'providers') as mock_providers:
            mock_provider = MagicMock()
            mock_provider.fetch_lyrics.return_value = lyrics_text
            mock_provider.get_provider_name.return_value = "TestProvider"
            mock_providers.__iter__ = MagicMock(return_value=iter([mock_provider]))
            mock_providers.__len__ = MagicMock(return_value=1)
            
            # Act: First fetch
            result1 = fetcher.fetch_lyrics(title, artist)
            
            # Assert: Should return lyrics
            assert result1 == lyrics_text
            
            # Assert: Should be cached properly
            cache_entry = LyricsCache.find_cached_lyrics(artist, title)
            assert cache_entry is not None
            assert cache_entry.lyrics == lyrics_text
            assert cache_entry.source == "TestProvider"
            
            # Act: Second fetch (should use cache)
            result2 = fetcher.fetch_lyrics(title, artist)
            
            # Assert: Should get same lyrics from cache
            assert result2 == lyrics_text
            
            # Assert: Provider should only be called once
            assert mock_provider.fetch_lyrics.call_count == 1

    def test_cache_key_generation_consistency(self, app, db_session):
        """Test that cache keys are generated consistently for the same artist/title combinations"""
        fetcher = LyricsFetcher()
        
        # Test various formatting variations should normalize to same cache key
        test_cases = [
            ("Chris Tomlin", "Amazing Grace"),
            (" Chris Tomlin ", " Amazing Grace "),
            ("CHRIS TOMLIN", "AMAZING GRACE"),
            ("chris tomlin", "amazing grace"),
        ]
        
        cache_keys = []
        for artist, title in test_cases:
            cache_key = fetcher._get_cache_key(title, artist)
            cache_keys.append(cache_key)
        
        # All should normalize to the same cache key
        assert len(set(cache_keys)) == 1, f"Cache keys should be identical: {cache_keys}"

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, app, db_session):
        """Setup and teardown for each test"""
        yield
        # Cleanup any test cache entries
        try:
            test_entries = LyricsCache.query.filter(
                LyricsCache.artist.in_(["Unknown Artist", "Test Artist", "Chris Tomlin"])
            ).all()
            for entry in test_entries:
                db.session.delete(entry)
            db.session.commit()
        except:
            db.session.rollback() 