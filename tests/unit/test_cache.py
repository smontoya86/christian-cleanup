"""
Tests for Redis cache service.
"""
import pytest
import json
import time
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models.models import User, Playlist, Song, AnalysisResult


class TestRedisCache:
    """Test Redis cache service functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        yield
        self.app_context.pop()
    
    def test_cache_service_initialization(self):
        """Test that cache service can be initialized."""
        from app.utils.cache import RedisCache
        
        cache = RedisCache()
        assert cache is not None
        
        # Test initialization with app
        cache.init_app(self.app)
        assert cache.app == self.app
        assert 'redis_cache' in self.app.extensions
    
    @patch('app.utils.cache.redis.from_url')
    def test_cache_get_hit(self, mock_redis):
        """Test cache get with hit."""
        from app.utils.cache import RedisCache
        
        # Mock Redis client
        mock_client = MagicMock()
        mock_client.get.return_value = '{"test": "value"}'
        mock_redis.return_value = mock_client
        
        cache = RedisCache(self.app)
        result = cache.get('test_key')
        
        assert result == {"test": "value"}
        assert cache.cache_hits == 1
        assert cache.cache_misses == 0
        mock_client.get.assert_called_once_with('test_key')
    
    @patch('app.utils.cache.redis.from_url')
    def test_cache_get_miss(self, mock_redis):
        """Test cache get with miss."""
        from app.utils.cache import RedisCache
        
        # Mock Redis client
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client
        
        cache = RedisCache(self.app)
        result = cache.get('test_key')
        
        assert result is None
        assert cache.cache_hits == 0
        assert cache.cache_misses == 1
        mock_client.get.assert_called_once_with('test_key')
    
    @patch('app.utils.cache.redis.from_url')
    def test_cache_set(self, mock_redis):
        """Test cache set operation."""
        from app.utils.cache import RedisCache
        
        # Mock Redis client
        mock_client = MagicMock()
        mock_client.setex.return_value = True
        mock_redis.return_value = mock_client
        
        cache = RedisCache(self.app)
        result = cache.set('test_key', {"test": "value"}, 300)
        
        assert result is True
        mock_client.setex.assert_called_once_with('test_key', 300, '{"test": "value"}')
    
    @patch('app.utils.cache.redis.from_url')
    def test_cache_delete(self, mock_redis):
        """Test cache delete operation."""
        from app.utils.cache import RedisCache
        
        # Mock Redis client
        mock_client = MagicMock()
        mock_client.delete.return_value = 1
        mock_redis.return_value = mock_client
        
        cache = RedisCache(self.app)
        result = cache.delete('test_key')
        
        assert result == 1
        mock_client.delete.assert_called_once_with('test_key')
    
    @patch('app.utils.cache.redis.from_url')
    def test_cache_delete_pattern(self, mock_redis):
        """Test cache delete pattern operation."""
        from app.utils.cache import RedisCache
        
        # Mock Redis client
        mock_client = MagicMock()
        mock_client.keys.return_value = ['key1', 'key2', 'key3']
        mock_client.delete.return_value = 3
        mock_redis.return_value = mock_client
        
        cache = RedisCache(self.app)
        result = cache.delete_pattern('key*')
        
        assert result == 3
        mock_client.keys.assert_called_once_with('key*')
        mock_client.delete.assert_called_once_with('key1', 'key2', 'key3')
    
    @patch('app.utils.cache.redis.from_url')
    def test_cache_metrics(self, mock_redis):
        """Test cache metrics calculation."""
        from app.utils.cache import RedisCache
        
        # Mock Redis client
        mock_client = MagicMock()
        mock_redis.return_value = mock_client
        
        cache = RedisCache(self.app)
        cache.cache_hits = 75
        cache.cache_misses = 25
        
        metrics = cache.get_metrics()
        
        assert metrics['hits'] == 75
        assert metrics['misses'] == 25
        assert metrics['total'] == 100
        assert metrics['hit_rate'] == 75.0
    
    @patch('app.utils.cache.redis.from_url')
    def test_cache_redis_error_handling(self, mock_redis):
        """Test cache error handling when Redis is unavailable."""
        from app.utils.cache import RedisCache
        import redis as redis_module
        
        # Mock Redis client to raise error
        mock_client = MagicMock()
        mock_client.get.side_effect = redis_module.RedisError("Connection failed")
        mock_redis.return_value = mock_client
        
        cache = RedisCache(self.app)
        result = cache.get('test_key')
        
        assert result is None
        assert cache.cache_misses == 1


class TestCacheDecorator:
    """Test cache decorator functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        yield
        self.app_context.pop()
    
    @patch('app.utils.cache.cache')
    def test_cached_decorator_hit(self, mock_cache):
        """Test cached decorator with cache hit."""
        from app.utils.cache import cached
        
        mock_cache.get.return_value = {"result": "cached"}
        
        @cached(expiry=300, key_prefix='test')
        def test_function(arg1, arg2=None):
            return {"result": "original"}
        
        result = test_function("value1", arg2="value2")
        
        assert result == {"result": "cached"}
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_not_called()
    
    @patch('app.utils.cache.cache')
    def test_cached_decorator_miss(self, mock_cache):
        """Test cached decorator with cache miss."""
        from app.utils.cache import cached
        
        mock_cache.get.return_value = None
        
        @cached(expiry=300, key_prefix='test')
        def test_function(arg1, arg2=None):
            return {"result": "original"}
        
        result = test_function("value1", arg2="value2")
        
        assert result == {"result": "original"}
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()
    
    @patch('app.utils.cache.cache')
    def test_cached_decorator_key_generation(self, mock_cache):
        """Test cached decorator key generation."""
        from app.utils.cache import cached
        
        mock_cache.get.return_value = None
        
        @cached(expiry=300, key_prefix='test')
        def test_function(arg1, arg2=None):
            return {"result": "original"}
        
        test_function("value1", arg2="value2")
        
        # Verify the cache key was generated correctly
        call_args = mock_cache.get.call_args[0]
        cache_key = call_args[0]
        
        assert cache_key.startswith('test:test_function')
        assert 'arg2:value2' in cache_key
        assert 'value1' in cache_key


