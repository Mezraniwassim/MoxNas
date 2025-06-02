/**
 * Proxmox Management Component for MoxNAS
 * Provides interface to manage Proxmox VE hosts, nodes, containers, and storage
 */

class ProxmoxManager {
    constructor() {
        this.currentHost = null;
        this.refreshInterval = null;
        this.apiBaseUrl = 'http://localhost:8000/api';
        this.config = null;
        this.init();
    }

    init() {
        console.log('ProxmoxManager: Initializing...');
        this.loadConfiguration().then(() => {
            this.createProxmoxSection();
            this.loadHosts();
            this.startAutoRefresh();
            console.log('ProxmoxManager: Initialization complete');
        });
    }

    /**
     * Load safe configuration from backend
     */
    async loadConfiguration() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/proxmox/api/config/`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.config = data.config;
                    console.log('Configuration loaded:', this.config);
                } else {
                    console.warn('Failed to load configuration:', data.error);
                }
            }
        } catch (error) {
            console.warn('Could not load configuration from backend:', error);
        }
    }

    /**
     * Pre-fill form with configuration values
     */
    fillConnectionForm() {
        if (!this.config || !this.config.proxmox) return;
        
        const form = document.getElementById('proxmox-connect-form');
        if (!form) return;
        
        const config = this.config.proxmox;
        if (config.host) {
            document.getElementById('proxmox-host').value = config.host;
        }
        if (config.port) {
            document.getElementById('proxmox-port').value = config.port;
        }
        if (config.user) {
            document.getElementById('proxmox-user').value = config.user;
        }
        if (config.verify_ssl !== undefined) {
            document.getElementById('proxmox-verify-ssl').checked = config.verify_ssl;
        }
    }

    /**
     * API call method for Proxmox operations
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
            console.error('Proxmox API call error:', error);
            throw error;
        }
    }

    createProxmoxSection() {
        const container = document.getElementById('proxmox-manager-container');
        if (!container) return;

        container.innerHTML = `
            <div class="section-header">
                <h2>🖥️ Proxmox Management</h2>
                <div class="section-controls">
                    <button id="connect-proxmox-btn" class="btn btn-primary">Connect to Proxmox</button>
                    <button id="sync-proxmox-btn" class="btn btn-secondary">Sync Data</button>
                    <button id="refresh-proxmox-btn" class="btn btn-outline">Refresh</button>
                </div>
            </div>

            <!-- Connection Status -->
            <div class="card">
                <div class="card-header">
                    <h3>Connection Status</h3>
                </div>
                <div class="card-content">
                    <div id="proxmox-status">
                        <span class="status-indicator offline">Disconnected</span>
                        <span id="proxmox-host-info">No Proxmox host configured</span>
                    </div>
                </div>
            </div>

            <!-- Cluster Overview -->
            <div class="card">
                <div class="card-header">
                    <h3>Cluster Overview</h3>
                </div>
                <div class="card-content">
                    <div id="cluster-stats" class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-value" id="total-nodes">0</span>
                            <span class="stat-label">Nodes</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="total-containers">0</span>
                            <span class="stat-label">Containers</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="running-containers">0</span>
                            <span class="stat-label">Running</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="total-storage">0</span>
                            <span class="stat-label">Storage Pools</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Nodes -->
            <div class="card">
                <div class="card-header">
                    <h3>Nodes</h3>
                </div>
                <div class="card-content">
                    <div id="nodes-list" class="table-container">
                        <p class="loading">Loading nodes...</p>
                    </div>
                </div>
            </div>

            <!-- Containers -->
            <div class="card">
                <div class="card-header">
                    <h3>LXC Containers</h3>
                    <div class="card-controls">
                        <button id="create-container-btn" class="btn btn-primary btn-sm">Create Container</button>
                    </div>
                </div>
                <div class="card-content">
                    <div id="containers-list" class="table-container">
                        <p class="loading">Loading containers...</p>
                    </div>
                </div>
            </div>

