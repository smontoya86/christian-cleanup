/**
 * Playlist Analysis Module
 * Handles playlist and song analysis operations
 */
import { apiService } from '../services/api-service.js';
import { UIHelpers } from '../utils/ui-helpers.js';

export class PlaylistAnalysis {
  /**
     * Create playlist analysis instance
     * @param {string} playlistId - Playlist ID
     */
  constructor (playlistId) {
    this.playlistId = playlistId;
    this.isAnalysisInProgress = false;
    this.pollInterval = null;

    this.initializeElements();
    this.bindEvents();
  }

  /**
     * Initialize DOM element references
     */
  initializeElements () {
    this.elements = {
      analyzeUnanalyzedBtn: UIHelpers.safeGetElement('analyzeUnanalyzedBtn'),
      analyzePlaylistBtn: UIHelpers.safeGetElement('analyzePlaylistBtn'),
      toggleViewBtn: UIHelpers.safeGetElement('toggleViewBtn'),
      songListView: UIHelpers.safeGetElement('song-list-view'),
      gridView: UIHelpers.safeGetElement('song-grid-view'),
      progressContainer: document.querySelector('#analysisProgress'),
      errorContainer: UIHelpers.safeGetElement('errorMessage')
    };
  }

  /**
     * Bind event listeners
     */
  bindEvents () {
    const { analyzeUnanalyzedBtn, analyzePlaylistBtn, toggleViewBtn } = this.elements;

    console.log('PlaylistAnalysis.bindEvents() called');
    console.log('Button elements found:', {
      analyzeUnanalyzedBtn: !!analyzeUnanalyzedBtn,
      analyzePlaylistBtn: !!analyzePlaylistBtn,
      toggleViewBtn: !!toggleViewBtn
    });

    UIHelpers.safeAddEventListener(analyzeUnanalyzedBtn, 'click', () => {
      console.log('Analyze unanalyzed button clicked');
      this.startAnalysis('unanalyzed');
    });

    UIHelpers.safeAddEventListener(analyzePlaylistBtn, 'click', () => {
      console.log('Analyze playlist button clicked');
      if (confirm('This will re-analyze all songs in the playlist. Are you sure?')) {
        console.log('User confirmed re-analysis');
        this.startAnalysis('all');
      } else {
        console.log('User cancelled re-analysis');
      }
    });

    UIHelpers.safeAddEventListener(toggleViewBtn, 'click', () => {
      this.toggleView();
    });

    // Bind individual song analysis buttons
    this.bindSongAnalysisButtons();
  }

  /**
     * Bind individual song analysis buttons
     */
  bindSongAnalysisButtons () {
    const songAnalysisButtons = document.querySelectorAll('.analyze-song-btn');
    songAnalysisButtons.forEach(button => {
      UIHelpers.safeAddEventListener(button, 'click', () => {
        const songId = button.dataset.songId;
        const songTitle = button.dataset.songTitle;
        const songArtist = button.dataset.songArtist;

        this.analyzeSingleSong(songId, songTitle, songArtist, button);
      });
    });
  }

  /**
     * Start playlist analysis
     * @param {string} analysisType - Type of analysis ('all' or 'unanalyzed')
     */
  async startAnalysis (analysisType) {
    console.log(`PlaylistAnalysis.startAnalysis('${analysisType}') called`);
    console.log('Current state:', {
      playlistId: this.playlistId,
      isAnalysisInProgress: this.isAnalysisInProgress
    });

    if (!this.playlistId) {
      console.error('No playlist ID available');
      UIHelpers.showError('No playlist ID available');
      return;
    }

    if (this.isAnalysisInProgress) {
      console.warn('Analysis is already in progress');
      UIHelpers.showError('Analysis is already in progress');
      return;
    }

    try {
      console.log('Starting analysis process...');
      this.isAnalysisInProgress = true;
      this.disableAnalysisButtons();
      
      console.log('Calling UIHelpers.showProgress()...');
      UIHelpers.showProgress();
      
      console.log('Updating progress to 0%...');
      UIHelpers.updateProgress(0, 'Starting analysis...');

      console.log('Calling apiService.startPlaylistAnalysis...');
      const response = await apiService.startPlaylistAnalysis(this.playlistId, analysisType);
      
      console.log('API response:', response);

      if (response.success) {
        console.log('Analysis started successfully, beginning polling...');
        UIHelpers.updateProgress(10, 'Analysis started successfully...');
        this.pollAnalysisStatus();
      } else {
        throw new Error(response.message || 'Analysis failed to start');
      }
    } catch (error) {
      console.error('Error in startAnalysis:', error);
      UIHelpers.showError(`Failed to start analysis: ${error.message}`);
      this.resetAnalysisState();
    }
  }

  /**
     * Poll for analysis status updates
     */
  async pollAnalysisStatus () {
    try {
      await apiService.pollForCompletion(
        () => apiService.getPlaylistAnalysisStatus(this.playlistId),
        {
          maxAttempts: 200,
          initialInterval: 3000,
          onProgress: (status) => this.handleAnalysisProgress(status)
        }
      );

      // Analysis completed successfully
      UIHelpers.updateProgress(100, 'Analysis complete!');
      UIHelpers.showSuccess('Analysis completed successfully!');

      // Reload page to show results
      setTimeout(() => window.location.reload(), 1500);
    } catch (error) {
      UIHelpers.showError(`Analysis failed: ${error.message}`);
      this.resetAnalysisState();
    }
  }

