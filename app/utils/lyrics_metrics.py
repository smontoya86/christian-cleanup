"""
Simple lyrics metrics tracking.
Provides minimal interface for metrics collection without complex monitoring.
"""
import time
from typing import Dict, Any, Optional

class LyricsMetricsCollector:
    """Simple metrics collector for lyrics operations."""
    
    def __init__(self):
        self.metrics = {}
    
    def record_fetch_attempt(self, source: str, success: bool, duration: float = 0.0):
        """Record a lyrics fetch attempt."""
        pass  # Simplified - no actual tracking
    
    def record_cache_hit(self, source: str):
        """Record a cache hit."""
        pass  # Simplified - no actual tracking
    
    def record_cache_miss(self, source: str):
        """Record a cache miss."""
        pass  # Simplified - no actual tracking
    
    def record_event(self, event_name: str, **kwargs):
        """Record a generic event."""
        pass  # Simplified - no actual tracking
    
    def record_error(self, error_name: str, **kwargs):
        """Record an error event."""
        pass  # Simplified - no actual tracking
    
    def record_cache_operation(self, operation: str, **kwargs):
        """Record a cache operation."""
        pass  # Simplified - no actual tracking
    
    def record_api_call(self, duration: float, **kwargs):
        """Record an API call."""
        pass  # Simplified - no actual tracking
    
    def record_retry_attempt(self, attempt: int, sleep_time: float, **kwargs):
        """Record a retry attempt."""
        pass  # Simplified - no actual tracking
    
    def record_rate_limit_event(self, event_type: str, sleep_time: float = 0.0, **kwargs):
        """Record a rate limit event."""
        pass  # Simplified - no actual tracking
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic stats."""
        return {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_response_time': 0.0
        }

# Global instance for backward compatibility
_metrics_collector = LyricsMetricsCollector()

def get_metrics_collector() -> LyricsMetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector 