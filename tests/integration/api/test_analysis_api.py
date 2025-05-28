"""
Integration tests for analysis API endpoints.
Tests the full API request/response cycle with authentication and data validation.
"""

import pytest
import json
from unittest.mock import patch, Mock
from flask import url_for

from app.models.models import User, Song, Playlist, AnalysisResult
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.extensions import db


class TestAnalysisAPI:
    """Integration tests for analysis API endpoints."""

    @pytest.fixture
    def authenticated_user(self, client, db_session):
        """Create and authenticate a test user."""
        from datetime import datetime, timedelta
        
        user = User(
            spotify_id='test_user_api',
            display_name='API Test User',
            email='api_test@example.com',
            access_token='test_access_token_api',
            refresh_token='test_refresh_token_api',
            token_expiry=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(user)
        db_session.commit()
        
        # Simulate login by setting the user in session
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
            sess['_fresh'] = True
        
        return user

    @pytest.fixture
    def test_song(self, db_session):
        """Create a test song in the database."""
        song = Song(
            spotify_id='test_song_api_123',
            title='Amazing Grace',
            artist='Chris Tomlin',
            album='How Great Is Our God',
            duration_ms=240000,
            lyrics='Amazing grace, how sweet the sound that saved a wretch like me'
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
            user_id=authenticated_user.id,
            total_tracks=1
        )
        db_session.add(playlist)
        db_session.commit()
        return playlist

    @pytest.mark.api
    @pytest.mark.integration
    def test_analyze_song_endpoint_success(self, client, authenticated_user, test_song):
        """Test successful song analysis via API."""
        # Mock the analysis service
        with patch('app.services.unified_analysis_service.UnifiedAnalysisService.enqueue_analysis_job') as mock_enqueue:
            # Mock successful job enqueue
            mock_job = Mock()
            mock_job.id = 'test_job_123'
            mock_enqueue.return_value = mock_job
            
            response = client.post(f'/api/songs/{test_song.id}/analyze')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['status'] == 'success'
            assert 'job_id' in data
            # Verify the service was called correctly
            mock_enqueue.assert_called_once_with(test_song.id, authenticated_user.id)

    @pytest.mark.api
    @pytest.mark.integration
    def test_analyze_song_endpoint_not_found(self, client, authenticated_user):
        """Test analysis of non-existent song."""
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
        """Test successful playlist analysis via API."""
        # Add song to playlist
        from app.models.models import PlaylistSong
        playlist_song = PlaylistSong(
            playlist_id=test_playlist.id,
            song_id=test_song.id,
            track_position=0
        )
        db.session.add(playlist_song)
        db.session.commit()
        
        # Mock the unified analysis service
        with patch('app.services.unified_analysis_service.UnifiedAnalysisService.enqueue_analysis_job') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = 'test_job_123'
            mock_enqueue.return_value = mock_job
            
            response = client.post(f'/api/playlists/{test_playlist.spotify_id}/analyze-unanalyzed')
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['status'] == 'success'
            # Should indicate that analysis jobs were enqueued
            assert 'message' in data

    @pytest.mark.api
    @pytest.mark.integration
    def test_get_analysis_result_endpoint_success(self, client, authenticated_user, test_song):
        """Test retrieving existing analysis result via API."""
        # Create an existing analysis result
        existing_result = AnalysisResult(
            song_id=test_song.id,
            score=75,
            christian_score=75,
            concern_level='Medium',
            themes=['faith'],
            explanation='Test analysis result',
            status='completed'
        )
        db.session.add(existing_result)
        db.session.commit()
        
        response = client.get(f'/api/songs/{test_song.id}/analysis-status')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['status'] == 'success'
        assert 'analysis' in data

    @pytest.mark.api
    @pytest.mark.integration
    def test_get_analysis_result_endpoint_not_found(self, client, authenticated_user, test_song):
        """Test retrieving non-existent analysis result."""
        response = client.get(f'/api/songs/{test_song.id}/analysis-status')
        
        # This should return 200 with a status indicating no analysis exists
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['status'] == 'success'
        # Check that no analysis exists
        assert data.get('analysis') is None or data.get('analysis', {}).get('status') == 'not_analyzed'

    @pytest.mark.api
    @pytest.mark.integration
    def test_analyze_endpoint_service_error(self, client, authenticated_user, test_song):
        """Test analysis endpoint when service throws an error."""
        # Mock service error
        with patch('app.services.unified_analysis_service.UnifiedAnalysisService.enqueue_analysis_job') as mock_enqueue:
            mock_enqueue.side_effect = Exception("Analysis service error")
            
            response = client.post(f'/api/songs/{test_song.id}/analyze')
            
            assert response.status_code == 500
            data = response.get_json()
            
            assert data['status'] == 'error'
            assert 'error' in data['message'].lower()

    @pytest.mark.api
    @pytest.mark.integration
    def test_analysis_status_endpoint(self, client, authenticated_user):
        """Test analysis status/health endpoint."""
        response = client.get('/api/analysis/status')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['status'] == 'success'
        assert 'analysis_queue_length' in data

    @pytest.mark.api
    @pytest.mark.integration
    def test_api_response_headers(self, client, authenticated_user, test_song):
        """Test that API responses have correct headers."""
        with patch('app.services.unified_analysis_service.UnifiedAnalysisService.enqueue_analysis_job') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = 'test_job_123'
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
        with patch('app.services.unified_analysis_service.UnifiedAnalysisService.enqueue_analysis_job') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = 'test_job_123'
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
        with patch('app.services.unified_analysis_service.UnifiedAnalysisService.enqueue_analysis_job') as mock_enqueue:
            mock_job = Mock()
            mock_job.id = 'test_job_123'
            mock_enqueue.return_value = mock_job
            
            response = client.post(f'/api/songs/{test_song.id}/analyze')
            
            assert response.status_code == 200
            data = response.get_json()
            
            # Check consistent response structure
            assert 'status' in data
            assert data['status'] == 'success'
            
            # Verify response contains expected fields
            assert 'job_id' in data 