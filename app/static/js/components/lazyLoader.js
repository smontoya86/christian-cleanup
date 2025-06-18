/**
 * Enhanced Lazy Loader Component
 * Handles lazy loading of images, content, and implements skeleton loading states
 */
import { UIHelpers } from '../utils/ui-helpers.js';

/**
 * LazyLoader class for handling intersection observer-based lazy loading
 */
export class LazyLoader {
  /**
     * Create lazy loader instance
     * @param {Object} options - Configuration options
     */
  constructor (options = {}) {
    this.options = {
      rootMargin: '50px 0px',
      threshold: 0.01,
      imageSelector: 'img[data-src]',
      contentSelector: '[data-lazy-content]',
      skeletonSelector: '.skeleton-loader',
      enableSkeletons: true,
      retryAttempts: 3,
      retryDelay: 1000,
      ...options
    };

    this.observer = null;
    this.imageObserver = null;
    this.loadedImages = new Set();
    this.loadedContent = new Set();
    this.loadAttempts = new Map();

    this.uiHelpers = new UIHelpers();
    this.init();
  }

  /**
     * Initialize the lazy loader
     */
  init () {
    if (!('IntersectionObserver' in window)) {
      // Fallback for browsers without IntersectionObserver
      this.loadAllImagesImmediately();
      return;
    }

    this.setupObservers();
    this.observeElements();
    this.setupPerformanceMonitoring();
  }

  /**
     * Setup intersection observers
     */
  setupObservers () {
    // Image observer
    this.imageObserver = new IntersectionObserver(
      this.handleImageIntersection.bind(this),
      {
        rootMargin: this.options.rootMargin,
        threshold: this.options.threshold
      }
    );

    // Content observer
    this.contentObserver = new IntersectionObserver(
      this.handleContentIntersection.bind(this),
      {
        rootMargin: '100px 0px', // Load content earlier
        threshold: 0.01
      }
    );
  }

  /**
     * Start observing elements
     */
  observeElements () {
    // Observe images
    const images = document.querySelectorAll(this.options.imageSelector);
    images.forEach(img => {
      this.imageObserver.observe(img);
      if (this.options.enableSkeletons) {
        this.addSkeletonLoader(img);
      }
    });

    // Observe lazy content
    const contentElements = document.querySelectorAll(this.options.contentSelector);
    contentElements.forEach(element => {
      this.contentObserver.observe(element);
    });
  }

