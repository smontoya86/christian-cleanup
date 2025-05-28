"""
Comprehensive Metrics Collection System for Christian Cleanup Application
Tracks performance metrics across all application components with thread-safe operations.
"""

import time
import threading
import statistics
from functools import wraps
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
from flask import current_app, request, g


@dataclass
class MetricPoint:
    """Individual metric data point."""
    timestamp: float
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentMetrics:
    """Metrics for a specific component."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_duration: float = 0.0
    min_duration: float = float('inf')
    max_duration: float = 0.0
    recent_operations: deque = field(default_factory=lambda: deque(maxlen=1000))
    error_counts: Dict[str, int] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_operations == 0:
            return 0.0
        return (self.successful_operations / self.total_operations) * 100
    
    @property
    def average_duration(self) -> float:
        """Calculate average operation duration."""
        if self.total_operations == 0:
            return 0.0
        return self.total_duration / self.total_operations
    
    @property
    def recent_durations(self) -> List[float]:
        """Get recent operation durations."""
        return [op.value for op in self.recent_operations]
    
    @property
    def p95_duration(self) -> float:
        """Calculate 95th percentile duration."""
        durations = self.recent_durations
        if not durations:
            return 0.0
        return statistics.quantiles(durations, n=20)[18]  # 95th percentile
    
    @property
    def p99_duration(self) -> float:
        """Calculate 99th percentile duration."""
        durations = self.recent_durations
        if not durations:
            return 0.0
        return statistics.quantiles(durations, n=100)[98]  # 99th percentile


class MetricsCollector:
    """Thread-safe metrics collector for application performance monitoring."""
    
    def __init__(self, max_history_size: int = 10000):
        """
        Initialize metrics collector.
        
        Args:
            max_history_size: Maximum number of historical data points to keep
        """
        self.max_history_size = max_history_size
        self._lock = threading.RLock()
        
        # Component metrics
        self.api_metrics: Dict[str, ComponentMetrics] = defaultdict(ComponentMetrics)
        self.analysis_metrics = ComponentMetrics()
        self.database_metrics: Dict[str, ComponentMetrics] = defaultdict(ComponentMetrics)
        self.redis_metrics: Dict[str, ComponentMetrics] = defaultdict(ComponentMetrics)
        self.worker_metrics: Dict[str, ComponentMetrics] = defaultdict(ComponentMetrics)
        self.cache_metrics = ComponentMetrics()
        
        # System metrics
        self.system_metrics: Dict[str, deque] = {
            'cpu_usage': deque(maxlen=1000),
            'memory_usage': deque(maxlen=1000),
            'disk_usage': deque(maxlen=1000)
        }
        
        # Error tracking
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.recent_errors: deque = deque(maxlen=100)
        
        # Performance alerts
        self.alert_thresholds = {
            'slow_request_ms': 2000,
            'slow_analysis_ms': 30000,
            'slow_db_query_ms': 1000,
            'error_rate_threshold': 5.0,  # percentage
            'queue_depth_threshold': 100
        }
    
    def track_api_request(self, endpoint: str, method: str, status_code: int, 
                         duration: float, content_length: Optional[int] = None):
        """
        Track API request metrics.
        
        Args:
            endpoint: API endpoint name
            method: HTTP method
            status_code: Response status code
            duration: Request duration in milliseconds
            content_length: Response content length in bytes
        """
        with self._lock:
            key = f"{method}:{endpoint}"
            metrics = self.api_metrics[key]
            
            # Update basic counters
            metrics.total_operations += 1
            if 200 <= status_code < 400:
                metrics.successful_operations += 1
            else:
                metrics.failed_operations += 1
                error_key = f"http_{status_code}"
                metrics.error_counts[error_key] = metrics.error_counts.get(error_key, 0) + 1
            
            # Update duration metrics
            metrics.total_duration += duration
            metrics.min_duration = min(metrics.min_duration, duration)
            metrics.max_duration = max(metrics.max_duration, duration)
            
            # Add to recent operations
            metrics.recent_operations.append(MetricPoint(
                timestamp=time.time(),
                value=duration,
                metadata={
                    'status_code': status_code,
                    'content_length': content_length,
                    'endpoint': endpoint,
                    'method': method
                }
            ))
            
            # Check for slow requests
            if duration > self.alert_thresholds['slow_request_ms']:
                self._record_alert('slow_request', {
                    'endpoint': key,
                    'duration_ms': duration,
                    'threshold_ms': self.alert_thresholds['slow_request_ms']
                })
    
    def track_analysis_operation(self, song_id: int, duration: float, success: bool, 
                               analysis_type: str = 'full', **metadata):
        """
        Track song analysis metrics.
        
        Args:
            song_id: ID of analyzed song
            duration: Analysis duration in milliseconds
            success: Whether analysis was successful
            analysis_type: Type of analysis performed
            **metadata: Additional metadata
        """
        with self._lock:
            metrics = self.analysis_metrics
            
            # Update basic counters
            metrics.total_operations += 1
            if success:
                metrics.successful_operations += 1
            else:
                metrics.failed_operations += 1
                error_type = metadata.get('error_type', 'unknown_error')
                metrics.error_counts[error_type] = metrics.error_counts.get(error_type, 0) + 1
            
            # Update duration metrics
            metrics.total_duration += duration
            metrics.min_duration = min(metrics.min_duration, duration)
            metrics.max_duration = max(metrics.max_duration, duration)
            
            # Add to recent operations
            metrics.recent_operations.append(MetricPoint(
                timestamp=time.time(),
                value=duration,
                metadata={
                    'song_id': song_id,
                    'success': success,
                    'analysis_type': analysis_type,
                    **metadata
                }
            ))
            
            # Check for slow analysis
            if duration > self.alert_thresholds['slow_analysis_ms']:
                self._record_alert('slow_analysis', {
                    'song_id': song_id,
                    'duration_ms': duration,
                    'threshold_ms': self.alert_thresholds['slow_analysis_ms'],
                    'analysis_type': analysis_type
                })
    
    def track_database_operation(self, operation: str, duration: float, 
                               affected_rows: Optional[int] = None, **metadata):
        """
        Track database operation metrics.
        
        Args:
            operation: Database operation type (SELECT, INSERT, UPDATE, etc.)
            duration: Operation duration in milliseconds
            affected_rows: Number of affected rows
            **metadata: Additional metadata
        """
        with self._lock:
            metrics = self.database_metrics[operation.upper()]
            
            # Update basic counters
            metrics.total_operations += 1
            metrics.successful_operations += 1  # Assume success if no exception
            
            # Update duration metrics
            metrics.total_duration += duration
            metrics.min_duration = min(metrics.min_duration, duration)
            metrics.max_duration = max(metrics.max_duration, duration)
            
            # Add to recent operations
            metrics.recent_operations.append(MetricPoint(
                timestamp=time.time(),
                value=duration,
                metadata={
                    'operation': operation,
                    'affected_rows': affected_rows,
                    **metadata
                }
            ))
            
            # Check for slow queries
            if duration > self.alert_thresholds['slow_db_query_ms']:
                self._record_alert('slow_db_query', {
                    'operation': operation,
                    'duration_ms': duration,
                    'threshold_ms': self.alert_thresholds['slow_db_query_ms'],
                    'affected_rows': affected_rows
                })
    
    def track_redis_operation(self, operation: str, duration: float, success: bool, **metadata):
        """
        Track Redis operation metrics.
        
        Args:
            operation: Redis operation type
            duration: Operation duration in milliseconds
            success: Whether operation was successful
            **metadata: Additional metadata
        """
        with self._lock:
            metrics = self.redis_metrics[operation]
            
            # Update basic counters
            metrics.total_operations += 1
            if success:
                metrics.successful_operations += 1
            else:
                metrics.failed_operations += 1
                error_type = metadata.get('error_type', 'redis_error')
                metrics.error_counts[error_type] = metrics.error_counts.get(error_type, 0) + 1
            
            # Update duration metrics
            metrics.total_duration += duration
            metrics.min_duration = min(metrics.min_duration, duration)
            metrics.max_duration = max(metrics.max_duration, duration)
            
            # Add to recent operations
            metrics.recent_operations.append(MetricPoint(
                timestamp=time.time(),
                value=duration,
                metadata={
                    'operation': operation,
                    'success': success,
                    **metadata
                }
            ))
    
    def track_worker_job(self, job_id: str, queue: str, duration: float, 
                        success: bool, job_type: str = 'unknown', **metadata):
        """
        Track worker job metrics.
        
        Args:
            job_id: Job identifier
            queue: Queue name
            duration: Job duration in milliseconds
            success: Whether job was successful
            job_type: Type of job
            **metadata: Additional metadata
        """
        with self._lock:
            key = f"{queue}:{job_type}"
            metrics = self.worker_metrics[key]
            
            # Update basic counters
            metrics.total_operations += 1
            if success:
                metrics.successful_operations += 1
            else:
                metrics.failed_operations += 1
                error_type = metadata.get('error_type', 'job_error')
                metrics.error_counts[error_type] = metrics.error_counts.get(error_type, 0) + 1
            
            # Update duration metrics
            metrics.total_duration += duration
            metrics.min_duration = min(metrics.min_duration, duration)
            metrics.max_duration = max(metrics.max_duration, duration)
            
            # Add to recent operations
            metrics.recent_operations.append(MetricPoint(
                timestamp=time.time(),
                value=duration,
                metadata={
                    'job_id': job_id,
                    'queue': queue,
                    'job_type': job_type,
                    'success': success,
                    **metadata
                }
            ))
    
    def track_cache_operation(self, operation: str, duration: float, hit: bool, **metadata):
        """
        Track cache operation metrics.
        
        Args:
            operation: Cache operation (get, set, delete, etc.)
            duration: Operation duration in milliseconds
            hit: Whether it was a cache hit (for get operations)
            **metadata: Additional metadata
        """
        with self._lock:
            metrics = self.cache_metrics
            
            # Update basic counters
            metrics.total_operations += 1
            if hit or operation != 'get':
                metrics.successful_operations += 1
            else:
                metrics.failed_operations += 1  # Cache miss
            
            # Update duration metrics
            metrics.total_duration += duration
            metrics.min_duration = min(metrics.min_duration, duration)
            metrics.max_duration = max(metrics.max_duration, duration)
            
            # Add to recent operations
            metrics.recent_operations.append(MetricPoint(
                timestamp=time.time(),
                value=duration,
                metadata={
                    'operation': operation,
                    'hit': hit,
                    **metadata
                }
            ))
    
    def track_system_metrics(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """
        Track system resource metrics.
        
        Args:
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            disk_percent: Disk usage percentage
        """
        with self._lock:
            timestamp = time.time()
            self.system_metrics['cpu_usage'].append(MetricPoint(timestamp, cpu_percent))
            self.system_metrics['memory_usage'].append(MetricPoint(timestamp, memory_percent))
            self.system_metrics['disk_usage'].append(MetricPoint(timestamp, disk_percent))
    
    def record_error(self, error_type: str, error_message: str, **metadata):
        """
        Record an application error.
        
        Args:
            error_type: Type/category of error
            error_message: Error message
            **metadata: Additional error metadata
        """
        with self._lock:
            self.error_counts[error_type] += 1
            self.recent_errors.append({
                'timestamp': time.time(),
                'type': error_type,
                'message': error_message,
                'metadata': metadata
            })
    
    def _record_alert(self, alert_type: str, alert_data: Dict[str, Any]):
        """Record a performance alert."""
        # This could be extended to send notifications, write to a separate log, etc.
        from .logging import get_logger
        logger = get_logger('app.monitoring')
        logger.warning(f"Performance alert: {alert_type}", extra={
            'extra_fields': {
                'alert_type': alert_type,
                **alert_data
            }
        })
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a comprehensive summary of all metrics.
        
        Returns:
            Dictionary containing all metrics data
        """
        with self._lock:
            return {
                'api_requests': {
                    endpoint: {
                        'total_operations': metrics.total_operations,
                        'success_rate': metrics.success_rate,
                        'average_duration_ms': metrics.average_duration,
                        'min_duration_ms': metrics.min_duration if metrics.min_duration != float('inf') else 0,
                        'max_duration_ms': metrics.max_duration,
                        'p95_duration_ms': metrics.p95_duration,
                        'p99_duration_ms': metrics.p99_duration,
                        'error_counts': dict(metrics.error_counts)
                    }
                    for endpoint, metrics in self.api_metrics.items()
                },
                'analysis': {
                    'total_operations': self.analysis_metrics.total_operations,
                    'success_rate': self.analysis_metrics.success_rate,
                    'average_duration_ms': self.analysis_metrics.average_duration,
                    'min_duration_ms': self.analysis_metrics.min_duration if self.analysis_metrics.min_duration != float('inf') else 0,
                    'max_duration_ms': self.analysis_metrics.max_duration,
                    'p95_duration_ms': self.analysis_metrics.p95_duration,
                    'p99_duration_ms': self.analysis_metrics.p99_duration,
                    'error_counts': dict(self.analysis_metrics.error_counts)
                },
                'database': {
                    operation: {
                        'total_operations': metrics.total_operations,
                        'success_rate': metrics.success_rate,
                        'average_duration_ms': metrics.average_duration,
                        'min_duration_ms': metrics.min_duration if metrics.min_duration != float('inf') else 0,
                        'max_duration_ms': metrics.max_duration,
                        'p95_duration_ms': metrics.p95_duration,
                        'p99_duration_ms': metrics.p99_duration
                    }
                    for operation, metrics in self.database_metrics.items()
                },
                'redis': {
                    operation: {
                        'total_operations': metrics.total_operations,
                        'success_rate': metrics.success_rate,
                        'average_duration_ms': metrics.average_duration,
                        'min_duration_ms': metrics.min_duration if metrics.min_duration != float('inf') else 0,
                        'max_duration_ms': metrics.max_duration,
                        'p95_duration_ms': metrics.p95_duration,
                        'p99_duration_ms': metrics.p99_duration,
                        'error_counts': dict(metrics.error_counts)
                    }
                    for operation, metrics in self.redis_metrics.items()
                },
                'workers': {
                    queue_job: {
                        'total_operations': metrics.total_operations,
                        'success_rate': metrics.success_rate,
                        'average_duration_ms': metrics.average_duration,
                        'min_duration_ms': metrics.min_duration if metrics.min_duration != float('inf') else 0,
                        'max_duration_ms': metrics.max_duration,
                        'p95_duration_ms': metrics.p95_duration,
                        'p99_duration_ms': metrics.p99_duration,
                        'error_counts': dict(metrics.error_counts)
                    }
                    for queue_job, metrics in self.worker_metrics.items()
                },
                'cache': {
                    'total_operations': self.cache_metrics.total_operations,
                    'hit_rate': self.cache_metrics.success_rate,  # For cache, success = hit
                    'average_duration_ms': self.cache_metrics.average_duration,
                    'min_duration_ms': self.cache_metrics.min_duration if self.cache_metrics.min_duration != float('inf') else 0,
                    'max_duration_ms': self.cache_metrics.max_duration
                },
                'system': {
                    metric_name: {
                        'current': metric_data[-1].value if metric_data else 0,
                        'average': statistics.mean([point.value for point in metric_data]) if metric_data else 0,
                        'max': max([point.value for point in metric_data]) if metric_data else 0,
                        'min': min([point.value for point in metric_data]) if metric_data else 0
                    }
                    for metric_name, metric_data in self.system_metrics.items()
                },
                'errors': {
                    'total_errors': sum(self.error_counts.values()),
                    'error_types': dict(self.error_counts),
                    'recent_errors': list(self.recent_errors)[-10:]  # Last 10 errors
                },
                'timestamp': time.time()
            }
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.api_metrics.clear()
            self.analysis_metrics = ComponentMetrics()
            self.database_metrics.clear()
            self.redis_metrics.clear()
            self.worker_metrics.clear()
            self.cache_metrics = ComponentMetrics()
            for metric_data in self.system_metrics.values():
                metric_data.clear()
            self.error_counts.clear()
            self.recent_errors.clear()


