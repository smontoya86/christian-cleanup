#!/bin/bash
set -e

# Set the Redis URL for Docker
export RQ_REDIS_URL=redis://redis:6379/0
export REDIS_URL=redis://redis:6379/0

# Force comprehensive analysis
export USE_LIGHTWEIGHT_ANALYZER=false

echo "Starting Simplified Priority Queue Worker with Redis URL: $REDIS_URL"
echo "Using cached AI models for fast analysis"

# Execute the simplified worker
exec python -c "
import os
import sys
import signal
import time
from pathlib import Path

# Add the app directory to Python path
app_dir = Path('/app')
sys.path.insert(0, str(app_dir))

# Import Flask app and services
from app import create_app
from app.services.priority_analysis_queue import PriorityAnalysisQueue
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.services.analyzer_cache import initialize_analyzer, is_analyzer_ready

def signal_handler(signum, frame):
    print('\\nReceived shutdown signal, exiting gracefully...')
    sys.exit(0)

# Set up signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Create Flask app
app = create_app()
print('Starting simplified worker with cached models...')

with app.app_context():
    # Pre-load shared analyzer
    print('🚀 Pre-loading shared analyzer...')
    if not is_analyzer_ready():
        initialize_analyzer()
    
    if is_analyzer_ready():
        print('✅ Shared analyzer ready for fast analysis!')
    else:
        print('⚠️ Analyzer not ready, will initialize on first job')
    
    # Initialize services
    queue = PriorityAnalysisQueue()
    analysis_service = UnifiedAnalysisService()
    
    # Check for stuck active jobs and reset them to pending
    print('🔍 Checking for stuck active jobs...')
    status = queue.get_queue_status()
    active_job = status.get('active_job')
    
    if active_job:
        print(f'📋 Found stuck active job: {active_job[\"job_id\"]} - resetting to pending')
        # Reset the job back to the queue
        import json
        from app.services.priority_analysis_queue import AnalysisJob, JobStatus
        
        # Recreate the job object and re-queue it
        job_data = {
            'job_id': active_job['job_id'],
            'job_type': active_job['job_type'], 
            'priority': active_job['priority'],
            'user_id': active_job['user_id'],
            'target_id': active_job['target_id'],
            'created_at': active_job['created_at'],
            'status': 'pending',  # Reset to pending
            'metadata': active_job['metadata']
        }
        
        # Clear the active job and re-queue
        queue.redis.delete(queue.active_key)
        queue.redis.hset(queue.jobs_key, active_job['job_id'], json.dumps(job_data))
        queue.redis.zadd(queue.queue_key, {active_job['job_id']: active_job['priority']})
        
        print('✅ Stuck job reset to pending and re-queued')
    else:
        print('✅ No stuck jobs found')
    
    print('🏃 Worker running - processing jobs from queue...')
    
    # Simple job processing loop
    processed_count = 0
    while True:
        try:
            # Get next job from queue
            job = queue.dequeue()
            
            if job:
                print(f'📋 Processing job {job.job_id} (type: {job.job_type.value})')
                
                try:
                    # Process song analysis job directly
                    if job.job_type.value == 'song_analysis':
                        from app.models.models import Song
                        song = Song.query.get(job.target_id)
                        if song:
                            print(f'🎵 Analyzing: {song.title} by {song.artist}')
                            
                            # Direct analysis using cached models
                            result = analysis_service.analyze_song(job.target_id, user_id=job.user_id)
                            
                            print(f'✅ Analysis complete: Score={result.score}, Concern={result.concern_level}')
                            processed_count += 1
                            
                            # Mark job as completed
                            queue.complete_job(job.job_id, success=True)
                        else:
                            print(f'❌ Song {job.target_id} not found')
                            queue.complete_job(job.job_id, success=False, error_message='Song not found')
                    else:
                        print(f'⚠️ Unsupported job type: {job.job_type.value}')
                        queue.complete_job(job.job_id, success=False, error_message='Unsupported job type')
                
                except Exception as e:
                    print(f'❌ Job {job.job_id} failed: {e}')
                    queue.complete_job(job.job_id, success=False, error_message=str(e))
                
                print(f'📊 Jobs processed: {processed_count}')
            else:
                # No jobs, wait a bit
                time.sleep(2)
                
        except KeyboardInterrupt:
            print('\\nShutting down worker...')
            break
        except Exception as e:
            print(f'❌ Worker error: {e}')
            time.sleep(5)  # Wait before retrying
    
    print(f'🏁 Worker shutdown. Total jobs processed: {processed_count}')
"
