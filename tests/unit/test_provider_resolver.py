"""
Unit tests for provider resolver and analyzer cache
"""

import pytest

from app.services.analyzer_cache import (
    clear_analyzer_cache,
    get_analyzer_info,
    get_shared_analyzer,
    is_analyzer_ready,
)
from app.services.provider_resolver import get_analyzer


class TestProviderResolver:
    """Test provider resolver"""
    
    def test_get_analyzer_returns_router(self):
        """Test get_analyzer returns RouterAnalyzer"""
        from app.services.analyzers.router_analyzer import RouterAnalyzer
        
        analyzer = get_analyzer()
        assert isinstance(analyzer, RouterAnalyzer)
    
    def test_get_analyzer_consistency(self):
        """Test get_analyzer returns consistent instance"""
        analyzer1 = get_analyzer()
        analyzer2 = get_analyzer()
        
        # Should return same type
        assert isinstance(analyzer1, type(analyzer2))


class TestAnalyzerCache:
    """Test analyzer cache functionality"""
    
    def test_get_shared_analyzer(self):
        """Test getting shared analyzer"""
        from app.services.analyzers.router_analyzer import RouterAnalyzer
        
        analyzer = get_shared_analyzer()
        assert isinstance(analyzer, RouterAnalyzer)
    
    def test_cache_singleton(self):
        """Test analyzer cache is singleton"""
        analyzer1 = get_shared_analyzer()
        analyzer2 = get_shared_analyzer()
        
        # Should be same instance
        assert analyzer1 is analyzer2
    
    def test_is_analyzer_ready(self):
        """Test is_analyzer_ready after initialization"""
        # Initialize
        get_shared_analyzer()
        
        # Check readiness
        assert is_analyzer_ready() is True
    
    def test_get_analyzer_info(self):
        """Test getting analyzer info"""
        # Initialize
        get_shared_analyzer()
        
        info = get_analyzer_info()
        assert 'status' in info
        assert 'analyzer_type' in info
        assert 'provider' in info
        assert info['provider'] == 'openai'
    
    def test_clear_cache(self):
        """Test clearing analyzer cache"""
        # Initialize
        get_shared_analyzer()
        assert is_analyzer_ready() is True
        
        # Clear
        clear_analyzer_cache()
        assert is_analyzer_ready() is False
        
        # Re-initialize
        get_shared_analyzer()
        assert is_analyzer_ready() is True


class TestAnalyzerPreflight:
    """Test analyzer preflight checks"""
    
    def test_preflight_with_api_key(self):
        """Test preflight succeeds with API key"""
        from app.services.analyzer_cache import AnalyzerCache
        
        cache = AnalyzerCache()
        ready, message = cache.preflight()
        
        assert ready is True
        assert 'configured' in message.lower()
    
    def test_preflight_without_api_key(self, monkeypatch):
        """Test preflight fails without API key"""
        from app.services.analyzer_cache import AnalyzerCache
        
        monkeypatch.setenv('OPENAI_API_KEY', '')
        
        cache = AnalyzerCache()
        ready, message = cache.preflight()
        
        assert ready is False
        assert 'not configured' in message.lower()

