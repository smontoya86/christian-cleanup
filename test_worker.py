from app import create_app
from app.extensions import rq
from app.tasks.test_tasks import test_job
from rq import Worker, Queue
from redis import Redis
import time

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        try:
            # Get the Redis connection from the queue
            queue = rq.get_queue()
            redis_conn = queue.connection
            
            # Enqueue the job
            job = queue.enqueue(test_job)
            job_id = job.get_id()
            print(f"Added test job with ID: {job_id}")
            
            # Wait a bit for the job to be processed
            print("Waiting for job to complete...")
            time.sleep(5)  # Give it time to process
            
            # Get job status using the job ID
            job = queue.fetch_job(job_id)
            
            if job is None:
                print("Job not found!")
            else:
                print(f"Job status: {job.get_status()}")
                print(f"Job result: {job.result}")
            
            # Print queue info
            print(f"\n=== Queue Information ===")
            print(f"Jobs in queue: {len(queue)}")
            
            # Get worker information
            workers = Worker.all(connection=redis_conn)
            print(f"\n=== Worker Information ===")
            if workers:
                for worker in workers:
                    print(f"Worker: {worker.name}")
                    print(f"  State: {worker.get_state()}")
                    print(f"  Current Job: {worker.get_current_job_id()}")
                    print(f"  Queues: {', '.join(worker.queue_names())}")
            else:
                print("No active workers found.")
            
            print("\nTest completed successfully!")
            
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
