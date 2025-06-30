# Smart Polling Integration Guide

This guide explains how to implement real-time progress updates for analysis jobs using smart polling instead of complex WebSocket infrastructure.

## Overview

The smart polling system provides real-time progress updates by efficiently polling our existing API endpoints. It features:

- **Adaptive polling intervals** (1-5 seconds based on progress)
- **Automatic error handling** with exponential backoff
- **Progress tracking** with ETA calculations
- **Multiple job support** for concurrent operations
- **Clean resource management** with automatic cleanup

## Quick Start

### 1. Include the Smart Polling Library

Add the progress polling script to your HTML templates:

```html
<!-- In your base template or specific pages -->
<script src="{{ url_for('static', filename='js/progress-polling.js') }}"></script>
```

### 2. Basic Song Analysis with Progress

```javascript
// Get UI elements
const progressBar = document.getElementById('progress-bar');
const statusText = document.getElementById('status-text');
const analyzeButton = document.getElementById('analyze-btn');

analyzeButton.addEventListener('click', function() {
    const songId = this.dataset.songId;
    
    // Start analysis and show progress
    analyzeSongWithProgress(songId, progressBar, statusText);
});
```

### 3. Playlist Analysis with Detailed Progress

```javascript
// For playlist analysis with per-song progress
const playlistContainer = document.getElementById('playlist-progress');
const analyzePlaylistBtn = document.getElementById('analyze-playlist-btn');

analyzePlaylistBtn.addEventListener('click', function() {
    const playlistId = this.dataset.playlistId;
    
    // Start playlist analysis with detailed progress
    analyzePlaylistWithProgress(playlistId, playlistContainer);
});
```

## API Endpoints Used

The smart polling system uses these existing API endpoints:

| Endpoint | Purpose | Polling Frequency |
|----------|---------|------------------|
| `/api/progress/<job_id>` | Get detailed job progress | 1-5 seconds |
| `/api/jobs/<job_id>/status` | Get job status and metadata | 1-5 seconds |
| `/api/queue/status` | Get queue health and statistics | 3 seconds |
| `/api/worker/health` | Get worker status | 3 seconds |

## Adaptive Polling Strategy

The polling system automatically adjusts intervals based on job progress:

```javascript
// Fast polling (1 second) for:
- First 10 seconds of any job
- Jobs with < 10% progress (rapid initial changes)

// Medium polling (2-3 seconds) for:
- Jobs with 10-90% progress (steady progress)

// Slower polling (5 seconds) for:
- Jobs with > 90% progress (final processing)
- Background/admin jobs
- Error recovery situations
```

## Integration Examples

### Example 1: Simple Progress Bar

```html
<div class="analysis-section">
    <button id="analyze-song" data-song-id="123">Analyze Song</button>
    <div class="progress-container" style="display: none;">
        <div class="progress-bar">
            <div class="progress-fill" id="progress-bar"></div>
        </div>
        <div class="progress-text" id="status-text">Ready to analyze...</div>
    </div>
</div>

<script>
document.getElementById('analyze-song').addEventListener('click', function() {
    const songId = this.dataset.songId;
    const container = document.querySelector('.progress-container');
    const progressBar = document.getElementById('progress-bar');
    const statusText = document.getElementById('status-text');
    
    // Show progress container
    container.style.display = 'block';
    this.disabled = true;
    
    // Start analysis with progress tracking
    analyzeSongWithProgress(songId, progressBar, statusText);
});
</script>
```

### Example 2: Advanced Playlist Progress

```html
<div class="playlist-analysis">
    <button id="analyze-playlist" data-playlist-id="456">Analyze Playlist</button>
    <div id="playlist-progress-container"></div>
</div>

<script>
document.getElementById('analyze-playlist').addEventListener('click', function() {
    const playlistId = this.dataset.playlistId;
    const container = document.getElementById('playlist-progress-container');
    
    this.disabled = true;
    analyzePlaylistWithProgress(playlistId, container);
});
</script>
```

### Example 3: Admin Dashboard with Queue Status

```html
<div class="admin-section">
    <div id="queue-dashboard"></div>
    <button id="background-analysis" data-user-id="789">Start Background Analysis</button>
</div>

<script>
// Initialize queue status dashboard
const dashboardContainer = document.getElementById('queue-dashboard');
createQueueStatusDashboard(dashboardContainer);

// Handle background analysis
document.getElementById('background-analysis').addEventListener('click', function() {
    const userId = this.dataset.userId;
    startBackgroundAnalysisWithNotification(userId);
});
</script>
```

## Error Handling

The smart polling system includes comprehensive error handling:

```javascript
// Automatic retry with exponential backoff
pollJobProgress(jobId, {
    maxErrorRetries: 3,           // Max retry attempts
    errorBackoffMultiplier: 2,    // 2x interval on each error
    
    onError: (error, retryCount) => {
        console.warn(`Polling error (attempt ${retryCount}):`, error.message);
        
        if (retryCount === 1) {
            showUserMessage('Connection issue, retrying...', 'warning');
        } else if (retryCount >= 3) {
            showUserMessage('Unable to track progress. Please refresh the page.', 'error');
        }
    }
});
```

## Performance Considerations

### Polling Efficiency

- **Adaptive intervals**: Reduces server load by polling less frequently when appropriate
- **Automatic cleanup**: Stops polling when jobs complete or fail
- **Error backoff**: Prevents overwhelming the server during network issues

### Memory Management