  /**
     * Handle analysis progress updates
     * @param {Object} status - Analysis status response
     */
  handleAnalysisProgress (status) {
    if (status.progress !== undefined) {
      const message = status.message || 'Processing...';
      const currentItem = status.current_song || '';
      UIHelpers.updateProgress(status.progress, message, currentItem);
    }
  }

  /**
     * Analyze a single song
     * @param {string} songId - Song ID
     * @param {string} songTitle - Song title
     * @param {string} songArtist - Song artist
     * @param {HTMLElement} button - Button element that triggered the analysis
     */
  async analyzeSingleSong (songId, songTitle, songArtist, button) {
    try {
      UIHelpers.toggleButtonLoading(button, true);

      const response = await apiService.analyzeSong(songId);

      if (response.success) {
        // Poll for song analysis completion
        await apiService.pollForCompletion(
          () => apiService.getSongAnalysisStatus(songId),
          {
            maxAttempts: 60,
            initialInterval: 3000
          }
        );

        // Reload page to show updated analysis
        window.location.reload();
      } else {
        throw new Error(response.message || 'Failed to start song analysis');
      }
    } catch (error) {
      UIHelpers.toggleButtonLoading(button, false);
      UIHelpers.showError(`Failed to analyze "${songTitle}": ${error.message}`);
    }
  }

  /**
     * Toggle between list and grid view
     */
  toggleView () {
    const { songListView, gridView, toggleViewBtn } = this.elements;

    if (!songListView || !gridView || !toggleViewBtn) return;

    const isGridView = !songListView.classList.contains('d-none');

    if (isGridView) {
      // Switch to grid view
      songListView.classList.add('d-none');
      gridView.style.display = 'block';
      toggleViewBtn.innerHTML = '<i class="fas fa-list me-1"></i> Switch to List View';

      // Lazy load grid view if empty
      if (gridView.children.length === 0) {
        this.loadGridView();
      }
    } else {
      // Switch to list view
      songListView.classList.remove('d-none');
      gridView.style.display = 'none';
      toggleViewBtn.innerHTML = '<i class="fas fa-th-large me-1"></i> Switch to Grid View';
    }
  }

  /**
     * Load grid view content (placeholder for future implementation)
     */
  loadGridView () {
    // Grid view is now populated by server-side rendering
    // This method is kept for future enhancement if needed
  }

  /**
     * Update song status in the UI
     * @param {string} songId - Song ID
     * @param {Object} status - Status object
     */
  updateSongStatus (songId, status) {
    const songRow = document.querySelector(`tr[data-song-id="${songId}"]`);
    if (!songRow) return;

    const statusCell = songRow.querySelector('.status-cell');
    const scoreCell = songRow.querySelector('.score-cell');
    const actionsCell = songRow.querySelector('.actions-cell');

    if (statusCell) {
      const badge = document.createElement('span');
      badge.className = `badge ${status.is_analyzing ? 'bg-warning' : 'bg-success'}`;
      badge.textContent = status.display_message || (status.is_analyzing ? 'Analyzing...' : 'Analyzed');

      statusCell.innerHTML = '';
      statusCell.appendChild(badge);
    }

    if (scoreCell && status.score !== undefined) {
      scoreCell.textContent = status.score !== null ? `${status.score}%` : '-';
    }

    if (actionsCell) {
      const analyzeBtn = actionsCell.querySelector('.analyze-song-btn');
      if (analyzeBtn) {
        UIHelpers.toggleButtonLoading(analyzeBtn, status.is_analyzing);
      }
    }
  }

  /**
     * Update overall score display
     * @param {Object|number} score - Score object or numeric value
     */
  updateOverallScore (score) {
    const scoreElement = UIHelpers.safeGetElement('overall-score');
    if (!scoreElement) return;

    const scoreValue = (typeof score === 'object' && score !== null)
      ? (score.christian_score || score.score || 0)
      : (score || 0);

    scoreElement.textContent = scoreValue !== null ? `${Math.round(scoreValue)}%` : 'N/A';

    // Update color based on score
    scoreElement.className = scoreValue >= 70
      ? 'text-success'
      : scoreValue >= 40 ? 'text-warning' : 'text-danger';
  }

  /**
     * Disable analysis buttons during processing
     */
  disableAnalysisButtons () {
    const { analyzeUnanalyzedBtn, analyzePlaylistBtn } = this.elements;
    if (analyzeUnanalyzedBtn) analyzeUnanalyzedBtn.disabled = true;
    if (analyzePlaylistBtn) analyzePlaylistBtn.disabled = true;
  }

  /**
     * Enable analysis buttons after processing
     */
  enableAnalysisButtons () {
    const { analyzeUnanalyzedBtn, analyzePlaylistBtn } = this.elements;
    if (analyzeUnanalyzedBtn) analyzeUnanalyzedBtn.disabled = false;
    if (analyzePlaylistBtn) analyzePlaylistBtn.disabled = false;
  }

  /**
     * Reset analysis state to initial condition
     */
  resetAnalysisState () {
    this.isAnalysisInProgress = false;
    this.enableAnalysisButtons();
    UIHelpers.hideProgress();

    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  /**
     * Cleanup resources
     */
  destroy () {
    this.resetAnalysisState();
  }
}
