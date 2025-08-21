"""
Production Deployment Tests
Comprehensive tests for production-ready features and configurations.
"""

import os

import pytest

from app import create_app


class TestProductionDeployment:
    """Test production deployment features."""

    def test_production_config_applied(self):
        """Test that production configuration is properly applied."""
        # Create app with production config
        app = create_app("production")

        with app.app_context():
            # Test security settings
            assert app.config.get("DEBUG") is False
            assert app.config.get("TESTING") is False
            assert app.config.get("WTF_CSRF_ENABLED") is True

            # Test secret key is set and secure
            secret_key = app.config.get("SECRET_KEY")
            assert secret_key is not None
            assert len(secret_key) >= 32
            assert secret_key != "dev-key-change-in-production"

    def test_health_endpoints(self, client):
        """Test all health check endpoints."""
        # Basic health check
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

        # Detailed health check
        response = client.get("/api/health/detailed")
        assert response.status_code in [200, 503]  # Could be warning state

        data = response.get_json()
        assert "status" in data
        assert "checks" in data

        # Readiness probe
        response = client.get("/api/health/ready")
        assert response.status_code in [200, 503]

        # Liveness probe
        response = client.get("/api/health/live")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "alive"


class TestHealthMonitoring:
    """Test the health monitoring system."""

    def test_health_monitor_import(self):
        """Test that health monitor can be imported."""
        from app.utils.health_monitor import HealthMonitor, HealthStatus

        monitor = HealthMonitor()
        assert monitor is not None

        # Test enum values
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.CRITICAL.value == "critical"


class TestDockerConfiguration:
    """Test Docker-related configuration."""

    def test_dockerfile_exists(self):
        """Test that production Dockerfile exists."""
        dockerfile_path = os.path.join(os.path.dirname(__file__), "..", "..", "Dockerfile.prod")
        assert os.path.exists(dockerfile_path)

        # Test basic Dockerfile content
        with open(dockerfile_path, "r") as f:
            content = f.read()
            assert "FROM python:" in content
            assert "COPY requirements.txt" in content

    def test_docker_compose_prod_exists(self):
        """Test that production docker-compose file exists."""
        compose_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "docker-compose.prod.yml"
        )
        assert os.path.exists(compose_path)

        # Test basic compose file content
        with open(compose_path, "r") as f:
            content = f.read()
            assert "services:" in content
            assert "nginx:" in content
            assert "web:" in content
            assert "db:" in content


class TestDeploymentScripts:
    """Test deployment scripts and tools."""

    def test_deploy_script_exists(self):
        """Test that deployment script exists and is executable."""
        script_path = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "deploy.sh")
        assert os.path.exists(script_path)

        # Test that script is executable
        assert os.access(script_path, os.X_OK)

        # Test script content
        with open(script_path, "r") as f:
            content = f.read()
            assert "#!/bin/bash" in content
            assert "docker-compose" in content

    def test_environment_template_exists(self):
        """Test that production environment template exists."""
        env_template_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "deploy", "production.env.example"
        )
        assert os.path.exists(env_template_path)

        # Test template content
        with open(env_template_path, "r") as f:
            content = f.read()
            assert "SECRET_KEY=" in content
            assert "DATABASE_URL=" in content
            assert "SPOTIFY_CLIENT_ID=" in content


@pytest.mark.integration
class TestProductionIntegration:
    """Integration tests for production features."""

    def test_full_health_check_workflow(self, client):
        """Test complete health check workflow."""
        # Test basic health
        response = client.get("/api/health")
        assert response.status_code == 200

        # Test detailed health
        response = client.get("/api/health/detailed")
        assert response.status_code in [200, 503]

        data = response.get_json()

        # Verify response structure
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data

        # Verify each check has required fields
        for check in data["checks"]:
            assert "name" in check
            assert "status" in check
            assert "message" in check
            assert "timestamp" in check

    def test_production_ready_checklist(self):
        """Test production readiness checklist."""
        checks = []

        # Check required files exist
        required_files = [
            "docker-compose.prod.yml",
            "Dockerfile.prod",
            "deploy/nginx/nginx.conf",
            "deploy/production.env.example",
            "scripts/deploy.sh",
        ]

        for file_path in required_files:
            full_path = os.path.join(os.path.dirname(__file__), "..", "..", file_path)
            checks.append((f"File exists: {file_path}", os.path.exists(full_path)))

        # Check required production modules can be imported
        try:
            from app.utils.health_monitor import HealthMonitor

            checks.append(("Health monitor importable", True))
        except ImportError:
            checks.append(("Health monitor importable", False))

        # Check all tests pass
        failed_checks = [check for check in checks if not check[1]]

        if failed_checks:
            pytest.fail(f"Production readiness checks failed: {failed_checks}")

        # All checks passed
        assert len(failed_checks) == 0
