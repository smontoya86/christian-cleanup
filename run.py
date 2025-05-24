from app import create_app
import os
import logging

# Create the Flask app instance using the factory
# The FLASK_ENV environment variable will determine which config is loaded (e.g., 'development', 'production')
# If FLASK_ENV is not set, it defaults to 'default' (which is DevelopmentConfig)
app = create_app(os.getenv('FLASK_ENV'))

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    port = int(os.environ.get('PORT', 5001))  # Changed back to 5001
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Set up detailed logging for debugging
    if debug_mode:
        logging.basicConfig(level=logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
    
    app.logger.info(f"Starting application on host {host}, port {port}, debug mode: {debug_mode}")
    app.run(host=host, port=port, debug=debug_mode)
