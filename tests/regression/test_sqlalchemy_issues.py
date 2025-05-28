"""
Regression tests for SQLAlchemy and database issues.
These tests ensure that previously fixed database bugs don't reoccur.
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import InvalidRequestError, IntegrityError

from app.models.models import User, Playlist, Song, AnalysisResult, PlaylistSong
from app.extensions import db
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.services.enhanced_analysis_service import analyze_song_background


class TestSQLAlchemyRegression:
    """Regression tests for SQLAlchemy and database issues."""

    @pytest.mark.regression
    @pytest.mark.database
    def test_detached_instance_error_in_worker_regression(self, app, db_session, new_user):
        """
        Regression test for DetachedInstanceError in background workers.
        
        Previously, background workers would fail with DetachedInstanceError
        when trying to access object attributes after the session was closed.
        
        Issue: DetachedInstanceError when accessing model attributes in workers
        Fix: Proper session management and object reattachment in worker context
        """
        with app.app_context():
            # Create test data
            song = Song(
                spotify_id='test_song_123',
                title='Amazing Grace',
                artist='Chris Tomlin',
                album='How Great Is Our God',
                duration_ms=240000
            )
            db_session.add(song)
            db_session.commit()
            song_id = song.id
            
            # Simulate session closure (what happens between web request and worker)
            db_session.expunge(song)
            db_session.close()
            
            # Worker process starts with new session
            with app.app_context():
                # This should not raise DetachedInstanceError
                try:
                    # Simulate worker accessing the song
                    worker_song = db.session.get(Song, song_id)
                    assert worker_song is not None
                    
                    # These accesses should not fail
                    title = worker_song.title
                    artist = worker_song.artist
                    spotify_id = worker_song.spotify_id
                    
                    assert title == 'Amazing Grace'
                    assert artist == 'Chris Tomlin'
                    assert spotify_id == 'test_song_123'
                    
                except DetachedInstanceError:
                    pytest.fail("DetachedInstanceError should not occur in worker context")

    @pytest.mark.regression
    @pytest.mark.database
    def test_analysis_result_session_management_regression(self, app, db_session, new_user):
        """
        Regression test for AnalysisResult session management issues.
        
        Previously, creating AnalysisResult objects in workers would fail
        due to improper session handling across thread boundaries.
        
        Issue: Session management errors when creating AnalysisResult objects
        Fix: Proper session scoping and object creation in worker context
        """
        with app.app_context():
            # Create test song
            song = Song(
                spotify_id='test_song_analysis',
                title='Test Song',
                artist='Test Artist',
                album='Test Album',
                duration_ms=180000
            )
            db_session.add(song)
            db_session.commit()
            song_id = song.id
            
            # Simulate worker context
            db_session.close()
            
            with app.app_context():
                # This should not fail with session errors
                try:
                    worker_song = db.session.get(Song, song_id)
                    
                    # Create analysis result (simulating worker behavior)
                    analysis_result = AnalysisResult(
                        song_id=worker_song.id,
                        user_id=new_user.id,
                        overall_score=8.5,
                        biblical_references=3,
                        spiritual_themes=['grace', 'salvation'],
                        explicit_christian_content=True,
                        analysis_version='1.0'
                    )
                    
                    db.session.add(analysis_result)
                    db.session.commit()
                    
                    # Verify the result was created properly
                    saved_result = db.session.query(AnalysisResult).filter_by(song_id=song_id).first()
                    assert saved_result is not None
                    assert saved_result.overall_score == 8.5
                    assert saved_result.biblical_references == 3
                    
                except (DetachedInstanceError, InvalidRequestError) as e:
                    pytest.fail(f"Session management error should not occur: {e}")

    @pytest.mark.regression
    @pytest.mark.database
    def test_playlist_sync_concurrent_access_regression(self, app, db_session, new_user):
        """
        Regression test for concurrent playlist synchronization issues.
        
        Previously, concurrent playlist sync operations would cause
        database integrity errors and session conflicts.
        
        Issue: Concurrent playlist sync causing database integrity errors
        Fix: Proper locking and conflict resolution in sync operations
        """
        import threading
        import time
        
        with app.app_context():
            # Create initial playlist
            playlist = Playlist(
                spotify_id='test_playlist_concurrent',
                name='Test Playlist',
                user_id=new_user.id,
                snapshot_id='initial_snapshot'
            )
            db_session.add(playlist)
            db_session.commit()
            playlist_id = playlist.id
            
            db_session.close()
            
            results = []
            errors = []
            
            def update_playlist(new_name, new_snapshot):
                try:
                    with app.app_context():
                        # Simulate concurrent playlist updates
                        existing_playlist = db.session.get(Playlist, playlist_id)
                        if existing_playlist:
                            existing_playlist.name = new_name
                            existing_playlist.snapshot_id = new_snapshot
                            db.session.commit()
                            results.append(f"Updated to {new_name}")
                        else:
                            results.append("Playlist not found")
                except Exception as e:
                    errors.append(str(e))
            
            # Simulate concurrent updates
            threads = []
            for i in range(3):
                thread = threading.Thread(
                    target=update_playlist,
                    args=(f'Updated Playlist {i}', f'snapshot_{i}')
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Should not have critical errors (some conflicts are expected)
            critical_errors = [e for e in errors if 'DetachedInstanceError' in e or 'InvalidRequestError' in e]
            assert len(critical_errors) == 0, f"Critical session errors occurred: {critical_errors}"
            
            # At least one update should have succeeded
            assert len(results) > 0

    @pytest.mark.regression
    @pytest.mark.database
    def test_song_lyrics_update_race_condition_regression(self, app, db_session):
        """
        Regression test for race conditions in song lyrics updates.
        
        Previously, concurrent lyrics updates for the same song would
        cause database integrity violations.
        
        Issue: Race conditions when multiple workers update song lyrics
        Fix: Proper conflict resolution and upsert logic
        """
        with app.app_context():
            # Create test song without lyrics
            song = Song(
                spotify_id='test_song_lyrics_race',
                title='Test Song',
                artist='Test Artist',
                album='Test Album',
                duration_ms=200000,
                lyrics=None
            )
            db_session.add(song)
            db_session.commit()
            song_id = song.id
            
            db_session.close()
            
            import threading
            results = []
            errors = []
            
            def update_lyrics(lyrics_content):
                try:
                    with app.app_context():
                        # Simulate worker updating lyrics
                        target_song = db.session.get(Song, song_id)
                        if target_song:
                            target_song.lyrics = lyrics_content
                            db.session.commit()
                            results.append(f"Updated with: {lyrics_content[:20]}...")
                        else:
                            results.append("Song not found")
                except Exception as e:
                    errors.append(str(e))
            
            # Simulate concurrent lyrics updates
            threads = []
            lyrics_contents = [
                "Amazing grace, how sweet the sound...",
                "How great thou art, how great thou art...", 
                "Blessed assurance, Jesus is mine..."
            ]
            
            for lyrics in lyrics_contents:
                thread = threading.Thread(target=update_lyrics, args=(lyrics,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Should not have session management errors
            session_errors = [e for e in errors if any(err_type in e for err_type in [
                'DetachedInstanceError', 'InvalidRequestError', 'Session'
            ])]
            assert len(session_errors) == 0, f"Session errors occurred: {session_errors}"
            
            # Verify final state
            with app.app_context():
                final_song = db.session.get(Song, song_id)
                assert final_song.lyrics is not None
                assert len(final_song.lyrics) > 0

    @pytest.mark.regression
    @pytest.mark.database
    def test_user_playlist_deletion_cascade_regression(self, app, db_session, new_user):
        """
        Regression test for proper cascade deletion handling.
        
        Previously, deleting users or playlists would leave orphaned records
        or cause foreign key constraint violations.
        
        Issue: Improper cascade deletion causing orphaned records
        Fix: Proper foreign key constraints and cascade rules
        """
        with app.app_context():
            # Create test data with relationships
            playlist = Playlist(
                spotify_id='test_playlist_cascade',
                name='Test Playlist',
                user_id=new_user.id,
                snapshot_id='test_snapshot'
            )
            db_session.add(playlist)
            db_session.flush()  # Get the ID without committing
            
            song = Song(
                spotify_id='test_song_cascade',
                title='Test Song',
                artist='Test Artist',
                album='Test Album',
                duration_ms=180000
            )
            db_session.add(song)
            db_session.flush()
            
            # Create playlist-song relationship
            playlist_song = PlaylistSong(
                playlist_id=playlist.id,
                song_id=song.id,
                position=1
            )
            db_session.add(playlist_song)
            
            # Create analysis result
            analysis = AnalysisResult(
                song_id=song.id,
                user_id=new_user.id,
                overall_score=7.5,
                biblical_references=2,
                analysis_version='1.0'
            )
            db_session.add(analysis)
            db_session.commit()
            
            # Store IDs for verification
            playlist_id = playlist.id
            song_id = song.id
            analysis_id = analysis.id
            
            # Delete the playlist - should not cause foreign key violations
            try:
                db_session.delete(playlist)
                db_session.commit()
                
                # Verify cascade behavior
                remaining_playlist_songs = db_session.query(PlaylistSong).filter_by(
                    playlist_id=playlist_id
                ).all()
                
                # Playlist-song relationships should be removed
                assert len(remaining_playlist_songs) == 0
                
                # Song and analysis should still exist (not cascaded)
                remaining_song = db_session.get(Song, song_id)
                remaining_analysis = db_session.get(AnalysisResult, analysis_id)
                
                assert remaining_song is not None
                assert remaining_analysis is not None
                
            except IntegrityError as e:
                pytest.fail(f"Foreign key constraint violation should not occur: {e}")

    @pytest.mark.regression
    @pytest.mark.database
    def test_analysis_service_session_isolation_regression(self, app, db_session, new_user):
        """
        Regression test for AnalysisService session isolation.
        
        Previously, AnalysisService would interfere with the main session
        causing unexpected commits and rollbacks.
        
        Issue: AnalysisService operations affecting main session state
        Fix: Proper session isolation and scoping
        """
        with app.app_context():
            # Create test song
            song = Song(
                spotify_id='test_song_isolation',
                title='Test Song',
                artist='Test Artist',
                album='Test Album',
                duration_ms=180000,
                lyrics='Amazing grace, how sweet the sound'
            )
            db_session.add(song)
            db_session.commit()
            song_id = song.id
            
            # Start a transaction but don't commit
            another_song = Song(
                spotify_id='test_song_uncommitted',
                title='Uncommitted Song',
                artist='Test Artist',
                album='Test Album',
                duration_ms=160000
            )
            db_session.add(another_song)
            # Don't commit - this should remain uncommitted
            
            # Use AnalysisService - this should not affect the uncommitted transaction
            analysis_service = UnifiedAnalysisService()
            
            try:
                # Perform analysis (which creates its own session)
                result = analyze_song_background(song.id, new_user.id)
                
                # Verify analysis was successful
                assert result is not None
                
                # Check that our uncommitted song is still uncommitted
                # (AnalysisService should not have committed our transaction)
                db_session.rollback()
                
                uncommitted_check = db_session.query(Song).filter_by(
                    spotify_id='test_song_uncommitted'
                ).first()
                
                # Should be None because we rolled back
                assert uncommitted_check is None
                
                # But the analysis should still exist (created in separate session)
                analysis_check = db_session.query(AnalysisResult).filter_by(
                    song_id=song_id
                ).first()
                assert analysis_check is not None
                
            except Exception as e:
                pytest.fail(f"AnalysisService should not interfere with session state: {e}")

    @pytest.mark.regression
    @pytest.mark.database
    def test_database_connection_recovery_regression(self, app, db_session):
        """
        Regression test for database connection recovery.
        
        Previously, lost database connections would not be properly
        recovered, leading to persistent connection errors.
        
        Issue: Lost database connections not properly recovered
        Fix: Connection pooling and automatic recovery mechanisms
        """
        with app.app_context():
            # Create initial test data
            song = Song(
                spotify_id='test_connection_recovery',
                title='Connection Test Song',
                artist='Test Artist',
                album='Test Album',
                duration_ms=180000
            )
            db_session.add(song)
            db_session.commit()
            song_id = song.id
            
            # Simulate connection loss by closing the session
            db_session.close()
            
            # Simulate application attempting to use database after connection loss
            try:
                with app.app_context():
                    # This should automatically recover the connection
                    recovered_song = db.session.get(Song, song_id)
                    assert recovered_song is not None
                    assert recovered_song.title == 'Connection Test Song'
                    
                    # Should be able to perform operations normally
                    recovered_song.title = 'Updated After Recovery'
                    db.session.commit()
                    
                    # Verify the update worked
                    final_check = db.session.get(Song, song_id)
                    assert final_check.title == 'Updated After Recovery'
                    
            except Exception as e:
                pytest.fail(f"Database connection should recover automatically: {e}") 