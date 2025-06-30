/**
 * Smart Polling Integration Examples
 * 
 * These examples show how to integrate the ProgressPoller with existing UI components
 * for real-time progress updates during analysis jobs.
 */

// Example 1: Single Song Analysis with Progress Bar
function analyzeSongWithProgress(songId, progressBarElement, statusElement) {
    // Show initial loading state
    progressBarElement.style.width = '0%';
    statusElement.textContent = 'Starting analysis...';
    
    // Start the analysis
    fetch(`/api/songs/${songId}/analyze`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.job_id) {
                // Start polling for progress
                pollJobProgress(data.job_id, {
                    onProgress: (progress) => {
                        // Update progress bar
                        const percent = Math.round(progress.progress * 100);
                        progressBarElement.style.width = `${percent}%`;
                        
                        // Update status text
                        const stepMessages = {
                            'starting': 'Initializing analysis...',
                            'fetching_lyrics': 'Fetching song lyrics...',
                            'analyzing': 'Analyzing content...',
                            'complete': 'Analysis complete!'
                        };
                        statusElement.textContent = stepMessages[progress.current_step] || 'Processing...';
                        
                        // Show ETA if available
                        if (progress.eta_seconds && progress.eta_seconds > 5) {
                            statusElement.textContent += ` (${Math.round(progress.eta_seconds)}s remaining)`;
                        }
                    },
                    onComplete: (progress) => {
                        progressBarElement.style.width = '100%';
                        statusElement.textContent = 'Analysis complete!';
                        
                        // Reload the page or update the analysis results
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    },
                    onError: (error) => {
                        progressBarElement.style.width = '100%';
                        progressBarElement.style.backgroundColor = '#dc3545'; // Red for error
                        statusElement.textContent = 'Analysis failed. Please try again.';
                        console.error('Analysis error:', error);
                    }
                });
            } else {
                statusElement.textContent = 'Failed to start analysis';
            }
        })
        .catch(error => {
            statusElement.textContent = 'Error starting analysis';
            console.error('Start analysis error:', error);
        });
}

// Example 2: Playlist Analysis with Per-Song Progress
function analyzePlaylistWithProgress(playlistId, containerElement) {
    // Create progress UI
    const progressContainer = document.createElement('div');
    progressContainer.className = 'playlist-analysis-progress';
    progressContainer.innerHTML = `
        <div class="overall-progress">
            <h4>Analyzing Playlist</h4>
            <div class="progress-bar-container">
                <div class="progress-bar" id="overall-progress-bar"></div>
            </div>
            <div class="progress-text" id="overall-status">Starting analysis...</div>
        </div>
        <div class="song-progress-list" id="song-progress-list">
            <!-- Individual song progress will be added here -->
        </div>
    `;
    
    containerElement.appendChild(progressContainer);
    
    const overallProgressBar = document.getElementById('overall-progress-bar');
    const overallStatus = document.getElementById('overall-status');
    const songProgressList = document.getElementById('song-progress-list');
    
    // Start playlist analysis
    fetch(`/api/playlists/${playlistId}/analyze-unanalyzed`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.job_id) {
                pollJobProgress(data.job_id, {
                    onProgress: (progress) => {
                        // Update overall progress
                        const percent = Math.round(progress.progress * 100);
                        overallProgressBar.style.width = `${percent}%`;
                        
                        // Update status with song count
                        if (progress.metadata && progress.metadata.total_songs) {
                            const current = progress.metadata.processed_songs || 0;
                            const total = progress.metadata.total_songs;
                            overallStatus.textContent = `Analyzing songs: ${current}/${total}`;
                            
                            if (progress.eta_seconds && progress.eta_seconds > 10) {
                                overallStatus.textContent += ` (${Math.round(progress.eta_seconds / 60)} min remaining)`;
                            }
                        }
                        
                        // Update individual song progress if available
                        if (progress.metadata && progress.metadata.current_song) {
                            updateSongProgress(songProgressList, progress.metadata.current_song, progress.metadata.song_progress || 0);
                        }
                    },
                    onComplete: (progress) => {
                        overallProgressBar.style.width = '100%';
                        overallStatus.textContent = 'Playlist analysis complete!';
                        
                        // Show completion message and reload
                        setTimeout(() => {
                            alert('Playlist analysis completed! The page will refresh to show results.');
                            window.location.reload();
                        }, 2000);
                    },
                    onError: (error) => {
                        overallProgressBar.style.backgroundColor = '#dc3545';
                        overallStatus.textContent = 'Analysis failed. Please try again.';
                        console.error('Playlist analysis error:', error);
                    }
                });
            }
        });
}

