/**
 * API Service
 * Handles all HTTP requests to the backend API with consistent error handling
 */
export class ApiService {
  /**
     * Create API service instance
     * @param {string} baseUrl - Base URL for API requests
     */
  constructor (baseUrl = '') {
    this.baseUrl = baseUrl;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    };
  }

  /**
     * Get CSRF token for requests
     * @returns {string|null} CSRF token
     */
  getCSRFToken () {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.content : null;
  }

  /**
     * Build headers with CSRF token
     * @param {Object} additionalHeaders - Additional headers to include
     * @returns {Object} Headers object
     */
  buildHeaders (additionalHeaders = {}) {
    const headers = { ...this.defaultHeaders, ...additionalHeaders };
    const csrfToken = this.getCSRFToken();
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
    return headers;
  }

  /**
     * Make HTTP request with error handling
     * @param {string} url - Request URL
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} Response data
     */
  async makeRequest (url, options = {}) {
    try {
      const finalUrl = url.startsWith('http') ? url : `${this.baseUrl}${url}`;
      const finalOptions = {
        credentials: 'same-origin',
        ...options,
        headers: this.buildHeaders(options.headers || {})
      };

      const response = await fetch(finalUrl, finalOptions);

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      throw new Error(`API request failed: ${error.message}`);
    }
  }

  /**
     * Make GET request
     * @param {string} url - Request URL
     * @param {Object} headers - Additional headers
     * @returns {Promise<Object>} Response data
     */
  async get (url, headers = {}) {
    return this.makeRequest(url, {
      method: 'GET',
      headers
    });
  }

  /**
     * Make POST request
     * @param {string} url - Request URL
     * @param {Object} data - Request body data
     * @param {Object} headers - Additional headers
     * @returns {Promise<Object>} Response data
     */
  async post (url, data = {}, headers = {}) {
    return this.makeRequest(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(data)
    });
  }

  /**
     * Make PUT request
     * @param {string} url - Request URL
     * @param {Object} data - Request body data
     * @param {Object} headers - Additional headers
     * @returns {Promise<Object>} Response data
     */
  async put (url, data = {}, headers = {}) {
    return this.makeRequest(url, {
      method: 'PUT',
      headers,
      body: JSON.stringify(data)
    });
  }

  /**
     * Make DELETE request
     * @param {string} url - Request URL
     * @param {Object} headers - Additional headers
     * @returns {Promise<Object>} Response data
     */
  async delete (url, headers = {}) {
    return this.makeRequest(url, {
      method: 'DELETE',
      headers
    });
  }

  /**
     * Start playlist analysis (Admin only)
     * @param {string} playlistId - Playlist ID
     * @param {string} analysisType - Type of analysis ('all' or 'unanalyzed')
     * @returns {Promise<Object>} Analysis start response
     */
  async startPlaylistAnalysis (playlistId, analysisType = 'all') {
    if (!playlistId) {
      throw new Error('Playlist ID is required');
    }

    // Use the simplified admin-only endpoint with cache busting
    const timestamp = Date.now();
    const endpoint = `/analyze_playlist/${playlistId}?t=${timestamp}`;
    console.log(`🚨 Making request to: ${endpoint}`);

    // Add cache-busting headers
    const cacheHeaders = {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0'
    };

    return this.post(endpoint, {}, cacheHeaders);
  }

  /**
     * Get playlist analysis status
     * @param {string} playlistId - Playlist ID
     * @returns {Promise<Object>} Analysis status response
     */
  async getPlaylistAnalysisStatus (playlistId, sinceEpochSeconds = null) {
    if (!playlistId) {
      throw new Error('Playlist ID is required');
    }

    const qs = sinceEpochSeconds ? `?since=${encodeURIComponent(sinceEpochSeconds)}` : '';
    return this.get(`/api/playlists/${playlistId}/analysis-status${qs}`);
  }

  /**
     * Analyze single song
     * @param {string} songId - Song ID
     * @returns {Promise<Object>} Analysis response
     */
  async analyzeSong (songId) {
    if (!songId) {
      throw new Error('Song ID is required');
    }

    return this.post(`/api/songs/${songId}/analyze`);
  }

  /**
     * Get song analysis status
     * @param {string} songId - Song ID
     * @returns {Promise<Object>} Song analysis status
     */
  async getSongAnalysisStatus (songId) {
    if (!songId) {
      throw new Error('Song ID is required');
    }

    return this.get(`/api/songs/${songId}/analysis-status`);
  }

  /**
     * Poll for completion with exponential backoff
     * @param {Function} statusCheckFn - Function that returns status check promise
     * @param {Object} options - Polling options
     * @returns {Promise<Object>} Final status when complete
     */
  async pollForCompletion (statusCheckFn, options = {}) {
    const {
      maxAttempts = 200,
      initialInterval = 1000,
      maxInterval = 10000,
      backoffFactor = 1.5,
      onProgress = null
    } = options;

    let attempts = 0;
    let interval = initialInterval;

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          attempts++;
          const status = await statusCheckFn();

          if (onProgress) {
            onProgress(status, attempts);
          }

          if (status.success && (status.completed || status.has_analysis)) {
            resolve(status);
            return;
          }

          if (status.error || attempts >= maxAttempts) {
            reject(new Error(status.message || 'Polling timed out'));
            return;
          }

          // Schedule next poll with exponential backoff
          setTimeout(poll, Math.min(interval, maxInterval));
          interval = Math.min(interval * backoffFactor, maxInterval);
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }
}

// Create default API service instance
export const apiService = new ApiService();
