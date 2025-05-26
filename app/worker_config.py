"""
Enhanced worker configuration for RQ background processing.
"""
import os
import redis
from rq import Queue

# Configure Redis connection
redis_url = os.getenv('RQ_REDIS_URL', 'redis://localhost:6379/0')
redis_conn = redis.from_url(redis_url)

# Define priority queue names
HIGH_QUEUE = 'high'
DEFAULT_QUEUE = 'default'
LOW_QUEUE = 'low'

# Queue definitions with TTL and result expiration settings
def get_queues():
    """Get all priority queues in order of priority."""
    high_queue = Queue(HIGH_QUEUE, connection=redis_conn, default_timeout=300)  # 5 minutes
    default_queue = Queue(DEFAULT_QUEUE, connection=redis_conn, default_timeout=600)  # 10 minutes
    low_queue = Queue(LOW_QUEUE, connection=redis_conn, default_timeout=1800)  # 30 minutes
    
    return [high_queue, default_queue, low_queue]

# Create individual queue instances for direct access
def get_high_queue():
    """Get high priority queue."""
    return Queue(HIGH_QUEUE, connection=redis_conn, default_timeout=300)

def get_default_queue():
    """Get default priority queue."""
    return Queue(DEFAULT_QUEUE, connection=redis_conn, default_timeout=600)

def get_low_queue():
    """Get low priority queue."""
    return Queue(LOW_QUEUE, connection=redis_conn, default_timeout=1800)

# RQ worker configuration
WORKER_NAME = 'song_analysis_worker'
QUEUES = ['default']

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