// Helper function to update individual song progress
function updateSongProgress(containerElement, songInfo, progress) {
    let songElement = document.getElementById(`song-progress-${songInfo.id}`);
    
    if (!songElement) {
        songElement = document.createElement('div');
        songElement.id = `song-progress-${songInfo.id}`;
        songElement.className = 'song-progress-item';
        songElement.innerHTML = `
            <div class="song-info">
                <span class="song-title">${songInfo.title || 'Unknown Song'}</span>
                <span class="song-artist">${songInfo.artist || 'Unknown Artist'}</span>
            </div>
            <div class="song-progress-bar-container">
                <div class="song-progress-bar"></div>
            </div>
            <div class="song-status">Waiting...</div>
        `;
        containerElement.appendChild(songElement);
    }
    
    const progressBar = songElement.querySelector('.song-progress-bar');
    const statusElement = songElement.querySelector('.song-status');
    
    const percent = Math.round(progress * 100);
    progressBar.style.width = `${percent}%`;
    
    if (progress >= 1.0) {
        statusElement.textContent = 'Complete';
        progressBar.style.backgroundColor = '#28a745'; // Green for complete
    } else if (progress > 0) {
        statusElement.textContent = 'Analyzing...';
        progressBar.style.backgroundColor = '#007bff'; // Blue for in progress
    } else {
        statusElement.textContent = 'Waiting...';
    }
}

