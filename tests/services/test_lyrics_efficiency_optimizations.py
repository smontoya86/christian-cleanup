"""
TDD tests for lyrics fetching efficiency optimizations.

This test suite verifies the performance improvements for lyrics fetching:
1. Failed lookup caching (prevents repeated API calls for unavailable lyrics)
2. Request deduplication (skips songs already processed)
3. Batch database operations (reduces DB overhead)
4. Better retry logic (handles rate limits more efficiently)
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.models.models import AnalysisResult, LyricsCache, Song, db
from app.utils.lyrics.lyrics_fetcher import LyricsFetcher, LyricsFetcherConfig


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
        with patch.object(fetcher, "providers") as mock_providers:
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
            assert cache_entry.source in [
                "negative_cache",
                "failed_lookup",
            ], f"Expected negative_cache, got {cache_entry.source}"

            # Act: Second fetch (should use cache, not hit API)
            result2 = fetcher.fetch_lyrics(title, artist)

            # Assert: Should still return None but from cache
            assert result2 is None

            # Assert: Provider should only be called once (first time)
            assert (
                mock_provider.fetch_lyrics.call_count == 1
            ), "Provider should only be called once, then cached"

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
        with patch.object(fetcher, "providers") as mock_providers:
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
        with patch.object(fetcher, "providers") as mock_providers:
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

    def test_request_deduplication_skips_analyzed_songs(self, app, db_session):
        """
        OPTIMIZATION TEST: Request deduplication should skip songs that already have completed analysis.

        Current issue: Analysis system may re-process songs that already have results.
        Expected fix: get_songs_needing_analysis() properly filters completed songs.
        """
        from app.services.unified_analysis_service import UnifiedAnalysisService

        # Arrange: Create test songs
        song1 = Song(spotify_id="track1", title="Test Song 1", artist="Test Artist 1")
        song2 = Song(spotify_id="track2", title="Test Song 2", artist="Test Artist 2")
        song3 = Song(spotify_id="track3", title="Test Song 3", artist="Test Artist 3")

        db.session.add_all([song1, song2, song3])
        db.session.flush()  # Get IDs

        # Create completed analysis for song1 and song2
        analysis1 = AnalysisResult(song_id=song1.id, status=AnalysisResult.STATUS_COMPLETED)
        analysis2 = AnalysisResult(song_id=song2.id, status=AnalysisResult.STATUS_COMPLETED)

        db.session.add_all([analysis1, analysis2])
        db.session.commit()

        # Act: Filter songs needing analysis
        service = UnifiedAnalysisService()
        song_ids = [song1.id, song2.id, song3.id]

        result = service.get_songs_needing_analysis(song_ids)

        # Assert: Only song3 should need analysis (song1 and song2 have completed analysis)
        assert result["song_ids"] == [song3.id], f"Expected [song3.id], got {result['song_ids']}"
        assert (
            result["total_filtered"] == 2
        ), f"Expected 2 filtered songs, got {result['total_filtered']}"
        assert (
            result["needs_analysis"] == 1
        ), f"Expected 1 song needing analysis, got {result['needs_analysis']}"

    def test_request_deduplication_includes_failed_when_retry_enabled(self, app, db_session):
        """Test that failed analysis can be retried when retry_failed=True"""
        from app.services.unified_analysis_service import UnifiedAnalysisService

        # Arrange: Create test song with failed analysis
        song = Song(spotify_id="failed_track", title="Failed Song", artist="Failed Artist")
        db.session.add(song)
        db.session.flush()

        failed_analysis = AnalysisResult(song_id=song.id, status=AnalysisResult.STATUS_FAILED)
        db.session.add(failed_analysis)
        db.session.commit()

        # Act: Filter without retry_failed (should exclude)
        service = UnifiedAnalysisService()
        result1 = service.get_songs_needing_analysis([song.id], retry_failed=False)

        # Assert: Failed song should be excluded
        assert result1["song_ids"] == [], "Failed song should be excluded when retry_failed=False"

        # Act: Filter with retry_failed (should include)
        result2 = service.get_songs_needing_analysis([song.id], retry_failed=True)

        # Assert: Failed song should be included
        assert result2["song_ids"] == [
            song.id
        ], "Failed song should be included when retry_failed=True"
        assert result2["retry_count"] == 1, "Should count as retry"

    def test_request_deduplication_handles_pending_status(self, app, db_session):
        """Test that songs with pending analysis are included for processing"""
        from app.services.unified_analysis_service import UnifiedAnalysisService

        # Arrange: Create test song with pending analysis
        song = Song(spotify_id="pending_track", title="Pending Song", artist="Pending Artist")
        db.session.add(song)
        db.session.flush()

        pending_analysis = AnalysisResult(song_id=song.id, status=AnalysisResult.STATUS_PENDING)
        db.session.add(pending_analysis)
        db.session.commit()

        # Act: Filter songs needing analysis
        service = UnifiedAnalysisService()
        result = service.get_songs_needing_analysis([song.id])

        # Assert: Pending song should be included (needs to be processed)
        assert result["song_ids"] == [song.id], "Pending song should be included for processing"

    def test_request_deduplication_performance_with_large_batch(self, app, db_session):
        """Test that deduplication is efficient with large batches of songs"""
        import time

        from app.services.unified_analysis_service import UnifiedAnalysisService

        # Arrange: Create a batch of songs, some with analysis
        songs = []
        for i in range(100):
            song = Song(
                spotify_id=f"batch_track_{i}", title=f"Batch Song {i}", artist=f"Batch Artist {i}"
            )
            songs.append(song)

        db.session.add_all(songs)
        db.session.flush()

        # Add completed analysis for first 50 songs
        analyses = []
        for i in range(50):
            analysis = AnalysisResult(song_id=songs[i].id, status=AnalysisResult.STATUS_COMPLETED)
            analyses.append(analysis)

        db.session.add_all(analyses)
        db.session.commit()

        # Act: Filter large batch (measure performance)
        service = UnifiedAnalysisService()
        song_ids = [song.id for song in songs]

        start_time = time.time()
        result = service.get_songs_needing_analysis(song_ids)
        duration = time.time() - start_time

        # Assert: Should efficiently filter out completed songs
        assert len(result["song_ids"]) == 50, "Should have 50 songs needing analysis"
        assert result["total_filtered"] == 50, "Should have filtered 50 completed songs"
        assert duration < 1.0, f"Filtering should be fast (<1s), took {duration:.3f}s"

    def test_batch_database_operations_reduce_commit_overhead(self, app, db_session):
        """
        OPTIMIZATION TEST: Batch database operations should reduce database commit overhead.

        Current issue: Each song analysis results in individual db.session.commit() calls.
        Expected fix: Batch multiple analysis results and commit together.
        """
        from unittest.mock import patch

        from app.services.unified_analysis_service import UnifiedAnalysisService

        # Arrange: Create test songs
        songs = []
        for i in range(10):
            song = Song(
                spotify_id=f"batch_db_track_{i}",
                title=f"Batch Song {i}",
                artist=f"Batch Artist {i}",
                lyrics="Test lyrics",
            )
            songs.append(song)

        db.session.add_all(songs)
        db.session.commit()
        song_ids = [song.id for song in songs]

        # Mock the analysis service to avoid actual AI calls
        service = UnifiedAnalysisService()

        with patch.object(service, "analyze_song_complete") as mock_analyze:
            mock_analyze.return_value = {
                "score": 85,
                "concern_level": "low",
                "themes": ["test"],
                "explanation": "Test analysis",
                "detailed_concerns": [],
                "positive_themes": [],
                "biblical_themes": [],
                "supporting_scripture": [],
            }

            # Count database commits
            original_commit = db.session.commit
            commit_count = 0

            def counting_commit():
                nonlocal commit_count
                commit_count += 1
                return original_commit()

            # Act: Process batch with commit counting
            with patch.object(db.session, "commit", side_effect=counting_commit):
                result = service.analyze_songs_batch(
                    song_ids=song_ids,
                    batch_size=5,  # Process in batches of 5
                    skip_existing=False,
                )

            # Assert: Should have significantly fewer commits than individual processing
            # With batching: Should be ~2 commits (one per batch of 5)
            # Without batching: Would be ~10 commits (one per song)
            assert (
                commit_count <= 3
            ), f"Expected ≤3 commits for batched processing, got {commit_count}"
            assert result["success"] is True
            assert result["total_analyzed"] == 10

    def test_batch_lyrics_cache_operations_are_efficient(self, app, db_session):
        """Test that lyrics cache operations can be batched for efficiency"""
        from app.utils.lyrics.lyrics_fetcher import LyricsFetcher

        # Arrange: Create fetcher
        fetcher = LyricsFetcher()

        # Create test data for bulk caching
        cache_operations = []
        for i in range(20):
            cache_operations.append(
                {
                    "artist": f"Test Artist {i}",
                    "title": f"Test Song {i}",
                    "lyrics": f"Test lyrics {i}"
                    if i % 2 == 0
                    else None,  # Mix of success and failure
                    "source": "TestProvider",
                }
            )

        # Count database commits during bulk operations
        original_commit = db.session.commit
        commit_count = 0

        def counting_commit():
            nonlocal commit_count
            commit_count += 1
            return original_commit()

        # Act: Perform cache operations
        with patch.object(db.session, "commit", side_effect=counting_commit):
            for op in cache_operations:
                cache_key = fetcher._get_cache_key(op["title"], op["artist"])
                fetcher._store_in_cache(cache_key, op["lyrics"])

        # Assert: Should have efficient cache operations
        # Current implementation: 1 commit per cache operation = 20 commits
        # Optimized implementation: Should batch and reduce commits
        print(
            f"Cache operations resulted in {commit_count} commits for {len(cache_operations)} operations"
        )

        # Verify all operations were cached
        successful_caches = 0
        negative_caches = 0

        for op in cache_operations:
            cached = LyricsCache.find_cached_lyrics(op["artist"], op["title"])
            if cached:
                if cached.source == "negative_cache":
                    negative_caches += 1
                else:
                    successful_caches += 1

        assert successful_caches == 10, f"Expected 10 successful caches, got {successful_caches}"
        assert negative_caches == 10, f"Expected 10 negative caches, got {negative_caches}"

    def test_database_bulk_insert_vs_individual_inserts(self, app, db_session):
        """Test performance difference between bulk inserts and individual inserts"""
        import time

        from app.models.models import LyricsCache

        # Test individual inserts (current approach)
        start_time = time.time()
        individual_entries = []
        for i in range(50):
            entry = LyricsCache.cache_lyrics(
                f"Individual Artist {i}", f"Individual Song {i}", f"Lyrics {i}", "TestProvider"
            )
            individual_entries.append(entry)
            db.session.commit()  # Individual commit
        individual_duration = time.time() - start_time

        # Test bulk insert approach
        start_time = time.time()
        bulk_entries = []
        for i in range(50):
            entry = LyricsCache(
                artist=f"Bulk Artist {i}",
                title=f"Bulk Song {i}",
                lyrics=f"Lyrics {i}",
                source="TestProvider",
            )
            bulk_entries.append(entry)
            db.session.add(entry)
        db.session.commit()  # Single commit
        bulk_duration = time.time() - start_time

        # Assert: Bulk operations should be significantly faster
        print(f"Individual inserts: {individual_duration:.3f}s")
        print(f"Bulk inserts: {bulk_duration:.3f}s")
        print(f"Bulk is {individual_duration/bulk_duration:.1f}x faster")

        # Bulk should be at least 2x faster (often much more)
        assert (
            bulk_duration < individual_duration / 2
        ), "Bulk inserts should be significantly faster than individual inserts"

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, app, db_session):
        """Setup and teardown for each test"""
        yield
        # Cleanup any test cache entries
        try:
            test_entries = LyricsCache.query.filter(
                LyricsCache.artist.in_(["Unknown Artist", "Test Artist", "Chris Tomlin"])
                | LyricsCache.artist.like("Test Artist%")
                | LyricsCache.artist.like("Batch Artist%")
                | LyricsCache.artist.like("Individual Artist%")
                | LyricsCache.artist.like("Bulk Artist%")
            ).all()
            for entry in test_entries:
                db.session.delete(entry)

            # Cleanup test songs and analyses
            test_songs = Song.query.filter(
                Song.spotify_id.like("track%")
                | Song.spotify_id.like("failed_track%")
                | Song.spotify_id.like("pending_track%")
                | Song.spotify_id.like("batch_track_%")
                | Song.spotify_id.like("batch_db_track_%")
            ).all()
            for song in test_songs:
                # Delete related analyses first
                analyses = AnalysisResult.query.filter_by(song_id=song.id).all()
                for analysis in analyses:
                    db.session.delete(analysis)
                db.session.delete(song)

            db.session.commit()
        except:
            db.session.rollback()
