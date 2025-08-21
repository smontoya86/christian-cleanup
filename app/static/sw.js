/**
 * Service Worker for Christian Music Curator
 * Handles caching of static assets, API responses, and offline functionality
 */

const CACHE_NAME = 'christian-music-curator-v1.0.0';
const API_CACHE_NAME = 'christian-music-curator-api-v1.0.0';

// Static assets to cache immediately
const STATIC_CACHE = [
  '/',
  '/static/css/base.css',
  '/static/css/components.css',
  '/static/css/utilities.css',
  '/static/js/main.js',
  '/static/dist/css/base.css',
  '/static/dist/css/components.css',
  '/static/dist/css/utilities.css',
  '/static/dist/js/main.js',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js'
];

// API endpoints to cache
const API_CACHE_PATTERNS = [
  '/api/health',
  '/api/playlists/',
  '/api/songs/',
  '/dashboard',
  '/playlist/'
];

// URLs that should bypass the cache
const CACHE_BYPASS = [
  '/auth/',
  '/admin/',
  '/api/songs/*/analyze',
  '/analyze_playlist_api/'
];

/**
 * Install event - pre-cache static assets
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    Promise.all([
      // Cache static assets
      caches.open(CACHE_NAME).then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_CACHE);
      }),
      // Cache API responses
      caches.open(API_CACHE_NAME)
    ]).then(() => {
      console.log('[SW] Installation complete');
      // Skip waiting to activate immediately
      return self.skipWaiting();
    }).catch((error) => {
      console.error('[SW] Installation failed:', error);
    })
  );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => {
            // Remove old cache versions
            return cacheName.startsWith('christian-music-curator') &&
                   cacheName !== CACHE_NAME &&
                   cacheName !== API_CACHE_NAME;
          })
          .map((cacheName) => {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          })
      );
    }).then(() => {
      console.log('[SW] Activation complete');
      // Take control of all open pages
      return self.clients.claim();
    })
  );
});

/**
 * Fetch event - handle requests with caching strategies
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip cache bypass URLs
  if (shouldBypassCache(request.url)) {
    return;
  }

  // Handle different types of requests
  if (isStaticAsset(request.url)) {
    event.respondWith(handleStaticAsset(request));
  } else if (isAPIRequest(request.url)) {
    event.respondWith(handleAPIRequest(request));
  } else if (isPageRequest(request)) {
    event.respondWith(handlePageRequest(request));
  }
});

/**
 * Handle static asset requests (CSS, JS, images)
 * Strategy: Cache First
 */
