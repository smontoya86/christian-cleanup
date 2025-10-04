# Simple Async Implementation with RQ

**Goal**: Background playlist analysis with progress tracking  
**Approach**: Redis Queue (RQ) - Simple, battle-tested, scales naturally  
**Time to implement**: 3-4 hours

---

## Why RQ? (The Simple Choice)

### What You Get:
✅ **Background jobs** - No more timeouts  
✅ **Progress tracking** - Built-in job status  
✅ **Failure handling** - Automatic retries  
✅ **Scalability** - Add workers when needed  
✅ **You already have Redis** - No new infrastructure  

### What You DON'T Get (Complexity You Don't Need):
❌ Complex priority queues  
❌ Smart scheduling algorithms  
❌ Custom progress tracking code  
❌ Thread management headaches  

---

## Implementation (4 Simple Steps)

### Step 1: Add RQ Dependency (1 minute)

```bash
# requirements.txt
rq>=1.15.0
```

That's it. One line.

---

### Step 2: Create Queue Configuration (5 minutes)

```python
# app/queue.py (NEW FILE - 20 lines)
"""Simple Redis Queue configuration for background jobs"""
import os
from redis import Redis
from rq import Queue

# Use existing Redis connection
redis_conn = Redis.from_url(
    os.environ.get('REDIS_URL', 'redis://redis:6379')
)

# Create queue for analysis jobs
analysis_queue = Queue('analysis', connection=redis_conn)

def enqueue_playlist_analysis(playlist_id, user_id):
    """Queue a playlist for background analysis"""
    job = analysis_queue.enqueue(
        'app.services.unified_analysis_service.analyze_playlist_async',
        playlist_id,
        user_id,
        job_timeout='30m',  # Max 30 minutes per playlist
        result_ttl=3600     # Keep result for 1 hour
    )
    return job.id
```

---

### Step 3: Make Analysis Async (10 minutes)

```python
# app/services/unified_analysis_service.py

# Add this new method (same logic as sync, just wrapped)
def analyze_playlist_async(playlist_id, user_id):
    """
    Background job to analyze a playlist.
    
    This is the same logic as the sync version, just called from RQ worker.
    No special code needed - RQ handles progress tracking automatically.
    """
    from app import create_app
    
    # Create app context for worker
    app = create_app()
    with app.app_context():
        # Your existing analysis logic
        playlist = Playlist.query.get_or_404(playlist_id)
        
        unanalyzed_songs = db.session.query(Song).join(
            PlaylistSong
        ).outerjoin(
            AnalysisResult, Song.id == AnalysisResult.song_id
        ).filter(
            PlaylistSong.playlist_id == playlist_id,
            db.or_(
                AnalysisResult.id.is_(None),
                AnalysisResult.status != 'completed'
            )
        ).all()
        
        # Analyze each song
        svc = UnifiedAnalysisService()
        results = {
            'total': len(unanalyzed_songs),
            'analyzed': 0,
            'failed': 0
        }
        
        for song in unanalyzed_songs:
            try:
                svc.analyze_song(song.id)
                results['analyzed'] += 1
            except Exception as e:
                current_app.logger.error(f"Failed to analyze song {song.id}: {e}")
                results['failed'] += 1
        
        return results  # RQ automatically stores this
```

---

### Step 4: Update API Endpoint (15 minutes)

```python
# app/routes/api.py

from app.queue import enqueue_playlist_analysis, analysis_queue
from rq.job import Job

@bp.route("/analyze_playlist/<int:playlist_id>", methods=["POST"])
@login_required
def analyze_playlist(playlist_id):
    """Queue playlist analysis in background"""
    if not current_user.is_admin:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    try:
        # Verify playlist exists and belongs to user
        playlist = Playlist.query.get_or_404(playlist_id)
        if playlist.owner_id != current_user.id:
            return jsonify({"success": False, "error": "Playlist not found"}), 404
        
        # Queue the analysis job
        job_id = enqueue_playlist_analysis(playlist_id, current_user.id)
        
        return jsonify({
            "success": True,
            "message": "Analysis started in background",
            "job_id": job_id,
            "playlist_id": playlist_id,
            "status": "queued"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route("/analysis/status/<job_id>", methods=["GET"])
@login_required
def get_analysis_status(job_id):
    """Get status of background analysis job"""
    try:
        job = Job.fetch(job_id, connection=analysis_queue.connection)
        
        response = {
            "job_id": job_id,
            "status": job.get_status(),
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        
        # Add progress info based on status
        if job.is_finished:
            response["result"] = job.result
            response["finished_at"] = job.ended_at.isoformat() if job.ended_at else None
        elif job.is_failed:
            response["error"] = str(job.exc_info) if job.exc_info else "Unknown error"
        elif job.is_queued:
            response["position"] = job.get_position()
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "error": "Job not found",
            "job_id": job_id
        }), 404
```

