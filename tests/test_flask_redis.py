from app import create_app
import os

# Create the Flask application
app = create_app()

# Get the Redis URL from the app config
redis_url = app.config.get('RQ_REDIS_URL', 'redis://localhost:6379/0')
print(f"Flask app Redis URL: {redis_url}")

# Test Redis connection using Flask-RQ2
with app.app_context():
    try:
        from redis import Redis
        from urllib.parse import urlparse
        
        # Parse the Redis URL
        url = urlparse(redis_url)
        
        # Create Redis connection
        r = Redis(
            host=url.hostname or 'localhost',
            port=url.port or 6379,
            db=int(url.path.lstrip('/') or 0),
            password=url.password,
            socket_connect_timeout=5
        )
        
        # Test connection
        r.ping()
        print("✓ Successfully connected to Redis via Flask app!")
        
        # Test setting and getting a value
        test_key = "flask_test_key_123"
        test_value = "flask_test_value_123"
        r.set(test_key, test_value)
        retrieved_value = r.get(test_key)
        print(f"✓ Successfully set and retrieved test value: {retrieved_value.decode()}")
        
        # Clean up
        r.delete(test_key)
        
    except Exception as e:
        print(f"✗ Error connecting to Redis via Flask app: {str(e)}")
        print("\nTroubleshooting steps:")
        print(f"1. Check if the Redis URL in your Flask config is correct: {redis_url}")
        print("2. Make sure Redis server is running and accessible")
        print("3. Check for any authentication requirements in your Redis configuration")

#!/usr/bin/env python3
"""
Quick test to verify database connectivity and playlist access.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.models import Playlist, Song, PlaylistSong, User
from app.utils.database import get_by_filter  # Add SQLAlchemy 2.0 utilities

def test_playlist_access():
    app = create_app()
    
    with app.app_context():
        # Test database connection
        try:
            print("Testing playlist access with Flask-RQ2...")
            
            # Get a playlist using SQLAlchemy 2.0 pattern
            playlist = get_by_filter(Playlist)  # Get first playlist
            if playlist:
                print(f"Found playlist: {playlist.name}")
                print(f"Owner ID: {playlist.owner_id}")
                print(f"Songs count: {len(playlist.songs)}")
            else:
                print("No playlists found in database")
                return
            
            # Try to access a specific playlist using SQLAlchemy 2.0 pattern
            specific_playlist = get_by_filter(Playlist, spotify_id="1U8Fwac8vpvD1s98MVNK79")
            
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False

if __name__ == '__main__':
    test_playlist_access()
