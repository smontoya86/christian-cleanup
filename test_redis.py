import os
import redis
from dotenv import load_dotenv

# Load environment variables
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv_path = os.path.join(project_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path, override=True)

# Get Redis URL from environment or use default
redis_url = os.environ.get('RQ_REDIS_URL', 'redis://localhost:6379/0')
print(f"Connecting to Redis at: {redis_url}")

try:
    # Try to connect to Redis
    r = redis.Redis.from_url(redis_url, socket_connect_timeout=5)
    r.ping()
    print("✓ Successfully connected to Redis!")
    
    # Test setting and getting a value
    test_key = "test_key_123"
    test_value = "test_value_123"
    r.set(test_key, test_value)
    retrieved_value = r.get(test_key)
    print(f"✓ Successfully set and retrieved test value: {retrieved_value.decode()}")
    
    # Clean up
    r.delete(test_key)
    
except Exception as e:
    print(f"✗ Error connecting to Redis: {str(e)}")
    print("\nTroubleshooting steps:")
    print("1. Make sure Redis server is running: `redis-cli ping` should return PONG")
    print("2. Check if Redis URL is correct (current: {})".format(redis_url))
    print("3. If using a password, make sure it's set in the URL: redis://:password@localhost:6379/0")
    print("4. Check if Redis is configured to accept connections (check bind and protected-mode in redis.conf)")
    print("5. Check if there's a firewall blocking the connection")
