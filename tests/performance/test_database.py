"""
Database performance tests for regression testing.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import create_app
from app.models.models import AnalysisResult, Playlist, PlaylistSong, Song, User, db
from tests.config import TestConfig
from tests.utils.benchmark import PerformanceBenchmark


class TestDatabasePerformance:
    """Test database query performance."""

    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database with performance data."""
        self.app = create_app()
        self.app.config.from_object(TestConfig)

        with self.app.app_context():
            db.drop_all()
            db.create_all()

            # Seed performance test data
            self._seed_performance_data()

            yield

            db.session.remove()
            db.drop_all()

    def _seed_performance_data(self):
        """Seed database with performance test data."""
        # Create test users
        users = []
        for i in range(10):
            unique_suffix = str(uuid.uuid4())[:8]
            user = User(
                spotify_id=f"test_user_{i}_{unique_suffix}",
                display_name=f"Test User {i}",
                email=f"test{i}_{unique_suffix}@example.com",
                access_token=f"test_access_token_{i}",
                token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            db.session.add(user)
            users.append(user)

        db.session.flush()  # Get user IDs

        # Create playlists for each user
        playlists = []
        for user in users:
            for j in range(5):  # 5 playlists per user
                unique_suffix = str(uuid.uuid4())[:8]
                playlist = Playlist(
                    spotify_id=f"playlist_{user.id}_{j}_{unique_suffix}",
                    name=f"Test Playlist {j} for User {user.id}",
                    owner_id=user.id,
                    image_url=f"http://example.com/image_{user.id}_{j}.jpg",
                )
                db.session.add(playlist)
                playlists.append(playlist)

        db.session.flush()  # Get playlist IDs

        # Create test songs (100 songs)
        songs = []
        for i in range(100):
            song = Song(
                spotify_id=f"test_song_{i+1}",
                title=f"Test Song {i}",
                artist=f"Test Artist {i}",
                album=f"Test Album {i}",
                duration_ms=180000 + (i * 1000),
                album_art_url=f"http://example.com/album_{i+1}.jpg",
                explicit=i % 10 == 0,  # Every 10th song is explicit
                lyrics=f"Lyrics for song {i}",
            )
            db.session.add(song)
            songs.append(song)

        db.session.flush()  # Get song IDs

        # Create playlist-song associations
        for playlist in playlists:
            playlist_songs = [s for s in songs if s.spotify_id.startswith("test_song_")]
            for i, song in enumerate(playlist_songs):
                playlist_song = PlaylistSong(
                    playlist_id=playlist.id, song_id=song.id, track_position=i
                )
                db.session.add(playlist_song)

        # Create analysis results for songs (simulate varying completion rates)
        for i, song in enumerate(songs):
            # Only create analysis for 70% of songs to simulate realistic scenario
            if i % 10 < 7:
                analysis = AnalysisResult(
                    song_id=song.id,
                    score=5.0 + (i % 6),  # Scores between 5-10
                    concern_level=["low", "medium", "high"][i % 3],
                    explanation=f"Analysis explanation for song {song.title}",
                    status="completed",
                    themes={"worship": i % 2 == 0, "praise": i % 3 == 0, "faith": True},
                    concerns=["keyword{j}" for j in range(i % 3)],
                    positive_themes_identified={
                        "biblical_references": i % 4 == 0,
                        "christian_values": True,
                    },
                )
                db.session.add(analysis)

        db.session.commit()

        # Store counts for verification
        self.user_count = len(users)
        self.playlist_count = len(playlists)
        self.song_count = len(songs)
        self.analysis_count = len([s for i, s in enumerate(songs) if i % 10 < 7])

    def test_user_playlists_query_performance(self):
        """Test performance of querying user playlists."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark("user_playlists_query", iterations=10)

            @benchmark.measure
            def query_user_playlists():
                # Get first user
                user = User.query.first()

                # Query user's playlists with song counts
                playlists = db.session.query(Playlist).filter_by(owner_id=user.id).all()

                # Access playlist data to trigger loading
                result = []
                for playlist in playlists:
                    playlist_data = {"id": playlist.id, "name": playlist.name}
                    result.append(playlist_data)

                return result

            result = query_user_playlists()
            assert len(result) == 5  # 5 playlists per user

    def test_playlist_songs_with_analysis_query_performance(self):
        """Test performance of querying playlist songs with analysis results."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark("playlist_songs_analysis_query", iterations=10)

            @benchmark.measure
            def query_playlist_songs_with_analysis():
                # Get first playlist
                playlist = Playlist.query.first()

                # Query songs with analysis results using JOIN
                songs_with_analysis = (
                    db.session.query(Song, AnalysisResult)
                    .outerjoin(AnalysisResult, Song.id == AnalysisResult.song_id)
                    .join(PlaylistSong, Song.id == PlaylistSong.song_id)
                    .filter(PlaylistSong.playlist_id == playlist.id)
                    .order_by(PlaylistSong.track_position)
                    .all()
                )

                # Process results
                result = []
                for song, analysis in songs_with_analysis:
                    song_data = {
                        "id": song.id,
                        "title": song.title,
                        "artist": song.artist,
                        "has_analysis": analysis is not None,
                        "score": analysis.score if analysis else None,
                    }
                    result.append(song_data)

                return result

            result = query_playlist_songs_with_analysis()
            assert len(result) == 100  # All 100 songs are added to the first playlist

    def test_analysis_aggregation_query_performance(self):
        """Test performance of aggregating analysis results."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark("analysis_aggregation_query", iterations=10)

            @benchmark.measure
            def query_analysis_aggregations():
                # Get aggregated analysis statistics
                from sqlalchemy import func

                # Count by concern level
                concern_stats = (
                    db.session.query(
                        AnalysisResult.concern_level,
                        func.count(AnalysisResult.id).label("count"),
                        func.avg(AnalysisResult.score).label("avg_score"),
                    )
                    .group_by(AnalysisResult.concern_level)
                    .all()
                )

                # Overall statistics
                overall_stats = db.session.query(
                    func.count(AnalysisResult.id).label("total_analyzed"),
                    func.avg(AnalysisResult.score).label("overall_avg_score"),
                    func.min(AnalysisResult.score).label("min_score"),
                    func.max(AnalysisResult.score).label("max_score"),
                ).first()

                # User-specific statistics
                user_stats = (
                    db.session.query(
                        User.id,
                        User.display_name,
                        func.count(AnalysisResult.id).label("analyzed_songs"),
                        func.avg(AnalysisResult.score).label("avg_score"),
                    )
                    .join(Playlist, User.id == Playlist.owner_id)
                    .join(PlaylistSong, Playlist.id == PlaylistSong.playlist_id)
                    .join(Song, PlaylistSong.song_id == Song.id)
                    .join(AnalysisResult, Song.id == AnalysisResult.song_id)
                    .group_by(User.id, User.display_name)
                    .all()
                )

                return {
                    "concern_stats": [
                        (level, count, float(avg)) for level, count, avg in concern_stats
                    ],
                    "overall_stats": {
                        "total_analyzed": overall_stats.total_analyzed,
                        "overall_avg_score": float(overall_stats.overall_avg_score),
                        "min_score": float(overall_stats.min_score),
                        "max_score": float(overall_stats.max_score),
                    },
                    "user_stats": [
                        (uid, name, count, float(avg)) for uid, name, count, avg in user_stats
                    ],
                }

            result = query_analysis_aggregations()
            assert result["overall_stats"]["total_analyzed"] > 0
            assert len(result["concern_stats"]) == 3  # low, medium, high

    def test_search_songs_query_performance(self):
        """Test performance of searching songs by title and artist."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark("search_songs_query", iterations=10)

            @benchmark.measure
            def search_songs():
                # Search for songs with specific patterns
                search_term = "Test Song 1"

                # Use ILIKE for case-insensitive search
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

                # Process results
                result = []
                for song in songs:
                    song_data = {
                        "id": song.id,
                        "title": song.title,
                        "artist": song.artist,
                        "album": song.album,
                    }
                    result.append(song_data)

                return result

            result = search_songs()
            assert len(result) > 0  # Should find matching songs

    def test_bulk_insert_performance(self):
        """Test performance of bulk inserting songs."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark("bulk_insert_songs", iterations=3)

            @benchmark.measure
            def bulk_insert_songs():
                # Get a user and playlist for the test
                user = User.query.first()

                # Create a new playlist for bulk insert test
                unique_suffix = str(uuid.uuid4())[:8]
                test_playlist = Playlist(
                    spotify_id=f"bulk_playlist_{unique_suffix}",
                    name=f"Bulk Test Playlist {unique_suffix}",
                    owner_id=user.id,
                )
                db.session.add(test_playlist)
                db.session.flush()

                # Prepare bulk data
                songs_data = []
                for i in range(100):
                    unique_song_suffix = str(uuid.uuid4())[:8]
                    song = Song(
                        spotify_id=f"bulk_song_{i}_{unique_song_suffix}",
                        title=f"Bulk Song {i}",
                        artist=f"Bulk Artist {i % 10}",
                        album=f"Bulk Album {i % 20}",
                        duration_ms=180000 + (i * 1000),
                    )
                    songs_data.append(song)

                # Bulk insert songs
                db.session.add_all(songs_data)
                db.session.flush()

                # Create playlist-song associations
                playlist_songs = []
                for i, song in enumerate(songs_data):
                    playlist_song = PlaylistSong(
                        playlist_id=test_playlist.id, song_id=song.id, track_position=i
                    )
                    playlist_songs.append(playlist_song)

                # Bulk insert associations
                db.session.add_all(playlist_songs)
                db.session.commit()

                return len(songs_data)

            result = bulk_insert_songs()
            assert result == 100

    def test_complex_join_query_performance(self):
        """Test performance of complex multi-table joins."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark("complex_join_query", iterations=5)

            @benchmark.measure
            def complex_join_query():
                # Complex query joining all tables
                from sqlalchemy import func

                results = (
                    db.session.query(
                        User.display_name,
                        Playlist.name.label("playlist_name"),
                        func.count(Song.id).label("total_songs"),
                        func.count(AnalysisResult.id).label("analyzed_songs"),
                        func.avg(AnalysisResult.score).label("avg_score"),
                        func.count(
                            db.case((AnalysisResult.concern_level == "high", 1), else_=None)
                        ).label("high_concern_songs"),
                    )
                    .select_from(User)
                    .join(Playlist, User.id == Playlist.owner_id)
                    .join(PlaylistSong, Playlist.id == PlaylistSong.playlist_id)
                    .join(Song, PlaylistSong.song_id == Song.id)
                    .outerjoin(AnalysisResult, Song.id == AnalysisResult.song_id)
                    .group_by(User.id, User.display_name, Playlist.id, Playlist.name)
                    .having(func.count(Song.id) > 0)
                    .order_by(func.avg(AnalysisResult.score).desc().nullslast())
                    .all()
                )

                # Process results
                processed_results = []
                for row in results:
                    result_data = {
                        "user_name": row.display_name,
                        "playlist_name": row.playlist_name,
                        "total_songs": row.total_songs,
                        "analyzed_songs": row.analyzed_songs,
                        "avg_score": float(row.avg_score) if row.avg_score else None,
                        "high_concern_songs": row.high_concern_songs,
                    }
                    processed_results.append(result_data)

                return processed_results

            result = complex_join_query()
            assert len(result) > 0  # Should return playlist statistics

    def test_pagination_query_performance(self):
        """Test performance of paginated queries."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark("pagination_query", iterations=10)

            @benchmark.measure
            def paginated_query():
                page_size = 20
                results = []

                # Test multiple pages
                for page in range(1, 6):  # Test first 5 pages
                    offset = (page - 1) * page_size

                    songs = (
                        db.session.query(Song)
                        .join(AnalysisResult, Song.id == AnalysisResult.song_id, isouter=True)
                        .order_by(Song.title)
                        .offset(offset)
                        .limit(page_size)
                        .all()
                    )

                    page_data = []
                    for song in songs:
                        song_data = {"id": song.id, "title": song.title, "artist": song.artist}
                        page_data.append(song_data)

                    results.extend(page_data)

                return results

            result = paginated_query()
            assert len(result) == 100  # 5 pages * 20 items per page

    def test_database_connection_performance(self):
        """Test database connection and basic query performance."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark("db_connection_query", iterations=20)

            @benchmark.measure
            def basic_connection_test():
                # Simple query to test connection performance
                user_count = db.session.query(User).count()
                playlist_count = db.session.query(Playlist).count()
                song_count = db.session.query(Song).count()
                analysis_count = db.session.query(AnalysisResult).count()

                return {
                    "users": user_count,
                    "playlists": playlist_count,
                    "songs": song_count,
                    "analyses": analysis_count,
                }

            result = basic_connection_test()
            assert result["users"] == self.user_count
            assert result["playlists"] == self.playlist_count
            assert result["songs"] == self.song_count
            assert result["analyses"] == self.analysis_count
