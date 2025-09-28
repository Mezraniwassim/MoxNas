class MoxNASApp {
    constructor() {
        this.charts = new Map();
        this.init();
    }

    init() {
        document.addEventListener('DOMContentLoaded', () => {
            this.initTooltips();
            this.initRealTimeUpdates();
            this.bindGlobalEvents();
        });
    }

    initTooltips() {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }

    initRealTimeUpdates() {
        this.socket = io();

        this.socket.on('connect', () => {
            console.log('Connected to MoxNAS WebSocket');
            document.getElementById('connection-status').innerHTML = '<i class="bi bi-circle-fill text-success" title="Online"></i>';
            this.subscribeToChannels();
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from MoxNAS WebSocket');
            document.getElementById('connection-status').innerHTML = '<i class="bi bi-circle-fill text-danger" title="Offline"></i>';
        });

        this.socket.on('system_stats', data => this.updateDashboard(data));
        this.socket.on('storage_status', data => this.updateStorageStatus(data));
        this.socket.on('new_alert', data => this.showAlert(data.message, this.getAlertType(data.severity)));
    }

    subscribeToChannels() {
        this.socket.emit('subscribe', { type: 'system' });
        this.socket.emit('subscribe', { type: 'storage' });
        this.socket.emit('subscribe', { type: 'alerts' });
    }

    bindGlobalEvents() {
        // Confirm dialogs
        document.querySelectorAll('[data-confirm]').forEach(element => {
            element.addEventListener('click', (e) => {
                if (!confirm(element.dataset.confirm)) {
                    e.preventDefault();
                }
            });
        });

        // Auto-hide alerts
        document.querySelectorAll('.alert[data-auto-hide]').forEach(alert => {
            setTimeout(() => alert.classList.add('fade'), 5000);
        });
    }

    showAlert(message, type = 'info', timeout = 5000) {
        const alertContainer = document.querySelector('.main-content .container-fluid');
        if (!alertContainer) return;

        const alertEl = document.createElement('div');
        alertEl.className = `alert alert-${type} alert-dismissible fade show`;
        alertEl.role = 'alert';
        alertEl.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        alertContainer.prepend(alertEl);

        if (timeout > 0) {
            setTimeout(() => {
                const alertInstance = bootstrap.Alert.getOrCreateInstance(alertEl);
                if (alertInstance) {
                    alertInstance.close();
                }
            }, timeout);
        }
    }

    getAlertType(severity) {
        switch (severity) {
            case 'critical': return 'danger';
            case 'warning': return 'warning';
            case 'info': return 'info';
            default: return 'secondary';
        }
    }

    updateDashboard(stats) {
        if (!stats || !stats.cpu) return;

        this.updateStatsCards(stats);
        this.updatePerformanceChart(stats);
    }

    updateStatsCards(stats) {
        this.updateCard('cpu-usage', `${stats.cpu.percent.toFixed(1)}%`, stats.cpu.percent, 80, 90);
        this.updateCard('memory-usage', `${stats.memory.percent.toFixed(1)}%`, stats.memory.percent, 80, 90);
        if (stats.disk) {
            this.updateCard('disk-usage', `${stats.disk.percent.toFixed(1)}%`, stats.disk.percent, 85, 95);
        }
    }

    updateCard(elementId, text, value, warn, crit) {
        const element = document.getElementById(elementId);
        if (!element) return;

        element.textContent = text;
        const card = element.closest('.card');
        if (!card) return;

        card.classList.remove('border-left-primary', 'border-left-success', 'border-left-warning', 'border-left-danger');
        if (value >= crit) {
            card.classList.add('border-left-danger');
        } else if (value >= warn) {
            card.classList.add('border-left-warning');
        } else {
            card.classList.add('border-left-success');
        }
    }

    updatePerformanceChart(stats) {
        const chart = this.charts.get('performanceChart');
        if (!chart) return;

        const now = new Date().toLocaleTimeString();
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(stats.cpu.percent);
        chart.data.datasets[1].data.push(stats.memory.percent);

        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets.forEach(dataset => dataset.data.shift());
        }
        chart.update('none');
    }

    updateStorageStatus(data) {
        if (data.error) return;

        data.pools.forEach(pool => {
            const poolElement = document.getElementById(`pool-${pool.id}-status`);
            if (poolElement) {
                poolElement.className = `status-indicator ${pool.status}`;
                poolElement.title = `${pool.name}: ${pool.status}`;
            }
            const usageElement = document.getElementById(`pool-${pool.id}-usage`);
            if (usageElement) {
                usageElement.textContent = `${pool.usage_percent.toFixed(1)}%`;
            }
        });
    }

    createChart(canvasId, type, data, options) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;

        const chart = new Chart(canvas, { type, data, options });
        this.charts.set(canvasId, chart);
        return chart;
    }

    async _post(url, data) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(data)
            });
            return await response.json();
        } catch (error) {
            this.showAlert('Request failed: ' + error, 'danger');
            return { success: false, error: 'Request failed' };
        }
    }

    scanDevices() {
        this.showAlert('Scanning storage devices...', 'info');
        this._post('/storage/devices/scan').then(data => {
            if (data.success) {
                this.showAlert(data.message, 'success');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                this.showAlert(data.error, 'danger');
            }
        });
    }

    startPoolScrub(poolId) {
        if (!confirm('Start scrubbing this storage pool? This may take several hours.')) return;
        this.showAlert('Starting pool scrub...', 'info');
        this._post(`/storage/pools/${poolId}/scrub`).then(data => {
            if (data.success) {
                this.showAlert(data.message, 'success');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                this.showAlert(data.error, 'danger');
            }
        });
    }

    deletePool(poolId, poolName) {
        if (!confirm(`Are you sure you want to delete pool \"${poolName}\"? This action cannot be undone and will permanently destroy all data.`)) return;
        if (prompt('Type \"DELETE\" to confirm:') !== 'DELETE') return;

        this.showAlert('Deleting storage pool...', 'warning');
        this._post(`/storage/pools/${poolId}/delete`).then(data => {
            if (data.success) {
                this.showAlert(data.message, 'success');
                setTimeout(() => window.location.href = '/storage/pools', 2000);
            } else {
                this.showAlert(data.error, 'danger');
            }
        });
    }

    toggleShare(shareId, shareName) {
        this.showAlert(`Toggling share \"${shareName}\"...`, 'info');
        this._post(`/shares/${shareId}/toggle`).then(data => {
            if (data.success) {
                this.showAlert(data.message, 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                this.showAlert(data.error, 'danger');
            }
        });
    }

    deleteShare(shareId, shareName) {
        if (!confirm(`Are you sure you want to delete share \"${shareName}\"?`)) return;
        this.showAlert('Deleting share...', 'warning');
        this._post(`/shares/${shareId}/delete`).then(data => {
            if (data.success) {
                this.showAlert(data.message, 'success');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                this.showAlert(data.error, 'danger');
            }
        });
    }

    startBackup(jobId, jobName) {
        if (!confirm(`Start backup job \"${jobName}\"?`)) return;
        this.showAlert('Starting backup...', 'info');
        this._post(`/backups/${jobId}/start`).then(data => {
            if (data.success) {
                this.showAlert(data.message, 'success');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                this.showAlert(data.error, 'danger');
            }
        });
    }

    stopBackup(jobId, jobName) {
        if (!confirm(`Stop backup job \"${jobName}\"?`)) return;
        this.showAlert('Stopping backup...', 'warning');
        this._post(`/backups/${jobId}/stop`).then(data => {
            if (data.success) {
                this.showAlert(data.message, 'success');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                this.showAlert(data.error, 'danger');
            }
        });
    }

    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showAlert('Copied to clipboard', 'success', 2000);
        }).catch(() => {
            this.showAlert('Failed to copy to clipboard', 'danger');
        });
    }
}

