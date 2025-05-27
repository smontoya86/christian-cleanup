"""
Redis Connection Manager with advanced pooling, retry mechanisms, and health monitoring.
Implements enterprise-grade Redis connectivity for the Christian Cleanup application.
"""

import os
import time
import logging
import threading
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError
from rq import Queue

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for job retry mechanisms."""
    max_retries: int = 3
    retry_delays: List[int] = field(default_factory=lambda: [60, 300, 600])  # seconds
    exponential_backoff: bool = True
    max_delay: int = 1800  # 30 minutes


@dataclass
class ConnectionConfig:
    """Configuration for Redis connections."""
    max_connections: int = 20
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    socket_keepalive: bool = True
    socket_keepalive_options: Dict[str, int] = field(default_factory=lambda: {})
    health_check_interval: int = 30
    retry_on_timeout: bool = True
    encoding: str = 'utf-8'
    decode_responses: bool = True


class RedisHealthMonitor:
    """Monitors Redis connection health and provides statistics."""
    
    def __init__(self, connection_manager: 'RedisConnectionManager'):
        self.connection_manager = connection_manager
        self._stats = {
            'total_connections': 0,
            'failed_connections': 0,
            'successful_pings': 0,
            'failed_pings': 0,
            'last_health_check': None,
            'last_error': None,
            'connection_errors': [],
            'uptime_start': datetime.now()
        }
        self._lock = threading.Lock()
        
    def record_connection_attempt(self, success: bool, error: Optional[Exception] = None):
        """Record a connection attempt result."""
        with self._lock:
            self._stats['total_connections'] += 1
            if success:
                logger.debug("Redis connection attempt successful")
            else:
                self._stats['failed_connections'] += 1
                if error:
                    self._stats['last_error'] = str(error)
                    self._stats['connection_errors'].append({
                        'timestamp': datetime.now().isoformat(),
                        'error': str(error)
                    })
                    # Keep only last 50 errors
                    if len(self._stats['connection_errors']) > 50:
                        self._stats['connection_errors'] = self._stats['connection_errors'][-50:]
                logger.warning(f"Redis connection attempt failed: {error}")
    
    def record_ping_result(self, success: bool, error: Optional[Exception] = None):
        """Record a ping operation result."""
        with self._lock:
            self._stats['last_health_check'] = datetime.now()
            if success:
                self._stats['successful_pings'] += 1
                logger.debug("Redis ping successful")
            else:
                self._stats['failed_pings'] += 1
                if error:
                    self._stats['last_error'] = str(error)
                logger.warning(f"Redis ping failed: {error}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current health statistics."""
        with self._lock:
            stats = self._stats.copy()
            # Calculate uptime
            uptime = datetime.now() - stats['uptime_start']
            stats['uptime_seconds'] = int(uptime.total_seconds())
            
            # Calculate success rates
            total_connections = stats['total_connections']
            if total_connections > 0:
                stats['connection_success_rate'] = (
                    (total_connections - stats['failed_connections']) / total_connections * 100
                )
            else:
                stats['connection_success_rate'] = 100.0
            
            total_pings = stats['successful_pings'] + stats['failed_pings']
            if total_pings > 0:
                stats['ping_success_rate'] = stats['successful_pings'] / total_pings * 100
            else:
                stats['ping_success_rate'] = 100.0
            
            return stats


