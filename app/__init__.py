"""
Christian Music Curator - Simple Flask Application Factory

A clean, straightforward Flask app for curating Christian music playlists.
"""

import os
from flask import Flask
from .extensions import db, login_manager, rq, bootstrap


def create_app(config_name='development', skip_db_init=False):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Set environment-specific configuration
    if config_name == 'testing':
        app.config['TESTING'] = True
    
    # Set debug mode for development
    if config_name == 'development':
        app.config['DEBUG'] = True
    
    # Load configuration
    app.config.update({
        # Basic Flask config
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-key-change-in-production'),
        'WTF_CSRF_ENABLED': True,
        
        # Database config - environment specific
        'SQLALCHEMY_DATABASE_URI': (
            'sqlite:///:memory:' if config_name == 'testing' 
            else os.environ.get('DATABASE_URL', 'sqlite:///app.db')
        ),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        
        # Redis config
        'RQ_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
        
        # Spotify OAuth config
        'SPOTIFY_CLIENT_ID': os.environ.get('SPOTIPY_CLIENT_ID'),
        'SPOTIFY_CLIENT_SECRET': os.environ.get('SPOTIPY_CLIENT_SECRET'),
        'SPOTIFY_REDIRECT_URI': os.environ.get('SPOTIPY_REDIRECT_URI', 'http://127.0.0.1:5001/auth/callback'),
        
        # Optional API keys
        'GENIUS_API_KEY': os.environ.get('GENIUS_API_KEY'),
        'BIBLE_API_KEY': os.environ.get('BIBLE_API_KEY'),
    })
    
    # Apply production security if in production
    if config_name == 'production' or os.environ.get('FLASK_ENV') == 'production':
        try:
            from config.production_security import configure_production_security
            app, limiter = configure_production_security(app)
            app.logger.info("Production security configuration applied")
        except ImportError:
            app.logger.warning("Production security configuration not available")
        except Exception as e:
            app.logger.error(f"Failed to apply production security: {e}")
            # Don't fail startup, but log the issue
    
    # Import models before initializing database
    from .models.models import User, Playlist, Song, AnalysisResult, Whitelist
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    rq.init_app(app)
    bootstrap.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in with Spotify to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # Register blueprints
    from .routes import auth, main, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp, url_prefix='/api')
    
    # Register simple error handlers for HTML pages
    from flask import render_template
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors with styled HTML page."""
        return render_template('error.html', 
                             error_code=404,
                             error_title="Page Not Found",
                             error_message="The page you're looking for doesn't exist."), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors with styled HTML page."""
        return render_template('error.html',
                             error_code=500,
                             error_title="Internal Server Error", 
                             error_message="Something went wrong on our end."), 500
    
    # Create database tables (if not skipping)
    if not skip_db_init:
        with app.app_context():
            db.create_all()
    
    return app 