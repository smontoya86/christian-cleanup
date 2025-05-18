# This file serves as an entry point for Gunicorn or other WSGI servers.
import os
from app import create_app

# Determine which configuration to use based on FLASK_CONFIG or default to 'default'
# This should match how your Flask app determines its config (e.g., from an environment variable)
flask_env = os.getenv('FLASK_CONFIG') or 'default'

app = create_app(config_name=flask_env)

if __name__ == "__main__":
    # This allows running the app directly with `python wsgi.py` for development,
    # though Flask's built-in server (`flask run`) is often preferred for that.
    # Note: For production, Gunicorn should be used as specified in the Procfile.
    app.run() 
