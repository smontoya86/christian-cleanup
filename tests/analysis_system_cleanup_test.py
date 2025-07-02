"""
Analysis System Cleanup Tests

TDD approach to identify the core HuggingFace analysis system and remove redundant components.
These tests validate that the essential analysis functionality remains intact.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from app import create_app, db
from app.models import Song, AnalysisResult, User, Playlist, PlaylistSong


class TestHuggingFaceAnalysisSystemCore:
    """Test the core HuggingFace analysis system that should be preserved."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test user
        self.test_user = User(
            spotify_id='test_user_123',
            email='test@example.com',
            display_name='Test User'
        )
        db.session.add(self.test_user)
        db.session.commit()
        
        yield
        
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_huggingface_analyzer_exists_and_works(self):
        """Test that HuggingFaceAnalyzer is the core system and works."""
        from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
        
        # Should be able to import and initialize
        analyzer = HuggingFaceAnalyzer()
        assert analyzer is not None
        
        # Should have the required models
        assert hasattr(analyzer, '_sentiment_analyzer')
        assert hasattr(analyzer, '_safety_analyzer')
        assert hasattr(analyzer, '_emotion_analyzer')
        
        # Should have Christian keywords
        assert hasattr(analyzer, 'christian_keywords')
        assert 'jesus' in analyzer.christian_keywords
        assert 'god' in analyzer.christian_keywords

    @patch('app.utils.analysis.huggingface_analyzer.pipeline')
    def test_huggingface_analyzer_analyze_song(self, mock_pipeline):
        """Test that HuggingFaceAnalyzer can analyze a song."""
        from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
        
        # Mock the pipeline responses
        mock_sentiment = MagicMock()
        mock_sentiment.return_value = [{'label': 'POSITIVE', 'score': 0.9}]
        
        mock_safety = MagicMock()
        mock_safety.return_value = [{'label': 'SAFE', 'score': 0.95}]
        
        mock_emotion = MagicMock()
        mock_emotion.return_value = [{'label': 'joy', 'score': 0.8}]
        
        mock_pipeline.side_effect = [mock_sentiment, mock_safety, mock_emotion]
        
        analyzer = HuggingFaceAnalyzer()
        analyzer._sentiment_analyzer = mock_sentiment
        analyzer._safety_analyzer = mock_safety
        analyzer._emotion_analyzer = mock_emotion
        
        # Test analysis
        result = analyzer.analyze_song(
            title="Amazing Grace",
            artist="Traditional",
            lyrics="Amazing grace how sweet the sound"
        )
        
        # Should return AnalysisResult
        from app.utils.analysis.analysis_result import AnalysisResult
        assert isinstance(result, AnalysisResult)
        assert result.title == "Amazing Grace"
        assert result.artist == "Traditional"

    def test_simplified_christian_analysis_service_uses_huggingface(self):
        """Test that SimplifiedChristianAnalysisService uses HuggingFace analyzer."""
        from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
        
        service = SimplifiedChristianAnalysisService()
        
        # Should have HuggingFace analyzer
        assert hasattr(service, 'ai_analyzer')
        assert hasattr(service.ai_analyzer, 'hf_analyzer')
        
        # Verify it's the HuggingFace analyzer
        from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
        assert isinstance(service.ai_analyzer.hf_analyzer, HuggingFaceAnalyzer)

    def test_dashboard_analyze_all_flow(self):
        """Test the complete flow from dashboard to HuggingFace analysis."""
        from app.services.unified_analysis_service import UnifiedAnalysisService
        
        # Create test song
        song = Song(
            spotify_id='test_song_123',
            name='Amazing Grace',
            artist='Traditional',
            lyrics='Amazing grace how sweet the sound'
        )
        db.session.add(song)
        db.session.commit()
        
        # Test the service that dashboard uses
        service = UnifiedAnalysisService()
        assert service is not None
        
        # Should use SimplifiedChristianAnalysisService internally
        assert hasattr(service, 'analysis_service')
        from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
        assert isinstance(service.analysis_service, SimplifiedChristianAnalysisService)


