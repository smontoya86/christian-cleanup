"""
Comprehensive tests for the performance monitoring and alerting system.
Tests performance metrics collection, alert rules, thresholds, and API endpoints.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import logging

from app import create_app
from app.extensions import db
from app.utils.performance_monitor import (
    PerformanceMonitor, PerformanceAlert, AlertRule, PerformanceThreshold,
    performance_monitor
)
from app.models.models import User


class TestPerformanceMonitor:
    """Test the performance monitoring system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.monitor = PerformanceMonitor()
        
    def test_metric_recording(self):
        """Test recording and retrieving metrics."""
        # Record some test metrics
        self.monitor._record_metric('test_metric', 100.0)
        self.monitor._record_metric('test_metric', 150.0)
        self.monitor._record_metric('test_metric', 200.0)
        
        # Get performance summary
        summary = self.monitor.get_performance_summary(hours=1)
        
        assert 'test_metric' in summary
        assert summary['test_metric']['count'] == 3
        assert summary['test_metric']['average'] == 150.0
        assert summary['test_metric']['min'] == 100.0
        assert summary['test_metric']['max'] == 200.0
        
    def test_alert_condition_evaluation(self):
        """Test alert condition evaluation."""
        # Test greater_than condition
        assert self.monitor._evaluate_condition(100, 'greater_than', 50) == True
        assert self.monitor._evaluate_condition(50, 'greater_than', 100) == False
        
        # Test less_than condition
        assert self.monitor._evaluate_condition(50, 'less_than', 100) == True
        assert self.monitor._evaluate_condition(100, 'less_than', 50) == False
        
        # Test equals condition
        assert self.monitor._evaluate_condition(100, 'equals', 100) == True
        assert self.monitor._evaluate_condition(100, 'equals', 101) == False
        
    def test_threshold_updates(self):
        """Test updating performance thresholds."""
        # Update existing threshold
        self.monitor.update_threshold('response_time_ms', warning=1500, critical=4000)
        
        threshold = self.monitor.thresholds['response_time_ms']
        assert threshold.warning_threshold == 1500
        assert threshold.critical_threshold == 4000
        
        # Try to update non-existent threshold
        self.monitor.update_threshold('non_existent_metric', warning=100)
        # Should not raise an error, just log a warning
        
    def test_alert_rule_management(self):
        """Test enabling and disabling alert rules."""
        rule_name = 'high_response_time'
        
        # Disable rule
        self.monitor.disable_alert_rule(rule_name)
        assert self.monitor.alert_rules[rule_name].enabled == False
        
        # Enable rule
        self.monitor.enable_alert_rule(rule_name)
        assert self.monitor.alert_rules[rule_name].enabled == True
        
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.net_io_counters')
    def test_system_metrics_collection(self, mock_net, mock_disk, mock_memory, mock_cpu):
        """Test system metrics collection."""
        # Mock system metrics
        mock_cpu.return_value = 75.5
        mock_memory.return_value = MagicMock(percent=60.2, available=1024*1024*1024)
        mock_disk.return_value = MagicMock(used=500*1024*1024*1024, total=1000*1024*1024*1024)
        mock_net.return_value = MagicMock(bytes_sent=1000000, bytes_recv=2000000)
        
        # Collect system metrics
        self.monitor._collect_system_metrics()
        
        # Check that metrics were recorded
        summary = self.monitor.get_performance_summary(hours=1)
        assert 'cpu_usage_percent' in summary
        assert 'memory_usage_percent' in summary
        assert 'disk_usage_percent' in summary
        assert summary['cpu_usage_percent']['average'] == 75.5
        assert summary['memory_usage_percent']['average'] == 60.2
        
    def test_alert_triggering(self):
        """Test alert triggering and resolution."""
        # Create a test alert rule that matches a metric we'll record
        test_rule = AlertRule(
            name='high_test_metric',
            condition='greater_than',
            threshold=100,
            duration_seconds=2,  # Slightly longer duration for testing
            severity='warning',
            cooldown_seconds=1  # Very short cooldown for testing
        )
        self.monitor.alert_rules['high_test_metric'] = test_rule
        
        # Record metrics that should trigger the alert
        # Record them right before checking to ensure they're within the duration window
        for _ in range(5):
            self.monitor._record_metric('test_metric', 150)  # Above threshold
            
        # Small delay to ensure metrics are recorded
        time.sleep(0.1)
        
        # Check alert conditions immediately after recording
        self.monitor._check_alert_conditions()
        
        # Should have triggered an alert
        active_alerts = self.monitor.get_active_alerts()
        assert len(active_alerts) > 0, f"Expected alert to be triggered"
        
        # Wait longer to ensure the high metrics fall outside the 2-second duration window
        time.sleep(2.5)
        
        # Record metrics that should resolve the alert
        for _ in range(5):
            self.monitor._record_metric('test_metric', 50)  # Below threshold
            
        # Small delay to ensure metrics are recorded
        time.sleep(0.1)
            
        # Check alert conditions again
        self.monitor._check_alert_conditions()
        
        # Alert should be resolved (no longer active)
        active_alerts_after_resolution = self.monitor.get_active_alerts()
        assert len(active_alerts_after_resolution) == 0, f"Expected alert to be resolved, but {len(active_alerts_after_resolution)} alerts are still active"
        
        # Check that the alert appears in history and is marked as resolved
        alert_history = self.monitor.get_alert_history()
        assert len(alert_history) > 0, "Expected alert to appear in history"
        
        # Find our specific alert in history
        test_alert = None
        for alert in alert_history:
            if alert.rule_name == 'high_test_metric':
                test_alert = alert
                break
                
        assert test_alert is not None, "Expected to find high_test_metric alert in history"
        assert test_alert.resolved, f"Expected alert to be marked as resolved, but resolved={test_alert.resolved}"
        
    def test_health_status(self):
        """Test overall health status calculation."""
        # Test healthy status (no alerts)
        health = self.monitor.get_health_status()
        assert health['status'] == 'healthy'
        assert health['active_alerts_count'] == 0
        
        # Add a mock critical alert
        critical_alert = PerformanceAlert(
            timestamp=datetime.utcnow(),
            rule_name='test_critical',
            metric_name='test_metric',
            current_value=200,
            threshold=100,
            severity='critical',
            message='Test critical alert'
        )
        self.monitor.active_alerts['test_critical'] = critical_alert
        
        # Test critical status
        health = self.monitor.get_health_status()
        assert health['status'] == 'critical'
        assert health['critical_alerts_count'] == 1
        
    def test_monitoring_thread_lifecycle(self):
        """Test starting and stopping the monitoring thread."""
        # Start monitoring
        self.monitor.start_monitoring(interval_seconds=0.1)
        assert self.monitor.monitoring_active == True
        assert self.monitor.monitor_thread is not None
        
        # Wait a moment for the thread to run
        time.sleep(0.2)
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        assert self.monitor.monitoring_active == False
        
    def test_data_cleanup(self):
        """Test old data cleanup functionality."""
        # Record old metrics (simulate by manually setting timestamps)
        old_timestamp = datetime.utcnow() - timedelta(hours=25)
        recent_timestamp = datetime.utcnow()
        
        # Manually add old and recent data
        self.monitor.performance_history['test_metric'].append({
            'timestamp': old_timestamp,
            'value': 100
        })
        self.monitor.performance_history['test_metric'].append({
            'timestamp': recent_timestamp,
            'value': 200
        })
        
        # Run cleanup
        self.monitor._cleanup_old_data()
        
        # Only recent data should remain
        remaining_data = list(self.monitor.performance_history['test_metric'])
        assert len(remaining_data) == 1
        assert remaining_data[0]['value'] == 200


