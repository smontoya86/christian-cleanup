import pytest
from unittest.mock import patch, Mock
from app.models import User, Song, AnalysisResult
from app.services.unified_analysis_service import UnifiedAnalysisService


class TestUnifiedAnalysisService:
    """Test cases for the UnifiedAnalysisService."""

    @pytest.fixture
    def analysis_service(self):
        """Create UnifiedAnalysisService instance for testing."""
        return UnifiedAnalysisService()

    @pytest.fixture
    def sample_song(self):
        """Create a sample song for testing."""
        return Song(
            id=1,
            spotify_id='test_song_123',
            title='Amazing Grace',
            artist='Traditional',
            album='Hymns Collection',
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
    def test_initialize_analysis_service(self):
        """Test that UnifiedAnalysisService initializes correctly."""
        analysis_service = UnifiedAnalysisService()
        assert analysis_service is not None
        assert hasattr(analysis_service, 'execute_comprehensive_analysis')
        assert hasattr(analysis_service, 'analysis_service')

    @pytest.mark.unit
    def test_analyze_song_complete(self, analysis_service, sample_song):
        """Test the analyze_song_complete method."""
        # Mock the analysis_service to return True
        with patch.object(analysis_service.analysis_service, 'analyze_song', return_value=True):
            result = analysis_service.analyze_song_complete(sample_song, force=True)
            
            assert result is not None
            assert result['status'] == 'completed'
            assert result['score'] == 85
            assert 'completed successfully' in result['explanation']

    @pytest.mark.unit
    def test_analyze_song_complete_failure(self, analysis_service, sample_song):
        """Test analyze_song_complete when analysis fails."""
        # Mock the analysis_service to return False
        with patch.object(analysis_service.analysis_service, 'analyze_song', return_value=False):
            result = analysis_service.analyze_song_complete(sample_song, force=True)
            
            assert result is not None
            assert result['status'] == 'failed'
            assert result['score'] == 0
            assert 'failed' in result['explanation'] 