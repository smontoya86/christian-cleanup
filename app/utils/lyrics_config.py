"""
Configuration management for LyricsFetcher rate limiting and caching
"""
import os
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class LyricsFetcherConfig:
    """Configuration class for LyricsFetcher rate limiting and caching"""
    
    # Rate limiting configuration
    rate_limit_window_size: int = 60  # seconds
    rate_limit_max_requests: int = 60  # requests per window
    rate_limit_threshold: float = 0.8  # threshold for "approaching limit" warning
    
    # Token bucket configuration
    token_bucket_capacity: int = 10  # maximum tokens
    token_bucket_refill_rate: float = 1.0  # tokens per second
    
    # Retry configuration
    max_retries: int = 5  # maximum retry attempts
    base_delay: float = 2.0  # base delay for exponential backoff (seconds)
    max_delay: float = 60.0  # maximum delay between retries (seconds)
    jitter_factor: float = 0.1  # jitter factor for randomization
    
    # Cache configuration
    default_cache_ttl: int = 7 * 24 * 60 * 60  # 7 days in seconds
    negative_cache_ttl: int = 24 * 60 * 60  # 1 day for not found results
    error_cache_ttl: int = 12 * 60 * 60  # 12 hours for error results
    cache_cleanup_interval: int = 60 * 60  # 1 hour between cleanup runs
    
    # Batch Cache Configuration (NEW - for database optimization)
    cache_batch_size: int = 50  # Number of cache operations to batch together
    cache_batch_timeout: int = 30  # Seconds to wait before forcing batch commit
    
    # Genius API configuration
    genius_timeout: int = 15  # API timeout in seconds (increased from 5)
    genius_sleep_time: float = 0.1  # sleep between requests
    genius_retries: int = 2  # Genius client internal retries
    genius_excluded_terms: Optional[List[str]] = None  # excluded terms for search
    
    # Logging configuration
    log_rate_limit_events: bool = True
    log_cache_operations: bool = True
    log_retry_attempts: bool = True
    log_api_calls: bool = True
    log_performance_metrics: bool = True
    
    # Monitoring configuration
    enable_metrics_collection: bool = True
    metrics_collection_interval: int = 300  # 5 minutes
    
    def __post_init__(self):
        """Initialize default values and validate configuration"""
        if self.genius_excluded_terms is None:
            self.genius_excluded_terms = ["(Remix)", "(Live)", "(Acoustic)", "(Demo)"]
        
        # Validate configuration values
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values"""
        if self.rate_limit_max_requests <= 0:
            raise ValueError("rate_limit_max_requests must be positive")
        
        if self.rate_limit_window_size <= 0:
            raise ValueError("rate_limit_window_size must be positive")
        
        if not 0 < self.rate_limit_threshold <= 1:
            raise ValueError("rate_limit_threshold must be between 0 and 1")
        
        if self.token_bucket_capacity <= 0:
            raise ValueError("token_bucket_capacity must be positive")
        
        if self.token_bucket_refill_rate <= 0:
            raise ValueError("token_bucket_refill_rate must be positive")
        
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        
        if self.default_cache_ttl <= 0:
            raise ValueError("default_cache_ttl must be positive")
    
    @classmethod
    def from_environment(cls) -> 'LyricsFetcherConfig':
        """Create configuration from environment variables"""
        return cls(
            # Rate limiting
            rate_limit_window_size=int(os.getenv('LYRICS_RATE_LIMIT_WINDOW', 60)),
            rate_limit_max_requests=int(os.getenv('LYRICS_RATE_LIMIT_MAX_REQUESTS', 60)),
            rate_limit_threshold=float(os.getenv('LYRICS_RATE_LIMIT_THRESHOLD', 0.8)),
            
            # Token bucket
            token_bucket_capacity=int(os.getenv('LYRICS_TOKEN_BUCKET_CAPACITY', 10)),
            token_bucket_refill_rate=float(os.getenv('LYRICS_TOKEN_BUCKET_REFILL_RATE', 1.0)),
            
            # Retry
            max_retries=int(os.getenv('LYRICS_MAX_RETRIES', 5)),
            base_delay=float(os.getenv('LYRICS_BASE_DELAY', 2.0)),
            max_delay=float(os.getenv('LYRICS_MAX_DELAY', 60.0)),
            jitter_factor=float(os.getenv('LYRICS_JITTER_FACTOR', 0.1)),
            
            # Cache
            default_cache_ttl=int(os.getenv('LYRICS_DEFAULT_CACHE_TTL', 7 * 24 * 60 * 60)),
            negative_cache_ttl=int(os.getenv('LYRICS_NEGATIVE_CACHE_TTL', 24 * 60 * 60)),
            error_cache_ttl=int(os.getenv('LYRICS_ERROR_CACHE_TTL', 12 * 60 * 60)),
            cache_cleanup_interval=int(os.getenv('LYRICS_CACHE_CLEANUP_INTERVAL', 60 * 60)),
            
            # Batch Cache Configuration
            cache_batch_size=int(os.getenv('LYRICS_CACHE_BATCH_SIZE', 50)),
            cache_batch_timeout=int(os.getenv('LYRICS_CACHE_BATCH_TIMEOUT', 30)),
            
            # Genius API
            genius_timeout=int(os.getenv('LYRICS_GENIUS_TIMEOUT', 5)),
            genius_sleep_time=float(os.getenv('LYRICS_GENIUS_SLEEP_TIME', 0.1)),
            genius_retries=int(os.getenv('LYRICS_GENIUS_RETRIES', 2)),
            
            # Logging
            log_rate_limit_events=os.getenv('LYRICS_LOG_RATE_LIMIT_EVENTS', 'true').lower() == 'true',
            log_cache_operations=os.getenv('LYRICS_LOG_CACHE_OPERATIONS', 'true').lower() == 'true',
            log_retry_attempts=os.getenv('LYRICS_LOG_RETRY_ATTEMPTS', 'true').lower() == 'true',
            log_api_calls=os.getenv('LYRICS_LOG_API_CALLS', 'true').lower() == 'true',
            log_performance_metrics=os.getenv('LYRICS_LOG_PERFORMANCE_METRICS', 'true').lower() == 'true',
            
            # Monitoring
            enable_metrics_collection=os.getenv('LYRICS_ENABLE_METRICS', 'true').lower() == 'true',
            metrics_collection_interval=int(os.getenv('LYRICS_METRICS_INTERVAL', 300)),
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        return {
            'rate_limiting': {
                'window_size': self.rate_limit_window_size,
                'max_requests': self.rate_limit_max_requests,
                'threshold': self.rate_limit_threshold,
            },
            'token_bucket': {
                'capacity': self.token_bucket_capacity,
                'refill_rate': self.token_bucket_refill_rate,
            },
            'retry': {
                'max_retries': self.max_retries,
                'base_delay': self.base_delay,
                'max_delay': self.max_delay,
                'jitter_factor': self.jitter_factor,
            },
            'cache': {
                'default_ttl': self.default_cache_ttl,
                'negative_ttl': self.negative_cache_ttl,
                'error_ttl': self.error_cache_ttl,
                'cleanup_interval': self.cache_cleanup_interval,
            },
            'batch_cache': {
                'size': self.cache_batch_size,
                'timeout': self.cache_batch_timeout,
            },
            'genius_api': {
                'timeout': self.genius_timeout,
                'sleep_time': self.genius_sleep_time,
                'retries': self.genius_retries,
                'excluded_terms': self.genius_excluded_terms,
            },
            'logging': {
                'rate_limit_events': self.log_rate_limit_events,
                'cache_operations': self.log_cache_operations,
                'retry_attempts': self.log_retry_attempts,
                'api_calls': self.log_api_calls,
                'performance_metrics': self.log_performance_metrics,
            },
            'monitoring': {
                'enable_metrics': self.enable_metrics_collection,
                'collection_interval': self.metrics_collection_interval,
            }
        }


# Global configuration instance
_config: Optional[LyricsFetcherConfig] = None


def get_config() -> LyricsFetcherConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = LyricsFetcherConfig.from_environment()
    return _config


def set_config(config: LyricsFetcherConfig):
    """Set the global configuration instance"""
    global _config
    _config = config


def reset_config():
    """Reset configuration to default (reload from environment)"""
    global _config
    _config = None 