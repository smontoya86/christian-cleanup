#!/usr/bin/env python3
"""
Production Queue Status Checker

A utility script for monitoring RQ queue status and job information.
Useful for system administrators and debugging queue issues.
"""

import redis
from rq import Queue
import json
import argparse
from datetime import datetime
import sys
import os
import logging

# Add the app directory to the path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_redis_connection(redis_url='redis://localhost:6379/0'):
    """Get Redis connection with error handling."""
    try:
        r = redis.Redis.from_url(redis_url)
        # Test the connection
        r.ping()
        return r
    except redis.ConnectionError as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Redis connection error: {e}")
        return None

def check_queue_status(redis_connection, queue_names=['high', 'default', 'low'], verbose=False):
    """Check status of specified queues."""
    if not redis_connection:
        return False
    
    queues = {}
    total_jobs = 0
    
    logger.info("📊 Queue Status Report")
    logger.info("=" * 40)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for queue_name in queue_names:
        try:
            queue = Queue(queue_name, connection=redis_connection)
            job_count = len(queue)
            queues[queue_name] = {
                'queue': queue,
                'count': job_count,
                'jobs': queue.jobs if verbose else []
            }
            total_jobs += job_count
            
            priority_indicator = "🔥" if queue_name == 'high' else "📋" if queue_name == 'default' else "📝"
            logger.info(f"{priority_indicator} {queue_name.title()} Queue: {job_count} jobs")
            
        except Exception as e:
            logger.error(f"❌ Error checking {queue_name} queue: {e}")
            queues[queue_name] = {'error': str(e), 'count': 0}
    
    logger.info(f"📈 Total Jobs: {total_jobs}")
    
    if verbose and total_jobs > 0:
        logger.info("🔍 Recent Job Details:")
        logger.info("-" * 40)
        
        for queue_name, queue_info in queues.items():
            if 'error' in queue_info:
                continue
                
            queue = queue_info['queue']
            if queue_info['count'] > 0:
                logger.info(f"{queue_name.title()} Queue Jobs:")
                
                for i, job in enumerate(queue.jobs[:5]):  # Show first 5 jobs
                    try:
                        status = job.get_status()
                        created_at = job.created_at.strftime('%Y-%m-%d %H:%M:%S') if job.created_at else 'Unknown'
                        func_name = getattr(job, 'func_name', 'Unknown')
                        
                        logger.info(f"  {i+1}. Job {job.id[:8]}...")
                        logger.info(f"     Function: {func_name}")
                        logger.info(f"     Status: {status}")
                        logger.info(f"     Created: {created_at}")
                        
                        if hasattr(job, 'args') and job.args:
                            args_str = str(job.args)[:100] + "..." if len(str(job.args)) > 100 else str(job.args)
                            logger.info(f"     Args: {args_str}")
                        
                    except Exception as e:
                        logger.error(f"  Job {job.id}: Error reading job - {e}")
    
    return True

def check_worker_health(redis_connection):
    """Check for worker heartbeats and health."""
    if not redis_connection:
        return
    
    logger.info("💓 Worker Health Check")
    logger.info("=" * 40)
    
    try:
        # Check for worker keys in Redis
        worker_keys = redis_connection.keys('rq:worker:*')
        
        if worker_keys:
            logger.info(f"🟢 Found {len(worker_keys)} worker(s)")
            for key in worker_keys[:5]:  # Show first 5 workers
                worker_id = key.decode('utf-8').split(':')[-1]
                logger.info(f"   • Worker: {worker_id}")
        else:
            logger.warning("🟡 No active workers found")
            
    except Exception as e:
        logger.error(f"❌ Error checking worker health: {e}")

def main():
    """Main function with command line argument parsing."""
    parser = argparse.ArgumentParser(description='Check RQ Queue Status')
    parser.add_argument('--redis-url', default='redis://localhost:6379/0',
                       help='Redis connection URL')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed job information')
    parser.add_argument('--workers', '-w', action='store_true',
                       help='Check worker health')
    parser.add_argument('--queues', nargs='+', default=['high', 'default', 'low'],
                       help='Queues to check')
    
    args = parser.parse_args()
    
    # Get Redis connection
    redis_conn = get_redis_connection(args.redis_url)
    if not redis_conn:
        return 1
    
    # Check queue status
    success = check_queue_status(redis_conn, args.queues, args.verbose)
    
    # Check worker health if requested
    if args.workers:
        check_worker_health(redis_conn)
    
    if success:
        logger.info("✅ Queue status check completed successfully")
        return 0
    else:
        logger.error("❌ Queue status check failed")
        return 1

if __name__ == "__main__":
    exit(main()) 