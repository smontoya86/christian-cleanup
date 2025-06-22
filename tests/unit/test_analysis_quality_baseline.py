"""
Analysis Quality Baseline Tests

Tests to establish quality metrics for the current analysis system
before simplification. These tests ensure the simplified system
maintains or improves educational value for Christian discernment training.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
from app.models import Song


class TestAnalysisQualityBaseline:
    """Test simplified analysis system quality to establish baseline metrics."""
    
    @pytest.fixture
    def simplified_service(self):
        """Create simplified analysis service for testing."""
        return SimplifiedChristianAnalysisService()
    
    @pytest.fixture
    def sample_christian_song(self):
        """Sample song with clear Christian themes."""
        return Song(
            id=1,
            spotify_id='test_song_123',
            title='Amazing Grace',
            artist='Chris Tomlin',
            lyrics="""Amazing grace how sweet the sound
                         That saved a wretch like me
                         I once was lost but now am found
                         Was blind but now I see
                         Jesus Christ my savior Lord"""
        )
    
    @pytest.fixture
    def sample_concerning_song(self):
        """Sample song with concerning content."""
        return Song(
            id=2,
            spotify_id='test_song_456',
            title='Dark Temptations',
            artist='Test Artist',
            lyrics="""Life is meaningless and dark
                         Nothing matters in this world
                         Hate and violence everywhere
                         God damn this broken life"""
        )
    
    @pytest.fixture
    def sample_nuanced_song(self):
        """Sample song requiring nuanced analysis (not obvious)."""
        return Song(
            id=3,
            spotify_id='test_song_789',
            title='Questioning Faith',
            artist='Deeper Artist',
            lyrics="""Sometimes I wonder where you are
                         In the silence of my prayers
                         Though I cannot see your face
                         I choose to trust in your embrace
                         Even when the storms arise"""
        )

    def test_christian_theme_detection_accuracy(self, simplified_service, sample_christian_song):
        """Test that obvious Christian themes are correctly identified."""
        result = simplified_service.analyze_song(
            sample_christian_song.title,
            sample_christian_song.artist,
            sample_christian_song.lyrics
        )
        
        # Baseline Quality Requirements - Now using our improved simplified service
        assert result.scoring_results['final_score'] >= 70, "Strong Christian content should score highly"
        assert len(result.biblical_analysis.get('themes', [])) >= 1, "Should detect biblical themes"
        assert result.scoring_results['quality_level'] in ['Very Low', 'Low', 'Medium'], "Should have low concern level"

    def test_concerning_content_detection(self, simplified_service, sample_concerning_song):
        """Test that concerning content is properly flagged."""
        result = simplified_service.analyze_song(
            sample_concerning_song.title,
            sample_concerning_song.artist,
            sample_concerning_song.lyrics
        )
        
        # Should detect concerning content - Now properly flagged with simplified service
        assert result.scoring_results['final_score'] <= 40, "Concerning content should have low score"
        assert len(result.content_analysis.get('concern_flags', [])) >= 1, "Should flag concerning content"
        assert result.scoring_results['quality_level'] in ['Medium', 'High'], "Should have elevated concern level"

    def test_nuanced_analysis_capability(self, simplified_service, sample_nuanced_song):
        """Test that nuanced content (questioning faith) is handled appropriately."""
        result = simplified_service.analyze_song(
            sample_nuanced_song.title,
            sample_nuanced_song.artist,
            sample_nuanced_song.lyrics
        )
        
        # Should handle nuanced content appropriately - Our improved system recognizes spiritual questioning as positive
        assert result.scoring_results['final_score'] >= 60, "Spiritual questioning content should be scored appropriately"
        assert result.scoring_results['quality_level'] in ['Very Low', 'Low', 'Medium'], "Should recognize spiritual questioning as acceptable"

    def test_educational_value_components(self, simplified_service, sample_christian_song):
        """Test that analysis provides educational value for discernment training."""
        result = simplified_service.analyze_song(
            sample_christian_song.title,
            sample_christian_song.artist,
            sample_christian_song.lyrics
        )
        
        # Educational components must be present
        assert 'explanation' in result.scoring_results, "Must provide explanation for learning"
        assert len(result.scoring_results['explanation']) > 50, "Explanation should be substantial"
        assert 'biblical_analysis' in result.__dict__, "Must include biblical analysis"
        assert 'supporting_scripture' in result.biblical_analysis, "Should connect to scripture"

    def test_consistency_across_multiple_runs(self, simplified_service, sample_christian_song):
        """Test that analysis is consistent across multiple runs."""
        results = []
        for i in range(3):
            result = simplified_service.analyze_song(
                sample_christian_song.title,
                sample_christian_song.artist,
                sample_christian_song.lyrics
            )
            results.append(result.scoring_results['final_score'])
        
        # Should be consistent (within reasonable tolerance)
        score_variance = max(results) - min(results)
        assert score_variance <= 5, "Analysis should be consistent across runs"

    def test_performance_baseline(self, simplified_service, sample_christian_song):
        """Test that analysis completes within reasonable time."""
        import time
        
        start_time = time.time()
        result = simplified_service.analyze_song(
            sample_christian_song.title,
            sample_christian_song.artist,
            sample_christian_song.lyrics
        )
        end_time = time.time()
        
        analysis_time = end_time - start_time
        assert analysis_time < 2.0, f"Analysis should complete quickly, took {analysis_time:.2f}s"
        assert result is not None, "Analysis should produce results"

    def test_error_handling_robustness(self, simplified_service):
        """Test that analyzer handles errors gracefully."""
        # Mock an error in the AI analyzer
        with patch.object(simplified_service.ai_analyzer, 'analyze_comprehensive', 
                         side_effect=Exception("AI service temporarily unavailable")):
            result = simplified_service.analyze_song('Test Title', 'Test Artist', 'Test lyrics...')
            
            # Should handle error gracefully with fallback
            assert result is not None, "Should handle errors gracefully"
            assert result.scoring_results['final_score'] >= 0, "Should provide valid fallback score"

    def test_educational_explanation_quality(self, simplified_service, sample_christian_song):
        """Test that explanations provide quality educational content."""
        result = simplified_service.analyze_song(
            sample_christian_song.title,
            sample_christian_song.artist,
            sample_christian_song.lyrics
        )
        
        explanation = result.scoring_results['explanation']
        
        # Quality checks for educational value
        assert 'Christian' in explanation or 'biblical' in explanation, "Should mention Christian/biblical elements"
        assert len(explanation.split()) >= 10, "Should provide substantive explanation"
        assert any(word in explanation.lower() for word in ['discernment', 'analysis', 'themes', 'content']), \
            "Should use educational terminology" 