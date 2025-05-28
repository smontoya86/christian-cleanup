"""
Unit tests for the unified analysis service.
Tests individual components and their integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

from app.services.unified_analysis_service import UnifiedAnalysisService
from app.models.models import Song, AnalysisResult, User


class TestUnifiedAnalysisService:
    """Test cases for the UnifiedAnalysisService."""

    @pytest.fixture
    def analysis_service(self):
        """Create a UnifiedAnalysisService instance."""
        return UnifiedAnalysisService()

    @pytest.fixture
    def sample_song(self):
        """Create a sample song for testing."""
        return Song(
            id=1,
            spotify_id='test_song_123',
            title='Amazing Grace',
            artist='Chris Tomlin',
            album='How Great Is Our God',
            duration_ms=240000,
            lyrics='Amazing grace, how sweet the sound that saved a wretch like me'
        )

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        return User(
            id=1,
            spotify_id='test_user_123',
            display_name='Test User',
            email='test@example.com'
        )

    @pytest.mark.unit
    def test_initialize_analysis_service(self, analysis_service):
        """Test that UnifiedAnalysisService initializes correctly."""
        assert analysis_service is not None
        assert hasattr(analysis_service, 'execute_comprehensive_analysis')
        assert hasattr(analysis_service, 'enqueue_analysis_job')

    @pytest.mark.unit
    @patch('app.services.unified_analysis_service.EnhancedSongAnalyzer')
    @patch('app.services.unified_analysis_service.LyricsFetcher')
    @patch('app.extensions.db.session')
    def test_execute_comprehensive_analysis(self, mock_db_session, mock_lyrics_fetcher_class, 
                                          mock_analyzer_class, analysis_service, sample_song, app):
        """Test comprehensive song analysis."""
        with app.app_context():
            # Mock database queries
            mock_db_session.get.return_value = sample_song
            
            # Mock lyrics fetcher
            mock_lyrics_instance = Mock()
            mock_lyrics_fetcher_class.return_value = mock_lyrics_instance
            mock_lyrics_instance.fetch_lyrics.return_value = "Amazing grace how sweet the sound"
            
            # Mock analyzer with correct format
            mock_analyzer_instance = Mock()
            mock_analyzer_class.return_value = mock_analyzer_instance
            mock_analyzer_instance.analyze_song.return_value = {
                'score': 85,
                'christian_score': 85,  # Added required field
                'concern_level': 'Low',  # Fixed case
                'detailed_concerns': [],
                'biblical_themes': [{'theme': 'salvation_and_redemption', 'confidence': 0.9}],
                'positive_themes': [{'theme': 'grace', 'confidence': 0.8}],
                'explanation': 'This song contains strong Christian themes about grace.',
                'positive_bonus': 15,
                'biblical_references': [],
                'content_flags': [],
                'supporting_scripture': []  # Added required field
            }
            
            result = analysis_service.execute_comprehensive_analysis(sample_song.id, user_id=1)
            
            # Verify result
            assert result is not None
            assert result.score == 85
            assert result.concern_level == 'Low'
            assert 'christian' in result.explanation.lower()
            
            # Verify mocks were called
            mock_lyrics_instance.fetch_lyrics.assert_called_once()
            mock_analyzer_instance.analyze_song.assert_called_once()

    @pytest.mark.unit
    @patch('app.services.unified_analysis_service.rq')
    @patch('app.extensions.db.session')
    def test_enqueue_analysis_job(self, mock_db_session, mock_rq, analysis_service, sample_song, app):
        """Test enqueueing analysis job."""
        with app.app_context():
            # Mock database to return a song
            mock_db_session.get.return_value = sample_song
            
            mock_queue = Mock()
            mock_rq.get_queue.return_value = mock_queue
            mock_queue.enqueue.return_value = Mock(id='job_123')
            
            job = analysis_service.enqueue_analysis_job(song_id=1, user_id=1)
            
            assert job is not None
            mock_queue.enqueue.assert_called_once()

    @pytest.mark.unit
    def test_get_song_cache_key(self, analysis_service):
        """Test cache key generation."""
        key = analysis_service._get_song_cache_key('Test Song', 'Test Artist', False)
        
        # Cache key should be a string (likely hashed)
        assert isinstance(key, str)
        assert len(key) > 0
        
        # Same inputs should produce same key
        key2 = analysis_service._get_song_cache_key('Test Song', 'Test Artist', False)
        assert key == key2
        
        # Different inputs should produce different keys
        key3 = analysis_service._get_song_cache_key('Different Song', 'Test Artist', False)
        assert key != key3

    @pytest.mark.unit
    @patch('app.extensions.db.session')
    def test_execute_comprehensive_analysis_song_not_found(self, mock_db_session, analysis_service, app):
        """Test analysis when song is not found."""
        with app.app_context():
            mock_db_session.get.return_value = None
            
            result = analysis_service.execute_comprehensive_analysis(999, user_id=1)
            
            assert result is None

    @pytest.mark.unit
    def test_validate_analysis_result(self, analysis_service):
        """Test analysis result validation."""
        valid_result = {
            'score': 85,
            'christian_score': 85,  # Required field
            'concern_level': 'Low',  # Fixed case
            'detailed_concerns': [],
            'biblical_themes': [{'theme': 'salvation', 'confidence': 0.9}],
            'explanation': 'Valid analysis result',
            'supporting_scripture': []  # Required field
        }
        
        is_valid = analysis_service._validate_comprehensive_analysis(valid_result)
        assert is_valid is True

    @pytest.mark.unit
    def test_validate_analysis_result_invalid(self, analysis_service):
        """Test validation of invalid analysis result."""
        invalid_result = {
            'score': 'not_a_number',  # Invalid score
            'concern_level': 'low'
        }
        
        is_valid = analysis_service._validate_comprehensive_analysis(invalid_result)
        assert is_valid is False

    @pytest.mark.unit
    def test_get_expected_concern_level(self, analysis_service):
        """Test concern level calculation."""
        # Test very high concern (very low score)
        concern = analysis_service._get_expected_concern_level(2)
        assert concern == 'Very High'
        
        # Test high concern (low score)
        concern = analysis_service._get_expected_concern_level(55)
        assert concern == 'High'
        
        # Test medium concern (medium score)
        concern = analysis_service._get_expected_concern_level(75)
        assert concern == 'Medium'
        
        # Test low concern (high score)  
        concern = analysis_service._get_expected_concern_level(90)
        assert concern == 'Low'

    @pytest.mark.unit
    @patch('app.services.unified_analysis_service.logger')
    def test_logging_during_analysis(self, mock_logger, analysis_service):
        """Test that analysis operations are properly logged."""
        # Test that logger is available and can be called
        analysis_service._log_analysis_completion(1, {'score': 85}, 1.5)
        
        # Verify logger was called
        assert mock_logger.info.called or mock_logger.debug.called or mock_logger.warning.called 