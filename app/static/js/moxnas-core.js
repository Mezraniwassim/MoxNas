/**
 * MoxNAS Modern JavaScript Architecture
 * ES6+ Module System with Real-time Updates
 */

// Application State Management
class AppState {
    constructor() {
        this.state = new Proxy({}, {
            set: (target, property, value) => {
                target[property] = value;
                this.notifySubscribers(property, value);
                return true;
            }
        });
        this.subscribers = new Map();
    }
    
    subscribe(property, callback) {
        if (!this.subscribers.has(property)) {
            this.subscribers.set(property, new Set());
        }
        this.subscribers.get(property).add(callback);
    }
    
    unsubscribe(property, callback) {
        if (this.subscribers.has(property)) {
            this.subscribers.get(property).delete(callback);
        }
    }
    
    notifySubscribers(property, value) {
        if (this.subscribers.has(property)) {
            this.subscribers.get(property).forEach(callback => callback(value));
        }
    }
    
    setState(property, value) {
        this.state[property] = value;
    }
    
    getState(property) {
        return this.state[property];
    }
}

// WebSocket Manager for Real-time Updates
class WebSocketManager {
    constructor(url) {
        this.url = url;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.eventHandlers = new Map();
    }
    
    connect() {
        try {
            this.socket = new WebSocket(this.url);
            
            this.socket.onopen = (event) => {
                console.log('🔗 WebSocket connected');
                this.reconnectAttempts = 0;
                this.emit('connected', event);
            };
            
            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.emit(data.type || 'message', data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.socket.onclose = (event) => {
                console.log('🔌 WebSocket disconnected');
                this.emit('disconnected', event);
                this.attemptReconnect();
            };
            
            this.socket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.emit('error', error);
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
            
            console.log(`🔄 Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`);
            
            setTimeout(() => {
                this.connect();
            }, delay);
        } else {
            console.error('❌ Max reconnection attempts reached');
            this.emit('maxReconnectReached');
        }
    }
    
    on(event, handler) {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, new Set());
        }
        this.eventHandlers.get(event).add(handler);
    }
    
    off(event, handler) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).delete(handler);
        }
    }
    
    emit(event, data) {
        if (this.eventHandlers.has(event)) {
            this.eventHandlers.get(event).forEach(handler => handler(data));
        }
    }
    
    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(data));
        } else {
            console.warn('WebSocket not connected, message not sent:', data);
        }
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
        }
    }
}

// API Client with Error Handling and Retry Logic
class APIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
        this.defaultHeaders = {
            'Content-Type': 'application/json',
            'X-CSRFToken': this.getCSRFToken()
        };
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name=csrf-token]');
        return token ? token.getAttribute('content') : '';
    }
    
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: { ...this.defaultHeaders, ...options.headers },
            ...options
        };
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
            
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }
    
    async get(endpoint, params = {}) {
        const url = new URL(endpoint, window.location.origin + this.baseURL);
        Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
        return this.request(url.pathname + url.search);
    }
    
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }
    
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }
}

// Component System for Modular UI
class Component {
    constructor(element, options = {}) {
        this.element = typeof element === 'string' ? document.querySelector(element) : element;
        this.options = options;
        this.eventListeners = [];
        
        if (this.element) {
            this.init();
        }
    }
    
    init() {
        // Override in subclasses
    }
    
    on(event, selector, handler) {
        const listener = (e) => {
            if (e.target.matches(selector)) {
                handler.call(e.target, e);
            }
        };
        
        this.element.addEventListener(event, listener);
        this.eventListeners.push({ event, listener });
    }
    
    emit(eventName, data = {}) {
        const event = new CustomEvent(eventName, { detail: data });
        this.element.dispatchEvent(event);
    }
    
    destroy() {
        this.eventListeners.forEach(({ event, listener }) => {
            this.element.removeEventListener(event, listener);
        });
        this.eventListeners = [];
    }
}

// Performance Monitor
class PerformanceMonitor {
    constructor() {
        this.metrics = new Map();
        this.observers = [];
    }
    
    startTiming(name) {
        this.metrics.set(name, { start: performance.now() });
    }
    
    endTiming(name) {
        const metric = this.metrics.get(name);
        if (metric) {
            metric.duration = performance.now() - metric.start;
            metric.end = performance.now();
        }
    }
    
    getMetric(name) {
        return this.metrics.get(name);
    }
    
    getAllMetrics() {
        return Object.fromEntries(this.metrics);
    }
    
    observePageLoad() {
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    console.log(`📊 ${entry.name}: ${entry.duration.toFixed(2)}ms`);
                }
            });
            
            observer.observe({ entryTypes: ['navigation', 'resource'] });
            this.observers.push(observer);
        }
    }
    
    disconnect() {
        this.observers.forEach(observer => observer.disconnect());
        this.observers = [];
    }
}

// Main Application Class
class MoxNASApp {
    constructor() {
        this.state = new AppState();
        this.api = new APIClient();
        this.ws = null;
        this.components = new Map();
        this.performance = new PerformanceMonitor();
        
        this.init();
    }
    
    init() {
        console.log('🚀 MoxNAS App Initializing...');
        
        // Start performance monitoring
        this.performance.observePageLoad();
        this.performance.startTiming('appInit');
        
        // Initialize WebSocket if available
        this.initWebSocket();
        
        // Initialize components
        this.initComponents();
        
        // Setup global error handling
        this.setupErrorHandling();
        
        this.performance.endTiming('appInit');
        console.log('✅ MoxNAS App Initialized');
    }
    
    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/socket.io`;
        
        this.ws = new WebSocketManager(wsUrl);
        this.ws.on('connected', () => {
            this.state.setState('websocketConnected', true);
        });
        
        this.ws.on('disconnected', () => {
            this.state.setState('websocketConnected', false);
        });
        
        this.ws.connect();
    }
    
    initComponents() {
        // Auto-initialize components with data-component attribute
        document.querySelectorAll('[data-component]').forEach(element => {
            const componentName = element.getAttribute('data-component');
            if (this[`init${componentName}`]) {
                this[`init${componentName}`](element);
            }
        });
    }
    
    setupErrorHandling() {
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
            this.handleError(event.error);
        });
        
        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled promise rejection:', event.reason);
            this.handleError(event.reason);
        });
    }
    
    handleError(error) {
        // Send error to server for logging
        this.api.post('/logs/client-error', {
            error: error.toString(),
            stack: error.stack,
            url: window.location.href,
            timestamp: new Date().toISOString()
        }).catch(err => {
            console.error('Failed to log client error:', err);
        });
    }
    
    registerComponent(name, component) {
        this.components.set(name, component);
    }
    
    getComponent(name) {
        return this.components.get(name);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.moxnas = new MoxNASApp();
});

// Export for module use
export { MoxNASApp, Component, APIClient, WebSocketManager, PerformanceMonitor };
