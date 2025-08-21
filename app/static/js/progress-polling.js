/**
 * Smart Progress Polling Utility
 *
 * Provides efficient polling for job progress updates with adaptive intervals,
 * error handling, and automatic cleanup.
 */

class ProgressPoller {
    constructor(options = {}) {
        this.baseUrl = options.baseUrl || '/api';
        this.initialInterval = options.initialInterval || 1000; // 1 second initially
        this.maxInterval = options.maxInterval || 5000; // Max 5 seconds
        this.errorBackoffMultiplier = options.errorBackoffMultiplier || 2;
        this.maxErrorRetries = options.maxErrorRetries || 3;

        // Active polling jobs
        this.activePolls = new Map();

        // Event callbacks
        this.callbacks = {
            progress: new Map(),
            complete: new Map(),
            error: new Map()
        };
    }

    /**
     * Start polling for a specific job
     * @param {string} jobId - The job ID to poll
     * @param {Object} callbacks - Callback functions for events
     */
    startPolling(jobId, callbacks = {}) {
        // Stop existing polling for this job
        this.stopPolling(jobId);

        // Register callbacks
        if (callbacks.onProgress) this.callbacks.progress.set(jobId, callbacks.onProgress);
        if (callbacks.onComplete) this.callbacks.complete.set(jobId, callbacks.onComplete);
        if (callbacks.onError) this.callbacks.error.set(jobId, callbacks.onError);

        // Initialize polling state
        const pollState = {
            jobId,
            interval: this.initialInterval,
            errorCount: 0,
            startTime: Date.now(),
            timeoutId: null,
            isActive: true
        };

        this.activePolls.set(jobId, pollState);

        // Start the polling loop
        this._pollJob(pollState);

        console.log(`🔄 Started polling for job ${jobId}`);
    }

    /**
     * Stop polling for a specific job
     * @param {string} jobId - The job ID to stop polling
     */
    stopPolling(jobId) {
        const pollState = this.activePolls.get(jobId);
        if (pollState) {
            pollState.isActive = false;
            if (pollState.timeoutId) {
                clearTimeout(pollState.timeoutId);
            }
            this.activePolls.delete(jobId);

            // Clean up callbacks
            this.callbacks.progress.delete(jobId);
            this.callbacks.complete.delete(jobId);
            this.callbacks.error.delete(jobId);

            console.log(`⏹️ Stopped polling for job ${jobId}`);
        }
    }

    /**
     * Stop all active polling
     */
    stopAllPolling() {
        const jobIds = Array.from(this.activePolls.keys());
        jobIds.forEach(jobId => this.stopPolling(jobId));
        console.log('⏹️ Stopped all polling');
    }

    /**
     * Get status of all active polls
     */
    getActivePolls() {
        const status = {};
        for (const [jobId, state] of this.activePolls) {
            status[jobId] = {
                interval: state.interval,
                errorCount: state.errorCount,
                duration: Date.now() - state.startTime,
                isActive: state.isActive
            };
        }
        return status;
    }

