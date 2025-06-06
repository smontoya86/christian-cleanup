import os
from dotenv import load_dotenv
import logging
from datetime import timedelta

# Load .env before Config class definition
# Determine the base directory of the project
# __file__ is app/config/settings.py
# os.path.dirname(__file__) is app/config
# os.path.dirname(os.path.dirname(__file__)) is app
# os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) is project root
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv_path = os.path.join(project_root, '.env')

print(f"[settings.py TOP] Attempting to load .env from: {dotenv_path}")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=False)  # Changed from override=True to override=False
    print(f"[settings.py TOP] .env file loaded successfully from {dotenv_path}")
    # Debug print values immediately after loading
    print(f"[settings.py TOP] After load_dotenv - SPOTIPY_CLIENT_ID: {os.environ.get('SPOTIPY_CLIENT_ID')}")
    print(f"[settings.py TOP] After load_dotenv - SPOTIPY_CLIENT_SECRET: {'*' * 5 + os.environ.get('SPOTIPY_CLIENT_SECRET')[-5:] if os.environ.get('SPOTIPY_CLIENT_SECRET') else 'None'}")
    print(f"[settings.py TOP] After load_dotenv - SPOTIPY_REDIRECT_URI: {os.environ.get('SPOTIPY_REDIRECT_URI')}")
else:
    print(f"[settings.py TOP] .env file not found at {dotenv_path}. Relying on system environment variables.")

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or logging.INFO

    # Database Connection Pooling Configuration
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', '10')),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', '20')),
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', '1800')),  # 30 minutes
        'pool_pre_ping': True,  # Verify connections before use
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', '30')),  # 30 seconds
    }

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

    # Lyrics Cache Configuration
    LYRICS_CACHE_ENABLED = os.environ.get('LYRICS_CACHE_ENABLED', 'true').lower() == 'true'
    LYRICS_CACHE_MAX_AGE_DAYS = int(os.environ.get('LYRICS_CACHE_MAX_AGE_DAYS', '30'))
    LYRICS_CACHE_CLEANUP_HOUR = int(os.environ.get('LYRICS_CACHE_CLEANUP_HOUR', '2'))  # 2 AM
    LYRICS_CACHE_OPTIMIZATION_DAY = os.environ.get('LYRICS_CACHE_OPTIMIZATION_DAY', 'sunday')  # Weekly on Sunday
    LYRICS_CACHE_VALIDATION_HOUR = int(os.environ.get('LYRICS_CACHE_VALIDATION_HOUR', '1'))  # 1 AM

    # RQ (Redis Queue) Configuration
    RQ_REDIS_URL = os.environ.get('RQ_REDIS_URL', 'redis://redis:6379/0')
    RQ_QUEUES = ['default']  # We only need the default queue for now
    RQ_CONNECTION_CLASS = 'redis.Redis'  # Use the Redis client directly

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
    
    # Query monitoring configuration
    SQLALCHEMY_RECORD_QUERIES = True
    SLOW_QUERY_THRESHOLD = float(os.environ.get('SLOW_QUERY_THRESHOLD', '0.5'))  # 500ms default
    
    # Development-specific pool settings (smaller for local development)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', '5')),
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', '10')),
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', '3600')),  # 1 hour
        'pool_pre_ping': True,
        'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', '30')),
    }

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False # Disable CSRF for tests
    LOG_LEVEL = logging.DEBUG
    RQ_REDIS_URL = os.environ.get('RQ_TEST_REDIS_URL') or 'redis://localhost:6379/1' # Use a different Redis DB for tests
    
    # Query monitoring configuration (enabled for testing)
    SQLALCHEMY_RECORD_QUERIES = True
    SLOW_QUERY_THRESHOLD = float(os.environ.get('TEST_SLOW_QUERY_THRESHOLD', '0.1'))  # 100ms for testing
    
    # Empty engine options for testing to avoid SQLite issues with pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {}

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        # Ensure the database is clean before each test
        if app.config.get('SQLALCHEMY_DATABASE_URI'):
            from app.extensions import db
            # Drop and recreate all tables
            db.drop_all()
            db.create_all()

    # Spotify credentials will be inherited from Config (os.environ)
    # and should be set by test setup (e.g., conftest.py)

class ProductionConfig(Config):
    """Production configuration."""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') # Must be set in production
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or logging.WARNING # Higher log level for production
    
    # Production-specific pool settings (larger for production load)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('PROD_DB_POOL_SIZE', '20')),
        'max_overflow': int(os.environ.get('PROD_DB_MAX_OVERFLOW', '40')),
        'pool_recycle': int(os.environ.get('PROD_DB_POOL_RECYCLE', '1800')),  # 30 minutes
        'pool_pre_ping': True,
        'pool_timeout': int(os.environ.get('PROD_DB_POOL_TIMEOUT', '30')),
    }

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

# Debug prints for class attributes
print(f"[settings.py POST-CLASS-DEF] Config.SPOTIPY_CLIENT_ID: {getattr(Config, 'SPOTIPY_CLIENT_ID', 'NOT_FOUND_ON_CONFIG_CLASS')}")
print(f"[settings.py POST-CLASS-DEF] DevelopmentConfig.SPOTIPY_CLIENT_ID: {getattr(DevelopmentConfig, 'SPOTIPY_CLIENT_ID', 'NOT_FOUND_ON_DEVCONFIG_CLASS')}")

def setup_logging(app_config):
    """Sets up basic logging for the application."""
    logging.basicConfig(level=app_config.LOG_LEVEL,
                        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
                        datefmt='%Y-%m-%d %H:%M:%S')