            <!-- Storage -->
            <div class="card">
                <div class="card-header">
                    <h3>Storage</h3>
                </div>
                <div class="card-content">
                    <div id="storage-list" class="table-container">
                        <p class="loading">Loading storage...</p>
                    </div>
                </div>
            </div>

            <!-- Connection Modal -->
            <div id="proxmox-connect-modal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Connect to Proxmox VE</h3>
                        <span class="close">&times;</span>
                    </div>
                    <div class="modal-body">
                        <form id="proxmox-connect-form">
                            <div class="form-group">
                                <label for="proxmox-host">Host/IP Address:</label>
                                <input type="text" id="proxmox-host" placeholder="Enter Proxmox host IP" required>
                            </div>
                            <div class="form-group">
                                <label for="proxmox-port">Port:</label>
                                <input type="number" id="proxmox-port" value="8006" required>
                                <small>Standard Proxmox port (8006)</small>
                            </div>
                            <div class="form-group">
                                <label for="proxmox-user">Username:</label>
                                <input type="text" id="proxmox-user" value="root@pam" required>
                            </div>
                            <div class="form-group">
                                <label for="proxmox-password">Password:</label>
                                <input type="password" id="proxmox-password" required>
                            </div>
                            <div class="form-group">
                                <label>
                                    <input type="checkbox" id="proxmox-verify-ssl"> Verify SSL Certificate
                                </label>
                            </div>
                            <div class="form-actions">
                                <button type="submit" class="btn btn-primary">Connect</button>
                                <button type="button" class="btn btn-secondary" onclick="closeModal('proxmox-connect-modal')">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Container Creation Modal -->
            <div id="create-container-modal" class="modal">
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Create LXC Container</h3>
                        <span class="close">&times;</span>
                    </div>
                    <div class="modal-body">
                        <form id="create-container-form">
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="container-node">Node:</label>
                                    <select id="container-node" required>
                                        <option value="">Select Node</option>
                                    </select>
                                </div>
                                <div class="form-group">
                                    <label for="container-vmid">VMID:</label>
                                    <input type="number" id="container-vmid" min="100" max="999999" required>
                                    <small>Unique container ID (100-999999)</small>
                                </div>
                            </div>
                            
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="container-hostname">Hostname:</label>
                                    <input type="text" id="container-hostname" pattern="[a-zA-Z0-9-]+" required>
                                    <small>Container hostname (alphanumeric and hyphens only)</small>
                                </div>
                                <div class="form-group">
                                    <label for="container-template">Template:</label>
                                    <select id="container-template" required>
                                        <option value="">Select Template</option>
                                    </select>
                                </div>
                            </div>

                            <h4>Resource Configuration</h4>
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="container-memory">Memory (MB):</label>
                                    <input type="number" id="container-memory" value="4096" min="512" max="65536" required>
                                </div>
                                <div class="form-group">
                                    <label for="container-cores">CPU Cores:</label>
                                    <input type="number" id="container-cores" value="2" min="1" max="32" required>
                                </div>
                            </div>

                            <div class="form-row">
                                <div class="form-group">
                                    <label for="container-disk-size">Disk Size:</label>
                                    <input type="text" id="container-disk-size" value="32G" pattern="[0-9]+G" required>
                                    <small>Size in GB (e.g., 32G, 64G)</small>
                                </div>
                                <div class="form-group">
                                    <label for="container-storage-pool">Storage Pool:</label>
                                    <select id="container-storage-pool" required>
                                        <option value="">Select Storage</option>
                                    </select>
                                </div>
                            </div>

                            <h4>Network Configuration</h4>
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="container-bridge">Network Bridge:</label>
                                    <input type="text" id="container-bridge" value="vmbr0" required>
                                </div>
                                <div class="form-group">
                                    <label for="container-ip">IP Configuration:</label>
                                    <select id="container-ip-type" onchange="toggleIPFields()">
                                        <option value="dhcp">DHCP</option>
                                        <option value="static">Static IP</option>
                                    </select>
                                </div>
                            </div>

