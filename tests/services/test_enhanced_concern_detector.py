#!/usr/bin/env python3
"""
TDD Tests for Enhanced Concern Detection
Testing the enhanced concern detection functionality
"""
import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.enhanced_concern_detector import EnhancedConcernDetector


class TestEnhancedConcernDetector:
    """Test suite for enhanced concern detection functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.detector = EnhancedConcernDetector()
    
    def test_detect_language_concerns(self):
        """Test detection of inappropriate language"""
        lyrics = "This is damn hard, what the hell are we doing"
        title = "Bad Language Song"
        artist = "Test Artist"
        
        result = self.detector.analyze_content_concerns(title, artist, lyrics)
        
        assert 'detailed_concerns' in result
        assert len(result['detailed_concerns']) > 0
        
        # Should detect language concerns
        concern_types = [c['category'] for c in result['detailed_concerns']]
        assert 'Language and Expression' in concern_types
    
    def test_detect_substance_concerns(self):
        """Test detection of substance use references"""
        lyrics = "Let's get drunk tonight, party with alcohol and drugs"
        title = "Party Night"
        artist = "Test Artist"
        
        result = self.detector.analyze_content_concerns(title, artist, lyrics)
        
        assert 'detailed_concerns' in result
        concern_types = [c['category'] for c in result['detailed_concerns']]
        assert 'Substance Use' in concern_types
    
    def test_clean_content_no_concerns(self):
        """Test that clean content raises no concerns"""
        lyrics = "God is good, His love endures forever, praise the Lord"
        title = "Praise Song"
        artist = "Test Artist"
        
        result = self.detector.analyze_content_concerns(title, artist, lyrics)
        
        assert 'detailed_concerns' in result
        assert len(result['detailed_concerns']) == 0
    
    def test_concern_analysis_structure(self):
        """Test that concern analysis returns proper structure"""
        lyrics = "This damn song"
        title = "Test Song"
        artist = "Test Artist"
        
        result = self.detector.analyze_content_concerns(title, artist, lyrics)
        
        # Check basic structure
        assert 'detailed_concerns' in result
        assert 'concern_score' in result
        # Overall level field may vary in name
        
        # If concerns exist, check their structure
        if result['detailed_concerns']:
            concern = result['detailed_concerns'][0]
            assert 'category' in concern
            assert 'severity' in concern
            assert 'biblical_perspective' in concern
            assert 'explanation' in concern
    
    def test_empty_input_handling(self):
        """Test handling of empty inputs"""
        result = self.detector.analyze_content_concerns("", "", "")
        
        assert 'detailed_concerns' in result
        assert 'concern_score' in result
        assert result['concern_score'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 