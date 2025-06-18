# Configuration Guide

This guide covers the comprehensive centralized configuration system for the Christian Cleanup application.

## Overview

The application uses a centralized configuration system located in `app/config/centralized.py` that provides:

- **Single Source of Truth**: All configuration consolidated in one place
- **Environment-Aware**: Automatic environment detection and settings
- **Type Safety**: Built-in type conversion and validation
- **Development-Friendly**: Clear defaults and helpful error messages
- **Production-Ready**: Security features and environment separation

## Configuration Structure

### Core Configuration Class

The `CentralizedConfig` class consolidates all application settings:

```python
from app.config.centralized import config

# Access configuration values
debug_mode = config.DEBUG
database_url = config.DATABASE_URL
spotify_client_id = config.SPOTIFY_CLIENT_ID
```

### Environment Detection

The system automatically detects the environment based on:

1. `FLASK_ENV` environment variable
2. `TESTING` environment variable
3. Pytest execution context
4. Defaults to 'development' if not specified

## Configuration Categories

### 1. Flask Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | development | Application environment |
| `DEBUG` | True (dev), False (prod) | Debug mode |
| `SECRET_KEY` | Auto-generated | Flask session secret |
| `WTF_CSRF_ENABLED` | True | CSRF protection |

### 2. Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | SQLite (dev), PostgreSQL (prod) | Database connection string |
| `DB_POOL_SIZE` | 20 | Connection pool size |
| `DB_MAX_OVERFLOW` | 30 | Maximum pool overflow |
| `DB_POOL_RECYCLE` | 3600 | Connection recycle time (seconds) |
| `DB_POOL_TIMEOUT` | 30 | Connection timeout (seconds) |

### 3. Redis/RQ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection string |
| `RQ_DEFAULT_TIMEOUT` | 3600 | Job timeout (seconds) |
| `RQ_RESULT_TTL` | 86400 | Result TTL (seconds) |

### 4. External API Configuration

#### Spotify API
| Variable | Required | Description |
|----------|----------|-------------|
| `SPOTIFY_CLIENT_ID` | Yes | Spotify application client ID |
| `SPOTIFY_CLIENT_SECRET` | Yes | Spotify application secret |
| `SPOTIFY_REDIRECT_URI` | Yes | OAuth redirect URI |
| `SPOTIFY_SCOPES` | No | OAuth scopes (defaults provided) |

#### AI Services
| Variable | Required | Description |
|----------|----------|-------------|
| ~~`ANTHROPIC_API_KEY`~~ | ~~Optional~~ | ~~Claude AI API key~~ **DEPRECATED - Not used (local models only)** |
| `PERPLEXITY_API_KEY` | Optional | Perplexity API key |

#### Other APIs
| Variable | Required | Description |
|----------|----------|-------------|
| `GENIUS_API_TOKEN` | Optional | Genius lyrics API token |
| `BIBLE_API_KEY` | Optional | Bible API key |

### 5. Logging Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_TO_FILE` | True | Enable file logging |
| `LOG_FILE_PATH` | logs/app.log | Log file location |
| `LOG_MAX_BYTES` | 10MB | Log file rotation size |
| `LOG_BACKUP_COUNT` | 5 | Number of backup files |

### 6. Analysis Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANALYSIS_BATCH_SIZE` | 50 | Songs per analysis batch |
| `ANALYSIS_TIMEOUT` | 300 | Analysis timeout (seconds) |
| `CACHE_LYRICS_TTL` | 604800 | Lyrics cache TTL (seconds) |

## Environment Files

### Development Environment (`.env`)

Create a `.env` file in the project root:

```bash
# Flask Configuration
FLASK_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost/christian_cleanup_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Spotify API (Required)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:5000/auth/callback

# Optional APIs
GENIUS_API_TOKEN=your_genius_token
# ANTHROPIC_API_KEY=your_anthropic_key  # DEPRECATED - Not used (local models only)
PERPLEXITY_API_KEY=your_perplexity_key

# Logging
LOG_LEVEL=DEBUG
LOG_TO_FILE=true
```

### Production Environment

Set environment variables through your deployment platform:

```bash
# Required Production Settings
FLASK_ENV=production
DEBUG=false
SECRET_KEY=strong-production-secret-key
DATABASE_URL=postgresql://user:password@prod-db/christian_cleanup
REDIS_URL=redis://prod-redis:6379/0

# Required APIs
SPOTIFY_CLIENT_ID=production_client_id
SPOTIFY_CLIENT_SECRET=production_client_secret
SPOTIFY_REDIRECT_URI=https://yourdomain.com/auth/callback

# Production Logging
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE_PATH=/var/log/christian-cleanup/app.log
```

### Testing Environment

Testing configurations are automatically handled:

```bash
# Automatically set during testing
TESTING=true
FLASK_ENV=testing
DATABASE_URL=sqlite:///:memory:
REDIS_URL=redis://localhost:6379/1
```

