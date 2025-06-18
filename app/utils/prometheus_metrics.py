"""
Prometheus Metrics Collection for Christian Music Curator
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
import logging

logger = logging.getLogger(__name__)

# Application Metrics
app_info = Info('christian_curator_app', 'Application information')
app_info.info({
    'version': '1.0.0',
    'environment': 'production',
    'service': 'christian-music-curator'
})

# HTTP Request Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Business Metrics
songs_analyzed_total = Counter(
    'songs_analyzed_total',
    'Total number of songs analyzed',
    ['status', 'concern_level']
)

analysis_duration_seconds = Histogram(
    'analysis_duration_seconds',
    'Song analysis duration in seconds'
)

playlists_synced_total = Counter(
    'playlists_synced_total',
    'Total number of playlists synced',
    ['status']
)

user_sessions_total = Counter(
    'user_sessions_total',
    'Total user sessions',
    ['action']
)

spotify_api_calls_total = Counter(
    'spotify_api_calls_total',
    'Total Spotify API calls',
    ['endpoint', 'status']
)

# System Health Metrics
health_check_status = Gauge(
    'health_check_status',
    'Health check status (1 = healthy, 0 = unhealthy)',
    ['component']
)

# Error Metrics
errors_total = Counter(
    'errors_total',
    'Total application errors',
    ['error_type', 'component']
)


class MetricsCollector:
    """Central metrics collection class"""
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_song_analysis(self, duration: float, status: str = 'completed', concern_level: str = 'low'):
        """Record song analysis metrics"""
        songs_analyzed_total.labels(
            status=status,
            concern_level=concern_level
        ).inc()
        
        analysis_duration_seconds.observe(duration)
    
    def record_playlist_sync(self, status: str = 'success'):
        """Record playlist sync metrics"""
        playlists_synced_total.labels(status=status).inc()
    
    def record_user_session(self, action: str):
        """Record user session metrics"""
        user_sessions_total.labels(action=action).inc()
    
    def record_spotify_api_call(self, endpoint: str, duration: float, status: str = 'success'):
        """Record Spotify API call metrics"""
        spotify_api_calls_total.labels(
            endpoint=endpoint,
            status=status
        ).inc()
    
    def update_health_status(self, component: str, healthy: bool):
        """Update health check status"""
        health_check_status.labels(component=component).set(1 if healthy else 0)
    
    def record_error(self, error_type: str, component: str):
        """Record application error"""
        errors_total.labels(
            error_type=error_type,
            component=component
        ).inc()


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics() -> str:
    """Get current metrics in Prometheus format"""
    return generate_latest()


def initialize_metrics():
    """Initialize default metric values"""
    components = ['database', 'redis', 'spotify_api', 'worker']
    for component in components:
        metrics_collector.update_health_status(component, True)
    
    logger.info("Prometheus metrics initialized")


# Initialize metrics on module import
initialize_metrics()