async function handleStaticAsset(request) {
  try {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(request);

    if (cached) {
      console.log('[SW] Serving static asset from cache:', request.url);
      return cached;
    }

    console.log('[SW] Fetching static asset:', request.url);
    const response = await fetch(request);

    // Cache successful responses
    if (response.ok) {
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.error('[SW] Static asset fetch failed:', error);
    return new Response('Asset not available', { status: 503 });
  }
}

/**
 * Handle API requests
 * Strategy: Network First with cache fallback
 */
async function handleAPIRequest(request) {
  try {
    // Try network first
    console.log('[SW] Fetching API request:', request.url);
    const response = await fetch(request, { timeout: 5000 });

    if (response.ok) {
      // Cache successful API responses
      const cache = await caches.open(API_CACHE_NAME);
      cache.put(request, response.clone());
      console.log('[SW] Cached API response:', request.url);
    }

    return response;
  } catch (error) {
    console.log('[SW] Network failed, trying cache for:', request.url);

    // Fallback to cache
    const cache = await caches.open(API_CACHE_NAME);
    const cached = await cache.match(request);

    if (cached) {
      console.log('[SW] Serving API response from cache:', request.url);
      // Add a header to indicate this is cached
      const response = cached.clone();
      response.headers.set('X-Served-By', 'ServiceWorker');
      return response;
    }

    // Return offline response for API requests
    return new Response(
      JSON.stringify({
        error: 'Offline',
        message: 'This feature is not available offline'
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Handle page requests
 * Strategy: Network First with cache fallback
 */
async function handlePageRequest(request) {
  try {
    console.log('[SW] Fetching page:', request.url);
    const response = await fetch(request);

    if (response.ok) {
      // Cache successful page responses
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.log('[SW] Network failed, trying cache for page:', request.url);

    // Try cache
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(request);

    if (cached) {
      return cached;
    }

    // Fallback to offline page
    return getOfflinePage();
  }
}

/**
 * Check if request should bypass cache
 */
function shouldBypassCache(url) {
  return CACHE_BYPASS.some(pattern => {
    if (pattern.includes('*')) {
      const regex = new RegExp(pattern.replace(/\*/g, '.*'));
      return regex.test(url);
    }
    return url.includes(pattern);
  });
}

/**
 * Check if request is for a static asset
 */
function isStaticAsset(url) {
  return /\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot)(\?.*)?$/.test(url) ||
         url.includes('/static/') ||
         url.includes('cdn.jsdelivr.net') ||
         url.includes('cdnjs.cloudflare.com');
}

/**
 * Check if request is an API request
 */
function isAPIRequest(url) {
  return url.includes('/api/') && !shouldBypassCache(url);
}

/**
 * Check if request is a page request
 */
function isPageRequest(request) {
  return request.headers.get('Accept') &&
         request.headers.get('Accept').includes('text/html');
}

/**
 * Generate offline page response
 */
function getOfflinePage() {
  const offlineHTML = `
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Offline - Christian Music Curator</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
                color: white;
            }
            .offline-container {
                text-align: center;
                max-width: 500px;
                padding: 2rem;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 1rem;
                backdrop-filter: blur(10px);
            }
            .offline-icon {
                font-size: 4rem;
                margin-bottom: 1rem;
            }
            h1 { margin-bottom: 0.5rem; }
            p { margin-bottom: 1.5rem; opacity: 0.9; }
            .retry-btn {
                background: #6f42c1;
                color: white;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 0.5rem;
                cursor: pointer;
                font-size: 1rem;
                transition: background-color 0.2s;
            }
            .retry-btn:hover {
                background: #5936a3;
            }
        </style>
    </head>
    <body>
        <div class="offline-container">
            <div class="offline-icon">⚡</div>
            <h1>You're Offline</h1>
            <p>It looks like you've lost your internet connection. Some features may not be available right now.</p>
            <button class="retry-btn" onclick="window.location.reload()">
                Try Again
            </button>
        </div>
    </body>
    </html>
  `;

  return new Response(offlineHTML, {
    headers: { 'Content-Type': 'text/html' }
  });
}

/**
 * Background sync for offline actions
 */
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    console.log('[SW] Background sync triggered');
    event.waitUntil(doBackgroundSync());
  }
});

/**
 * Handle background sync
 */
async function doBackgroundSync() {
  try {
    // Get pending actions from IndexedDB or localStorage
    const pendingActions = await getPendingActions();

    for (const action of pendingActions) {
      try {
        await processPendingAction(action);
        await removePendingAction(action.id);
      } catch (error) {
        console.error('[SW] Failed to process pending action:', error);
      }
    }
  } catch (error) {
    console.error('[SW] Background sync failed:', error);
  }
}

/**
 * Get pending actions (placeholder - implement with IndexedDB)
 */
async function getPendingActions() {
  // This would normally read from IndexedDB
  return [];
}

/**
 * Process a pending action
 */
async function processPendingAction(action) {
  // Process the action when back online
  console.log('[SW] Processing pending action:', action);
}

/**
 * Remove processed action
 */
async function removePendingAction(actionId) {
  // Remove from IndexedDB
  console.log('[SW] Removed pending action:', actionId);
}

/**
 * Handle push notifications (future enhancement)
 */
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  const options = {
    body: data.body || 'New update available',
    icon: '/static/images/icon-192x192.png',
    badge: '/static/images/badge-72x72.png',
    data: data.url || '/',
    actions: [
      {
        action: 'open',
        title: 'View',
        icon: '/static/images/view-icon.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/images/close-icon.png'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'Christian Music Curator', options)
  );
});

/**
 * Handle notification clicks
 */
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  if (event.action === 'open' || !event.action) {
    const url = event.notification.data || '/';
    event.waitUntil(
      clients.openWindow(url)
    );
  }
});

/**
 * Periodic background sync (future enhancement)
 */
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'playlist-sync') {
    event.waitUntil(syncPlaylistsInBackground());
  }
});

/**
 * Background playlist sync
 */
async function syncPlaylistsInBackground() {
  try {
    console.log('[SW] Syncing playlists in background...');
    // Implement background playlist synchronization
  } catch (error) {
    console.error('[SW] Background playlist sync failed:', error);
  }
}

console.log('[SW] Service worker script loaded');