// Example 3: Background Analysis with Minimal UI
function startBackgroundAnalysisWithNotification(userId) {
    // Show a small notification
    const notification = createNotification('Starting background analysis...', 'info');
    
    fetch(`/api/admin/reanalyze-user/${userId}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.job_id) {
                updateNotification(notification, 'Background analysis in progress...', 'info');
                
                pollJobProgress(data.job_id, {
                    initialInterval: 5000, // Poll every 5 seconds for background jobs
                    maxInterval: 30000,    // Max 30 seconds between polls
                    
                    onProgress: (progress) => {
                        if (progress.metadata && progress.metadata.total_songs) {
                            const current = progress.metadata.processed_songs || 0;
                            const total = progress.metadata.total_songs;
                            updateNotification(notification, 
                                `Background analysis: ${current}/${total} songs processed`, 'info');
                        }
                    },
                    onComplete: (progress) => {
                        updateNotification(notification, 'Background analysis completed!', 'success');
                        setTimeout(() => {
                            removeNotification(notification);
                        }, 5000);
                    },
                    onError: (error) => {
                        updateNotification(notification, 'Background analysis failed', 'error');
                        setTimeout(() => {
                            removeNotification(notification);
                        }, 5000);
                    }
                });
            }
        });
}

// Example 4: Queue Status Dashboard
function createQueueStatusDashboard(containerElement) {
    const dashboardHTML = `
        <div class="queue-dashboard">
            <h3>Analysis Queue Status</h3>
            <div class="queue-stats" id="queue-stats">
                <div class="stat-item">
                    <span class="stat-label">Pending Jobs:</span>
                    <span class="stat-value" id="pending-jobs">-</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Active Jobs:</span>
                    <span class="stat-value" id="active-jobs">-</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Worker Status:</span>
                    <span class="stat-value" id="worker-status">-</span>
                </div>
            </div>
            <div class="active-jobs-list" id="active-jobs-list">
                <!-- Active jobs will be listed here -->
            </div>
        </div>
    `;
    
    containerElement.innerHTML = dashboardHTML;
    
    // Poll queue status every 3 seconds
    function updateQueueStatus() {
        Promise.all([
            fetch('/api/queue/status').then(r => r.json()),
            fetch('/api/worker/health').then(r => r.json())
        ]).then(([queueData, workerData]) => {
            // Update stats
            document.getElementById('pending-jobs').textContent = queueData.queue_size || 0;
            document.getElementById('active-jobs').textContent = queueData.active_jobs || 0;
            document.getElementById('worker-status').textContent = workerData.status || 'Unknown';
            
            // Update active jobs list
            updateActiveJobsList(queueData.active_jobs_details || []);
        }).catch(error => {
            console.error('Queue status update error:', error);
        });
    }
    
    // Update immediately and then every 3 seconds
    updateQueueStatus();
    setInterval(updateQueueStatus, 3000);
}

function updateActiveJobsList(activeJobs) {
    const container = document.getElementById('active-jobs-list');
    
    if (activeJobs.length === 0) {
        container.innerHTML = '<p class="no-jobs">No active jobs</p>';
        return;
    }
    
    container.innerHTML = activeJobs.map(job => `
        <div class="active-job-item" data-job-id="${job.job_id}">
            <div class="job-info">
                <span class="job-type">${job.job_type}</span>
                <span class="job-target">${job.target_id}</span>
            </div>
            <div class="job-progress">
                <div class="progress-bar-small">
                    <div class="progress-fill" style="width: ${Math.round((job.progress || 0) * 100)}%"></div>
                </div>
                <span class="progress-text">${Math.round((job.progress || 0) * 100)}%</span>
            </div>
        </div>
    `).join('');
}

// Utility functions for notifications
function createNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span class="notification-message">${message}</span>
        <button class="notification-close" onclick="removeNotification(this.parentElement)">×</button>
    `;
    
    // Add to notification container or body
    const container = document.getElementById('notification-container') || document.body;
    container.appendChild(notification);
    
    return notification;
}

function updateNotification(notification, message, type) {
    notification.className = `notification notification-${type}`;
    notification.querySelector('.notification-message').textContent = message;
}

function removeNotification(notification) {
    if (notification && notification.parentElement) {
        notification.parentElement.removeChild(notification);
    }
}

// Example CSS for styling (add to your CSS files)
const exampleCSS = `
.playlist-analysis-progress {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
    background: #f9f9f9;
}

.progress-bar-container {
    width: 100%;
    height: 20px;
    background: #e9ecef;
    border-radius: 10px;
    overflow: hidden;
    margin: 10px 0;
}

.progress-bar {
    height: 100%;
    background: #007bff;
    transition: width 0.3s ease;
}

.song-progress-item {
    display: flex;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #eee;
}

.song-info {
    flex: 1;
    margin-right: 15px;
}

.song-title {
    font-weight: bold;
    display: block;
}

.song-artist {
    color: #666;
    font-size: 0.9em;
}

.song-progress-bar-container {
    width: 100px;
    height: 8px;
    background: #e9ecef;
    border-radius: 4px;
    margin-right: 10px;
}

.song-progress-bar {
    height: 100%;
    background: #007bff;
    border-radius: 4px;
    transition: width 0.3s ease;
}

.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 4px;
    color: white;
    z-index: 1000;
    max-width: 300px;
}

.notification-info { background: #17a2b8; }
.notification-success { background: #28a745; }
.notification-error { background: #dc3545; }

.notification-close {
    background: none;
    border: none;
    color: white;
    font-size: 18px;
    cursor: pointer;
    float: right;
    margin-left: 10px;
}

.queue-dashboard {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}

.queue-stats {
    display: flex;
    gap: 20px;
    margin-bottom: 20px;
}

.stat-item {
    display: flex;
    flex-direction: column;
    align-items: center;
}

.stat-label {
    font-size: 0.9em;
    color: #666;
}

.stat-value {
    font-size: 1.5em;
    font-weight: bold;
    color: #007bff;
}

.active-job-item {
    display: flex;
    align-items: center;
    padding: 10px;
    border: 1px solid #eee;
    border-radius: 4px;
    margin-bottom: 8px;
}

.job-info {
    flex: 1;
}

.progress-bar-small {
    width: 60px;
    height: 6px;
    background: #e9ecef;
    border-radius: 3px;
    margin-right: 8px;
}

.progress-fill {
    height: 100%;
    background: #007bff;
    border-radius: 3px;
    transition: width 0.3s ease;
}
`;

// Export examples for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        analyzeSongWithProgress,
        analyzePlaylistWithProgress,
        startBackgroundAnalysisWithNotification,
        createQueueStatusDashboard,
        exampleCSS
    };
} 