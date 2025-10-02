# This file serves as an entry point for Gunicorn or other WSGI servers.
import logging

from app import create_app
from app.utils.secrets_loader import inject_secrets_into_env

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load secrets from Docker secrets or environment variables
try:
    inject_secrets_into_env()
except Exception as e:
    logger.error(f"Failed to load secrets: {e}")
    # Continue anyway for development environments

app = create_app()

if __name__ == "__main__":
    # This allows running the app directly with `python wsgi.py` for development,
    # though Flask's built-in server (`flask run`) is often preferred for that.
    # Note: For production, Gunicorn should be used as specified in the Procfile.
    app.run()
