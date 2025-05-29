from app import create_app
from app.extensions import rq

app = create_app()
with app.app_context():
    try:
        queue = rq.get_queue()
        print('Queue info:')
        print(f'  Jobs: {len(queue)}')
        print(f'  Failed: {len(queue.failed_job_registry)}')
        print(f'  Started: {len(queue.started_job_registry)}')
        print(f'  Deferred: {len(queue.deferred_job_registry)}')
        print(f'  Finished: {len(queue.finished_job_registry)}')
        
        print('\n--- Current Jobs ---')
        for job in queue.jobs[:10]:
            print(f'  {job.id}: {job.func_name} - {job.get_status()}')
            
        print('\n--- Failed Jobs (last 5) ---')
        for job_id in queue.failed_job_registry.get_job_ids()[:5]:
            try:
                job = queue.failed_job_registry[job_id]
                print(f'  {job_id}: {job.description if hasattr(job, "description") else "Unknown"}')
            except Exception as e:
                print(f'  {job_id}: Error accessing job - {e}')
    except Exception as e:
        print(f'Error checking queue: {e}')
        import traceback
        traceback.print_exc() 