/**
 * Storage Components for MoxNAS Frontend
 * Handles storage pool and dataset management
 */

class StorageComponents {
    constructor() {
        this.storagePools = [];
        this.storageStats = {};
        this.currentView = 'table'; // 'table' or 'card'
    }

    /**
     * Initialize storage components
     */
    init() {
        this.bindEvents();
        this.loadStorageData();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Storage type change handler
        const storageTypeSelect = document.getElementById('storage-type');
        if (storageTypeSelect) {
            storageTypeSelect.addEventListener('change', this.handleStorageTypeChange.bind(this));
        }
    }

    /**
     * Handle storage type change
     */
    handleStorageTypeChange(event) {
        const storageType = event.target.value;
        const sourcePathGroup = document.getElementById('source-path-group');
        const filesystemGroup = document.getElementById('filesystem-group');

        if (sourcePathGroup && filesystemGroup) {
            if (storageType === 'device') {
                sourcePathGroup.style.display = 'block';
                filesystemGroup.style.display = 'block';
                
                // Update label for device
                const label = sourcePathGroup.querySelector('label');
                if (label) {
                    label.textContent = 'Device Path';
                }
                
                const input = document.getElementById('storage-source-path');
                if (input) {
                    input.placeholder = '/dev/sdb1';
                }
            } else if (storageType === 'bind') {
                sourcePathGroup.style.display = 'block';
                filesystemGroup.style.display = 'none';
                
                // Update label for bind mount
                const label = sourcePathGroup.querySelector('label');
                if (label) {
                    label.textContent = 'Source Path';
                }
                
                const input = document.getElementById('storage-source-path');
                if (input) {
                    input.placeholder = '/path/to/source';
                }
            } else {
                sourcePathGroup.style.display = 'none';
                filesystemGroup.style.display = 'none';
            }
        }
    }

    /**
     * Load storage data
     */
    async loadStorageData() {
        try {
            // Load storage pools and stats
            const [poolsData, statsData] = await Promise.all([
                this.loadStoragePools(),
                this.loadStorageStats()
            ]);

            this.storagePools = poolsData || [];
            this.storageStats = statsData || {};

            this.renderStoragePools();
            this.renderStorageStats();
            this.updateMountMonitoring();

        } catch (error) {
            console.error('Error loading storage data:', error);
            this.showStorageError('Failed to load storage data');
        }
    }

    /**
     * Load storage pools
     */
    async loadStoragePools() {
        try {
            return await window.moxnasAPI.getStoragePools();
        } catch (error) {
            console.error('Error loading storage pools:', error);
            return this.getMockStoragePools();
        }
    }

    /**
     * Load storage statistics
     */
    async loadStorageStats() {
        try {
            return await window.moxnasAPI.get('/storage/stats/');
        } catch (error) {
            console.error('Error loading storage stats:', error);
            return this.getMockStorageStats();
        }
    }

    /**
     * Render storage pools
     */
    renderStoragePools() {
        if (this.currentView === 'table') {
            this.renderStorageTable();
        } else {
            this.renderStorageCards();
        }
    }

