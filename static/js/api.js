/**
 * MoxNAS API Client
 * Handles all API communication with the backend
 */

class MoxNASAPI {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
        this.cache = new Map();
        this.cacheTimeout = 30000; // 30 seconds
    }

    /**
     * Make HTTP request with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            return { success: true, data };
        } catch (error) {
            console.error(`API request failed for ${endpoint}:`, error);
            return { success: false, error: error.message };
        }
    }

    /**
     * GET request with caching
     */
    async get(endpoint, useCache = true) {
        const cacheKey = `GET:${endpoint}`;
        
        if (useCache && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return { success: true, data: cached.data };
            }
        }

        const result = await this.request(endpoint);
        
        if (result.success && useCache) {
            this.cache.set(cacheKey, {
                data: result.data,
                timestamp: Date.now()
            });
        }
        
        return result;
    }

    /**
     * POST request
     */
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE request
     */
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }

    /**
     * Clear cache
     */
    clearCache(pattern = null) {
        if (pattern) {
            for (const key of this.cache.keys()) {
                if (key.includes(pattern)) {
                    this.cache.delete(key);
                }
            }
        } else {
            this.cache.clear();
        }
    }

    // System Stats API
    async getSystemStats() {
        return this.get('/system-stats', false); // Don't cache real-time stats
    }

    // Services API
    async getServices() {
        return this.get('/services');
    }

    async restartService(serviceName) {
        const result = await this.post(`/services/${serviceName}/restart`);
        if (result.success) {
            this.clearCache('services');
        }
        return result;
    }

    // Shares API
    async getShares() {
        return this.get('/shares');
    }

    async createShare(shareData) {
        const result = await this.post('/shares', shareData);
        if (result.success) {
            this.clearCache('shares');
        }
        return result;
    }

    async deleteShare(shareName) {
        const result = await this.delete(`/shares/${shareName}`);
        if (result.success) {
            this.clearCache('shares');
        }
        return result;
    }

    // Storage API
    async getStorageInfo() {
        return this.get('/storage');
    }

    async getMountPoints() {
        return this.get('/storage/mounts');
    }

    // Network API
    async getNetworkInfo() {
        return this.get('/network');
    }

    // Users API
    async getUsers() {
        return this.get('/users');
    }

    async createUser(userData) {
        const result = await this.post('/users', userData);
        if (result.success) {
            this.clearCache('users');
        }
        return result;
    }

    async deleteUser(username) {
        const result = await this.delete(`/users/${username}`);
        if (result.success) {
            this.clearCache('users');
        }
        return result;
    }

    // Logs API
    async getLogs(service, lines = 100) {
        return this.get(`/logs/${service}?lines=${lines}`, false);
    }
}

// Global API instance
window.moxnasAPI = new MoxNASAPI();