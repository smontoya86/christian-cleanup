"""
Database Performance Baseline Tests
Direct database query performance testing without API dependencies
"""

import time
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models import AnalysisResult, Playlist, PlaylistSong, Song, User


class TestDatabaseQueryPerformance:
    """Test direct database query performance"""

    @pytest.fixture(autouse=True)
    def setup_test_data(self, app):
        """Setup test data for performance testing"""
        with app.app_context():
            # Create test user
            test_user = User(
                spotify_id="perf_test_user",
                email="perf@test.com",
                display_name="Performance Test User",
                access_token="test_access_token",
                refresh_token="test_refresh_token",
                token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            db.session.add(test_user)
            db.session.flush()

            # Store user ID instead of object to avoid DetachedInstanceError
            self.test_user_id = test_user.id

            # Create test songs
            self.test_songs = []
            for i in range(100):
                song = Song(
                    spotify_id=f"perf_song_{i}",
                    title=f"Performance Test Song {i}",
                    artist=f"Test Artist {i % 10}",  # 10 different artists
                    album=f"Test Album {i % 20}",  # 20 different albums
                    duration_ms=180000 + (i * 1000),
                    explicit=i % 5 == 0,  # 20% explicit
                )
                db.session.add(song)
                self.test_songs.append(song)

            db.session.flush()

            # Create analysis results for songs
            for i, song in enumerate(self.test_songs):
                if i % 2 == 0:  # 50% of songs have analysis
                    analysis = AnalysisResult(
                        song_id=song.id,
                        status="completed",
                        score=85 - (i % 30),
                        concern_level="low" if i % 3 == 0 else "medium",
                        explanation=f"Test analysis for song {i}",
                        analyzed_at=datetime.now(timezone.utc),
                    )
                    db.session.add(analysis)

            # Create test playlists - use test_user.id before commit
            self.test_playlist_ids = []
            for i in range(25):
                playlist = Playlist(
                    spotify_id=f"perf_playlist_{i}",
                    name=f"Performance Test Playlist {i}",
                    owner_id=test_user.id,
                )
                db.session.add(playlist)
                db.session.flush()
                self.test_playlist_ids.append(playlist.id)

            # Add songs to playlists - access IDs before object becomes detached
            song_ids = [song.id for song in self.test_songs]

            for playlist_idx, playlist_id in enumerate(self.test_playlist_ids):
                songs_per_playlist = 20 + (playlist_idx % 10)
                for song_idx in range(songs_per_playlist):
                    song_id = song_ids[song_idx % len(song_ids)]
                    playlist_song = PlaylistSong(
                        playlist_id=playlist_id, song_id=song_id, track_position=song_idx + 1
                    )
                    db.session.add(playlist_song)

            db.session.commit()

    def test_song_count_query_performance(self, app):
        """Test basic song count query performance"""
        with app.app_context():
            start_time = time.time()
            count = db.session.query(Song).count()
            end_time = time.time()

            query_time_ms = (end_time - start_time) * 1000

            assert count >= 100
            assert (
                query_time_ms < 50
            ), f"Song count query took {query_time_ms:.1f}ms, target was 50ms"
            print(f"Song count query: {query_time_ms:.1f}ms ({count:,} songs)")

    def test_analysis_results_with_songs_query(self, app):
        """Test the slow query from Progress API - analysis results with songs"""
        with app.app_context():
            start_time = time.time()

            # This is the actual slow query from the Progress API
            recent_results = (
                db.session.query(AnalysisResult, Song)
                .join(Song)
                .filter(AnalysisResult.status == "completed")
                .order_by(AnalysisResult.analyzed_at.desc())
                .limit(5)
                .all()
            )

            end_time = time.time()
            query_time_ms = (end_time - start_time) * 1000

            assert len(recent_results) <= 5
            assert (
                query_time_ms < 100
            ), f"Analysis results join query took {query_time_ms:.1f}ms, target was 100ms"
            print(
                f"Analysis results join query: {query_time_ms:.1f}ms ({len(recent_results)} results)"
            )

    def test_playlist_songs_join_query(self, app):
        """Test playlist songs join query performance"""
        with app.app_context():
            # Get first playlist ID from our stored IDs
            playlist_id = self.test_playlist_ids[0]

            start_time = time.time()

            songs = (
                db.session.query(Song, AnalysisResult)
                .join(PlaylistSong)
                .outerjoin(AnalysisResult)
                .filter(PlaylistSong.playlist_id == playlist_id)
                .order_by(PlaylistSong.track_position)
                .limit(25)
                .all()
            )

            end_time = time.time()
            query_time_ms = (end_time - start_time) * 1000

            assert len(songs) <= 25
            assert (
                query_time_ms < 50
            ), f"Playlist songs join took {query_time_ms:.1f}ms, target was 50ms"
            print(f"Playlist songs join query: {query_time_ms:.1f}ms ({len(songs)} songs)")

    def test_user_playlists_query(self, app):
        """Test user playlists query for dashboard"""
        with app.app_context():
            start_time = time.time()

            playlists = (
                Playlist.query.filter_by(owner_id=self.test_user_id)
                .order_by(Playlist.updated_at.desc())
                .limit(25)
                .all()
            )

            end_time = time.time()
            query_time_ms = (end_time - start_time) * 1000

            assert len(playlists) <= 25
            assert (
                query_time_ms < 30
            ), f"User playlists query took {query_time_ms:.1f}ms, target was 30ms"
            print(f"User playlists query: {query_time_ms:.1f}ms ({len(playlists)} playlists)")

    def test_analysis_status_aggregation(self, app):
        """Test analysis status aggregation query"""
        with app.app_context():
            start_time = time.time()

            # Simulate the aggregation query from Progress API
            total_songs = db.session.query(Song).count()
            completed_analyses = (
                db.session.query(AnalysisResult)
                .filter(AnalysisResult.status == "completed")
                .count()
            )
            pending_analyses = total_songs - completed_analyses

            end_time = time.time()
            query_time_ms = (end_time - start_time) * 1000

            assert total_songs > 0
            assert completed_analyses >= 0
            assert pending_analyses >= 0
            assert (
                query_time_ms < 100
            ), f"Analysis aggregation took {query_time_ms:.1f}ms, target was 100ms"
            print(
                f"Analysis aggregation: {query_time_ms:.1f}ms (Total: {total_songs}, Completed: {completed_analyses})"
            )

    def test_complex_playlist_analysis_query(self, app):
        """Test complex query combining playlists, songs, and analysis results"""
        with app.app_context():
            # Get first playlist ID from our stored IDs
            playlist_id = self.test_playlist_ids[0]

            start_time = time.time()

            # Simplified but realistic query that's commonly used in the app
            # Get playlist with its song count and analysis summary
            playlist_info = db.session.query(Playlist).filter(Playlist.id == playlist_id).first()

            if playlist_info:
                # Count songs in this playlist
                song_count = (
                    db.session.query(PlaylistSong)
                    .filter(PlaylistSong.playlist_id == playlist_id)
                    .count()
                )

                # Count completed analyses for songs in this playlist
                analyzed_count = (
                    db.session.query(AnalysisResult)
                    .join(Song)
                    .join(PlaylistSong)
                    .filter(PlaylistSong.playlist_id == playlist_id)
                    .filter(AnalysisResult.status == "completed")
                    .count()
                )

            end_time = time.time()
            query_time_ms = (end_time - start_time) * 1000

            assert playlist_info is not None
            assert (
                query_time_ms < 150
            ), f"Complex playlist query took {query_time_ms:.1f}ms, target was 150ms"
            print(f"Complex playlist analysis query: {query_time_ms:.1f}ms")

    def test_search_query_performance(self, app):
        """Test search query performance"""
        with app.app_context():
            start_time = time.time()

            # Simulate search functionality
            search_term = "Test"
            songs = (
                db.session.query(Song)
                .filter(
                    db.or_(
                        Song.title.ilike(f"%{search_term}%"),
                        Song.artist.ilike(f"%{search_term}%"),
                        Song.album.ilike(f"%{search_term}%"),
                    )
                )
                .limit(20)
                .all()
            )

            end_time = time.time()
            query_time_ms = (end_time - start_time) * 1000

            assert len(songs) <= 20
            assert query_time_ms < 100, f"Search query took {query_time_ms:.1f}ms, target was 100ms"
            print(f"Search query: {query_time_ms:.1f}ms ({len(songs)} results)")


class TestDatabaseIndexAnalysis:
    """Analyze which indexes would provide the most benefit"""

    def test_identify_slow_queries(self, app):
        """Identify queries that would benefit most from indexing"""
        with app.app_context():
            # Create some test data
            user = User(
                spotify_id="index_test",
                email="index@test.com",
                display_name="Index Test",
                access_token="test_access_token",
                refresh_token="test_refresh_token",
                token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            db.session.add(user)
            db.session.flush()

            # Test various query patterns and identify slow ones
            slow_queries = []

            # Test 1: Analysis results by status (common filter)
            start_time = time.time()
            db.session.query(AnalysisResult).filter(AnalysisResult.status == "completed").count()
            query_time = (time.time() - start_time) * 1000
            if query_time > 20:
                slow_queries.append(("AnalysisResult.status filter", query_time))

            # Test 2: Analysis results ordered by analyzed_at (common sort)
            start_time = time.time()
            db.session.query(AnalysisResult).order_by(AnalysisResult.analyzed_at.desc()).limit(
                10
            ).all()
            query_time = (time.time() - start_time) * 1000
            if query_time > 20:
                slow_queries.append(("AnalysisResult.analyzed_at order", query_time))

            # Test 3: Playlist songs by playlist_id (very common join)
            start_time = time.time()
            db.session.query(PlaylistSong).filter(PlaylistSong.playlist_id == 1).count()
            query_time = (time.time() - start_time) * 1000
            if query_time > 10:
                slow_queries.append(("PlaylistSong.playlist_id filter", query_time))

            # Test 4: Songs by spotify_id (unique lookups)
            start_time = time.time()
            db.session.query(Song).filter(Song.spotify_id == "test_song_1").first()
            query_time = (time.time() - start_time) * 1000
            if query_time > 10:
                slow_queries.append(("Song.spotify_id lookup", query_time))

            # Test 5: Playlists by owner_id (user's playlists)
            start_time = time.time()
            db.session.query(Playlist).filter(Playlist.owner_id == user.id).count()
            query_time = (time.time() - start_time) * 1000
            if query_time > 10:
                slow_queries.append(("Playlist.owner_id filter", query_time))

            print("\\n🔍 SLOW QUERY ANALYSIS:")
            if slow_queries:
                print("Queries that would benefit from indexing:")
                for query_desc, time_ms in slow_queries:
                    print(f"  - {query_desc}: {time_ms:.1f}ms")
            else:
                print(
                    "  ✅ All test queries performed well (may need more data to see bottlenecks)"
                )

            # Always pass - this is analysis, not a strict test
            assert True


@pytest.fixture
def performance_baseline():
    """Performance targets for database queries"""
    return {
        "simple_count": 50,  # ms
        "join_query": 100,  # ms
        "complex_query": 150,  # ms
        "search_query": 100,  # ms
        "aggregation": 100,  # ms
    }
