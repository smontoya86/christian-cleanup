"""
Redis cache service for improving application performance.
"""
import redis
import json
import functools
import time
from flask import current_app


class RedisCache:
    """Redis-based cache service with graceful fallback."""
    
    def __init__(self, app=None):
        self.app = app
        self._redis_client = None
        self.cache_hits = 0
        self.cache_misses = 0
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize cache with Flask app."""
        self.app = app
        redis_url = app.config.get('RQ_REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            self._redis_client = redis.from_url(redis_url)
            # Test connection
            self._redis_client.ping()
        except (redis.RedisError, redis.ConnectionError) as e:
            current_app.logger.warning(f"Redis connection failed: {e}")
            self._redis_client = None
        
        # Register extension with app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['redis_cache'] = self
    
    @property
    def redis(self):
        """Get Redis client."""
        if self._redis_client is None:
            raise RuntimeError("Redis cache not initialized or unavailable")
        return self._redis_client
    
    def get(self, key):
        """Get value from cache."""
        try:
            if self._redis_client is None:
                self.cache_misses += 1
                return None
                
            value = self.redis.get(key)
            if value:
                self.cache_hits += 1
                return json.loads(value)
            self.cache_misses += 1
            return None
        except redis.RedisError:
            if current_app:
                current_app.logger.warning(f"Redis error when getting key {key}")
            self.cache_misses += 1
            return None
    
    def set(self, key, value, expiry=300):
        """Set value in cache with expiry in seconds."""
        try:
            if self._redis_client is None:
                return False
                
            return self.redis.setex(key, expiry, json.dumps(value, default=str))
        except redis.RedisError:
            if current_app:
                current_app.logger.warning(f"Redis error when setting key {key}")
            return False
    
    def delete(self, key):
        """Delete key from cache."""
        try:
            if self._redis_client is None:
                return False
                
            return self.redis.delete(key)
        except redis.RedisError:
            if current_app:
                current_app.logger.warning(f"Redis error when deleting key {key}")
            return False
    
    def delete_pattern(self, pattern):
        """Delete all keys matching pattern."""
        try:
            if self._redis_client is None:
                return 0
                
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except redis.RedisError:
            if current_app:
                current_app.logger.warning(f"Redis error when deleting pattern {pattern}")
            return 0
    
    def get_metrics(self):
        """Return cache hit/miss metrics."""
        total = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total) * 100 if total > 0 else 0
        return {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'total': total,
            'hit_rate': hit_rate
        }


# Create singleton instance
cache = RedisCache()


def cached(expiry=300, key_prefix='view'):
    """Decorator for caching view functions."""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Create a cache key based on function name and arguments
            key_parts = [key_prefix, f.__name__]
            
            # Add sorted kwargs to ensure consistent key generation
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}:{v}")
            
            # Add positional args (skip complex objects)
            for arg in args:
                if hasattr(arg, '__dict__'):  # Skip complex objects
                    continue
                key_parts.append(str(arg))
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # If not in cache, call the function
            result = f(*args, **kwargs)
            
            # Cache the result
            cache.set(cache_key, result, expiry)
            return result
        return decorated_function
    return decorator


def invalidate_playlist_cache(playlist_id=None):
    """Helper to invalidate playlist-related caches."""
    if playlist_id:
        # Invalidate specific playlist cache
        cache.delete_pattern(f"view:playlist_detail:playlist_id:{playlist_id}*")
    else:
        # Invalidate all playlist caches
        cache.delete_pattern("view:playlist_detail*")
    
    # Always invalidate dashboard cache as it shows playlist summaries
    cache.delete_pattern("view:dashboard*")


def invalidate_analysis_cache(song_id=None):
    """Helper to invalidate analysis-related caches."""
    if song_id:
        # Find playlists containing this song and invalidate them
        from ..models.models import PlaylistSong
        playlist_songs = PlaylistSong.query.filter_by(song_id=song_id).all()
        for ps in playlist_songs:
            invalidate_playlist_cache(ps.playlist_id)
    else:
        # Invalidate all playlist and analysis caches
        cache.delete_pattern("view:playlist_detail*")
        cache.delete_pattern("view:dashboard*") 