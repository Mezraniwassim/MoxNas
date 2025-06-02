/**
 * MoxNAS Frontend JavaScript
 * Handles navigation, API communication, and UI interactions
 */

class MoxNAS {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000/api';
        this.currentPage = 'dashboard';
        this.charts = {};
        this.intervals = [];
        
        this.init();
    }

    /**
     * Initialize the application
     */
    init() {
        this.setupEventListeners();
        this.loadDashboard();
        this.startPeriodicUpdates();
        
        // Show dashboard by default
        this.showPage('dashboard');
    }

    /**
     * Setup event listeners for navigation and UI interactions
     */
    setupEventListeners() {
        // Navigation links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = link.getAttribute('data-page');
                this.navigateToPage(page);
            });
        });

        // Modal close buttons
        document.querySelectorAll('[data-modal-close]').forEach(button => {
            button.addEventListener('click', (e) => {
                const modalId = button.getAttribute('data-modal-close');
                this.closeModal(modalId);
            });
        });

        // Modal overlays (click outside to close)
        document.querySelectorAll('.modal-overlay').forEach(overlay => {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    overlay.style.display = 'none';
                }
            });
        });

        // Form submissions
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleFormSubmit(form);
            });
        });

        // Refresh buttons
        document.querySelectorAll('[data-refresh]').forEach(button => {
            button.addEventListener('click', (e) => {
                const target = button.getAttribute('data-refresh');
                this.refreshData(target);
            });
        });
    }

    /**
     * Navigate to a specific page
     */
    navigateToPage(pageName = 'dashboard') {
        // Update active navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[data-page="${pageName}"]`).classList.add('active');

        // Show the requested page
        this.showPage(pageName);
        this.currentPage = pageName;

        // Load page-specific data
        this.loadPageData(pageName);

        // Update page title
        this.updatePageTitle(pageName);
    }

    /**
     * Show a specific page and hide others
     */
    showPage(pageName) {
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });
        
        const targetPage = document.getElementById(`${pageName}-page`);
        if (targetPage) {
            targetPage.classList.add('active');
        }
    }

    /**
     * Update the page title
     */
    updatePageTitle(pageName) {
        const titles = {
            dashboard: 'Dashboard',
            storage: 'Storage Management',
            shares: 'Shares',
            network: 'Network Configuration',
            system: 'System Management',
            tasks: 'Scheduled Tasks',
            proxmox: 'Proxmox Management',
            reporting: 'Reporting'
        };

        const titleElement = document.getElementById('page-title');
        const subtitleElement = document.getElementById('page-subtitle');
        
        if (titleElement && titles[pageName]) {
            titleElement.textContent = titles[pageName];
        }
        
        if (subtitleElement) {
            const subtitles = {
                dashboard: 'System Overview',
                storage: 'Manage Storage Pools and Datasets',
                shares: 'Network Shares Configuration',
                network: 'Network Settings and Services',
                system: 'System Configuration and Status',
                tasks: 'Scheduled Jobs and Automation',
                proxmox: 'Virtualization Infrastructure Management',
                reporting: 'System Analytics and Reports'
            };
            subtitleElement.textContent = subtitles[pageName] || '';
        }
    }

    /**
     * Load page-specific data
     */
    async loadPageData(pageName) {
        switch (pageName) {
            case 'dashboard':
                await this.loadDashboard();
                break;
            case 'storage':
                await this.loadStorageData();
                break;
            case 'shares':
                await this.loadSharesData();
                break;
            case 'network':
                await this.loadNetworkData();
                break;
            case 'system':
                await this.loadSystemData();
                break;
            case 'tasks':
                await this.loadTasksData();
                break;
            case 'proxmox':
                this.initializeProxmoxManager();
                break;
            case 'reporting':
                await this.loadReportingData();
                break;
        }
    }

    /**
     * Load dashboard data
     */
    async loadDashboard() {
        try {
            console.log('Loading dashboard data...');
            
            // Load Proxmox data (our working endpoint)
            const proxmoxData = await this.loadProxmoxDashboardData();
            
            // Load storage data
            const storageData = await this.loadStorageDashboardData();
            
            // Update dashboard with available data
            this.updateDashboardStats(proxmoxData, storageData);
            
            console.log('Dashboard data loaded successfully');

        } catch (error) {
            console.error('Error loading dashboard data:', error);
            this.showAlert('error', 'Failed to load dashboard data: ' + error.message);
        }
    }

    /**
     * Load Proxmox data for dashboard
     */
    async loadProxmoxDashboardData() {
        try {
            const [nodes, containers, storage] = await Promise.all([
                this.apiCall('/proxmox/api/nodes/'),
                this.apiCall('/proxmox/api/containers/'),
                this.apiCall('/proxmox/api/storage/')
            ]);
            
            return {
                nodes: nodes || [],        // Proxmox endpoints return arrays directly
                containers: containers || [],
                storage: storage || []
            };
        } catch (error) {
            console.warn('Could not load Proxmox data:', error);
            return { nodes: [], containers: [], storage: [] };
        }
    }

    /**
     * Load storage data for dashboard
     */
    async loadStorageDashboardData() {
        try {
            const response = await this.apiCall('/storage/pools/');
            return response.results || [];
        } catch (error) {
            console.warn('Could not load storage data:', error);
            return [];
        }
    }

    /**
     * Update dashboard statistics
     */
    updateDashboardStats(proxmoxData, storageData) {
        console.log('Updating dashboard stats with:', { proxmoxData, storageData });
        
        // Update storage pools count
        if (storageData && Array.isArray(storageData)) {
            const activePools = storageData.filter(pool => pool.status === 'healthy' || pool.status === 'online').length;
            document.getElementById('storage-pools-count').textContent = activePools || storageData.length || 0;
        } else {
            document.getElementById('storage-pools-count').textContent = '0';
        }
        
        // Update memory and CPU with mock data or Proxmox data
        if (proxmoxData && proxmoxData.nodes && proxmoxData.nodes.length > 0) {
            const node = proxmoxData.nodes[0];
            document.getElementById('memory-usage').textContent = `${Math.round((node.memory_used / node.memory_total) * 100) || 0}%`;
            document.getElementById('cpu-usage').textContent = `${Math.round(node.cpu_usage * 100) || 0}%`;
        } else {
            // Use mock data if Proxmox is not available
            document.getElementById('memory-usage').textContent = '45%';
            document.getElementById('cpu-usage').textContent = '23%';
        }
        
        // Update shares count (placeholder for now)
        document.getElementById('shares-count').textContent = '0';
        
        // Update storage overview
        this.updateStorageOverview(proxmoxData, storageData);
    }

    /**
     * Update storage overview in dashboard
     */
    updateStorageOverview(proxmoxData, storageData) {
        try {
            let totalSpace = 0;
            let usedSpace = 0;
            
            if (proxmoxData && proxmoxData.storage && proxmoxData.storage.length > 0) {
                proxmoxData.storage.forEach(storage => {
                    totalSpace += storage.total_space || 0;   // Use correct field names from API
                    usedSpace += storage.used_space || 0;
                });
            }
            
            if (totalSpace > 0) {
                const usagePercent = Math.round((usedSpace / totalSpace) * 100);
                const usedGB = Math.round(usedSpace / (1024 * 1024 * 1024));
                const totalGB = Math.round(totalSpace / (1024 * 1024 * 1024));
                
                // Update storage bar
                const storageBar = document.querySelector('.storage-used');
                if (storageBar) {
                    storageBar.style.width = `${usagePercent}%`;
                }
                
                // Update storage info
                const storageInfo = document.querySelector('.storage-info span');
                if (storageInfo) {
                    storageInfo.textContent = `${usedGB} GB used of ${totalGB} GB total`;
                }
            } else {
                // Default values when no storage data available
                const storageBar = document.querySelector('.storage-used');
                if (storageBar) {
                    storageBar.style.width = '0%';
                }
                
                const storageInfo = document.querySelector('.storage-info span');
                if (storageInfo) {
                    storageInfo.textContent = '0 GB used of 0 GB total';
                }
            }
        } catch (error) {
            console.warn('Could not update storage overview:', error);
        }
    }



    /**
     * Load storage data
     */
    async loadStorageData() {
        try {
            await Promise.all([
                this.updateStorageStats(),
                this.updateStoragePools(),
                this.updateMountMonitoring()
            ]);
        } catch (error) {
            console.error('Error loading storage data:', error);
            this.showNotification('error', 'Failed to load storage data');
        }
    }

    /**
     * Update storage statistics
     */
    async updateStorageStats() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/storage/stats`);
            if (!response.ok) throw new Error('Failed to fetch storage stats');
            
            const stats = await response.json();
            const container = document.getElementById('storage-stats');
            
            if (container) {
                container.innerHTML = StorageComponents.createStorageStatsWidget(stats);
            }
        } catch (error) {
            console.error('Error updating storage stats:', error);
            const container = document.getElementById('storage-stats');
            if (container) {
                container.innerHTML = StorageComponents.createErrorState(
                    'Failed to load storage statistics',
                    'moxnas.updateStorageStats()'
                );
            }
        }
    }

    /**
     * Update storage pools
     */
    async updateStoragePools() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/storage/pools`);
            if (!response.ok) throw new Error('Failed to fetch storage pools');
            
            const pools = await response.json();
            
            // Update table view
            const tableBody = document.getElementById('storage-table-body');
            if (tableBody) {
                if (pools.length === 0) {
                    tableBody.innerHTML = `
                        <tr>
                            <td colspan="7">
                                ${StorageComponents.createEmptyState(
                                    'No storage pools configured',
                                    '<button class="btn btn-primary" onclick="moxnas.showModal(\'add-storage-modal\')"><i class="fas fa-plus"></i> Add Storage Pool</button>'
                                )}
                            </td>
                        </tr>
                    `;
                } else {
                    tableBody.innerHTML = pools.map(pool => 
                        StorageComponents.createStoragePoolRow(pool)
                    ).join('');
                }
            }
            
            // Update card view
            const cardsContainer = document.getElementById('storage-pools-cards');
            if (cardsContainer) {
                if (pools.length === 0) {
                    cardsContainer.innerHTML = StorageComponents.createEmptyState(
                        'No storage pools configured',
                        '<button class="btn btn-primary" onclick="moxnas.showModal(\'add-storage-modal\')"><i class="fas fa-plus"></i> Add Storage Pool</button>'
                    );
                } else {
                    cardsContainer.innerHTML = pools.map(pool => 
                        StorageComponents.createStoragePoolCard(pool)
                    ).join('');
                }
            }
            
            // Update dashboard stats
            this.updateDashboardStorageCount(pools.length);
            
        } catch (error) {
            console.error('Error updating storage pools:', error);
            const tableBody = document.getElementById('storage-table-body');
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="7">
                            ${StorageComponents.createErrorState(
                                'Failed to load storage pools',
                                'moxnas.updateStoragePools()'
                            )}
                        </td>
                    </tr>
                `;
            }
        }
    }

    /**
     * Update mount monitoring status
     */
    async updateMountMonitoring() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/storage/monitoring`);
            if (!response.ok) throw new Error('Failed to fetch monitoring status');
            
            const monitoring = await response.json();
            const container = document.getElementById('mount-monitoring');
            
            if (container) {
                if (monitoring.length === 0) {
                    container.innerHTML = StorageComponents.createEmptyState(
                        'No mount points being monitored'
                    );
                } else {
                    container.innerHTML = monitoring.map(item => `
                        <div class="monitor-item">
                            <div class="monitor-info">
                                <div class="monitor-name">${item.mount_point}</div>
                                <div class="monitor-status">
                                    ${item.service_active ? 'Active' : 'Inactive'} | 
                                    ${item.mounted ? 'Mounted' : 'Not Mounted'}
                                </div>
                            </div>
                            <div class="monitor-actions">
                                <button class="btn btn-sm btn-${item.service_active ? 'warning' : 'success'}" 
                                        onclick="moxnas.toggleMountMonitoring('${item.mount_point}')">
                                    <i class="fas fa-${item.service_active ? 'pause' : 'play'}"></i>
                                </button>
                            </div>
                        </div>
                    `).join('');
                }
            }
        } catch (error) {
            console.error('Error updating mount monitoring:', error);
            const container = document.getElementById('mount-monitoring');
            if (container) {
                container.innerHTML = StorageComponents.createErrorState(
                    'Failed to load monitoring status',
                    'moxnas.updateMountMonitoring()'
                );
            }
        }
    }

    /**
     * Toggle storage view (card/table)
     */
    toggleStorageView(view) {
        const cardView = document.getElementById('storage-pools-cards');
        const tableView = document.getElementById('storage-pools-table');
        const cardButton = document.getElementById('storage-card-view');
        const tableButton = document.getElementById('storage-table-view');
        
        if (view === 'card') {
            cardView.style.display = 'grid';
            tableView.style.display = 'none';
            cardButton.classList.add('active');
            tableButton.classList.remove('active');
        } else {
            cardView.style.display = 'none';
            tableView.style.display = 'block';
            cardButton.classList.remove('active');
            tableButton.classList.add('active');
        }
    }

    /**
     * Add storage pool
     */
    async addStoragePool() {
        try {
            const form = document.getElementById('add-storage-form');
            const formData = new FormData(form);
            
            const data = {
                name: formData.get('name'),
                mount_path: formData.get('mount_path'),
                type: formData.get('type'),
                source_path: formData.get('source_path'),
                filesystem: formData.get('filesystem'),
                description: formData.get('description'),
                read_only: formData.get('read_only') === 'on',
                auto_mount: formData.get('auto_mount') === 'on'
            };
            
            const response = await fetch(`${this.apiBaseUrl}/storage/pools`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to add storage pool');
            }
            
            this.showNotification('success', 'Storage pool added successfully');
            this.closeModal('add-storage-modal');
            this.updateStoragePools();
            form.reset();
            
        } catch (error) {
            console.error('Error adding storage pool:', error);
            this.showNotification('error', error.message);
        }
    }

    /**
     * Edit storage pool
     */
    async editStoragePool(poolId) {
        // Implementation for editing storage pool
        console.log('Edit storage pool:', poolId);
        this.showNotification('info', 'Edit storage pool feature coming soon');
    }

    /**
     * Delete storage pool
     */
    async deleteStoragePool(poolId) {
        if (!confirm('Are you sure you want to delete this storage pool?')) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/storage/pools/${poolId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to delete storage pool');
            }
            
            this.showNotification('success', 'Storage pool deleted successfully');
            this.updateStoragePools();
            
        } catch (error) {
            console.error('Error deleting storage pool:', error);
            this.showNotification('error', error.message);
        }
    }

    /**
     * Toggle mount monitoring
     */
    async toggleMountMonitoring(mountPoint) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/storage/monitoring/${encodeURIComponent(mountPoint)}/toggle`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to toggle mount monitoring');
            }
            
            this.showNotification('success', 'Mount monitoring toggled successfully');
            this.updateMountMonitoring();
            
        } catch (error) {
            console.error('Error toggling mount monitoring:', error);
            this.showNotification('error', error.message);
        }
    }

    /**
     * Refresh storage data
     */
    refreshStorageData() {
        this.loadStorageData();
    }

    /**
     * Refresh storage stats
     */
    refreshStorageStats() {
        this.updateStorageStats();
    }

    /**
     * Shares Management Functions
     */
    
    /**
     * Load shares data
     */
    async loadSharesData() {
        try {
            await Promise.all([
                this.updateSharesStats(),
                this.updateShares(),
                this.loadStoragePoolsForShares()
            ]);
        } catch (error) {
            console.error('Error loading shares data:', error);
            this.showNotification('error', 'Failed to load shares data');
        }
    }

    /**
     * Update shares statistics
     */
    async updateSharesStats() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/shares/stats`);
            if (!response.ok) throw new Error('Failed to fetch shares stats');
            
            const stats = await response.json();
            
            // Update individual counters
            document.getElementById('smb-shares-count').textContent = stats.smb_count || 0;
            document.getElementById('nfs-shares-count').textContent = stats.nfs_count || 0;
            document.getElementById('ftp-shares-count').textContent = stats.ftp_count || 0;
            document.getElementById('active-shares-count').textContent = stats.active_count || 0;
            
        } catch (error) {
            console.error('Error updating shares stats:', error);
            // Set default values on error
            document.getElementById('smb-shares-count').textContent = '0';
            document.getElementById('nfs-shares-count').textContent = '0';
            document.getElementById('ftp-shares-count').textContent = '0';
            document.getElementById('active-shares-count').textContent = '0';
        }
    }

    /**
     * Update shares list
     */
    async updateShares() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/shares`);
            if (!response.ok) throw new Error('Failed to fetch shares');
            
            const shares = await response.json();
            
            // Update table view
            const tableBody = document.getElementById('shares-table-body');
            if (tableBody) {
                if (shares.length === 0) {
                    tableBody.innerHTML = `
                        <tr>
                            <td colspan="6">
                                ${StorageComponents.createEmptyState(
                                    'No shares configured',
                                    '<button class="btn btn-primary" onclick="moxnas.showModal(\'add-share-modal\')"><i class="fas fa-plus"></i> Add Share</button>'
                                )}
                            </td>
                        </tr>
                    `;
                } else {
                    tableBody.innerHTML = shares.map(share => 
                        StorageComponents.createShareRow(share)
                    ).join('');
                }
            }
            
            // Update card view
            const cardsContainer = document.getElementById('shares-cards');
            if (cardsContainer) {
                if (shares.length === 0) {
                    cardsContainer.innerHTML = StorageComponents.createEmptyState(
                        'No shares configured',
                        '<button class="btn btn-primary" onclick="moxnas.showModal(\'add-share-modal\')"><i class="fas fa-plus"></i> Add Share</button>'
                    );
                } else {
                    cardsContainer.innerHTML = shares.map(share => 
                        StorageComponents.createShareCard(share)
                    ).join('');
                }
            }
            
            // Update dashboard stats
            this.updateDashboardSharesCount(shares.length);
            
        } catch (error) {
            console.error('Error updating shares:', error);
            const tableBody = document.getElementById('shares-table-body');
            if (tableBody) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6">
                            ${StorageComponents.createErrorState(
                                'Failed to load shares',
                                'moxnas.updateShares()'
                            )}
                        </td>
                    </tr>
                `;
            }
        }
    }

    /**
     * Load storage pools for shares dropdown
     */
    async loadStoragePoolsForShares() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/storage/pools`);
            if (!response.ok) throw new Error('Failed to fetch storage pools');
            
            const pools = await response.json();
            const select = document.getElementById('share-storage-pool');
            
            if (select) {
                select.innerHTML = '<option value="">Select storage pool...</option>' +
                    pools.map(pool => `<option value="${pool.id}">${pool.name} (${pool.mount_path})</option>`).join('');
            }
            
        } catch (error) {
            console.error('Error loading storage pools for shares:', error);
        }
    }

    /**
     * Toggle shares view (card/table)
     */
    toggleSharesView(view) {
        const cardView = document.getElementById('shares-cards');
        const tableView = document.getElementById('shares-table');
        const cardButton = document.getElementById('shares-card-view');
        const tableButton = document.getElementById('shares-table-view');
        
        if (view === 'card') {
            cardView.style.display = 'grid';
            tableView.style.display = 'none';
            cardButton.classList.add('active');
            tableButton.classList.remove('active');
        } else {
            cardView.style.display = 'none';
            tableView.style.display = 'block';
            cardButton.classList.remove('active');
            tableButton.classList.add('active');
        }
    }

    /**
     * Switch tabs in share settings
     */
    switchTab(tabId) {
        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Remove active class from all tab buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });
        
        // Show selected tab content
        const selectedTab = document.getElementById(tabId);
        if (selectedTab) {
            selectedTab.classList.add('active');
        }
        
        // Add active class to corresponding button
        event.target.classList.add('active');
    }

    /**
     * Handle share type change in modal
     */
    handleShareTypeChange() {
        const shareType = document.getElementById('share-type').value;
        const smbOptions = document.getElementById('smb-options');
        const nfsOptions = document.getElementById('nfs-options');
        const ftpOptions = document.getElementById('ftp-options');
        
        // Hide all options
        [smbOptions, nfsOptions, ftpOptions].forEach(el => {
            if (el) el.style.display = 'none';
        });
        
        // Show relevant options
        if (shareType === 'smb' && smbOptions) {
            smbOptions.style.display = 'block';
        } else if (shareType === 'nfs' && nfsOptions) {
            nfsOptions.style.display = 'block';
        } else if (shareType === 'ftp' && ftpOptions) {
            ftpOptions.style.display = 'block';
        }
    }

    /**
     * Handle storage type change in modal
     */
    handleStorageTypeChange() {
        const storageType = document.getElementById('storage-type').value;
        const sourcePathGroup = document.getElementById('source-path-group');
        const filesystemGroup = document.getElementById('filesystem-group');
        
        // Show/hide relevant fields based on storage type
        if (storageType === 'device') {
            if (sourcePathGroup) sourcePathGroup.style.display = 'block';
            if (filesystemGroup) filesystemGroup.style.display = 'block';
            
            // Update labels
            const sourceLabel = sourcePathGroup?.querySelector('label');
            if (sourceLabel) sourceLabel.textContent = 'Device Path';
            
            const sourceInput = document.getElementById('storage-source-path');
            if (sourceInput) sourceInput.placeholder = '/dev/sdb1';
            
        } else if (storageType === 'bind') {
            if (sourcePathGroup) sourcePathGroup.style.display = 'block';
            if (filesystemGroup) filesystemGroup.style.display = 'none';
            
            // Update labels
            const sourceLabel = sourcePathGroup?.querySelector('label');
            if (sourceLabel) sourceLabel.textContent = 'Source Path';
            
            const sourceInput = document.getElementById('storage-source-path');
            if (sourceInput) sourceInput.placeholder = '/path/to/source';
            
        } else if (storageType === 'directory') {
            if (sourcePathGroup) sourcePathGroup.style.display = 'none';
            if (filesystemGroup) filesystemGroup.style.display = 'none';
        }
    }

    /**
     * Add share
     */
    async addShare() {
        try {
            const form = document.getElementById('add-share-form');
            const formData = new FormData(form);
            const shareType = formData.get('type');
            
            const data = {
                name: formData.get('name'),
                type: shareType,
                storage_pool: formData.get('storage_pool'),
                path: formData.get('path'),
                description: formData.get('description'),
                read_only: formData.get('read_only') === 'on',
                enabled: formData.get('enabled') === 'on'
            };
            
            // Add type-specific options
            if (shareType === 'smb') {
                data.guest_access = formData.get('guest_access') === 'on';
                data.browseable = formData.get('browseable') === 'on';
                data.valid_users = formData.get('valid_users');
            } else if (shareType === 'nfs') {
                data.allowed_networks = formData.get('allowed_networks');
                data.root_squash = formData.get('root_squash');
            } else if (shareType === 'ftp') {
                data.anonymous_access = formData.get('anonymous_access') === 'on';
                data.upload_permissions = formData.get('upload_permissions');
            }
            
            const response = await fetch(`${this.apiBaseUrl}/shares`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to add share');
            }
            
            this.showNotification('success', 'Share added successfully');
            this.closeModal('add-share-modal');
            this.updateShares();
            this.updateSharesStats();
            form.reset();
            
        } catch (error) {
            console.error('Error adding share:', error);
            this.showNotification('error', error.message);
        }
    }

    /**
     * Toggle share
     */
    async toggleShare(shareId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/shares/${shareId}/toggle`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to toggle share');
            }
            
            this.showNotification('success', 'Share toggled successfully');
            this.updateShares();
            this.updateSharesStats();
            
        } catch (error) {
            console.error('Error toggling share:', error);
            this.showNotification('error', error.message);
        }
    }

    /**
     * Edit share
     */
    async editShare(shareId) {
        // Implementation for editing share
        console.log('Edit share:', shareId);
        this.showNotification('info', 'Edit share feature coming soon');
    }

    /**
     * Delete share
     */
    async deleteShare(shareId) {
        if (!confirm('Are you sure you want to delete this share?')) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBaseUrl}/shares/${shareId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to delete share');
            }
            
            this.showNotification('success', 'Share deleted successfully');
            this.updateShares();
            this.updateSharesStats();
            
        } catch (error) {
            console.error('Error deleting share:', error);
            this.showNotification('error', error.message);
        }
    }

    /**
     * Refresh shares data
     */
    refreshSharesData() {
        this.loadSharesData();
    }

    /**
     * Network Management Functions
     */
    
    /**
     * Load network data
     */
    async loadNetworkData() {
        try {
            await Promise.all([
                this.updateNetworkInterfaces(),
                this.updateNetworkServices(),
                this.updateNetworkStats()
            ]);
        } catch (error) {
            console.error('Error loading network data:', error);
            this.showNotification('error', 'Failed to load network data');
        }
    }

    /**
     * Update network interfaces
     */
    async updateNetworkInterfaces() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/network/interfaces/`);
            if (!response.ok) throw new Error('Failed to fetch network interfaces');
            
            const interfaces = await response.json();
            
            // Update interfaces list
            const container = document.getElementById('network-interfaces');
            if (container) {
                if (interfaces.length === 0) {
                    container.innerHTML = NetworkComponents.createEmptyState(
                        'No network interfaces found'
                    );
                } else {
                    container.innerHTML = interfaces.map(iface => 
                        NetworkComponents.createInterfaceCard(iface)
                    ).join('');
                }
            }
            
        } catch (error) {
            console.error('Error updating network interfaces:', error);
            const container = document.getElementById('network-interfaces');
            if (container) {
                container.innerHTML = NetworkComponents.createErrorState(
                    'Failed to load network interfaces',
                    'moxnas.updateNetworkInterfaces()'
                );
            }
        }
    }

    /**
     * Update network services
     */
    async updateNetworkServices() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/network/services/`);
            if (!response.ok) throw new Error('Failed to fetch network services');
            
            const services = await response.json();
            
            // Update services status
            const container = document.getElementById('network-services');
            if (container) {
                container.innerHTML = services.map(service => 
                    NetworkComponents.createServiceStatusCard(service)
                ).join('');
            }
            
        } catch (error) {
            console.error('Error updating network services:', error);
            const container = document.getElementById('network-services');
            if (container) {
                container.innerHTML = NetworkComponents.createErrorState(
                    'Failed to load network services',
                    'moxnas.updateNetworkServices()'
                );
            }
        }
    }

    /**
     * Update network statistics
     */
    async updateNetworkStats() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/network/stats/`);
            if (!response.ok) throw new Error('Failed to fetch network statistics');
            
            const stats = await response.json();
            
            // Update stats widgets
            const container = document.getElementById('network-stats');
            if (container) {
                container.innerHTML = NetworkComponents.createNetworkStatsWidget(stats);
            }
            
        } catch (error) {
            console.error('Error updating network stats:', error);
            const container = document.getElementById('network-stats');
            if (container) {
                container.innerHTML = NetworkComponents.createErrorState(
                    'Failed to load network statistics',
                    'moxnas.updateNetworkStats()'
                );
            }
        }
    }

    /**
     * System Management Functions
     */
    
    /**
     * Load system data
     */
    async loadSystemData() {
        try {
            await Promise.all([
                this.updateSystemInfo(),
                this.updateSystemServices(),
                this.updateSystemLogs()
            ]);
        } catch (error) {
            console.error('Error loading system data:', error);
            this.showNotification('error', 'Failed to load system data');
        }
    }

    /**
     * Update system information
     */
    async updateSystemInfo() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/system/info/`);
            if (!response.ok) throw new Error('Failed to fetch system info');
            
            const info = await response.json();
            
            // Update system info display
            if (info.hostname) document.getElementById('system-hostname').textContent = info.hostname;
            if (info.uptime) document.getElementById('system-uptime').textContent = info.uptime;
            if (info.version) document.getElementById('system-version').textContent = info.version;
            if (info.kernel) document.getElementById('system-kernel').textContent = info.kernel;
            
        } catch (error) {
            console.error('Error updating system info:', error);
        }
    }

    /**
     * Update system services
     */
    async updateSystemServices() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/system/services/`);
            if (!response.ok) throw new Error('Failed to fetch system services');
            
            const services = await response.json();
            
            // Update services list
            const container = document.getElementById('system-services-list');
            if (container) {
                container.innerHTML = services.map(service => `
                    <div class="service-item">
                        <div class="service-info">
                            <div class="service-name">${service.name}</div>
                            <div class="service-status ${service.active ? 'active' : 'inactive'}">
                                ${service.active ? 'Active' : 'Inactive'}
                            </div>
                        </div>
                        <div class="service-actions">
                            <button class="btn btn-sm btn-${service.active ? 'warning' : 'success'}" 
                                    onclick="moxnas.toggleSystemService('${service.name}')">
                                <i class="fas fa-${service.active ? 'stop' : 'play'}"></i>
                                ${service.active ? 'Stop' : 'Start'}
                            </button>
                            <button class="btn btn-sm btn-secondary" 
                                    onclick="moxnas.restartSystemService('${service.name}')">
                                <i class="fas fa-redo"></i> Restart
                            </button>
                        </div>
                    </div>
                `).join('');
            }
            
        } catch (error) {
            console.error('Error updating system services:', error);
        }
    }

    /**
     * Update system logs
     */
    async updateSystemLogs() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/system/logs/`);
            if (!response.ok) throw new Error('Failed to fetch system logs');
            
            const logs = await response.json();
            
            // Update logs display
            const container = document.getElementById('system-logs');
            if (container) {
                container.innerHTML = logs.map(log => `
                    <div class="log-entry log-${log.level}">
                        <div class="log-timestamp">${new Date(log.timestamp).toLocaleString()}</div>
                        <div class="log-service">${log.service}</div>
                        <div class="log-message">${log.message}</div>
                    </div>
                `).join('');
            }
            
        } catch (error) {
            console.error('Error updating system logs:', error);
        }
    }

    /**
     * Toggle system service
     */
    async toggleSystemService(serviceName) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/system/services/${serviceName}/toggle`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to toggle service');
            }
            
            this.showNotification('success', `Service ${serviceName} toggled successfully`);
            this.updateSystemServices();
            
        } catch (error) {
            console.error('Error toggling system service:', error);
            this.showNotification('error', error.message);
        }
    }

    /**
     * Restart system service
     */
    async restartSystemService(serviceName) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/system/services/${serviceName}/restart`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to restart service');
            }
            
            this.showNotification('success', `Service ${serviceName} restarted successfully`);
            this.updateSystemServices();
            
        } catch (error) {
            console.error('Error restarting system service:', error);
            this.showNotification('error', error.message);
        }
    }

    /**
     * Tasks Management Functions
     */
    
    /**
     * Load tasks data
     */
    async loadTasksData() {
        try {
            await this.updateTasks();
        } catch (error) {
            console.error('Error loading tasks data:', error);
            this.showNotification('error', 'Failed to load tasks data');
        }
    }

    /**
     * Update tasks list
     */
    async updateTasks() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/tasks/`);
            if (!response.ok) throw new Error('Failed to fetch tasks');
            
            const tasks = await response.json();
            
            // Update tasks list
            const container = document.getElementById('tasks-list');
            if (container) {
                if (tasks.length === 0) {
                    container.innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-tasks"></i>
                            <h3>No scheduled tasks</h3>
                            <p>Create your first scheduled task to automate system operations.</p>
                            <button class="btn btn-primary" onclick="moxnas.showModal('add-task-modal')">
                                <i class="fas fa-plus"></i> Add Task
                            </button>
                        </div>
                    `;
                } else {
                    container.innerHTML = tasks.map(task => `
                        <div class="task-item">
                            <div class="task-info">
                                <div class="task-name">${task.name}</div>
                                <div class="task-schedule">${task.schedule}</div>
                                <div class="task-status ${task.enabled ? 'enabled' : 'disabled'}">
                                    ${task.enabled ? 'Enabled' : 'Disabled'}
                                </div>
                            </div>
                            <div class="task-actions">
                                <button class="btn btn-sm btn-${task.enabled ? 'warning' : 'success'}" 
                                        onclick="moxnas.toggleTask('${task.id}')">
                                    <i class="fas fa-${task.enabled ? 'pause' : 'play'}"></i>
                                </button>
                                <button class="btn btn-sm btn-primary" 
                                        onclick="moxnas.editTask('${task.id}')">
                                    <i class="fas fa-edit"></i>
                                </button>
                                <button class="btn btn-sm btn-danger" 
                                        onclick="moxnas.deleteTask('${task.id}')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    `).join('');
                }
            }
            
        } catch (error) {
            console.error('Error updating tasks:', error);
            const container = document.getElementById('tasks-list');
            if (container) {
                container.innerHTML = `
                    <div class="error-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <h3>Failed to load tasks</h3>
                        <p>Error: ${error.message}</p>
                        <button class="btn btn-secondary" onclick="moxnas.updateTasks()">
                            <i class="fas fa-refresh"></i> Retry
                        </button>
                    </div>
                `;
            }
        }
    }

    /**
     * Proxmox Management Functions
     */
    
    /**
     * Initialize Proxmox Manager
     */
    initializeProxmoxManager() {
        console.log('MoxNAS: Initializing Proxmox Manager...');
        if (!window.proxmoxManager) {
            console.log('MoxNAS: Creating new ProxmoxManager instance');
            window.proxmoxManager = new ProxmoxManager();
        } else {
            console.log('MoxNAS: ProxmoxManager already exists, refreshing data');
            window.proxmoxManager.loadHosts();
        }
        // The ProxmoxManager will handle loading its own data
    }

    /**
     * Reporting Functions
     */
    
    /**
     * Load reporting data
     */
    async loadReportingData() {
        try {
            await this.updateReports();
        } catch (error) {
            console.error('Error loading reporting data:', error);
            this.showNotification('error', 'Failed to load reporting data');
        }
    }

    /**
     * Update reports list
     */
    async updateReports() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/reporting/`);
            if (!response.ok) throw new Error('Failed to fetch reports');
            
            const reports = await response.json();
            
            // Update reports display
            const container = document.getElementById('reports-list');
            if (container) {
                container.innerHTML = reports.map(report => `
                    <div class="report-item">
                        <div class="report-info">
                            <div class="report-name">${report.name}</div>
                            <div class="report-date">${new Date(report.created).toLocaleDateString()}</div>
                        </div>
                        <div class="report-actions">
                            <button class="btn btn-sm btn-primary" onclick="moxnas.downloadReport('${report.id}')">
                                <i class="fas fa-download"></i> Download
                            </button>
                        </div>
                    </div>
                `).join('');
            }
            
        } catch (error) {
            console.error('Error updating reports:', error);
        }
    }

    /**
     * Utility Functions
     */
    
    /**
     * Make API call
     */
    async apiCall(endpoint, options = {}) {
        try {
            const url = `${this.apiBaseUrl}${endpoint}`;
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`API call failed: ${response.status} ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API call error:', error);
            throw error;
        }
    }

    /**
     * Show modal
     */
    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
        }
    }

    /**
     * Close modal
     */
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * Handle form submission
     */
    async handleFormSubmit(form) {
        const formId = form.id;
        
        switch (formId) {
            case 'add-storage-form':
                await this.addStoragePool();
                break;
            case 'add-share-form':
                await this.addShare();
                break;
            default:
                console.log('Unhandled form submission:', formId);
        }
    }

    /**
     * Refresh data for specific target
     */
    refreshData(target) {
        switch (target) {
            case 'dashboard':
                this.loadDashboard();
                break;
            case 'storage':
                this.loadStorageData();
                break;
            case 'shares':
                this.loadSharesData();
                break;
            case 'network':
                this.loadNetworkData();
                break;
            case 'system':
                this.loadSystemData();
                break;
            default:
                console.log('Unhandled refresh target:', target);
        }
    }

    /**
     * Show notification
     */
    showNotification(type, message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

        // Add to notifications container
        let container = document.getElementById('notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notifications-container';
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }

        container.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    /**
     * Get notification icon based on type
     */
    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    /**
     * Show alert
     */
    showAlert(type, message) {
        alert(`${type.toUpperCase()}: ${message}`);
    }

    /**
     * Update dashboard storage count
     */
    updateDashboardStorageCount(count) {
        const element = document.getElementById('storage-pools-count');
        if (element) {
            element.textContent = count;
        }
    }

    /**
     * Update dashboard shares count
     */
    updateDashboardSharesCount(count) {
        const element = document.getElementById('shares-count');
        if (element) {
            element.textContent = count;
        }
    }

    /**
     * Start periodic updates
     */
    startPeriodicUpdates() {
        // Update dashboard every 30 seconds
        this.intervals.push(setInterval(() => {
            if (this.currentPage === 'dashboard') {
                this.loadDashboard();
            }
        }, 30000));

        // Update current page data every 60 seconds
        this.intervals.push(setInterval(() => {
            this.loadPageData(this.currentPage);
        }, 60000));
    }

    /**
     * Stop periodic updates
     */
    stopPeriodicUpdates() {
        this.intervals.forEach(interval => clearInterval(interval));
        this.intervals = [];
    }

    /**
     * Cleanup when page unloads
     */
    cleanup() {
        this.stopPeriodicUpdates();
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};
    }
}

// Initialize MoxNAS when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.moxnas = new MoxNAS();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.moxnas) {
        window.moxnas.cleanup();
    }
});
