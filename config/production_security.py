"""
Production Security Configuration
Implements comprehensive security hardening for production deployment.
"""

import os
from datetime import timedelta


class ProductionSecurityConfig:
    """Production security configuration with hardened settings."""

    # Session Security
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # Prevent XSS
    SESSION_COOKIE_SAMESITE = "Lax"  # CSRF protection
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # 24-hour sessions

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour CSRF token validity

    # Security Headers
    SECURITY_HEADERS = {
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https://i.scdn.co https://images.genius.com; "
            "connect-src 'self' https://api.spotify.com https://accounts.spotify.com "
            + os.environ.get("LLM_API_BASE_URL", "").split("/v1")[0]
            + "; "
            "frame-ancestors 'none';"
        ),
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_STORAGE_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")

    # API Rate Limits
    API_RATE_LIMITS = {
        "/api/": "100 per minute",
        "/auth/": "10 per minute",
        "/analyze_playlist_api/": "5 per minute",
        "default": "1000 per hour",
    }

    # Upload Security
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    ALLOWED_EXTENSIONS = {"txt", "json"}

    # Database Security
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        # Only apply connect args in non-sqlite environments
        "connect_args": {},
    }

    # Redis Security
    REDIS_SSL = os.environ.get("REDIS_SSL", "false").lower() == "true"
    REDIS_SSL_CERT_REQS = "required" if REDIS_SSL else None

    # Logging Security
    LOG_LEVEL = "INFO"
    LOG_SANITIZATION = True  # Remove sensitive data from logs
    LOG_RETENTION_DAYS = 30

    # Environment Validation
    REQUIRED_ENV_VARS = [
        "SECRET_KEY",
        "DATABASE_URL",
        "REDIS_URL",
        "SPOTIFY_CLIENT_ID",
        "SPOTIFY_CLIENT_SECRET",
    ]

    @classmethod
    def validate_environment(cls):
        """Validate required environment variables for production."""
        missing = []
        for var in cls.REQUIRED_ENV_VARS:
            if not os.environ.get(var):
                missing.append(var)

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Validate SECRET_KEY strength
        secret_key = os.environ.get("SECRET_KEY", "")
        if len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters for production")

        return True


def apply_security_headers(app):
    """Apply security headers to all responses."""

    @app.after_request
    def add_security_headers(response):
        for header, value in ProductionSecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

    return app


def setup_rate_limiting(app):
    """Setup rate limiting for production."""
    try:
        from flask_limiter import Limiter
        from flask_limiter.util import get_remote_address

        def user_or_ip_key_func():
            try:
                from flask_login import current_user

                if getattr(current_user, "is_authenticated", False):
                    return f"user:{getattr(current_user, 'id', 'anon')}"
            except Exception:
                pass
            return get_remote_address()

        limiter = Limiter(
            key_func=user_or_ip_key_func,
            storage_uri=ProductionSecurityConfig.RATE_LIMIT_STORAGE_URL,
            default_limits=[ProductionSecurityConfig.API_RATE_LIMITS["default"]],
        )
        limiter.init_app(app)

        # Apply specific rate limits to route prefixes safely
        # Avoid decorating non-existent endpoints which caused NoneType errors
        prefix_limits = {
            prefix: limit
            for prefix, limit in ProductionSecurityConfig.API_RATE_LIMITS.items()
            if prefix != "default"
        }

        limited_endpoints = set()
        try:
            for rule in app.url_map.iter_rules():
                for prefix, limit in prefix_limits.items():
                    if rule.rule.startswith(prefix):
                        endpoint = rule.endpoint
                        if endpoint in limited_endpoints:
                            continue
                        view_func = app.view_functions.get(endpoint)
                        if view_func is None:
                            continue
                        limiter.limit(limit)(view_func)
                        limited_endpoints.add(endpoint)
        except Exception as e:
            app.logger.warning(f"Rate limit prefix application skipped due to error: {e}")

        return limiter
    except ImportError:
        app.logger.warning("flask-limiter not installed, skipping rate limiting")
        return None


def configure_production_security(app):
    """Configure all production security measures."""
    # Validate environment
    ProductionSecurityConfig.validate_environment()

    # Apply security configuration
    app.config.update(
        {
            "SESSION_COOKIE_SECURE": ProductionSecurityConfig.SESSION_COOKIE_SECURE,
            "SESSION_COOKIE_HTTPONLY": ProductionSecurityConfig.SESSION_COOKIE_HTTPONLY,
            "SESSION_COOKIE_SAMESITE": ProductionSecurityConfig.SESSION_COOKIE_SAMESITE,
            "PERMANENT_SESSION_LIFETIME": ProductionSecurityConfig.PERMANENT_SESSION_LIFETIME,
            "WTF_CSRF_ENABLED": ProductionSecurityConfig.WTF_CSRF_ENABLED,
            "WTF_CSRF_TIME_LIMIT": ProductionSecurityConfig.WTF_CSRF_TIME_LIMIT,
            "MAX_CONTENT_LENGTH": ProductionSecurityConfig.MAX_CONTENT_LENGTH,
            "SQLALCHEMY_ENGINE_OPTIONS": ProductionSecurityConfig.SQLALCHEMY_ENGINE_OPTIONS,
        }
    )

    # Apply security middleware
    app = apply_security_headers(app)

    # Setup rate limiting
    limiter = setup_rate_limiting(app)

    app.logger.info("Production security configuration applied successfully")
    return app, limiter
