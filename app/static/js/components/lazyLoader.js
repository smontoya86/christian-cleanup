/**
 * LazyLoader - A component for lazy loading content using Intersection Observer
 */
class LazyLoader {
  constructor(options = {}) {
    this.threshold = options.threshold || 0.1;
    this.rootMargin = options.rootMargin || '0px';
    this.observer = null;
    this.retryLimit = options.retryLimit || 3;
    this.retryDelay = options.retryDelay || 2000;
    this.initObserver();
  }
  
  initObserver() {
    if ('IntersectionObserver' in window) {
      this.observer = new IntersectionObserver(this.handleIntersection.bind(this), {
        threshold: this.threshold,
        rootMargin: this.rootMargin
      });
    } else {
      // Fallback for browsers without IntersectionObserver support
      console.warn('IntersectionObserver not supported, loading all content immediately');
      this.observer = {
        observe: (element) => {
          // Load content immediately for unsupported browsers
          const dataUrl = element.getAttribute('data-lazy-url');
          const loadingTemplate = element.getAttribute('data-loading-template');
          const errorTemplate = element.getAttribute('data-error-template');
          this.loadContent(element, dataUrl, loadingTemplate, errorTemplate);
        },
        unobserve: () => {},
        disconnect: () => {}
      };
    }
  }
  
  handleIntersection(entries, observer) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const element = entry.target;
        const dataUrl = element.getAttribute('data-lazy-url');
        const loadingTemplate = element.getAttribute('data-loading-template');
        const errorTemplate = element.getAttribute('data-error-template');
        
        this.loadContent(element, dataUrl, loadingTemplate, errorTemplate);
        observer.unobserve(element);
      }
    });
  }
  
  loadContent(element, url, loadingTemplate, errorTemplate, retryCount = 0) {
    // Show loading state
    this.showLoadingState(element, loadingTemplate);
    
    fetch(url)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        this.renderContent(element, data);
        element.setAttribute('aria-busy', 'false');
      })
      .catch(error => {
        console.error('Lazy loading error:', error);
        this.handleLoadError(element, url, loadingTemplate, errorTemplate, retryCount);
      });
  }
  
  showLoadingState(element, loadingTemplate) {
    element.setAttribute('aria-busy', 'true');
    
    if (loadingTemplate) {
      const template = document.getElementById(loadingTemplate);
      if (template) {
        element.innerHTML = template.innerHTML;
        return;
      }
    }
    
    // Default skeleton loader
    element.innerHTML = '<div class="skeleton-loader"></div>';
  }
  
  handleLoadError(element, url, loadingTemplate, errorTemplate, retryCount) {
    if (retryCount < this.retryLimit) {
      console.warn(`Retrying load (${retryCount + 1}/${this.retryLimit}): ${url}`);
      setTimeout(() => {
        this.loadContent(element, url, loadingTemplate, errorTemplate, retryCount + 1);
      }, this.retryDelay * Math.pow(2, retryCount)); // Exponential backoff
    } else {
      this.showErrorState(element, url, errorTemplate);
    }
  }
  
  showErrorState(element, url, errorTemplate) {
    element.setAttribute('aria-busy', 'false');
    
    if (errorTemplate) {
      const template = document.getElementById(errorTemplate);
      if (template) {
        element.innerHTML = template.innerHTML;
        return;
      }
    }
    
    // Default error state
    element.innerHTML = `
      <div class="error-container">
        <p>Failed to load content</p>
        <button class="retry-btn" onclick="retryLoad(this, '${url}')">Retry</button>
      </div>
    `;
  }
  
  renderContent(element, data) {
    // Default implementation - clear content
    // This method should be overridden for specific content types
    element.innerHTML = '';
  }
  
  observe(element) {
    if (this.observer) {
      this.observer.observe(element);
    }
  }
  
  unobserve(element) {
    if (this.observer) {
      this.observer.unobserve(element);
    }
  }
  
  disconnect() {
    if (this.observer) {
      this.observer.disconnect();
    }
  }
}

// Global retry function for error state buttons
function retryLoad(button, url) {
  const container = button.closest('[data-lazy-url]');
  if (container) {
    const lazyLoader = new LazyLoader();
    const loadingTemplate = container.getAttribute('data-loading-template');
    const errorTemplate = container.getAttribute('data-error-template');
    lazyLoader.loadContent(container, url, loadingTemplate, errorTemplate);
  }
}

// Make retryLoad available globally
if (typeof window !== 'undefined') {
  window.retryLoad = retryLoad;
}

// Support both ES modules and CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { default: LazyLoader };
} else if (typeof window !== 'undefined') {
  window.LazyLoader = LazyLoader;
} 