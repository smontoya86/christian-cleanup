from app import create_app
import os
import logging

# Create the Flask app instance using the factory
# The FLASK_ENV environment variable will determine which config is loaded (e.g., 'development', 'production')
# If FLASK_ENV is not set, it defaults to 'development'
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Simple configuration for our simplified structure
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    port = int(os.getenv('PORT', 5001))
    host = os.getenv('HOST', '0.0.0.0')
    
    # Set up detailed logging for debugging
    if debug_mode:
        logging.basicConfig(level=logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
    
    app.logger.info(f"Starting application on host {host}, port {port}, debug mode: {debug_mode}")
    app.run(host=host, port=port, debug=debug_mode)