class RedisConnectionManager:
    """
    Advanced Redis connection manager with pooling, retry mechanisms, and health monitoring.
    """
    
    _instance = None
    _lock = threading.Lock()
    _pools: Dict[str, redis.ConnectionPool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.config = ConnectionConfig()
            self.retry_config = RetryConfig()
            self.health_monitor = RedisHealthMonitor(self)
            self._initialized = True
            logger.info("RedisConnectionManager initialized")
    
    def configure(self, connection_config: Optional[ConnectionConfig] = None, 
                  retry_config: Optional[RetryConfig] = None):
        """Configure the connection manager with custom settings."""
        if connection_config:
            self.config = connection_config
        if retry_config:
            self.retry_config = retry_config
        logger.info("RedisConnectionManager reconfigured")
    
    def get_connection_pool(self, redis_url: Optional[str] = None) -> redis.ConnectionPool:
        """
        Get or create a Redis connection pool for the given URL.
        
        Args:
            redis_url: Redis URL. If None, uses current app config.
            
        Returns:
            Redis connection pool instance.
        """
        if redis_url is None:
            # Try to get from Flask app config if available
            try:
                from flask import current_app
                redis_url = current_app.config.get('RQ_REDIS_URL') or current_app.config.get('REDIS_URL')
            except:
                pass
            
            # Fallback to environment variable
            if not redis_url:
                redis_url = os.environ.get('RQ_REDIS_URL') or os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        
        if redis_url not in self._pools:
            logger.info(f"Creating new Redis connection pool for {redis_url}")
            
            # Parse URL for logging (without exposing passwords)
            import urllib.parse
            parsed = urllib.parse.urlparse(redis_url)
            safe_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}"
            logger.info(f"Redis connection pool target: {safe_url}")
            
            pool = redis.ConnectionPool.from_url(
                redis_url,
                max_connections=self.config.max_connections,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                socket_keepalive=self.config.socket_keepalive,
                socket_keepalive_options=self.config.socket_keepalive_options,
                retry_on_timeout=self.config.retry_on_timeout,
                encoding=self.config.encoding,
                decode_responses=self.config.decode_responses
            )
            
            self._pools[redis_url] = pool
            logger.info(f"Redis connection pool created successfully for {safe_url}")
        
        return self._pools[redis_url]
    
    def get_connection(self, redis_url: Optional[str] = None, 
                      max_retries: int = 5, backoff_factor: float = 0.5) -> redis.Redis:
        """
        Get a Redis connection with automatic retry logic.
        
        Args:
            redis_url: Redis URL. If None, uses current app config.
            max_retries: Maximum number of connection attempts.
            backoff_factor: Exponential backoff factor for retries.
            
        Returns:
            Redis connection instance.
            
        Raises:
            RedisError: If connection fails after all retry attempts.
        """
        pool = self.get_connection_pool(redis_url)
        
        for attempt in range(max_retries):
            try:
                connection = redis.Redis(connection_pool=pool)
                # Test the connection
                connection.ping()
                
                self.health_monitor.record_connection_attempt(True)
                self.health_monitor.record_ping_result(True)
                
                if attempt > 0:
                    logger.info(f"Redis connection successful on attempt {attempt + 1}/{max_retries}")
                
                return connection
                
            except (ConnectionError, TimeoutError, RedisError) as e:
                self.health_monitor.record_connection_attempt(False, e)
                self.health_monitor.record_ping_result(False, e)
                
                if attempt == max_retries - 1:
                    logger.error(f"Redis connection failed after {max_retries} attempts: {e}")
                    raise
                
                # Calculate delay with exponential backoff
                delay = backoff_factor * (2 ** attempt)
                logger.warning(f"Redis connection attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
    
    @contextmanager
    def get_connection_context(self, redis_url: Optional[str] = None):
        """
        Context manager for Redis connections with automatic cleanup.
        
        Args:
            redis_url: Redis URL. If None, uses current app config.
            
        Yields:
            Redis connection instance.
        """
        connection = None
        try:
            connection = self.get_connection(redis_url)
            yield connection
        finally:
            if connection:
                try:
                    connection.close()
                except Exception as e:
                    logger.warning(f"Error closing Redis connection: {e}")
    
    def get_queue(self, name: str, redis_url: Optional[str] = None) -> Queue:
        """
        Get an RQ Queue instance with managed Redis connection.
        
        Args:
            name: Queue name.
            redis_url: Redis URL. If None, uses current app config.
            
        Returns:
            RQ Queue instance.
        """
        connection = self.get_connection(redis_url)
        return Queue(name, connection=connection)
    
    def test_connection(self, redis_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Test Redis connection and return detailed information.
        
        Args:
            redis_url: Redis URL. If None, uses current app config.
            
        Returns:
            Dictionary with connection test results.
        """
        start_time = time.time()
        result = {
            'success': False,
            'error': None,
            'response_time_ms': 0,
            'redis_info': {},
            'pool_info': {}
        }
        
        try:
            with self.get_connection_context(redis_url) as conn:
                # Test ping
                ping_start = time.time()
                ping_result = conn.ping()
                ping_time = (time.time() - ping_start) * 1000
                
                result.update({
                    'success': True,
                    'ping_result': ping_result,
                    'response_time_ms': ping_time
                })
                
                # Get Redis server info
                try:
                    redis_info = conn.info()
                    result['redis_info'] = {
                        'version': redis_info.get('redis_version'),
                        'uptime_in_seconds': redis_info.get('uptime_in_seconds'),
                        'connected_clients': redis_info.get('connected_clients'),
                        'used_memory_human': redis_info.get('used_memory_human'),
                        'total_commands_processed': redis_info.get('total_commands_processed')
                    }
                except Exception as e:
                    logger.warning(f"Could not get Redis info: {e}")
                
                # Get connection pool info
                pool = self.get_connection_pool(redis_url)
                result['pool_info'] = {
                    'max_connections': pool.max_connections,
                    'connection_kwargs': {k: v for k, v in pool.connection_kwargs.items() 
                                        if k not in ['password', 'username']}
                }
                
        except Exception as e:
            result.update({
                'success': False,
                'error': str(e),
                'response_time_ms': (time.time() - start_time) * 1000
            })
        
        return result
    
    def get_health_stats(self) -> Dict[str, Any]:
        """Get comprehensive health statistics."""
        return self.health_monitor.get_stats()
    
    def monitor_queue_health(self, queue_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Monitor health of RQ queues.
        
        Args:
            queue_names: List of queue names to monitor. If None, uses default queues.
            
        Returns:
            Dictionary with queue health information.
        """
        if queue_names is None:
            queue_names = ['high', 'default', 'low']
        
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'queues': {},
            'overall_status': 'healthy'
        }
        
        try:
            connection = self.get_connection()
            
            for queue_name in queue_names:
                try:
                    queue = Queue(queue_name, connection=connection)
                    failed_job_registry = queue.failed_job_registry
                    
                    # Get worker information using RQ's API
                    from rq import Worker
                    workers = Worker.all(connection=connection, queue=queue)
                    
                    queue_info = {
                        'name': queue_name,
                        'jobs_count': len(queue),
                        'failed_jobs_count': len(failed_job_registry),
                        'workers_count': len(workers),
                        'is_empty': queue.is_empty(),
                        'status': 'healthy'
                    }
                    
                    # Determine queue status
                    if queue_info['failed_jobs_count'] > 10:
                        queue_info['status'] = 'degraded'
                        health_data['overall_status'] = 'degraded'
                    elif queue_info['workers_count'] == 0 and not queue_info['is_empty']:
                        queue_info['status'] = 'unhealthy'
                        health_data['overall_status'] = 'unhealthy'
                    
                    health_data['queues'][queue_name] = queue_info
                    
                except Exception as e:
                    logger.error(f"Error monitoring queue {queue_name}: {e}")
                    health_data['queues'][queue_name] = {
                        'name': queue_name,
                        'status': 'error',
                        'error': str(e)
                    }
                    health_data['overall_status'] = 'unhealthy'
            
        except Exception as e:
            logger.error(f"Error monitoring queue health: {e}")
            health_data.update({
                'overall_status': 'error',
                'error': str(e)
            })
        
        return health_data


# Global instance for easy access
redis_manager = RedisConnectionManager()


def get_redis_connection(redis_url: Optional[str] = None) -> redis.Redis:
    """
    Get a Redis connection using the global connection manager.
    
    Args:
        redis_url: Redis URL. If None, uses current app config.
        
    Returns:
        Redis connection instance.
    """
    return redis_manager.get_connection(redis_url)


def get_queue(name: str, redis_url: Optional[str] = None) -> Queue:
    """
    Get an RQ Queue instance using the global connection manager.
    
    Args:
        name: Queue name.
        redis_url: Redis URL. If None, uses current app config.
        
    Returns:
        RQ Queue instance.
    """
    return redis_manager.get_queue(name, redis_url)


def test_redis_connection(redis_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Test Redis connection and return detailed information.
    
    Args:
        redis_url: Redis URL. If None, uses current app config.
        
    Returns:
        Dictionary with connection test results.
    """
    return redis_manager.test_connection(redis_url) 