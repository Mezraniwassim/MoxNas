/**
 * Proxmox Management Component for MoxNAS
 * Provides interface to manage Proxmox VE hosts, nodes, containers, and storage
 */

class ProxmoxManager {
    constructor() {
        this.currentHost = null;
        this.refreshInterval = null;
        this.init();
    }

    init() {
        this.createProxmoxSection();
        this.loadHosts();
        this.startAutoRefresh();
    }

    createProxmoxSection() {
        const container = document.getElementById('main-content');
        if (!container) return;

        const proxmoxSection = document.createElement('div');
        proxmoxSection.id = 'proxmox-section';
        proxmoxSection.style.display = 'none';
        proxmoxSection.innerHTML = `
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
                    <div class="stats-grid">
                        <div class="stat-item">
                            <span class="stat-value" id="total-nodes">0</span>
                            <span class="stat-label">Nodes</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="online-nodes">0</span>
                            <span class="stat-label">Online</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="total-containers">0</span>
                            <span class="stat-label">Containers</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value" id="running-containers">0</span>
                            <span class="stat-label">Running</span>
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
                    <div class="card-actions">
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
        `;

        container.appendChild(proxmoxSection);
        this.attachEventListeners();
    }

    attachEventListeners() {
        // Connect button
        document.getElementById('connect-proxmox-btn').addEventListener('click', () => {
            document.getElementById('proxmox-connect-modal').style.display = 'block';
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
            this.openCreateContainerModal();
        });
    }

    async openCreateContainerModal() {
        try {
            // Load necessary data for the modal
            await this.loadModalData();
            document.getElementById('create-container-modal').style.display = 'block';
        } catch (error) {
            showNotification('Failed to load container creation data', 'error');
        }
    }

    async loadModalData() {
        try {
            // Load nodes
            const nodesResponse = await apiCall('/api/proxmox/api/containers/nodes/');
            const nodes = nodesResponse.nodes || [];
            
            const nodeSelect = document.getElementById('container-node');
            nodeSelect.innerHTML = '<option value="">Select Node</option>';
            nodes.forEach(node => {
                const option = document.createElement('option');
                option.value = node.name;
                option.textContent = `${node.name} (${node.status})`;
                nodeSelect.appendChild(option);
            });

            // Load templates for first node
            if (nodes.length > 0) {
                await this.loadTemplatesForNode(nodes[0].name);
                await this.loadStorageForNode(nodes[0].name);
            }

            // Add change listener for node selection
            nodeSelect.addEventListener('change', async (e) => {
                if (e.target.value) {
                    await this.loadTemplatesForNode(e.target.value);
                    await this.loadStorageForNode(e.target.value);
                }
            });

            // Generate suggested VMID
            await this.suggestVMID();

        } catch (error) {
            console.error('Error loading modal data:', error);
            throw error;
        }
    }

    async loadTemplatesForNode(nodeName) {
        try {
            const templatesResponse = await apiCall(`/api/proxmox/api/containers/templates/?node=${nodeName}`);
            const templates = templatesResponse.templates || [];
            
            const templateSelect = document.getElementById('container-template');
            templateSelect.innerHTML = '<option value="">Select Template</option>';
            
            templates.forEach(template => {
                const option = document.createElement('option');
                option.value = template.volid;
                option.textContent = template.name;
                templateSelect.appendChild(option);
            });

            // Pre-select Debian template if available
            const debianTemplate = templates.find(t => t.name.includes('debian'));
            if (debianTemplate) {
                templateSelect.value = debianTemplate.volid;
            }

        } catch (error) {
            console.error('Error loading templates:', error);
        }
    }

    async loadStorageForNode(nodeName) {
        try {
            const storageResponse = await apiCall(`/api/proxmox/api/containers/storage_pools/?node=${nodeName}`);
            const storagePools = storageResponse.storage_pools || [];
            
            const storageSelect = document.getElementById('container-storage-pool');
            storageSelect.innerHTML = '<option value="">Select Storage</option>';
            
            storagePools.forEach(storage => {
                const option = document.createElement('option');
                option.value = storage.id;
                option.textContent = `${storage.id} (${storage.type}) - ${this.formatBytes(storage.available)} available`;
                storageSelect.appendChild(option);
            });

            // Pre-select local-lvm if available
            const localLvm = storagePools.find(s => s.id === 'local-lvm');
            if (localLvm) {
                storageSelect.value = 'local-lvm';
            }

        } catch (error) {
            console.error('Error loading storage:', error);
        }
    }

    async suggestVMID() {
        try {
            const containersResponse = await apiCall('/api/proxmox/api/containers/');
            const containers = containersResponse || [];
            
            // Find next available VMID starting from 200
            let vmid = 200;
            const usedVMIDs = containers.map(c => c.vmid).sort((a, b) => a - b);
            
            while (usedVMIDs.includes(vmid)) {
                vmid++;
            }
            
            document.getElementById('container-vmid').value = vmid;
            
        } catch (error) {
            console.error('Error suggesting VMID:', error);
            document.getElementById('container-vmid').value = 200;
        }
    }

