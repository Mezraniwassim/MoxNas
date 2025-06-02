/**
 * API Communication Module for MoxNAS
 * Handles all API requests to the Django backend
 */

class MoxNASAPI {
    constructor() {
        this.baseUrl = 'http://localhost:8000/api';
        this.timeout = 10000; // 10 seconds
    }

    /**
     * Make an HTTP request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            timeout: this.timeout,
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    /**
     * GET request
     */
    async get(endpoint, params = {}) {
        const url = new URL(`${this.baseUrl}${endpoint}`);
        Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
        
        return this.request(endpoint, {
            method: 'GET'
        });
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
     * PUT request
     */
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
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

    // Storage API endpoints
    async getStoragePools() {
        return this.get('/storage/pools/');
    }

    async createStoragePool(data) {
        return this.post('/storage/pools/', data);
    }

    async getStoragePool(poolId) {
        return this.get(`/storage/pools/${poolId}/`);
    }

    async updateStoragePool(poolId, data) {
        return this.put(`/storage/pools/${poolId}/`, data);
    }

    async deleteStoragePool(poolId) {
        return this.delete(`/storage/pools/${poolId}/`);
    }

    // Shares API endpoints
    async getShares() {
        return this.get('/shares/');
    }

    async createShare(data) {
        return this.post('/shares/', data);
    }

    async getShare(shareId) {
        return this.get(`/shares/${shareId}/`);
    }

    async updateShare(shareId, data) {
        return this.put(`/shares/${shareId}/`, data);
    }

    async deleteShare(shareId) {
        return this.delete(`/shares/${shareId}/`);
    }

    // Network API endpoints
    async getNetworkInterfaces() {
        return this.get('/network/interfaces/');
    }

    async createNetworkInterface(data) {
        return this.post('/network/interfaces/', data);
    }

    async updateNetworkInterface(interfaceId, data) {
        return this.put(`/network/interfaces/${interfaceId}/`, data);
    }

    async deleteNetworkInterface(interfaceId) {
        return this.delete(`/network/interfaces/${interfaceId}/`);
    }

    async getNetworkServices() {
        return this.get('/network/services/');
    }

    async toggleNetworkService(serviceName, enabled) {
        return this.post(`/network/services/${serviceName}/toggle/`, { enabled });
    }

    // System API endpoints
    async getSystemInfo() {
        return this.get('/system/info/');
    }

    async getSystemServices() {
        return this.get('/system/services/');
    }

    async getSystemStats() {
        return this.get('/system/stats/');
    }

    // Proxmox API endpoints
    async getProxmoxNodes() {
        return this.get('/proxmox/api/nodes/');
    }

    async getProxmoxContainers() {
        return this.get('/proxmox/api/containers/');
    }

    async createProxmoxContainer(data) {
        return this.post('/proxmox/api/containers/', data);
    }

    async getProxmoxTemplates() {
        return this.get('/proxmox/api/templates/');
    }

    async getProxmoxStorage() {
        return this.get('/proxmox/api/storage/');
    }

    // Tasks API endpoints
    async getTasks() {
        return this.get('/tasks/');
    }

    async createTask(data) {
        return this.post('/tasks/', data);
    }

    async updateTask(taskId, data) {
        return this.put(`/tasks/${taskId}/`, data);
    }

    async deleteTask(taskId) {
        return this.delete(`/tasks/${taskId}/`);
    }

    async runTask(taskId) {
        return this.post(`/tasks/${taskId}/run/`);
    }
}

// Create global API instance
window.moxnasAPI = new MoxNASAPI();
