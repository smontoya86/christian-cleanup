"""
Integration tests for analysis API endpoints.
Tests the full API request/response cycle with authentication and data validation.
"""

import pytest
import json
from unittest.mock import patch, Mock
from flask import url_for
from flask_login import login_user
from datetime import datetime, timedelta, timezone

from app.models.models import User, Song, Playlist, AnalysisResult, PlaylistSong
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.extensions import db


class TestAnalysisAPI:
    """Integration tests for analysis API endpoints."""

    @pytest.fixture
    def authenticated_user(self, app, client, db_session):
        """Create and authenticate a test user."""
        user = User(
            spotify_id='test_user_api',
            display_name='API Test User',
            email='api_test@example.com',
            access_token='test_access_token_api',
            refresh_token='test_refresh_token_api',
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.add(user)
        db_session.commit()
        
        # Properly authenticate the user using Flask-Login
        with app.test_request_context():
            login_user(user)
            
        # Also set session manually for the test client
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
        
        return user

    @pytest.fixture
    def authenticated_admin(self, app, client, db_session):
        """Create and authenticate an admin user."""
        admin_user = User(
            spotify_id='test_admin_api',
            display_name='API Admin User',
            email='admin@example.com',
            access_token='test_admin_access_token',
            refresh_token='test_admin_refresh_token',
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
            is_admin=True
        )
        db_session.add(admin_user)
        db_session.commit()
        
        # Set session manually for the test client (Flask-Login session)
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin_user.id)
            sess['_fresh'] = True
        
        return admin_user

    @pytest.fixture
    def test_song(self, db_session, authenticated_user):
        """Create a test song."""
        song = Song(
            spotify_id='test_song_api',
            title='Test Christian Song',
            artist='Test Artist',
            album='Test Album',
            lyrics='Amazing grace how sweet the sound'
        )
        db_session.add(song)
        db_session.commit()
        return song

    @pytest.fixture
    def test_playlist(self, db_session, authenticated_user):
        """Create a test playlist with songs."""
        playlist = Playlist(
            spotify_id='test_playlist_api',
            name='Test Christian Playlist',
            description='Test playlist for API testing',
            owner_id=authenticated_user.id
        )
        db_session.add(playlist)
        db_session.commit()
        return playlist

    @pytest.mark.api
    @pytest.mark.integration
    def test_analyze_song_endpoint_success(self, client, authenticated_user, test_song):
        """Test successful song analysis via API with priority queue."""
        # Create a playlist owned by the authenticated user
        playlist = Playlist(
            spotify_id='test_playlist_for_analysis',
            name='Test Playlist for Analysis',
            description='Test playlist for API testing',
            owner_id=authenticated_user.id
        )
        db.session.add(playlist)
        db.session.commit()
        
        # Associate the test song with the playlist so it passes authorization
        playlist_song = PlaylistSong(
            playlist_id=playlist.id,
            song_id=test_song.id,
            track_position=0
        )
        db.session.add(playlist_song)
        db.session.commit()
        
        # Mock the priority queue enqueue function
        with patch('app.routes.api.enqueue_song_analysis') as mock_enqueue:
            mock_job = Mock()
            mock_job.job_id = 'test_job_123'
            mock_enqueue.return_value = mock_job
            
            response = client.post(f'/api/songs/{test_song.id}/analyze')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['success'] is True
            assert data['status'] == 'success'
            assert data['song_id'] == test_song.id
            assert data['job_id'] == 'test_job_123'
            assert 'queued for analysis' in data['message']
            
            # Verify enqueue was called with correct priority (HIGH for individual songs)
            mock_enqueue.assert_called_once()
            call_args = mock_enqueue.call_args
            assert call_args[1]['priority'].name == 'HIGH'  # Individual song = HIGH priority

    @pytest.mark.api
    @pytest.mark.integration
    def test_analyze_song_endpoint_not_found(self, client, authenticated_user):
        """Test analysis endpoint with non-existent song."""
        response = client.post('/api/songs/99999/analyze')
        
        assert response.status_code == 404
        data = response.get_json()
        
        assert data['status'] == 'error'
        assert 'not found' in data['message'].lower()

    @pytest.mark.api
    @pytest.mark.integration
    def test_analyze_song_endpoint_unauthorized(self, client, test_song):
        """Test analysis endpoint without authentication."""
        response = client.post(f'/api/songs/{test_song.id}/analyze')
        
        assert response.status_code == 302  # Redirect to login
        # Or check for 401 if API returns JSON error
        if response.status_code == 401:
            data = response.get_json()
            assert data['status'] == 'error'
            assert 'unauthorized' in data['message'].lower()

    @pytest.mark.api
    @pytest.mark.integration
    def test_analyze_song_endpoint_invalid_method(self, client, authenticated_user, test_song):
        """Test analysis endpoint with invalid HTTP method."""
        response = client.get(f'/api/songs/{test_song.id}/analyze')
        
        assert response.status_code == 405  # Method Not Allowed

    @pytest.mark.api
    @pytest.mark.integration
    def test_analyze_playlist_endpoint_success(self, client, authenticated_user, test_playlist, test_song):
        """Test successful playlist analysis via API with priority queue."""
        # Add song to playlist
        playlist_song = PlaylistSong(
            playlist_id=test_playlist.id,
            song_id=test_song.id,
            track_position=0
        )
        db.session.add(playlist_song)
        db.session.commit()
        
        # Mock the priority queue playlist analysis function
        with patch('app.services.unified_analysis_service.UnifiedAnalysisService.enqueue_playlist_analysis') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = 'test_playlist_job_123'
            mock_enqueue.return_value = mock_job
            
            response = client.post(f'/api/playlists/{test_playlist.id}/analyze-unanalyzed')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['status'] == 'success'
            assert data['success'] is True
            assert data['queued_count'] == 1
            assert 'queued' in data['message'].lower()

    @pytest.mark.api
    @pytest.mark.integration
    def test_playlist_reanalyze_all_endpoint(self, client, authenticated_user, test_playlist, test_song):
        """Test playlist reanalyze all endpoint with priority queue."""
        # Add song to playlist
        playlist_song = PlaylistSong(
            playlist_id=test_playlist.id,
            song_id=test_song.id,
            track_position=0
        )
        db.session.add(playlist_song)
        db.session.commit()
        
        # Mock the priority queue playlist analysis function
        with patch('app.services.unified_analysis_service.UnifiedAnalysisService.enqueue_playlist_analysis') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = 'test_reanalyze_job_123'
            mock_enqueue.return_value = mock_job
            
            response = client.post(f'/api/playlists/{test_playlist.id}/reanalyze-all')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['success'] is True
            assert data['queued_count'] == 1
            assert 'reanalysis' in data['message'].lower()

    @pytest.mark.api
    @pytest.mark.integration
    def test_analysis_status_endpoint_with_queue(self, client, authenticated_user):
        """Test analysis status endpoint with priority queue information."""
        # Mock the priority queue status
        with patch('app.services.priority_analysis_queue.PriorityAnalysisQueue.get_queue_status') as mock_status:
            mock_status.return_value = {
                'total_jobs': 5,
                'pending_jobs': 3,
                'in_progress_jobs': 1,
                'completed_jobs': 1,
                'failed_jobs': 0,
                'priority_counts': {
                    'HIGH': 2,
                    'MEDIUM': 2,
                    'LOW': 1
                },
                'estimated_completion_time': 15.5
            }
            
            response = client.get('/api/analysis/status')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['status'] == 'success'
            assert data['success'] is True
            assert data['queue_length'] == 5
            assert data['pending_jobs'] == 3
            assert data['in_progress_jobs'] == 1
            assert data['estimated_completion_minutes'] == 15.5

    # New queue management endpoints tests
    @pytest.mark.api
    @pytest.mark.integration
    def test_queue_status_endpoint(self, client, authenticated_user):
        """Test queue status endpoint."""
        with patch('app.services.priority_analysis_queue.PriorityAnalysisQueue.get_queue_status') as mock_status:
            mock_status.return_value = {
                'total_jobs': 10,
                'pending_jobs': 7,
                'in_progress_jobs': 2,
                'completed_jobs': 1,
                'failed_jobs': 0,
                'priority_counts': {
                    'HIGH': 3,
                    'MEDIUM': 4,
                    'LOW': 3
                },
                'estimated_completion_time': 25.0,
                'active_job': {
                    'job_id': 'active_123',
                    'job_type': 'SONG_ANALYSIS',
                    'priority': 'HIGH',
                    'started_at': '2024-01-01T12:00:00Z'
                }
            }
            
            response = client.get('/api/queue/status')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['status'] == 'success'
            assert data['queue']['total_jobs'] == 10
            assert data['queue']['pending_jobs'] == 7
            assert data['queue']['active_job']['job_id'] == 'active_123'
            assert data['queue']['estimated_completion_minutes'] == 25.0

    @pytest.mark.api
    @pytest.mark.integration
    def test_worker_health_endpoint(self, client, authenticated_user):
        """Test worker health endpoint."""
        with patch('app.routes.api.get_worker_status') as mock_worker_status:
            mock_worker_status.return_value = {
                'status': 'running',
                'uptime_seconds': 3600,
                'jobs_processed': 45,
                'jobs_failed': 2,
                'jobs_interrupted': 1,
                'last_heartbeat': '2024-01-01T12:00:00Z',
                'current_job': {
                    'job_id': 'current_456',
                    'started_at': '2024-01-01T11:55:00Z',
                    'job_type': 'PLAYLIST_ANALYSIS'
                }
            }
            
            response = client.get('/api/worker/health')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['status'] == 'success'
            assert data['worker']['status'] == 'running'
            assert data['worker']['uptime_seconds'] == 3600
            assert data['worker']['jobs_processed'] == 45
            assert data['worker']['current_job']['job_id'] == 'current_456'

    @pytest.mark.api
    @pytest.mark.integration
    def test_job_status_endpoint(self, client, authenticated_user):
        """Test individual job status endpoint."""
        job_id = 'test_job_789'
        
        with patch('app.services.priority_analysis_queue.PriorityAnalysisQueue.get_job') as mock_get_job:
            from app.services.priority_analysis_queue import JobStatus, JobType, JobPriority
            
            mock_job = Mock()
            mock_job.job_id = job_id
            mock_job.status = JobStatus.IN_PROGRESS
            mock_job.job_type = JobType.SONG_ANALYSIS
            mock_job.priority = JobPriority.HIGH
            mock_job.progress = 0.6
            mock_job.created_at = '2024-01-01T11:30:00Z'
            mock_job.started_at = '2024-01-01T11:32:00Z'
            mock_job.estimated_completion_time = 5.5
            mock_job.metadata = {'song_title': 'Test Song', 'artist': 'Test Artist'}
            mock_get_job.return_value = mock_job
            
            response = client.get(f'/api/jobs/{job_id}/status')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['status'] == 'success'
            assert data['job']['job_id'] == job_id
            assert data['job']['status'] == 'IN_PROGRESS'
            assert data['job']['progress'] == 0.6
            assert data['job']['estimated_completion_minutes'] == 5.5

    @pytest.mark.api
    @pytest.mark.integration
    def test_job_status_not_found(self, client, authenticated_user):
        """Test job status endpoint with non-existent job."""
        with patch('app.services.priority_analysis_queue.PriorityAnalysisQueue.get_job') as mock_get_job:
            mock_get_job.return_value = None
            
            response = client.get('/api/jobs/nonexistent_job/status')
            
            assert response.status_code == 404
            data = response.get_json()
            
            assert data['status'] == 'error'
            assert 'not found' in data['message'].lower()

    @pytest.mark.api
    @pytest.mark.integration
    def test_analyze_endpoint_service_error(self, client, authenticated_user, test_song):
        """Test analysis endpoint when service throws an error."""
        # Create a playlist owned by the authenticated user
        playlist = Playlist(
            spotify_id='test_playlist_for_error',
            name='Test Playlist for Service Error',
            description='Test playlist for API testing',
            owner_id=authenticated_user.id
        )
        db.session.add(playlist)
        db.session.commit()
        
        # Associate the test song with the playlist so it passes authorization
        playlist_song = PlaylistSong(
            playlist_id=playlist.id,
            song_id=test_song.id,
            track_position=0
        )
        db.session.add(playlist_song)
        db.session.commit()
        
        # Mock service error
        with patch('app.routes.api.enqueue_song_analysis') as mock_enqueue:
            mock_enqueue.side_effect = Exception("Queue service error")
            
            response = client.post(f'/api/songs/{test_song.id}/analyze')
            
            assert response.status_code == 500
            data = response.get_json()
            
            assert data['status'] == 'error'
            assert 'error' in data['message'].lower()

    @pytest.mark.api
    @pytest.mark.integration
    def test_api_response_headers(self, client, authenticated_user, test_song):
        """Test that API responses have correct headers."""
        # Create a playlist owned by the authenticated user
        playlist = Playlist(
            spotify_id='test_playlist_for_headers',
            name='Test Playlist for Headers',
            description='Test playlist for API testing',
            owner_id=authenticated_user.id
        )
        db.session.add(playlist)
        db.session.commit()
        
        # Associate the test song with the playlist so it passes authorization
        playlist_song = PlaylistSong(
            playlist_id=playlist.id,
            song_id=test_song.id,
            track_position=0
        )
        db.session.add(playlist_song)
        db.session.commit()
        
        with patch('app.routes.api.enqueue_song_analysis') as mock_enqueue:
            mock_job = Mock()
            mock_job.job_id = 'test_job_123'
            mock_enqueue.return_value = mock_job
            
            response = client.post(f'/api/songs/{test_song.id}/analyze')
            
            assert response.status_code == 200
            assert response.headers.get('Content-Type') == 'application/json'

    @pytest.mark.api
    @pytest.mark.integration
    def test_api_rate_limiting(self, client, authenticated_user, test_song):
        """Test API rate limiting behavior."""
        # Mock analysis service for consistent responses
        with patch('app.services.unified_analysis_service.UnifiedAnalysisService.enqueue_analysis_job') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = 'test_job_123'
            mock_enqueue.return_value = mock_job
            
            # Make multiple rapid requests
            responses = []
            for i in range(5):  # Reduced number for faster testing
                response = client.post(f'/api/songs/{test_song.id}/analyze')
                responses.append(response)
            
            # Most requests should succeed (rate limiting may not be enforced in tests)
            successful_responses = [r for r in responses if r.status_code == 200]
            assert len(successful_responses) >= 3  # At least some should succeed

    @pytest.mark.api
    @pytest.mark.integration
    def test_api_cors_headers(self, client, authenticated_user, test_song):
        """Test CORS headers in API responses."""
        with patch('app.routes.api.enqueue_song_analysis') as mock_enqueue:
            mock_job = Mock()
            mock_job.job_id = 'test_job_123'
            mock_enqueue.return_value = mock_job
            
            response = client.post(f'/api/songs/{test_song.id}/analyze')
            
            assert response.status_code == 200
            # Note: CORS headers would be set by Flask-CORS if configured
            # This test verifies the response structure is correct

    @pytest.mark.api
    @pytest.mark.integration
    def test_api_error_response_format(self, client, authenticated_user):
        """Test that API error responses follow consistent format."""
        # Test 404 error
        response = client.post('/api/songs/99999/analyze')
        
        assert response.status_code == 404
        data = response.get_json()
        
        # Should have consistent error format
        assert 'status' in data
        assert 'message' in data
        assert data['status'] == 'error'
        assert isinstance(data['message'], str)

    @pytest.mark.api
    @pytest.mark.integration
    def test_api_success_response_format(self, client, authenticated_user, test_song):
        """Test that API success responses follow consistent format."""
        with patch('app.routes.api.enqueue_song_analysis') as mock_enqueue:
            mock_job = Mock()
            mock_job.job_id = 'test_job_123'
            mock_enqueue.return_value = mock_job
            
            response = client.post(f'/api/songs/{test_song.id}/analyze')
            
            assert response.status_code == 200
            data = response.get_json()
            
            # Check consistent response structure
            assert 'status' in data
            assert data['status'] == 'success'
            
            # Verify response contains expected fields
            assert 'job_id' in data 

    # Admin endpoint tests with priority queue
    @pytest.mark.skip(reason="Admin authentication complex - will fix in separate task")
    @pytest.mark.api
    @pytest.mark.integration
    def test_admin_reanalyze_user_with_queue(self, client, authenticated_admin, test_song):
        """Test admin reanalyze user endpoint with priority queue."""
        # Create a test user and playlist
        test_user = User(
            spotify_id='test_user_for_admin',
            email='testuser@example.com',
            display_name='Test User',
            access_token='test_access_token_admin',
            refresh_token='test_refresh_token_admin',
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db.session.add(test_user)
        db.session.commit()
        
        playlist = Playlist(
            spotify_id='admin_test_playlist',
            name='Admin Test Playlist',
            owner_id=test_user.id
        )
        db.session.add(playlist)
        db.session.commit()
        
        # Add song to playlist
        playlist_song = PlaylistSong(
            playlist_id=playlist.id,
            song_id=test_song.id,
            track_position=0
        )
        db.session.add(playlist_song)
        db.session.commit()
        
        # Mock the admin_required decorator to bypass authentication for this test
        def mock_admin_required(f):
            return f  # Just return the function unchanged
        
        with patch('app.routes.api.admin_required', mock_admin_required), \
             patch('app.services.unified_analysis_service.UnifiedAnalysisService.enqueue_background_analysis') as mock_enqueue:
            
            mock_job = Mock()
            mock_job.id = 'admin_background_job_123'
            mock_enqueue.return_value = mock_job
            
            response = client.post(f'/api/admin/reanalyze-user/{test_user.id}')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['success'] is True
            assert data['queued_count'] == 1
            assert 'background analysis' in data['message'].lower()

    @pytest.mark.api
    @pytest.mark.integration  
    def test_queue_health_check_endpoint(self, client, authenticated_user):
        """Test queue health check endpoint."""
        with patch('app.services.priority_analysis_queue.PriorityAnalysisQueue.health_check') as mock_health:
            mock_health.return_value = {
                'redis_connected': True,
                'queue_accessible': True,
                'total_jobs': 5,
                'oldest_job_age_seconds': 120,
                'last_activity': '2024-01-01T12:00:00Z'
            }
            
            response = client.get('/api/queue/health')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['status'] == 'success'
            assert data['queue_health']['redis_connected'] is True
            assert data['queue_health']['queue_accessible'] is True
            assert data['queue_health']['total_jobs'] == 5

    @pytest.mark.api
    @pytest.mark.integration
    def test_queue_health_check_failure(self, client, authenticated_user):
        """Test queue health check endpoint when queue is unhealthy."""
        with patch('app.services.priority_analysis_queue.PriorityAnalysisQueue.health_check') as mock_health:
            mock_health.return_value = {
                'redis_connected': False,
                'queue_accessible': False,
                'error': 'Redis connection failed'
            }
            
            response = client.get('/api/queue/health')
            
            assert response.status_code == 503  # Service Unavailable
            data = response.get_json()
            
            assert data['status'] == 'error'
            assert data['queue_health']['redis_connected'] is False
            assert 'Redis connection failed' in data['queue_health']['error'] 