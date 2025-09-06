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

    console.log('🔗 Binding event listeners for PlaylistAnalysis...');
    console.log('Button elements found:', {
      analyzeUnanalyzedBtn: !!analyzeUnanalyzedBtn,
      analyzePlaylistBtn: !!analyzePlaylistBtn,
      toggleViewBtn: !!toggleViewBtn
    });

    UIHelpers.safeAddEventListener(analyzeUnanalyzedBtn, 'click', () => {
      console.log('🎵 Analyze unanalyzed button clicked');
      this.startAnalysis('unanalyzed');
    });

    UIHelpers.safeAddEventListener(analyzePlaylistBtn, 'click', () => {
      console.log('📊 Analyze playlist button clicked');
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
    console.log(`🎵 Found ${songAnalysisButtons.length} song analysis buttons`);

    songAnalysisButtons.forEach((btn, index) => {
      UIHelpers.safeAddEventListener(btn, 'click', () => {
        const songId = btn.dataset.songId;
        const songTitle = btn.dataset.songTitle;
        const songArtist = btn.dataset.songArtist;

        console.log(`🎵 Song analysis button ${index + 1} clicked:`, {
          songId,
          songTitle,
          songArtist,
          button: btn
        });

        this.analyzeSingleSong(songId, songTitle, songArtist, btn);
      });
      console.log(`✅ Song analysis button ${index + 1} bound (ID: ${btn.dataset.songId})`);
    });
  }

  /**
     * Start playlist analysis (Admin only) - Uses workers for parallel processing
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
      console.log('Starting direct queue-free analysis...');
      this.isAnalysisInProgress = true;
      this.disableAnalysisButtons();

      // Show processing indicator
      UIHelpers.showProgress();
      UIHelpers.updateProgress(0, 'Starting analysis...', 'Preparing...');

      console.log('Calling apiService.startPlaylistAnalysis...');
      const response = await apiService.startPlaylistAnalysis(this.playlistId, analysisType);

      console.log('API response:', response);

      if (response.success) {
        // Begin progress polling against API endpoint to update in-page progress bar
        await this.pollPlaylistProgress();
      } else {
        throw new Error(response.message || 'Analysis failed');
      }
    } catch (error) {
      console.error('Error in startAnalysis:', error);
      UIHelpers.hideProgress();
      if (error.message.includes('Access denied')) {
        UIHelpers.showError('Access denied. Analysis is restricted to administrators.');
      } else {
        UIHelpers.showError(`Failed to complete analysis: ${error.message}`);
      }
      this.resetAnalysisState();
    }
  }
  /**
   * Poll playlist progress and update in-page progress UI
   */
  async pollPlaylistProgress () {
    const maxMinutes = 15;
    const endTime = Date.now() + maxMinutes * 60 * 1000;

    const tick = async () => {
      try {
        const status = await apiService.getPlaylistAnalysisStatus(this.playlistId);
        if (!status || status.success !== true) {
          UIHelpers.showError('Unable to track analysis progress');
          this.resetAnalysisState();
          return;
        }

        const progress = Math.round(status.progress || 0);
        const analyzed = status.analyzed_count || 0;
        const total = status.total_count || 0;
        const message = status.message || `${analyzed}/${total} songs analyzed`;

        UIHelpers.updateProgress(progress, message, `${analyzed}/${total} analyzed`);

        if (status.completed || progress >= 100) {
          UIHelpers.hideProgress();
          this.resetAnalysisState();
          setTimeout(() => window.location.reload(), 1000);
          return;
        }

        if (Date.now() < endTime) {
          setTimeout(tick, 5000);
        } else {
          UIHelpers.showError('Analysis is taking longer than expected. Please refresh to check status.');
          this.resetAnalysisState();
        }
      } catch (err) {
        UIHelpers.showError('Lost connection while tracking progress');
        this.resetAnalysisState();
      }
    };

    // kick off
    setTimeout(tick, 3000);
  }

  /**
   * Back-compat handler bound in some listeners
   */
  analyzePlaylist () {
    if (this.isAnalysisInProgress) {
      UIHelpers.showError('Analysis is already in progress');
      return;
    }
    this.startAnalysis('all');
  }



  /**
   * Enhanced polling for batch completion
   */
  async pollForBatchCompletion(totalSongs, batchesQueued, workersActive) {
    console.log(`Starting enhanced batch completion polling for ${totalSongs} songs...`);

    let attempts = 0;
    const maxAttempts = 30; // 30 * 10 seconds = 5 minutes max

    const checkCompletion = async () => {
      attempts++;
      console.log(`Batch completion check ${attempts}/${maxAttempts}`);

      try {
        // For simplified system, just reload page after reasonable time
        if (attempts >= maxAttempts) {
          UIHelpers.showAlert(`Batch analysis should be complete. Refreshing page to show results...`, 'info');
          setTimeout(() => window.location.reload(), 2000);
          return;
        }

        // Check again in 10 seconds (workers handle the processing)
        setTimeout(checkCompletion, 10000);

      } catch (error) {
        console.error('Error in batch completion polling:', error);
        this.resetAnalysisState();
      }
    };

    // Start checking after 20 seconds (give workers time to process)
    setTimeout(checkCompletion, 20000);
  }


  /**
     * Analyze a single song with progress tracking
     * @param {string} songId - Song ID
     * @param {string} songTitle - Song title
     * @param {string} songArtist - Song artist
     * @param {HTMLElement} button - Button element that triggered the analysis
     */
  async analyzeSingleSong (songId, songTitle, songArtist, button) {
    console.log('🎵 Starting single song analysis:', {
      songId, songTitle, songArtist
    });

    try {
      // Prevent double-clicks
      if (button.disabled) {
        console.log('⚠️ Button already disabled, ignoring click');
        return;
      }

      UIHelpers.toggleButtonLoading(button, true);
      console.log('🔄 Button set to loading state');

      // Show initial notification
      UIHelpers.showAlert(`Analysis started for "${songTitle}". Progress tracking enabled.`, 'info');
      console.log('✅ Initial notification shown');

      console.log('📡 Making API call to analyze song...');
      const response = await apiService.analyzeSong(songId);
      console.log('📡 API response received:', response);

      if (response.success) {
        console.log('🎯 Starting progress tracking...');

        // Start progress tracking with real-time updates
        this.startSongProgressTracking(songId, songTitle, button);
      } else {
        throw new Error(response.message || 'Failed to start song analysis');
      }
    } catch (error) {
      console.error('❌ Error analyzing song:', error);
      UIHelpers.showAlert(`Failed to analyze "${songTitle}": ${error.message}`, 'error');
      UIHelpers.toggleButtonLoading(button, false);
    }
  }

  /**
   * Start progress tracking for a single song
   */
  async startSongProgressTracking(songId, songTitle, button) {
    console.log('🎯 Starting song progress tracking for:', songId);

    const startTime = Date.now();
    let attempts = 0;
    const maxAttempts = 30; // 30 attempts * 2 seconds = 1 minute max

    const checkProgress = async () => {
      attempts++;
      console.log(`🔍 Progress check #${attempts} for song ${songId}`);

      try {
        const status = await apiService.getSongAnalysisStatus(songId);
        console.log('📊 Progress status:', status);

        if (status.completed) {
          console.log('✅ Analysis completed!');

          // Update button to success state
          button.innerHTML = '✓ Analyzed';
          button.className = 'btn btn-sm btn-success';
          button.disabled = true;

          // Update score column if results available
          if (status.result && status.result.score !== undefined) {
            this.updateSongScoreDisplay(songId, status.result);
          }

          // Show completion notification
          UIHelpers.showAlert(`Analysis completed for "${songTitle}"!`, 'success');

          return; // Stop polling
        }

        if (status.failed) {
          console.log('❌ Analysis failed');
          UIHelpers.toggleButtonLoading(button, false);
          UIHelpers.showAlert(`Analysis failed for "${songTitle}": ${status.error || 'Unknown error'}`, 'error');
          return; // Stop polling
        }

        // Continue polling if not complete and under max attempts
        if (attempts < maxAttempts) {
          console.log(`⏳ Analysis in progress, checking again in 2 seconds...`);
          setTimeout(checkProgress, 2000);
        } else {
          console.log('⏰ Max attempts reached, stopping progress tracking');
          UIHelpers.toggleButtonLoading(button, false);
          UIHelpers.showAlert(`Analysis for "${songTitle}" is taking longer than expected. Please refresh the page to check results.`, 'warning');
        }

      } catch (error) {
        console.error('❌ Error checking progress:', error);
        UIHelpers.toggleButtonLoading(button, false);
        UIHelpers.showAlert(`Error tracking progress for "${songTitle}": ${error.message}`, 'error');
      }
    };

    // Start checking progress after 3 seconds (give analysis time to start)
    setTimeout(checkProgress, 3000);
  }

  /**
   * Update song score display in the table
   */
  updateSongScoreDisplay(songId, result) {
    console.log('🎯 Updating score display for song:', songId, result);

    // Prefer card UI; fall back to table if present
    const songCard = document.querySelector(`.song-card[data-song-id="${songId}"]`);
    if (songCard) {
      // Update score circle text
      const circle = songCard.querySelector('.score-circle');
      if (circle && typeof result.score !== 'undefined') {
        const s = Math.round(result.score);
        circle.textContent = `${s}%`;
        // Update color classes based on standardized thresholds
        circle.classList.remove('score-green','score-yellow','score-red','bg-extreme','bg-high','bg-medium','bg-low');
        if (s >= 75) circle.classList.add('score-green');
        else if (s >= 50) circle.classList.add('score-yellow');
        else circle.classList.add('score-red');
      }

      // Update reason snippet if available
      const reasonElem = songCard.querySelector('.reason-snippet');
      if (reasonElem && (result.explanation || (result.concerns && result.concerns.length))) {
        const reason = result.explanation || result.concerns[0];
        reasonElem.textContent = `Reason: ${reason}`;
        reasonElem.setAttribute('title', reason);
      }
      return;
    }

    // Legacy table fallback
    const songRow = document.querySelector(`tr[data-song-id="${songId}"]`);
    if (!songRow) return;
    const scoreCell = songRow.querySelector('.score-cell');
    if (!scoreCell) return;
    if (result.score !== undefined) {
      const score = Math.round(result.score);
      const concernLevel = result.concern_level || 'unknown';
      const badgeClass = score >= 80 ? 'bg-success' : score >= 60 ? 'bg-warning' : 'bg-danger';
      scoreCell.innerHTML = `<span class="badge ${badgeClass} fs-6">${score}%</span><div class="small text-muted">${concernLevel}</div>`;
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

  init () {
    console.log('🎵 PlaylistAnalysis module initializing...', {
      playlistId: this.playlistId,
      options: this.options
    });

    this.bindEventListeners();
    this.initializeElements();
    console.log('✅ PlaylistAnalysis module fully initialized');
  }

  bindEventListeners () {
    console.log('🔗 Binding event listeners for PlaylistAnalysis...');

    // Bind playlist-level analysis button
    const analyzePlaylistBtn = document.querySelector('.analyze-playlist-btn');
    if (analyzePlaylistBtn) {
      analyzePlaylistBtn.addEventListener('click', (e) => {
        e.preventDefault();
        console.log('📊 Analyze playlist button clicked');
        this.analyzePlaylist();
      });
      console.log('✅ Playlist analysis button bound');
    }

    // Bind individual song analysis buttons
    const analyzeSongBtns = document.querySelectorAll('.analyze-song-btn');
    console.log(`🎵 Found ${analyzeSongBtns.length} song analysis buttons`);

    analyzeSongBtns.forEach((btn, index) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const songId = btn.dataset.songId;
        const songTitle = btn.dataset.songTitle;
        const songArtist = btn.dataset.songArtist;

        console.log(`🎵 Song analysis button ${index + 1} clicked:`, {
          songId,
          songTitle,
          songArtist,
          button: btn
        });

        this.analyzeSingleSong(songId, songTitle, songArtist, btn);
      });
      console.log(`✅ Song analysis button ${index + 1} bound (ID: ${btn.dataset.songId})`);
    });
  }
}
