/**
 * Smart Polling Tests
 * 
 * Tests for the progress polling functionality
 */

// Mock fetch for testing
global.fetch = jest.fn();

// Import the polling library
const { ProgressPoller, pollJobProgress, pollMultipleJobs } = require('../../app/static/js/progress-polling.js');

describe('ProgressPoller', () => {
    let poller;
    
    beforeEach(() => {
        poller = new ProgressPoller({
            initialInterval: 100, // Fast polling for tests
            maxInterval: 500
        });
        
        // Clear all mocks
        fetch.mockClear();
        
        // Mock successful response by default
        fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                success: true,
                progress: {
                    progress: 0.5,
                    current_step: 'analyzing',
                    eta_seconds: 30,
                    status: 'in_progress'
                }
            })
        });
    });
    
    afterEach(() => {
        // Clean up any active polling
        poller.stopAllPolling();
    });

    test('should create poller with default options', () => {
        const defaultPoller = new ProgressPoller();
        expect(defaultPoller.baseUrl).toBe('/api');
        expect(defaultPoller.initialInterval).toBe(1000);
        expect(defaultPoller.maxInterval).toBe(5000);
    });

    test('should start polling for a job', async () => {
        const onProgress = jest.fn();
        const onComplete = jest.fn();
        
        poller.startPolling('test-job-123', {
            onProgress,
            onComplete
        });
        
        expect(poller.activePolls.has('test-job-123')).toBe(true);
        
        // Wait for first poll
        await new Promise(resolve => setTimeout(resolve, 150));
        
        expect(fetch).toHaveBeenCalledWith('/api/progress/test-job-123');
        expect(onProgress).toHaveBeenCalledWith({
            progress: 0.5,
            current_step: 'analyzing',
            eta_seconds: 30,
            status: 'in_progress'
        });
    });

    test('should stop polling when job completes', async () => {
        const onComplete = jest.fn();
        
        // Mock completed job response
        fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                success: true,
                progress: {
                    progress: 1.0,
                    current_step: 'complete',
                    status: 'completed'
                }
            })
        });
        
        poller.startPolling('test-job-complete', {
            onComplete
        });
        
        // Wait for poll
        await new Promise(resolve => setTimeout(resolve, 150));
        
        expect(onComplete).toHaveBeenCalled();
        expect(poller.activePolls.has('test-job-complete')).toBe(false);
    });

    test('should handle polling errors with retry', async () => {
        const onError = jest.fn();
        
        // Mock error response
        fetch.mockRejectedValue(new Error('Network error'));
        
        poller.startPolling('test-job-error', {
            onError
        });
        
        // Wait for error
        await new Promise(resolve => setTimeout(resolve, 150));
        
        expect(onError).toHaveBeenCalledWith(
            expect.any(Error),
            1 // First retry
        );
    });

    test('should stop polling after max retries', async () => {
        const onError = jest.fn();
        
        // Create poller with low retry limit
        const testPoller = new ProgressPoller({
            initialInterval: 50,
            maxErrorRetries: 2
        });
        
        // Mock error response
        fetch.mockRejectedValue(new Error('Network error'));
        
        testPoller.startPolling('test-job-max-errors', {
            onError
        });
        
        // Wait for multiple retries
        await new Promise(resolve => setTimeout(resolve, 300));
        
        expect(onError).toHaveBeenCalledTimes(2);
        expect(testPoller.activePolls.has('test-job-max-errors')).toBe(false);
        
        testPoller.stopAllPolling();
    });

    test('should adapt polling intervals based on progress', () => {
        const pollState = {
            interval: 1000,
            startTime: Date.now() - 5000 // 5 seconds ago
        };
        
        // Test fast polling for early progress
        poller._adaptPollingInterval(pollState, { progress: 0.05 });
        expect(pollState.interval).toBe(poller.initialInterval);
        
        // Test medium polling for mid progress
        poller._adaptPollingInterval(pollState, { progress: 0.5 });
        expect(pollState.interval).toBe(poller.initialInterval * 2);
        
        // Test slower polling for near completion
        poller._adaptPollingInterval(pollState, { progress: 0.95 });
        expect(pollState.interval).toBe(poller.initialInterval * 3);
    });

    test('should detect job completion correctly', () => {
        expect(poller._isJobComplete({ progress: 1.0 })).toBe(true);
        expect(poller._isJobComplete({ current_step: 'complete' })).toBe(true);
        expect(poller._isJobComplete({ status: 'completed' })).toBe(true);
        expect(poller._isJobComplete({ status: 'failed' })).toBe(true);
        expect(poller._isJobComplete({ progress: 0.5, status: 'in_progress' })).toBe(false);
    });

    test('should stop specific job polling', () => {
        poller.startPolling('job1', {});
        poller.startPolling('job2', {});
        
        expect(poller.activePolls.size).toBe(2);
        
        poller.stopPolling('job1');
        
        expect(poller.activePolls.size).toBe(1);
        expect(poller.activePolls.has('job1')).toBe(false);
        expect(poller.activePolls.has('job2')).toBe(true);
    });

    test('should stop all polling', () => {
        poller.startPolling('job1', {});
        poller.startPolling('job2', {});
        poller.startPolling('job3', {});
        
        expect(poller.activePolls.size).toBe(3);
        
        poller.stopAllPolling();
        
        expect(poller.activePolls.size).toBe(0);
    });

    test('should get active polls status', () => {
        poller.startPolling('job1', {});
        
        const status = poller.getActivePolls();
        
        expect(status).toHaveProperty('job1');
        expect(status.job1).toHaveProperty('interval');
        expect(status.job1).toHaveProperty('errorCount');
        expect(status.job1).toHaveProperty('duration');
        expect(status.job1).toHaveProperty('isActive');
    });
});

