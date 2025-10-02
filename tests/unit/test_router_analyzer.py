"""
Unit tests for RouterAnalyzer (OpenAI-powered)
"""

import pytest
import os
from unittest.mock import Mock, patch
from app.services.analyzers.router_analyzer import RouterAnalyzer


class TestRouterAnalyzer:
    """Test RouterAnalyzer initialization and configuration"""
    
    def test_init_with_api_key(self):
        """Test analyzer initializes with API key"""
        analyzer = RouterAnalyzer()
        assert analyzer.api_key is not None
        assert analyzer.model is not None
        assert analyzer.base_url is not None
    
    def test_init_without_api_key(self, monkeypatch):
        """Test analyzer fails without API key"""
        monkeypatch.setenv('OPENAI_API_KEY', '')
        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            RouterAnalyzer()
    
    def test_default_configuration(self):
        """Test default configuration values"""
        analyzer = RouterAnalyzer()
        assert analyzer.temperature == 0.2
        assert analyzer.max_tokens > 0  # Just verify it's set (can vary by env)
        assert analyzer.timeout > 0  # Just verify it's set
    
    def test_custom_configuration(self, monkeypatch):
        """Test custom configuration via environment"""
        monkeypatch.setenv('LLM_TEMPERATURE', '0.5')
        monkeypatch.setenv('LLM_MAX_TOKENS', '3000')
        monkeypatch.setenv('LLM_TIMEOUT', '120')
        
        analyzer = RouterAnalyzer()
        assert analyzer.temperature == 0.5
        assert analyzer.max_tokens == 3000
        assert analyzer.timeout == 120.0


class TestRouterAnalyzerAnalysis:
    """Test RouterAnalyzer analysis functionality"""
    
    @patch('requests.post')
    def test_analyze_song_success(self, mock_post):
        """Test successful song analysis"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': '''
                    {
                        "score": 85,
                        "verdict": "freely_listen",
                        "formation_risk": "low",
                        "narrative_voice": "artist",
                        "lament_filter_applied": false,
                        "themes_positive": ["Worship (+15)", "Grace (+10)"],
                        "themes_negative": [],
                        "concerns": [],
                        "scripture_references": ["Ephesians 2:8-9"],
                        "analysis": "Strong Christian content"
                    }
                    '''
                }
            }]
        }
        mock_post.return_value = mock_response
        
        analyzer = RouterAnalyzer()
        result = analyzer.analyze_song('Amazing Grace', 'John Newton', 'Amazing grace...')
        
        assert result['score'] == 85
        assert result['verdict'] == 'freely_listen'
        assert 'Worship' in str(result['themes_positive'])
        assert len(result['concerns']) == 0
    
    @patch('requests.post')
    def test_analyze_song_api_error(self, mock_post):
        """Test analysis handles API errors gracefully"""
        mock_post.side_effect = Exception('API Error')
        
        analyzer = RouterAnalyzer()
        result = analyzer.analyze_song('Test Song', 'Test Artist', 'Test lyrics')
        
        # Should return default output
        assert 'score' in result
        assert 'verdict' in result
        assert result['score'] == 50  # Default score
    
    @patch('requests.post')
    def test_analyze_song_invalid_json(self, mock_post):
        """Test analysis handles invalid JSON response"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Invalid JSON response'
                }
            }]
        }
        mock_post.return_value = mock_response
        
        analyzer = RouterAnalyzer()
        result = analyzer.analyze_song('Test Song', 'Test Artist', 'Test lyrics')
        
        # Should return default output
        assert 'score' in result
        assert 'verdict' in result
    
    def test_normalize_output(self):
        """Test output normalization"""
        analyzer = RouterAnalyzer()
        
        raw_output = {
            'score': 75,
            'verdict': 'context_required',
            'themes_positive': ['Faith'],
            'themes_negative': [],
            'concerns': [],
            'scripture_references': ['John 3:16']
        }
        
        normalized = analyzer._normalize_output(raw_output)
        
        assert normalized['score'] == 75
        assert normalized['verdict'] == 'context_required'
        assert 'themes_positive' in normalized
        assert 'scripture_references' in normalized
    
    def test_default_output(self):
        """Test default output structure"""
        analyzer = RouterAnalyzer()
        default = analyzer._default_output()
        
        assert 'score' in default
        assert 'verdict' in default
        assert 'formation_risk' in default
        assert isinstance(default.get('themes_positive', []), list)
        assert isinstance(default.get('concerns', []), list)

