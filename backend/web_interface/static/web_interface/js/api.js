/**
 * MoxNAS API Client
 * Provides a simple interface for communicating with the Django REST API
 */

class MoxNASAPI {
    constructor(baseUrl = 'http://localhost:8000/api') {
        this.baseUrl = baseUrl;
        this.token = localStorage.getItem('moxnas_token');
    }

    /**
     * Set authentication token
     */
    setToken(token) {
        this.token = token;
        localStorage.setItem('moxnas_token', token);
    }

    /**
     * Clear authentication token
     */
    clearToken() {
        this.token = null;
        localStorage.removeItem('moxnas_token');
    }

    /**
     * Make authenticated API request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Token ${this.token}`;
        }

        const config = {
            headers,
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                this.clearToken();
                throw new Error('Authentication required');
            }
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(errorData?.detail || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
            
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    /**
     * GET request
     */
    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url, { method: 'GET' });
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
     * PATCH request
     */
    async patch(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE request
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // Storage API endpoints
    async getStoragePools() {
        return this.get('/storage/pools/');
    }

    async createStoragePool(data) {
        return this.post('/storage/pools/', data);
    }

    async getStoragePool(id) {
        return this.get(`/storage/pools/${id}/`);
    }

    async updateStoragePool(id, data) {
        return this.put(`/storage/pools/${id}/`, data);
    }

    async deleteStoragePool(id) {
        return this.delete(`/storage/pools/${id}/`);
    }

    async getDatasets() {
        return this.get('/storage/datasets/');
    }

    async createDataset(data) {
        return this.post('/storage/datasets/', data);
    }

    async getDataset(id) {
        return this.get(`/storage/datasets/${id}/`);
    }

    async updateDataset(id, data) {
        return this.put(`/storage/datasets/${id}/`, data);
    }

    async deleteDataset(id) {
        return this.delete(`/storage/datasets/${id}/`);
    }

    async getShares() {
        return this.get('/storage/shares/');
    }

    async createShare(data) {
        return this.post('/storage/shares/', data);
    }

    async getShare(id) {
        return this.get(`/storage/shares/${id}/`);
    }

    async updateShare(id, data) {
        return this.put(`/storage/shares/${id}/`, data);
    }

    async deleteShare(id) {
        return this.delete(`/storage/shares/${id}/`);
    }

    // Network API endpoints
    async getNetworkInterfaces() {
        return this.get('/network/interfaces/');
    }

    async updateNetworkInterface(id, data) {
        return this.put(`/network/interfaces/${id}/`, data);
    }

    async getNetworkServices() {
        return this.get('/network/services/');
    }

    async updateNetworkService(serviceName, data) {
        return this.put(`/network/services/${serviceName}/`, data);
    }

    // Enhanced Network API endpoints
    async getSMBService() {
        return this.get('/network/smb/');
    }

    async manageSMBService(action) {
        return this.post('/network/smb/manage_service/', { action });
    }

    async getSMBShares() {
        return this.get('/network/smb/shares/');
    }

    async getSMBSessions() {
        return this.get('/network/smb/sessions/');
    }

    async testSMBShare(shareName) {
        return this.post('/network/smb/test_share/', { share_name: shareName });
    }

    async reloadSMBConfig() {
        return this.post('/network/smb/reload_config/');
    }

    async getNFSService() {
        return this.get('/network/nfs/');
    }

    async manageNFSService(action) {
        return this.post('/network/nfs/manage_service/', { action });
    }

    async getNFSExports() {
        return this.get('/network/nfs/exports/');
    }

    async getNFSMounts() {
        return this.get('/network/nfs/mounts/');
    }

    async exportNFSPath(path, client = '*', options = ['rw', 'sync', 'no_subtree_check']) {
        return this.post('/network/nfs/export_path/', { path, client, options });
    }

    async unexportNFSPath(path) {
        return this.post('/network/nfs/unexport_path/', { path });
    }

    async getFTPService() {
        return this.get('/network/ftp/');
    }

    async manageFTPService(action) {
        return this.post('/network/ftp/manage_service/', { action });
    }

    async getFTPConnections() {
        return this.get('/network/ftp/connections/');
    }

    async testFTPLogin(username = 'anonymous', password = '') {
        return this.post('/network/ftp/test_login/', { username, password });
    }

    async getSSHService() {
        return this.get('/network/ssh/');
    }

    async manageSSHService(action) {
        return this.post('/network/ssh/manage_service/', { action });
    }

    async getSSHSessions() {
        return this.get('/network/ssh/sessions/');
    }

    async getSSHFailedLogins(lines = 50) {
        return this.get('/network/ssh/failed_logins/', { lines });
    }

    async getFirewallStatus() {
        return this.get('/network/firewall/');
    }

    async openFirewallPort(port, protocol = 'tcp') {
        return this.post('/network/firewall/open_port/', { port, protocol });
    }

    async getNetworkInterfaceStats(interfaceName) {
        return this.get('/network/interfaces/live_stats/', { interface: interfaceName });
    }

    async testNetworkConnectivity(host, timeout = 5) {
        return this.post('/network/interfaces/test_connectivity/', { host, timeout });
    }

    // System API endpoints
    async getSystemInfo() {
        return this.get('/system/info/');
    }

    async getSystemServices() {
        return this.get('/system/services/');
    }

    async updateSystemService(id, data) {
        return this.put(`/system/services/${id}/`, data);
    }

    async startSystemService(id) {
        return this.post(`/system/services/${id}/start/`);
    }

    async stopSystemService(id) {
        return this.post(`/system/services/${id}/stop/`);
    }

    async restartSystemService(id) {
        return this.post(`/system/services/${id}/restart/`);
    }

    async getCronJobs() {
        return this.get('/system/cron-jobs/');
    }

    async createCronJob(data) {
        return this.post('/system/cron-jobs/', data);
    }

    async updateCronJob(id, data) {
        return this.put(`/system/cron-jobs/${id}/`, data);
    }

    async deleteCronJob(id) {
        return this.delete(`/system/cron-jobs/${id}/`);
    }

    async getSyncTasks() {
        return this.get('/system/sync-tasks/');
    }

    async createSyncTask(data) {
        return this.post('/system/sync-tasks/', data);
    }

    async updateSyncTask(id, data) {
        return this.put(`/system/sync-tasks/${id}/`, data);
    }

    async deleteSyncTask(id) {
        return this.delete(`/system/sync-tasks/${id}/`);
    }

    async runSyncTask(id) {
        return this.post(`/system/sync-tasks/${id}/run/`);
    }

    // Monitoring endpoints
    async getSystemMonitoring() {
        return this.get('/system/monitoring/');
    }

    async getSystemLogs(params = {}) {
        return this.get('/system/logs/', params);
    }

    // Authentication endpoints
    async login(username, password) {
        try {
            const response = await this.post('/auth/login/', {
                username,
                password
            });
            
            if (response.token) {
                this.setToken(response.token);
            }
            
            return response;
        } catch (error) {
            this.clearToken();
            throw error;
        }
    }

    async logout() {
        try {
            await this.post('/auth/logout/');
        } catch (error) {
            console.warn('Logout error:', error);
        } finally {
            this.clearToken();
        }
    }

    async getCurrentUser() {
        return this.get('/auth/user/');
    }

    // Utility methods
    async checkAPIStatus() {
        try {
            const response = await fetch(`${this.baseUrl.replace('/api', '')}/api/status/`);
            return await response.json();
        } catch (error) {
            console.error('API status check failed:', error);
            return { status: 'offline' };
        }
    }

    async uploadFile(endpoint, file, progressCallback = null) {
        const formData = new FormData();
        formData.append('file', file);

        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Token ${this.token}`;
        }

        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers,
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Upload error:', error);
            throw error;
        }
    }
}

// Export for use in main application
window.MoxNASAPI = MoxNASAPI;
