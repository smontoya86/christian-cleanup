"""
Christian Music Curator - Simple Flask Application Factory

A clean, straightforward Flask app for curating Christian music playlists.
"""

import os

from flask import Flask
from flask_migrate import Migrate

from .extensions import bootstrap, db, login_manager


def create_app(config_name="development", skip_db_init=False):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Set environment-specific configuration
    if config_name == "testing":
        app.config["TESTING"] = True
        # Improve SQLite-in-memory behavior for threaded tests
        try:
            from sqlalchemy.pool import StaticPool

            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            }
        except Exception:
            pass

    # Set debug mode for development
    if config_name == "development":
        app.config["DEBUG"] = True

    # Load configuration
    app.config.update(
        {
            # Basic Flask config
            "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-key-change-in-production"),
            "WTF_CSRF_ENABLED": True,
            # Database config - environment specific
            "SQLALCHEMY_DATABASE_URI": (
                "sqlite:///:memory:"
                if config_name == "testing"
                else os.environ.get("DATABASE_URL", "sqlite:///app.db")
            ),
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            # Redis config
            "RQ_REDIS_URL": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
            # Spotify OAuth config (support both SPOTIFY_* and SPOTIPY_* envs)
            "SPOTIFY_CLIENT_ID": os.environ.get("SPOTIFY_CLIENT_ID")
            or os.environ.get("SPOTIPY_CLIENT_ID"),
            "SPOTIFY_CLIENT_SECRET": os.environ.get("SPOTIFY_CLIENT_SECRET")
            or os.environ.get("SPOTIPY_CLIENT_SECRET"),
            "SPOTIFY_REDIRECT_URI": (
                os.environ.get("SPOTIFY_REDIRECT_URI")
                or os.environ.get("SPOTIPY_REDIRECT_URI")
                or "http://127.0.0.1:5001/auth/callback"
            ),
            # Optional API keys
            "GENIUS_API_KEY": os.environ.get("GENIUS_API_KEY"),
            "BIBLE_API_KEY": os.environ.get("BIBLE_API_KEY"),
            # Google Analytics (GA4)
            "GA4_MEASUREMENT_ID": os.environ.get("GA4_MEASUREMENT_ID"),
            "GA4_API_SECRET": os.environ.get(
                "GA4_API_SECRET"
            ),  # For Measurement Protocol (optional)
            "GA4_DEBUG_MODE": os.environ.get("GA4_DEBUG_MODE", "0") in ["1", "true", "True"],
        }
    )

    # Defer production security application until after blueprints are registered

    # Import models before initializing database
    from .models.models import AnalysisResult, Playlist, Song, User, Whitelist

    # Initialize extensions with app
    db.init_app(app)
    # Enable Flask-Migrate CLI (flask db ...)
    try:
        Migrate(app, db)
    except Exception:
        pass
    login_manager.init_app(app)
    bootstrap.init_app(app)

    # Configure login manager
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in with Spotify to access this page."

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from .routes import api, auth, main

    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp, url_prefix="/api")

    # Apply production security AFTER routes are registered so rate limits bind correctly
    if config_name == "production" or os.environ.get("FLASK_ENV") == "production":
        try:
            # Ensure a strong SECRET_KEY or generate a random one for runtime if not provided
            if not os.environ.get("SECRET_KEY") or len(os.environ.get("SECRET_KEY", "")) < 32:
                import secrets

                os.environ["SECRET_KEY"] = secrets.token_hex(32)
                app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
            from config.production_security import configure_production_security

            app, limiter = configure_production_security(app)
            app.logger.info("Production security configuration applied")
        except ImportError:
            app.logger.warning("Production security configuration not available")
        except Exception as e:
            app.logger.error(f"Failed to apply production security: {e}")

    # Auto-start background analysis for users on dashboard only (not homepage)
    @app.before_request
    def _auto_background_analysis():
        try:
            from flask import request
            from flask_login import current_user

            # Only trigger on dashboard page and when authenticated
            # Skip index to avoid performance issues on homepage
            if not current_user.is_authenticated:
                return
            if request.endpoint not in ("main.dashboard",):  # Removed main.index
                return
            # If a job is already active for this user, skip
            state = app.config.get("USER_ANALYSIS_PROGRESS", {})
            snap = state.get(current_user.id)
            if snap and snap.get("active"):
                return
            # Start background analysis (best-effort)
            from app.utils.analysis_starter import start_user_analysis

            start_user_analysis(app, current_user.id)
        except Exception:
            # Never block request flow
            pass

    # Inject common template variables (including GA4 settings)
    @app.context_processor
    def inject_template_globals():
        return {
            "GA4_MEASUREMENT_ID": app.config.get("GA4_MEASUREMENT_ID"),
            "GA4_DEBUG_MODE": app.config.get("GA4_DEBUG_MODE", False),
        }

    # Register simple error handlers for HTML pages
    from flask import render_template

    from .utils.correlation import HEADER_NAME, get_request_id

    @app.after_request
    def add_request_id_header(response):
        try:
            response.headers[HEADER_NAME] = get_request_id()
        except Exception:
            pass
        return response

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors with styled HTML page."""
        return render_template(
            "error.html",
            error_code=404,
            error_title="Page Not Found",
            error_message="The page you're looking for doesn't exist.",
        ), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors with styled HTML page."""
        app.logger.error(f"500 Internal Server Error: {error}", exc_info=True)
        return render_template(
            "error.html",
            error_code=500,
            error_title="Internal Server Error",
            error_message="Something went wrong on our end.",
        ), 500

    # Ensure AJAX auth failures return JSON 401 with redirect target instead of a 302 to Spotify
    @login_manager.unauthorized_handler
    def handle_unauthorized():
        from flask import jsonify, redirect, request, url_for

        is_ajax = request.headers.get(
            "X-Requested-With"
        ) == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")
        login_url = url_for("auth.login")
        if is_ajax:
            return jsonify({"success": False, "error": "unauthorized", "redirect": login_url}), 401
        return redirect(login_url)

    # Create database tables (if not skipping)
    if not skip_db_init:
        with app.app_context():
            db.create_all()

            # Pre-load AI models for fast analysis (PERFORMANCE FIX)
            disable_pref = os.environ.get("DISABLE_ANALYZER_PREFLIGHT", "0") in ("1", "true", "True")
            is_ci = os.environ.get("CI", "0") in ("1", "true", "True")
            if config_name != "testing" and not disable_pref and not is_ci:  # Skip model loading in tests/CI/offline
                from .reloader import Reloader
                app.config["ANALYZER_RELOADER"] = Reloader(app, watch_files=["/home/ubuntu/christian-cleanup/app/services/analyzers/router_analyzer.py"])
                try:
                    # Only warm Router/LLM analyzer (OpenAI-compatible)
                    from .services.analyzer_cache import (
                        AnalyzerCache,
                        get_analyzer_info,
                        initialize_analyzer,
                        is_analyzer_ready,
                    )

                    preflight_ok, msg = AnalyzerCache().preflight()
                    if preflight_ok and "endpoint" in msg:
                        app.logger.info("🚀 Pre-loading LLM analyzer for fast analysis...")
                        _ = initialize_analyzer()
                        if is_analyzer_ready():
                            model_info = get_analyzer_info()
                            app.logger.info(f"✅ AI models pre-loaded successfully: {model_info}")
                            app.logger.info("🚀 Analysis requests will now be fast!")
                        else:
                            app.logger.warning("⚠️ Analyzer not ready after initialization")
                    else:
                        app.logger.info("⏭️ Skipping analyzer pre-load (endpoint not ready)")
                except Exception as e:
                    app.logger.error(f"❌ Failed to pre-load analyzer: {e}")
                    app.logger.warning("⚠️ Analysis may be slower on first request")

            # Auto-build RAG index at startup when enabled
            try:
                from .services.rules_rag import build_index as rag_build_index

                info = rag_build_index(force=False)
                app.logger.info(f"[RAG] startup status: {info}")
            except Exception as e:
                app.logger.warning(f"[RAG] startup skipped/failed: {e}")

            # Queue system removed - job reconnection no longer needed
            # All analysis is performed directly in web container using batch processing

    return app