    /**
     * Render storage pools as table
     */
    renderStorageTable() {
        const tableBody = document.getElementById('storage-table-body');
        if (!tableBody) return;

        if (this.storagePools.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="7">
                        <div class="truenas-empty-state">
                            <i class="fas fa-hdd"></i>
                            <p>No storage pools configured</p>
                            <button class="truenas-btn truenas-btn-primary" onclick="moxnas.showModal('add-storage-modal')">
                                <i class="fas fa-plus"></i> Add Storage Pool
                            </button>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = this.storagePools.map(pool => `
            <tr data-pool-id="${pool.id}">
                <td>
                    <div class="pool-name">
                        <i class="fas fa-hdd"></i>
                        <span>${pool.name}</span>
                    </div>
                </td>
                <td>${pool.mount_path}</td>
                <td>${this.formatBytes(pool.total_size)}</td>
                <td>
                    <div class="usage-info">
                        <span>${this.formatBytes(pool.used_size)}</span>
                        <div class="usage-bar">
                            <div class="usage-fill" style="width: ${pool.usage_percent}%"></div>
                        </div>
                        <span class="usage-percent">${pool.usage_percent}%</span>
                    </div>
                </td>
                <td>${this.formatBytes(pool.available_size)}</td>
                <td>
                    <span class="truenas-badge ${pool.status === 'online' ? 'truenas-badge-success' : 'truenas-badge-danger'}">
                        ${pool.status}
                    </span>
                </td>
                <td>
                    <div class="action-buttons">
                        <button class="truenas-btn truenas-btn-sm truenas-btn-secondary" onclick="storageComponents.editPool(${pool.id})" title="Edit">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="truenas-btn truenas-btn-sm truenas-btn-info" onclick="storageComponents.viewPoolDetails(${pool.id})" title="Details">
                            <i class="fas fa-info"></i>
                        </button>
                        <button class="truenas-btn truenas-btn-sm truenas-btn-danger" onclick="storageComponents.deletePool(${pool.id})" title="Delete">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    /**
     * Render storage pools as cards
     */
    renderStorageCards() {
        const cardsContainer = document.getElementById('storage-pools-cards');
        if (!cardsContainer) return;

        if (this.storagePools.length === 0) {
            cardsContainer.innerHTML = `
                <div class="truenas-empty-state">
                    <i class="fas fa-hdd"></i>
                    <p>No storage pools configured</p>
                    <button class="truenas-btn truenas-btn-primary" onclick="moxnas.showModal('add-storage-modal')">
                        <i class="fas fa-plus"></i> Add Storage Pool
                    </button>
                </div>
            `;
            return;
        }

        cardsContainer.innerHTML = this.storagePools.map(pool => `
            <div class="truenas-storage-pool-card" data-pool-id="${pool.id}">
                <div class="pool-card-header">
                    <h4><i class="fas fa-hdd"></i> ${pool.name}</h4>
                    <span class="truenas-badge ${pool.status === 'online' ? 'truenas-badge-success' : 'truenas-badge-danger'}">
                        ${pool.status}
                    </span>
                </div>
                <div class="pool-card-body">
                    <div class="pool-usage">
                        <div class="usage-bar">
                            <div class="usage-fill" style="width: ${pool.usage_percent}%"></div>
                        </div>
                        <div class="usage-text">
                            ${this.formatBytes(pool.used_size)} / ${this.formatBytes(pool.total_size)} (${pool.usage_percent}%)
                        </div>
                    </div>
                    <div class="pool-info">
                        <div class="info-item">
                            <span class="info-label">Mount Path:</span>
                            <span class="info-value">${pool.mount_path}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Available:</span>
                            <span class="info-value">${this.formatBytes(pool.available_size)}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Type:</span>
                            <span class="info-value">${pool.type || 'Unknown'}</span>
                        </div>
                    </div>
                </div>
                <div class="pool-card-footer">
                    <button class="truenas-btn truenas-btn-sm truenas-btn-secondary" onclick="storageComponents.editPool(${pool.id})">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="truenas-btn truenas-btn-sm truenas-btn-info" onclick="storageComponents.viewPoolDetails(${pool.id})">
                        <i class="fas fa-info"></i> Details
                    </button>
                    <button class="truenas-btn truenas-btn-sm truenas-btn-danger" onclick="storageComponents.deletePool(${pool.id})">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render storage statistics
     */
    renderStorageStats() {
        const statsContainer = document.getElementById('storage-stats');
        if (!statsContainer) return;

        const totalUsed = this.storageStats.total_used || 0;
        const totalSize = this.storageStats.total_size || 0;
        const usagePercent = totalSize > 0 ? Math.round((totalUsed / totalSize) * 100) : 0;

        statsContainer.innerHTML = `
            <div class="truenas-storage-overview">
                <div class="storage-usage-chart">
                    <div class="usage-circle">
                        <svg viewBox="0 0 36 36" class="circular-chart">
                            <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
                            <path class="circle" stroke-dasharray="${usagePercent}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/>
                            <text x="18" y="20.35" class="percentage">${usagePercent}%</text>
                        </svg>
                    </div>
                </div>
                <div class="storage-usage-details">
                    <div class="usage-item">
                        <span class="usage-label">Total Capacity:</span>
                        <span class="usage-value">${this.formatBytes(totalSize)}</span>
                    </div>
                    <div class="usage-item">
                        <span class="usage-label">Used Space:</span>
                        <span class="usage-value">${this.formatBytes(totalUsed)}</span>
                    </div>
                    <div class="usage-item">
                        <span class="usage-label">Available Space:</span>
                        <span class="usage-value">${this.formatBytes(totalSize - totalUsed)}</span>
                    </div>
                    <div class="usage-item">
                        <span class="usage-label">Storage Pools:</span>
                        <span class="usage-value">${this.storagePools.length}</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Update mount point monitoring
     */
    updateMountMonitoring() {
        const monitoringContainer = document.getElementById('mount-monitoring');
        if (!monitoringContainer) return;

        const activeMonitors = this.storagePools.filter(pool => pool.status === 'online').length;
        const totalMonitors = this.storagePools.length;

        monitoringContainer.innerHTML = `
            <div class="monitoring-summary">
                <div class="monitor-stat">
                    <span class="stat-number">${activeMonitors}</span>
                    <span class="stat-label">Active Monitors</span>
                </div>
                <div class="monitor-stat">
                    <span class="stat-number">${totalMonitors}</span>
                    <span class="stat-label">Total Mount Points</span>
                </div>
            </div>
            <div class="monitoring-list">
                ${this.storagePools.map(pool => `
                    <div class="monitor-item">
                        <div class="monitor-info">
                            <span class="monitor-path">${pool.mount_path}</span>
                            <span class="monitor-name">${pool.name}</span>
                        </div>
                        <div class="monitor-status">
                            <span class="truenas-badge ${pool.status === 'online' ? 'truenas-badge-success' : 'truenas-badge-danger'}">
                                ${pool.status}
                            </span>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * Toggle storage view between table and cards
     */
    toggleView(viewType) {
        this.currentView = viewType;
        
        const tableContainer = document.getElementById('storage-pools-table');
        const cardsContainer = document.getElementById('storage-pools-cards');
        const tableViewBtn = document.getElementById('storage-table-view');
        const cardViewBtn = document.getElementById('storage-card-view');

        if (viewType === 'table') {
            if (tableContainer) tableContainer.style.display = 'block';
            if (cardsContainer) cardsContainer.style.display = 'none';
            if (tableViewBtn) tableViewBtn.classList.add('active');
            if (cardViewBtn) cardViewBtn.classList.remove('active');
        } else {
            if (tableContainer) tableContainer.style.display = 'none';
            if (cardsContainer) cardsContainer.style.display = 'block';
            if (tableViewBtn) tableViewBtn.classList.remove('active');
            if (cardViewBtn) cardViewBtn.classList.add('active');
        }

        this.renderStoragePools();
    }

    /**
     * Edit storage pool
     */
    editPool(poolId) {
        const pool = this.storagePools.find(p => p.id === poolId);
        if (!pool) return;

        // Populate edit form (would need to create edit modal)
        console.log('Edit pool:', pool);
        this.showStorageInfo(`Edit functionality for pool "${pool.name}" would be implemented here`);
    }

    /**
     * View pool details
     */
    viewPoolDetails(poolId) {
        const pool = this.storagePools.find(p => p.id === poolId);
        if (!pool) return;

        console.log('View pool details:', pool);
        this.showStorageInfo(`Details for pool "${pool.name}" would be displayed here`);
    }

    /**
     * Delete storage pool
     */
    async deletePool(poolId) {
        const pool = this.storagePools.find(p => p.id === poolId);
        if (!pool) return;

        if (!confirm(`Are you sure you want to delete storage pool "${pool.name}"? This action cannot be undone.`)) {
            return;
        }

        try {
            await window.moxnasAPI.deleteStoragePool(poolId);
            this.storagePools = this.storagePools.filter(p => p.id !== poolId);
            this.renderStoragePools();
            this.renderStorageStats();
            this.showStorageSuccess(`Storage pool "${pool.name}" deleted successfully`);
        } catch (error) {
            console.error('Error deleting storage pool:', error);
            this.showStorageError('Failed to delete storage pool');
        }
    }

    /**
     * Format bytes to human readable format
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Get mock storage pools for development
     */
    getMockStoragePools() {
        return [
            {
                id: 1,
                name: 'pool1',
                mount_path: '/mnt/pool1',
                type: 'bind',
                status: 'online',
                total_size: 1000000000000, // 1TB
                used_size: 450000000000,   // 450GB
                available_size: 550000000000, // 550GB
                usage_percent: 45
            },
            {
                id: 2,
                name: 'backup',
                mount_path: '/mnt/backup',
                type: 'device',
                status: 'online',
                total_size: 2000000000000, // 2TB
                used_size: 800000000000,   // 800GB
                available_size: 1200000000000, // 1.2TB
                usage_percent: 40
            }
        ];
    }

    /**
     * Get mock storage statistics
     */
    getMockStorageStats() {
        return {
            total_size: 3000000000000,  // 3TB
            total_used: 1250000000000,  // 1.25TB
            pools_count: 2
        };
    }

    /**
     * Show storage success message
     */
    showStorageSuccess(message) {
        if (window.moxnas && window.moxnas.showAlert) {
            window.moxnas.showAlert('success', message);
        } else {
            console.log('SUCCESS:', message);
        }
    }

    /**
     * Show storage info message
     */
    showStorageInfo(message) {
        if (window.moxnas && window.moxnas.showAlert) {
            window.moxnas.showAlert('info', message);
        } else {
            console.log('INFO:', message);
        }
    }

    /**
     * Show storage error message
     */
    showStorageError(message) {
        if (window.moxnas && window.moxnas.showAlert) {
            window.moxnas.showAlert('error', message);
        } else {
            console.error('ERROR:', message);
        }
    }
}

// Create global instance
window.storageComponents = new StorageComponents();
