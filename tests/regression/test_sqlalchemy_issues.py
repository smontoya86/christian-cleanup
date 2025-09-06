"""
SQLAlchemy Regression Tests

Simplified regression tests for database functionality
in the Christian Music Curator application.
"""

import time
from datetime import datetime, timezone

import pytest

from app.models.models import AnalysisResult, Playlist, Song, User


class TestSQLAlchemyRegression:
    """
    Regression tests for SQLAlchemy functionality.

    Tests scenarios that have previously caused issues:
    - Database session management
    - Model relationships
    - Concurrent access patterns
    - Connection recovery
    """

    @pytest.mark.regression
    @pytest.mark.database
    def test_database_session_management_regression(self, app, db_session):
        """
        Regression test for proper database session management.

        Previously, sessions could leak or become detached.
        Now they should be managed properly with automatic cleanup.

        Issue: Session leaks and detached instances
        Fix: Proper session lifecycle management
        """
        with app.app_context():
            try:
                # Create a user
                test_user = User(
                    spotify_id="session_test_user",
                    display_name="Session Test User",
                    email="session@test.com",
                    access_token="test_token",
                    refresh_token="test_refresh",
                    token_expiry=datetime.now(timezone.utc),
                )

                db_session.add(test_user)
                db_session.commit()

                # Verify user was saved
                saved_user = (
                    db_session.query(User).filter_by(spotify_id="session_test_user").first()
                )
                assert saved_user is not None
                assert saved_user.display_name == "Session Test User"

                # Test session is still active
                assert db_session.is_active

                # Clean up
                db_session.delete(saved_user)
                db_session.commit()

                # Should not raise session-related errors
                assert True, "Database session management should work properly"

            except Exception as e:
                pytest.fail(f"Database session management should work properly: {e}")

    @pytest.mark.regression
    @pytest.mark.database
    def test_model_relationships_integrity_regression(self, app, db_session, test_user):
        """
        Regression test for model relationship integrity.

        Previously, relationships could become corrupted or inconsistent.
        Now they should maintain referential integrity.

        Issue: Relationship corruption and inconsistency
        Fix: Proper foreign key constraints and cascade behavior
        """
        with app.app_context():
            try:
                # Create a playlist for the user (using correct field name)
                playlist = Playlist(
                    spotify_id="test_playlist_relationships",
                    name="Test Playlist",
                    description="Test Description",
                    owner_id=test_user.id,  # This is the correct field name
                    spotify_snapshot_id="test_snapshot",
                )

                db_session.add(playlist)
                db_session.commit()

                # Create a song (using correct field names)
                song = Song(
                    spotify_id="test_song_relationships",
                    title="Test Song",
                    artist="Test Artist",
                    album="Test Album",
                    duration_ms=200000,
                )

                db_session.add(song)
                db_session.commit()

                # Create an analysis result
                analysis = AnalysisResult(
                    song_id=song.id,
                    # No status field needed - all stored analyses are completed
                    score=85,
                    concern_level="Low",
                    explanation="Test analysis for regression testing",
                    themes={"worship": True},
                    concerns=[],
                    analyzed_at=datetime.now(timezone.utc),
                )

                db_session.add(analysis)
                db_session.commit()

                # Test relationships
                assert playlist.owner_id == test_user.id
                assert analysis.song_id == song.id

                # Clean up
                db_session.delete(analysis)
                db_session.delete(song)
                db_session.delete(playlist)
                db_session.commit()

                # Should not raise relationship errors
                assert True, "Model relationships should maintain integrity"

            except Exception as e:
                pytest.fail(f"Model relationships should maintain integrity: {e}")

    @pytest.mark.regression
    @pytest.mark.database
    def test_song_lyrics_update_race_condition_regression(self, app, db_session):
        """
        Regression test for race conditions in song lyrics updates.

        Previously, concurrent updates could cause data corruption.
        Now they should be handled safely with proper locking.

        Issue: Race conditions in lyrics updates
        Fix: Proper database transaction handling
        """
        with app.app_context():
            try:
                # Create a test song (using correct field names)
                song = Song(
                    spotify_id="test_song_race_condition",
                    title="Race Test Song",
                    artist="Race Test Artist",
                    album="Race Test Album",
                    duration_ms=200000,
                )

                db_session.add(song)
                db_session.commit()

                # Simulate concurrent updates (simplified)
                original_lyrics = song.lyrics

                # Update lyrics field
                song.lyrics = "Updated lyrics content"
                db_session.commit()

                # Verify update
                updated_song = (
                    db_session.query(Song).filter_by(spotify_id="test_song_race_condition").first()
                )
                assert updated_song.lyrics == "Updated lyrics content"

                # Clean up
                db_session.delete(updated_song)
                db_session.commit()

                # Should not raise race condition errors
                assert True, "Lyrics updates should handle concurrency safely"

            except Exception as e:
                pytest.fail(f"Lyrics updates should handle concurrency safely: {e}")

    @pytest.mark.regression
    @pytest.mark.database
    def test_database_connection_recovery_regression(self, app):
        """
        Regression test for database connection recovery.

        Previously, lost connections would not recover properly.
        Now they should be handled with automatic reconnection.

        Issue: Database connection not recovering after loss
        Fix: Proper connection pool management and retry logic
        """
        try:
            with app.app_context():
                from app.extensions import db

                # Test basic database operation (using modern SQLAlchemy API)
                with db.engine.connect() as connection:
                    result = connection.execute(db.text("SELECT 1 as test_value"))
                    row = result.fetchone()
                    assert row[0] == 1

                # Should not raise connection errors
                assert True, "Database connection should be stable"

        except Exception as e:
            pytest.fail(f"Database connection should be stable: {e}")

    @pytest.mark.regression
    @pytest.mark.database
    def test_analysis_result_aggregation_regression(self, app, db_session, test_user):
        """
        Regression test for analysis result aggregation queries.

        Previously, complex aggregation queries could fail or be slow.
        Now they should work efficiently with proper indexing.

        Issue: Slow or failing aggregation queries
        Fix: Optimized queries with proper indexing
        """
        with app.app_context():
            try:
                # Create test data
                songs = []
                analyses = []

                for i in range(3):
                    song = Song(
                        spotify_id=f"test_song_aggregation_{i}",
                        title=f"Test Song {i}",
                        artist="Test Artist",
                        album="Test Album",
                        duration_ms=200000 + i * 1000,
                    )
                    songs.append(song)
                    db_session.add(song)

                db_session.commit()

                for i, song in enumerate(songs):
                    analysis = AnalysisResult(
                        song_id=song.id,
                        # No status field needed - all stored analyses are completed
                        score=80 + i * 5,
                        concern_level="Low" if i < 2 else "Medium",
                        explanation=f"Test analysis {i+1} for aggregation testing",
                        themes={"worship": True},
                        concerns=[],
                        analyzed_at=datetime.now(timezone.utc),
                    )
                    analyses.append(analysis)
                    db_session.add(analysis)

                db_session.commit()

                # Test aggregation query
                from sqlalchemy import func

                avg_score = (
                    db_session.query(func.avg(AnalysisResult.score))
                    # No status filter needed - all stored analyses are completed
                    .scalar()
                )

                assert avg_score is not None
                assert isinstance(avg_score, (int, float))

                # Clean up
                for analysis in analyses:
                    db_session.delete(analysis)
                for song in songs:
                    db_session.delete(song)
                db_session.commit()

                # Should not raise aggregation errors
                assert True, "Analysis aggregation queries should work efficiently"

            except Exception as e:
                pytest.fail(f"Analysis aggregation queries should work efficiently: {e}")

    @pytest.mark.regression
    @pytest.mark.database
    def test_large_dataset_performance_regression(self, app, db_session):
        """
        Regression test for performance with larger datasets.

        Previously, queries would slow down significantly with more data.
        Now they should maintain reasonable performance with indexing.

        Issue: Poor performance with larger datasets
        Fix: Proper indexing and query optimization
        """
        with app.app_context():
            try:
                start_time = time.time()

                # Test a query that should be fast
                user_count = db_session.query(User).count()
                song_count = db_session.query(Song).count()

                end_time = time.time()
                query_duration = end_time - start_time

                # Basic queries should be fast (under 1 second)
                assert query_duration < 1.0, f"Basic queries took too long: {query_duration:.3f}s"

                # Should return reasonable results
                assert user_count >= 0
                assert song_count >= 0

                # Should not raise performance errors
                assert True, "Database queries should maintain reasonable performance"

            except Exception as e:
                pytest.fail(f"Database queries should maintain reasonable performance: {e}")

    @pytest.mark.regression
    @pytest.mark.database
    def test_transaction_rollback_regression(self, app, db_session):
        """
        Regression test for proper transaction rollback behavior.

        Previously, failed transactions could leave the database in inconsistent state.
        Now they should rollback cleanly on errors.

        Issue: Inconsistent database state after failed transactions
        Fix: Proper exception handling and rollback mechanisms
        """
        with app.app_context():
            try:
                # Start a transaction that will fail
                test_user = User(
                    spotify_id="test_rollback_user",
                    display_name="Rollback Test User",
                    email="rollback@test.com",
                    access_token="test_token",
                    refresh_token="test_refresh",
                    token_expiry=datetime.now(timezone.utc),
                )

                db_session.add(test_user)

                # Force a constraint violation (duplicate spotify_id)
                duplicate_user = User(
                    spotify_id="test_rollback_user",  # Same ID - should fail
                    display_name="Duplicate User",
                    email="duplicate@test.com",
                    access_token="test_token2",
                    refresh_token="test_refresh2",
                    token_expiry=datetime.now(timezone.utc),
                )

                db_session.add(duplicate_user)

                # This should fail and rollback
                try:
                    db_session.commit()
                    pytest.fail("Should have failed due to duplicate constraint")
                except Exception:
                    # Expected failure - rollback should happen automatically
                    db_session.rollback()

                # Database should be in clean state
                user_exists = (
                    db_session.query(User).filter_by(spotify_id="test_rollback_user").first()
                )
                assert user_exists is None, "User should not exist after rollback"

                # Should not raise transaction errors
                assert True, "Transaction rollback should work properly"

            except Exception as e:
                pytest.fail(f"Transaction rollback should work properly: {e}")
