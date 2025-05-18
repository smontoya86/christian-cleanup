from flask import Flask, jsonify, request, redirect, url_for, current_app
from flask_migrate import Migrate
from .extensions import db, login_manager, scheduler, bootstrap, rq
from .config import config, setup_logging
import os
from .jobs import sync_all_playlists_job
from .utils import format_ms_filter
import datetime

# Initialize extensions
migrate = Migrate()
login_manager.login_view = 'auth.login'
# login_manager.login_message_category = 'info'

@login_manager.unauthorized_handler
def unauthorized():
    # If the request is for an API endpoint, return JSON 401
    # Check the blueprint name associated with the request endpoint
    if request.blueprint == 'api':
        return jsonify(error="Unauthorized", message="Authentication is required to access this resource."), 401
    # Otherwise, for non-API requests, redirect to the login page
    return redirect(url_for(login_manager.login_view))

@login_manager.user_loader
def load_user(user_id):
    from .models.models import User # Import User model here
    current_app.logger.debug(f"load_user CALLED with user_id: {user_id}")
    user = db.session.get(User, int(user_id))
    if user:
        current_app.logger.debug(f"load_user: Found user {user.id} for user_id: {user_id}")
    else:
        current_app.logger.debug(f"load_user: No user found for user_id: {user_id}")
    return user

def create_app(config_name=None):
    """Application factory function."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')

    app = Flask(__name__)
    app_config = config[config_name]
    print(f"[create_app PRE-FROM_OBJECT] Type of app_config: {type(app_config)}")
    print(f"[create_app PRE-FROM_OBJECT] SPOTIPY_CLIENT_ID on app_config class: {getattr(app_config, 'SPOTIPY_CLIENT_ID', 'NOT_FOUND_ON_CONFIG_OBJ_DIRECTLY')}")
    
    app.config.from_object(app_config)

    print(f"[create_app POST-FROM_OBJECT] SPOTIPY_CLIENT_ID in app.config: {app.config.get('SPOTIPY_CLIENT_ID', 'NOT_FOUND_IN_APP_CONFIG')}")
    print(f"[create_app POST-FROM_OBJECT] All app.config keys: {list(app.config.keys())}")

    # Register custom Jinja filters
    app.jinja_env.filters['format_ms'] = format_ms_filter

    # If in testing mode, explicitly override Spotify config from environment variables
    # This ensures that os.environ.setdefault in conftest.py takes effect for these keys
    # after the initial config object has been loaded.
    if config_name == 'testing':
        app.logger.debug("Testing mode: Overriding Spotify config from environment variables if set.")
        app.config['SPOTIPY_CLIENT_ID'] = os.environ.get('SPOTIPY_CLIENT_ID', app.config.get('SPOTIPY_CLIENT_ID'))
        app.config['SPOTIPY_CLIENT_SECRET'] = os.environ.get('SPOTIPY_CLIENT_SECRET', app.config.get('SPOTIPY_CLIENT_SECRET'))
        app.config['SPOTIPY_REDIRECT_URI'] = os.environ.get('SPOTIPY_REDIRECT_URI', app.config.get('SPOTIPY_REDIRECT_URI'))
        app.config['SPOTIFY_SCOPES'] = os.environ.get('SPOTIFY_SCOPES', app.config.get('SPOTIFY_SCOPES'))
        app.logger.debug(f"SPOTIPY_CLIENT_ID set to: {app.config.get('SPOTIPY_CLIENT_ID')}")

    # Setup logging
    setup_logging(app_config)
    app.logger.info(f"Application starting with '{config_name}' configuration.")

    # Ensure all models are imported BEFORE db.init_app so metadata is populated
    from . import models # This imports the app.models package, executing its __init__.py

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    scheduler.init_app(app)
    bootstrap.init_app(app) 
    rq.init_app(app) 

    # Only start the scheduler if it's not already running AND we are not in testing mode.
    # For testing, we typically don't want background jobs running.
    if not scheduler.running and not app.config.get('TESTING', False):
        scheduler.start()

    # Instantiate and register application services
    from .services.spotify_service import SpotifyService
    from .services.list_management_service import ListManagementService

    if 'extensions' not in app.__dict__:
        app.extensions = {}
        
    # Instantiate SpotifyService, passing the app logger
    app.extensions['spotify_service'] = SpotifyService(logger=app.logger)
    app.logger.info("SpotifyService instantiated and attached to app.extensions.")

    app.extensions['list_management_service'] = ListManagementService(
        spotify_service=app.extensions['spotify_service']
    )
    app.logger.info("ListManagementService instantiated and attached to app.extensions.")

    # Register blueprints
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.logger.info("Auth blueprint registered.")

    from .main import main_bp as main_blueprint # Import from app.main
    app.register_blueprint(main_blueprint)
    app.logger.info("Main blueprint registered.")

    # Context processor to inject current year
    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.datetime.now().year}

    with app.app_context():
        # Register API blueprint
        from .api import api_bp
        app.register_blueprint(api_bp, url_prefix='/api')
        current_app.logger.info("API blueprint registered.")

        # Schedule the background sync job
        # Ensure the job doesn't run when importing for migrations or other non-server tasks
        # Or handle this within the job itself if needed.
        if not app.config.get('TESTING', False) and os.environ.get('WERKZEUG_RUN_MAIN') == 'true': 
            # Check WERKZEUG_RUN_MAIN prevents duplicate jobs with Flask reloader
            # Check not TESTING to avoid running scheduler during tests
            job_id = 'sync_all_playlists'
            if not scheduler.get_job(job_id):
                scheduler.add_job(
                    id=job_id,
                    func=sync_all_playlists_job,
                    trigger='interval',
                    hours=1, # Run every hour
                    # next_run_time=datetime.now() + timedelta(seconds=10) # Optionally delay first run
                )
                app.logger.info(f"Scheduled job '{job_id}' to run every 1 hour.")
            else:
                app.logger.info(f"Job '{job_id}' already scheduled.")

        app.logger.info("Application models imported/registered.")

    app.logger.info("Flask application created successfully.")
    return app
