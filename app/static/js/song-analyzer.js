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

        // Handle playlist analysis button
        if (e.target.classList.contains('analyze-playlist-btn')) {
            console.log('🚨 PLAYLIST BUTTON CLICKED!', e.target);
            console.log('🚨 Button classes:', e.target.classList);
            console.log('🚨 Button data attributes:', {
                playlistId: e.target.getAttribute('data-playlist-id'),
                playlistName: e.target.getAttribute('data-playlist-name')
            });

            e.preventDefault();
            e.stopImmediatePropagation();

            const playlistId = e.target.getAttribute('data-playlist-id');
            const playlistName = e.target.getAttribute('data-playlist-name') || 'Unknown Playlist';

            console.log(`🎯 Starting playlist analysis for Playlist ID: ${playlistId}, Name: ${playlistName}`);

            analyzePlaylist(playlistId, playlistName, e.target);
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

function analyzePlaylist(playlistId, playlistName, buttonElement) {
    console.log(`🔬 analyzePlaylist called: ${playlistId} - ${playlistName}`);

    // Show ETA toast immediately
    showPlaylistEtaToast(playlistName);

    // Disable the button and show loading state
    buttonElement.disabled = true;
    const originalText = buttonElement.innerHTML;
    buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing Playlist...';

    // Start the playlist analysis
    console.log(`📤 Starting AJAX request to /analyze_playlist/${playlistId}`);
    console.log('🚨 FETCH ABOUT TO BE CALLED!');

    fetch(`/analyze_playlist/${playlistId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
    .then(response => {
        console.log('🚨 FETCH RESPONSE RECEIVED!', response);
        console.log(`📡 Playlist analysis response status: ${response.status}`);
        // If session expired, server will return 401 JSON with redirect
        if (response.status === 401 && !response.redirected) {
            return response.json().then(data => {
                const target = (data && data.redirect) || '/auth/login';
                console.error('🔒 Unauthorized. Redirecting to login:', target);
                window.location.href = target;
                return { success: false };
            });
        }
        if (response.redirected) {
            // The server redirected us (typical for non-AJAX requests)
            console.log('✅ Playlist analysis started successfully (redirected)');
            showPlaylistStartedToast(playlistName);

            // Start polling for progress instead of just reloading
            pollPlaylistProgress(playlistId, playlistName, buttonElement, originalText);

            return { success: true };
        } else {
            // AJAX request - parse JSON response
            return response.json();
        }
    })
    .then(data => {
        if (data && data.success === false) {
            console.error('❌ Playlist analysis failed:', data);
            showErrorToast('Playlist Analysis Failed', data.message || 'Unknown error');
            resetPlaylistButton(buttonElement, originalText);
        } else if (data && data.success === true) {
            console.log('✅ Playlist analysis started successfully (AJAX)');
            showPlaylistStartedToast(playlistName);

            // Start polling for progress
            pollPlaylistProgress(playlistId, playlistName, buttonElement, originalText);
        }
    })
    .catch(error => {
        console.error('💥 Error starting playlist analysis:', error);
        showErrorToast('Error Starting Analysis', 'Failed to start playlist analysis. Please try again.');
        resetPlaylistButton(buttonElement, originalText);
    });
}

function pollPlaylistProgress(playlistId, playlistName, buttonElement, originalText) {
    console.log(`🔄 Starting progress polling for playlist ${playlistId}`);

    let lastProgress = 0;
    let progressToastId = null;

    const updateProgress = (progress, message) => {
        console.log(`🎯 updateProgress called: ${progress}% - ${message}`);

        // Update button text with progress
        const newButtonText = `<i class="fas fa-spinner fa-spin"></i> ${progress}% Complete`;
        console.log(`🔄 Updating button text to: ${newButtonText}`);
        buttonElement.innerHTML = newButtonText;

        // Update or create progress toast
        if (progressToastId) {
            console.log(`📝 Updating existing toast: ${progressToastId}`);
            const existingToast = document.getElementById(progressToastId);
            if (existingToast) {
                const toastBody = existingToast.querySelector('.toast-body');
                if (toastBody) {
                    toastBody.innerHTML = `<strong>Analysis Progress</strong><br>${message}`;
                    console.log(`✅ Toast updated with: ${message}`);
                } else {
                    console.log(`❌ Toast body not found in existing toast`);
                }
            } else {
                console.log(`❌ Existing toast not found: ${progressToastId}`);
            }
        } else {
            console.log(`🆕 Creating new progress toast`);
            progressToastId = 'progress-toast-' + Date.now();
            createProgressToast(progressToastId, 'Analysis Progress', message, 'info');
            console.log(`✅ Created new toast: ${progressToastId}`);
        }
    };

    const pollInterval = setInterval(() => {
        fetch(`/api/playlists/${playlistId}/analysis-status`, {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            console.log(`📡 Poll response status: ${response.status}, redirected: ${response.redirected}, url: ${response.url}`);
            if (response.status === 401) {
                // Unauthorized during polling
                return response.json().then(data => {
                    const target = (data && data.redirect) || '/auth/login';
                    console.error('🔒 Unauthorized during polling. Redirecting to login:', target);
                    clearInterval(pollInterval);
                    showErrorToast('Authentication Error', 'Session expired. Redirecting to login...');
                    resetPlaylistButton(buttonElement, originalText);
                    window.location.href = target;
                    return null;
                });
            }
            if (response.status === 302 || response.redirected) {
                console.error('🚨 Authentication issue: API request redirected to login');
                clearInterval(pollInterval);
                showErrorToast('Authentication Error', 'Session expired. Please refresh the page and log in again.');
                resetPlaylistButton(buttonElement, originalText);
                return null;
            }
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data) return; // Skip if no data (authentication error)
            console.log(`📊 Progress poll data:`, data);

            if (data.success) {
                const progress = data.progress || 0;
                const analyzedCount = data.analyzed_count || 0;
                const totalCount = data.total_count || 0;
                const message = data.message || `${analyzedCount}/${totalCount} songs analyzed`;

                console.log(`🔍 Progress details: ${progress}% (${analyzedCount}/${totalCount}), last: ${lastProgress}%`);

                // Update progress if it has changed
                if (progress !== lastProgress) {
                    console.log(`📈 Updating progress from ${lastProgress}% to ${progress}%`);
                    updateProgress(progress, message);
                    lastProgress = progress;
                } else {
                    console.log(`⏸️ No progress change (still ${progress}%)`);
                }

                // Check if completed
                if (data.completed && progress >= 100) {
                    clearInterval(pollInterval);
                    console.log('🎉 Playlist analysis completed');

                    // Remove progress toast
                    if (progressToastId) {
                        const progressToast = document.getElementById(progressToastId);
                        if (progressToast && window.bootstrap && window.bootstrap.Toast) {
                            const toast = window.bootstrap.Toast.getInstance(progressToast);
                            if (toast) toast.hide();
                        }
                    }

                    // Show completion toast
                    showPlaylistCompletionToast(playlistName, analyzedCount, totalCount);

                    // Reset button
                    resetPlaylistButton(buttonElement, originalText);

                    // Refresh page to show updated results
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                }
            } else {
                console.error('❌ Error polling progress:', data);
                clearInterval(pollInterval);
                showErrorToast('Progress Error', 'Unable to track analysis progress');
                resetPlaylistButton(buttonElement, originalText);
            }
        })
        .catch(error => {
            console.error('💥 Error polling playlist progress:', error);
            clearInterval(pollInterval);
            showErrorToast('Progress Error', 'Lost connection while tracking progress');
            resetPlaylistButton(buttonElement, originalText);
        });
    }, 5000); // Poll every 5 seconds

    // Set a timeout to stop polling after reasonable time (15 minutes)
    setTimeout(() => {
        clearInterval(pollInterval);
        if (buttonElement.disabled) {
            console.log('⏰ Polling timeout - stopping progress tracking');
            showErrorToast('Analysis Timeout', 'Analysis is taking longer than expected. Please refresh the page to check status.');
            resetPlaylistButton(buttonElement, originalText);
        }
    }, 15 * 60 * 1000); // 15 minutes
}

function showPlaylistEtaToast(playlistName) {
    const message = `Starting analysis for all songs in "${playlistName}". Progress will be shown in real-time. This may take several minutes depending on playlist size.`;

    console.log('📢 Showing playlist ETA toast:', message);
    createToast('Playlist Analysis Started', message, 'info', 10000);
}

function showPlaylistStartedToast(playlistName) {
    const message = `Analysis jobs queued for "${playlistName}". Watch the button and notifications for real-time progress updates.`;

    console.log('🎉 Showing playlist started toast:', message);
    createToast('Analysis Jobs Queued', message, 'success', 8000);
}

function showPlaylistCompletionToast(playlistName, analyzedCount, totalCount) {
    const message = `Analysis completed for "${playlistName}". ${analyzedCount}/${totalCount} songs analyzed.`;

    console.log('🎉 Showing playlist completion toast:', message);
    createToast('Analysis Complete', message, 'success', 6000);
}

function createProgressToast(toastId, title, message, type = 'info') {
    // Find or create toast container
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '1055';
        document.body.appendChild(toastContainer);
    }

    // Create persistent progress toast (no auto-hide)
    const toastHtml = `
        <div class="toast align-items-center text-bg-${type} border-0" role="alert" aria-live="polite" aria-atomic="true" id="${toastId}">
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

    // Initialize and show toast (persistent, no auto-hide)
    const toastElement = document.getElementById(toastId);
    if (window.bootstrap && window.bootstrap.Toast) {
        const toast = new window.bootstrap.Toast(toastElement, {
            autohide: false  // Don't auto-hide progress toasts
        });
        toast.show();

        // Remove from DOM when manually dismissed
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    } else {
        console.warn('Bootstrap Toast not available, using fallback display');
    }
}

function resetPlaylistButton(buttonElement, originalText) {
    buttonElement.disabled = false;
    buttonElement.innerHTML = originalText;
}

console.log('📝 Song Analyzer Script Loaded');
