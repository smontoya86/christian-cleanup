#!/usr/bin/env python3
"""
Check RQ Queue Status
"""

import redis
from rq import Queue
import json

def main():
    # Connect to Redis
    r = redis.Redis.from_url('redis://localhost:6379/0')
    
    # Check queues
    high_q = Queue('high', connection=r)
    default_q = Queue('default', connection=r)
    low_q = Queue('low', connection=r)
    
    print(f"Queue Status:")
    print(f"  High priority: {len(high_q)} jobs")
    print(f"  Default: {len(default_q)} jobs")  
    print(f"  Low priority: {len(low_q)} jobs")
    
    print(f"\nRecent jobs in default queue:")
    for job in default_q.jobs[:10]:
        try:
            status = job.get_status()
            created_at = job.created_at.strftime('%Y-%m-%d %H:%M:%S') if job.created_at else 'Unknown'
            print(f"  Job {job.id}:")
            print(f"    Function: {getattr(job, 'func_name', 'Unknown')}")
            print(f"    Status: {status}")
            print(f"    Created: {created_at}")
            if hasattr(job, 'args') and job.args:
                print(f"    Args: {job.args}")
            print()
        except Exception as e:
            print(f"  Job {job.id}: Error reading job - {e}")

if __name__ == "__main__":
    main() 