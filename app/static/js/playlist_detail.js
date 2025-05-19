// Playlist Detail Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    const analyzeUnanalyzedBtn = document.getElementById('analyzeUnanalyzedBtn');
    const analyzePlaylistBtn = document.getElementById('analyzePlaylistBtn');
    const toggleViewBtn = document.getElementById('toggleViewBtn');
    const songListView = document.getElementById('song-list-view');
    const gridView = document.getElementById('song-grid-view');
    const progressBar = document.querySelector('.progress');
    const progressBarInner = document.querySelector('.progress-bar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const analysisStatus = document.getElementById('analysisStatus');
    const errorMessage = document.getElementById('errorMessage');
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    const playlistContainer = document.querySelector('.playlist-container');
    const playlistId = playlistContainer ? playlistContainer.getAttribute('data-playlist-id') : null;
    let pollInterval = null;
    let analysisInProgress = false;

    // Toggle between list and grid view
    if (toggleViewBtn && songListView && gridView) {
        toggleViewBtn.addEventListener('click', function() {
            const isGridView = !songListView.classList.contains('d-none');
            
            if (isGridView) {
                // Switch to grid view
                songListView.classList.add('d-none');
                gridView.style.display = 'block';
                toggleViewBtn.innerHTML = '<i class="fas fa-list me-1"></i> Switch to List View';
                
                // Lazy load grid view if empty
                if (gridView.children.length === 0) {
                    loadGridView();
                }
            } else {
                // Switch to list view
                songListView.classList.remove('d-none');
                gridView.style.display = 'none';
                toggleViewBtn.innerHTML = '<i class="fas fa-th-large me-1"></i> Switch to Grid View';
            }
        });
    }
    
    // Function to update UI for analysis start
    function startAnalysis(analysisType) {
        console.log(`Starting ${analysisType} analysis...`);
        
        // Reset UI
        if (progressBar) {
            progressBar.style.display = 'block';
            progressBarInner.style.width = '0%';
            progressBarInner.setAttribute('aria-valuenow', '0');
        }
        
        if (progressText) {
            progressText.textContent = 'Starting analysis...';
        }
        
        if (progressPercent) {
            progressPercent.textContent = '0%';
        }
        
        if (analysisStatus) {
            analysisStatus.textContent = 'Preparing...';
            analysisStatus.className = 'text-muted';
        }
        
        if (errorMessage) {
            errorMessage.style.display = 'none';
            errorMessage.textContent = '';
        }
        
        analysisInProgress = true;
        return true;
    }
    
    // Function to update progress
    function updateProgress(percent, message, currentSong = '') {
        if (progressBarInner) {
            progressBarInner.style.width = `${percent}%`;
            progressBarInner.setAttribute('aria-valuenow', percent);
            progressBarInner.textContent = `${Math.round(percent)}%`;
        }
        
        if (progressPercent) {
            progressPercent.textContent = `${Math.round(percent)}%`;
        }
        
        if (progressText) {
            progressText.textContent = message;
        }
        
        if (analysisStatus) {
            if (percent >= 100) {
                analysisStatus.textContent = 'Analysis complete!';
                analysisStatus.className = 'text-success';
            } else if (percent > 0) {
                analysisStatus.textContent = currentSong || 'Analyzing...';
                analysisStatus.className = 'text-primary';
            } else {
                analysisStatus.textContent = 'Starting...';
                analysisStatus.className = 'text-muted';
            }
        }
    }
    
    // Function to update individual song status
    function updateSongStatus(songId, status) {
        const songRow = document.querySelector(`tr[data-song-id="${songId}"]`);
        if (!songRow) return;
        
        const statusCell = songRow.querySelector('.status-cell');
        const scoreCell = songRow.querySelector('.score-cell');
        const actionsCell = songRow.querySelector('.actions-cell');
        
        if (statusCell) {
            const badge = document.createElement('span');
            badge.className = `badge ${status.is_analyzing ? 'bg-warning' : 'bg-success'}`;
            badge.textContent = status.display_message || (status.is_analyzing ? 'Analyzing...' : 'Analyzed');
            
            // Clear existing status
            while (statusCell.firstChild) {
                statusCell.removeChild(statusCell.firstChild);
            }
            
            statusCell.appendChild(badge);
        }
        
        if (scoreCell && status.score !== undefined) {
            scoreCell.textContent = status.score !== null ? `${status.score}%` : '-';
        }
        
        if (actionsCell) {
            // Update action buttons if needed
            const analyzeBtn = actionsCell.querySelector('.analyze-song-btn');
            if (analyzeBtn) {
                analyzeBtn.disabled = status.is_analyzing;
                analyzeBtn.innerHTML = status.is_analyzing 
                    ? '<i class="fas fa-spinner fa-spin"></i> Analyzing...' 
                    : '<i class="fas fa-search"></i> Re-analyze';
            }
        }
    }
    
    // Function to update the overall score display
    function updateOverallScore(score) {
        const scoreElement = document.getElementById('overall-score');
        if (scoreElement) {
            scoreElement.textContent = score !== null ? `${score}%` : 'N/A';
            
            // Update color based on score
            if (score >= 70) {
                scoreElement.className = 'text-success';
            } else if (score >= 40) {
                scoreElement.className = 'text-warning';
            } else {
                scoreElement.className = 'text-danger';
            }
        }
    }
    
    // Function to show success message
    function showSuccess(message) {
        if (errorMessage) {
            errorMessage.className = 'alert alert-success';
            errorMessage.innerHTML = `<i class="fas fa-check-circle me-2"></i>${message}`;
            errorMessage.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                if (errorMessage.className.includes('alert-success')) {
                    errorMessage.style.display = 'none';
                }
            }, 5000);
        }
    }
    
    // Function to show error message
    function showError(message) {
        if (errorMessage) {
            errorMessage.className = 'alert alert-danger';
            errorMessage.innerHTML = `<i class="fas fa-exclamation-circle me-2"></i>${message}`;
            errorMessage.style.display = 'block';
        }
    }
    
    // Function to reset UI to initial state
    function resetUI() {
        if (progressBar) {
            progressBar.style.display = 'none';
        }
        
        if (analysisStatus) {
            analysisStatus.textContent = 'Ready';
            analysisStatus.className = 'text-muted';
        }
        
        analysisInProgress = false;
    }
    
    // Function to start analysis of songs
    function startSongAnalysis(analysisType) {
        const button = analysisType === 'all' ? analyzePlaylistBtn : analyzeUnanalyzedBtn;
        const originalText = button ? button.innerHTML : '';
        
        // Get playlist ID from multiple possible sources
        const playlistContainer = document.querySelector('.playlist-container');
        const playlistId = playlistContainer ? playlistContainer.getAttribute('data-playlist-id') : 
                            (window.currentPlaylistId || '');
        
        console.log('Starting analysis with playlist ID:', playlistId);
        
        if (!playlistId) {
            showError('Error: Could not determine playlist ID. Please refresh the page and try again.');
            console.error('Playlist ID is missing or empty');
            return false;
        }
        
        if (analysisInProgress) {
            showError('An analysis is already in progress');
            return false;
        }
        
        // Start the analysis UI
        if (!startAnalysis(analysisType)) {
            return false;
        }
        
        // Update button state
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Analyzing...';
        }
        
        // Set a timeout for the fetch request
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
        
        // Ensure playlist ID is properly encoded
        const encodedPlaylistId = encodeURIComponent(playlistId);
        
        // Determine the endpoint based on analysis type
        const endpoint = analysisType === 'all' 
            ? `/api/playlists/${encodedPlaylistId}/analyze/`
            : `/api/playlists/${encodedPlaylistId}/analyze-unanalyzed/`;
            
        console.log('Using endpoint:', endpoint);
        
        // Start the analysis
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
                'X-CSRFToken': csrfToken
            },
            credentials: 'same-origin',
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.message || `Failed to start analysis (HTTP ${response.status})`);
                }).catch(() => {
                    throw new Error(`Failed to start analysis (HTTP ${response.status})`);
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('Analysis started:', data);
            
            if (data.task_id) {
                updateProgress(10, 'Analysis started in the background...');
                showSuccess('Analysis started successfully. The page will refresh when complete.');
                
                // Check status every 5 seconds
                const checkStatus = setInterval(() => {
                    // Use the encoded playlist ID that was used for the initial request
                    const currentPlaylistId = encodeURIComponent(playlistId);
                    
                    if (!currentPlaylistId) {
                        console.error('Playlist ID is missing in status check');
                        clearInterval(checkStatus);
                        showError('Error: Missing playlist ID in status check');
                        if (button) {
                            button.disabled = false;
                            button.innerHTML = originalText;
                        }
                        return;
                    }
                    
                    const statusUrl = `/api/playlists/${currentPlaylistId}/analysis-status/?task_id=${encodeURIComponent(data.task_id)}`;
                    console.log('Checking status at:', statusUrl);
                    
                    fetch(statusUrl, {
                        method: 'GET',
                        headers: {
                            'Accept': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-CSRFToken': csrfToken
                        },
                        credentials: 'same-origin'
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(status => {
                        console.log('Analysis status:', status);
                        
                        if (!status.success) {
                            // Handle error from server
                            clearInterval(checkStatus);
                            showError(status.message || 'Analysis failed. Please try again.');
                            if (button) {
                                button.disabled = false;
                                button.innerHTML = originalText;
                            }
                            return;
                        }
                        
                        if (status.completed || (status.analyzed === status.total && status.total > 0)) {
                            // Analysis is complete
                            clearInterval(checkStatus);
                            showSuccess('Analysis completed successfully! Refreshing page...');
                            setTimeout(() => window.location.reload(), 1500);
                        } else if (status.in_progress) {
                            // Update progress
                            updateProgress(
                                status.progress || 0,
                                status.message || 'Analyzing...',
                                status.current_song || ''
                            );
                        }
                    })
                    .catch(err => {
                        console.error('Error checking status:', err);
                        // Don't clear interval, will retry
                    });
                }, 5000);
            } else {
                throw new Error('Unexpected response from server');
            }
        })
        .catch(error => {
            console.error('Error starting analysis:', error);
            let errorMessage = 'Failed to start analysis. ';
            
            if (error.name === 'AbortError') {
                errorMessage += 'The request timed out. The analysis might still be running in the background.';
            } else if (error.message) {
                errorMessage += error.message;
            } else {
                errorMessage += 'Please try again.';
            }
            
            showError(errorMessage);
            
            if (button) {
                button.disabled = false;
                button.innerHTML = originalText;
                
                // Show a retry button
                const retryButton = document.createElement('button');
                retryButton.className = 'btn btn-warning btn-sm mt-2';
                retryButton.textContent = 'Retry Analysis';
                retryButton.onclick = () => startSongAnalysis(analysisType);
                
                const errorDiv = document.querySelector('.alert-danger');
                if (errorDiv) {
                    errorDiv.appendChild(document.createElement('br'));
                    errorDiv.appendChild(retryButton);
                }
            }
            
            resetUI();
        });
        
        return true;
    }
    
    // Function to load grid view (lazy loading)
    function loadGridView() {
        // Implementation for grid view loading
        console.log('Loading grid view...');
    }
    
    // Helper function to analyze songs one by one
    function analyzeNextSong(songRows, index) {
        if (index >= songRows.length) {
            showSuccess('All songs have been processed!');
            return;
        }
        
        const row = songRows[index];
        const songId = row.getAttribute('data-song-id');
        const songTitle = row.querySelector('td:nth-child(3) a')?.textContent.trim() || 'Unknown Title';
        const songArtist = row.querySelector('td:nth-child(3) .text-muted')?.textContent.trim() || 'Unknown Artist';
        const analyzeBtn = row.querySelector('.analyze-song-btn') || document.createElement('button');
        
        // Update UI to show which song is being analyzed
        const statusCell = row.querySelector('.song-status');
        if (statusCell) {
            statusCell.innerHTML = '<span class="badge bg-info">Analyzing...</span>';
        }
        
        // Analyze the current song
        analyzeSingleSong(songId, songTitle, songArtist, analyzeBtn, () => {
            // After analysis is complete, move to the next song
            analyzeNextSong(songRows, index + 1);
        });
    }
    
    // Event Listeners
    if (analyzeUnanalyzedBtn) {
        analyzeUnanalyzedBtn.addEventListener('click', () => {
            // Find all unanalyzed songs and analyze them one by one
            const unanalyzedSongs = Array.from(document.querySelectorAll('.song-row')).filter(row => {
                const statusBadge = row.querySelector('.song-status .badge');
                return !statusBadge || !statusBadge.classList.contains('bg-success');
            });
            
            if (unanalyzedSongs.length === 0) {
                showSuccess('All songs have been analyzed!');
                return;
            }
            
            // Start with the first unanalyzed song
            analyzeNextSong(unanalyzedSongs, 0);
        });
    }
    
    if (analyzePlaylistBtn) {
        analyzePlaylistBtn.addEventListener('click', () => {
            // Find all songs and analyze them one by one
            const allSongs = document.querySelectorAll('.song-row');
            if (allSongs.length === 0) {
                showError('No songs found to analyze');
                return;
            }
            
            // Start with the first song
            analyzeNextSong(Array.from(allSongs), 0);
        });
    }
    
    // Add event listeners for individual song analysis buttons
    document.addEventListener('click', function(e) {
        const analyzeBtn = e.target.closest('.analyze-song-btn');
        if (analyzeBtn) {
            e.preventDefault();
            const songId = analyzeBtn.getAttribute('data-song-id');
            const songTitle = analyzeBtn.getAttribute('data-song-title');
            const songArtist = analyzeBtn.getAttribute('data-song-artist');
            analyzeSingleSong(songId, songTitle, songArtist, analyzeBtn);
        }
    });
    
    // Function to analyze a single song
    function analyzeSingleSong(songId, songTitle, songArtist, button, onComplete = null) {
        if (!songId) {
            console.error('Song ID is missing');
            showError('Error: Could not determine song ID');
            return;
        }
        
        // Show analyzing status in the UI if not already set
        const songRowElement = document.querySelector(`tr[data-song-id="${songId}"]`);
        if (songRowElement) {
            const statusCell = songRowElement.querySelector('.song-status');
            if (statusCell && !statusCell.innerHTML.includes('Analyzing')) {
                statusCell.innerHTML = '<span class="badge bg-info">Analyzing...</span>';
            }
        }
        
        const originalButtonHTML = button ? button.innerHTML : '';
        const buttonText = button ? button.querySelector('.analyze-btn-text') : null;
        const spinner = button ? button.querySelector('.spinner-border') : null;
        
        // Update button state
        if (button) {
            button.disabled = true;
            if (buttonText) buttonText.textContent = 'Analyzing...';
            if (spinner) spinner.classList.remove('d-none');
        }
        
        // Show progress for this specific song
        const songRow = button ? button.closest('tr') : null;
        if (songRow) {
            const statusCell = songRow.querySelector('.song-status');
            if (statusCell) {
                statusCell.innerHTML = '<span class="badge bg-info">Analyzing...</span>';
            }
        }
        
        // Start the analysis
        fetch(`/api/songs/${songId}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.message || `Failed to start analysis (HTTP ${response.status})`);
                }).catch(() => {
                    throw new Error(`Failed to start analysis (HTTP ${response.status})`);
                });
            }
            return response.json();
        })
        .then(data => {
            if (!data.success) {
                throw new Error(data.message || 'Failed to start analysis');
            }
            
            console.log(`Analysis started for song ${songId}:`, data);
            
            // Start polling for status updates
            const checkStatus = setInterval(() => {
                fetch(`/api/songs/${songId}/analysis-status?task_id=${encodeURIComponent(data.task_id)}`, {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': csrfToken
                    },
                    credentials: 'same-origin'
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! Status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(status => {
                    console.log(`Status for song ${songId}:`, status);
                    
                    if (!status.success) {
                        throw new Error(status.message || 'Failed to check status');
                    }
                    
                    if (status.completed) {
                        // Analysis complete
                        clearInterval(checkStatus);
                        updateSongAnalysisUI(songId, status.analysis);
                        showSuccess(`Analysis complete for "${songTitle}" by ${songArtist}`);
                        
                        // Reset button
                        if (button) {
                            button.disabled = false;
                            if (buttonText) buttonText.textContent = 'Re-analyze';
                            if (spinner) spinner.classList.add('d-none');
                        }
                        
                        // Call the completion callback if provided
                        if (typeof onComplete === 'function') {
                            onComplete();
                        }
                    } else if (status.in_progress) {
                        // Still processing
                        if (songRow) {
                            const statusCell = songRow.querySelector('.song-status');
                            if (statusCell) {
                                statusCell.innerHTML = '<span class="badge bg-info">Analyzing...</span>';
                            }
                        }
                    }
                })
                .catch(err => {
                    console.error(`Error checking status for song ${songId}:`, err);
                    // Don't clear interval, will retry
                });
                
            }, 2000); // Check every 2 seconds
            
        })
        .catch(error => {
            console.error(`Error analyzing song ${songId}:`, error);
            showError(`Failed to analyze "${songTitle}": ${error.message}`);
            
            // Reset button
            if (button) {
                button.disabled = false;
                if (buttonText) buttonText.textContent = 'Try Again';
                if (spinner) spinner.classList.add('d-none');
            }
            
            // Update status cell
            if (songRow) {
                const statusCell = songRow.querySelector('.song-status');
                if (statusCell) {
                    statusCell.innerHTML = '<span class="badge bg-danger">Failed</span>';
                }
            }
        });
    }
    
    // Function to update the UI after song analysis
    function updateSongAnalysisUI(songId, analysis) {
        const songRow = document.querySelector(`tr[data-song-id="${songId}"]`);
        if (!songRow) return;
        
        // Update score and concern level
        const scoreCell = songRow.querySelector('.song-score');
        if (scoreCell && analysis && analysis.score !== undefined) {
            const concernLevel = analysis.concern_level ? analysis.concern_level.toLowerCase() : '';
            let badgeClass = 'bg-secondary';
            let iconClass = 'fa-question-circle';
            
            if (concernLevel === 'extreme') {
                badgeClass = 'bg-extreme';
                iconClass = 'fa-exclamation-triangle';
            } else if (concernLevel === 'high') {
                badgeClass = 'bg-high';
                iconClass = 'fa-exclamation-circle';
            } else if (concernLevel === 'medium') {
                badgeClass = 'bg-medium';
                iconClass = 'fa-info-circle';
            } else if (concernLevel === 'low') {
                badgeClass = 'bg-low';
                iconClass = 'fa-check-circle';
            }
            
            // Update the score cell with the same structure as the initial template
            scoreCell.innerHTML = `
                <div class="d-flex align-items-center">
                    <span class="concern-badge ${badgeClass}">
                        <i class="fas ${iconClass}"></i>
                        ${Math.round(analysis.score)}
                    </span>
                    <span class="small ms-2">${analysis.concern_level || 'Not Analyzed'}</span>
                </div>
                <button class="btn btn-sm btn-outline-primary ms-2 analyze-song-btn" 
                        data-song-id="${songId}"
                        data-song-title="${songRow.dataset.songTitle || ''}"
                        data-song-artist="${songRow.dataset.songArtist || ''}"
                        title="Re-analyze Song">
                    <i class="fas fa-sync-alt"></i>
                </button>
            `;
            
            // Re-attach the event listener to the new analyze button
            const newButton = scoreCell.querySelector('.analyze-song-btn');
            if (newButton) {
                newButton.addEventListener('click', function() {
                    analyzeSingleSong(
                        songId,
                        this.dataset.songTitle,
                        this.dataset.songArtist,
                        this
                    );
                });
            }
        }
        
        // Update status
        const statusCell = songRow.querySelector('.song-status');
        if (statusCell) {
            statusCell.innerHTML = '<span class="badge bg-success">Analyzed</span>';
        }
        
        // Update the overall score display
        updateOverallScore();
    }
    
    // Initialize the page
    resetUI();
});
