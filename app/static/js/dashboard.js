/**
 * Dashboard Real-time Component
 * Manages real-time system monitoring dashboard
 */

import { Component } from './moxnas-core.js';

class DashboardComponent extends Component {
    init() {
        this.charts = new Map();
        this.updateInterval = 5000; // 5 seconds
        this.lastUpdate = null;
        
        this.initCharts();
        this.startRealTimeUpdates();
        this.bindEvents();
    }
    
    initCharts() {
        // CPU Usage Chart
        if (document.getElementById('cpuChart')) {
            this.charts.set('cpu', new Chart(document.getElementById('cpuChart'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'CPU Usage %',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        },
                        x: {
                            display: false
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    elements: {
                        point: {
                            radius: 0
                        }
                    }
                }
            }));
        }
        
        // Memory Usage Chart
        if (document.getElementById('memoryChart')) {
            this.charts.set('memory', new Chart(document.getElementById('memoryChart'), {
                type: 'doughnut',
                data: {
                    labels: ['Used', 'Available'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: [
                            'rgba(255, 99, 132, 0.8)',
                            'rgba(201, 203, 207, 0.3)'
                        ],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            }));
        }
        
        // Storage Usage Chart
        if (document.getElementById('storageChart')) {
            this.charts.set('storage', new Chart(document.getElementById('storageChart'), {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Used %',
                        data: [],
                        backgroundColor: 'rgba(75, 192, 192, 0.8)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            }));
        }
    }
    
    async startRealTimeUpdates() {
        try {
            await this.updateDashboard();
            setTimeout(() => this.startRealTimeUpdates(), this.updateInterval);
        } catch (error) {
            console.error('Dashboard update failed:', error);
            // Exponential backoff on error
            setTimeout(() => this.startRealTimeUpdates(), this.updateInterval * 2);
        }
    }
    
    async updateDashboard() {
        const data = await window.moxnas.api.get('/monitoring/system');
        
        this.updateSystemStats(data.system);
        this.updateCharts(data);
        this.updateAlerts(data.alerts);
        
        this.lastUpdate = new Date();
        this.updateLastUpdateTime();
    }
    
    updateSystemStats(system) {
        // Update system stat cards
        const stats = [
            { id: 'cpu-usage', value: `${system.cpu_percent}%` },
            { id: 'memory-usage', value: `${system.memory_percent}%` },
            { id: 'disk-usage', value: `${system.disk_percent}%` },
            { id: 'network-io', value: `${this.formatBytes(system.network_io)}/s` },
            { id: 'uptime', value: this.formatUptime(system.uptime) }
        ];
        
        stats.forEach(stat => {
            const element = document.getElementById(stat.id);
            if (element) {
                element.textContent = stat.value;
                
                // Add animation class
                element.classList.add('stat-updated');
                setTimeout(() => element.classList.remove('stat-updated'), 500);
            }
        });
    }
    
    updateCharts(data) {
        // Update CPU chart
        const cpuChart = this.charts.get('cpu');
        if (cpuChart) {
            const now = new Date().toLocaleTimeString();
            cpuChart.data.labels.push(now);
            cpuChart.data.datasets[0].data.push(data.system.cpu_percent);
            
            // Keep only last 20 data points
            if (cpuChart.data.labels.length > 20) {
                cpuChart.data.labels.shift();
                cpuChart.data.datasets[0].data.shift();
            }
            
            cpuChart.update('none'); // No animation for real-time updates
        }
        
        // Update memory chart
        const memoryChart = this.charts.get('memory');
        if (memoryChart) {
            const used = data.system.memory_percent;
            const available = 100 - used;
            memoryChart.data.datasets[0].data = [used, available];
            memoryChart.update('none');
        }
        
        // Update storage chart
        const storageChart = this.charts.get('storage');
        if (storageChart && data.storage) {
            storageChart.data.labels = data.storage.map(pool => pool.name);
            storageChart.data.datasets[0].data = data.storage.map(pool => pool.usage_percent);
            storageChart.update('none');
        }
    }
    
    updateAlerts(alerts) {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;
        
        alertContainer.innerHTML = '';
        
        alerts.forEach(alert => {
            const alertElement = this.createAlertElement(alert);
            alertContainer.appendChild(alertElement);
        });
    }
    
    createAlertElement(alert) {
        const div = document.createElement('div');
        div.className = `alert alert-${this.getAlertClass(alert.severity)} alert-dismissible fade show`;
        div.innerHTML = `
            <strong>${alert.title}</strong> ${alert.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        return div;
    }
    
    getAlertClass(severity) {
        const severityMap = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'light'
        };
        return severityMap[severity] || 'info';
    }
    
    updateLastUpdateTime() {
        const updateElement = document.getElementById('last-update');
        if (updateElement && this.lastUpdate) {
            updateElement.textContent = `Last updated: ${this.lastUpdate.toLocaleTimeString()}`;
        }
    }
    
    formatBytes(bytes) {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }
    
    bindEvents() {
        // Refresh button
        this.on('click', '[data-action="refresh"]', () => {
            this.updateDashboard();
        });
        
        // Chart time range selector
        this.on('change', '#time-range', (e) => {
            this.updateInterval = parseInt(e.target.value) * 1000;
        });
    }
    
    destroy() {
        // Clean up charts
        this.charts.forEach(chart => chart.destroy());
        this.charts.clear();
        
        super.destroy();
    }
}

// Register component
if (window.moxnas) {
    window.moxnas.registerComponent('dashboard', DashboardComponent);
}

export default DashboardComponent;
