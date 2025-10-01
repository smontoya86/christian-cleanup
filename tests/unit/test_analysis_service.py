"""
Unit tests for SimplifiedChristianAnalysisService
"""

import pytest
from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService


class TestAnalysisServiceInitialization:
    """Test service initialization"""
    
    def test_init_service(self):
        """Test service initializes correctly"""
        service = SimplifiedChristianAnalysisService()
        assert service.analyzer is not None
        assert service.concern_detector is not None
        assert service.scripture_mapper is not None
    
    def test_analyzer_type(self):
        """Test analyzer is RouterAnalyzer"""
        service = SimplifiedChristianAnalysisService()
        from app.services.analyzers.router_analyzer import RouterAnalyzer
        assert isinstance(service.analyzer, RouterAnalyzer)
    
    def test_stub_services(self):
        """Test stub services exist for backward compatibility"""
        service = SimplifiedChristianAnalysisService()
        
        # Concern detector stub
        concerns = service.concern_detector.analyze_content_concerns(
            'Test', 'Test', 'Test'
        )
        assert 'detailed_concerns' in concerns
        assert concerns['detailed_concerns'] == []
        
        # Scripture mapper stub
        passages = service.scripture_mapper.find_relevant_passages([])
        assert passages == []


class TestAnalysisServiceAnalysis:
    """Test analysis functionality"""
    
    def test_analyze_song_content(self, mock_analysis_service):
        """Test song content analysis"""
        service = SimplifiedChristianAnalysisService()
        
        result = service.analyze_song_content(
            'Amazing Grace',
            'John Newton',
            'Amazing grace, how sweet the sound...'
        )
        
        assert 'overall_score' in result or 'score' in result
        assert 'verdict' in result
        assert 'biblical_analysis' in result or 'themes' in result
    
    def test_analyze_empty_lyrics(self):
        """Test analysis with empty lyrics"""
        service = SimplifiedChristianAnalysisService()
        
        result = service.analyze_song_content(
            'Test Song',
            'Test Artist',
            ''
        )
        
        # Should still return valid structure
        assert 'overall_score' in result or 'score' in result
    
    def test_precision_report(self):
        """Test get_analysis_precision_report"""
        service = SimplifiedChristianAnalysisService()
        report = service.get_analysis_precision_report()
        
        assert 'precision_tracking' in report
        assert 'system_status' in report
        assert 'analyzer_type' in report
        assert 'OpenAI' in report['analyzer_type']

