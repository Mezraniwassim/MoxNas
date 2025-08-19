/**
 * MoxNAS Dashboard Specific JavaScript
 * Real-time monitoring and dashboard interactions
 */

class DashboardManager {
    constructor() {
        this.charts = {};
        this.updateInterval = 5000; // 5 seconds
        this.init();
    }

    init() {
        this.setupRealtimeUpdates();
        this.loadInitialData();
    }

    setupRealtimeUpdates() {
        // Update system stats every 5 seconds
        setInterval(() => this.updateSystemStats(), this.updateInterval);
        
        // Update service status every 10 seconds
        setInterval(() => this.updateServiceStatus(), 10000);
        
        // Update shares list every 30 seconds
        setInterval(() => this.updateSharesList(), 30000);
    }

    async loadInitialData() {
        await Promise.all([
            this.updateSystemStats(),
            this.updateServiceStatus(),
            this.updateSharesList(),
            this.updateStorageInfo(),
            this.updateNetworkInfo()
        ]);
    }

    async updateSystemStats() {
        try {
            const result = await window.moxnasAPI.getSystemStats();
            if (result.success) {
                this.displaySystemStats(result.data);
                this.updateCharts(result.data);
            }
        } catch (error) {
            console.error('Failed to update system stats:', error);
        }
    }

    displaySystemStats(stats) {
        // CPU Stats
        this.updateStatCard('cpu', {
            percentage: stats.cpu?.percent || 0,
            details: {
                cores: stats.cpu?.cores || 0,
                frequency: stats.cpu?.frequency ? `${Math.round(stats.cpu.frequency)}MHz` : 'N/A'
            }
        });

        // Memory Stats
        this.updateStatCard('memory', {
            percentage: stats.memory?.percent || 0,
            details: {
                used: stats.memory?.used || 'N/A',
                total: stats.memory?.total || 'N/A',
                available: stats.memory?.available || 'N/A'
            }
        });

        // Disk Stats
        this.updateStatCard('disk', {
            percentage: stats.disk?.percent || 0,
            details: {
                used: stats.disk?.used || 'N/A',
                total: stats.disk?.total || 'N/A',
                free: stats.disk?.free || 'N/A'
            }
        });

        // System Info
        if (stats.system) {
            this.updateElement('uptime', `Up ${stats.system.uptime}`);
            this.updateElement('processes', `${stats.system.processes} processes`);
        }

        // Network Stats
        if (stats.network) {
            this.updateElement('network-status', 'Connected');
            this.updateElement('network-info', 
                `↓ ${stats.network.bytes_recv} ↑ ${stats.network.bytes_sent}`);
        }

        // Update timestamp
        this.updateElement('lastUpdated', new Date().toLocaleString());
    }

    updateStatCard(type, data) {
        // Update percentage display
        this.updateElement(`${type}-percentage`, Math.round(data.percentage));
        
        // Update progress bar
        const progressBar = document.getElementById(`${type}-progress`);
        if (progressBar) {
            progressBar.style.width = `${Math.min(100, Math.max(0, data.percentage))}%`;
            
            // Color coding based on usage
            const usage = data.percentage;
            if (usage > 90) {
                progressBar.style.background = 'linear-gradient(90deg, #f44336, #d32f2f)';
            } else if (usage > 75) {
                progressBar.style.background = 'linear-gradient(90deg, #ff9800, #f57c00)';
            } else {
                progressBar.style.background = 'linear-gradient(90deg, var(--primary-color), var(--accent-color))';
            }
        }

        // Update details if provided
        if (data.details) {
            Object.entries(data.details).forEach(([key, value]) => {
                this.updateElement(`${type}-${key}`, value);
            });
        }
    }

    async updateServiceStatus() {
        try {
            const result = await window.moxnasAPI.getServices();
            if (result.success) {
                this.displayServiceStatus(result.data);
            }
        } catch (error) {
            console.error('Failed to update service status:', error);
        }
    }

    displayServiceStatus(services) {
        const serviceNames = ['nginx', 'smbd', 'nfs-kernel-server', 'vsftpd'];
        
        serviceNames.forEach(serviceName => {
            const serviceData = services[serviceName];
            if (!serviceData) return;

            const card = document.querySelector(`[data-service="${serviceName}"]`);
            if (!card) return;

            const statusElement = card.querySelector('.status-indicator');
            if (statusElement) {
                statusElement.textContent = serviceData.active ? 'Running' : 'Stopped';
                statusElement.className = `status-indicator ${serviceData.active ? 'active' : 'inactive'}`;
            }

            // Update service card styling based on status
            card.style.borderColor = serviceData.active ? 'var(--success-color)' : 'var(--error-color)';
        });
    }

    async updateSharesList() {
        try {
            const result = await window.moxnasAPI.getShares();
            if (result.success) {
                this.displayQuickSharesInfo(result.data);
            }
        } catch (error) {
            console.error('Failed to update shares list:', error);
        }
    }

    displayQuickSharesInfo(shares) {
        const activeShares = shares.filter(share => share.active).length;
        const totalShares = shares.length;
        
        // Update shares summary in quick actions or info cards
        this.updateElement('shares-count', `${activeShares}/${totalShares} Active`);
        
        // Update shares by type
        const sharesByType = shares.reduce((acc, share) => {
            acc[share.type] = (acc[share.type] || 0) + 1;
            return acc;
        }, {});
        
        this.updateElement('smb-shares', sharesByType.smb || 0);
        this.updateElement('nfs-shares', sharesByType.nfs || 0);
        this.updateElement('ftp-shares', sharesByType.ftp || 0);
    }

