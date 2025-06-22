/**
 * Main JavaScript Entry Point
 * Initializes and coordinates all application modules
 */
import { UIHelpers } from './utils/ui-helpers.js';
import { apiService } from './services/api-service.js';
import { PlaylistAnalysis } from './modules/playlist-analysis.js';

/**
 * Application Main Class
 * Handles global initialization and module coordination
 */
class ChristianMusicCuratorApp {
    
    constructor() {
        this.modules = new Map();
        this.isInitialized = false;
        this.performanceMetrics = {};
        
        // Bind global error handler
        this.setupGlobalErrorHandling();
    }
    
    /**
     * Initialize the application
     */
    async init() {
        if (this.isInitialized) {
            return;
        }
        
        try {
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                await new Promise(resolve => {
                    document.addEventListener('DOMContentLoaded', resolve);
                });
            }
            
            // Initialize stagewise toolbar in development
            await this.initializeStagewiseToolbar();
            
            // Start performance monitoring
            this.startPerformanceMonitoring();
            
            // Register service worker
            await this.registerServiceWorker();
            
            // Initialize core modules
            this.initializeModules();
            
            // Setup global event listeners
            this.setupGlobalEventListeners();
            
            // Initialize page-specific functionality
            this.initializePageFeatures();
            
            this.isInitialized = true;
            console.log('✅ Application initialized successfully');
            
            // Report initialization performance
            this.reportPerformanceMetric('app_init_time', performance.now());
            
        } catch (error) {
            console.error('❌ Application initialization failed:', error);
            this.handleInitializationError(error);
        }
    }
    
    /**
     * Initialize stagewise toolbar for development
     */
    async initializeStagewiseToolbar() {
        // Stagewise toolbar initialization disabled for now
        console.log('📝 Stagewise toolbar initialization skipped');
    }
    
    /**
     * Start performance monitoring
     */
    startPerformanceMonitoring() {
        if ('PerformanceObserver' in window) {
            try {
                // Monitor First Contentful Paint (FCP)
                const fcpObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.name === 'first-contentful-paint') {
                            this.reportPerformanceMetric('fcp', entry.startTime);
                        }
                    }
                });
                fcpObserver.observe({ entryTypes: ['paint'] });
                
                // Monitor Largest Contentful Paint (LCP)
                const lcpObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    const lastEntry = entries[entries.length - 1];
                    this.reportPerformanceMetric('lcp', lastEntry.startTime);
                });
                lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
                
                // Monitor First Input Delay (FID)
                const fidObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        this.reportPerformanceMetric('fid', entry.processingStart - entry.startTime);
                    }
                });
                fidObserver.observe({ entryTypes: ['first-input'] });
                
                // Monitor Cumulative Layout Shift (CLS)
                let clsScore = 0;
                const clsObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (!entry.hadRecentInput) {
                            clsScore += entry.value;
                            this.reportPerformanceMetric('cls', clsScore);
                        }
                    }
                });
                clsObserver.observe({ entryTypes: ['layout-shift'] });
                
                // Monitor navigation timing
                window.addEventListener('load', () => {
                    const navigationTiming = performance.getEntriesByType('navigation')[0];
                    if (navigationTiming) {
                        this.reportPerformanceMetric('page_load_time', navigationTiming.loadEventEnd - navigationTiming.navigationStart);
                        this.reportPerformanceMetric('dom_content_loaded', navigationTiming.domContentLoadedEventEnd - navigationTiming.navigationStart);
                        this.reportPerformanceMetric('time_to_interactive', navigationTiming.domInteractive - navigationTiming.navigationStart);
                    }
                });
                
            } catch (error) {
                console.warn('Performance monitoring setup failed:', error);
            }
        }
    }
    
    /**
     * Register service worker for caching and offline functionality
     */
    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                // Register without explicit scope to use default scope (/static/)
                const registration = await navigator.serviceWorker.register('/static/sw.js');
                
                console.log('✅ Service Worker registered:', registration.scope);
                
                // Listen for updates
                registration.addEventListener('updatefound', () => {
                    console.log('🔄 Service Worker update found');
                    
                    const newWorker = registration.installing;
                    if (newWorker) {
                        newWorker.addEventListener('statechange', () => {
                            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                                // New service worker available
                                this.showServiceWorkerUpdatePrompt();
                            }
                        });
                    }
                });
                
                // Handle service worker messages
                navigator.serviceWorker.addEventListener('message', (event) => {
                    this.handleServiceWorkerMessage(event.data);
                });
                
                return registration;
            } catch (error) {
                console.log('Service Worker registration failed (this is OK):', error.message);
                // Don't treat this as a critical error - app should still work without SW
            }
        } else {
            console.log('Service Worker not supported');
        }
    }
    
    /**
     * Initialize core application modules
     */
    initializeModules() {
        // Initialize UI helpers (always available)
        this.modules.set('uiHelpers', new UIHelpers());
        
        // Initialize API service
        this.modules.set('apiService', apiService);
        
        console.log('✅ Core modules initialized');
    }
    
    /**
     * Setup global event listeners
     */
    setupGlobalEventListeners() {
        // Handle global click events for analytics
        document.addEventListener('click', this.handleGlobalClick.bind(this));
        
        // Handle network status changes
        window.addEventListener('online', this.handleOnlineStatus.bind(this));
        window.addEventListener('offline', this.handleOfflineStatus.bind(this));
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
        
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', this.handleUnhandledRejection.bind(this));
    }
    
    /**
     * Initialize page-specific features based on current page
     */
    initializePageFeatures() {
        const currentPage = this.detectCurrentPage();
        
        switch (currentPage) {
            case 'playlist_detail':
                this.initializePlaylistDetailPage();
                break;
            case 'dashboard':
                this.initializeDashboardPage();
                break;
            case 'song_detail':
                this.initializeSongDetailPage();
                break;
            default:
                this.initializeGenericPage();
        }
    }
    
    /**
     * Detect current page type
     */
    detectCurrentPage() {
        const path = window.location.pathname;
        
        if (path.includes('/playlist/')) {
            return 'playlist_detail';
        } else if (path === '/dashboard' || path === '/') {
            return 'dashboard';
        } else if (path.includes('/song/')) {
            return 'song_detail';
        }
        
        return 'generic';
    }
    
    /**
     * Initialize playlist detail page functionality
     */
    initializePlaylistDetailPage() {
        const playlistContainer = document.querySelector('[data-playlist-id]');
        
        if (playlistContainer) {
            const playlistId = playlistContainer.dataset.playlistId;
            const playlistName = playlistContainer.dataset.playlistName;
            
            if (playlistId) {
                const playlistAnalysis = new PlaylistAnalysis(playlistId, {
                    playlistName,
                    uiHelpers: this.modules.get('uiHelpers'),
                    apiService: this.modules.get('apiService')
                });
                
                // Initialize the playlist analysis module
                playlistAnalysis.init();
                
                this.modules.set('playlistAnalysis', playlistAnalysis);
                console.log('✅ Playlist detail page initialized');
            }
        }
    }
    
    /**
     * Initialize dashboard page functionality
     */
    initializeDashboardPage() {
        // Initialize dashboard-specific features
        this.initializeDashboardStats();
        this.initializePlaylistGrid();
        console.log('✅ Dashboard page initialized');
    }
    
    /**
     * Initialize song detail page functionality
     */
    initializeSongDetailPage() {
        // Initialize song-specific features
        this.initializeSongAnalysisDisplay();
        console.log('✅ Song detail page initialized');
    }
    
    /**
     * Initialize generic page functionality
     */
    initializeGenericPage() {
        // Initialize common features for all pages
        this.initializeGenericFeatures();
        console.log('✅ Generic page initialized');
    }
    
    /**
     * Initialize dashboard statistics
     */
    initializeDashboardStats() {
        const statsCards = document.querySelectorAll('[data-stat-card]');
        statsCards.forEach(card => {
            // Add animation effects
            card.classList.add('stat-card-animated');
        });
    }
    
    /**
     * Initialize playlist grid functionality
     */
    initializePlaylistGrid() {
        const playlistGrid = document.querySelector('.playlist-grid');
        if (playlistGrid) {
            // Initialize any grid-specific functionality
            this.setupPlaylistGridAnimations(playlistGrid);
        }
    }
    
    /**
     * Setup playlist grid animations
     */
    setupPlaylistGridAnimations(grid) {
        const cards = grid.querySelectorAll('.playlist-card');
        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.1}s`;
            card.classList.add('fade-in-up');
        });
    }
    
    /**
     * Initialize song analysis display
     */
    initializeSongAnalysisDisplay() {
        const analysisContainer = document.querySelector('.song-analysis');
        if (analysisContainer) {
            // Initialize analysis visualizations
            this.setupAnalysisCharts(analysisContainer);
        }
    }
    
    /**
     * Setup analysis charts
     */
    setupAnalysisCharts(container) {
        // Placeholder for future chart implementation
        console.log('Analysis charts initialized');
    }
    
    /**
     * Initialize generic features for all pages
     */
    initializeGenericFeatures() {
        // Initialize tooltips
        this.initializeTooltips();
        
        // Initialize modals
        this.initializeModals();
        
        // Initialize form enhancements
        this.initializeFormEnhancements();
    }
    
    /**
     * Initialize Bootstrap tooltips
     */
    initializeTooltips() {
        const tooltipElements = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltipElements.forEach(element => {
            new bootstrap.Tooltip(element);
        });
    }
    
    /**
     * Initialize Bootstrap modals
     */
    initializeModals() {
        const modalElements = document.querySelectorAll('.modal');
        modalElements.forEach(element => {
            new bootstrap.Modal(element);
        });
    }
    
    /**
     * Initialize form enhancements
     */
    initializeFormEnhancements() {
        const forms = document.querySelectorAll('form[data-enhanced]');
        forms.forEach(form => {
            this.enhanceForm(form);
        });
    }
    
    /**
     * Enhance a form with better UX
     */
    enhanceForm(form) {
        // Add loading states to submit buttons
        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) {
            form.addEventListener('submit', () => {
                submitBtn.disabled = true;
                submitBtn.innerHTML += ' <i class="fas fa-spinner fa-spin"></i>';
            });
        }
    }
    
    /**
     * Handle global click events for analytics
     */
    handleGlobalClick(event) {
        const target = event.target.closest('[data-analytics]');
        if (target) {
            const action = target.dataset.analytics;
            this.trackAnalyticsEvent('click', action, {
                element: target.tagName,
                text: target.textContent?.trim().substring(0, 50)
            });
        }
    }
    
    /**
     * Handle online status
     */
    handleOnlineStatus() {
        console.log('🌐 Back online');
        this.modules.get('uiHelpers')?.showSuccess('Connection restored!');
        
        // Sync any pending offline actions
        if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({
                type: 'SYNC_PENDING_ACTIONS'
            });
        }
    }
    
    /**
     * Handle offline status
     */
    handleOfflineStatus() {
        console.log('📴 Gone offline');
        this.modules.get('uiHelpers')?.showWarning('You are now offline. Some features may be limited.');
    }
    
    /**
     * Handle page visibility changes
     */
    handleVisibilityChange() {
        if (document.hidden) {
            // Page is now hidden
            this.reportPerformanceMetric('page_hide', performance.now());
        } else {
            // Page is now visible
            this.reportPerformanceMetric('page_show', performance.now());
        }
    }
    
    /**
     * Handle unhandled promise rejections
     */
    handleUnhandledRejection(event) {
        console.error('Unhandled promise rejection:', event.reason);
        
        // Report to error tracking service
        this.reportError('unhandled_rejection', event.reason);
        
        // Prevent the default error handling
        event.preventDefault();
    }
    
    /**
     * Handle service worker messages
     */
    handleServiceWorkerMessage(data) {
        switch (data.type) {
            case 'CACHE_UPDATED':
                console.log('Cache updated:', data.payload);
                break;
            case 'OFFLINE_READY':
                console.log('App is ready for offline use');
                break;
            default:
                console.log('Service worker message:', data);
        }
    }
    
    /**
     * Show service worker update prompt
     */
    showServiceWorkerUpdatePrompt() {
        const uiHelpers = this.modules.get('uiHelpers');
        if (uiHelpers) {
            // Show a user-friendly update prompt
            const updateMessage = `
                A new version of the app is available. 
                <button class="btn btn-sm btn-primary ms-2" onclick="window.location.reload()">
                    Update Now
                </button>
            `;
            uiHelpers.showInfo(updateMessage, 10000); // Show for 10 seconds
        }
    }
    
    /**
     * Setup global error handling
     */
    setupGlobalErrorHandling() {
        // Handle JavaScript errors
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
            this.reportError('javascript_error', event.error);
        });
        
        // Handle resource loading errors
        window.addEventListener('error', (event) => {
            if (event.target !== window) {
                console.error('Resource loading error:', event.target.src || event.target.href);
                this.reportError('resource_error', {
                    src: event.target.src || event.target.href,
                    type: event.target.tagName
                });
            }
        }, true);
    }
    
    /**
     * Handle initialization errors
     */
    handleInitializationError(error) {
        // Show user-friendly error message
        const errorContainer = document.createElement('div');
        errorContainer.className = 'alert alert-danger alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x';
        errorContainer.style.zIndex = '9999';
        errorContainer.innerHTML = `
            <strong>Application Error:</strong> The app failed to start properly. 
            <button class="btn btn-sm btn-outline-danger ms-2" onclick="window.location.reload()">
                Reload Page
            </button>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(errorContainer);
        
        // Report the error
        this.reportError('initialization_error', error);
    }
    
    /**
     * Track analytics events
     */
    trackAnalyticsEvent(type, action, data = {}) {
        // Store locally for potential batching
        const event = {
            type,
            action,
            data,
            timestamp: Date.now(),
            page: window.location.pathname
        };
        
        // Add to analytics queue
        if (!window.analyticsQueue) {
            window.analyticsQueue = [];
        }
        window.analyticsQueue.push(event);
        
        // Optional: Send to analytics endpoint
        if (window.analyticsEndpoint) {
            fetch(window.analyticsEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(event)
            }).catch(() => {
                // Analytics is optional, don't throw errors
            });
        }
    }
    
    /**
     * Report performance metrics
     */
    reportPerformanceMetric(name, value) {
        this.performanceMetrics[name] = value;
        
        // Log to console for development
        console.log(`📊 Performance: ${name} = ${Math.round(value)}ms`);
        
        // Optional: Send to performance monitoring endpoint
        if (window.performanceEndpoint) {
            fetch(window.performanceEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    metric: name,
                    value,
                    timestamp: Date.now(),
                    page: window.location.pathname
                })
            }).catch(() => {
                // Performance monitoring is optional
            });
        }
    }
    
    /**
     * Report errors to monitoring service
     */
    reportError(type, error) {
        const errorData = {
            type,
            message: error?.message || error,
            stack: error?.stack,
            timestamp: Date.now(),
            page: window.location.pathname,
            userAgent: navigator.userAgent
        };
        
        // Optional: Send to error tracking endpoint
        if (window.errorEndpoint) {
            fetch(window.errorEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(errorData)
            }).catch(() => {
                // Error reporting is optional
            });
        }
    }
    
    /**
     * Get a module instance
     */
    getModule(name) {
        return this.modules.get(name);
    }
    
    /**
     * Check if app is initialized
     */
    isReady() {
        return this.isInitialized;
    }
}

// Create global app instance
const app = new ChristianMusicCuratorApp();

// Initialize the app
app.init();

// Export for global access
window.app = app;
export default app; 