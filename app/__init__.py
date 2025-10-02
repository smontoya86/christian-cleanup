import os

from flask import Flask

# Import extensions
from .extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost/christian_cleanup')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Spotify OAuth Configuration
    app.config['SPOTIFY_CLIENT_ID'] = os.environ.get('SPOTIFY_CLIENT_ID')
    app.config['SPOTIFY_CLIENT_SECRET'] = os.environ.get('SPOTIFY_CLIENT_SECRET')
    app.config['SPOTIFY_REDIRECT_URI'] = os.environ.get('SPOTIFY_REDIRECT_URI', 'http://127.0.0.1:5001/auth/callback')
    
    # Token Encryption
    app.config['ENCRYPTION_KEY'] = os.environ.get('ENCRYPTION_KEY')
    
    # Database Connection Pooling
    # Only apply pooling config for PostgreSQL (not SQLite/in-memory databases)
    database_url = app.config['SQLALCHEMY_DATABASE_URI']
    is_postgresql = database_url.startswith('postgresql')
    
    if is_postgresql:
        # Optimal settings for production performance and stability
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            # Pool size: number of connections to keep in the pool
            'pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
            
            # Max overflow: additional connections beyond pool_size when pool is full
            'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 20)),
            
            # Pool timeout: seconds to wait for a connection before raising error
            'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', 30)),
            
            # Pool recycle: recycle connections after N seconds (prevent stale connections)
            'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 3600)),  # 1 hour
            
            # Pool pre-ping: test connection before using (prevents stale connection errors)
            'pool_pre_ping': True,
            
            # Echo pool: log connection pool events (set to False in production)
            'echo_pool': os.environ.get('DB_ECHO_POOL', 'false').lower() == 'true',
        }
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # Configure user loader
    from .models.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from .routes.admin import admin_bp
    from .routes.api import bp as api_bp
    from .routes.auth import bp as auth_bp
    from .routes.main import main_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp)
    
    # Register error handlers
    from flask import render_template
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Rollback any failed database transactions
        return render_template('errors/500.html'), 500
    
    return app

