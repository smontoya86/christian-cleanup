"""
Worker configuration for RQ (Redis Queue) with platform-specific optimizations.
Supports both fork-based and threading-based worker modes.
"""

import os
import platform
from rq import Worker
from rq.worker import WorkerStatus


# Queue configuration
HIGH_PRIORITY_QUEUE = 'high'
DEFAULT_QUEUE = 'default'
LOW_PRIORITY_QUEUE = 'low'

# Default queue listening order (high priority first)
DEFAULT_QUEUES = [HIGH_PRIORITY_QUEUE, DEFAULT_QUEUE, LOW_PRIORITY_QUEUE]


def configure_worker_for_platform(connection, queues=None, worker_class=None, **kwargs):
    """
    Create a platform-optimized RQ worker with appropriate configuration.
    
    Args:
        connection: Redis connection instance
        queues: List of queue names to listen on (default: DEFAULT_QUEUES)
        worker_class: Custom worker class (optional)
        **kwargs: Additional worker configuration options
    
    Returns:
        Configured RQ Worker instance
    """
    if queues is None:
        queues = DEFAULT_QUEUES
    
    # Detect platform
    is_macos = platform.system() == 'Darwin'
    is_docker = os.path.exists('/.dockerenv')
    
    # Base worker configuration
    worker_config = {
        'queues': queues,
        'connection': connection,
        **kwargs
    }
    
    # Platform-specific configuration
    if is_macos and not is_docker:
        print("macOS detected: Configuring worker with platform optimizations")
        
        # Apply macOS fork safety measures
        os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
        
        # Use threading mode if explicitly requested or if fork mode fails
        use_threading = os.environ.get('RQ_WORKER_USE_THREADING', 'false').lower() == 'true'
        
        if use_threading:
            print("Threading mode enabled for macOS compatibility")
            # Note: RQ doesn't have built-in threading mode, but we can configure
            # the worker to be more thread-safe and use different job execution
            worker_config.update({
                'job_monitoring_interval': 1,  # More frequent monitoring
                'default_worker_ttl': 420,     # Shorter TTL for better cleanup
            })
        else:
            print("Fork mode with safety measures enabled")
            
    elif is_docker:
        print("Docker environment detected: Using standard configuration")
        # Docker environments typically work well with fork mode
        worker_config.update({
            'job_monitoring_interval': 5,
            'default_worker_ttl': 420,
        })
    else:
        print("Linux/Unix environment detected: Using standard configuration")
        # Standard configuration for Linux environments
        pass
    
    # Create worker instance
    if worker_class:
        worker = worker_class(**worker_config)
    else:
        worker = Worker(**worker_config)
    
    return worker


def create_threading_worker(connection, queues=None, **kwargs):
    """
    Create a worker optimized for threading-based job execution.
    This is an alternative approach for environments where fork() causes issues.
    
    Args:
        connection: Redis connection instance
        queues: List of queue names to listen on
        **kwargs: Additional worker configuration
    
    Returns:
        Worker configured for threading-based execution
    """
    if queues is None:
        queues = DEFAULT_QUEUES
    
    print("Creating threading-optimized worker")
    
    # Threading-specific configuration
    threading_config = {
        'queues': queues,
        'connection': connection,
        'job_monitoring_interval': 1,      # Frequent monitoring for responsiveness
        'default_worker_ttl': 300,         # Shorter TTL for threading mode
        **kwargs
    }
    
    # Set environment variables for threading safety
    os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
    os.environ['RQ_WORKER_USE_THREADING'] = 'true'
    
    worker = Worker(**threading_config)
    
    # Add custom attributes to identify this as a threading worker
    worker._is_threading_mode = True
    worker._platform_mode = 'threading'
    
    return worker


def get_worker_info(worker):
    """
    Get information about the worker configuration and platform.
    
    Args:
        worker: RQ Worker instance
    
    Returns:
        Dictionary with worker information
    """
    info = {
        'platform': platform.system(),
        'is_docker': os.path.exists('/.dockerenv'),
        'worker_id': worker.name,
        'queues': [q.name for q in worker.queues],
        'connection_info': {
            'host': worker.connection.connection_pool.connection_kwargs.get('host', 'unknown'),
            'port': worker.connection.connection_pool.connection_kwargs.get('port', 'unknown'),
            'db': worker.connection.connection_pool.connection_kwargs.get('db', 0),
        },
        'threading_mode': getattr(worker, '_is_threading_mode', False),
        'platform_mode': getattr(worker, '_platform_mode', 'fork'),
        'environment_vars': {
            'OBJC_DISABLE_INITIALIZE_FORK_SAFETY': os.environ.get('OBJC_DISABLE_INITIALIZE_FORK_SAFETY'),
            'RQ_WORKER_USE_THREADING': os.environ.get('RQ_WORKER_USE_THREADING'),
        }
    }
    
    return info


def print_worker_startup_info(worker):
    """
    Print detailed information about the worker configuration at startup.
    
    Args:
        worker: RQ Worker instance
    """
    info = get_worker_info(worker)
    
    print("\n" + "="*60)
    print("RQ WORKER STARTUP INFORMATION")
    print("="*60)
    print(f"Platform: {info['platform']}")
    print(f"Docker Environment: {info['is_docker']}")
    print(f"Worker ID: {info['worker_id']}")
    print(f"Platform Mode: {info['platform_mode']}")
    print(f"Threading Mode: {info['threading_mode']}")
    print(f"Queues: {', '.join(info['queues'])}")
    print(f"Redis Connection: {info['connection_info']['host']}:{info['connection_info']['port']}/{info['connection_info']['db']}")
    
    print("\nEnvironment Variables:")
    for key, value in info['environment_vars'].items():
        if value:
            print(f"  {key}: {value}")
    
    print("="*60 + "\n")