    async updateStorageInfo() {
        try {
            const result = await window.moxnasAPI.getStorageInfo();
            if (result.success) {
                this.displayStorageInfo(result.data);
            }
        } catch (error) {
            console.error('Failed to update storage info:', error);
        }
    }

    displayStorageInfo(storage) {
        if (storage.disks && storage.disks.length > 0) {
            const totalStorage = storage.disks.reduce((acc, disk) => {
                // Parse storage sizes (assume they're in bytes or have units)
                return acc + (disk.total || 0);
            }, 0);
            
            this.updateElement('storage-devices', `${storage.disks.length} devices`);
        }
    }

    async updateNetworkInfo() {
        try {
            const result = await window.moxnasAPI.getNetworkInfo();
            if (result.success) {
                this.displayNetworkInfo(result.data);
            }
        } catch (error) {
            console.error('Failed to update network info:', error);
        }
    }

    displayNetworkInfo(network) {
        if (network.interfaces) {
            const activeInterfaces = network.interfaces.filter(iface => 
                iface.addresses.some(addr => addr.address !== '127.0.0.1' && addr.family === 'AddressFamily.AF_INET')
            ).length;
            
            this.updateElement('network-interfaces', `${activeInterfaces} active`);
        }
    }

    updateCharts(stats) {
        // Simple text-based charts for now
        // In a full implementation, you might use Chart.js or similar
        this.updateMiniChart('cpu-chart', stats.cpu?.percent || 0);
        this.updateMiniChart('memory-chart', stats.memory?.percent || 0);
        this.updateMiniChart('disk-chart', stats.disk?.percent || 0);
    }

    updateMiniChart(chartId, percentage) {
        const chartElement = document.getElementById(chartId);
        if (chartElement) {
            // Simple ASCII-style chart
            const bars = Math.round(percentage / 10);
            const chart = '█'.repeat(bars) + '░'.repeat(10 - bars);
            chartElement.textContent = chart;
            chartElement.title = `${percentage.toFixed(1)}%`;
        }
    }

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    // Dashboard-specific actions
    async quickRestartAllServices() {
        if (!confirm('Are you sure you want to restart all NAS services?')) {
            return;
        }

        const services = ['smbd', 'nfs-kernel-server', 'vsftpd'];
        let successCount = 0;

        for (const service of services) {
            try {
                const result = await window.moxnasAPI.restartService(service);
                if (result.success) {
                    successCount++;
                }
            } catch (error) {
                console.error(`Failed to restart ${service}:`, error);
            }
        }

        if (successCount === services.length) {
            window.app.showNotification('All services restarted successfully', 'success');
        } else {
            window.app.showNotification(`${successCount}/${services.length} services restarted`, 'warning');
        }

        // Refresh service status
        setTimeout(() => this.updateServiceStatus(), 2000);
    }

    async createQuickShare() {
        const shareName = prompt('Enter share name:');
        if (!shareName) return;

        const shareData = {
            name: shareName,
            type: 'smb',
            path: `/mnt/shares/${shareName}`,
            guest: true
        };

        try {
            const result = await window.moxnasAPI.createShare(shareData);
            
            if (result.success) {
                window.app.showNotification(`Share "${shareName}" created successfully`, 'success');
                this.updateSharesList();
            } else {
                window.app.showNotification(`Failed to create share: ${result.error}`, 'error');
            }
        } catch (error) {
            window.app.showNotification(`Error creating share: ${error.message}`, 'error');
        }
    }

    // System health check
    async performHealthCheck() {
        window.app.showNotification('Performing system health check...', 'info');

        const checks = [
            { name: 'System Stats', fn: () => window.moxnasAPI.getSystemStats() },
            { name: 'Service Status', fn: () => window.moxnasAPI.getServices() },
            { name: 'Storage Info', fn: () => window.moxnasAPI.getStorageInfo() },
            { name: 'Network Info', fn: () => window.moxnasAPI.getNetworkInfo() }
        ];

        let passedChecks = 0;
        const results = [];

        for (const check of checks) {
            try {
                const result = await check.fn();
                if (result.success) {
                    passedChecks++;
                    results.push(`✅ ${check.name}: OK`);
                } else {
                    results.push(`❌ ${check.name}: Failed`);
                }
            } catch (error) {
                results.push(`❌ ${check.name}: Error - ${error.message}`);
            }
        }

        const healthScore = Math.round((passedChecks / checks.length) * 100);
        let message = `Health Check Complete: ${healthScore}% (${passedChecks}/${checks.length} checks passed)`;
        
        const notificationType = healthScore === 100 ? 'success' : healthScore >= 75 ? 'warning' : 'error';
        window.app.showNotification(message, notificationType, 8000);

        // Log detailed results to console
        console.log('Health Check Results:', results);
    }
}

// Global dashboard functions
window.quickRestartAllServices = () => {
    if (window.dashboardManager) {
        window.dashboardManager.quickRestartAllServices();
    }
};

window.createQuickShare = () => {
    if (window.dashboardManager) {
        window.dashboardManager.createQuickShare();
    }
};

window.performHealthCheck = () => {
    if (window.dashboardManager) {
        window.dashboardManager.performHealthCheck();
    }
};

// Initialize dashboard manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize on dashboard page
    if (document.querySelector('.dashboard') || document.body.classList.contains('dashboard-page')) {
        window.dashboardManager = new DashboardManager();
    }
});