---

### Step 5: Add Worker to Docker (5 minutes)

```yaml
# docker-compose.yml

services:
  web:
    # ... existing config ...

  worker:
    build:
      context: .
      network: host
    command: rq worker analysis --url redis://redis:6379
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - redis
      - db
    restart: unless-stopped
    environment:
      - OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

  db:
    # ... existing config ...

  redis:
    # ... existing config ...
```

**That's it. One new service, 7 lines of config.**

---

### Step 6: Update Frontend (20 minutes)

```javascript
// In your playlist page JavaScript

async function analyzePlaylist(playlistId) {
    // Show loading state
    const button = document.getElementById('analyzePlaylistBtn');
    button.disabled = true;
    button.textContent = 'Starting...';
    
    try {
        // Start the analysis
        const response = await fetch(`/api/analyze_playlist/${playlistId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Show progress modal
            showProgressModal(data.job_id, playlistId);
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        alert(`Failed to start analysis: ${error}`);
    } finally {
        button.disabled = false;
        button.textContent = 'Analyze All Songs';
    }
}

function showProgressModal(jobId, playlistId) {
    // Create simple modal
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Analyzing Playlist</h5>
                </div>
                <div class="modal-body">
                    <div class="progress">
                        <div id="progress-bar" class="progress-bar progress-bar-striped progress-bar-animated" 
                             style="width: 0%">0%</div>
                    </div>
                    <p id="progress-text" class="mt-3 text-center">Starting analysis...</p>
                    <p id="progress-details" class="text-muted text-center small"></p>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    // Poll for progress
    pollJobProgress(jobId, playlistId, modal);
}