                            <div id="static-ip-fields" style="display: none;">
                                <div class="form-row">
                                    <div class="form-group">
                                        <label for="container-static-ip">IP Address/CIDR:</label>
                                        <input type="text" id="container-static-ip" placeholder="192.168.1.100/24">
                                    </div>
                                    <div class="form-group">
                                        <label for="container-gateway">Gateway:</label>
                                        <input type="text" id="container-gateway" placeholder="192.168.1.1">
                                    </div>
                                </div>
                            </div>

                            <div class="form-actions">
                                <button type="submit" class="btn btn-primary">Create Container</button>
                                <button type="button" class="btn btn-secondary" onclick="closeModal('create-container-modal')">Cancel</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;

        this.attachEventListeners();
    }

    attachEventListeners() {
        // Connect button
        document.getElementById('connect-proxmox-btn').addEventListener('click', () => {
            document.getElementById('proxmox-connect-modal').style.display = 'block';
            this.fillConnectionForm(); // Pre-fill with configuration
        });

        // Sync button
        document.getElementById('sync-proxmox-btn').addEventListener('click', () => {
            this.syncData();
        });

        // Refresh button
        document.getElementById('refresh-proxmox-btn').addEventListener('click', () => {
            this.loadData();
        });

        // Connect form
        document.getElementById('proxmox-connect-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.connectToProxmox();
        });

        // Modal close
        document.querySelector('#proxmox-connect-modal .close').addEventListener('click', () => {
            document.getElementById('proxmox-connect-modal').style.display = 'none';
        });

        // Create container button
        document.getElementById('create-container-btn').addEventListener('click', () => {
            this.loadContainerCreationData();
            document.getElementById('create-container-modal').style.display = 'block';
        });

        // Create container form
        document.getElementById('create-container-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createContainer();
        });

        // Modal close
        document.querySelector('#create-container-modal .modal-close').addEventListener('click', () => {
            document.getElementById('create-container-modal').style.display = 'none';
        });
    }

    async connectToProxmox() {
        const host = document.getElementById('proxmox-host').value;
        const port = parseInt(document.getElementById('proxmox-port').value);
        const user = document.getElementById('proxmox-user').value;
        const password = document.getElementById('proxmox-password').value;
        const verify_ssl = document.getElementById('proxmox-verify-ssl').checked;

        try {
            showLoading();
            const response = await apiCall('/api/proxmox/api/connect/', 'POST', {
                host,
                port,
                user,
                password,
                verify_ssl
            });

            if (response.success) {
                showNotification('Connected to Proxmox successfully!', 'success');
                document.getElementById('proxmox-connect-modal').style.display = 'none';
                this.updateConnectionStatus(true, { host, port, user });
                await this.syncData();
                this.loadData();
            } else {
                throw new Error(response.error || 'Connection failed');
            }
        } catch (error) {
            console.error('Proxmox connection error:', error);
            showNotification(`Failed to connect to Proxmox: ${error.message}`, 'error');
        } finally {
            hideLoading();
        }
    }

    async syncData() {
        try {
            showLoading();
            const response = await apiCall('/api/proxmox/api/sync/', 'POST');
            
            if (response.success) {
                showNotification(`Synced: ${response.stats.nodes} nodes, ${response.stats.containers} containers, ${response.stats.storage} storage pools`, 'success');
                this.loadData();
            } else {
                throw new Error(response.error || 'Sync failed');
            }
        } catch (error) {
            console.error('Proxmox sync error:', error);
            showNotification(`Sync failed: ${error.message}`, 'error');
        } finally {
            hideLoading();
        }
    }

    async loadHosts() {
        try {
            console.log('ProxmoxManager: Loading hosts...');
            const hosts = await this.apiCall('/proxmox/api/hosts/');
            console.log('ProxmoxManager: Hosts loaded:', hosts);
            if (hosts && hosts.length > 0) {
                const connectedHost = hosts.find(h => h.is_connected);
                if (connectedHost) {
                    this.currentHost = connectedHost;
                    this.updateConnectionStatus(true, connectedHost);
                    this.loadData();
                }
            }
        } catch (error) {
            console.error('Error loading Proxmox hosts:', error);
        }
    }

    async loadData() {
        if (!this.currentHost) {
            return;
        }

        try {
            console.log('ProxmoxManager: Loading data...');
            // Load all data in parallel
            const [nodes, containers, storage] = await Promise.all([
                this.apiCall('/proxmox/api/nodes/'),
                this.apiCall('/proxmox/api/containers/'),
                this.apiCall('/proxmox/api/storage/')
            ]);

            console.log('ProxmoxManager: Data loaded:', { nodes, containers, storage });
            this.updateStats(nodes, containers, storage);
            this.renderNodes(nodes);
            this.renderContainers(containers);
            this.renderStorage(storage);
        } catch (error) {
            console.error('Error loading Proxmox data:', error);
            this.showNotification('Failed to load Proxmox data', 'error');
        }
    }

    updateConnectionStatus(connected, hostInfo = null) {
        const statusElement = document.getElementById('proxmox-status');
        const infoElement = document.getElementById('proxmox-host-info');
        
        if (connected && hostInfo) {
            statusElement.innerHTML = '<span class="status-indicator online">Connected</span>';
            infoElement.textContent = `${hostInfo.host}:${hostInfo.port} (${hostInfo.user})`;
        } else {
            statusElement.innerHTML = '<span class="status-indicator offline">Disconnected</span>';
            infoElement.textContent = 'No Proxmox host configured';
        }
    }

    updateStats(nodes, containers, storage) {
        document.getElementById('total-nodes').textContent = nodes.length;
        document.getElementById('total-containers').textContent = containers.length;
        document.getElementById('running-containers').textContent = 
            containers.filter(c => c.status === 'running').length;
        document.getElementById('total-storage').textContent = storage.length;
    }

    renderNodes(nodes) {
        const container = document.getElementById('nodes-list');
        
        if (!nodes || nodes.length === 0) {
            container.innerHTML = '<p class="no-data">No nodes found</p>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'data-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Node</th>
                    <th>Status</th>
                    <th>Uptime</th>
                    <th>CPU Usage</th>
                    <th>Memory Usage</th>
                    <th>Last Updated</th>
                </tr>
            </thead>
            <tbody>
                ${nodes.map(node => `
                    <tr>
                        <td><strong>${node.name}</strong></td>
                        <td><span class="status-badge ${node.status}">${node.status}</span></td>
                        <td>${this.formatUptime(node.uptime)}</td>
                        <td>${node.cpu_usage.toFixed(1)}%</td>
                        <td>
                            ${this.formatBytes(node.memory_used)} / ${this.formatBytes(node.memory_total)}
                            (${node.memory_usage_percentage.toFixed(1)}%)
                        </td>
                        <td>${this.formatDateTime(node.last_updated)}</td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        
        container.innerHTML = '';
        container.appendChild(table);
    }

    renderContainers(containers) {
        const container = document.getElementById('containers-list');
        
        if (!containers || containers.length === 0) {
            container.innerHTML = '<p class="no-data">No containers found</p>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'data-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>VMID</th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Node</th>
                    <th>Memory</th>
                    <th>CPU</th>
                    <th>Uptime</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${containers.map(ct => `
                    <tr>
                        <td><strong>CT${ct.vmid}</strong></td>
                        <td>${ct.name}</td>
                        <td><span class="status-badge ${ct.status}">${ct.status}</span></td>
                        <td>${ct.node}</td>
                        <td>${ct.memory}MB</td>
                        <td>${ct.cores} cores</td>
                        <td>${this.formatUptime(ct.uptime)}</td>
                        <td>
                            <div class="action-buttons">
                                ${ct.status === 'stopped' ? 
                                    `<button class="btn btn-sm btn-success" onclick="proxmoxManager.startContainer(${ct.id})">Start</button>` :
                                    `<button class="btn btn-sm btn-warning" onclick="proxmoxManager.stopContainer(${ct.id})">Stop</button>`
                                }
                                <button class="btn btn-sm btn-info" onclick="proxmoxManager.viewContainer(${ct.id})">Details</button>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        
        container.innerHTML = '';
        container.appendChild(table);
    }

    renderStorage(storage) {
        const container = document.getElementById('storage-list');
        
        if (!storage || storage.length === 0) {
            container.innerHTML = '<p class="no-data">No storage found</p>';
            return;
        }

        const table = document.createElement('table');
        table.className = 'data-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Storage</th>
                    <th>Type</th>
                    <th>Node</th>
                    <th>Usage</th>
                    <th>Content Types</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${storage.map(store => `
                    <tr>
                        <td><strong>${store.storage_id}</strong></td>
                        <td>${store.storage_type}</td>
                        <td>${store.node}</td>
                        <td>
                            ${this.formatBytes(store.used_space)} / ${this.formatBytes(store.total_space)}
                            (${store.usage_percentage.toFixed(1)}%)
                        </td>
                        <td>${store.content_types.join(', ')}</td>
                        <td>
                            <span class="status-badge ${store.enabled ? 'online' : 'offline'}">
                                ${store.enabled ? 'Enabled' : 'Disabled'}
                            </span>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        `;
        
        container.innerHTML = '';
        container.appendChild(table);
    }

    async startContainer(containerId) {
        try {
            const response = await apiCall(`/api/proxmox/api/containers/${containerId}/start/`, 'POST');
            if (response.success) {
                showNotification('Container started successfully', 'success');
                this.loadData();
            } else {
                throw new Error(response.error);
            }
        } catch (error) {
            showNotification(`Failed to start container: ${error.message}`, 'error');
        }
    }

    async stopContainer(containerId) {
        try {
            const response = await apiCall(`/api/proxmox/api/containers/${containerId}/stop/`, 'POST');
            if (response.success) {
                showNotification('Container stopped successfully', 'success');
                this.loadData();
            } else {
                throw new Error(response.error);
            }
        } catch (error) {
            showNotification(`Failed to stop container: ${error.message}`, 'error');
        }
    }

    viewContainer(containerId) {
        // TODO: Implement container details view
        showNotification('Container details view not implemented yet', 'info');
    }

    async createContainer() {
        const node = document.getElementById('container-node').value;
        const vmid = parseInt(document.getElementById('container-vmid').value);
        const hostname = document.getElementById('container-hostname').value;
        const template = document.getElementById('container-template').value;
        const memory = parseInt(document.getElementById('container-memory').value);
        const cores = parseInt(document.getElementById('container-cores').value);
        const diskSize = document.getElementById('container-disk-size').value;
        const storagePool = document.getElementById('container-storage-pool').value;
        const bridge = document.getElementById('container-bridge').value;
        const ipType = document.getElementById('container-ip-type').value;
        let ipAddress = '';
        let gateway = '';

        if (ipType === 'static') {
            ipAddress = document.getElementById('container-static-ip').value;
            gateway = document.getElementById('container-gateway').value;
        }

        try {
            showLoading();
            const response = await apiCall('/api/proxmox/api/containers/create_container/', 'POST', {
                node,
                vmid,
                hostname,
                template,
                memory,
                cores,
                disk_size: diskSize,
                storage_pool: storagePool,
                bridge,
                ip_type: ipType,
                ip_address: ipAddress,
                gateway
            });

            if (response.success) {
                showNotification('Container created successfully', 'success');
                document.getElementById('create-container-modal').style.display = 'none';
                this.loadData();
            } else {
                throw new Error(response.error || 'Container creation failed');
            }
        } catch (error) {
            console.error('Container creation error:', error);
            showNotification(`Failed to create container: ${error.message}`, 'error');
        } finally {
            hideLoading();
        }
    }

    async loadContainerCreationData() {
        try {
            // Load nodes
            const nodesResponse = await apiCall('/api/proxmox/api/containers/nodes/', 'GET');
            if (nodesResponse.success) {
                this.populateNodeSelect(nodesResponse.data);
            }

            // Load templates
            const templatesResponse = await apiCall('/api/proxmox/api/containers/templates/', 'GET');
            if (templatesResponse.success) {
                this.populateTemplateSelect(templatesResponse.data);
            }

            // Load storage pools
            const storageResponse = await apiCall('/api/proxmox/api/containers/storage_pools/', 'GET');
            if (storageResponse.success) {
                this.populateStorageSelect(storageResponse.data);
            }

            // Suggest VMID
            this.suggestVMID();
        } catch (error) {
            console.error('Error loading container creation data:', error);
            showNotification('Failed to load container creation data', 'error');
        }
    }

    populateNodeSelect(nodes) {
        const select = document.getElementById('container-node');
        select.innerHTML = '<option value="">Select Node</option>';
        
        nodes.forEach(node => {
            const option = document.createElement('option');
            option.value = node.name;
            option.textContent = `${node.name} (${node.status})`;
            select.appendChild(option);
        });
    }

    populateTemplateSelect(templates) {
        const select = document.getElementById('container-template');
        select.innerHTML = '<option value="">Select Template</option>';
        
        templates.forEach(template => {
            const option = document.createElement('option');
            option.value = template.volid;
            option.textContent = template.description || template.volid;
            select.appendChild(option);
        });

        // Pre-select Debian if available
        const debianOption = select.querySelector('option[value*="debian"]');
        if (debianOption) {
            debianOption.selected = true;
        }
    }

    populateStorageSelect(storages) {
        const select = document.getElementById('container-storage-pool');
        select.innerHTML = '<option value="">Select Storage</option>';
        
        storages.forEach(storage => {
            if (storage.content && storage.content.includes('rootdir')) {
                const option = document.createElement('option');
                option.value = storage.storage;
                option.textContent = `${storage.storage} (${this.formatBytes(storage.avail)})`;
                select.appendChild(option);
            }
        });
    }

    async suggestVMID() {
        try {
            const response = await apiCall('/api/proxmox/api/containers/', 'GET');
            if (response.success) {
                const usedVMIDs = response.data.map(container => container.vmid);
                let suggestedVMID = 100;
                
                while (usedVMIDs.includes(suggestedVMID)) {
                    suggestedVMID++;
                }
                
                document.getElementById('container-vmid').value = suggestedVMID;
            }
        } catch (error) {
            console.error('Error suggesting VMID:', error);
            document.getElementById('container-vmid').value = 100;
        }
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    startAutoRefresh() {
        // Refresh data every 30 seconds if connected
        this.refreshInterval = setInterval(() => {
            if (this.currentHost) {
                this.loadData();
            }
        }, 30000);
    }

    show() {
        document.getElementById('proxmox-section').style.display = 'block';
        this.loadData();
    }

    hide() {
        document.getElementById('proxmox-section').style.display = 'none';
    }

    // Utility methods
    formatUptime(seconds) {
        if (!seconds) return 'Not running';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }

    formatBytes(bytes) {
        if (!bytes) return '0 B';
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
    }

    formatDateTime(dateString) {
        if (!dateString) return 'Never';
        return new Date(dateString).toLocaleString();
    }
}

// Global function for toggling IP fields in container creation modal
function toggleIPFields() {
    const ipType = document.getElementById('container-ip-type').value;
    const staticFields = document.getElementById('static-ip-fields');
    
    if (ipType === 'static') {
        staticFields.style.display = 'block';
    } else {
        staticFields.style.display = 'none';
    }
}

// ProxmoxManager class is available globally
// Initialize when called by main.js navigation