class TestCacheInvalidation:
    """Test cache invalidation functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        yield
        self.app_context.pop()
    
    @patch('app.utils.cache.cache')
    def test_invalidate_playlist_cache_specific(self, mock_cache):
        """Test invalidating specific playlist cache."""
        from app.utils.cache import invalidate_playlist_cache
        
        invalidate_playlist_cache(playlist_id=123)
        
        # Should delete specific playlist cache and dashboard cache
        assert mock_cache.delete_pattern.call_count == 2
        calls = mock_cache.delete_pattern.call_args_list
        
        # Check that specific playlist pattern was called
        playlist_pattern_called = any('playlist_id:123' in str(call) for call in calls)
        assert playlist_pattern_called
        
        # Check that dashboard pattern was called
        dashboard_pattern_called = any('dashboard' in str(call) for call in calls)
        assert dashboard_pattern_called
    
    @patch('app.utils.cache.cache')
    def test_invalidate_playlist_cache_all(self, mock_cache):
        """Test invalidating all playlist caches."""
        from app.utils.cache import invalidate_playlist_cache
        
        invalidate_playlist_cache()
        
        # Should delete all playlist caches and dashboard cache
        assert mock_cache.delete_pattern.call_count == 2
        calls = mock_cache.delete_pattern.call_args_list
        
        # Check patterns
        patterns = [str(call) for call in calls]
        assert any('playlist_detail' in pattern for pattern in patterns)
        assert any('dashboard' in pattern for pattern in patterns)
    
    @patch('app.utils.cache.cache')
    @patch('app.models.models.PlaylistSong')
    def test_invalidate_analysis_cache(self, mock_playlist_song, mock_cache):
        """Test invalidating analysis-related caches."""
        from app.utils.cache import invalidate_analysis_cache
        
        # Mock playlist songs
        mock_ps1 = MagicMock()
        mock_ps1.playlist_id = 1
        mock_ps2 = MagicMock()
        mock_ps2.playlist_id = 2
        
        mock_playlist_song.query.filter_by.return_value.all.return_value = [mock_ps1, mock_ps2]
        
        invalidate_analysis_cache(song_id=123)
        
        # Should invalidate caches for playlists containing the song
        mock_playlist_song.query.filter_by.assert_called_once_with(song_id=123)
        
        # Should call delete_pattern multiple times for different playlists
        assert mock_cache.delete_pattern.call_count >= 2


class TestCacheConfiguration:
    """Test cache configuration and setup."""
    
    def test_cache_config_in_app(self):
        """Test that cache configuration is properly set in app."""
        app = create_app('testing')
        
        # Check that Redis URL is configured
        assert 'RQ_REDIS_URL' in app.config
        
        # Check that cache is initialized
        with app.app_context():
            assert 'redis_cache' in app.extensions
    
    def test_cache_fallback_when_redis_unavailable(self):
        """Test that application works when Redis is unavailable."""
        from app.utils.cache import RedisCache
        import redis as redis_module
        
        app = create_app('testing')
        
        with patch('app.utils.cache.redis.from_url') as mock_redis:
            mock_redis.side_effect = redis_module.ConnectionError("Redis unavailable")
            
            cache = RedisCache()
            
            # Should handle Redis unavailability gracefully
            with app.app_context():
                result = cache.get('test_key')
                assert result is None
                
                # Set should return False but not crash
                set_result = cache.set('test_key', 'value')
                assert set_result is False 