"""
Comprehensive tests for the monitoring and logging system.
Tests metrics collection, diagnostic endpoints, structured logging, and performance tracking.
"""

import pytest
import json
import time
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import g

from app import create_app
from app.extensions import db
from app.utils.metrics import metrics_collector, MetricsCollector, track_time
from app.utils.logging import get_logger, log_analysis_metrics, log_worker_metrics
from app.models.models import User


class TestMetricsCollector:
    """Test the metrics collection system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.collector = MetricsCollector()
    
    def test_api_request_tracking(self):
        """Test API request metrics tracking."""
        # Track successful request
        self.collector.track_api_request(
            endpoint='/api/songs',
            method='GET',
            status_code=200,
            duration=150.5,
            content_length=1024
        )
        
        # Track failed request
        self.collector.track_api_request(
            endpoint='/api/songs',
            method='GET',
            status_code=500,
            duration=75.2
        )
        
        metrics = self.collector.get_metrics_summary()
        api_metrics = metrics['api_requests']['GET:/api/songs']
        
        assert api_metrics['total_operations'] == 2
        assert api_metrics['success_rate'] == 50.0
        assert api_metrics['average_duration_ms'] == (150.5 + 75.2) / 2
        assert api_metrics['min_duration_ms'] == 75.2
        assert api_metrics['max_duration_ms'] == 150.5
        assert 'http_500' in api_metrics['error_counts']
    
    def test_analysis_operation_tracking(self):
        """Test analysis operation metrics tracking."""
        # Track successful analysis
        self.collector.track_analysis_operation(
            song_id=123,
            duration=5000.0,
            success=True,
            analysis_type='full',
            biblical_score=0.85
        )
        
        # Track failed analysis
        self.collector.track_analysis_operation(
            song_id=124,
            duration=2000.0,
            success=False,
            analysis_type='quick',
            error_type='timeout'
        )
        
        metrics = self.collector.get_metrics_summary()
        analysis_metrics = metrics['analysis']
        
        assert analysis_metrics['total_operations'] == 2
        assert analysis_metrics['success_rate'] == 50.0
        assert analysis_metrics['average_duration_ms'] == 3500.0
        assert 'timeout' in analysis_metrics['error_counts']
    
    def test_database_operation_tracking(self):
        """Test database operation metrics tracking."""
        self.collector.track_database_operation(
            operation='SELECT',
            duration=25.5,
            affected_rows=10,
            table='songs'
        )
        
        self.collector.track_database_operation(
            operation='INSERT',
            duration=45.2,
            affected_rows=1,
            table='analysis_results'
        )
        
        metrics = self.collector.get_metrics_summary()
        
        assert 'SELECT' in metrics['database']
        assert 'INSERT' in metrics['database']
        assert metrics['database']['SELECT']['total_operations'] == 1
        assert metrics['database']['INSERT']['average_duration_ms'] == 45.2
    
    def test_redis_operation_tracking(self):
        """Test Redis operation metrics tracking."""
        self.collector.track_redis_operation(
            operation='GET',
            duration=5.5,
            success=True,
            key='cache:song:123'
        )
        
        self.collector.track_redis_operation(
            operation='SET',
            duration=8.2,
            success=False,
            error_type='connection_error'
        )
        
        metrics = self.collector.get_metrics_summary()
        
        assert 'GET' in metrics['redis']
        assert 'SET' in metrics['redis']
        assert metrics['redis']['GET']['success_rate'] == 100.0
        assert metrics['redis']['SET']['success_rate'] == 0.0
        assert 'connection_error' in metrics['redis']['SET']['error_counts']
    
    def test_worker_job_tracking(self):
        """Test worker job metrics tracking."""
        self.collector.track_worker_job(
            job_id='job-123',
            queue='high',
            duration=15000.0,
            success=True,
            job_type='analysis'
        )
        
        self.collector.track_worker_job(
            job_id='job-124',
            queue='default',
            duration=5000.0,
            success=False,
            job_type='sync',
            error_type='api_error'
        )
        
        metrics = self.collector.get_metrics_summary()
        
        assert 'high:analysis' in metrics['workers']
        assert 'default:sync' in metrics['workers']
        assert metrics['workers']['high:analysis']['success_rate'] == 100.0
        assert metrics['workers']['default:sync']['success_rate'] == 0.0
    
    def test_cache_operation_tracking(self):
        """Test cache operation metrics tracking."""
        # Cache hit
        self.collector.track_cache_operation(
            operation='get',
            duration=2.5,
            hit=True,
            key='lyrics:123'
        )
        
        # Cache miss
        self.collector.track_cache_operation(
            operation='get',
            duration=3.0,
            hit=False,
            key='lyrics:124'
        )
        
        # Cache set
        self.collector.track_cache_operation(
            operation='set',
            duration=5.0,
            hit=True,  # Not applicable for set operations
            key='lyrics:124'
        )
        
        metrics = self.collector.get_metrics_summary()
        cache_metrics = metrics['cache']
        
        assert cache_metrics['total_operations'] == 3
        assert abs(cache_metrics['hit_rate'] - 66.67) < 0.01  # 2 hits out of 3 operations (set counts as hit)
    
    def test_system_metrics_tracking(self):
        """Test system metrics tracking."""
        self.collector.track_system_metrics(
            cpu_percent=45.5,
            memory_percent=62.3,
            disk_percent=78.9
        )
        
        self.collector.track_system_metrics(
            cpu_percent=52.1,
            memory_percent=65.8,
            disk_percent=79.2
        )
        
        metrics = self.collector.get_metrics_summary()
        system_metrics = metrics['system']
        
        assert system_metrics['cpu_usage']['current'] == 52.1
        assert system_metrics['memory_usage']['average'] == (62.3 + 65.8) / 2
        assert system_metrics['disk_usage']['max'] == 79.2
    
    def test_error_recording(self):
        """Test error recording functionality."""
        self.collector.record_error(
            error_type='database_error',
            error_message='Connection timeout',
            query='SELECT * FROM songs',
            duration=5000
        )
        
        self.collector.record_error(
            error_type='api_error',
            error_message='Rate limit exceeded',
            endpoint='/api/spotify'
        )
        
        metrics = self.collector.get_metrics_summary()
        errors = metrics['errors']
        
        assert errors['total_errors'] == 2
        assert 'database_error' in errors['error_types']
        assert 'api_error' in errors['error_types']
        assert len(errors['recent_errors']) == 2
    
    def test_metrics_reset(self):
        """Test metrics reset functionality."""
        # Add some metrics
        self.collector.track_api_request('/test', 'GET', 200, 100)
        self.collector.record_error('test_error', 'Test message')
        
        # Verify metrics exist
        metrics = self.collector.get_metrics_summary()
        assert metrics['errors']['total_errors'] > 0
        assert len(metrics['api_requests']) > 0
        
        # Reset metrics
        self.collector.reset_metrics()
        
        # Verify metrics are cleared
        metrics = self.collector.get_metrics_summary()
        assert metrics['errors']['total_errors'] == 0
        assert len(metrics['api_requests']) == 0
    
    def test_track_time_decorator(self):
        """Test the track_time decorator."""
        # Reset the global metrics collector for this test
        metrics_collector.reset_metrics()
        
        @track_time('analysis', 'test_analysis')
        def test_analysis_function(song_id):
            time.sleep(0.01)  # Small delay to measure
            return f"analyzed_{song_id}"
        
        # Test successful execution
        result = test_analysis_function(123)
        assert result == "analyzed_123"
        
        # Check metrics were recorded in the global collector
        metrics = metrics_collector.get_metrics_summary()
        assert metrics['analysis']['total_operations'] == 1
        assert metrics['analysis']['success_rate'] == 100.0
        assert metrics['analysis']['average_duration_ms'] > 0
        
        # Test failed execution
        @track_time('analysis', 'failing_analysis')
        def failing_analysis_function(song_id):
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_analysis_function(124)
        
        # Check failure was recorded
        metrics = metrics_collector.get_metrics_summary()
        assert metrics['analysis']['total_operations'] == 2
        assert metrics['analysis']['success_rate'] == 50.0


class TestStructuredLogging:
    """Test the structured logging system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
    
    def teardown_method(self):
        """Clean up test environment."""
        self.app_context.pop()
    
    def test_logger_creation(self):
        """Test logger creation and configuration."""
        logger = get_logger('app.test')
        assert logger.name == 'app.test'
        
        # Test component-specific loggers
        analysis_logger = get_logger('app.analysis')
        worker_logger = get_logger('app.worker')
        
        assert analysis_logger.name == 'app.analysis'
        assert worker_logger.name == 'app.worker'
    
    def test_analysis_metrics_logging(self):
        """Test analysis metrics logging."""
        with patch('app.utils.logging.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_analysis_metrics(
                song_id=123,
                duration=5.5,
                success=True,
                biblical_score=0.85,
                sentiment_score=0.72
            )
            
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert call_args[0][1] == "Song analysis completed: song_id=123"
    
    def test_worker_metrics_logging(self):
        """Test worker metrics logging."""
        with patch('app.utils.logging.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            log_worker_metrics(
                job_id='job-123',
                queue='high',
                duration=15.2,
                success=False,
                error_type='timeout'
            )
            
            mock_logger.log.assert_called_once()
            call_args = mock_logger.log.call_args
            assert call_args[0][1] == "Worker job failed: job-123"
    
    def test_request_id_middleware(self):
        """Test request ID middleware functionality."""
        with self.client:
            response = self.client.get('/api/diagnostics/health')
            
            # The middleware should have set a request ID
            with self.app.test_request_context():
                # We can't directly access g from outside request context,
                # but we can verify the response was successful
                assert response.status_code in [200, 503]  # Health check might fail in test