# Global metrics collector instance
metrics_collector = MetricsCollector()


def track_time(category: str, operation: str = None, **extra_metadata):
    """
    Decorator to track execution time of functions.
    
    Args:
        category: Metric category ('api', 'analysis', 'database', 'redis', 'worker', 'cache')
        operation: Specific operation name
        **extra_metadata: Additional metadata to include
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_type = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Track metrics based on category
                if category == 'analysis':
                    song_id = kwargs.get('song_id') or (args[1] if len(args) > 1 else None)
                    metrics_collector.track_analysis_operation(
                        song_id=song_id or 0,
                        duration=duration,
                        success=success,
                        analysis_type=operation or func.__name__,
                        error_type=error_type,
                        **extra_metadata
                    )
                elif category == 'database':
                    metrics_collector.track_database_operation(
                        operation=operation or func.__name__,
                        duration=duration,
                        error_type=error_type,
                        **extra_metadata
                    )
                elif category == 'redis':
                    metrics_collector.track_redis_operation(
                        operation=operation or func.__name__,
                        duration=duration,
                        success=success,
                        error_type=error_type,
                        **extra_metadata
                    )
                elif category == 'worker':
                    job_id = kwargs.get('job_id') or extra_metadata.get('job_id', 'unknown')
                    queue = kwargs.get('queue') or extra_metadata.get('queue', 'default')
                    metrics_collector.track_worker_job(
                        job_id=job_id,
                        queue=queue,
                        duration=duration,
                        success=success,
                        job_type=operation or func.__name__,
                        error_type=error_type,
                        **extra_metadata
                    )
                elif category == 'cache':
                    hit = kwargs.get('hit', success)  # For cache operations
                    metrics_collector.track_cache_operation(
                        operation=operation or func.__name__,
                        duration=duration,
                        hit=hit,
                        error_type=error_type,
                        **extra_metadata
                    )
        
        return wrapper
    return decorator 