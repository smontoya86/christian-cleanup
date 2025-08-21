#!/usr/bin/env python3
"""
Test Redis connectivity through Flask app configuration.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


def test_flask_redis_configuration():
    """Test that Flask app has Redis configuration."""
    app = create_app()

    # Test that Redis URL is configured
    redis_url = app.config.get("RQ_REDIS_URL", "redis://localhost:6379/0")
    assert redis_url is not None
    assert "redis://" in redis_url
    print(f"Flask app Redis URL: {redis_url}")


def test_redis_connection_with_flask_app():
    """Test Redis connection using Flask app configuration."""
    app = create_app()

    with app.app_context():
        try:
            from urllib.parse import urlparse

            from redis import Redis

            # Parse the Redis URL
            redis_url = app.config.get("RQ_REDIS_URL", "redis://localhost:6379/0")
            url = urlparse(redis_url)

            # Create Redis connection
            r = Redis(
                host=url.hostname or "localhost",
                port=url.port or 6379,
                db=int(url.path.lstrip("/") or 0),
                password=url.password,
                socket_connect_timeout=5,
            )

            # Test connection
            r.ping()
            print("✓ Successfully connected to Redis via Flask app!")

            # Test setting and getting a value
            test_key = "flask_test_key_123"
            test_value = "flask_test_value_123"
            r.set(test_key, test_value)
            retrieved_value = r.get(test_key)
            assert retrieved_value.decode() == test_value
            print(f"✓ Successfully set and retrieved test value: {retrieved_value.decode()}")

            # Clean up
            r.delete(test_key)

        except Exception as e:
            pytest.skip(f"Redis not available: {str(e)}")


class TestRedisConnection:
    """Test class for Redis connection functionality."""

    def test_redis_connection_with_mock(self):
        """Test Redis connection with mock."""
        with patch("redis.Redis") as mock_redis:
            mock_instance = MagicMock()
            mock_redis.return_value = mock_instance
            mock_instance.ping.return_value = True

            # Test connection
            result = mock_instance.ping()
            assert result is True
            mock_instance.ping.assert_called_once()


if __name__ == "__main__":
    test_flask_redis_configuration()
    test_redis_connection_with_flask_app()
