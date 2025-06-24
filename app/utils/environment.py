"""
Simple environment validation.

Only checks what actually matters:
1. Required environment variables exist
2. SECRET_KEY is strong enough  
3. Production environment is secure
"""

import os


class EnvironmentError(Exception):
    """Raised when environment configuration is invalid"""
    pass


def validate_environment():
    """
    Validate environment configuration.
    
    Raises EnvironmentError if configuration is invalid.
    """
    # Check required variables
    required_vars = [
        'SPOTIFY_CLIENT_ID',
        'SPOTIFY_CLIENT_SECRET', 
        'SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Check SECRET_KEY strength
    secret_key = os.getenv('SECRET_KEY', '')
    if len(secret_key) < 32:
        raise EnvironmentError("SECRET_KEY is too weak - must be at least 32 characters")
    
    # Check production environment security (only if explicitly set to production)
    is_production = os.getenv('FLASK_ENV') == 'production' or os.getenv('ENV') == 'production'
    if is_production:
        _validate_production_security()


def _validate_production_security():
    """Validate production-specific security requirements"""
    database_url = os.getenv('DATABASE_URL', '')
    
    # Check database security
    if database_url and not _is_secure_database_url(database_url):
        raise EnvironmentError("Production environment requires secure database connection (HTTPS/SSL)")


def _is_secure_database_url(url):
    """Check if database URL is secure for production"""
    # Accept SSL-enabled connections
    secure_indicators = ['ssl=true', 'sslmode=require', '+pymysql', 'mysql+pymysql']
    return any(indicator in url for indicator in secure_indicators) 