    async createContainer() {
        try {
            const formData = {
                node: document.getElementById('container-node').value,
                vmid: parseInt(document.getElementById('container-vmid').value),
                hostname: document.getElementById('container-hostname').value,
                memory: parseInt(document.getElementById('container-memory').value),
                cores: parseInt(document.getElementById('container-cores').value),
                disk_size: document.getElementById('container-disk-size').value,
                storage_pool: document.getElementById('container-storage-pool').value,
                template_storage: 'local',
                network_bridge: document.getElementById('container-bridge').value,
                ipv4: document.getElementById('container-ip-type').value === 'dhcp' ? 'dhcp' : document.getElementById('container-static-ip').value,
                gateway: document.getElementById('container-ip-type').value === 'static' ? document.getElementById('container-gateway').value : null
            };

            // Validate required fields
            if (!formData.node || !formData.vmid || !formData.hostname || !formData.storage_pool) {
                showNotification('Please fill in all required fields', 'error');
                return;
            }

            showNotification('Creating container...', 'info');
            
            const response = await apiCall('/api/proxmox/api/containers/create_container/', 'POST', formData);
            
            if (response.success) {
                showNotification(`Container ${formData.vmid} created successfully`, 'success');
                document.getElementById('create-container-modal').style.display = 'none';
                this.loadData(); // Refresh the container list
                
                // Reset form
                document.getElementById('create-container-form').reset();
            } else {
                throw new Error(response.error || 'Failed to create container');
            }

        } catch (error) {
            console.error('Error creating container:', error);
            showNotification(`Failed to create container: ${error.message}`, 'error');
        }
    }

    async loadHosts() {
        try {
            const hosts = await apiCall('/api/proxmox/api/hosts/');
            this.updateConnectionStatus(hosts);
        } catch (error) {
            console.error('Error loading hosts:', error);
        }
    }

    updateConnectionStatus(hosts) {
        const statusIndicator = document.querySelector('#proxmox-status .status-indicator');
        const hostInfo = document.getElementById('proxmox-host-info');
        
        const connectedHost = hosts.find(host => host.is_connected);
        
        if (connectedHost) {
            statusIndicator.className = 'status-indicator online';
            statusIndicator.textContent = 'Connected';
            hostInfo.textContent = `${connectedHost.name} (${connectedHost.host}:${connectedHost.port})`;
            this.currentHost = connectedHost;
            this.loadData();
        } else {
            statusIndicator.className = 'status-indicator offline';
            statusIndicator.textContent = 'Disconnected';
            hostInfo.textContent = 'No Proxmox host configured';
            this.currentHost = null;
        }
    }

    async connectToProxmox() {
        try {
            const host = document.getElementById('proxmox-host').value;
            const port = document.getElementById('proxmox-port').value;
            const user = document.getElementById('proxmox-user').value;
            const password = document.getElementById('proxmox-password').value;
            const verify_ssl = document.getElementById('proxmox-verify-ssl').checked;
            
            showNotification('Connecting to Proxmox...', 'info');
            
            const response = await apiCall('/api/proxmox/api/connect/', 'POST', {
                host,
                port: parseInt(port),
                user,
                password,
                verify_ssl
            });
            
            if (response.success) {
                showNotification('Connected to Proxmox successfully', 'success');
                document.getElementById('proxmox-connect-modal').style.display = 'none';
                document.getElementById('proxmox-password').value = '';
                this.loadHosts();
            } else {
                throw new Error(response.error);
            }
        } catch (error) {
            showNotification(`Connection failed: ${error.message}`, 'error');
        }
    }

    async syncData() {
        try {
            showNotification('Syncing Proxmox data...', 'info');
            const response = await apiCall('/api/proxmox/api/sync/', 'POST');
            
            if (response.success) {
                showNotification(`Synced: ${response.stats.nodes} nodes, ${response.stats.containers} containers, ${response.stats.storage} storage pools`, 'success');
                this.loadData();
            } else {
                throw new Error(response.error);
            }
        } catch (error) {
            showNotification(`Sync failed: ${error.message}`, 'error');
        }
    }

    async loadData() {
        if (!this.currentHost) return;
        
        try {
            const [nodes, containers, storage] = await Promise.all([
                apiCall('/api/proxmox/api/nodes/'),
                apiCall('/api/proxmox/api/containers/'),
                apiCall('/api/proxmox/api/storage/')
            ]);
            
            this.renderNodes(nodes);
            this.renderContainers(containers);
            this.renderStorage(storage);
            this.updateStats(nodes, containers);
            
        } catch (error) {
            console.error('Error loading data:', error);
            showNotification('Failed to load Proxmox data', 'error');
        }
    }

    updateStats(nodes, containers) {
        document.getElementById('total-nodes').textContent = nodes.length;
        document.getElementById('online-nodes').textContent = nodes.filter(n => n.status === 'online').length;
        document.getElementById('total-containers').textContent = containers.length;
        document.getElementById('running-containers').textContent = containers.filter(c => c.status === 'running').length;
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
                    <th>CPU Usage</th>
                    <th>Memory</th>
                    <th>Uptime</th>
                </tr>
            </thead>
            <tbody>
                ${nodes.map(node => `
                    <tr>
                        <td><strong>${node.name}</strong></td>
                        <td><span class="status-badge ${node.status}">${node.status}</span></td>
                        <td>${node.cpu_usage.toFixed(1)}%</td>
                        <td>${this.formatBytes(node.memory_used)} / ${this.formatBytes(node.memory_total)}</td>
                        <td>${this.formatUptime(node.uptime)}</td>
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
        return new Date(dateString).toLocaleString();
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// Global functions for modal and form handling
function toggleIPFields() {
    const ipType = document.getElementById('container-ip-type').value;
    const staticFields = document.getElementById('static-ip-fields');
    
    if (ipType === 'static') {
        staticFields.style.display = 'block';
        document.getElementById('container-static-ip').required = true;
    } else {
        staticFields.style.display = 'none';
        document.getElementById('container-static-ip').required = false;
    }
}

// Initialize Proxmox manager
const proxmoxManager = new ProxmoxManager();