describe('Convenience Functions', () => {
    beforeEach(() => {
        fetch.mockClear();
        
        // Mock successful response
        fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                success: true,
                progress: {
                    progress: 1.0,
                    current_step: 'complete',
                    status: 'completed'
                }
            })
        });
    });

    test('pollJobProgress should resolve when job completes', async () => {
        const onProgress = jest.fn();
        
        const result = await pollJobProgress('test-job', {
            onProgress,
            initialInterval: 50
        });
        
        expect(result).toEqual({
            progress: 1.0,
            current_step: 'complete',
            status: 'completed'
        });
        expect(onProgress).toHaveBeenCalled();
    });

    test('pollMultipleJobs should handle multiple jobs', async () => {
        const onProgress = jest.fn();
        const onJobComplete = jest.fn();
        
        const results = await pollMultipleJobs(['job1', 'job2'], {
            onProgress,
            onJobComplete,
            initialInterval: 50
        });
        
        expect(results).toHaveProperty('job1');
        expect(results).toHaveProperty('job2');
        expect(onJobComplete).toHaveBeenCalledTimes(2);
    });

    test('pollJobProgress should reject on max errors', async () => {
        // Mock error response
        fetch.mockRejectedValue(new Error('Network error'));
        
        await expect(pollJobProgress('test-job', {
            initialInterval: 50,
            maxErrorRetries: 1
        })).rejects.toThrow('Network error');
    });
});

describe('Error Handling', () => {
    let poller;
    
    beforeEach(() => {
        poller = new ProgressPoller({
            initialInterval: 50,
            maxErrorRetries: 2
        });
        fetch.mockClear();
    });
    
    afterEach(() => {
        poller.stopAllPolling();
    });

    test('should handle HTTP errors', async () => {
        const onError = jest.fn();
        
        // Mock HTTP error
        fetch.mockResolvedValue({
            ok: false,
            status: 404,
            statusText: 'Not Found'
        });
        
        poller.startPolling('test-job', { onError });
        
        await new Promise(resolve => setTimeout(resolve, 100));
        
        expect(onError).toHaveBeenCalledWith(
            expect.objectContaining({
                message: expect.stringContaining('HTTP 404')
            }),
            1
        );
    });

    test('should handle API errors', async () => {
        const onError = jest.fn();
        
        // Mock API error response
        fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                success: false,
                error: 'Job not found'
            })
        });
        
        poller.startPolling('test-job', { onError });
        
        await new Promise(resolve => setTimeout(resolve, 100));
        
        expect(onError).toHaveBeenCalledWith(
            expect.objectContaining({
                message: 'Job not found'
            }),
            1
        );
    });

    test('should increase interval on errors', async () => {
        // Mock error response
        fetch.mockRejectedValue(new Error('Network error'));
        
        const pollState = {
            interval: 100,
            errorCount: 0
        };
        
        poller.startPolling('test-job', {});
        
        // Simulate error handling
        pollState.errorCount = 1;
        pollState.interval = Math.min(
            pollState.interval * poller.errorBackoffMultiplier,
            poller.maxInterval
        );
        
        expect(pollState.interval).toBe(200); // 100 * 2
    });
});

describe('Integration Scenarios', () => {
    beforeEach(() => {
        fetch.mockClear();
    });

    test('should handle song analysis progress', async () => {
        const progressSteps = [
            { progress: 0.1, current_step: 'starting' },
            { progress: 0.3, current_step: 'fetching_lyrics' },
            { progress: 0.7, current_step: 'analyzing' },
            { progress: 1.0, current_step: 'complete' }
        ];
        
        let stepIndex = 0;
        fetch.mockImplementation(() => {
            const step = progressSteps[stepIndex++] || progressSteps[progressSteps.length - 1];
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve({
                    success: true,
                    progress: step
                })
            });
        });
        
        const progressUpdates = [];
        
        const result = await pollJobProgress('song-analysis', {
            initialInterval: 50,
            onProgress: (progress) => {
                progressUpdates.push(progress.current_step);
            }
        });
        
        expect(progressUpdates).toContain('starting');
        expect(progressUpdates).toContain('fetching_lyrics');
        expect(progressUpdates).toContain('analyzing');
        expect(result.current_step).toBe('complete');
    });

    test('should handle playlist analysis with metadata', async () => {
        fetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                success: true,
                progress: {
                    progress: 0.6,
                    current_step: 'analyzing',
                    metadata: {
                        total_songs: 10,
                        processed_songs: 6,
                        current_song: {
                            id: 'song123',
                            title: 'Test Song',
                            artist: 'Test Artist'
                        },
                        song_progress: 0.8
                    }
                }
            })
        });
        
        const metadataUpdates = [];
        
        await pollJobProgress('playlist-analysis', {
            initialInterval: 50,
            onProgress: (progress) => {
                if (progress.metadata) {
                    metadataUpdates.push(progress.metadata);
                }
            }
        });
        
        expect(metadataUpdates.length).toBeGreaterThan(0);
        expect(metadataUpdates[0]).toHaveProperty('total_songs', 10);
        expect(metadataUpdates[0]).toHaveProperty('processed_songs', 6);
        expect(metadataUpdates[0].current_song).toHaveProperty('title', 'Test Song');
    });
}); 