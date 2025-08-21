/**
 * Unit tests for LazyLoader component
 */

// Mock IntersectionObserver for testing
global.IntersectionObserver = jest.fn().mockImplementation((callback) => {
  return {
    observe: jest.fn(),
    unobserve: jest.fn(),
    disconnect: jest.fn(),
    callback: callback
  };
});

// Mock fetch for testing
global.fetch = jest.fn();

describe('LazyLoader', () => {
  let LazyLoader;
  let lazyLoader;
  let mockElement;

  beforeAll(() => {
    // Use require instead of dynamic import for Jest compatibility
    LazyLoader = require('../../app/static/js/components/lazyLoader.js').default;
  });

  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();

    // Create mock DOM element
    mockElement = document.createElement('div');
    mockElement.setAttribute('data-lazy-url', '/api/test');
    mockElement.setAttribute('data-loading-template', 'loading-template');
    mockElement.setAttribute('data-error-template', 'error-template');
    document.body.appendChild(mockElement);

    // Create LazyLoader instance
    lazyLoader = new LazyLoader();
  });

  afterEach(() => {
    if (mockElement && mockElement.parentNode) {
      document.body.removeChild(mockElement);
    }
  });

  describe('Initialization', () => {
    test('should initialize with default options', () => {
      expect(lazyLoader.threshold).toBe(0.1);
      expect(lazyLoader.retryLimit).toBe(3);
      expect(lazyLoader.retryDelay).toBe(2000);
      expect(lazyLoader.rootMargin).toBe('0px');
    });

    test('should initialize with custom options', () => {
      const customLoader = new LazyLoader({
        threshold: 0.5,
        retryLimit: 5,
        retryDelay: 1000,
        rootMargin: '50px'
      });

      expect(customLoader.threshold).toBe(0.5);
      expect(customLoader.retryLimit).toBe(5);
      expect(customLoader.retryDelay).toBe(1000);
      expect(customLoader.rootMargin).toBe('50px');
    });

    test('should create IntersectionObserver with correct options', () => {
      expect(global.IntersectionObserver).toHaveBeenCalledWith(
        expect.any(Function),
        {
          threshold: 0.1,
          rootMargin: '0px'
        }
      );
    });
  });

  describe('Element Observation', () => {
    test('should observe elements', () => {
      const spy = jest.spyOn(lazyLoader.observer, 'observe');
      lazyLoader.observe(mockElement);
      expect(spy).toHaveBeenCalledWith(mockElement);
    });

    test('should handle intersection correctly', () => {
      const loadContentSpy = jest.spyOn(lazyLoader, 'loadContent');
      const unobserveSpy = jest.spyOn(lazyLoader.observer, 'unobserve');

      // Simulate intersection
      const entries = [{
        isIntersecting: true,
        target: mockElement
      }];

      lazyLoader.handleIntersection(entries, lazyLoader.observer);

      expect(loadContentSpy).toHaveBeenCalledWith(
        mockElement,
        '/api/test',
        'loading-template',
        'error-template'
      );
      expect(unobserveSpy).toHaveBeenCalledWith(mockElement);
    });

    test('should not load content when not intersecting', () => {
      const loadContentSpy = jest.spyOn(lazyLoader, 'loadContent');

      // Simulate no intersection
      const entries = [{
        isIntersecting: false,
        target: mockElement
      }];

      lazyLoader.handleIntersection(entries, lazyLoader.observer);

      expect(loadContentSpy).not.toHaveBeenCalled();
    });
  });

  describe('Content Loading', () => {
    test('should show loading state initially', () => {
      // Create loading template
      const loadingTemplate = document.createElement('template');
      loadingTemplate.id = 'loading-template';
      loadingTemplate.innerHTML = '<div class="loading">Loading...</div>';
      document.body.appendChild(loadingTemplate);

      global.fetch.mockImplementation(() => new Promise(() => {})); // Never resolves

      lazyLoader.loadContent(mockElement, '/api/test', 'loading-template', 'error-template');

      expect(mockElement.innerHTML).toContain('Loading...');

      document.body.removeChild(loadingTemplate);
    });

    test('should show default skeleton loader when no template provided', () => {
      global.fetch.mockImplementation(() => new Promise(() => {})); // Never resolves

      lazyLoader.loadContent(mockElement, '/api/test');

      expect(mockElement.innerHTML).toContain('skeleton-loader');
    });

    test('should handle successful API response', async () => {
      const mockData = { test: 'data', status: 'success' };
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockData)
      });

      const renderContentSpy = jest.spyOn(lazyLoader, 'renderContent');

      await lazyLoader.loadContent(mockElement, '/api/test');

      expect(global.fetch).toHaveBeenCalledWith('/api/test');
      expect(renderContentSpy).toHaveBeenCalledWith(mockElement, mockData);
    });

    test('should handle API error response', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 404
      });

      // Mock setTimeout to avoid actual delays in tests
      jest.useFakeTimers();

      lazyLoader.loadContent(mockElement, '/api/test', null, null);

      await new Promise(resolve => setTimeout(resolve, 0));

      // Should show error state
      expect(mockElement.innerHTML).toContain('Failed to load content');
      expect(mockElement.innerHTML).toContain('retry-btn');

      jest.useRealTimers();
    });

    test('should retry on network failure', async () => {
      global.fetch
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValue({
          ok: true,
          json: () => Promise.resolve({ test: 'data' })
        });

      jest.useFakeTimers();

      const promise = lazyLoader.loadContent(mockElement, '/api/test');

      // Fast-forward past retry delay
      jest.advanceTimersByTime(2000);

      await promise;

      expect(global.fetch).toHaveBeenCalledTimes(2);

      jest.useRealTimers();
    });

    test('should stop retrying after max attempts', async () => {
      global.fetch.mockRejectedValue(new Error('Network error'));

      jest.useFakeTimers();

      lazyLoader.loadContent(mockElement, '/api/test');

      // Fast-forward past all retry attempts
      for (let i = 0; i < 3; i++) {
        jest.advanceTimersByTime(2000);
        await new Promise(resolve => setTimeout(resolve, 0));
      }

      expect(global.fetch).toHaveBeenCalledTimes(4); // Initial + 3 retries
      expect(mockElement.innerHTML).toContain('Failed to load content');

      jest.useRealTimers();
    });
  });

  describe('Content Rendering', () => {
    test('should have renderContent method', () => {
      expect(typeof lazyLoader.renderContent).toBe('function');
    });

    test('should clear element content by default', () => {
      mockElement.innerHTML = '<div>existing content</div>';

      lazyLoader.renderContent(mockElement, { test: 'data' });

      expect(mockElement.innerHTML).toBe('');
    });
  });

  describe('Error Handling', () => {
    test('should use error template when provided', async () => {
      // Create error template
      const errorTemplate = document.createElement('template');
      errorTemplate.id = 'error-template';
      errorTemplate.innerHTML = '<div class="custom-error">Custom error message</div>';
      document.body.appendChild(errorTemplate);

      global.fetch.mockRejectedValue(new Error('Network error'));

      jest.useFakeTimers();

      lazyLoader.loadContent(mockElement, '/api/test', null, 'error-template');

      // Fast-forward past all retry attempts
      for (let i = 0; i < 3; i++) {
        jest.advanceTimersByTime(2000);
        await new Promise(resolve => setTimeout(resolve, 0));
      }

      expect(mockElement.innerHTML).toContain('Custom error message');

      document.body.removeChild(errorTemplate);
      jest.useRealTimers();
    });

    test('should handle missing templates gracefully', () => {
      lazyLoader.loadContent(mockElement, '/api/test', 'non-existent-template', 'non-existent-error');

      // Should not throw error and should show default skeleton
      expect(mockElement.innerHTML).toContain('skeleton-loader');
    });
  });

  describe('Global Retry Function', () => {
    test('should have global retryLoad function', () => {
      expect(typeof window.retryLoad).toBe('function');
    });

    test('should retry loading when retry button is clicked', () => {
      // Create a retry button
      const retryButton = document.createElement('button');
      retryButton.className = 'retry-btn';

      // Create container with lazy loading attributes
      const container = document.createElement('div');
      container.setAttribute('data-lazy-url', '/api/retry-test');
      container.appendChild(retryButton);
      document.body.appendChild(container);

      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ test: 'retry-data' })
      });

      // Call global retry function
      window.retryLoad(retryButton, '/api/retry-test');

      expect(global.fetch).toHaveBeenCalledWith('/api/retry-test');

      document.body.removeChild(container);
    });
  });
});