```javascript
// Always clean up polling when leaving pages
window.addEventListener('beforeunload', function() {
    // Stop all active polling to prevent memory leaks
    if (window.globalPoller) {
        window.globalPoller.stopAllPolling();
    }
});

// Or stop specific job polling when no longer needed
function cleanupJobPolling(jobId) {
    if (window.globalPoller) {
        window.globalPoller.stopPolling(jobId);
    }
}
```

### Server Load

With default settings, each active job polls every 1-5 seconds. For high-traffic scenarios:

```javascript
// Adjust polling for production environments
const productionPoller = new ProgressPoller({
    initialInterval: 2000,    // Start with 2 seconds
    maxInterval: 10000,       // Max 10 seconds
    maxErrorRetries: 5        // More retry attempts
});
```

## Styling and User Experience

### Progress Bar CSS

```css
.progress-container {
    margin: 15px 0;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 8px;
    background: #f9f9f9;
}

.progress-bar {
    width: 100%;
    height: 20px;
    background: #e9ecef;
    border-radius: 10px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #007bff, #0056b3);
    transition: width 0.3s ease;
    border-radius: 10px;
}

.progress-text {
    margin-top: 8px;
    font-size: 14px;
    color: #666;
    text-align: center;
}

/* Error state */
.progress-fill.error {
    background: linear-gradient(90deg, #dc3545, #c82333);
}

/* Success state */
.progress-fill.success {
    background: linear-gradient(90deg, #28a745, #1e7e34);
}
```

### User Feedback

```javascript
// Enhanced progress updates with user-friendly messages
function updateProgressUI(progress) {
    const percent = Math.round(progress.progress * 100);
    const progressBar = document.getElementById('progress-bar');
    const statusText = document.getElementById('status-text');
    
    // Update progress bar
    progressBar.style.width = `${percent}%`;
    
    // User-friendly status messages
    const stepMessages = {
        'starting': 'Getting ready to analyze...',
        'fetching_lyrics': 'Finding song lyrics...',
        'analyzing': 'Checking content for concerns...',
        'complete': 'Analysis finished!'
    };
    
    let message = stepMessages[progress.current_step] || 'Processing...';
    
    // Add ETA for longer jobs
    if (progress.eta_seconds && progress.eta_seconds > 10) {
        const minutes = Math.ceil(progress.eta_seconds / 60);
        message += ` (about ${minutes} minute${minutes > 1 ? 's' : ''} remaining)`;
    }
    
    statusText.textContent = message;
}
```

## Testing and Debugging

### Debug Mode

Enable debug logging to troubleshoot polling issues:

```javascript
// Enable debug mode for development
const debugPoller = new ProgressPoller({
    debug: true  // Will log detailed polling information
});

// Or check polling status
console.log('Active polls:', debugPoller.getActivePolls());
```

### Manual Testing

Test the polling system with curl commands:

```bash
# Start a job
curl -X POST http://localhost:5001/api/songs/123/analyze

# Check progress (replace JOB_ID with actual job ID)
curl http://localhost:5001/api/progress/JOB_ID

# Check queue status
curl http://localhost:5001/api/queue/status

# Check worker health
curl http://localhost:5001/api/worker/health
```

## Migration from Synchronous Analysis

If you're updating existing synchronous analysis code:

### Before (Synchronous)
```javascript
// Old synchronous approach
fetch(`/api/songs/${songId}/analyze`, { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Analysis complete, reload page
            window.location.reload();
        }
    });
```

### After (Asynchronous with Progress)
```javascript
// New asynchronous approach with progress
fetch(`/api/songs/${songId}/analyze`, { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.job_id) {
            // Start polling for progress
            pollJobProgress(data.job_id, {
                onProgress: updateProgressUI,
                onComplete: () => {
                    showSuccessMessage('Analysis complete!');
                    setTimeout(() => window.location.reload(), 1000);
                }
            });
        }
    });
```

## Production Deployment

### Environment Configuration

For production environments, consider these settings:

```javascript
// Production-optimized polling configuration
const productionConfig = {
    initialInterval: 3000,      // Start with 3 seconds
    maxInterval: 15000,         // Max 15 seconds
    maxErrorRetries: 5,         // More retries for network issues
    errorBackoffMultiplier: 1.5 // Gentler backoff
};

const poller = new ProgressPoller(productionConfig);
```

### Load Balancing Considerations

When using load balancers, ensure session affinity or use Redis-based progress storage:

```javascript
// The progress tracking system uses Redis for persistence,
// so it works across multiple app instances automatically
```

## Troubleshooting

### Common Issues

1. **Polling never stops**: Check that job completion detection is working
2. **High server load**: Increase polling intervals for production
3. **Memory leaks**: Ensure `stopPolling()` is called when leaving pages
4. **Stale progress data**: Use the cleanup endpoint: `/api/progress/cleanup`

### Performance Monitoring

Monitor polling performance:

```javascript
// Track polling performance
const performanceMonitor = {
    startTime: Date.now(),
    pollCount: 0,
    
    onProgress: function(progress) {
        this.pollCount++;
        const duration = Date.now() - this.startTime;
        const avgInterval = duration / this.pollCount;
        
        console.log(`Poll #${this.pollCount}, avg interval: ${avgInterval}ms`);
    }
};
```

## Conclusion

Smart polling provides a simple, reliable way to implement real-time progress updates without the complexity of WebSocket infrastructure. It leverages existing API endpoints and provides a smooth user experience with minimal server overhead.

The system is designed to be:
- **Simple to implement** - Just include the script and call functions
- **Efficient** - Adaptive polling reduces unnecessary requests
- **Robust** - Comprehensive error handling and recovery
- **Maintainable** - Uses existing API endpoints and patterns

For questions or issues, refer to the API documentation or check the browser console for debugging information. 