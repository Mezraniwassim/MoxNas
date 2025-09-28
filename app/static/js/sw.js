/* MoxNAS Service Worker */

const CACHE_NAME = 'moxnas-v1.0.0';
const STATIC_CACHE = 'moxnas-static-v1.0.0';
const DYNAMIC_CACHE = 'moxnas-dynamic-v1.0.0';

// Files to cache for offline functionality
const STATIC_FILES = [
    '/',
    '/static/css/style.css',
    '/static/css/modern-ui.css',
    '/static/js/app-modern.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/chart.js',
    '/static/images/icon-192x192.png',
    '/static/images/icon-512x512.png',
    '/static/manifest.json'
];

// API endpoints to cache
const API_ENDPOINTS = [
    '/api/system/stats',
    '/api/storage/pools',
    '/api/shares',
    '/api/monitoring/alerts'
];

// Install event - cache static resources
self.addEventListener('install', event => {
    console.log('[SW] Installing service worker...');
    
    event.waitUntil(
        Promise.all([
            caches.open(STATIC_CACHE).then(cache => {
                console.log('[SW] Caching static files');
                return cache.addAll(STATIC_FILES);
            }),
            self.skipWaiting()
        ])
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('[SW] Activating service worker...');
    
    event.waitUntil(
        Promise.all([
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            self.clients.claim()
        ])
    );
});

// Fetch event - implement caching strategies
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Handle different types of requests with appropriate strategies
    if (request.method !== 'GET') {
        // Handle POST/PUT/DELETE requests
        event.respondWith(handleDynamicRequest(request));
    } else if (url.pathname.startsWith('/api/')) {
        // API requests - network first, cache as fallback
        event.respondWith(handleAPIRequest(request));
    } else if (url.pathname.startsWith('/static/')) {
        // Static assets - cache first
        event.respondWith(handleStaticRequest(request));
    } else if (url.origin === location.origin) {
        // HTML pages - network first, cache as fallback
        event.respondWith(handlePageRequest(request));
    }
});

