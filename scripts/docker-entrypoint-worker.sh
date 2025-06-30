#!/bin/bash
set -e

# Set the Redis URL for Docker
export RQ_REDIS_URL=redis://redis:6379/0
export REDIS_URL=redis://redis:6379/0

# Force comprehensive analysis
export USE_LIGHTWEIGHT_ANALYZER=false

echo "Starting Priority Queue Worker with Redis URL: $REDIS_URL"
echo "Comprehensive analysis mode: enabled"

# Execute the custom priority queue worker
exec python -c "
import os
import sys
import signal
from pathlib import Path

# Add the app directory to Python path
app_dir = Path('/app')
sys.path.insert(0, str(app_dir))

# Import Flask app and worker
from app import create_app
from app.services.priority_queue_worker import start_worker

def signal_handler(signum, frame):
    print('\\nReceived signal, shutting down worker...')
    from app.services.priority_queue_worker import shutdown_worker
    shutdown_worker()
    sys.exit(0)

# Set up signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Create Flask app and start worker
app = create_app()
print('Starting priority queue worker...')
with app.app_context():
    worker = start_worker(app)
    
print(f'Worker created: {worker}')
print(f'Worker running: {worker.is_running if worker else False}')

# Keep the worker running
try:
    import time
    # Give worker time to start
    time.sleep(1)
    
    # Keep running until interrupted
    while True:
        time.sleep(1)
        # Check if worker is still alive
        if worker and (not worker.is_running or not worker.worker_thread or not worker.worker_thread.is_alive()):
            print('Worker thread died, restarting...')
            # Properly stop the old worker first
            worker.stop()
            time.sleep(0.5)  # Give it time to stop
            # Start a new worker
            worker = start_worker(app)
            time.sleep(1)
except KeyboardInterrupt:
    print('\\nShutting down worker...')
    if worker:
        worker.stop()
"
