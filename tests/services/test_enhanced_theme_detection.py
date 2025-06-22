#!/usr/bin/env python3
"""
TDD Tests for Enhanced Theme Detection
Testing the enhanced theme detection functionality in SimplifiedChristianAnalysisService
"""
import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.simplified_christian_analysis_service import EnhancedAIAnalyzer
from app.utils.analysis.analysis_result import AnalysisResult


class TestEnhancedThemeDetection:
    """Test suite for enhanced theme detection functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analyzer = EnhancedAIAnalyzer()
    
    def test_detect_god_themes(self):
        """Test detection of God-related themes with various keywords"""
        lyrics = "Our Father in heaven, the Creator of all things, the Almighty Lord God"
        title = "Praise to Yahweh"
        existing_themes = []
        
        detected = self.analyzer._detect_additional_themes(lyrics, title, existing_themes)
        
        assert 'God' in detected
        assert len(detected) >= 1
    
    def test_detect_jesus_themes(self):
        """Test detection of Jesus-related themes"""
        lyrics = "Jesus Christ our Savior, the Messiah has come, Lamb of God"
        title = "Christ the Redeemer"
        existing_themes = []
        
        detected = self.analyzer._detect_additional_themes(lyrics, title, existing_themes)
        
        assert 'Jesus' in detected
        assert len(detected) >= 1
    
    def test_detect_multiple_themes(self):
        """Test detection of multiple themes in one song"""
        lyrics = """
        Amazing grace how sweet the sound
        Jesus Christ the Son of God
        His love will set us free
        We worship and praise the Lord
        """
        title = "Amazing Grace"
        existing_themes = []
        
        detected = self.analyzer._detect_additional_themes(lyrics, title, existing_themes)
        
        # Should detect multiple themes
        assert 'grace' in detected
        assert 'Jesus' in detected
        assert 'God' in detected or 'love' in detected  # At least one of these
        assert len(detected) >= 3
    
    def test_empty_input_handling(self):
        """Test handling of empty or None inputs"""
        # Test empty strings
        detected1 = self.analyzer._detect_additional_themes("", "", [])
        assert detected1 == []
        
        # Test None values - should handle gracefully
        detected2 = self.analyzer._detect_additional_themes(None, None, [])
        assert detected2 == []


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 