// Handle API requests with network-first strategy
async function handleAPIRequest(request) {
    try {
        // Try network first
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            // Cache successful API responses
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[SW] Network failed, trying cache for:', request.url);
        
        // Fall back to cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline response for API requests
        return new Response(
            JSON.stringify({
                error: 'Offline',
                message: 'This request requires an internet connection',
                offline: true
            }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Handle static requests with cache-first strategy
async function handleStaticRequest(request) {
    try {
        // Try cache first
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Fall back to network
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(STATIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[SW] Failed to fetch static resource:', request.url);
        
        // Return a generic offline response for static resources
        if (request.url.includes('.css')) {
            return new Response('/* Offline */', {
                headers: { 'Content-Type': 'text/css' }
            });
        } else if (request.url.includes('.js')) {
            return new Response('// Offline', {
                headers: { 'Content-Type': 'application/javascript' }
            });
        }
        
        return new Response('Offline', { status: 503 });
    }
}

// Handle page requests with network-first strategy
async function handlePageRequest(request) {
    try {
        // Try network first
        const networkResponse = await fetch(request);
        
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.log('[SW] Network failed, trying cache for:', request.url);
        
        // Fall back to cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline page
        return caches.match('/offline.html') || new Response(
            createOfflinePage(),
            { headers: { 'Content-Type': 'text/html' } }
        );
    }
}

// Handle dynamic requests (POST, PUT, DELETE)
async function handleDynamicRequest(request) {
    try {
        return await fetch(request);
    } catch (error) {
        console.log('[SW] Dynamic request failed:', request.url);
        
        // For critical operations, we might want to queue them
        if (request.method === 'POST' || request.method === 'PUT') {
            await queueRequest(request);
        }
        
        return new Response(
            JSON.stringify({
                error: 'Offline',
                message: 'Request queued for when connection is restored',
                queued: true
            }),
            {
                status: 202,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

// Queue requests for background sync
async function queueRequest(request) {
    try {
        const cache = await caches.open('offline-queue');
        const queuedRequest = {
            url: request.url,
            method: request.method,
            headers: Object.fromEntries(request.headers.entries()),
            body: request.method !== 'GET' ? await request.text() : null,
            timestamp: Date.now()
        };
        
        await cache.put(
            `/queue/${Date.now()}`,
            new Response(JSON.stringify(queuedRequest))
        );
        
        console.log('[SW] Request queued:', request.url);
    } catch (error) {
        console.error('[SW] Failed to queue request:', error);
    }
}

// Background sync event
self.addEventListener('sync', event => {
    console.log('[SW] Background sync triggered:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(processQueuedRequests());
    }
});

// Process queued requests when online
async function processQueuedRequests() {
    try {
        const cache = await caches.open('offline-queue');
        const keys = await cache.keys();
        
        for (const key of keys) {
            try {
                const response = await cache.match(key);
                const queuedRequest = await response.json();
                
                // Replay the request
                await fetch(queuedRequest.url, {
                    method: queuedRequest.method,
                    headers: queuedRequest.headers,
                    body: queuedRequest.body
                });
                
                // Remove from queue
                await cache.delete(key);
                console.log('[SW] Processed queued request:', queuedRequest.url);
            } catch (error) {
                console.error('[SW] Failed to process queued request:', error);
            }
        }
    } catch (error) {
        console.error('[SW] Failed to process queue:', error);
    }
}

// Push notification event
self.addEventListener('push', event => {
    console.log('[SW] Push message received');
    
    let notificationData = {
        title: 'MoxNAS',
        body: 'You have a new notification',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge-72x72.png',
        tag: 'general'
    };
    
    if (event.data) {
        try {
            const data = event.data.json();
            notificationData = { ...notificationData, ...data };
        } catch (error) {
            console.error('[SW] Failed to parse push data:', error);
        }
    }
    
    event.waitUntil(
        self.registration.showNotification(notificationData.title, {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            tag: notificationData.tag,
            data: notificationData.data,
            actions: notificationData.actions || []
        })
    );
});

// Notification click event
self.addEventListener('notificationclick', event => {
    console.log('[SW] Notification clicked:', event.notification.tag);
    
    event.notification.close();
    
    // Handle notification actions
    if (event.action) {
        handleNotificationAction(event.action, event.notification.data);
    } else {
        // Default action - open the app
        event.waitUntil(
            clients.matchAll({ type: 'window' }).then(clientList => {
                for (const client of clientList) {
                    if (client.url.includes(self.location.origin) && 'focus' in client) {
                        return client.focus();
                    }
                }
                
                if (clients.openWindow) {
                    return clients.openWindow('/');
                }
            })
        );
    }
});

// Handle notification actions
function handleNotificationAction(action, data) {
    switch (action) {
        case 'view-alerts':
            clients.openWindow('/monitoring/alerts');
            break;
        case 'view-storage':
            clients.openWindow('/storage');
            break;
        default:
            clients.openWindow('/');
    }
}

// Create offline page HTML
function createOfflinePage() {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Offline - MoxNAS</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            text-align: center;
            padding: 50px;
            background: #f8f9fa;
        }
        .offline-container {
            max-width: 500px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .offline-icon {
            font-size: 4rem;
            margin-bottom: 20px;
            color: #6c757d;
        }
        h1 { color: #343a40; margin-bottom: 20px; }
        p { color: #6c757d; margin-bottom: 30px; }
        .btn {
            background: #007bff;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1rem;
        }
        .btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="offline-container">
        <div class="offline-icon">📡</div>
        <h1>You're Offline</h1>
        <p>It looks like you've lost your connection. Don't worry - some features of MoxNAS are still available offline.</p>
        <button class="btn" onclick="window.location.reload()">Try Again</button>
    </div>
</body>
</html>
    `;
}

// Message event for communication with main app
self.addEventListener('message', event => {
    console.log('[SW] Message received:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('[SW] Service worker loaded');