async function pollJobProgress(jobId, playlistId, modal) {
    const progressBar = modal.querySelector('#progress-bar');
    const progressText = modal.querySelector('#progress-text');
    const progressDetails = modal.querySelector('#progress-details');
    
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/analysis/status/${jobId}`);
            const status = await response.json();
            
            if (status.status === 'finished') {
                // Success!
                clearInterval(pollInterval);
                progressBar.style.width = '100%';
                progressBar.textContent = '100%';
                progressText.textContent = `Analyzed ${status.result.analyzed} songs!`;
                progressDetails.textContent = `Failed: ${status.result.failed}`;
                
                setTimeout(() => {
                    modal.remove();
                    location.reload();  // Refresh to show results
                }, 2000);
                
            } else if (status.status === 'failed') {
                // Error
                clearInterval(pollInterval);
                progressBar.classList.add('bg-danger');
                progressText.textContent = 'Analysis failed';
                progressDetails.textContent = status.error || 'Unknown error';
                
            } else if (status.status === 'started') {
                // In progress
                progressText.textContent = 'Analyzing songs...';
                progressDetails.textContent = 'This may take several minutes';
                
            } else if (status.status === 'queued') {
                // Waiting
                progressText.textContent = `Position in queue: ${status.position || '?'}`;
                progressDetails.textContent = 'Waiting to start...';
            }
            
        } catch (error) {
            console.error('Failed to check progress:', error);
        }
    }, 2000);  // Poll every 2 seconds
}
```

---

## Scaling Path (When You Need It)

### Current (1,000 users):
```yaml
worker:
  command: rq worker analysis --url redis://redis:6379
```
**1 worker = 75 songs/minute = Good for 1,000 users**

### Growing (5,000 users):
```yaml
worker:
  command: rq worker analysis --url redis://redis:6379
  deploy:
    replicas: 2
```
**2 workers = 150 songs/minute = Good for 5,000 users**

### Large Scale (10,000+ users):
```yaml
worker:
  command: rq worker analysis --url redis://redis:6379
  deploy:
    replicas: 5
```
**5 workers = 375 songs/minute = Good for 10,000+ users**

**That's literally the only change needed to scale.**

---

## Progress Tracking Details

RQ automatically tracks:
- **queued**: Job is waiting in queue
- **started**: Job is being processed
- **finished**: Job completed successfully
- **failed**: Job encountered an error

You can also add custom progress updates inside your job:

```python
from rq import get_current_job

def analyze_playlist_async(playlist_id, user_id):
    job = get_current_job()
    
    # ... get songs ...
    
    total = len(unanalyzed_songs)
    
    for i, song in enumerate(unanalyzed_songs):
        # Update progress
        job.meta['progress'] = {
            'current': i + 1,
            'total': total,
            'percentage': ((i + 1) / total * 100)
        }
        job.save_meta()
        
        # Analyze song
        svc.analyze_song(song.id)
```

Then in your status endpoint:
```python
@bp.route("/analysis/status/<job_id>", methods=["GET"])
def get_analysis_status(job_id):
    job = Job.fetch(job_id, connection=analysis_queue.connection)
    
    response = {
        "status": job.get_status(),
        "progress": job.meta.get('progress', {})  # Your custom progress
    }
    
    return jsonify(response)
```

---

## Testing Locally

```bash
# Terminal 1: Start services
docker-compose up

# Terminal 2: Start RQ worker (if not using docker-compose worker)
rq worker analysis --url redis://localhost:6379

# Terminal 3: Test the queue
python
>>> from app.queue import enqueue_playlist_analysis
>>> job_id = enqueue_playlist_analysis(1, 1)
>>> print(job_id)
```

---

## Monitoring (Optional, Later)

RQ has a built-in dashboard:

```bash
# requirements.txt
rq-dashboard

# Run it
rq-dashboard --redis-url redis://localhost:6379
# Visit http://localhost:9181
```

Shows:
- Active workers
- Queued jobs
- Failed jobs
- Job durations
- Success/failure rates

---

## Summary

### What You're Adding:
1. **One dependency**: `rq>=1.15.0`
2. **One new file**: `app/queue.py` (~20 lines)
3. **One new method**: `analyze_playlist_async()` (wraps existing logic)
4. **Two new endpoints**: `/analyze_playlist` (modified), `/analysis/status` (new)
5. **One docker service**: RQ worker
6. **Frontend progress**: Modal with polling (~50 lines JS)

### What You Get:
✅ No more timeouts  
✅ Progress tracking built-in  
✅ Automatic retries on failure  
✅ Natural scaling path (add workers)  
✅ Clean separation (web vs worker)  
✅ Monitoring dashboard (optional)  

### Time Investment:
- **Initial**: 3-4 hours
- **Maintenance**: ~0 (it just works)
- **Scaling**: Change one number (replicas)

---

## Alternative: If You REALLY Want Simpler

If RQ still feels like too much, here's the threading approach:

```python
# app/routes/api.py
import threading
from flask import current_app

@bp.route("/analyze_playlist/<int:playlist_id>", methods=["POST"])
@login_required
def analyze_playlist(playlist_id):
    """Start playlist analysis in background thread"""
    if not current_user.is_admin:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    # Start thread
    thread = threading.Thread(
        target=analyze_playlist_thread,
        args=(current_app._get_current_object(), playlist_id, current_user.id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Analysis started",
        "status": "processing"
    })

def analyze_playlist_thread(app, playlist_id, user_id):
    """Background thread for playlist analysis"""
    with app.app_context():
        # ... your existing sync logic ...
```

**Pros**: Simplest possible (no new dependencies)  
**Cons**: No progress tracking, no scaling, no failure recovery

---

## My Recommendation

**Use RQ.** 

It's barely more complex than threading, but gives you:
- Built-in progress tracking (essential UX requirement)
- Natural scaling path
- Better reliability

The initial setup is 3-4 hours, then you never touch it again. When you need to scale, change one number.

**Threading is simpler to implement but harder to maintain and doesn't solve progress tracking.**

