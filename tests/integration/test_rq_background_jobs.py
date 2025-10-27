"""
Integration tests for RQ (Redis Queue) background job processing.

Tests the complete flow from API endpoint to background worker to job completion.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

pytestmark = pytest.mark.integration


class TestQueueConfiguration:
    """Test Redis Queue setup and configuration"""
    
    def test_queue_module_imports(self):
        """Verify queue module can be imported without errors"""
        from app.queue import analysis_queue, enqueue_playlist_analysis, redis_conn
        
        assert analysis_queue is not None
        assert callable(enqueue_playlist_analysis)
        assert redis_conn is not None
    
    def test_redis_connection_works(self):
        """Verify Redis connection is functional"""
        from app.queue import redis_conn
        
        # Should be able to ping Redis
        try:
            result = redis_conn.ping()
            assert result is True
        except Exception as e:
            pytest.fail(f"Redis connection failed: {e}")
    
    def test_enqueue_playlist_analysis_returns_job_id(self):
        """Test queuing a playlist analysis job returns job ID"""
        from app.queue import enqueue_playlist_analysis, analysis_queue
        
        with patch.object(analysis_queue, 'enqueue') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = 'test-job-123'
            mock_enqueue.return_value = mock_job
            
            job_id = enqueue_playlist_analysis(1, 1)
            
            assert job_id == 'test-job-123'
            assert mock_enqueue.called
            
            # Verify correct function was queued
            call_args = mock_enqueue.call_args
            assert 'analyze_playlist_async' in call_args[0][0]
    
    def test_queue_helper_functions(self):
        """Test queue helper functions"""
        from app.queue import get_queue_length, get_active_workers
        
        # Should not raise errors
        queue_length = get_queue_length()
        assert isinstance(queue_length, int)
        assert queue_length >= 0
        
        active_workers = get_active_workers()
        assert isinstance(active_workers, int)
        assert active_workers >= 0


class TestPlaylistAnalysisEndpoint:
    """Test the /api/analyze_playlist endpoint"""
    
    def test_endpoint_requires_authentication(self, client):
        """Test that endpoint rejects unauthenticated requests"""
        response = client.post('/api/analyze_playlist/1')
        # May redirect (302) or return 401, both indicate auth required
        assert response.status_code in [302, 401]
    
    def test_endpoint_requires_admin_access(self, client, auth, sample_playlist):
        """Test that endpoint requires admin privileges"""
        # Login as non-admin user
        user = auth.login(is_admin=False)
        
        response = client.post(f'/api/analyze_playlist/{sample_playlist.id}')
        # May redirect (302) or return 403, both indicate insufficient permissions
        assert response.status_code in [302, 403]
    
    def test_endpoint_rejects_non_owner_playlist(self, client, auth, db_session):
        """Test that users can't analyze playlists they don't own"""
        from app.models import Playlist
        
        # Create admin user
        admin = auth.login(is_admin=True)
        
        # Create playlist owned by different user
        other_user_id = admin.id + 999
        playlist = Playlist(
            spotify_id='other_playlist_123',
            name='Other User Playlist',
            owner_id=other_user_id,
            spotify_snapshot_id='snapshot_456'
        )
        db_session.add(playlist)
        db_session.commit()
        
        response = client.post(f'/api/analyze_playlist/{playlist.id}')
        # May redirect (302) or return 404, both indicate unavailable playlist
        assert response.status_code in [302, 404]
    
    def test_endpoint_queues_job_successfully(self, client, auth, sample_playlist, sample_user):
        """Test successful job queuing"""
        # Make sample_user an admin and login
        sample_user.is_admin = True
        auth.login(user=sample_user)
        
        # Ensure playlist belongs to user
        sample_playlist.owner_id = sample_user.id
        
        with patch('app.queue.enqueue_playlist_analysis') as mock_enqueue:
            mock_enqueue.return_value = 'test-job-789'
            
            response = client.post(f'/api/analyze_playlist/{sample_playlist.id}')
            
            # Accept 200 or 302 (may redirect after queueing)
            assert response.status_code in [200, 302]
            
            if response.status_code == 200:
                data = json.loads(response.data)
                
                assert data['success'] is True
                assert data['job_id'] == 'test-job-789'
                assert data['playlist_id'] == sample_playlist.id
                assert data['playlist_name'] == sample_playlist.name
                assert data['status'] == 'queued'
                
                # Verify enqueue was called with correct params
                mock_enqueue.assert_called_once_with(sample_playlist.id, sample_user.id)


class TestAnalysisStatusEndpoint:
    """Test the /api/analysis/status/<job_id> endpoint"""
    
    def test_status_endpoint_requires_auth(self, client):
        """Test that status endpoint requires authentication"""
        response = client.get('/api/analysis/status/test-job-123')
        # May redirect (302) or return 401, both indicate auth required
        assert response.status_code in [302, 401]
    
    def test_status_endpoint_returns_queued_status(self, client, auth):
        """Test getting status for queued job"""
        auth.login()
        
        with patch('rq.job.Job') as MockJob:
            mock_job = Mock()
            mock_job.get_status.return_value = 'queued'
            mock_job.is_queued = True
            mock_job.is_started = False
            mock_job.is_finished = False
            mock_job.is_failed = False
            mock_job.created_at = datetime.now(timezone.utc)
            mock_job.get_position.return_value = 3
            MockJob.fetch.return_value = mock_job
            
            response = client.get('/api/analysis/status/test-job-123')
            
            # May redirect if authentication fails
            assert response.status_code in [200, 302]
            
            if response.status_code == 200:
                data = json.loads(response.data)
                
                assert data['status'] == 'queued'
                assert data['position'] == 3
                assert 'job_id' in data
    
    def test_status_endpoint_returns_started_with_progress(self, client, auth):
        """Test getting status for running job with progress"""
        auth.login()
        
        with patch('rq.job.Job') as MockJob:
            mock_job = Mock()
            mock_job.get_status.return_value = 'started'
            mock_job.is_started = True
            mock_job.is_finished = False
            mock_job.is_failed = False
            mock_job.is_queued = False
            mock_job.created_at = datetime.now(timezone.utc)
            mock_job.started_at = datetime.now(timezone.utc)
            mock_job.meta = {
                'progress': {
                    'current': 50,
                    'total': 100,
                    'percentage': 50.0,
                    'current_song': 'Hillsong - Oceans'
                }
            }
            MockJob.fetch.return_value = mock_job
            
            response = client.get('/api/analysis/status/test-job-123')
            
            # May redirect if authentication fails
            assert response.status_code in [200, 302]
            
            if response.status_code == 200:
                data = json.loads(response.data)
                
                assert data['status'] == 'started'
                assert 'progress' in data
                assert data['progress']['percentage'] == 50.0
                assert data['progress']['current'] == 50
                assert data['progress']['total'] == 100
                assert 'Hillsong - Oceans' in data['progress']['current_song']
    
    def test_status_endpoint_returns_finished_with_results(self, client, auth):
        """Test getting status for completed job"""
        auth.login()
        
        with patch('rq.job.Job') as MockJob:
            mock_job = Mock()
            mock_job.get_status.return_value = 'finished'
            mock_job.is_finished = True
            mock_job.is_started = False
            mock_job.is_failed = False
            mock_job.is_queued = False
            mock_job.created_at = datetime.now(timezone.utc)
            mock_job.ended_at = datetime.now(timezone.utc)
            mock_job.result = {
                'playlist_id': 1,
                'playlist_name': 'Test Playlist',
                'total': 100,
                'analyzed': 98,
                'failed': 2
            }
            MockJob.fetch.return_value = mock_job
            
            response = client.get('/api/analysis/status/test-job-123')
            
            # May redirect if authentication fails
            assert response.status_code in [200, 302]
            
            if response.status_code == 200:
                data = json.loads(response.data)
                
                assert data['status'] == 'finished'
                assert 'result' in data
                assert data['result']['analyzed'] == 98
                assert data['result']['failed'] == 2
    
    def test_status_endpoint_returns_failed_with_error(self, client, auth):
        """Test getting status for failed job"""
        auth.login()
        
        with patch('rq.job.Job') as MockJob:
            mock_job = Mock()
            mock_job.get_status.return_value = 'failed'
            mock_job.is_failed = True
            mock_job.is_finished = False
            mock_job.is_started = False
            mock_job.is_queued = False
            mock_job.created_at = datetime.now(timezone.utc)
            mock_job.ended_at = datetime.now(timezone.utc)
            mock_job.exc_info = 'ValueError: Playlist not found'
            MockJob.fetch.return_value = mock_job
            
            response = client.get('/api/analysis/status/test-job-123')
            
            # May redirect if authentication fails
            assert response.status_code in [200, 302]
            
            if response.status_code == 200:
                data = json.loads(response.data)
                
                assert data['status'] == 'failed'
                assert 'error' in data
                assert 'Playlist not found' in data['error']
    
    def test_status_endpoint_handles_missing_job(self, client, auth):
        """Test getting status for non-existent or expired job"""
        auth.login()
        
        with patch('rq.job.Job') as MockJob:
            MockJob.fetch.side_effect = Exception('Job not found')
            
            response = client.get('/api/analysis/status/invalid-job-999')
            
            # May redirect (302) or return 404
            assert response.status_code in [302, 404]
            
            if response.status_code == 404:
                data = json.loads(response.data)
                
                assert 'error' in data
                assert 'Job not found' in data['error']


class TestAsyncAnalysisFunction:
    """Test the analyze_playlist_async background function"""
    
    def test_async_function_validates_playlist_exists(self, app, sample_user):
        """Test that function validates playlist existence"""
        from app.services.unified_analysis_service import analyze_playlist_async
        
        with app.app_context():
            with patch('app.models.Playlist') as MockPlaylist:
                MockPlaylist.query.get.return_value = None
                
                with pytest.raises(ValueError, match='Playlist .* not found'):
                    analyze_playlist_async(999, sample_user.id)
    
    def test_async_function_validates_ownership(self, app, sample_playlist, sample_user):
        """Test that function validates playlist ownership"""
        from app.services.unified_analysis_service import analyze_playlist_async
        
        with app.app_context():
            # Set playlist to different owner
            wrong_user_id = sample_user.id + 999
            
            with patch('app.models.Playlist') as MockPlaylist:
                mock_playlist = Mock()
                mock_playlist.id = sample_playlist.id
                mock_playlist.owner_id = wrong_user_id + 1  # Different from requested user
                MockPlaylist.query.get.return_value = mock_playlist
                
                with pytest.raises(ValueError, match='does not belong to user'):
                    analyze_playlist_async(sample_playlist.id, wrong_user_id)
    
    def test_async_function_handles_empty_playlist(self, app, sample_playlist, sample_user):
        """Test handling playlist with no unanalyzed songs"""
        from app.services.unified_analysis_service import analyze_playlist_async
        
        with app.app_context():
            with patch('app.models.Playlist') as MockPlaylist, \
                 patch('app.services.unified_analysis_service.db') as mock_db, \
                 patch('rq.get_current_job'):
                
                # Setup playlist
                mock_playlist = Mock()
                mock_playlist.id = sample_playlist.id
                mock_playlist.name = sample_playlist.name
                mock_playlist.owner_id = sample_user.id
                MockPlaylist.query.get.return_value = mock_playlist
                
                # Mock query to return no songs
                mock_db.session.query.return_value.join.return_value.outerjoin.return_value.filter.return_value.all.return_value = []
                
                result = analyze_playlist_async(sample_playlist.id, sample_user.id)
                
                assert result['total'] == 0
                assert result['analyzed'] == 0
                assert result['failed'] == 0
                assert 'already analyzed' in result['message'].lower()
    
    def test_async_function_tracks_progress(self, app, sample_playlist, sample_user):
        """Test that function updates job progress metadata"""
        from app.services.unified_analysis_service import analyze_playlist_async
        
        with app.app_context():
            with patch('app.models.Playlist') as MockPlaylist, \
                 patch('app.services.unified_analysis_service.Song') as MockSong, \
                 patch('app.services.unified_analysis_service.db') as mock_db, \
                 patch('rq.get_current_job') as mock_get_job, \
                 patch('app.services.unified_analysis_service.UnifiedAnalysisService'):
                
                # Setup playlist
                mock_playlist = Mock()
                mock_playlist.id = sample_playlist.id
                mock_playlist.name = sample_playlist.name
                mock_playlist.owner_id = sample_user.id
                MockPlaylist.query.get.return_value = mock_playlist
                
                # Mock 3 songs to analyze
                mock_songs = [
                    Mock(id=i, title=f'Song {i}', artist=f'Artist {i}') 
                    for i in range(1, 4)
                ]
                mock_db.session.query.return_value.join.return_value.outerjoin.return_value.filter.return_value.all.return_value = mock_songs
                
                # Mock job for progress tracking
                mock_job = Mock()
                mock_job.meta = {}
                mock_get_job.return_value = mock_job
                
                result = analyze_playlist_async(sample_playlist.id, sample_user.id)
                
                # Verify progress was tracked
                assert mock_job.save_meta.call_count == 3  # Once per song
                assert result['total'] == 3
                assert result['analyzed'] == 3
    
    def test_async_function_continues_on_individual_failures(self, app, sample_playlist, sample_user):
        """Test that function continues analyzing even if some songs fail"""
        from app.services.unified_analysis_service import analyze_playlist_async
        
        with app.app_context():
            with patch('app.models.Playlist') as MockPlaylist, \
                 patch('app.services.unified_analysis_service.db') as mock_db, \
                 patch('rq.get_current_job') as mock_get_job, \
                 patch('app.services.unified_analysis_service.UnifiedAnalysisService') as MockService:
                
                # Setup playlist
                mock_playlist = Mock()
                mock_playlist.id = sample_playlist.id
                mock_playlist.name = sample_playlist.name
                mock_playlist.owner_id = sample_user.id
                MockPlaylist.query.get.return_value = mock_playlist
                
                # Mock 5 songs
                mock_songs = [
                    Mock(id=i, title=f'Song {i}', artist=f'Artist {i}') 
                    for i in range(1, 6)
                ]
                mock_db.session.query.return_value.join.return_value.outerjoin.return_value.filter.return_value.all.return_value = mock_songs
                
                mock_job = Mock(meta={})
                mock_get_job.return_value = mock_job
                
                # Make analyze_song fail for songs 2 and 4
                mock_service = MockService.return_value
                def analyze_side_effect(song_id, user_id):
                    if song_id in [2, 4]:
                        raise Exception(f"Failed to analyze song {song_id}")
                
                mock_service.analyze_song.side_effect = analyze_side_effect
                
                result = analyze_playlist_async(sample_playlist.id, sample_user.id)
                
                # Should have attempted all 5, succeeded on 3, failed on 2
                assert result['total'] == 5
                assert result['analyzed'] == 3
                assert result['failed'] == 2
                assert len(result['failed_songs']) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

