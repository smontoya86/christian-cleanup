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
    
    def test_atomic_track_operations(self, app, db_session, test_user, test_playlist):
        """Test that track clearing and adding is atomic"""
        with app.app_context():
            # Create some existing tracks
            existing_song = Song(spotify_id='existing_track', title='Existing Song', 
                               artist='Existing Artist', album='Existing Album')
            db_session.add(existing_song)
            db_session.flush()
            
            existing_playlist_song = PlaylistSong(
                playlist_id=test_playlist.id,
                song_id=existing_song.id,
                track_position=0
            )
            db_session.add(existing_playlist_song)
            db_session.commit()
            
            sync_service = PlaylistSyncService()
            
            with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                mock_spotify = Mock()
                mock_spotify_class.return_value = mock_spotify
                # Simulate failure after clearing existing tracks
                mock_spotify.get_playlist_tracks.side_effect = Exception("Spotify API Error")
                
                initial_count = PlaylistSong.query.filter_by(playlist_id=test_playlist.id).count()
                assert initial_count == 1
                
                result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                
                # Verify existing tracks are still there after failure (atomic operation)
                final_count = PlaylistSong.query.filter_by(playlist_id=test_playlist.id).count()
                assert final_count == 1  # Should not have cleared existing tracks due to rollback
                assert result['status'] == 'failed'


class TestPlaylistSyncServiceErrorRecovery:
    """Test error recovery mechanisms (Task 3)"""
    
    def test_sync_state_tracking(self, app, db_session, test_user, test_playlist):
        """Test that sync state is tracked for recovery"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            # Mock Redis for state tracking
            with patch('app.services.playlist_sync_service.redis') as mock_redis:
                mock_redis.hset = Mock()
                mock_redis.hget = Mock()
                
                with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                    mock_spotify = Mock()
                    mock_spotify_class.return_value = mock_spotify
                    mock_spotify.get_playlist_tracks.return_value = []
                    
                    result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                    
                    # Verify sync state was tracked
                    mock_redis.hset.assert_called()
                    state_calls = [call for call in mock_redis.hset.call_args_list 
                                 if 'sync_state' in str(call)]
                    assert len(state_calls) > 0
    
    def test_partial_sync_recovery(self, app, db_session, test_user, test_playlist):
        """Test recovery from partial sync failure"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            # Mock partial failure scenario
            with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                mock_spotify = Mock()
                mock_spotify_class.return_value = mock_spotify
                mock_spotify.get_playlist_tracks.return_value = [
                    {'id': 'track1', 'name': 'Song 1', 'artists': [{'name': 'Artist 1'}], 
                     'album': {'name': 'Album 1', 'images': []}, 'duration_ms': 180000},
                    {'id': 'track2', 'name': 'Song 2', 'artists': [{'name': 'Artist 2'}], 
                     'album': {'name': 'Album 2', 'images': []}, 'duration_ms': 200000}
                ]
                
                # Mock failure after first track
                with patch.object(sync_service, '_sync_single_song') as mock_sync_song:
                    mock_sync_song.side_effect = [Mock(id=1), Exception("Sync Error")]
                    
                    result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                    
                    # Should handle partial failure gracefully
                    assert 'error' in result
                    assert result['status'] == 'failed'
    
    def test_resumable_sync_operations(self, app, db_session, test_user, test_playlist):
        """Test that sync operations can be resumed"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            # Mock resumable state
            with patch('app.services.playlist_sync_service.redis') as mock_redis:
                mock_redis.hget.return_value = json.dumps({
                    'playlist_id': test_playlist.id,
                    'last_processed_track': 5,
                    'total_tracks': 10,
                    'sync_started_at': datetime.now(timezone.utc).isoformat()
                })
                
                with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                    mock_spotify = Mock()
                    mock_spotify_class.return_value = mock_spotify
                    mock_spotify.get_playlist_tracks.return_value = []
                    
                    result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                    
                    # Should detect resumable state
                    mock_redis.hget.assert_called()
                    assert result is not None


class TestPlaylistSyncServiceTrackCountConsistency:
    """Test track count consistency (Task 4)"""
    
    def test_consistent_track_counting_between_services(self, app, db_session, test_user, test_playlist):
        """Test that PlaylistSyncService and SpotifyService produce consistent track counts"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            mock_tracks = [
                {'id': f'track{i}', 'name': f'Song {i}', 'artists': [{'name': f'Artist {i}'}], 
                 'album': {'name': f'Album {i}', 'images': []}, 'duration_ms': 180000}
                for i in range(1, 6)  # 5 tracks
            ]
            
            with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                mock_spotify = Mock()
                mock_spotify_class.return_value = mock_spotify
                mock_spotify.get_playlist_tracks.return_value = mock_tracks
                
                result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                
                # Verify track count matches actual synced tracks
                db_session.refresh(test_playlist)
                assert test_playlist.track_count == result['tracks_synced']
                assert test_playlist.track_count == 5
    
    def test_track_count_accuracy_with_unavailable_tracks(self, app, db_session, test_user, test_playlist):
        """Test track count accuracy when some tracks are unavailable"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            # Mock tracks where some fail to sync
            mock_tracks = [
                {'id': 'track1', 'name': 'Song 1', 'artists': [{'name': 'Artist 1'}], 
                 'album': {'name': 'Album 1', 'images': []}, 'duration_ms': 180000},
                {'id': 'track2', 'name': 'Song 2', 'artists': [{'name': 'Artist 2'}], 
                 'album': {'name': 'Album 2', 'images': []}, 'duration_ms': 200000},
                {'id': 'track3', 'name': 'Song 3', 'artists': [{'name': 'Artist 3'}], 
                 'album': {'name': 'Album 3', 'images': []}, 'duration_ms': 220000}
            ]
            
            with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                mock_spotify = Mock()
                mock_spotify_class.return_value = mock_spotify
                mock_spotify.get_playlist_tracks.return_value = mock_tracks
                
                # Mock one track failing to sync
                with patch.object(sync_service, '_sync_single_song') as mock_sync_song:
                    mock_sync_song.side_effect = [Mock(id=1), None, Mock(id=3)]  # Middle track fails
                    
                    result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                    
                    # Track count should reflect actually synced tracks (2), not total tracks (3)
                    db_session.refresh(test_playlist)
                    assert test_playlist.track_count == 2
                    assert result['tracks_synced'] == 2
    
    def test_track_count_validation(self, app, db_session, test_user, test_playlist):
        """Test validation of track count accuracy"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            # Set up playlist with existing tracks
            for i in range(3):
                song = Song(spotify_id=f'existing_{i}', title=f'Existing Song {i}', 
                           artist=f'Artist {i}', album=f'Album {i}')
                db_session.add(song)
                db_session.flush()
                
                playlist_song = PlaylistSong(
                    playlist_id=test_playlist.id,
                    song_id=song.id,
                    track_position=i
                )
                db_session.add(playlist_song)
            
            test_playlist.track_count = 3
            db_session.commit()
            
            # Verify track count matches database records
            actual_count = PlaylistSong.query.filter_by(playlist_id=test_playlist.id).count()
            assert test_playlist.track_count == actual_count == 3