  /**
     * Handle image intersection
     * @param {Array} entries - Intersection observer entries
     */
  handleImageIntersection (entries) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        this.loadImage(entry.target);
        this.imageObserver.unobserve(entry.target);
      }
    });
  }

  /**
     * Handle content intersection
     * @param {Array} entries - Intersection observer entries
     */
  handleContentIntersection (entries) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        this.loadContent(entry.target);
        this.contentObserver.unobserve(entry.target);
      }
    });
  }

  /**
     * Load an image with retry logic
     * @param {HTMLImageElement} img - Image element to load
     */
  async loadImage (img) {
    const src = img.dataset.src;
    const alt = img.dataset.alt || img.alt;

    if (!src || this.loadedImages.has(src)) {
      return;
    }

    const attemptKey = `img_${src}`;
    const attempts = this.loadAttempts.get(attemptKey) || 0;

    try {
      // Create a new image to preload
      const newImg = new Image();

      // Set up promise for image loading
      const loadPromise = new Promise((resolve, reject) => {
        newImg.onload = resolve;
        newImg.onerror = reject;
        newImg.src = src;
      });

      // Wait for image to load
      await loadPromise;

      // Update the actual image element
      img.src = src;
      if (alt) img.alt = alt;
      img.classList.add('loaded');

      // Remove skeleton loader
      this.removeSkeletonLoader(img);

      // Mark as loaded
      this.loadedImages.add(src);
      this.loadAttempts.delete(attemptKey);

      // Trigger load event
      img.dispatchEvent(new CustomEvent('lazyload', {
        detail: { src, success: true }
      }));

    } catch (error) {
      if (attempts < this.options.retryAttempts) {
        // Retry after delay
        this.loadAttempts.set(attemptKey, attempts + 1);
        setTimeout(() => {
          this.loadImage(img);
        }, this.options.retryDelay * Math.pow(2, attempts)); // Exponential backoff
      } else {
        // Final failure - show error state
        this.handleImageError(img, error);
      }
    }
  }

  /**
     * Load lazy content
     * @param {HTMLElement} element - Element to load content for
     */
  async loadContent (element) {
    const contentUrl = element.dataset.lazyContent;
    const contentType = element.dataset.contentType || 'html';

    if (!contentUrl || this.loadedContent.has(contentUrl)) {
      return;
    }

    try {
      // Show loading state
      element.classList.add('loading');

      const response = await fetch(contentUrl);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      let content;
      switch (contentType) {
        case 'json':
          content = await response.json();
          this.renderJsonContent(element, content);
          break;
        case 'text':
          content = await response.text();
          element.textContent = content;
          break;
        default: // html
          content = await response.text();
          element.innerHTML = content;
      }

      // Mark as loaded
      this.loadedContent.add(contentUrl);
      element.classList.remove('loading');
      element.classList.add('loaded');

      // Trigger load event
      element.dispatchEvent(new CustomEvent('contentload', {
        detail: { url: contentUrl, content, success: true }
      }));

    } catch (error) {
      this.handleContentError(element, error);
    }
  }

  /**
     * Add skeleton loader to image
     * @param {HTMLImageElement} img - Image element
     */
  addSkeletonLoader (img) {
    if (img.closest('.skeleton-wrapper')) {
      return; // Already has skeleton
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'skeleton-wrapper';

    const skeleton = document.createElement('div');
    skeleton.className = 'skeleton-loader skeleton-img';
    skeleton.style.width = img.width ? `${img.width}px` : '100%';
    skeleton.style.height = img.height ? `${img.height}px` : '200px';

    img.parentNode.insertBefore(wrapper, img);
    wrapper.appendChild(skeleton);
    wrapper.appendChild(img);
  }

  /**
     * Remove skeleton loader
     * @param {HTMLImageElement} img - Image element
     */
  removeSkeletonLoader (img) {
    const wrapper = img.closest('.skeleton-wrapper');
    if (wrapper) {
      const skeleton = wrapper.querySelector('.skeleton-loader');
      if (skeleton) {
        skeleton.classList.add('fade-out');
        setTimeout(() => {
          skeleton.remove();
          // Unwrap the image
          wrapper.parentNode.insertBefore(img, wrapper);
          wrapper.remove();
        }, 300);
      }
    }
  }

  /**
     * Handle image loading error
     * @param {HTMLImageElement} img - Image element
     * @param {Error} error - Error object
     */
  handleImageError (img, error) {
    img.classList.add('error');
    img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNiIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBmb3VuZDwvdGV4dD48L3N2Zz4=';
    img.alt = 'Image failed to load';

    this.removeSkeletonLoader(img);

    // Trigger error event
    img.dispatchEvent(new CustomEvent('lazyload', {
      detail: { src: img.dataset.src, success: false, error: error.message }
    }));
  }

  /**
     * Handle content loading error
     * @param {HTMLElement} element - Element
     * @param {Error} error - Error object
     */
  handleContentError (element, error) {
    element.classList.remove('loading');
    element.classList.add('error');
    element.innerHTML = '<p class="text-muted"><i class="fas fa-exclamation-triangle"></i> Content failed to load</p>';

    // Trigger error event
    element.dispatchEvent(new CustomEvent('contentload', {
      detail: { url: element.dataset.lazyContent, success: false, error: error.message }
    }));
  }

  /**
     * Render JSON content
     * @param {HTMLElement} element - Target element
     * @param {Object} data - JSON data
     */
  renderJsonContent (element, data) {
    // Basic JSON rendering - can be extended for specific data types
    if (Array.isArray(data)) {
      const list = document.createElement('ul');
      data.forEach(item => {
        const listItem = document.createElement('li');
        listItem.textContent = typeof item === 'object' ? JSON.stringify(item) : item;
        list.appendChild(listItem);
      });
      element.appendChild(list);
    } else if (typeof data === 'object') {
      const pre = document.createElement('pre');
      pre.textContent = JSON.stringify(data, null, 2);
      element.appendChild(pre);
    } else {
      element.textContent = data;
    }
  }

  /**
     * Fallback for browsers without IntersectionObserver
     */
  loadAllImagesImmediately () {
    const images = document.querySelectorAll(this.options.imageSelector);
    images.forEach(img => {
      if (img.dataset.src) {
        img.src = img.dataset.src;
        if (img.dataset.alt) img.alt = img.dataset.alt;
      }
    });

    const contentElements = document.querySelectorAll(this.options.contentSelector);
    contentElements.forEach(element => {
      this.loadContent(element);
    });
  }

  /**
     * Setup performance monitoring
     */
  setupPerformanceMonitoring () {
    if ('PerformanceObserver' in window) {
      try {
        // Monitor largest contentful paint
        const lcpObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const lastEntry = entries[entries.length - 1];

          // Log LCP for monitoring
          if (lastEntry && lastEntry.startTime > 0) {
            this.reportPerformance('lcp', lastEntry.startTime);
          }
        });
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });

        // Monitor cumulative layout shift
        const clsObserver = new PerformanceObserver((list) => {
          let clsScore = 0;
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) {
              clsScore += entry.value;
            }
          }
          if (clsScore > 0) {
            this.reportPerformance('cls', clsScore);
          }
        });
        clsObserver.observe({ entryTypes: ['layout-shift'] });

      } catch (error) {
        // Performance monitoring is optional
        console.warn('Performance monitoring not available:', error.message);
      }
    }
  }

  /**
     * Report performance metrics
     * @param {string} metric - Metric name
     * @param {number} value - Metric value
     */
  reportPerformance (metric, value) {
    // Store metrics for potential reporting
    if (!window.performanceMetrics) {
      window.performanceMetrics = {};
    }
    window.performanceMetrics[metric] = value;

    // Optional: Send to analytics endpoint
    if (window.analyticsEndpoint) {
      fetch(window.analyticsEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metric, value, timestamp: Date.now() })
      }).catch(() => {
        // Analytics is optional, don't throw errors
      });
    }
  }

  /**
     * Refresh lazy loading for new content
     */
  refresh () {
    this.observeElements();
  }

  /**
     * Destroy the lazy loader
     */
  destroy () {
    if (this.imageObserver) {
      this.imageObserver.disconnect();
    }
    if (this.contentObserver) {
      this.contentObserver.disconnect();
    }
    this.loadedImages.clear();
    this.loadedContent.clear();
    this.loadAttempts.clear();
  }
}

// Auto-initialize lazy loader when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    window.lazyLoader = new LazyLoader();
  });
} else {
  window.lazyLoader = new LazyLoader();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = LazyLoader;
}
