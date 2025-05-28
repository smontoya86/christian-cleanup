"""
Metrics collection system for LyricsFetcher rate limiting and caching
"""
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricEvent:
    """Represents a single metric event"""
    timestamp: float
    event_type: str
    value: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricsSummary:
    """Summary of metrics over a time period"""
    total_events: int = 0
    events_per_minute: float = 0.0
    events_per_hour: float = 0.0
    success_rate: float = 0.0
    average_response_time: float = 0.0
    cache_hit_rate: float = 0.0
    rate_limit_events: int = 0
    retry_events: int = 0
    error_events: int = 0


class LyricsMetricsCollector:
    """Collects and manages metrics for LyricsFetcher operations"""
    
    def __init__(self, max_events: int = 10000, cleanup_interval: int = 300):
        """
        Initialize metrics collector
        
        Args:
            max_events: Maximum number of events to keep in memory
            cleanup_interval: Interval in seconds to clean up old events
        """
        self.max_events = max_events
        self.cleanup_interval = cleanup_interval
        
        # Thread-safe storage for events
        self._events: deque = deque(maxlen=max_events)
        self._lock = threading.RLock()
        
        # Counters for different event types
        self._counters = defaultdict(int)
        self._timers = defaultdict(list)
        
        # Last cleanup time
        self._last_cleanup = time.time()
        
        # Performance tracking
        self._api_call_times = deque(maxlen=1000)
        self._cache_operations = defaultdict(int)
        self._rate_limit_events = deque(maxlen=100)
        self._retry_events = deque(maxlen=100)
        self._error_events = deque(maxlen=100)
    
    def record_event(self, event_type: str, value: float = 1.0, **metadata):
        """Record a metric event"""
        with self._lock:
            event = MetricEvent(
                timestamp=time.time(),
                event_type=event_type,
                value=value,
                metadata=metadata
            )
            self._events.append(event)
            self._counters[event_type] += 1
            
            # Store specific event types for detailed analysis
            if event_type == 'api_call_time':
                self._api_call_times.append(value)
            elif event_type.startswith('cache_'):
                self._cache_operations[event_type] += 1
            elif event_type == 'rate_limit_hit':
                self._rate_limit_events.append(event)
            elif event_type == 'retry_attempt':
                self._retry_events.append(event)
            elif event_type.startswith('error_'):
                self._error_events.append(event)
            
            # Cleanup old events if needed
            if time.time() - self._last_cleanup > self.cleanup_interval:
                self._cleanup_old_events()
    
    def record_api_call(self, duration: float, success: bool = True, **metadata):
        """Record an API call with timing and success information"""
        self.record_event('api_call', 1.0, duration=duration, success=success, **metadata)
        self.record_event('api_call_time', duration)
        if success:
            self.record_event('api_call_success')
        else:
            self.record_event('api_call_failure')
    
    def record_cache_operation(self, operation: str, hit: bool = None, **metadata):
        """Record a cache operation (hit, miss, store, cleanup)"""
        event_type = f'cache_{operation}'
        self.record_event(event_type, 1.0, **metadata)
        
        if hit is not None:
            if hit:
                self.record_event('cache_hit')
            else:
                self.record_event('cache_miss')
    
    def record_rate_limit_event(self, event_type: str, delay: float = 0.0, **metadata):
        """Record a rate limiting event"""
        self.record_event(f'rate_limit_{event_type}', delay, **metadata)
    
    def record_retry_attempt(self, attempt: int, delay: float, **metadata):
        """Record a retry attempt"""
        self.record_event('retry_attempt', attempt, delay=delay, **metadata)
    
    def record_error(self, error_type: str, **metadata):
        """Record an error event"""
        self.record_event(f'error_{error_type}', 1.0, **metadata)
    
    def get_summary(self, time_window: int = 3600) -> MetricsSummary:
        """
        Get a summary of metrics for the specified time window
        
        Args:
            time_window: Time window in seconds (default: 1 hour)
        """
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - time_window
            
            # Filter events within time window
            recent_events = [e for e in self._events if e.timestamp >= cutoff_time]
            
            if not recent_events:
                return MetricsSummary()
            
            # Calculate basic metrics
            total_events = len(recent_events)
            events_per_minute = (total_events / time_window) * 60
            events_per_hour = (total_events / time_window) * 3600
            
            # Calculate success rate
            api_calls = [e for e in recent_events if e.event_type == 'api_call']
            successful_calls = [e for e in api_calls if e.metadata.get('success', True)]
            success_rate = len(successful_calls) / len(api_calls) if api_calls else 0.0
            
            # Calculate average response time
            api_times = [e.metadata.get('duration', 0) for e in api_calls]
            average_response_time = sum(api_times) / len(api_times) if api_times else 0.0
            
            # Calculate cache hit rate
            cache_hits = len([e for e in recent_events if e.event_type == 'cache_hit'])
            cache_misses = len([e for e in recent_events if e.event_type == 'cache_miss'])
            total_cache_ops = cache_hits + cache_misses
            cache_hit_rate = cache_hits / total_cache_ops if total_cache_ops > 0 else 0.0
            
            # Count specific event types
            rate_limit_events = len([e for e in recent_events if e.event_type.startswith('rate_limit_')])
            retry_events = len([e for e in recent_events if e.event_type == 'retry_attempt'])
            error_events = len([e for e in recent_events if e.event_type.startswith('error_')])
            
            return MetricsSummary(
                total_events=total_events,
                events_per_minute=events_per_minute,
                events_per_hour=events_per_hour,
                success_rate=success_rate,
                average_response_time=average_response_time,
                cache_hit_rate=cache_hit_rate,
                rate_limit_events=rate_limit_events,
                retry_events=retry_events,
                error_events=error_events
            )
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics about all collected metrics"""
        with self._lock:
            current_time = time.time()
            
            # Basic counts
            stats = {
                'total_events': len(self._events),
                'event_types': dict(self._counters),
                'collection_period': {
                    'start': min(e.timestamp for e in self._events) if self._events else current_time,
                    'end': current_time,
                    'duration_hours': (current_time - min(e.timestamp for e in self._events)) / 3600 if self._events else 0
                }
            }
            
            # API call statistics
            if self._api_call_times:
                stats['api_performance'] = {
                    'total_calls': len(self._api_call_times),
                    'average_time': sum(self._api_call_times) / len(self._api_call_times),
                    'min_time': min(self._api_call_times),
                    'max_time': max(self._api_call_times),
                    'median_time': sorted(self._api_call_times)[len(self._api_call_times) // 2]
                }
            
            # Cache statistics
            if self._cache_operations:
                total_cache_ops = sum(self._cache_operations.values())
                stats['cache_performance'] = {
                    'operations': dict(self._cache_operations),
                    'total_operations': total_cache_ops,
                    'hit_rate': self._cache_operations.get('cache_hit', 0) / 
                               (self._cache_operations.get('cache_hit', 0) + self._cache_operations.get('cache_miss', 0))
                               if (self._cache_operations.get('cache_hit', 0) + self._cache_operations.get('cache_miss', 0)) > 0 else 0
                }
            
            # Rate limiting statistics
            if self._rate_limit_events:
                stats['rate_limiting'] = {
                    'total_events': len(self._rate_limit_events),
                    'recent_events': len([e for e in self._rate_limit_events if current_time - e.timestamp < 3600])
                }
            
            # Retry statistics
            if self._retry_events:
                retry_attempts = [e.value for e in self._retry_events]
                stats['retry_behavior'] = {
                    'total_retries': len(self._retry_events),
                    'average_attempts': sum(retry_attempts) / len(retry_attempts),
                    'max_attempts': max(retry_attempts)
                }
            
            # Error statistics
            if self._error_events:
                error_types = defaultdict(int)
                for event in self._error_events:
                    error_types[event.event_type] += 1
                stats['errors'] = {
                    'total_errors': len(self._error_events),
                    'error_types': dict(error_types),
                    'recent_errors': len([e for e in self._error_events if current_time - e.timestamp < 3600])
                }
            
            return stats
    
    def _cleanup_old_events(self):
        """Remove events older than a certain threshold"""
        current_time = time.time()
        cutoff_time = current_time - (24 * 60 * 60)  # Keep 24 hours of data
        
        # Clean up main events deque (automatically handled by maxlen)
        # Clean up specific event collections
        self._rate_limit_events = deque(
            [e for e in self._rate_limit_events if e.timestamp >= cutoff_time],
            maxlen=100
        )
        self._retry_events = deque(
            [e for e in self._retry_events if e.timestamp >= cutoff_time],
            maxlen=100
        )
        self._error_events = deque(
            [e for e in self._error_events if e.timestamp >= cutoff_time],
            maxlen=100
        )
        
        self._last_cleanup = current_time
        logger.debug(f"Cleaned up old metrics events. Current event count: {len(self._events)}")
    
    def export_metrics(self, format: str = 'dict') -> Any:
        """Export metrics in various formats"""
        if format == 'dict':
            return self.get_detailed_stats()
        elif format == 'summary':
            return self.get_summary()
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def reset_metrics(self):
        """Reset all collected metrics"""
        with self._lock:
            self._events.clear()
            self._counters.clear()
            self._timers.clear()
            self._api_call_times.clear()
            self._cache_operations.clear()
            self._rate_limit_events.clear()
            self._retry_events.clear()
            self._error_events.clear()
            logger.info("All metrics have been reset")


# Global metrics collector instance
_metrics_collector: Optional[LyricsMetricsCollector] = None


def get_metrics_collector() -> LyricsMetricsCollector:
    """Get the global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = LyricsMetricsCollector()
    return _metrics_collector


def reset_metrics_collector():
    """Reset the global metrics collector"""
    global _metrics_collector
    _metrics_collector = None 