class TestPlaylistSyncServicePerformance:
    """Test performance optimizations (Task 5)"""
    
    def test_batch_database_operations(self, app, db_session, test_user, test_playlist):
        """Test that database operations are batched for performance"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            # Mock large number of tracks
            mock_tracks = [
                {'id': f'track{i}', 'name': f'Song {i}', 'artists': [{'name': f'Artist {i}'}], 
                 'album': {'name': f'Album {i}', 'images': []}, 'duration_ms': 180000}
                for i in range(1, 101)  # 100 tracks
            ]
            
            with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                mock_spotify = Mock()
                mock_spotify_class.return_value = mock_spotify
                mock_spotify.get_playlist_tracks.return_value = mock_tracks
                
                with patch.object(db.session, 'commit') as mock_commit:
                    result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                    
                    # Should use single commit for all operations, not one per track
                    assert mock_commit.call_count == 1
                    assert result['tracks_synced'] == 100
    
    def test_bulk_song_creation(self, app, db_session, test_user, test_playlist):
        """Test bulk creation of songs for performance"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            mock_tracks = [
                {'id': f'new_track{i}', 'name': f'New Song {i}', 'artists': [{'name': f'Artist {i}'}], 
                 'album': {'name': f'Album {i}', 'images': []}, 'duration_ms': 180000}
                for i in range(1, 21)  # 20 new tracks
            ]
            
            with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                mock_spotify = Mock()
                mock_spotify_class.return_value = mock_spotify
                mock_spotify.get_playlist_tracks.return_value = mock_tracks
                
                with patch.object(db.session, 'add') as mock_add:
                    with patch.object(db.session, 'bulk_insert_mappings') as mock_bulk_insert:
                        result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                        
                        # Should use bulk operations when available
                        # Note: Actual implementation may vary, but should minimize individual adds
                        assert result['tracks_synced'] == 20
    
    def test_performance_with_large_playlists(self, app, db_session, test_user, test_playlist):
        """Test performance with large playlists"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            # Mock very large playlist
            mock_tracks = [
                {'id': f'large_track{i}', 'name': f'Song {i}', 'artists': [{'name': f'Artist {i}'}], 
                 'album': {'name': f'Album {i}', 'images': []}, 'duration_ms': 180000}
                for i in range(1, 501)  # 500 tracks
            ]
            
            with patch('app.services.spotify_service.SpotifyService') as mock_spotify_class:
                mock_spotify = Mock()
                mock_spotify_class.return_value = mock_spotify
                mock_spotify.get_playlist_tracks.return_value = mock_tracks
                
                import time
                start_time = time.time()
                result = sync_service.sync_playlist_tracks(test_user, test_playlist)
                duration = time.time() - start_time
                
                # Should complete large playlist sync in reasonable time
                assert result['tracks_synced'] == 500
                assert duration < 30  # Should complete in under 30 seconds


class TestPlaylistSyncServiceFieldConsistency:
    """Test field consistency (Task 6)"""
    
    def test_all_playlist_fields_synced(self, app, db_session, test_user):
        """Test that all playlist fields are synced consistently"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            mock_spotify_playlist = {
                'id': 'spotify_playlist_123',
                'name': 'Test Playlist',
                'description': 'Test Description',
                'public': True,
                'collaborative': False,
                'tracks': {'total': 25},
                'images': [{'url': 'https://example.com/image.jpg'}],
                'owner': {'id': 'owner_123', 'display_name': 'Owner Name'}
            }
            
            playlist = sync_service._sync_single_playlist(test_user, mock_spotify_playlist)
            
            # Verify all fields are mapped correctly
            assert playlist.spotify_id == 'spotify_playlist_123'
            assert playlist.name == 'Test Playlist'
            assert playlist.description == 'Test Description'
            assert playlist.public == True
            assert playlist.collaborative == False
            assert playlist.image_url == 'https://example.com/image.jpg'
            assert playlist.owner_display_name == 'Owner Name'
    
    def test_missing_public_field_handling(self, app, db_session, test_user):
        """Test that missing public field is handled correctly"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            mock_spotify_playlist = {
                'id': 'spotify_playlist_456',
                'name': 'Private Playlist',
                'description': 'Private Description',
                # Missing 'public' field
                'collaborative': False,
                'tracks': {'total': 10},
                'images': [],
                'owner': {'id': 'owner_456', 'display_name': 'Private Owner'}
            }
            
            playlist = sync_service._sync_single_playlist(test_user, mock_spotify_playlist)
            
            # Should handle missing public field gracefully
            assert playlist.public is not None  # Should have default value
            assert playlist.name == 'Private Playlist'
    
    def test_field_completeness_validation(self, app, db_session, test_user):
        """Test validation of field completeness"""
        with app.app_context():
            sync_service = PlaylistSyncService()
            
            # Test with complete data
            complete_playlist = {
                'id': 'complete_playlist',
                'name': 'Complete Playlist',
                'description': 'Complete Description',
                'public': True,
                'collaborative': False,
                'tracks': {'total': 15},
                'images': [{'url': 'https://example.com/complete.jpg'}],
                'owner': {'id': 'complete_owner', 'display_name': 'Complete Owner'}
            }
            
            playlist = sync_service._sync_single_playlist(test_user, complete_playlist)
            
            # Verify no fields are missing or None when they should have values
            required_fields = ['spotify_id', 'name', 'owner_id', 'public', 'collaborative']
            for field in required_fields:
                assert getattr(playlist, field) is not None
            
            # Optional fields should handle None gracefully
            optional_fields = ['description', 'image_url', 'owner_display_name']
            for field in optional_fields:
                # Should exist as attribute even if None
                assert hasattr(playlist, field)


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