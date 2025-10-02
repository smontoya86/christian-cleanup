"""
Redis Cache Service

Provides fast, distributed caching for analysis results.

Cache Hierarchy:
1. Redis (microseconds) - Hot cache
2. Database (milliseconds) - Persistent cache
3. OpenAI API (seconds) - Source of truth

TTL Strategy:
- Analysis results: 30 days (user preference: effectively permanent)
- Reanalysis triggered by: model version change, manual request
"""

import json
import logging
import os
from typing import Optional, Dict, Any
from datetime import timedelta

import redis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis-based caching for analysis results.
    
    Features:
    - Fast in-memory lookups
    - Distributed caching across multiple servers
    - Automatic expiration with configurable TTL
    - Graceful fallback on connection failures
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        db: int = 0,
        password: str = None,
        default_ttl: int = 2592000  # 30 days in seconds
    ):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis host (defaults to REDIS_HOST env var or 'localhost')
            port: Redis port (defaults to REDIS_PORT env var or 6379)
            db: Redis database number (default: 0)
            password: Redis password (defaults to REDIS_PASSWORD env var)
            default_ttl: Default TTL in seconds (default: 30 days)
        """
        self.host = host or os.environ.get('REDIS_HOST', 'localhost')
        self.port = port or int(os.environ.get('REDIS_PORT', 6379))
        self.db = db
        self.password = password or os.environ.get('REDIS_PASSWORD')
        self.default_ttl = default_ttl
        
        self._client: Optional[redis.Redis] = None
        self._connection_failed = False
        
        logger.info(
            f"RedisCache initialized: {self.host}:{self.port} "
            f"(db={self.db}, ttl={self.default_ttl}s)"
        )
    
    @property
    def client(self) -> Optional[redis.Redis]:
        """Get or create Redis client with lazy initialization."""
        if self._connection_failed:
            return None
        
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                # Test connection
                self._client.ping()
                logger.info(f"✅ Redis connection established: {self.host}:{self.port}")
                
            except (RedisConnectionError, RedisError) as e:
                logger.error(f"❌ Failed to connect to Redis: {e}")
                self._connection_failed = True
                self._client = None
        
        return self._client
    
    def _make_key(self, artist: str, title: str, lyrics_hash: str, model_version: str) -> str:
        """
        Generate cache key for analysis result.
        
        Format: analysis:{model_version}:{artist}:{title}:{lyrics_hash}
        """
        # Normalize strings
        artist = artist.strip().lower()
        title = title.strip().lower()
        
        return f"analysis:{model_version}:{artist}:{title}:{lyrics_hash}"
    
    def get_analysis(
        self,
        artist: str,
        title: str,
        lyrics_hash: str,
        model_version: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached analysis result.
        
        Args:
            artist: Artist name
            title: Song title
            lyrics_hash: SHA256 hash of lyrics
            model_version: Model version used for analysis
            
        Returns:
            Analysis result dict or None if not found
        """
        if self.client is None:
            return None
        
        try:
            key = self._make_key(artist, title, lyrics_hash, model_version)
            cached = self.client.get(key)
            
            if cached:
                logger.debug(f"✅ Redis cache hit: {artist} - {title}")
                result = json.loads(cached)
                result['cache_hit'] = True
                result['cache_source'] = 'redis'
                return result
            
            logger.debug(f"❌ Redis cache miss: {artist} - {title}")
            return None
            
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Redis get error: {e}")
            return None
    
    def set_analysis(
        self,
        artist: str,
        title: str,
        lyrics_hash: str,
        model_version: str,
        analysis_result: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache analysis result.
        
        Args:
            artist: Artist name
            title: Song title
            lyrics_hash: SHA256 hash of lyrics
            model_version: Model version used for analysis
            analysis_result: Analysis result to cache
            ttl: Time to live in seconds (default: use default_ttl)
            
        Returns:
            True if successful, False otherwise
        """
        if self.client is None:
            return False
        
        try:
            key = self._make_key(artist, title, lyrics_hash, model_version)
            
            # Remove cache metadata before storing
            clean_result = {k: v for k, v in analysis_result.items() 
                          if k not in ['cache_hit', 'cache_source']}
            
            value = json.dumps(clean_result)
            ttl_seconds = ttl or self.default_ttl
            
            self.client.setex(key, ttl_seconds, value)
            logger.debug(f"💾 Cached in Redis: {artist} - {title} (TTL: {ttl_seconds}s)")
            return True
            
        except (RedisError, TypeError) as e:
            logger.warning(f"Redis set error: {e}")
            return False
    
    def delete_analysis(
        self,
        artist: str,
        title: str,
        lyrics_hash: str,
        model_version: str
    ) -> bool:
        """
        Delete cached analysis.
        
        Args:
            artist: Artist name
            title: Song title
            lyrics_hash: SHA256 hash of lyrics
            model_version: Model version
            
        Returns:
            True if deleted, False otherwise
        """
        if self.client is None:
            return False
        
        try:
            key = self._make_key(artist, title, lyrics_hash, model_version)
            deleted = self.client.delete(key)
            
            if deleted:
                logger.debug(f"🗑️  Deleted from Redis: {artist} - {title}")
            
            return bool(deleted)
            
        except RedisError as e:
            logger.warning(f"Redis delete error: {e}")
            return False
    
    def flush_by_model_version(self, model_version: str) -> int:
        """
        Flush all cached analyses for a specific model version.
        
        Useful when updating the model and wanting to trigger re-analysis.
        
        Args:
            model_version: Model version to flush
            
        Returns:
            Number of keys deleted
        """
        if self.client is None:
            return 0
        
        try:
            pattern = f"analysis:{model_version}:*"
            cursor = 0
            deleted_count = 0
            
            while True:
                cursor, keys = self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted_count += self.client.delete(*keys)
                
                if cursor == 0:
                    break
            
            logger.info(f"🗑️  Flushed {deleted_count} Redis keys for model: {model_version}")
            return deleted_count
            
        except RedisError as e:
            logger.error(f"Redis flush error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        if self.client is None:
            return {
                'connected': False,
                'error': 'Redis connection failed'
            }
        
        try:
            info = self.client.info('stats')
            memory = self.client.info('memory')
            
            # Count analysis keys
            cursor = 0
            analysis_count = 0
            while True:
                cursor, keys = self.client.scan(cursor, match="analysis:*", count=100)
                analysis_count += len(keys)
                if cursor == 0:
                    break
            
            return {
                'connected': True,
                'total_keys': self.client.dbsize(),
                'analysis_keys': analysis_count,
                'used_memory_mb': round(memory.get('used_memory', 0) / 1024 / 1024, 2),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': round(
                    info.get('keyspace_hits', 0) / 
                    max(info.get('keyspace_hits', 0) + info.get('keyspace_misses', 0), 1) * 100,
                    2
                )
            }
            
        except RedisError as e:
            logger.error(f"Redis stats error: {e}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def health_check(self) -> bool:
        """
        Check if Redis is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        if self.client is None:
            return False
        
        try:
            return self.client.ping()
        except RedisError:
            return False


# Global Redis cache instance
_redis_cache: Optional[RedisCache] = None


def get_redis_cache() -> RedisCache:
    """Get the global Redis cache instance."""
    global _redis_cache
    
    if _redis_cache is None:
        _redis_cache = RedisCache()
    
    return _redis_cache

