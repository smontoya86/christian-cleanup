import pytest
from unittest.mock import Mock, patch
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.models.models import Song, AnalysisResult, Playlist, PlaylistSong
from app import db
from datetime import datetime


class TestUnifiedAnalysisServiceProgressTracking:
    """Test progress tracking functionality for playlist analysis"""
    
    def test_playlist_analysis_progress_tracking(self, app, db_session, sample_user):
        """Test that playlist analysis properly tracks progress through status transitions"""
        with app.app_context():
            # Create test playlist and songs
            playlist = Playlist(
                name="Test Playlist",
                spotify_id="test_playlist_123",
                owner_id=sample_user.id
            )
            db_session.add(playlist)
            db_session.commit()
            
            # Create test songs
            songs = []
            for i in range(3):
                song = Song(
                    title=f"Test Song {i+1}",
                    artist=f"Test Artist {i+1}",
                    spotify_id=f"test_song_{i+1}",
                    lyrics=f"Test lyrics for song {i+1} with positive content"
                )
                db_session.add(song)
                songs.append(song)
            
            db_session.commit()
            
            # Add songs to playlist
            for i, song in enumerate(songs):
                playlist_song = PlaylistSong(
                    playlist_id=playlist.id,
                    song_id=song.id,
                    track_position=i
                )
                db_session.add(playlist_song)
            
            db_session.commit()
            
            # Step 1: Create pending analysis records (simulating AJAX route behavior)
            pending_analyses = []
            for song in songs:
                analysis = AnalysisResult(
                    song_id=song.id,
                    status='pending',
                    created_at=datetime.utcnow()
                )
                db_session.add(analysis)
                pending_analyses.append(analysis)
            
            db_session.commit()
            
            # Verify all analyses start as pending
            for analysis in pending_analyses:
                db_session.refresh(analysis)
                assert analysis.status == 'pending'
            
            # Step 2: Process each song with proper status tracking
            service = UnifiedAnalysisService()
            
            for i, (song, analysis) in enumerate(zip(songs, pending_analyses)):
                # Update to in_progress (simulating background thread)
                analysis.status = 'in_progress'
                db_session.commit()
                
                # Verify status is in_progress before analysis
                db_session.refresh(analysis)
                assert analysis.status == 'in_progress'
                
                # Call the analysis service with existing pending record
                service.enqueue_analysis_job(song.id, user_id=sample_user.id)
                
                # Verify the analysis was completed
                db_session.refresh(analysis)
                assert analysis.status == 'completed'
                assert analysis.score is not None
                assert analysis.concern_level is not None
                
                # Verify other songs are still in their expected states
                for j, other_analysis in enumerate(pending_analyses):
                    db_session.refresh(other_analysis)
                    if j < i:
                        # Already processed songs should be completed
                        assert other_analysis.status == 'completed'
                    elif j == i:
                        # Current song should be completed
                        assert other_analysis.status == 'completed'
                    else:
                        # Future songs should still be pending
                        assert other_analysis.status == 'pending'
    
    def test_enqueue_analysis_respects_existing_pending_status(self, app, db_session, sample_user):
        """Test that enqueue_analysis_job respects existing pending analysis records"""
        with app.app_context():
            # Create test song
            song = Song(
                title="Test Song",
                artist="Test Artist",
                spotify_id="test_song_123",
                lyrics="Test lyrics with positive content"
            )
            db_session.add(song)
            db_session.commit()
            
            # Create pending analysis record first
            pending_analysis = AnalysisResult(
                song_id=song.id,
                status='pending',
                created_at=datetime.utcnow()
            )
            db_session.add(pending_analysis)
            db_session.commit()
            
            # Get the analysis ID for tracking
            analysis_id = pending_analysis.id
            
            # Call enqueue_analysis_job
            service = UnifiedAnalysisService()
            job = service.enqueue_analysis_job(song.id, user_id=sample_user.id)
            
            # Verify the existing analysis record was updated, not replaced
            updated_analysis = AnalysisResult.query.get(analysis_id)
            assert updated_analysis is not None
            assert updated_analysis.status == 'completed'
            assert updated_analysis.score is not None
            
            # Verify no duplicate analysis records were created
            all_analyses = AnalysisResult.query.filter_by(song_id=song.id).all()
            assert len(all_analyses) == 1
            assert all_analyses[0].id == analysis_id
    
    def test_enqueue_analysis_creates_new_record_when_none_exists(self, app, db_session, sample_user):
        """Test that enqueue_analysis_job creates new record when none exists"""
        with app.app_context():
            # Create test song
            song = Song(
                title="Test Song",
                artist="Test Artist",
                spotify_id="test_song_123",
                lyrics="Test lyrics with positive content"
            )
            db_session.add(song)
            db_session.commit()
            
            # Verify no analysis exists
            existing_analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
            assert existing_analysis is None
            
            # Call enqueue_analysis_job
            service = UnifiedAnalysisService()
            job = service.enqueue_analysis_job(song.id, user_id=sample_user.id)
            
            # Verify analysis record was created and completed
            analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
            assert analysis is not None
            assert analysis.status == 'completed'
            assert analysis.score is not None
            assert analysis.concern_level is not None 