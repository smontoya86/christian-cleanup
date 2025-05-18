import os
from redis import Redis

# Get Redis URL from environment variable or use default
REDIS_URL = os.getenv('RQ_REDIS_URL', 'redis://redis:6379/0')

# Create Redis connection
redis_conn = Redis.from_url(REDIS_URL)

# RQ worker configuration
WORKER_NAME = 'song_analysis_worker'
QUEUES = ['default']

# Logging configuration
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