window.moxnas = new MoxNASApp();

// Dashboard-specific logic
if (document.getElementById('performanceChart')) {
    const performanceData = {
        labels: [],
        datasets: [{
            label: 'CPU %',
            data: [],
            borderColor: 'rgb(75, 192, 192)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            fill: true,
            tension: 0.2
        }, {
            label: 'Memory %',
            data: [],
            borderColor: 'rgb(255, 99, 132)',
            backgroundColor: 'rgba(255, 99, 132, 0.1)',
            fill: true,
            tension: 0.2
        }]
    };

    const performanceOptions = {
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                ticks: { callback: value => value + '%' }
            }
        },
        plugins: {
            tooltip: {
                callbacks: {
                    label: context => `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`
                }
            }
        },
        interaction: { intersect: false, mode: 'index' }
    };

    window.moxnas.createChart('performanceChart', 'line', performanceData, performanceOptions);
}

// Global utility functions
window.scanDevices = () => window.moxnas.scanDevices();
window.startPoolScrub = (poolId) => window.moxnas.startPoolScrub(poolId);
window.deletePool = (poolId, poolName) => window.moxnas.deletePool(poolId, poolName);
window.toggleShare = (shareId, shareName) => window.moxnas.toggleShare(shareId, shareName);
window.deleteShare = (shareId, shareName) => window.moxnas.deleteShare(shareId, shareName);
window.startBackup = (jobId, jobName) => window.moxnas.startBackup(jobId, jobName);
window.stopBackup = (jobId, jobName) => window.moxnas.stopBackup(jobId, jobName);
window.copyToClipboard = (text) => window.moxnas.copyToClipboard(text);