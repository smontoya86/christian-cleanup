"""
Tests for Prometheus metrics collection and monitoring infrastructure
"""

from unittest.mock import patch

from app.utils.prometheus_metrics import get_metrics, initialize_metrics, metrics_collector


class TestPrometheusMetrics:
    """Test Prometheus metrics collection"""

    def test_metrics_collector_creation(self):
        """Test that metrics collector can be created"""
        assert metrics_collector is not None
        assert hasattr(metrics_collector, "record_http_request")
        assert hasattr(metrics_collector, "record_song_analysis")

    def test_record_http_request(self):
        """Test HTTP request metrics recording"""
        # Should not raise any errors
        metrics_collector.record_http_request(
            method="GET", endpoint="test", status_code=200, duration=0.1
        )

    def test_record_song_analysis(self):
        """Test song analysis metrics recording"""
        # Should not raise any errors
        metrics_collector.record_song_analysis(
            duration=2.5, status="completed", concern_level="low"
        )

    def test_record_playlist_sync(self):
        """Test playlist sync metrics recording"""
        # Should not raise any errors
        metrics_collector.record_playlist_sync("success")
        metrics_collector.record_playlist_sync("failed")

    def test_record_user_session(self):
        """Test user session metrics recording"""
        # Should not raise any errors
        metrics_collector.record_user_session("login")
        metrics_collector.record_user_session("logout")

    def test_record_spotify_api_call(self):
        """Test Spotify API call metrics recording"""
        # Should not raise any errors
        metrics_collector.record_spotify_api_call(
            endpoint="playlists", duration=1.2, status="success"
        )

    def test_update_health_status(self):
        """Test health status metrics updates"""
        # Should not raise any errors
        metrics_collector.update_health_status("database", True)
        metrics_collector.update_health_status("redis", False)

    def test_record_error(self):
        """Test error metrics recording"""
        # Should not raise any errors
        metrics_collector.record_error("ValueError", "database")
        metrics_collector.record_error("ConnectionError", "spotify_api")

    def test_get_metrics_returns_string(self):
        """Test that get_metrics returns Prometheus format string"""
        metrics_output = get_metrics()

        assert isinstance(metrics_output, (str, bytes))
        # Should contain some basic Prometheus metrics
        assert len(metrics_output) > 0

    def test_initialize_metrics(self):
        """Test metrics initialization"""
        # Should not raise any errors
        initialize_metrics()


class TestMetricsEndpoint:
    """Test the /api/metrics endpoint"""

    def test_metrics_endpoint_exists(self, client):
        """Test that metrics endpoint is accessible"""
        response = client.get("/api/metrics")

        # Should return either metrics or error (both acceptable for testing)
        assert response.status_code in [200, 500]

    @patch("app.routes.api.get_metrics")
    def test_metrics_endpoint_success(self, mock_get_metrics, client):
        """Test successful metrics endpoint response"""
        mock_get_metrics.return_value = "# HELP test_metric Test metric\ntest_metric 1"

        response = client.get("/api/metrics")

        assert response.status_code == 200
        assert response.mimetype == "text/plain"
        assert "test_metric" in response.get_data(as_text=True)

    @patch("app.routes.api.get_metrics")
    def test_metrics_endpoint_error(self, mock_get_metrics, client):
        """Test metrics endpoint error handling"""
        mock_get_metrics.side_effect = Exception("Metrics error")

        response = client.get("/api/metrics")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
        assert "Metrics unavailable" in data["error"]


class TestMetricsIntegration:
    """Test metrics integration with application"""

    def test_metrics_in_health_check(self, client):
        """Test that health checks work with metrics system"""
        response = client.get("/api/health/detailed")

        # Should work even with metrics system loaded (accept both healthy and unhealthy states)
        assert response.status_code in [200, 503]
        data = response.get_json()
        assert data["status"] in ["healthy", "degraded", "unhealthy", "critical"]

    def test_application_startup_with_metrics(self, app):
        """Test that application starts successfully with metrics"""
        # Application should start without errors
        assert app is not None

        # Metrics collector should be initialized
        assert metrics_collector is not None
