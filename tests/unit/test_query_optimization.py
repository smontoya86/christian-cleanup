"""
Tests for query optimization and N+1 pattern elimination.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from app import create_app, db
from app.models.models import AnalysisResult, Playlist, PlaylistSong, Song, User


class QueryCounter:
    """Helper class to count database queries."""

    def __init__(self):
        self.query_count = 0
        self.queries = []

    def reset(self):
        self.query_count = 0
        self.queries = []

    def count_query(self, conn, cursor, statement, parameters, context, executemany):
        self.query_count += 1
        self.queries.append(statement)


class TestQueryOptimization:
    """Test query optimization and N+1 pattern elimination."""

    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database."""
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Set up query counter
        self.query_counter = QueryCounter()
        event.listen(db.engine, "before_cursor_execute", self.query_counter.count_query)

        yield

        # Clean up
        event.remove(db.engine, "before_cursor_execute", self.query_counter.count_query)
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_test_data(self):
        """Create test data for optimization tests."""
        # Create user
        user = User(
            spotify_id="test_user",
            email="test@example.com",
            access_token="test_token",
            refresh_token="test_refresh",
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.session.add(user)
        db.session.commit()

        # Create playlists
        playlists = []
        for i in range(3):
            playlist = Playlist(
                spotify_id=f"test_playlist_{i}", name=f"Test Playlist {i}", owner_id=user.id
            )
            playlists.append(playlist)
            db.session.add(playlist)
        db.session.commit()

        # Create songs
        songs = []
        for i in range(10):
            song = Song(spotify_id=f"test_song_{i}", title=f"Test Song {i}", artist="Test Artist")
            songs.append(song)
            db.session.add(song)
        db.session.commit()

        # Create playlist-song associations
        for playlist_idx, playlist in enumerate(playlists):
            for song_idx in range(3):  # 3 songs per playlist
                song = songs[playlist_idx * 3 + song_idx]
                association = PlaylistSong(
                    playlist_id=playlist.id, song_id=song.id, track_position=song_idx
                )
                db.session.add(association)
        db.session.commit()

        # Create analysis results
        for song in songs:
            analysis = AnalysisResult(song_id=song.id, score=85.0 + song.id, concern_level="Low", explanation="Test analysis")
            db.session.add(analysis)
        db.session.commit()

        return user, playlists, songs

    def test_n_plus_one_pattern_detection(self):
        """Test detection of N+1 query patterns in playlist loading."""
        user, playlists, songs = self.create_test_data()

        # Reset query counter
        self.query_counter.reset()

        # Simulate N+1 pattern: Load playlists then access songs individually
        user_playlists = Playlist.query.filter_by(owner_id=user.id).all()

        # This creates N+1 pattern - one query for playlists, then one query per playlist for songs
        for playlist in user_playlists:
            # Accessing songs through the relationship triggers additional queries
            songs_in_playlist = [assoc.song for assoc in playlist.song_associations]
            for song in songs_in_playlist:
                # Accessing analysis results triggers more queries
                analysis = song.analysis_results.first()

        n_plus_one_query_count = self.query_counter.query_count

        # Should be more than 4 queries (1 for playlists + 3 for song associations + more for analysis)
        assert (
            n_plus_one_query_count > 4
        ), f"Expected N+1 pattern with >4 queries, got {n_plus_one_query_count}"

        print(f"N+1 pattern detected: {n_plus_one_query_count} queries")

    def test_optimized_playlist_loading_with_eager_loading(self):
        """Test optimized playlist loading using eager loading."""
        user, playlists, songs = self.create_test_data()

        # Reset query counter
        self.query_counter.reset()

        # Optimized query using eager loading
        from sqlalchemy.orm import subqueryload

        optimized_playlists = (
            Playlist.query.filter_by(owner_id=user.id)
            .options(subqueryload(Playlist.song_associations).joinedload(PlaylistSong.song))
            .all()
        )

        # Access the data to trigger loading
        for playlist in optimized_playlists:
            songs_in_playlist = [assoc.song for assoc in playlist.song_associations]
            for song in songs_in_playlist:
                # This should not trigger additional queries due to eager loading
                title = song.title

        optimized_query_count = self.query_counter.query_count

        # Should be significantly fewer queries (ideally 2-3: playlists + associations + songs)
        assert (
            optimized_query_count <= 3
        ), f"Expected ≤3 queries with eager loading, got {optimized_query_count}"

        print(f"Optimized query count: {optimized_query_count} queries")

    def test_query_optimization_performance_improvement(self):
        """Test that query optimization provides significant performance improvement."""
        # Create test data once for this test
        user, playlists, songs = self.create_test_data()

        # Test N+1 pattern
        self.query_counter.reset()
        user_playlists = Playlist.query.filter_by(owner_id=user.id).all()
        for playlist in user_playlists:
            songs_in_playlist = [assoc.song for assoc in playlist.song_associations]
            for song in songs_in_playlist:
                analysis = song.analysis_results.first()
        n_plus_one_count = self.query_counter.query_count

        # Test optimized version
        self.query_counter.reset()
        from sqlalchemy.orm import subqueryload

        optimized_playlists = (
            Playlist.query.filter_by(owner_id=user.id)
            .options(subqueryload(Playlist.song_associations).joinedload(PlaylistSong.song))
            .all()
        )
        for playlist in optimized_playlists:
            songs_in_playlist = [assoc.song for assoc in playlist.song_associations]
            for song in songs_in_playlist:
                title = song.title
        optimized_count = self.query_counter.query_count

        # Calculate improvement
        improvement_ratio = n_plus_one_count / optimized_count

        # Should be at least 2x improvement
        assert (
            improvement_ratio >= 2
        ), f"Expected at least 2x query reduction, got {improvement_ratio:.1f}x"

    def test_dashboard_query_optimization(self):
        """Test that dashboard queries are optimized."""
        user, playlists, songs = self.create_test_data()

        # Reset query counter
        self.query_counter.reset()

        # Simulate dashboard statistics queries (optimized version)
        stats = {}

        # Total playlists count
        stats["total_playlists"] = db.session.query(Playlist).filter_by(owner_id=user.id).count()

        # Total songs count using JOIN
        stats["total_songs"] = (
            db.session.query(Song)
            .join(PlaylistSong, Song.id == PlaylistSong.song_id)
            .join(Playlist, PlaylistSong.playlist_id == Playlist.id)
            .filter(Playlist.owner_id == user.id)
            .count()
        )

        # Analyzed songs count using JOIN
        stats["analyzed_songs"] = (
            db.session.query(Song)
            .join(PlaylistSong, Song.id == PlaylistSong.song_id)
            .join(Playlist, PlaylistSong.playlist_id == Playlist.id)
            .join(AnalysisResult, Song.id == AnalysisResult.song_id)
            .filter(Playlist.owner_id == user.id)
            .count()
        )

        dashboard_query_count = self.query_counter.query_count

        # Should be 3-4 queries for the 3 statistics (allowing for some overhead)
        assert (
            dashboard_query_count <= 4
        ), f"Expected ≤4 optimized dashboard queries, got {dashboard_query_count}"

        # Verify results are correct
        assert stats["total_playlists"] == 3
        assert stats["total_songs"] == 9  # 3 playlists * 3 songs each
        assert stats["analyzed_songs"] == 9  # All songs have analysis

    def test_playlist_detail_optimization(self):
        """Test that playlist detail view is optimized."""
        user, playlists, songs = self.create_test_data()
        playlist = playlists[0]

        # Reset query counter
        self.query_counter.reset()

        # Optimized playlist detail query (without eager loading dynamic relationships)
        from sqlalchemy.orm import subqueryload

        playlist_with_songs = (
            Playlist.query.filter_by(id=playlist.id)
            .options(subqueryload(Playlist.song_associations).joinedload(PlaylistSong.song))
            .first()
        )

        # Access all the data
        songs_data = []
        for assoc in playlist_with_songs.song_associations:
            song = assoc.song
            # Get analysis separately (since it's a dynamic relationship)
            analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
            songs_data.append(
                {
                    "title": song.title,
                    "artist": song.artist,
                    "score": analysis.score if analysis else None,
                }
            )

        detail_query_count = self.query_counter.query_count

        # Should be minimal queries due to eager loading (allowing for analysis queries)
        assert (
            detail_query_count <= 6
        ), f"Expected ≤6 queries for playlist detail, got {detail_query_count}"

        # Verify we got the expected data
        assert len(songs_data) == 3
        assert all(song_data["score"] is not None for song_data in songs_data)

    def test_bulk_analysis_status_check(self):
        """Test bulk analysis status checking is optimized."""
        user, playlists, songs = self.create_test_data()

        # Get song IDs for a playlist first (this may require queries)
        playlist = playlists[0]
        song_ids = [assoc.song_id for assoc in playlist.song_associations]

        # Reset query counter AFTER getting song IDs
        self.query_counter.reset()

        # Bulk query for analysis status
        analysis_results = AnalysisResult.query.filter(AnalysisResult.song_id.in_(song_ids)).all()

        # Create status mapping
        status_map = {result.song_id: "completed" for result in analysis_results}

        bulk_query_count = self.query_counter.query_count

        # Should be just 1 query for bulk status check
        assert bulk_query_count == 1, f"Expected 1 bulk query, got {bulk_query_count}"

        # Verify we got status for all songs
        assert len(status_map) == 3
