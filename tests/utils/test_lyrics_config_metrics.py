"""
Tests for LyricsFetcher configuration and metrics functionality
"""
import pytest
import time
import os
from unittest.mock import patch, Mock
from app.utils.lyrics import LyricsFetcher
from app.utils.lyrics_config import LyricsFetcherConfig, get_config, set_config, reset_config
from app.utils.lyrics_metrics import get_metrics_collector, reset_metrics_collector


class TestLyricsFetcherConfiguration:
    """Test suite for LyricsFetcher configuration management"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Reset configuration and metrics before each test
        reset_config()
        reset_metrics_collector()
    
    def test_default_configuration(self):
        """Test that default configuration is loaded correctly"""
        fetcher = LyricsFetcher()
        config = fetcher.config
        
        # Test default values
        assert config.rate_limit_window_size == 60
        assert config.rate_limit_max_requests == 60
        assert config.token_bucket_capacity == 10
        assert config.token_bucket_refill_rate == 1.0
        assert config.max_retries == 5
        assert config.default_cache_ttl == 7 * 24 * 60 * 60  # 7 days
    
    def test_custom_configuration(self):
        """Test that custom configuration is applied correctly"""
        custom_config = LyricsFetcherConfig(
            rate_limit_max_requests=30,
            token_bucket_capacity=5,
            max_retries=3,
            default_cache_ttl=3600  # 1 hour
        )
        
        fetcher = LyricsFetcher(config=custom_config)
        
        assert fetcher.config.rate_limit_max_requests == 30
        assert fetcher.config.token_bucket_capacity == 5
        assert fetcher.config.max_retries == 3
        assert fetcher.config.default_cache_ttl == 3600
        
        # Verify components use the custom configuration
        assert fetcher.rate_tracker.max_requests == 30
        assert fetcher.token_bucket.capacity == 5
    
    def test_environment_configuration(self):
        """Test configuration loading from environment variables"""
        env_vars = {
            'LYRICS_RATE_LIMIT_MAX_REQUESTS': '40',
            'LYRICS_TOKEN_BUCKET_CAPACITY': '15',
            'LYRICS_MAX_RETRIES': '7',
            'LYRICS_DEFAULT_CACHE_TTL': '86400'  # 1 day
        }
        
        with patch.dict(os.environ, env_vars):
            config = LyricsFetcherConfig.from_environment()
            
            assert config.rate_limit_max_requests == 40
            assert config.token_bucket_capacity == 15
            assert config.max_retries == 7
            assert config.default_cache_ttl == 86400
    
    def test_configuration_validation(self):
        """Test that invalid configuration values raise errors"""
        with pytest.raises(ValueError, match="rate_limit_max_requests must be positive"):
            LyricsFetcherConfig(rate_limit_max_requests=0)
        
        with pytest.raises(ValueError, match="token_bucket_capacity must be positive"):
            LyricsFetcherConfig(token_bucket_capacity=-1)
        
        with pytest.raises(ValueError, match="rate_limit_threshold must be between 0 and 1"):
            LyricsFetcherConfig(rate_limit_threshold=1.5)
    
    def test_configuration_export(self):
        """Test configuration export to dictionary"""
        config = LyricsFetcherConfig(
            rate_limit_max_requests=50,
            token_bucket_capacity=8
        )
        
        config_dict = config.to_dict()
        
        assert config_dict['rate_limiting']['max_requests'] == 50
        assert config_dict['token_bucket']['capacity'] == 8
        assert 'cache' in config_dict
        assert 'genius_api' in config_dict
        assert 'logging' in config_dict
    
    def test_configuration_update(self):
        """Test updating configuration on existing LyricsFetcher instance"""
        fetcher = LyricsFetcher()
        original_max_requests = fetcher.rate_tracker.max_requests
        
        # Update configuration
        new_config = LyricsFetcherConfig(rate_limit_max_requests=100)
        fetcher.update_configuration(new_config)
        
        # Verify configuration was updated
        assert fetcher.config.rate_limit_max_requests == 100
        assert fetcher.rate_tracker.max_requests == 100
        assert fetcher.rate_tracker.max_requests != original_max_requests


class TestLyricsFetcherMetrics:
    """Test suite for LyricsFetcher metrics collection"""
    
    def setup_method(self):
        """Set up test fixtures"""
        reset_config()
        reset_metrics_collector()
        self.fetcher = LyricsFetcher()
    
    def test_metrics_initialization(self):
        """Test that metrics collector is properly initialized"""
        assert self.fetcher.metrics is not None
        assert hasattr(self.fetcher.metrics, 'record_event')
        assert hasattr(self.fetcher.metrics, 'get_summary')
    
    def test_api_call_metrics(self):
        """Test that API call metrics are recorded correctly"""
        # Record some API calls
        self.fetcher.metrics.record_api_call(0.5, success=True)
        self.fetcher.metrics.record_api_call(1.2, success=False)
        
        summary = self.fetcher.metrics.get_summary()
        
        assert summary.total_events > 0
        assert summary.success_rate == 0.5  # 1 success out of 2 calls
        assert summary.average_response_time == 0.85  # (0.5 + 1.2) / 2
    
    def test_cache_operation_metrics(self):
        """Test that cache operation metrics are recorded correctly"""
        # Record cache operations
        self.fetcher.metrics.record_cache_operation('lookup', hit=True)
        self.fetcher.metrics.record_cache_operation('lookup', hit=False)
        self.fetcher.metrics.record_cache_operation('store')
        
        summary = self.fetcher.metrics.get_summary()
        
        assert summary.cache_hit_rate == 0.5  # 1 hit out of 2 lookups
    
    def test_rate_limit_metrics(self):
        """Test that rate limit events are recorded correctly"""
        # Record rate limit events
        self.fetcher.metrics.record_rate_limit_event('hit', delay=2.0)
        self.fetcher.metrics.record_rate_limit_event('approaching')
        
        summary = self.fetcher.metrics.get_summary()
        
        assert summary.rate_limit_events == 2
    
    def test_retry_metrics(self):
        """Test that retry attempt metrics are recorded correctly"""
        # Record retry attempts
        self.fetcher.metrics.record_retry_attempt(1, delay=1.0)
        self.fetcher.metrics.record_retry_attempt(2, delay=2.0)
        
        summary = self.fetcher.metrics.get_summary()
        
        assert summary.retry_events == 2
    
    def test_error_metrics(self):
        """Test that error metrics are recorded correctly"""
        # Record errors
        self.fetcher.metrics.record_error('network_error')
        self.fetcher.metrics.record_error('api_error')
        
        summary = self.fetcher.metrics.get_summary()
        
        assert summary.error_events == 2
    
    def test_detailed_metrics(self):
        """Test detailed metrics collection"""
        # Record various events
        self.fetcher.metrics.record_api_call(0.5, success=True)
        self.fetcher.metrics.record_cache_operation('hit')
        self.fetcher.metrics.record_error('test_error')
        
        detailed_stats = self.fetcher.get_detailed_metrics()
        
        assert 'total_events' in detailed_stats
        assert 'event_types' in detailed_stats
        assert 'collection_period' in detailed_stats
        assert detailed_stats['total_events'] >= 3
    
    def test_metrics_reset(self):
        """Test metrics reset functionality"""
        # Record some events
        self.fetcher.metrics.record_api_call(0.5, success=True)
        self.fetcher.metrics.record_cache_operation('hit')
        
        # Verify events were recorded
        summary_before = self.fetcher.metrics.get_summary()
        assert summary_before.total_events > 0
        
        # Reset metrics
        self.fetcher.reset_metrics()
        
        # Verify metrics were reset
        summary_after = self.fetcher.metrics.get_summary()
        assert summary_after.total_events == 0
    
    def test_cache_stats_with_metrics(self):
        """Test that cache stats include metrics information"""
        # Record some events to populate metrics
        self.fetcher.metrics.record_api_call(0.5, success=True)
        self.fetcher.metrics.record_cache_operation('lookup', hit=True)
        
        stats = self.fetcher.get_cache_stats()
        
        # Verify cache stats structure
        assert 'cache_size' in stats
        assert 'metrics_summary' in stats
        assert 'configuration' in stats
        
        # Verify metrics summary is included
        metrics_summary = stats['metrics_summary']
        assert 'total_events' in metrics_summary
        assert 'success_rate' in metrics_summary
        assert 'cache_hit_rate' in metrics_summary
        
        # Verify configuration is included
        config_info = stats['configuration']
        assert 'rate_limit_max_requests' in config_info
        assert 'token_bucket_capacity' in config_info


class TestIntegratedFunctionality:
    """Test suite for integrated configuration and metrics functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        reset_config()
        reset_metrics_collector()
    
    @patch('app.utils.lyrics.time.sleep')  # Mock sleep to speed up tests
    def test_fetch_lyrics_with_metrics_and_config(self, mock_sleep):
        """Test that fetch_lyrics properly uses configuration and records metrics"""
        # Create custom configuration
        config = LyricsFetcherConfig(
            log_api_calls=True,
            log_cache_operations=True,
            default_cache_ttl=3600
        )
        
        # Mock genius client
        mock_song = Mock()
        mock_song.lyrics = "Test lyrics content"
        mock_genius = Mock()
        mock_genius.search_song.return_value = mock_song
        
        fetcher = LyricsFetcher(config=config)
        fetcher.genius = mock_genius
        
        # Fetch lyrics
        result = fetcher.fetch_lyrics("Test Song", "Test Artist")
        
        # Verify result
        assert result == "Test lyrics content"
        
        # Verify metrics were recorded
        summary = fetcher.metrics.get_summary()
        assert summary.total_events > 0
        
        # Verify cache stats include all information
        stats = fetcher.get_cache_stats()
        assert stats['cache_size'] == 1  # One cached entry
        assert stats['configuration']['default_cache_ttl'] == 3600
    
    def test_configuration_affects_behavior(self):
        """Test that configuration changes actually affect behavior"""
        # Test with different retry configurations
        config_low_retries = LyricsFetcherConfig(max_retries=1)
        config_high_retries = LyricsFetcherConfig(max_retries=5)
        
        fetcher_low = LyricsFetcher(config=config_low_retries)
        fetcher_high = LyricsFetcher(config=config_high_retries)
        
        # Verify different configurations
        assert fetcher_low.config.max_retries == 1
        assert fetcher_high.config.max_retries == 5
        
        # Test with different cache TTL configurations
        config_short_cache = LyricsFetcherConfig(default_cache_ttl=60)
        config_long_cache = LyricsFetcherConfig(default_cache_ttl=86400)
        
        fetcher_short = LyricsFetcher(config=config_short_cache)
        fetcher_long = LyricsFetcher(config=config_long_cache)
        
        assert fetcher_short.config.default_cache_ttl == 60
        assert fetcher_long.config.default_cache_ttl == 86400 