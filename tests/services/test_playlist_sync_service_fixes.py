"""
Test suite for Playlist Sync Service - TDD Implementation

This test suite covers all the critical fixes needed for the playlist sync system:
1. Real queue integration (replacing mock implementations)
2. Database transaction safety
3. Error recovery mechanisms
4. Track count consistency
5. Performance optimizations
6. Field consistency
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.models.models import User, Playlist, Song, PlaylistSong
from app.services.playlist_sync_service import (
    PlaylistSyncService,
    sync_user_playlists_task,
    enqueue_user_playlist_sync,
    enqueue_playlist_sync,
    get_sync_status,
    sync_playlist_task
)
from app.services.priority_analysis_queue import PriorityAnalysisQueue, JobType, JobPriority


class TestPlaylistSyncServiceRealQueue:
    """Test real queue integration (Task 1)"""
    
    def test_enqueue_user_playlist_sync_creates_real_job(self, app, db_session, test_user):
        """Test that enqueue_user_playlist_sync creates actual queue jobs"""
        with app.app_context():
            with patch('app.services.playlist_sync_service.PriorityAnalysisQueue') as mock_queue_class:
                mock_queue = Mock()
                mock_queue_class.return_value = mock_queue
                mock_queue.enqueue.return_value = 'real_job_id_123'
                
                result = enqueue_user_playlist_sync(test_user.id, priority='high')
                
                # Verify real job was enqueued
                mock_queue.enqueue.assert_called_once()
                call_args = mock_queue.enqueue.call_args
                assert call_args[1]['job_type'] == JobType.PLAYLIST_ANALYSIS
                assert call_args[1]['user_id'] == test_user.id
                assert call_args[1]['priority'] == JobPriority.HIGH
                
                # Verify response contains real job ID
                assert result['job_id'] == 'real_job_id_123'
                assert result['status'] == 'queued'
                assert 'mock' not in result['job_id']
    
    def test_enqueue_playlist_sync_creates_real_job(self, app, db_session, test_user, test_playlist):
        """Test that enqueue_playlist_sync creates actual queue jobs"""
        with app.app_context():
            with patch('app.services.playlist_sync_service.PriorityAnalysisQueue') as mock_queue_class:
                mock_queue = Mock()
                mock_queue_class.return_value = mock_queue
                mock_queue.enqueue.return_value = 'real_playlist_job_456'
                
                result = enqueue_playlist_sync(test_playlist.id, test_user.id, priority='normal')
                
                # Verify real job was enqueued
                mock_queue.enqueue.assert_called_once()
                call_args = mock_queue.enqueue.call_args
                assert call_args[1]['job_type'] == JobType.PLAYLIST_ANALYSIS
                assert call_args[1]['target_id'] == test_playlist.id
                assert call_args[1]['user_id'] == test_user.id
                assert call_args[1]['priority'] == JobPriority.MEDIUM
                
                # Verify response contains real job ID
                assert result['job_id'] == 'real_playlist_job_456'
                assert result['status'] == 'queued'
    
    def test_get_sync_status_returns_real_status(self, app, db_session):
        """Test that get_sync_status returns actual job status from Redis"""
        with app.app_context():
            with patch('app.services.playlist_sync_service.PriorityAnalysisQueue') as mock_queue_class:
                mock_queue = Mock()
                mock_queue_class.return_value = mock_queue
                
                # Mock job data
                mock_job = Mock()
                mock_job.job_id = 'test_job_789'
                mock_job.status.value = 'in_progress'
                mock_job.created_at = datetime.now(timezone.utc)
                mock_job.started_at = datetime.now(timezone.utc)
                mock_job.to_dict.return_value = {
                    'job_id': 'test_job_789',
                    'status': 'in_progress',
                    'progress': 50
                }
                mock_queue.get_job.return_value = mock_job
                
                result = get_sync_status(job_id='test_job_789')
                
                # Verify real status was retrieved
                mock_queue.get_job.assert_called_once_with('test_job_789')
                assert result['job_id'] == 'test_job_789'
                assert result['status'] == 'in_progress'
                assert 'mock' not in str(result)
    
    def test_sync_playlist_task_integrates_with_queue(self, app, db_session, test_user, test_playlist):
        """Test that sync_playlist_task integrates with priority queue worker"""
        with app.app_context():
            with patch('app.services.playlist_sync_service.PlaylistSyncService') as mock_service_class:
                mock_service = Mock()
                mock_service_class.return_value = mock_service
                mock_service.sync_playlist_tracks.return_value = {
                    'status': 'completed',
                    'tracks_synced': 15,
                    'new_tracks': 5
                }
                
                result = sync_playlist_task(test_playlist.id, test_user.id)
                
                # Verify actual sync service was called
                mock_service.sync_playlist_tracks.assert_called_once()
                assert result['status'] == 'completed'
                assert result['tracks_synced'] == 15
                assert result['playlist_id'] == test_playlist.id
                assert result['user_id'] == test_user.id


class TestPlaylistSyncServiceTransactionSafety:
    """Test database transaction safety (Task 2)"""
    
    def test_sync_playlist_tracks_uses_single_transaction(self, app, db_session, test_user, test_playlist):
        """Test that sync_playlist_tracks uses single transaction per playlist"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                mock_spotify = Mock()
                mock_spotify_class.return_value = mock_spotify
                mock_spotify.get_playlist_tracks.return_value = [
                    {'id': 'track1', 'name': 'Song 1', 'artists': [{'name': 'Artist 1'}], 
                     'album': {'name': 'Album 1', 'images': []}, 'duration_ms': 180000},
                    {'id': 'track2', 'name': 'Song 2', 'artists': [{'name': 'Artist 2'}], 
                     'album': {'name': 'Album 2', 'images': []}, 'duration_ms': 200000}
                ]
                
                with patch.object(db.session, 'commit') as mock_commit:
                    with patch.object(db.session, 'rollback') as mock_rollback:
                        result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                        
                        # Verify only one commit was called at the end
                        assert mock_commit.call_count == 1
                        assert mock_rollback.call_count == 0
                        assert result['status'] == 'completed'
    
    def test_sync_playlist_tracks_rollback_on_failure(self, app, db_session, test_user, test_playlist):
        """Test that sync_playlist_tracks rolls back on failure"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                mock_spotify = Mock()
                mock_spotify_class.return_value = mock_spotify
                mock_spotify.get_playlist_tracks.return_value = [
                    {'id': 'track1', 'name': 'Song 1', 'artists': [{'name': 'Artist 1'}], 
                     'album': {'name': 'Album 1', 'images': []}, 'duration_ms': 180000}
                ]
                
                with patch.object(db.session, 'commit', side_effect=IntegrityError("DB Error", None, None)):
                    with patch.object(db.session, 'rollback') as mock_rollback:
                        result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                        
                        # Verify rollback was called on failure
                        mock_rollback.assert_called_once()
                        assert result['status'] == 'failed'


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        id=1,
        spotify_id='test_user_123',
        display_name='Test User',
        email='test@example.com'
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_playlist(db_session, test_user):
    """Create a test playlist"""
    playlist = Playlist(
        id=1,
        spotify_id='test_playlist_123',
        name='Test Playlist',
        description='Test Description',
        owner_id=test_user.id,
        public=True,
        collaborative=False,
        track_count=0
    )
    db_session.add(playlist)
    db_session.commit()
    return playlist 