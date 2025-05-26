"""
Tests for database monitoring utilities.
"""
import pytest
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.utils.database_monitoring import (
    get_pool_status, 
    log_pool_status, 
    check_pool_health,
    setup_pool_monitoring
)


class TestDatabaseMonitoring:
    """Test database monitoring utilities."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_get_pool_status(self):
        """Test that pool status can be retrieved successfully."""
        status = get_pool_status()
        
        # Verify required fields are present
        required_fields = [
            'pool_size', 'checked_in', 'checked_out', 
            'overflow', 'invalid', 'pool_class', 
            'engine_url', 'utilization_percent'
        ]
        
        for field in required_fields:
            assert field in status, f"Status should contain {field}"
        
        # Verify data types
        assert isinstance(status['pool_size'], int), "pool_size should be an integer"
        assert isinstance(status['checked_in'], int), "checked_in should be an integer"
        assert isinstance(status['checked_out'], int), "checked_out should be an integer"
        assert isinstance(status['utilization_percent'], (int, float)), "utilization_percent should be numeric"
        
        # Verify reasonable values
        assert status['pool_size'] >= 0, "pool_size should be non-negative"
        assert status['checked_in'] >= 0, "checked_in should be non-negative"
        assert status['checked_out'] >= 0, "checked_out should be non-negative"
        assert 0 <= status['utilization_percent'] <= 100, "utilization_percent should be between 0 and 100"
    
    def test_log_pool_status(self, caplog):
        """Test that pool status logging works correctly."""
        with caplog.at_level('INFO'):
            log_pool_status()
        
        # Verify log message was created
        assert len(caplog.records) > 0, "Should have logged pool status"
        
        # Verify log message contains expected information
        log_message = caplog.records[0].message
        assert "DB Pool Status" in log_message, "Log should contain pool status info"
        assert "Size:" in log_message, "Log should contain pool size"
        assert "Utilization:" in log_message, "Log should contain utilization info"
    
    def test_check_pool_health_healthy(self):
        """Test pool health check when pool is healthy."""
        health = check_pool_health()
        
        # Verify required fields
        required_fields = ['healthy', 'status', 'issues', 'recommendations']
        for field in required_fields:
            assert field in health, f"Health check should contain {field}"
        
        # Verify data types
        assert isinstance(health['healthy'], bool), "healthy should be a boolean"
        assert isinstance(health['issues'], list), "issues should be a list"
        assert isinstance(health['recommendations'], list), "recommendations should be a list"
        assert isinstance(health['status'], dict), "status should be a dictionary"
    
    @patch('app.utils.database_monitoring.get_pool_status')
    def test_check_pool_health_with_issues(self, mock_get_pool_status):
        """Test pool health check when there are issues."""
        # Mock a pool with high utilization
        mock_get_pool_status.return_value = {
            'pool_size': 10,
            'checked_in': 1,
            'checked_out': 9,
            'overflow': 5,
            'invalid': 1,
            'utilization_percent': 90.0,
            'pool_class': 'QueuePool',
            'engine_url': 'postgresql://test'
        }
        
        health = check_pool_health()
        
        # Should detect issues
        assert not health['healthy'], "Pool should be marked as unhealthy"
        assert len(health['issues']) > 0, "Should have detected issues"
        assert len(health['recommendations']) > 0, "Should have recommendations"
        
        # Check specific issues
        issues_text = ' '.join(health['issues'])
        assert "High pool utilization" in issues_text, "Should detect high utilization"
        assert "Invalid connections" in issues_text, "Should detect invalid connections"
    
    @patch('app.utils.database_monitoring.get_pool_status')
    def test_check_pool_health_with_error(self, mock_get_pool_status):
        """Test pool health check when there's an error getting status."""
        # Mock an error condition
        mock_get_pool_status.return_value = {
            'error': 'Database connection failed'
        }
        
        health = check_pool_health()
        
        # Should handle error gracefully
        assert not health['healthy'], "Pool should be marked as unhealthy on error"
        assert len(health['issues']) > 0, "Should have error in issues"
        assert "Pool status error" in health['issues'][0], "Should report the error"
    
    def test_setup_pool_monitoring(self):
        """Test that pool monitoring setup works correctly."""
        # This should not raise any exceptions
        setup_pool_monitoring(self.app)
        
        # Verify health endpoint was created
        with self.app.test_client() as client:
            response = client.get('/health/database')
            assert response.status_code in [200, 503], "Health endpoint should respond"
            
            data = response.get_json()
            assert 'service' in data, "Response should contain service field"
            assert data['service'] == 'database', "Service should be 'database'"
            assert 'healthy' in data, "Response should contain healthy field"
            assert 'pool_status' in data, "Response should contain pool_status"
    
    def test_pool_monitoring_with_mock_unhealthy_pool(self):
        """Test health endpoint with unhealthy pool."""
        setup_pool_monitoring(self.app)
        
        with patch('app.utils.database_monitoring.check_pool_health') as mock_health:
            # Mock an unhealthy pool
            mock_health.return_value = {
                'healthy': False,
                'status': {'pool_size': 5, 'utilization_percent': 95.0},
                'issues': ['High pool utilization: 95.0%'],
                'recommendations': ['Consider increasing pool_size']
            }
            
            with self.app.test_client() as client:
                response = client.get('/health/database')
                
                # Should return 503 for unhealthy pool
                assert response.status_code == 503, "Should return 503 for unhealthy pool"
                
                data = response.get_json()
                assert not data['healthy'], "Should report as unhealthy"
                assert len(data['issues']) > 0, "Should include issues"
                assert len(data['recommendations']) > 0, "Should include recommendations" 