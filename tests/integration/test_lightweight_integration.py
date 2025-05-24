"""
Integration Test for Lightweight Analysis Pipeline

Tests the complete analysis pipeline using the lightweight analyzer
to ensure all components work together correctly.
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from app.models import Song, AnalysisResult, db
from app.services.analysis_service import _execute_song_analysis_impl
from app.utils.database import get_by_filter  # Add SQLAlchemy 2.0 utilities
import os

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        
    yield app
    
    # Clean up / reset resources here
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

class TestLightweightIntegration:
    """Test the complete lightweight analysis pipeline"""
    
    def test_complete_analysis_pipeline(self, app):
        """Test the complete analysis pipeline from song creation to result storage"""
        with app.app_context():
            # Create a test song
            song = Song(
                spotify_id="test_integration_123",
                title="Test Integration Song",
                artist="Test Artist",
                explicit=False
            )
            db.session.add(song)
            db.session.commit()
            
            # Mock lyrics fetcher to return test lyrics
            with patch('app.utils.lyrics.LyricsFetcher') as mock_lyrics_class:
                mock_fetcher = MagicMock()
                mock_fetcher.fetch_lyrics.return_value = "Jesus loves us all, praise the Lord"
                mock_lyrics_class.return_value = mock_fetcher
                
                # Execute the analysis
                result = _execute_song_analysis_impl(song.id, user_id=1)
                
                # Verify analysis completed successfully
                assert result is not None
                assert 'christian_score' in result
                assert 'christian_concern_level' in result
                
                # Verify database was updated
                analysis_result = get_by_filter(AnalysisResult, song_id=song.id)
                assert analysis_result is not None
                assert analysis_result.status == AnalysisResult.STATUS_COMPLETED
                assert analysis_result.score is not None
                assert analysis_result.concern_level is not None
                
                # Verify song was updated
                updated_song = db.session.get(Song, song.id)
                assert updated_song.last_analyzed is not None
                
    def test_explicit_song_analysis_pipeline(self, app):
        """Test analysis pipeline with explicit song"""
        with app.app_context():
            # Create an explicit test song
            song = Song(
                spotify_id="test_explicit_456",
                title="Explicit Test Song",
                artist="Test Artist",
                explicit=True
            )
            db.session.add(song)
            db.session.commit()
            
            # Mock lyrics fetcher to return clean lyrics (but song is marked explicit)
            with patch('app.utils.lyrics.LyricsFetcher') as mock_lyrics_class:
                mock_fetcher = MagicMock()
                mock_fetcher.fetch_lyrics.return_value = "Clean lyrics but marked explicit"
                mock_lyrics_class.return_value = mock_fetcher
                
                # Execute the analysis
                result = _execute_song_analysis_impl(song.id, user_id=1)
                
                # Verify analysis completed successfully
                assert result is not None
                assert result['is_explicit'] is True
                assert result['christian_score'] < 80  # Should be penalized for explicit flag
                
                # Verify explicit flag was detected
                flags = result['christian_purity_flags_details']
                explicit_flag = next(
                    (flag for flag in flags if 'Explicit' in flag.get('flag', '')), 
                    None
                )
                assert explicit_flag is not None
                
                # Verify database storage
                analysis_result = get_by_filter(AnalysisResult, song_id=song.id)
                assert analysis_result is not None
                assert analysis_result.score < 80
                
    def test_problematic_lyrics_analysis_pipeline(self, app):
        """Test analysis pipeline with problematic lyrics"""
        with app.app_context():
            # Create a test song
            song = Song(
                spotify_id="test_problematic_789",
                title="Problematic Song",
                artist="Test Artist",
                explicit=False
            )
            db.session.add(song)
            db.session.commit()
            
            # Mock lyrics fetcher to return problematic lyrics
            with patch('app.utils.lyrics.LyricsFetcher') as mock_lyrics_class:
                mock_fetcher = MagicMock()
                mock_fetcher.fetch_lyrics.return_value = "This damn song has violence and drugs"
                mock_lyrics_class.return_value = mock_fetcher
                
                # Execute the analysis
                result = _execute_song_analysis_impl(song.id, user_id=1)
                
                # Verify analysis completed successfully
                assert result is not None
                assert result['christian_score'] < 80  # Should be penalized
                
                # Verify flags were detected
                flags = result['christian_purity_flags_details']
                assert len(flags) > 0  # Should have detected some flags
                
                # Verify concern level reflects the issues
                assert result['christian_concern_level'] in ['Medium', 'High', 'Very High']
                
                # Verify database storage
                analysis_result = get_by_filter(AnalysisResult, song_id=song.id)
                assert analysis_result is not None
                assert analysis_result.score < 80
                assert analysis_result.concern_level in ['Medium', 'High', 'Very High']
                
    def test_lyrics_fetch_failure_handling(self, app):
        """Test analysis pipeline when lyrics fetching fails"""
        with app.app_context():
            # Create a test song
            song = Song(
                spotify_id="test_no_lyrics_101",
                title="No Lyrics Song",
                artist="Test Artist",
                explicit=False
            )
            db.session.add(song)
            db.session.commit()
            
            # Mock lyrics fetcher to return None (fetch failure)
            with patch('app.utils.lyrics.LyricsFetcher') as mock_lyrics_class:
                mock_fetcher = MagicMock()
                mock_fetcher.fetch_lyrics.return_value = None
                mock_lyrics_class.return_value = mock_fetcher
                
                # Execute the analysis
                result = _execute_song_analysis_impl(song.id, user_id=1)
                
                # Verify analysis completed with default values
                assert result is not None
                assert 'christian_score' in result
                assert 'warnings' in result
                assert len(result['warnings']) > 0  # Should have warning about missing lyrics
                
                # Verify database was still updated with default analysis
                analysis_result = get_by_filter(AnalysisResult, song_id=song.id)
                assert analysis_result is not None
                assert analysis_result.status == AnalysisResult.STATUS_COMPLETED
                
    def test_positive_christian_themes_detection(self, app):
        """Test detection of positive Christian themes"""
        with app.app_context():
            # Create a test song
            song = Song(
                spotify_id="test_christian_202",
                title="Christian Song",
                artist="Christian Artist",
                explicit=False
            )
            db.session.add(song)
            db.session.commit()
            
            # Mock lyrics fetcher to return Christian lyrics
            with patch('app.utils.lyrics.LyricsFetcher') as mock_lyrics_class:
                mock_fetcher = MagicMock()
                mock_fetcher.fetch_lyrics.return_value = "Jesus Christ is Lord, praise God, faith and hope, salvation through grace"
                mock_lyrics_class.return_value = mock_fetcher
                
                # Execute the analysis
                result = _execute_song_analysis_impl(song.id, user_id=1)
                
                # Verify analysis completed successfully
                assert result is not None
                assert result['christian_score'] >= 75  # Should have high score
                
                # Verify positive themes were detected
                positive_themes = result['christian_positive_themes_detected']
                assert len(positive_themes) > 0
                
                # Verify scripture support was provided
                scripture = result['christian_supporting_scripture']
                assert len(scripture) > 0
                
                # Verify concern level is low
                assert result['christian_concern_level'] == 'Low'
                
    def test_analysis_service_interface_compatibility(self, app):
        """Test that the analysis service interface remains compatible"""
        with app.app_context():
            # Import the analysis service functions
            from app.services.analysis_service import _execute_song_analysis_impl
            
            # Create a test song
            song = Song(
                spotify_id="test_interface_303",
                title="Interface Test Song",
                artist="Test Artist",
                explicit=False
            )
            db.session.add(song)
            db.session.commit()
            
            # Mock lyrics fetcher
            with patch('app.utils.lyrics.LyricsFetcher') as mock_lyrics_class:
                mock_fetcher = MagicMock()
                mock_fetcher.fetch_lyrics.return_value = "Test lyrics for interface compatibility"
                mock_lyrics_class.return_value = mock_fetcher
                
                # Execute analysis using the service
                result = _execute_song_analysis_impl(song.id, user_id=1)
                
                # Verify the result has all expected keys from original interface
                expected_keys = [
                    'title', 'artist', 'christian_score', 'christian_concern_level',
                    'christian_purity_flags_details', 'christian_positive_themes_detected',
                    'christian_negative_themes_detected', 'warnings', 'errors'
                ]
                
                for key in expected_keys:
                    assert key in result, f"Missing expected key: {key}"
                    
                # Verify data types are correct
                assert isinstance(result['christian_score'], int)
                assert isinstance(result['christian_purity_flags_details'], list)
                assert isinstance(result['warnings'], list)
                assert isinstance(result['errors'], list)
                
    @patch.dict(os.environ, {'USE_LIGHTWEIGHT_ANALYZER': 'true'})
    def test_environment_variable_controls_mode(self, app):
        """Test that environment variable controls which analyzer is used"""
        with app.app_context():
            # Import after setting environment variable
            from app.utils.analysis_adapter import SongAnalyzer
            
            # Create analyzer
            analyzer = SongAnalyzer(user_id=1)
            
            # Verify it's using lightweight mode
            assert hasattr(analyzer, 'lightweight_analyzer')
            assert analyzer.lightweight_analyzer is not None
            
            # Test analysis works
            result = analyzer.analyze_song(
                title="Test Song",
                artist="Test Artist",
                lyrics_text="Test lyrics",
                is_explicit=False
            )
            
            assert 'christian_score' in result
            assert isinstance(result['christian_score'], int) 