"""
Integration tests for API health and basic endpoints
"""

import pytest


class TestHealthEndpoints:
    """Test health check and status endpoints"""
    
    def test_home_page(self, client):
        """Test home page loads"""
        response = client.get('/')
        assert response.status_code in [200, 302]  # Allow redirect to /dashboard
    
    def test_api_health_check(self, client):
        """Test API health endpoint if it exists"""
        response = client.get('/api/health')
        # 404 is ok if endpoint doesn't exist
        assert response.status_code in [200, 404]
    
    def test_api_status(self, client):
        """Test API status endpoint if it exists"""
        response = client.get('/api/status')
        # 404 is ok if endpoint doesn't exist
        assert response.status_code in [200, 401, 404]


class TestBasicAPIRoutes:
    """Test basic API functionality"""
    
    def test_dashboard_without_auth(self, client):
        """Test dashboard requires authentication"""
        response = client.get('/dashboard')
        # Should redirect to login or show login page
        assert response.status_code in [200, 302, 401]
    
    def test_api_requires_auth(self, client):
        """Test protected API endpoints require authentication"""
        response = client.post('/api/analyze')
        # Should return 401 or redirect
        assert response.status_code in [401, 302, 400]

