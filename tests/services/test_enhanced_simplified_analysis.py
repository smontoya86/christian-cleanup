"""
Tests for Enhanced SimplifiedChristianAnalysisService - Incremental Enhancement

Starting with current structure to add biblical foundations for concerns.
"""

import pytest
from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService


class TestEnhancedSimplifiedAnalysis:
    """Test the enhanced analysis service incrementally."""
    
    @pytest.fixture
    def analysis_service(self):
        """Create analysis service instance for testing."""
        return SimplifiedChristianAnalysisService()
    
    def test_current_structure_understanding(self, analysis_service):
        """Test to understand current structure before enhancement."""
        title = "Test Song"
        artist = "Test Artist"
        lyrics = "Simple test lyrics"
        
        result = analysis_service.analyze_song(title, artist, lyrics)
        
        # Verify current structure
        assert hasattr(result, 'content_analysis')
        assert hasattr(result, 'biblical_analysis')
        assert hasattr(result, 'scoring_results')
        
        # Current content analysis structure
        content = result.content_analysis
        assert 'concern_flags' in content
        assert 'detailed_concerns' in content
        assert 'discernment_guidance' in content
        
        # Current biblical analysis structure  
        biblical = result.biblical_analysis
        assert 'themes' in biblical
        assert 'supporting_scripture' in biblical
        assert 'educational_insights' in biblical
        
        print(f"Current concern flags: {content['concern_flags']}")
        print(f"Current detailed concerns: {content['detailed_concerns']}")
        print(f"Current supporting scripture: {biblical['supporting_scripture']}")
        
    def test_concerning_content_current_structure(self, analysis_service):
        """Test what happens with concerning content in current structure."""
        title = "Bad Song"
        artist = "Test Artist"
        lyrics = "This damn song has bad language and talks about getting drunk"
        
        result = analysis_service.analyze_song(title, artist, lyrics)
        
        # Check if concerns are detected
        content = result.content_analysis
        biblical = result.biblical_analysis
        
        print(f"Concern flags for concerning content: {content['concern_flags']}")
        print(f"Detailed concerns: {content['detailed_concerns']}")
        print(f"Scripture references: {biblical['supporting_scripture']}")
        print(f"Educational insights: {biblical['educational_insights']}")
        
        # Current structure should detect concerns but may not provide biblical foundation
        assert len(content['detailed_concerns']) > 0  # Should detect concerns
        
    def test_positive_content_current_structure(self, analysis_service):
        """Test positive content to understand current scripture reference behavior."""
        title = "Amazing Grace"
        artist = "John Newton"
        lyrics = "Amazing grace how sweet the sound that saved a wretch like me"
        
        result = analysis_service.analyze_song(title, artist, lyrics)
        
        biblical = result.biblical_analysis
        content = result.content_analysis
        
        print(f"Themes for positive content: {biblical['themes']}")
        print(f"Scripture references: {biblical['supporting_scripture']}")
        print(f"Educational insights: {biblical['educational_insights']}")
        
        # Should have themes and scripture references for positive content
        assert len(biblical['themes']) > 0
        assert len(biblical['supporting_scripture']) > 0 