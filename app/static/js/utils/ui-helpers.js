/**
 * UI Helper Utilities
 * Common functions for DOM manipulation and UI state management
 */
export class UIHelpers {
  /**
     * Show success message with auto-hide
     * @param {string} message - Success message to display
     * @param {HTMLElement} container - Container element for the message
     * @param {number} autoHideMs - Auto-hide timeout in milliseconds
     */
  static showSuccess (message, container = null, autoHideMs = 5000) {
    const errorElement = container || document.getElementById('errorMessage');
    if (errorElement) {
      errorElement.className = 'alert alert-success';
      errorElement.innerHTML = `<i class="fas fa-check-circle me-2"></i>${message}`;
      errorElement.style.display = 'block';

      // Auto-hide after specified time
      if (autoHideMs > 0) {
        setTimeout(() => {
          if (errorElement.className.includes('alert-success')) {
            errorElement.style.display = 'none';
          }
        }, autoHideMs);
      }
    }
  }

  /**
     * Show error message
     * @param {string} message - Error message to display
     * @param {HTMLElement} container - Container element for the message
     */
  static showError (message, container = null) {
    const errorElement = container || document.getElementById('errorMessage');
    if (errorElement) {
      errorElement.className = 'alert alert-danger';
      errorElement.innerHTML = `<i class="fas fa-exclamation-circle me-2"></i>${message}`;
      errorElement.style.display = 'block';
    }
  }

  /**
     * Hide message element
     * @param {HTMLElement} element - Element to hide
     */
  static hideMessage (element = null) {
    const messageElement = element || document.getElementById('errorMessage');
    if (messageElement) {
      messageElement.style.display = 'none';
    }
  }

  /**
     * Update progress bar with percentage and message
     * @param {number} percent - Progress percentage (0-100)
     * @param {string} message - Progress message
     * @param {string} currentItem - Currently processing item name
     */
  static updateProgress (percent, message, currentItem = '') {
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const analysisStatus = document.getElementById('analysisStatus');

    if (progressBar) {
      progressBar.style.width = `${percent}%`;
      progressBar.setAttribute('aria-valuenow', percent);
      progressBar.textContent = `${Math.round(percent)}%`;
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
        analysisStatus.textContent = currentItem || 'Processing...';
        analysisStatus.className = 'text-primary';
      } else {
        analysisStatus.textContent = 'Starting...';
        analysisStatus.className = 'text-muted';
      }
    }
  }

  /**
     * Show progress bar and reset to initial state
     */
  static showProgress () {
    console.log('UIHelpers.showProgress() called');
    
    // Fix: Show the main progress container #analysisProgress, not just .progress
    const progressContainer = document.getElementById('analysisProgress');
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');
    const analysisStatus = document.getElementById('analysisStatus');
    const errorMessage = document.getElementById('errorMessage');

    console.log('Progress elements found:', {
      progressContainer: !!progressContainer,
      progressBar: !!progressBar,
      progressText: !!progressText,
      progressPercent: !!progressPercent,
      analysisStatus: !!analysisStatus
    });

    // Show the main progress container
    if (progressContainer) {
      progressContainer.style.display = 'block';
      console.log('Progress container shown');
    } else {
      console.error('Progress container #analysisProgress not found!');
    }

    // Reset progress bar
    if (progressBar) {
      progressBar.style.width = '0%';
      progressBar.setAttribute('aria-valuenow', '0');
    }

    // Reset text elements
    if (progressText) {
      progressText.textContent = 'Starting...';
    }

    if (progressPercent) {
      progressPercent.textContent = '0%';
    }

    // Show and reset status
    if (analysisStatus) {
      analysisStatus.textContent = 'Preparing...';
      analysisStatus.className = 'text-muted';
      analysisStatus.style.display = 'block';
    }

    // Hide error messages
    if (errorMessage) {
      errorMessage.style.display = 'none';
      errorMessage.textContent = '';
    }
  }

  /**
     * Hide progress bar
     */
  static hideProgress () {
    // Fix: Hide the main progress container #analysisProgress, not just .progress
    const progressContainer = document.getElementById('analysisProgress');
    if (progressContainer) {
      progressContainer.style.display = 'none';
      console.log('Progress container hidden');
    }
  }

  /**
     * Toggle button loading state
     * @param {HTMLElement} button - Button element
     * @param {boolean} loading - Whether button is in loading state
     * @param {string} loadingText - Text to show when loading
     */
  static toggleButtonLoading (button, loading, loadingText = 'Loading...') {
    if (!button) return;

    const textSpan = button.querySelector('.analyze-btn-text') || button;
    const spinner = button.querySelector('.spinner-border');

    if (loading) {
      button.disabled = true;
      if (textSpan && textSpan !== button) {
        textSpan.classList.add('d-none');
      } else {
        button.setAttribute('data-original-text', button.innerHTML);
        button.innerHTML = loadingText;
      }
      if (spinner) {
        spinner.classList.remove('d-none');
      }
    } else {
      button.disabled = false;
      if (textSpan && textSpan !== button) {
        textSpan.classList.remove('d-none');
      } else {
        const originalText = button.getAttribute('data-original-text');
        if (originalText) {
          button.innerHTML = originalText;
        }
      }
      if (spinner) {
        spinner.classList.add('d-none');
      }
    }
  }

  /**
     * Get CSRF token from meta tag
     * @returns {string|null} CSRF token
     */
  static getCSRFToken () {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.content : null;
  }

  /**
     * Safely get element by ID with error logging
     * @param {string} id - Element ID
     * @returns {HTMLElement|null} Element or null if not found
     */
  static safeGetElement (id) {
    try {
      return document.getElementById(id);
    } catch (error) {
      return null;
    }
  }

  /**
     * Add event listener with error handling
     * @param {HTMLElement} element - Element to add listener to
     * @param {string} event - Event type
     * @param {Function} handler - Event handler function
     */
  static safeAddEventListener (element, event, handler) {
    if (element && typeof handler === 'function') {
      try {
        element.addEventListener(event, handler);
      } catch (error) {
        console.warn('Failed to add event listener:', error);
      }
    }
  }
}
