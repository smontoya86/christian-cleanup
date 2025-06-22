console.log('🎵 Song Analyzer Loading...');

// Simple song analysis with ETA and completion notification
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Song Analyzer DOM Ready');
    
    // Add click handler for analyze buttons with higher priority (capture phase)
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('analyze-song-btn')) {
            e.preventDefault();
            e.stopImmediatePropagation(); // Stop other event handlers from firing
            
            const songId = e.target.getAttribute('data-song-id');
            const songTitle = e.target.getAttribute('data-song-title') || 'Unknown Song';
            const songArtist = e.target.getAttribute('data-song-artist') || 'Unknown Artist';
            
            console.log(`🎯 Starting analysis for Song ID: ${songId}, Title: ${songTitle}`);
            
            analyzeSong(songId, songTitle, songArtist, e.target);
        }
    }, true); // Use capture phase to get priority over other event handlers
    
    console.log('✅ Song Analyzer Event Listeners Ready');
});

function analyzeSong(songId, songTitle, songArtist, buttonElement) {
    console.log(`🔬 analyzeSong called: ${songId} - ${songTitle}`);
    
    // Show ETA toast immediately
    showEtaToast(songTitle, songArtist);
    
    // Disable the button and show loading state
    buttonElement.disabled = true;
    buttonElement.textContent = 'Analyzing...';
    
    // Start the analysis
    fetch(`/api/analyze_song/${songId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        console.log(`📡 Analysis response status: ${response.status}`);
        return response.json();
    })
    .then(data => {
        console.log('📊 Analysis response data:', data);
        
        if (data.success || data.status === 'success') {
            console.log('✅ Analysis started successfully');
            
            // Start polling for completion
            pollForCompletion(songId, songTitle, songArtist, buttonElement);
        } else {
            console.error('❌ Analysis failed to start:', data);
            showErrorToast('Failed to start analysis', data.message || 'Unknown error');
            resetButton(buttonElement);
        }
    })
    .catch(error => {
        console.error('💥 Error starting song analysis:', error);
        showErrorToast('Error starting analysis', error.message);
        resetButton(buttonElement);
    });
}

function pollForCompletion(songId, songTitle, songArtist, buttonElement) {
    console.log(`🔄 Polling for completion: ${songId}`);
    
    const pollInterval = setInterval(() => {
        fetch(`/api/song_analysis_status/${songId}`, {
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            console.log(`📊 Status poll data:`, data);
            
            if (data.completed) {
                clearInterval(pollInterval);
                
                if (data.success && data.has_analysis) {
                    console.log('🎉 Analysis completed successfully');
                    showCompletionToast(songTitle, songArtist, data.result);
                    updateSongRow(songId, data.result);
                } else if (data.failed) {
                    console.log('💥 Analysis failed');
                    showErrorToast('Analysis failed', `Failed to analyze "${songTitle}"`);
                }
                
                resetButton(buttonElement);
            }
        })
        .catch(error => {
            console.error('💥 Error polling status:', error);
            clearInterval(pollInterval);
            resetButton(buttonElement);
        });
    }, 3000); // Poll every 3 seconds
}

function showEtaToast(songTitle, songArtist) {
    const artistText = songArtist && songArtist !== 'Unknown Artist' ? ` by ${songArtist}` : '';
    const message = `Analysis started for "${songTitle}"${artistText}. ETA: 30-60 seconds.`;
    
    console.log('📢 Showing ETA toast:', message);
    createToast('Analysis Started', message, 'primary', 8000);
}

function showCompletionToast(songTitle, songArtist, result) {
    const score = Math.round(result.score || 0);
    const concern = result.concern_level || 'Unknown';
    const artistText = songArtist && songArtist !== 'Unknown Artist' ? ` by ${songArtist}` : '';
    
    const message = `"${songTitle}"${artistText} - Score: ${score}% (${concern})`;
    
    console.log('🎉 Showing completion toast:', message);
    createToast('Analysis Complete', message, 'success', 6000);
}

function showErrorToast(title, message) {
    console.log('❌ Showing error toast:', title, message);
    createToast(title, message, 'danger', 5000);
}

function createToast(title, message, type = 'primary', duration = 5000) {
    // Find or create toast container
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1055';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true" id="${toastId}">
            <div class="d-flex">
                <div class="toast-body">
                    <strong>${title}</strong><br>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    
    // Initialize and show toast
    const toastElement = document.getElementById(toastId);
    if (window.bootstrap && window.bootstrap.Toast) {
        const toast = new window.bootstrap.Toast(toastElement, {
            autohide: true,
            delay: duration
        });
        toast.show();
        
        // Remove from DOM after hiding
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    } else {
        console.warn('Bootstrap Toast not available, toast will remain visible');
        // Fallback: auto-remove after duration
        setTimeout(() => {
            if (toastElement && toastElement.parentNode) {
                toastElement.remove();
            }
        }, duration);
    }
}

function updateSongRow(songId, result) {
    // Find the song row in the table and update the score column
    const songLinks = document.querySelectorAll(`a[href$="/song/${songId}"]`);
    if (songLinks.length > 0) {
        // Find the closest table row
        const row = songLinks[0].closest('tr');
        if (row) {
            // Find the score column (usually the 5th td - 0-indexed = 4)
            const scoreCells = row.querySelectorAll('td');
            if (scoreCells.length >= 5) {
                const scoreCell = scoreCells[4]; // 5th column (0-indexed)
                const score = Math.round(result.score || 0);
                const concern = result.concern_level || 'Unknown';
                
                scoreCell.innerHTML = `
                    <span class="badge bg-primary">${score}%</span>
                    <span class="badge bg-secondary">${concern}</span>
                `;
                
                console.log(`✅ Updated song row for ID ${songId}: ${score}% ${concern}`);
            }
        }
    }
}

function resetButton(buttonElement) {
    buttonElement.disabled = false;
    buttonElement.textContent = 'Analyze';
}

console.log('📝 Song Analyzer Script Loaded'); 