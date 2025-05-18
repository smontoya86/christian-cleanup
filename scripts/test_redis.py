#!/usr/bin/env python3
"""
Test script to verify Redis connection and basic operations.
"""
import os
import sys
from redis import Redis
from datetime import datetime

def test_redis_connection():
    """Test Redis connection and basic operations."""
    try:
        # Get Redis URL from environment or use default
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        print(f"Connecting to Redis at {redis_url}...")
        redis_conn = Redis.from_url(redis_url)
        
        # Test connection
        redis_conn.ping()
        print("✓ Successfully connected to Redis")
        
        # Test basic operations
        test_key = "test:connection"
        test_value = f"Test at {datetime.utcnow().isoformat()}"
        
        # Set a test key
        redis_conn.set(test_key, test_value)
        print(f"✓ Set test key '{test_key}'")
        
        # Get the test key
        retrieved_value = redis_conn.get(test_key)
        if retrieved_value and retrieved_value.decode('utf-8') == test_value:
            print("✓ Successfully retrieved test key")
        else:
            print("✗ Failed to retrieve test key")
            return False
            
        # Clean up
        redis_conn.delete(test_key)
        print("✓ Cleaned up test key")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing Redis connection: {e}")
        return False

if __name__ == "__main__":
    print("Testing Redis connection...")
    success = test_redis_connection()
    
    if success:
        print("\n✅ Redis connection test passed!")
        sys.exit(0)
    else:
        print("\n❌ Redis connection test failed!")
        print("\nTroubleshooting steps:")
        print("1. Make sure Redis server is running (run 'redis-cli ping' to check)")
        print("2. Verify the REDIS_URL in your .env file is correct")
        print("3. Check if Redis is configured to accept connections (check bind and protected-mode in redis.conf)")
        print("4. Ensure no firewall is blocking the Redis port (default: 6379)")
        sys.exit(1)
