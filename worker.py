import os
from dotenv import load_dotenv
from redis import Redis
from rq import Worker # Queue import is not used by worker.py directly

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

from app import create_app

if __name__ == '__main__':
    # Create and configure the Flask app instance
    # Ensure your create_app function can accept config_name or similar
    flask_env = os.getenv('FLASK_CONFIG') or 'default'
    app = create_app(config_name=flask_env) # Pass the config name

    # It's crucial to operate within an application context if jobs or the worker setup
    # need to access app.config or Flask extensions like SQLAlchemy.
    with app.app_context():
        # Get queue names and Redis URL from the app's configuration
        # Default to ['default'] if RQ_QUEUES is not set
        listen_queues = app.config.get('RQ_QUEUES', ['default'])
        # Default to 'redis://localhost:6379/0' if RQ_REDIS_URL is not set
        redis_url = app.config.get('RQ_REDIS_URL', 'redis://localhost:6379/0')

        print(f"RQ Worker attempting to connect to Redis at: {redis_url}")
        print(f"RQ Worker will listen on queues: {', '.join(listen_queues)}")

        # Create a Redis connection instance for RQ
        conn = Redis.from_url(redis_url)

        # Create an RQ worker instance
        # Pass the list of queue names (strings) and the connection object
        worker = Worker(listen_queues, connection=conn)
        
        print(f"RQ Worker configured. Starting work...")
        try:
            # The with_scheduler argument depends on your RQ/Flask-RQ2 version and setup.
            # If using Flask-RQ2's scheduler, it might be managed differently.
            # For a basic RQ worker, with_scheduler=True might be used if you run rqscheduler separately.
            # If Flask-RQ2 manages the scheduler via its own CLI (e.g., flask rq scheduler), 
            # you might not need it here or it might be a config like app.config.get('RQ_SCHEDULER_HEARTBEAT', False).
            # For simplicity, let's assume no separate scheduler process is being started by this worker.py directly.
            worker.work() # Removed with_scheduler for now to simplify; add back if needed based on your setup
        except Exception as e:
            print(f"Error during worker execution: {e}")
            # It's good practice to log the full traceback here for debugging
            # import traceback
            # traceback.print_exc()

    # These print statements might not be reached if worker.work() blocks indefinitely
    # or if an unhandled exception occurs within the try block that causes an exit.
    # Consider logging within the worker loop or using RQ's event handlers for more robust status reporting.
    # print(f"RQ Worker process finished or was interrupted.")
