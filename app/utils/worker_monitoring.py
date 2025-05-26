"""
Worker monitoring utilities for enhanced RQ background processing.
"""
import time
import psutil
import logging
from rq import Worker
from flask import current_app

logger = logging.getLogger(__name__)


class MonitoredWorker(Worker):
    """Worker with health monitoring capabilities."""
    
    def __init__(self, *args, **kwargs):
        self.last_heartbeat = time.time()
        self.health_check_interval = kwargs.pop('health_check_interval', 60)
        super().__init__(*args, **kwargs)
    
    def perform_job(self, job, queue):
        """Perform job with metrics tracking."""
        # Record start time for metrics
        start_time = time.time()
        
        # Perform the job
        result = super().perform_job(job, queue)
        
        # Record metrics
        if job and job.ended_at:
            duration = job.ended_at - job.started_at
            logger.info(f"Job {job.id} completed in {duration:.2f}s "
                       f"(queue: {queue.name}, status: {job.get_status()})")
        
        return result
    
    def register_birth(self):
        """Register worker birth with additional metadata."""
        super().register_birth()
        
        # Record worker metadata
        try:
            process = psutil.Process()
            self.connection.hset(
                f"worker:{self.name}:info",
                mapping={
                    'pid': process.pid,
                    'host': self.hostname,
                    'queues': ','.join(q.name for q in self.queues),
                    'start_time': time.time(),
                    'memory_percent': process.memory_percent(),
                    'cpu_percent': process.cpu_percent()
                }
            )
            logger.info(f"Worker {self.name} registered on queues: {[q.name for q in self.queues]}")
        except Exception as e:
            logger.warning(f"Failed to record worker metadata: {e}")
    
    def heartbeat(self):
        """Send heartbeat and health metrics."""
        super().heartbeat()
        
        now = time.time()
        if now - self.last_heartbeat >= self.health_check_interval:
            try:
                process = psutil.Process()
                self.connection.hset(
                    f"worker:{self.name}:info",
                    mapping={
                        'last_heartbeat': now,
                        'memory_percent': process.memory_percent(),
                        'cpu_percent': process.cpu_percent(),
                        'num_jobs_processed': self.successful_job_count
                    }
                )
                self.last_heartbeat = now
            except Exception as e:
                logger.warning(f"Failed to send heartbeat: {e}")


def get_worker_stats(redis_conn):
    """Get statistics for all workers."""
    workers = Worker.all(connection=redis_conn)
    
    worker_data = []
    for worker in workers:
        # Get worker info
        try:
            info = redis_conn.hgetall(f"worker:{worker.name}:info")
            
            # Convert to proper types
            if info:
                info = {k.decode() if isinstance(k, bytes) else k: 
                       v.decode() if isinstance(v, bytes) else v 
                       for k, v in info.items()}
                
                # Convert numeric fields
                for field in ['memory_percent', 'cpu_percent', 'start_time', 'last_heartbeat']:
                    if field in info:
                        try:
                            info[field] = float(info[field])
                        except (ValueError, TypeError):
                            info[field] = 0.0
                
                # Calculate uptime
                if 'start_time' in info and info['start_time']:
                    info['uptime'] = time.time() - info['start_time']
        except Exception as e:
            logger.warning(f"Failed to get worker info for {worker.name}: {e}")
            info = {}
        
        # Get current job if any
        current_job = None
        try:
            job = worker.get_current_job()
            if job:
                current_job = {
                    'id': job.id,
                    'description': job.description,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'enqueued_at': job.enqueued_at.isoformat() if job.enqueued_at else None,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'queue': job.origin,
                }
        except Exception as e:
            logger.warning(f"Failed to get current job for {worker.name}: {e}")
        
        worker_data.append({
            'name': worker.name,
            'queues': [q.name for q in worker.queues],
            'state': worker.state,
            'info': info,
            'current_job': current_job
        })
    
    return worker_data


def get_queue_stats(redis_conn, queue_names):
    """Get statistics for specified queues."""
    from rq import Queue
    
    queue_data = []
    for queue_name in queue_names:
        try:
            queue = Queue(queue_name, connection=redis_conn)
            queue_data.append({
                'name': queue.name,
                'count': queue.count,
                'failed': queue.failed_job_registry.count,
                'workers': len(queue.worker_ids),
            })
        except Exception as e:
            logger.warning(f"Failed to get stats for queue {queue_name}: {e}")
            queue_data.append({
                'name': queue_name,
                'count': 0,
                'failed': 0,
                'workers': 0,
                'error': str(e)
            })
    
    return queue_data 