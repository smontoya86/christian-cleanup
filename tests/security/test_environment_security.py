"""
Simple environment security tests.

Focus on what actually matters:
1. Required vars exist
2. SECRET_KEY is strong
3. Production isn't misconfigured
"""

import os
from unittest.mock import patch

import pytest

from app.utils.environment import EnvironmentError, validate_environment


class TestSimpleEnvironmentSecurity:
    """Simple, focused environment security tests"""

    def test_validates_required_environment_variables(self):
        """Test that required environment variables are checked"""
        required_vars = ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SECRET_KEY"]

        # Test missing variables
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError) as exc_info:
                validate_environment()

            error_msg = str(exc_info.value)
            for var in required_vars:
                assert var in error_msg

    def test_validates_secret_key_strength(self):
        """Test that SECRET_KEY must be strong enough"""
        # Test weak SECRET_KEY
        with patch.dict(
            os.environ,
            {
                "SPOTIFY_CLIENT_ID": "test_id",
                "SPOTIFY_CLIENT_SECRET": "test_secret",
                "SECRET_KEY": "weak",
            },
        ):
            with pytest.raises(EnvironmentError) as exc_info:
                validate_environment()
            assert "SECRET_KEY" in str(exc_info.value)
            assert "weak" in str(exc_info.value).lower()

    def test_accepts_valid_environment(self):
        """Test that valid environment passes validation"""
        valid_env = {
            "SPOTIFY_CLIENT_ID": "test_client_id_12345",
            "SPOTIFY_CLIENT_SECRET": "test_client_secret_67890",
            "SECRET_KEY": "this_is_a_sufficiently_long_secret_key_for_production_use_12345",
            "FLASK_ENV": "development",  # Explicitly set as development
        }

        with patch.dict(os.environ, valid_env, clear=True):
            # Should not raise any exception
            validate_environment()

    def test_production_requires_https_database(self):
        """Test that production environment requires secure database URL"""
        production_env = {
            "SPOTIFY_CLIENT_ID": "prod_id",
            "SPOTIFY_CLIENT_SECRET": "prod_secret",
            "SECRET_KEY": "production_secret_key_that_is_long_enough_12345",
            "FLASK_ENV": "production",
            "DATABASE_URL": "mysql://user:pass@localhost/db",  # Insecure
        }

        with patch.dict(os.environ, production_env):
            with pytest.raises(EnvironmentError) as exc_info:
                validate_environment()
            assert "production" in str(exc_info.value).lower()
            assert "secure" in str(exc_info.value).lower()

    def test_production_accepts_secure_database(self):
        """Test that production accepts secure database URLs"""
        production_env = {
            "SPOTIFY_CLIENT_ID": "prod_id",
            "SPOTIFY_CLIENT_SECRET": "prod_secret",
            "SECRET_KEY": "production_secret_key_that_is_long_enough_12345",
            "FLASK_ENV": "production",
            "DATABASE_URL": "mysql+pymysql://user:pass@localhost/db?ssl=true",
        }

        with patch.dict(os.environ, production_env):
            # Should not raise
            validate_environment()
