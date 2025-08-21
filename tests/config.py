"""
Test configuration for performance regression testing.
"""

import os


class TestConfig:
    """Configuration for performance tests."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("TEST_DATABASE_URL")
        or "postgresql://localhost/christian_music_analyzer_test"
    )
    REDIS_URL = os.environ.get("TEST_REDIS_URL") or "redis://localhost:6379/1"
    WTF_CSRF_ENABLED = False
    PRESERVE_CONTEXT_ON_EXCEPTION = False

    # Performance test specific settings
    SECRET_KEY = "test-secret-key"
    SPOTIPY_CLIENT_ID = "test-client-id"
    SPOTIPY_CLIENT_SECRET = "test-client-secret"
    SPOTIPY_REDIRECT_URI = "http://localhost:5000/auth/callback"

    # Disable external API calls during testing
    GENIUS_ACCESS_TOKEN = "test-genius-token"
    BIBLE_API_KEY = "test-bible-key"

    # RQ Configuration for testing
    RQ_REDIS_URL = os.environ.get("TEST_REDIS_URL") or "redis://localhost:6379/1"
    RQ_QUEUES = {
        "high": {"host": "localhost", "port": 6379, "db": 1, "default_timeout": 300},
        "default": {"host": "localhost", "port": 6379, "db": 1, "default_timeout": 600},
        "low": {"host": "localhost", "port": 6379, "db": 1, "default_timeout": 1800},
    }

    # Logging configuration
    LOG_LEVEL = "WARNING"  # Reduce noise during testing

    # SQLAlchemy configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
