import sys
import os
import pytest
from flask import current_app
from datetime import datetime, timedelta

# Add project root to sys.path once at the top
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Update imports
from app import create_app
from app.extensions import db
from app.models.models import User, Playlist, Song, PlaylistSong # Ensure all models used in fixtures are imported

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    os.environ['FLASK_ENV'] = 'testing'
    os.environ.setdefault('SPOTIPY_CLIENT_ID', 'test_client_id')
    os.environ.setdefault('SPOTIPY_CLIENT_SECRET', 'test_client_secret')
    os.environ.setdefault('SPOTIPY_REDIRECT_URI', 'http://localhost/callback')
    os.environ.setdefault('SPOTIFY_SCOPES', 'user-read-email')

    app_instance = create_app('testing')

    with app_instance.app_context():
        db.create_all()
        yield app_instance
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def db_session(app):
    """Ensures a clean database state for each test and provides the session."""
    with app.app_context(): # Ensure app context is active for logging and db operations
        # Ensure tables are created in this context, in case it's a truly fresh in-memory DB for this scope
        # This is generally safe; create_all won't re-create if they exist on the bound engine.
        db.create_all()

        # --- Re-enable table clearing ---
        for table in reversed(db.metadata.sorted_tables):
            try:
                db.session.execute(table.delete())
            except Exception as e_del:
                pass # Or re-raise, or log to a more permanent test log if needed
        try:
            db.session.commit() # Commit the clear operations
        except Exception as e_commit:
            db.session.rollback()
            raise # Re-raise if committing clear fails, as it's a setup issue
        # --- End table clearing ---

        # Each test will run within its own nested transaction (SAVEPOINT)
        db.session.begin_nested()

    yield db.session # Provide the session to the test

    # Rollback the test's SAVEPOINT
    db.session.rollback()
    db.session.remove() # Ensure session is removed after each test

@pytest.fixture(scope='function')
def new_user(db_session): 
    """Fixture to create a new user for testing, within the test's transaction."""
    user = User(
        spotify_id='test_spotify_id', 
        display_name='Test User',
        access_token='dummy_access_token', 
        refresh_token='dummy_refresh_token', 
        token_expiry=datetime.utcnow() + timedelta(hours=1)
    )
    db_session.add(user)
    db_session.flush() 
    return user