class TestPerformanceAPI:
    """Test the performance monitoring API endpoints."""
    
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
        # Query for the user by email instead of using the detached instance
        with self.app.app_context():
            user = User.query.filter_by(email='test@example.com').first()
            if user:
                with self.client.session_transaction() as sess:
                    sess['_user_id'] = str(user.id)
                    sess['_fresh'] = True
            
    def test_performance_summary_endpoint(self):
        """Test the performance summary API endpoint."""
        self.login_user()
        
        # Add some test metrics
        performance_monitor._record_metric('test_metric', 100)
        performance_monitor._record_metric('test_metric', 200)
        
        response = self.client.get('/api/diagnostics/performance/summary?hours=1')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'performance_summary' in data
        assert data['hours'] == 1
        
    def test_performance_alerts_endpoint(self):
        """Test the performance alerts API endpoint."""
        self.login_user()
        
        response = self.client.get('/api/diagnostics/performance/alerts?hours=24')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'active_alerts' in data
        assert 'alert_history' in data
        assert data['history_hours'] == 24
        
    def test_performance_health_endpoint(self):
        """Test the performance health API endpoint."""
        self.login_user()
        
        response = self.client.get('/api/diagnostics/performance/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'health' in data
        assert 'status' in data['health']
        
    def test_performance_thresholds_get_endpoint(self):
        """Test getting performance thresholds via API."""
        self.login_user()
        
        response = self.client.get('/api/diagnostics/performance/thresholds')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'thresholds' in data
        assert 'response_time_ms' in data['thresholds']
        
    def test_performance_thresholds_post_endpoint(self):
        """Test updating performance thresholds via API."""
        self.login_user()
        
        update_data = {
            'response_time_ms': {
                'warning_threshold': 1500,
                'critical_threshold': 4000
            }
        }
        
        response = self.client.post(
            '/api/diagnostics/performance/thresholds',
            json=update_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'response_time_ms' in data['updated_metrics']
        
    def test_performance_monitoring_control_endpoint(self):
        """Test controlling performance monitoring via API."""
        self.login_user()
        
        # Test starting monitoring
        start_data = {'action': 'start', 'interval_seconds': 60}
        response = self.client.post(
            '/api/diagnostics/performance/monitoring',
            json=start_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['action'] == 'started'
        
        # Test stopping monitoring
        stop_data = {'action': 'stop'}
        response = self.client.post(
            '/api/diagnostics/performance/monitoring',
            json=stop_data,
            content_type='application/json'
        )
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['action'] == 'stopped'
        
    def test_unauthorized_access(self):
        """Test that endpoints require authentication."""
        # Don't log in user
        
        endpoints = [
            '/api/diagnostics/performance/summary',
            '/api/diagnostics/performance/alerts',
            '/api/diagnostics/performance/health',
            '/api/diagnostics/performance/thresholds'
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            assert response.status_code == 302  # Redirect to login


class TestAlertCallbacks:
    """Test alert callback functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        self.monitor = PerformanceMonitor()
        self.callback_called = False
        self.callback_alert = None
        
    def test_alert_callback_registration(self):
        """Test registering and triggering alert callbacks."""
        def test_callback(alert):
            self.callback_called = True
            self.callback_alert = alert
            
        # Register callback
        self.monitor.add_alert_callback(test_callback)
        assert len(self.monitor.alert_callbacks) == 1
        
        # Create and trigger an alert
        test_alert = PerformanceAlert(
            timestamp=datetime.utcnow(),
            rule_name='test_alert',
            metric_name='test_metric',
            current_value=200,
            threshold=100,
            severity='warning',
            message='Test alert'
        )
        
        # Trigger callbacks
        self.monitor._trigger_alert_callbacks(test_alert)
        
        # Check that callback was called
        assert self.callback_called == True
        assert self.callback_alert == test_alert
        
    def test_callback_error_handling(self):
        """Test that callback errors don't break the monitoring system."""
        def failing_callback(alert):
            raise Exception("Callback error")
            
        def working_callback(alert):
            self.callback_called = True
            
        # Register both callbacks
        self.monitor.add_alert_callback(failing_callback)
        self.monitor.add_alert_callback(working_callback)
        
        # Create test alert
        test_alert = PerformanceAlert(
            timestamp=datetime.utcnow(),
            rule_name='test_alert',
            metric_name='test_metric',
            current_value=200,
            threshold=100,
            severity='warning',
            message='Test alert'
        )
        
        # Trigger callbacks - should not raise exception
        self.monitor._trigger_alert_callbacks(test_alert)
        
        # Working callback should still have been called
        assert self.callback_called == True


if __name__ == '__main__':
    pytest.main([__file__]) 