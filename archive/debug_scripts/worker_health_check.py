#!/usr/bin/env python3
"""
Worker Health Check Utility for Christian Cleanup application.
Provides health monitoring and status checking for RQ workers.
"""

import os
import sys
import time
import argparse
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from dotenv import load_dotenv
from redis import Redis
from rq import Worker
from rq.worker import WorkerStatus

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)


class WorkerHealthMonitor:
    """
    Monitor and report on the health of RQ workers.
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv('RQ_REDIS_URL', 'redis://localhost:6379/0')
        self.connection = Redis.from_url(self.redis_url)
        
    def get_all_workers(self) -> List[Worker]:
        """Get all registered workers."""
        try:
            return Worker.all(connection=self.connection)
        except Exception as e:
            print(f"Error getting workers: {e}")
            return []
    
    def get_worker_health(self, worker: Worker) -> Dict:
        """Get detailed health information for a worker."""
        try:
            # Basic worker information
            health_info = {
                'worker_id': worker.name,
                'state': worker.get_state(),
                'current_job': None,
                'last_heartbeat': None,
                'birth_date': None,
                'death_date': None,
                'queues': [q.name for q in worker.queues],
                'is_alive': False,
                'uptime': None,
                'jobs_processed': 0,
                'failed_jobs': 0
            }
            
            # Check if worker is alive
            health_info['is_alive'] = worker.get_state() in [WorkerStatus.BUSY, WorkerStatus.IDLE]
            
            # Get current job if any
            current_job = worker.get_current_job()
            if current_job:
                health_info['current_job'] = {
                    'id': current_job.id,
                    'func_name': current_job.func_name,
                    'created_at': current_job.created_at.isoformat() if current_job.created_at else None,
                    'started_at': current_job.started_at.isoformat() if current_job.started_at else None,
                    'status': current_job.get_status()
                }
            
            # Get worker timestamps
            if hasattr(worker, 'last_heartbeat') and worker.last_heartbeat:
                health_info['last_heartbeat'] = worker.last_heartbeat.isoformat()
            
            if hasattr(worker, 'birth_date') and worker.birth_date:
                health_info['birth_date'] = worker.birth_date.isoformat()
                # Calculate uptime
                uptime = datetime.now() - worker.birth_date
                health_info['uptime'] = str(uptime)
            
            if hasattr(worker, 'death_date') and worker.death_date:
                health_info['death_date'] = worker.death_date.isoformat()
            
            # Get job statistics
            try:
                health_info['jobs_processed'] = worker.successful_job_count
                health_info['failed_jobs'] = worker.failed_job_count
            except AttributeError:
                # Fallback for older RQ versions
                pass
            
            return health_info
            
        except Exception as e:
            return {
                'worker_id': getattr(worker, 'name', 'unknown'),
                'error': str(e),
                'is_alive': False
            }
    
    def check_worker_health(self, worker_id: str = None) -> Dict:
        """Check health of specific worker or all workers."""
        workers = self.get_all_workers()
        
        if worker_id:
            # Check specific worker
            target_worker = None
            for worker in workers:
                if worker.name == worker_id:
                    target_worker = worker
                    break
            
            if not target_worker:
                return {'error': f'Worker {worker_id} not found'}
            
            return self.get_worker_health(target_worker)
        else:
            # Check all workers
            health_report = {
                'timestamp': datetime.now().isoformat(),
                'total_workers': len(workers),
                'alive_workers': 0,
                'dead_workers': 0,
                'workers': []
            }
            
            for worker in workers:
                worker_health = self.get_worker_health(worker)
                health_report['workers'].append(worker_health)
                
                if worker_health.get('is_alive', False):
                    health_report['alive_workers'] += 1
                else:
                    health_report['dead_workers'] += 1
            
            return health_report
    
    def check_stuck_jobs(self, threshold_minutes: int = 30) -> List[Dict]:
        """Check for jobs that have been running longer than the threshold."""
        stuck_jobs = []
        workers = self.get_all_workers()
        threshold = timedelta(minutes=threshold_minutes)
        
        for worker in workers:
            try:
                current_job = worker.get_current_job()
                if current_job and current_job.started_at:
                    job_duration = datetime.now() - current_job.started_at
                    if job_duration > threshold:
                        stuck_jobs.append({
                            'worker_id': worker.name,
                            'job_id': current_job.id,
                            'func_name': current_job.func_name,
                            'started_at': current_job.started_at.isoformat(),
                            'duration': str(job_duration),
                            'status': current_job.get_status()
                        })
            except Exception as e:
                print(f"Error checking job for worker {worker.name}: {e}")
        
        return stuck_jobs
    
    def cleanup_dead_workers(self) -> int:
        """Remove dead workers from Redis. Returns count of cleaned workers."""
        workers = self.get_all_workers()
        cleaned_count = 0
        
        for worker in workers:
            try:
                if worker.get_state() == WorkerStatus.DEAD:
                    worker.cleanup()
                    cleaned_count += 1
                    print(f"Cleaned up dead worker: {worker.name}")
            except Exception as e:
                print(f"Error cleaning worker {worker.name}: {e}")
        
        return cleaned_count
    
    def get_queue_status(self) -> Dict:
        """Get status of all queues."""
        from rq import Queue
        
        queue_names = ['high', 'default', 'low']  # Default queues
        queue_status = {}
        
        for queue_name in queue_names:
            try:
                queue = Queue(queue_name, connection=self.connection)
                queue_status[queue_name] = {
                    'length': len(queue),
                    'failed_count': queue.failed_job_registry.count,
                    'deferred_count': queue.deferred_job_registry.count,
                    'scheduled_count': queue.scheduled_job_registry.count
                }
            except Exception as e:
                queue_status[queue_name] = {'error': str(e)}
        
        return queue_status


def main():
    """Main entry point for the health check utility."""
    parser = argparse.ArgumentParser(description='RQ Worker Health Check Utility')
    parser.add_argument('--worker-id', type=str, help='Check specific worker by ID')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--stuck-threshold', type=int, default=30, 
                       help='Threshold in minutes for stuck job detection (default: 30)')
    parser.add_argument('--cleanup-dead', action='store_true', 
                       help='Clean up dead workers from Redis')
    parser.add_argument('--queue-status', action='store_true', 
                       help='Show queue status information')
    parser.add_argument('--watch', type=int, metavar='SECONDS',
                       help='Watch mode: refresh every N seconds')
    
    args = parser.parse_args()
    
    monitor = WorkerHealthMonitor()
    
    def run_health_check():
        """Run a single health check iteration."""
        if args.cleanup_dead:
            cleaned = monitor.cleanup_dead_workers()
            print(f"Cleaned up {cleaned} dead workers")
            return
        
        if args.queue_status:
            queue_status = monitor.get_queue_status()
            if args.json:
                print(json.dumps(queue_status, indent=2))
            else:
                print("Queue Status:")
                for queue_name, status in queue_status.items():
                    if 'error' in status:
                        print(f"  {queue_name}: ERROR - {status['error']}")
                    else:
                        print(f"  {queue_name}: {status['length']} jobs, "
                              f"{status['failed_count']} failed, "
                              f"{status['deferred_count']} deferred, "
                              f"{status['scheduled_count']} scheduled")
            return
        
        # Main health check
        health_report = monitor.check_worker_health(args.worker_id)
        
        if args.json:
            print(json.dumps(health_report, indent=2))
        else:
            if args.worker_id:
                # Single worker report
                if 'error' in health_report:
                    print(f"Error: {health_report['error']}")
                else:
                    print(f"Worker: {health_report['worker_id']}")
                    print(f"  State: {health_report['state']}")
                    print(f"  Alive: {health_report['is_alive']}")
                    print(f"  Uptime: {health_report.get('uptime', 'N/A')}")
                    print(f"  Jobs Processed: {health_report['jobs_processed']}")
                    print(f"  Failed Jobs: {health_report['failed_jobs']}")
                    if health_report['current_job']:
                        job = health_report['current_job']
                        print(f"  Current Job: {job['id']} ({job['func_name']})")
            else:
                # All workers report
                print(f"Worker Health Report - {health_report['timestamp']}")
                print(f"Total Workers: {health_report['total_workers']}")
                print(f"Alive: {health_report['alive_workers']}, Dead: {health_report['dead_workers']}")
                print()
                
                for worker in health_report['workers']:
                    status = "🟢" if worker.get('is_alive', False) else "🔴"
                    print(f"{status} {worker['worker_id']} - {worker.get('state', 'unknown')}")
                    if worker.get('current_job'):
                        job = worker['current_job']
                        print(f"    Current Job: {job['id']} ({job['func_name']})")
        
        # Check for stuck jobs
        stuck_jobs = monitor.check_stuck_jobs(args.stuck_threshold)
        if stuck_jobs:
            print(f"\n⚠️  Found {len(stuck_jobs)} stuck jobs:")
            for job in stuck_jobs:
                print(f"  Worker: {job['worker_id']}, Job: {job['job_id']}, "
                      f"Duration: {job['duration']}")
    
    # Run health check
    if args.watch:
        try:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')  # Clear screen
                run_health_check()
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nWatch mode stopped.")
    else:
        run_health_check()


if __name__ == '__main__':
    main() 