/**
 * MoxNAS Main Application JavaScript
 * Core functionality and UI interactions
 */

class MoxNASApp {
    constructor() {
        this.sidebarCollapsed = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.updateClock();
        this.startPeriodicUpdates();
    }

    setupEventListeners() {
        // Sidebar toggle
        const sidebarToggle = document.getElementById('sidebarToggle');
        if (sidebarToggle) {
            sidebarToggle.addEventListener('click', () => this.toggleSidebar());
        }

        // User menu toggle
        const userMenuBtn = document.getElementById('userMenuBtn');
        const userDropdown = document.getElementById('userDropdown');
        if (userMenuBtn && userDropdown) {
            userMenuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                userDropdown.classList.toggle('show');
            });

            // Close user menu when clicking outside
            document.addEventListener('click', () => {
                userDropdown.classList.remove('show');
            });
        }

        // Modal handlers
        this.setupModalHandlers();

        // Form handlers
        this.setupFormHandlers();

        // Service restart buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('.service-btn[data-action="restart"]')) {
                const service = e.target.getAttribute('data-service');
                this.restartService(service);
            }
        });

        // Responsive handling
        this.handleResize();
        window.addEventListener('resize', () => this.handleResize());
    }

    toggleSidebar() {
        const sidebar = document.querySelector('.sidebar');
        if (sidebar) {
            sidebar.classList.toggle('show');
            this.sidebarCollapsed = !this.sidebarCollapsed;
        }
    }

    handleResize() {
        const sidebar = document.querySelector('.sidebar');
        if (window.innerWidth > 1024) {
            if (sidebar) {
                sidebar.classList.remove('show');
            }
            this.sidebarCollapsed = false;
        }
    }

    updateClock() {
        const clockElement = document.getElementById('lastUpdated');
        if (clockElement) {
            clockElement.textContent = new Date().toLocaleString();
        }
    }

    startPeriodicUpdates() {
        // Update clock every minute
        setInterval(() => this.updateClock(), 60000);

        // Update system stats every 5 seconds
        setInterval(() => this.updateSystemStats(), 5000);

        // Update service status every 30 seconds
        setInterval(() => this.updateServiceStatus(), 30000);

        // Initial updates
        this.updateSystemStats();
        this.updateServiceStatus();
    }

    async updateSystemStats() {
        try {
            const result = await window.moxnasAPI.getSystemStats();
            if (result.success) {
                this.displaySystemStats(result.data);
            }
        } catch (error) {
            console.error('Failed to update system stats:', error);
        }
    }

    displaySystemStats(stats) {
        // Update header stats
        this.updateElement('cpu-usage', `${stats.cpu?.percent || '--'}%`);
        this.updateElement('memory-usage', `${stats.memory?.percent || '--'}%`);
        this.updateElement('disk-usage', `${stats.disk?.percent || '--'}%`);

        // Update dashboard stats if present
        this.updateElement('cpu-percentage', stats.cpu?.percent || '--');
        this.updateElement('memory-percentage', stats.memory?.percent || '--');
        this.updateElement('disk-percentage', stats.disk?.percent || '--');

        // Update progress bars
        this.updateProgressBar('cpu-progress', stats.cpu?.percent || 0);
        this.updateProgressBar('memory-progress', stats.memory?.percent || 0);
        this.updateProgressBar('disk-progress', stats.disk?.percent || 0);

        // Update uptime
        if (stats.system?.uptime) {
            this.updateElement('uptime', `Up ${stats.system.uptime}`);
        }

        // Update network status
        if (stats.network) {
            this.updateElement('network-status', 'Online');
            this.updateElement('network-info', 
                `${stats.network.bytes_recv} received, ${stats.network.bytes_sent} sent`);
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
        for (const [serviceName, serviceData] of Object.entries(services)) {
            const statusElement = document.getElementById(`${serviceName}-status`);
            if (statusElement) {
                statusElement.textContent = serviceData.active ? 'Running' : 'Stopped';
                statusElement.className = `status-indicator ${serviceData.active ? 'active' : 'inactive'}`;
            }
        }
    }

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    updateProgressBar(id, percentage) {
        const element = document.getElementById(id);
        if (element) {
            element.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
        }
    }

    async restartService(serviceName) {
        if (!confirm(`Are you sure you want to restart the ${serviceName} service?`)) {
            return;
        }

        try {
            this.showNotification(`Restarting ${serviceName}...`, 'info');
            const result = await window.moxnasAPI.restartService(serviceName);
            
            if (result.success) {
                this.showNotification(`${serviceName} restarted successfully`, 'success');
                // Refresh service status after a delay
                setTimeout(() => this.updateServiceStatus(), 2000);
            } else {
                this.showNotification(`Failed to restart ${serviceName}: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Error restarting ${serviceName}: ${error.message}`, 'error');
        }
    }

    setupModalHandlers() {
        // Generic modal close handlers
        document.addEventListener('click', (e) => {
            if (e.target.matches('.modal-close') || e.target.matches('.modal[data-close="true"]')) {
                const modal = e.target.closest('.modal') || e.target;
                this.hideModal(modal);
            }
        });

        // Close modal on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const openModal = document.querySelector('.modal.show');
                if (openModal) {
                    this.hideModal(openModal);
                }
            }
        });
    }

    setupFormHandlers() {
        // Generic form submission
        document.addEventListener('submit', (e) => {
            if (e.target.matches('#createShareForm')) {
                e.preventDefault();
                this.handleCreateShare(e.target);
            }
        });
    }

    async handleCreateShare(form) {
        const formData = new FormData(form);
        const shareData = {
            name: formData.get('name'),
            type: formData.get('type'),
            path: formData.get('path') || `/mnt/shares/${formData.get('name')}`,
            guest: formData.has('guest')
        };

        try {
            const result = await window.moxnasAPI.createShare(shareData);
            
            if (result.success) {
                this.showNotification(`Share "${shareData.name}" created successfully`, 'success');
                this.hideCreateShareModal();
                this.refreshShareList();
                form.reset();
            } else {
                this.showNotification(`Failed to create share: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Error creating share: ${error.message}`, 'error');
        }
    }

    showModal(modal) {
        if (typeof modal === 'string') {
            modal = document.getElementById(modal);
        }
        if (modal) {
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
    }

    hideModal(modal) {
        if (typeof modal === 'string') {
            modal = document.getElementById(modal);
        }
        if (modal) {
            modal.classList.remove('show');
            document.body.style.overflow = '';
        }
    }

    async refreshShareList() {
        try {
            const result = await window.moxnasAPI.getShares();
            if (result.success) {
                this.displayShareList(result.data);
            }
        } catch (error) {
            console.error('Failed to refresh share list:', error);
        }
    }

    displayShareList(shares) {
        const tbody = document.getElementById('share-table-body');
        if (!tbody) return;

        if (shares.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">No shares configured</td></tr>';
            return;
        }

        tbody.innerHTML = shares.map(share => `
            <tr>
                <td>${this.escapeHtml(share.name)}</td>
                <td><span class="badge badge-${share.type}">${share.type.toUpperCase()}</span></td>
                <td>${this.escapeHtml(share.path)}</td>
                <td>
                    <span class="status-indicator ${share.active ? 'active' : 'inactive'}">
                        ${share.active ? 'Active' : 'Inactive'}
                    </span>
                </td>
                <td>
                    <button class="btn btn-sm btn-secondary" onclick="app.editShare('${share.name}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="app.deleteShare('${share.name}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    async deleteShare(shareName) {
        if (!confirm(`Are you sure you want to delete the share "${shareName}"?`)) {
            return;
        }

        try {
            const result = await window.moxnasAPI.deleteShare(shareName);
            
            if (result.success) {
                this.showNotification(`Share "${shareName}" deleted successfully`, 'success');
                this.refreshShareList();
            } else {
                this.showNotification(`Failed to delete share: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Error deleting share: ${error.message}`, 'error');
        }
    }

    showNotification(message, type = 'info', duration = 5000) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${this.escapeHtml(message)}</span>
            </div>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Add styles if not already present
        this.addNotificationStyles();

        // Add to page
        document.body.appendChild(notification);

        // Show notification
        setTimeout(() => notification.classList.add('show'), 100);

        // Auto-hide
        const hideTimeout = setTimeout(() => this.hideNotification(notification), duration);

        // Manual close
        notification.querySelector('.notification-close').addEventListener('click', () => {
            clearTimeout(hideTimeout);
            this.hideNotification(notification);
        });
    }

    hideNotification(notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    addNotificationStyles() {
        if (document.getElementById('notification-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'notification-styles';
        styles.textContent = `
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: var(--border-radius);
                box-shadow: var(--shadow-lg);
                max-width: 400px;
                z-index: 3000;
                opacity: 0;
                transform: translateX(100%);
                transition: all 0.3s ease-in-out;
            }
            .notification.show {
                opacity: 1;
                transform: translateX(0);
            }
            .notification-content {
                display: flex;
                align-items: center;
                gap: var(--spacing-sm);
                padding: var(--spacing-md);
                color: var(--text-primary);
            }
            .notification-success { border-left: 4px solid var(--success-color); }
            .notification-error { border-left: 4px solid var(--error-color); }
            .notification-warning { border-left: 4px solid var(--warning-color); }
            .notification-info { border-left: 4px solid var(--info-color); }
            .notification-close {
                position: absolute;
                top: 8px;
                right: 8px;
                background: none;
                border: none;
                color: var(--text-muted);
                cursor: pointer;
                padding: 4px;
                border-radius: 4px;
                transition: var(--transition);
            }
            .notification-close:hover {
                background: var(--bg-hover);
                color: var(--text-primary);
            }
        `;
        document.head.appendChild(styles);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Global functions for easy access from HTML
window.showCreateShareModal = () => {
    window.app.showModal('createShareModal');
};

window.hideCreateShareModal = () => {
    window.app.hideModal('createShareModal');
};

window.showCreateUserModal = () => {
    // TODO: Implement user creation modal
    window.app.showNotification('User creation feature coming soon', 'info');
};

window.showLogsModal = () => {
    // TODO: Implement logs modal
    window.app.showNotification('System logs feature coming soon', 'info');
};

window.createShare = () => {
    const form = document.getElementById('createShareForm');
    if (form) {
        form.dispatchEvent(new Event('submit'));
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MoxNASApp();
});