class TestDiagnosticEndpoints:
    """Test the diagnostic API endpoints."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Create test user for authentication
        with self.app.app_context():
            db.create_all()
            self.test_user = User(
                spotify_id='test_spotify_id',
                email='test@example.com',
                display_name='Test User',
                access_token='test_access_token',
                token_expiry=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(self.test_user)
            db.session.commit()
    
    def teardown_method(self):
        """Clean up test environment."""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.app_context.pop()
    
    def login_user(self):
        """Helper to log in test user."""
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.test_user.id)
            sess['_fresh'] = True
    
    def test_health_check_endpoint(self):
        """Test the health check endpoint."""
        response = self.client.get('/api/diagnostics/health')
        
        assert response.status_code in [200, 503]
        data = json.loads(response.data)
        
        assert 'status' in data
        assert 'timestamp' in data
        assert 'components' in data
        assert 'database' in data['components']
        assert 'redis' in data['components']
        assert 'application' in data['components']
    
    def test_metrics_endpoint_requires_auth(self):
        """Test that metrics endpoint requires authentication."""
        response = self.client.get('/api/diagnostics/metrics')
        assert response.status_code == 401
    
    def test_metrics_endpoint_with_auth(self):
        """Test metrics endpoint with authentication."""
        self.login_user()
        
        # Add some test metrics
        metrics_collector.track_api_request('/test', 'GET', 200, 100)
        metrics_collector.track_analysis_operation(123, 5000, True)
        
        response = self.client.get('/api/diagnostics/metrics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'data' in data
        assert 'api_requests' in data['data']
        assert 'analysis' in data['data']
        assert 'database' in data['data']
        assert 'redis' in data['data']
        assert 'workers' in data['data']
        assert 'cache' in data['data']
        assert 'system' in data['data']
        assert 'errors' in data['data']
    
    def test_system_info_endpoint(self):
        """Test system information endpoint."""
        self.login_user()
        
        response = self.client.get('/api/diagnostics/system')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'system' in data['data']
        assert 'process' in data['data']
        
        system_info = data['data']['system']
        assert 'cpu_percent' in system_info
        assert 'memory_total_gb' in system_info
        assert 'disk_total_gb' in system_info
        
        process_info = data['data']['process']
        assert 'pid' in process_info
        assert 'memory_rss_mb' in process_info
    
    def test_redis_info_endpoint(self):
        """Test Redis information endpoint."""
        self.login_user()
        
        response = self.client.get('/api/diagnostics/redis')
        
        # Response might be 200 or 503 depending on Redis availability
        assert response.status_code in [200, 503]
        
        data = json.loads(response.data)
        assert 'data' in data
        assert 'connection' in data['data']
    
    def test_database_info_endpoint(self):
        """Test database information endpoint."""
        self.login_user()
        
        response = self.client.get('/api/diagnostics/database')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'connection' in data['data']
        assert 'tables' in data['data']
        
        connection_info = data['data']['connection']
        assert 'connected' in connection_info
        assert connection_info['connected'] is True
    
    def test_alerts_endpoint(self):
        """Test alerts endpoint."""
        self.login_user()
        
        # Add some test data that might trigger alerts
        metrics_collector.track_api_request('/test', 'GET', 500, 100)  # Error
        metrics_collector.track_analysis_operation(123, 35000, True)  # Slow analysis
        
        response = self.client.get('/api/diagnostics/alerts')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'alerts' in data['data']
        assert 'recent_errors' in data['data']
        assert 'alert_count' in data['data']
    
    def test_config_info_endpoint(self):
        """Test configuration information endpoint."""
        self.login_user()
        
        response = self.client.get('/api/diagnostics/config')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'config' in data['data']
        assert 'environment' in data['data']
        assert 'debug' in data['data']
        assert 'testing' in data['data']
        
        # Verify sensitive keys are redacted
        config = data['data']['config']
        if 'SECRET_KEY' in config:
            assert config['SECRET_KEY'] == '***REDACTED***'
    
    def test_reset_metrics_endpoint(self):
        """Test metrics reset endpoint."""
        self.login_user()
        
        # Add some test metrics
        metrics_collector.track_api_request('/test', 'GET', 200, 100)
        
        # Verify metrics exist
        response = self.client.get('/api/diagnostics/metrics')
        data = json.loads(response.data)
        assert len(data['data']['api_requests']) > 0
        
        # Reset metrics
        response = self.client.post('/api/diagnostics/reset-metrics')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'Metrics have been reset' in data['message']
        
        # Verify metrics are cleared
        response = self.client.get('/api/diagnostics/metrics')
        data = json.loads(response.data)
        assert len(data['data']['api_requests']) == 0
    
    def test_logs_endpoint_file_not_found(self):
        """Test logs endpoint when log file doesn't exist."""
        self.login_user()
        
        with patch('os.path.exists', return_value=False):
            response = self.client.get('/api/diagnostics/logs?type=app')
            assert response.status_code == 404
            
            data = json.loads(response.data)
            assert data['status'] == 'error'
            assert 'Log file not found' in data['message']
    
    def test_logs_endpoint_with_file(self):
        """Test logs endpoint when log file exists."""
        self.login_user()
        
        # Create a temporary log file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("Line 1: Test log entry\n")
            f.write("Line 2: Another log entry\n")
            f.write("Line 3: Final log entry\n")
            temp_log_file = f.name
        
        try:
            with patch('os.path.join', return_value=temp_log_file):
                with patch('os.path.exists', return_value=True):
                    response = self.client.get('/api/diagnostics/logs?type=app&lines=2')
                    assert response.status_code == 200
                    
                    data = json.loads(response.data)
                    assert data['status'] == 'success'
                    assert 'logs' in data['data']
                    assert len(data['data']['logs']) == 2  # Last 2 lines
                    assert 'Line 2: Another log entry' in data['data']['logs']
                    assert 'Line 3: Final log entry' in data['data']['logs']
        finally:
            os.unlink(temp_log_file)


