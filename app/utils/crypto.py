"""
Cryptography utilities for sensitive data encryption
"""
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


def get_encryption_key() -> bytes:
    """
    Get or generate encryption key for token encryption.
    
    In production, this should be stored in environment variables or secrets manager.
    For development, we generate a key and store it in the app config.
    
    Returns:
        bytes: Fernet encryption key
    """
    # Try to get key from environment first
    key_str = os.environ.get('ENCRYPTION_KEY')
    
    if key_str:
        return key_str.encode()
    
    # For development, generate and store in app config
    # WARNING: This means tokens won't persist across app restarts in dev
    if not current_app.config.get('_ENCRYPTION_KEY'):
        current_app.logger.warning(
            "No ENCRYPTION_KEY found in environment. Generating temporary key for development. "
            "Tokens will not persist across app restarts. "
            "Set ENCRYPTION_KEY environment variable for production."
        )
        current_app.config['_ENCRYPTION_KEY'] = Fernet.generate_key()
    
    return current_app.config['_ENCRYPTION_KEY']


def encrypt_token(token: Optional[str]) -> Optional[str]:
    """
    Encrypt a token for secure storage.
    
    Args:
        token: Plain text token to encrypt
        
    Returns:
        Encrypted token as string, or None if input is None
    """
    if not token:
        return None
    
    try:
        cipher = Fernet(get_encryption_key())
        encrypted = cipher.encrypt(token.encode())
        return encrypted.decode()
    except Exception as e:
        current_app.logger.error(f"Token encryption failed: {e}")
        raise


def decrypt_token(encrypted_token: Optional[str]) -> Optional[str]:
    """
    Decrypt a token for use.
    
    Args:
        encrypted_token: Encrypted token string
        
    Returns:
        Decrypted token as string, or None if input is None
        
    Raises:
        InvalidToken: If token cannot be decrypted (wrong key or corrupted)
    """
    if not encrypted_token:
        return None
    
    try:
        cipher = Fernet(get_encryption_key())
        decrypted = cipher.decrypt(encrypted_token.encode())
        return decrypted.decode()
    except InvalidToken:
        current_app.logger.error("Token decryption failed: Invalid token or wrong encryption key")
        raise
    except Exception as e:
        current_app.logger.error(f"Token decryption failed: {e}")
        raise


def rotate_encryption_key(old_key: bytes, new_key: bytes) -> None:
    """
    Rotate encryption key by re-encrypting all tokens with new key.
    
    This is a placeholder for key rotation functionality.
    In production, this would:
    1. Decrypt all tokens with old key
    2. Re-encrypt with new key
    3. Update all records
    
    Args:
        old_key: Current encryption key
        new_key: New encryption key to use
    """
    # This would be implemented with a migration script
    # that processes all User records
    raise NotImplementedError("Key rotation requires manual migration script")