class TestRedundantAnalysisComponents:
    """Test to identify which analysis components are redundant and can be removed."""
    
    def test_analysis_orchestrator_complexity(self):
        """Test that AnalysisOrchestrator is over-engineered."""
        from app.utils.analysis.orchestrator import AnalysisOrchestrator
        
        orchestrator = AnalysisOrchestrator()
        
        # Count the number of complex components - should be excessive
        complex_components = [
            'lyrics_preprocessor', 'text_tokenizer', 'text_cleaner',
            'pattern_registry', 'biblical_detector', 'model_manager',
            'content_model', 'scorer', 'content_engine', 'biblical_engine',
            'qa_engine', 'scoring_engine'
        ]
        
        existing_components = [attr for attr in complex_components if hasattr(orchestrator, attr)]
        
        # If most of these exist, the orchestrator is over-engineered
        assert len(existing_components) > 8, "AnalysisOrchestrator appears to be over-engineered"

    def test_unified_service_is_just_wrapper(self):
        """Test that UnifiedAnalysisService is just a wrapper."""
        import inspect
        from app.services.unified_analysis_service import UnifiedAnalysisService
        
        # Get source code
        source = inspect.getsource(UnifiedAnalysisService)
        
        # Should be mostly delegation to SimplifiedChristianAnalysisService
        assert 'SimplifiedChristianAnalysisService' in source
        assert 'self.analysis_service' in source
        
        # Check if it's mainly a wrapper (should have lots of delegation)
        lines = source.split('\n')
        delegation_lines = [line for line in lines if 'self.analysis_service.' in line]
        
        # If significant portion is delegation, it's a wrapper
        total_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        delegation_ratio = len(delegation_lines) / total_lines if total_lines > 0 else 0
        
        # This will help us decide if it's worth keeping
        print(f"UnifiedAnalysisService delegation ratio: {delegation_ratio:.2f}")


class TestCurrentActiveAnalysisPath:
    """Test the current active analysis path to ensure we preserve the right components."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        yield
        
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_api_route_uses_unified_service(self):
        """Test that API routes use UnifiedAnalysisService."""
        from app.routes.api import UnifiedAnalysisService
        
        # Should be importable from api routes
        assert UnifiedAnalysisService is not None

    def test_main_route_uses_unified_service(self):
        """Test that main routes use UnifiedAnalysisService."""
        from app.routes.main import UnifiedAnalysisService
        
        # Should be importable from main routes
        assert UnifiedAnalysisService is not None

    @patch('app.utils.analysis.huggingface_analyzer.pipeline')
    def test_end_to_end_analysis_flow(self, mock_pipeline):
        """Test the complete end-to-end analysis flow."""
        from app.services.unified_analysis_service import UnifiedAnalysisService
        
        # Mock HuggingFace models
        mock_sentiment = MagicMock()
        mock_sentiment.return_value = [{'label': 'POSITIVE', 'score': 0.9}]
        
        mock_safety = MagicMock()
        mock_safety.return_value = [{'label': 'SAFE', 'score': 0.95}]
        
        mock_emotion = MagicMock()
        mock_emotion.return_value = [{'label': 'joy', 'score': 0.8}]
        
        mock_pipeline.side_effect = [mock_sentiment, mock_safety, mock_emotion]
        
        # Create test song
        song = Song(
            spotify_id='test_song_123',
            name='Amazing Grace',
            artist='Traditional',
            lyrics='Amazing grace how sweet the sound'
        )
        db.session.add(song)
        db.session.commit()
        
        # Test the complete flow
        service = UnifiedAnalysisService()
        result = service.analyze_song_complete(song, force=True)
        
        # Should get analysis result
        assert result is not None
        assert 'score' in result
        assert 'concern_level' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 