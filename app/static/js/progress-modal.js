/**
 * Progress Modal for Background Job Tracking
 * 
 * Provides a Bootstrap modal with progress bar for tracking
 * long-running background jobs (like playlist analysis).
 */

class ProgressModal {
    constructor() {
        this.modal = null;
        this.jobId = null;
        this.pollInterval = null;
        this.onComplete = null;
    }

    /**
     * Show the progress modal and start tracking a job
     * @param {string} jobId - RQ job ID
     * @param {string} title - Modal title
     * @param {function} onComplete - Callback when job completes
     */
    show(jobId, title = 'Processing...', onComplete = null) {
        this.jobId = jobId;
        this.onComplete = onComplete;
        this.createModal(title);
        this.startPolling();
    }

    createModal(title) {
        // Remove existing modal if any
        const existing = document.getElementById('progressModal');
        if (existing) {
            existing.remove();
        }

        // Create modal HTML
        const modalHTML = `
            <div class="modal fade" id="progressModal" data-bs-backdrop="static" data-bs-keyboard="false" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                        </div>
                        <div class="modal-body">
                            <div class="progress mb-3" style="height: 30px;">
                                <div id="progressBar" 
                                     class="progress-bar progress-bar-striped progress-bar-animated" 
                                     role="progressbar" 
                                     style="width: 0%"
                                     aria-valuenow="0" 
                                     aria-valuemin="0" 
                                     aria-valuemax="100">
                                    0%
                                </div>
                            </div>
                            <div class="text-center">
                                <p id="progressStatus" class="mb-2">
                                    <i class="fas fa-hourglass-start me-2"></i>
                                    <span>Starting analysis...</span>
                                </p>
                                <p id="progressDetails" class="text-muted small mb-0"></p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add to page
        document.body.insertAdjacentHTML('beforeend', modalHTML);

        // Show modal
        this.modal = new bootstrap.Modal(document.getElementById('progressModal'));
        this.modal.show();
    }

    startPolling() {
        // Poll every 2 seconds
        this.pollInterval = setInterval(() => this.checkProgress(), 2000);
        // Initial check
        this.checkProgress();
    }

    async checkProgress() {
        try {
            const response = await fetch(`/api/analysis/status/${this.jobId}`);
            
            if (!response.ok) {
                if (response.status === 404) {
                    this.handleError('Job not found. It may have expired.');
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
                return;
            }

            const data = await response.json();
            this.updateUI(data);

        } catch (error) {
            console.error('Error checking progress:', error);
            this.handleError(`Failed to check progress: ${error.message}`);
        }
    }

    updateUI(data) {
        const progressBar = document.getElementById('progressBar');
        const progressStatus = document.getElementById('progressStatus');
        const progressDetails = document.getElementById('progressDetails');

        const status = data.status;

        if (status === 'queued') {
            // Waiting in queue
            const position = data.position || 0;
            progressStatus.innerHTML = `
                <i class="fas fa-clock me-2"></i>
                <span>Waiting in queue...</span>
            `;
            progressDetails.textContent = position > 0 
                ? `Position in queue: ${position}`
                : 'Starting soon...';

        } else if (status === 'started') {
            // In progress
            const progress = data.progress || {};
            const percentage = progress.percentage || 0;
            const current = progress.current || 0;
            const total = progress.total || 0;
            const currentSong = progress.current_song || '';

            // Update progress bar
            progressBar.style.width = `${percentage}%`;
            progressBar.textContent = `${Math.round(percentage)}%`;
            progressBar.setAttribute('aria-valuenow', percentage);

            // Update status
            progressStatus.innerHTML = `
                <i class="fas fa-spinner fa-spin me-2"></i>
                <span>Analyzing songs... (${current} of ${total})</span>
            `;

            // Show current song
            if (currentSong) {
                progressDetails.textContent = `Current: ${currentSong}`;
            }

        } else if (status === 'finished') {
            // Success!
            this.handleSuccess(data.result);

        } else if (status === 'failed') {
            // Error
            this.handleError(data.error || 'Analysis failed');
        }
    }

    handleSuccess(result) {
        const progressBar = document.getElementById('progressBar');
        const progressStatus = document.getElementById('progressStatus');
        const progressDetails = document.getElementById('progressDetails');

        // Stop polling
        clearInterval(this.pollInterval);

        // Update to 100%
        progressBar.style.width = '100%';
        progressBar.textContent = '100%';
        progressBar.classList.remove('progress-bar-animated');
        progressBar.classList.add('bg-success');

        // Show success message
        const analyzed = result.analyzed || 0;
        const failed = result.failed || 0;
        const total = result.total || 0;

        progressStatus.innerHTML = `
            <i class="fas fa-check-circle text-success me-2"></i>
            <span>Analysis complete!</span>
        `;

        progressDetails.textContent = 
            `Successfully analyzed ${analyzed} of ${total} songs` +
            (failed > 0 ? ` (${failed} failed)` : '');

        // Call completion callback
        if (this.onComplete) {
            this.onComplete(result);
        }

        // Auto-close after 2 seconds
        setTimeout(() => {
            this.close();
            window.location.reload();
        }, 2000);
    }

    handleError(errorMessage) {
        const progressBar = document.getElementById('progressBar');
        const progressStatus = document.getElementById('progressStatus');
        const progressDetails = document.getElementById('progressDetails');

        // Stop polling
        clearInterval(this.pollInterval);

        // Show error
        progressBar.classList.remove('progress-bar-animated', 'progress-bar-striped');
        progressBar.classList.add('bg-danger');

        progressStatus.innerHTML = `
            <i class="fas fa-exclamation-circle text-danger me-2"></i>
            <span>Analysis failed</span>
        `;

        progressDetails.textContent = errorMessage;

        // Allow manual close after error
        setTimeout(() => {
            this.modal._element.setAttribute('data-bs-backdrop', 'true');
            this.modal._element.setAttribute('data-bs-keyboard', 'true');
        }, 1000);
    }

    close() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        if (this.modal) {
            this.modal.hide();
            // Remove modal element after animation
            setTimeout(() => {
                const modalElement = document.getElementById('progressModal');
                if (modalElement) {
                    modalElement.remove();
                }
            }, 500);
        }
    }
}

// Make available globally
window.ProgressModal = ProgressModal;