    /**
     * Internal polling function
     * @param {Object} pollState - The polling state object
     */
    async _pollJob(pollState) {
        if (!pollState.isActive) return;

        try {
            const response = await fetch(`${this.baseUrl}/progress/${pollState.jobId}`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            if (data.success) {
                const progress = data.progress;

                // Reset error count on successful response
                pollState.errorCount = 0;

                // Call progress callback
                const progressCallback = this.callbacks.progress.get(pollState.jobId);
                if (progressCallback) {
                    progressCallback(progress);
                }

                // Check if job is complete
                if (this._isJobComplete(progress)) {
                    const completeCallback = this.callbacks.complete.get(pollState.jobId);
                    if (completeCallback) {
                        completeCallback(progress);
                    }
                    this.stopPolling(pollState.jobId);
                    return;
                }

                // Adapt polling interval based on progress and time
                this._adaptPollingInterval(pollState, progress);

            } else {
                throw new Error(data.error || 'Unknown API error');
            }

        } catch (error) {
            console.warn(`⚠️ Polling error for job ${pollState.jobId}:`, error.message);

            pollState.errorCount++;

            // Call error callback
            const errorCallback = this.callbacks.error.get(pollState.jobId);
            if (errorCallback) {
                errorCallback(error, pollState.errorCount);
            }

            // Stop polling if too many errors
            if (pollState.errorCount >= this.maxErrorRetries) {
                console.error(`❌ Max retries exceeded for job ${pollState.jobId}, stopping polling`);
                this.stopPolling(pollState.jobId);
                return;
            }

            // Increase interval on error
            pollState.interval = Math.min(
                pollState.interval * this.errorBackoffMultiplier,
                this.maxInterval
            );
        }

        // Schedule next poll if still active
        if (pollState.isActive) {
            pollState.timeoutId = setTimeout(() => {
                this._pollJob(pollState);
            }, pollState.interval);
        }
    }

    /**
     * Check if a job is complete
     * @param {Object} progress - Progress data
     * @returns {boolean} True if job is complete
     */
    _isJobComplete(progress) {
        return progress.progress >= 1.0 ||
               progress.current_step === 'complete' ||
               ['completed', 'failed', 'cancelled'].includes(progress.status);
    }

    /**
     * Adapt polling interval based on progress and elapsed time
     * @param {Object} pollState - The polling state
     * @param {Object} progress - Current progress data
     */
    _adaptPollingInterval(pollState, progress) {
        const elapsedSeconds = (Date.now() - pollState.startTime) / 1000;
        const progressPercent = progress.progress || 0;

        // Fast polling for first 10 seconds or if progress is moving quickly
        if (elapsedSeconds < 10 || progressPercent < 0.1) {
            pollState.interval = this.initialInterval;
        }
        // Medium polling for active progress
        else if (progressPercent < 0.9) {
            pollState.interval = Math.min(this.initialInterval * 2, 3000);
        }
        // Slower polling when nearly complete
        else {
            pollState.interval = Math.min(this.initialInterval * 3, this.maxInterval);
        }
    }
}

/**
 * Convenience function to poll a single job with simple callbacks
 * @param {string} jobId - Job ID to poll
 * @param {Object} options - Options and callbacks
 */
function pollJobProgress(jobId, options = {}) {
    const poller = new ProgressPoller(options);

    return new Promise((resolve, reject) => {
        poller.startPolling(jobId, {
            onProgress: options.onProgress || (() => {}),
            onComplete: (progress) => {
                if (options.onComplete) options.onComplete(progress);
                resolve(progress);
            },
            onError: (error, retryCount) => {
                if (options.onError) options.onError(error, retryCount);
                if (retryCount >= (options.maxErrorRetries || 3)) {
                    reject(error);
                }
            }
        });
    });
}

/**
 * Utility to poll multiple jobs simultaneously
 * @param {Array} jobIds - Array of job IDs to poll
 * @param {Object} options - Options and callbacks
 */
function pollMultipleJobs(jobIds, options = {}) {
    const poller = new ProgressPoller(options);
    const results = {};

    return new Promise((resolve, reject) => {
        let completedJobs = 0;
        let hasError = false;

        jobIds.forEach(jobId => {
            poller.startPolling(jobId, {
                onProgress: (progress) => {
                    results[jobId] = progress;
                    if (options.onProgress) {
                        options.onProgress(jobId, progress, results);
                    }
                },
                onComplete: (progress) => {
                    results[jobId] = progress;
                    completedJobs++;

                    if (options.onJobComplete) {
                        options.onJobComplete(jobId, progress);
                    }

                    if (completedJobs === jobIds.length) {
                        if (options.onAllComplete) options.onAllComplete(results);
                        resolve(results);
                    }
                },
                onError: (error, retryCount) => {
                    if (options.onError) options.onError(jobId, error, retryCount);
                    if (retryCount >= (options.maxErrorRetries || 3) && !hasError) {
                        hasError = true;
                        reject(error);
                    }
                }
            });
        });
    });
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ProgressPoller, pollJobProgress, pollMultipleJobs };
} else {
    // Browser global
    window.ProgressPoller = ProgressPoller;
    window.pollJobProgress = pollJobProgress;
    window.pollMultipleJobs = pollMultipleJobs;
}
