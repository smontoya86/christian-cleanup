import os
from dotenv import load_dotenv
import logging
from datetime import timedelta

# Load environment variables from .env file
# Corrected basedir for when this file is in app/config/
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
load_dotenv(os.path.join(basedir, '..', '.env')) # Load .env from project root

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or logging.INFO

    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ.get('PERMANENT_SESSION_LIFETIME_DAYS', '7')))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production' # True in production
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Spotify API Configuration
    SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')
    SPOTIPY_REDIRECT_URI = os.environ.get('SPOTIPY_REDIRECT_URI')
    SPOTIFY_SCOPES = os.environ.get('SPOTIFY_SCOPES') or 'user-read-email playlist-read-private user-library-read user-top-read'

    # Genius API Configuration
    GENIUS_ACCESS_TOKEN = os.environ.get('GENIUS_ACCESS_TOKEN')

    # Bible API Configuration (Optional)
    BIBLE_API_KEY = os.environ.get('BIBLE_API_KEY')

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Corrected basedir for when this file is in app/config/
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)), 'app_dev.db')
    LOG_LEVEL = logging.DEBUG

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Force in-memory SQLite for tests
    WTF_CSRF_ENABLED = False # Disable CSRF for tests
    LOG_LEVEL = logging.DEBUG

    # Spotify credentials will be inherited from Config (os.environ)
    # and should be set by test setup (e.g., conftest.py)

class ProductionConfig(Config):
    """Production configuration."""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') # Must be set in production
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or logging.WARNING # Higher log level for production

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # Production specific initializations (e.g., logging to file or external service)
        if not app.debug and not app.testing:
            # Example: Log to a file
            # import logging
            # from logging.handlers import RotatingFileHandler
            # file_handler = RotatingFileHandler('logs/app.log', 'a', 1 * 1024 * 1024, 10)
            # file_handler.setFormatter(logging.Formatter(
            #     '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
            # app.logger.addHandler(file_handler)
            # app.logger.setLevel(cls.LOG_LEVEL)
            # app.logger.info('Application startup')
            pass # Placeholder for more robust production logging

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def setup_logging(app_config):
    """Sets up basic logging for the application."""
    logging.basicConfig(level=app_config.LOG_LEVEL,
                        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
