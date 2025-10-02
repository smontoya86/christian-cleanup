"""
Docker Secrets Loader

Loads secrets from Docker secret files (/run/secrets/*) or falls back to environment variables.
This provides backward compatibility with .env files while supporting Docker secrets.
"""

import logging
import os

logger = logging.getLogger(__name__)


def load_secret(secret_name: str, env_var_name: str = None, required: bool = True) -> str:
    """
    Load a secret from Docker secrets file or environment variable.
    
    Priority:
    1. Docker secret file (/run/secrets/<secret_name>)
    2. Environment variable specified by <env_var_name>_FILE
    3. Environment variable specified by <env_var_name>
    
    Args:
        secret_name: Name of the Docker secret (e.g., 'openai_api_key')
        env_var_name: Name of the environment variable (e.g., 'OPENAI_API_KEY')
                     If None, defaults to secret_name.upper()
        required: Whether this secret is required
        
    Returns:
        Secret value as string
        
    Raises:
        ValueError: If secret is required but not found
    """
    if env_var_name is None:
        env_var_name = secret_name.upper()
    
    # 1. Try Docker secrets directory
    docker_secret_path = f"/run/secrets/{secret_name}"
    if os.path.exists(docker_secret_path):
        try:
            with open(docker_secret_path, 'r') as f:
                value = f.read().strip()
                if value:
                    logger.info(f"✅ Loaded {secret_name} from Docker secret")
                    return value
        except Exception as e:
            logger.warning(f"Failed to read Docker secret {secret_name}: {e}")
    
    # 2. Try environment variable pointing to file
    env_file_path = os.environ.get(f"{env_var_name}_FILE")
    if env_file_path and os.path.exists(env_file_path):
        try:
            with open(env_file_path, 'r') as f:
                value = f.read().strip()
                if value:
                    logger.info(f"✅ Loaded {secret_name} from file: {env_file_path}")
                    return value
        except Exception as e:
            logger.warning(f"Failed to read secret from {env_file_path}: {e}")
    
    # 3. Try environment variable directly
    value = os.environ.get(env_var_name)
    if value:
        logger.info(f"✅ Loaded {secret_name} from environment variable")
        return value
    
    # Not found
    if required:
        raise ValueError(
            f"Required secret '{secret_name}' not found. "
            f"Provide via Docker secret, {env_var_name}_FILE, or {env_var_name}"
        )
    
    logger.debug(f"Optional secret '{secret_name}' not found")
    return ""


def load_all_secrets() -> dict:
    """
    Load all application secrets.
    
    Returns:
        Dictionary of secret names to values
    """
    secrets = {}
    
    # Required secrets
    try:
        secrets['OPENAI_API_KEY'] = load_secret('openai_api_key', 'OPENAI_API_KEY', required=True)
    except ValueError as e:
        logger.error(f"❌ {e}")
        raise
    
    # Optional secrets
    secrets['SPOTIFY_CLIENT_ID'] = load_secret('spotify_client_id', 'SPOTIFY_CLIENT_ID', required=False)
    secrets['SPOTIFY_CLIENT_SECRET'] = load_secret('spotify_client_secret', 'SPOTIFY_CLIENT_SECRET', required=False)
    secrets['GENIUS_ACCESS_TOKEN'] = load_secret('genius_access_token', 'GENIUS_ACCESS_TOKEN', required=False)
    secrets['GENIUS_CLIENT_ID'] = load_secret('genius_client_id', 'GENIUS_CLIENT_ID', required=False)
    secrets['GENIUS_CLIENT_SECRET'] = load_secret('genius_client_secret', 'GENIUS_CLIENT_SECRET', required=False)
    
    return secrets


def inject_secrets_into_env():
    """
    Load secrets and inject them into os.environ.
    This allows existing code to use os.environ.get() without changes.
    
    Call this early in application initialization.
    """
    try:
        secrets = load_all_secrets()
        
        for key, value in secrets.items():
            if value and not os.environ.get(key):
                os.environ[key] = value
        
        logger.info("✅ All secrets loaded and injected into environment")
        
    except Exception as e:
        logger.error(f"❌ Failed to load secrets: {e}")
        raise