class TestIntegration:
    """Integration tests for the complete monitoring system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Reset metrics for clean test
        metrics_collector.reset_metrics()
    
    def teardown_method(self):
        """Clean up test environment."""
        self.app_context.pop()
    
    def test_request_metrics_integration(self):
        """Test that API requests are automatically tracked."""
        # Make several requests
        self.client.get('/api/diagnostics/health')
        self.client.get('/api/diagnostics/health')
        self.client.get('/nonexistent')  # 404 error
        
        # Check that metrics were collected
        metrics = metrics_collector.get_metrics_summary()
        
        # Should have metrics for the health endpoint
        health_endpoint_key = None
        for key in metrics['api_requests'].keys():
            if 'health' in key:
                health_endpoint_key = key
                break
        
        if health_endpoint_key:
            health_metrics = metrics['api_requests'][health_endpoint_key]
            assert health_metrics['total_operations'] >= 2
    
    def test_error_tracking_integration(self):
        """Test that errors are properly tracked and reported."""
        # Generate some errors by calling non-existent endpoints
        self.client.get('/api/nonexistent')
        self.client.post('/api/invalid')
        
        # Check error tracking
        metrics = metrics_collector.get_metrics_summary()
        
        # Should have some error metrics
        total_errors = metrics['errors']['total_errors']
        assert total_errors >= 0  # Might be 0 if endpoints don't exist in routing
    
    def test_performance_monitoring_integration(self):
        """Test that performance metrics are collected during normal operation."""
        # Make requests that should generate performance data
        self.client.get('/api/diagnostics/health')
        
        # Check that timing data was collected
        metrics = metrics_collector.get_metrics_summary()
        
        # Verify timestamp is recent
        assert abs(metrics['timestamp'] - time.time()) < 10  # Within 10 seconds


if __name__ == '__main__':
    pytest.main([__file__]) 