# This file serves as an entry point for Gunicorn or other WSGI servers.
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load secrets from Docker secrets or environment variables
try:
    from app.utils.secrets_loader import inject_secrets_into_env
    inject_secrets_into_env()
except Exception as e:
    logger.error(f"Failed to load secrets: {e}")
    # Continue anyway for development environments
    pass

from app import create_app

app = create_app()

if __name__ == "__main__":
    # This allows running the app directly with `python wsgi.py` for development,
    # though Flask's built-in server (`flask run`) is often preferred for that.
    # Note: For production, Gunicorn should be used as specified in the Procfile.
    app.run()