## Docker Configuration

### Docker Environment File (`.env.docker`)

```bash
# Container-specific settings
DATABASE_URL=postgresql://postgres:password@db:5432/christian_cleanup
REDIS_URL=redis://redis:6379/0

# External services (same as development)
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://localhost:5000/auth/callback
```

### Docker Compose Integration

The configuration system integrates seamlessly with Docker Compose:

```yaml
services:
  web:
    env_file:
      - .env.docker
    environment:
      - FLASK_ENV=production
      - PORT=5000
```

## Configuration Validation

The system includes comprehensive validation:

### Automatic Validation

Configuration is validated automatically during application startup:

```python
# Validation runs automatically when config is loaded
config = get_config()  # Raises ConfigurationError if invalid
```

### Validation Rules

1. **Log Level**: Must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL
2. **Environment**: Must be development, testing, or production
3. **URLs**: Database and Redis URLs must be properly formatted
4. **Numeric Values**: Pool sizes, timeouts must be positive integers
5. **Required Fields**: Critical settings must be present in production

### Error Messages

Clear, actionable error messages help with debugging:

```python
ConfigurationError: LOG_LEVEL must be one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], got: INVALID
ConfigurationError: DATABASE_URL must be a valid database URL, got: invalid-url
ConfigurationError: SPOTIFY_CLIENT_ID is required for production environment
```

## Usage Examples

### Accessing Configuration

```python
from app.config.centralized import config

# Basic usage
if config.DEBUG:
    print("Debug mode enabled")

# Database connection
engine = create_engine(config.DATABASE_URL)

# API configuration
spotify_client = SpotifyOAuth(
    client_id=config.SPOTIFY_CLIENT_ID,
    client_secret=config.SPOTIFY_CLIENT_SECRET,
    redirect_uri=config.SPOTIFY_REDIRECT_URI
)
```

### Environment-Specific Logic

```python
from app.config.centralized import config

if config.ENVIRONMENT == 'production':
    # Production-specific setup
    app.logger.setLevel(logging.INFO)
elif config.ENVIRONMENT == 'development':
    # Development-specific setup
    app.logger.setLevel(logging.DEBUG)
```

### Testing with Custom Configuration

```python
from app.config.centralized import reload_config_for_testing

def test_with_custom_config():
    # Temporarily override configuration for testing
    reload_config_for_testing()
    # Test with custom settings
    assert config.TESTING == True
```

## Migration from Legacy Configuration

If upgrading from the old configuration system:

### 1. Update Imports

**Before:**
```python
from app.config import config
from config import DevelopmentConfig
```

**After:**
```python
from app.config.centralized import config
```

### 2. Update Environment Files

Move all settings to `.env` file using the documented format above.

### 3. Update Application Factory

The application factory automatically uses centralized configuration:

```python
from app.config.centralized import configure_app

def create_app():
    app = Flask(__name__)
    configure_app(app)  # Automatically configures from centralized system
    return app
```

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   - Error: `ConfigurationError: SPOTIFY_CLIENT_ID is required`
   - Solution: Add the required variable to your `.env` file

2. **Invalid Configuration Values**
   - Error: `ConfigurationError: LOG_LEVEL must be one of...`
   - Solution: Check the valid values in the error message

3. **Database Connection Issues**
   - Error: `ConfigurationError: DATABASE_URL must be a valid database URL`
   - Solution: Verify your database URL format

### Debug Configuration

To debug configuration issues:

```python
from app.config.centralized import config

# Print current configuration (sanitized)
print(f"Environment: {config.ENVIRONMENT}")
print(f"Debug: {config.DEBUG}")
print(f"Database: {config.DATABASE_URL}")
# Sensitive values are automatically sanitized in output
```

### Configuration Health Check

The application includes a health check endpoint that verifies configuration:

```bash
curl http://localhost:5000/health
# Returns configuration status and any issues
```

## Security Considerations

1. **Secret Management**: Never commit sensitive values to version control
2. **Environment Separation**: Use different values for development/production
3. **Access Control**: Limit access to production configuration
4. **Logging Safety**: Sensitive values are automatically sanitized in logs
5. **Validation**: All inputs are validated to prevent injection attacks

## Best Practices

1. **Use Environment Variables**: Store sensitive configuration in environment variables
2. **Document Changes**: Update this guide when adding new configuration options
3. **Validate Early**: Let the validation system catch configuration errors during startup
4. **Environment Parity**: Keep development and production configurations as similar as possible
5. **Default Values**: Provide sensible defaults for non-sensitive configuration

## Support

For configuration-related issues:

1. Check the validation error messages for specific guidance
2. Verify your `.env` file format matches the examples above
3. Ensure all required environment variables are set
4. Check the application logs for configuration-related errors

The centralized configuration system is designed to be developer-friendly while maintaining production security and reliability. 