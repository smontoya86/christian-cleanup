from app import create_app
import os

# Create the Flask app instance using the factory
# The FLASK_ENV environment variable will determine which config is loaded (e.g., 'development', 'production')
# If FLASK_ENV is not set, it defaults to 'default' (which is DevelopmentConfig)
app = create_app(os.getenv('FLASK_ENV'))

if __name__ == '__main__':
    # The host and port can also be configured via environment variables or app.config
    # For Docker, host='0.0.0.0' is important to make the server accessible externally
    host = app.config.get('HOST', '0.0.0.0')
    port = app.config.get('PORT', 5000)
    debug = app.config.get('DEBUG', False)
    
    app.logger.info(f"Starting application on host {host}, port {port}, debug mode: {debug}")
    app.run(host=host, port=port, debug=debug)
