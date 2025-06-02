/**
 * Simplified Proxmox Management Component for MoxNAS
 * Focuses on displaying data from working API endpoints
 */

class ProxmoxManager {
    constructor() {
        this.currentHost = null;
        this.apiBaseUrl = 'http://localhost:8000/api';
        this.config = null;
        this.init();
    }

    init() {
        console.log('ProxmoxManager: Initializing...');
        this.loadConfiguration().then(() => {
            this.createProxmoxSection();
            this.loadHosts();
            console.log('ProxmoxManager: Initialization complete');
        }).catch(error => {
            console.error('ProxmoxManager: Configuration loading failed:', error);
            // Continue with default configuration
            this.createProxmoxSection();
            this.loadHosts();
        });
    }

    /**
     * Load safe configuration from backend
     */
    async loadConfiguration() {
        try {
            console.log('ProxmoxManager: Loading configuration...');
            const response = await fetch(`${this.apiBaseUrl}/proxmox/api/config/`);
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.config = data.config;
                    console.log('ProxmoxManager: Configuration loaded:', this.config);
                } else {
                    console.warn('ProxmoxManager: Failed to load configuration:', data.error);
                }
            } else {
                console.warn('ProxmoxManager: Configuration request failed:', response.status);
            }
        } catch (error) {
            console.warn('ProxmoxManager: Could not load configuration from backend:', error);
        }
    }

    /**
     * API call method for Proxmox operations
     */
    async apiCall(endpoint, options = {}) {
        try {
            const url = `${this.apiBaseUrl}${endpoint}`;
            console.log('ProxmoxManager: Making API call to:', url);
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            console.log('ProxmoxManager: API response status:', response.status);
            if (!response.ok) {
                throw new Error(`API call failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('ProxmoxManager: API response data:', data);
            return data;
        } catch (error) {
            console.error('Proxmox API call error:', error);
            throw error;
        }
    }

    createProxmoxSection() {
        const container = document.getElementById('proxmox-manager-container');
        if (!container) {
            console.error('ProxmoxManager: Container element not found!');
            return;
        }

        container.innerHTML = `
            <div class="section-header">
                <h2>🖥️ Proxmox Management</h2>
                <div class="section-controls">
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
                        <span class="status-indicator offline">Checking connection...</span>
                        <span id="proxmox-host-info">Loading host information...</span>
                    </div>
                </div>
            </div>

            <!-- Container Creation -->
            <div class="card">
                <div class="card-header">
                    <h3>Create New Container</h3>
                </div>
                <div class="card-content">
                    <form id="create-container-form">
                        <div class="form-grid">
                            <div class="form-group">
                                <label for="container-node">Node:</label>
                                <select id="container-node" name="node" required>
                                    <option value="">Select a node...</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="container-vmid">VMID:</label>
                                <input type="number" id="container-vmid" name="vmid" 
                                       placeholder="e.g., 100" min="100" max="999999" required>
                            </div>
                            <div class="form-group">
                                <label for="container-hostname">Hostname:</label>
                                <input type="text" id="container-hostname" name="hostname" 
                                       placeholder="e.g., truenas-container" required>
                            </div>
                            <div class="form-group">
                                <label for="container-memory">Memory (MB):</label>
                                <input type="number" id="container-memory" name="memory" 
                                       value="4096" min="512" max="32768" required>
                            </div>
                            <div class="form-group">
                                <label for="container-cores">CPU Cores:</label>
                                <input type="number" id="container-cores" name="cores" 
                                       value="2" min="1" max="16" required>
                            </div>
                            <div class="form-group">
                                <label for="container-disk">Disk Size:</label>
                                <input type="text" id="container-disk" name="disk_size" 
                                       value="32G" placeholder="e.g., 32G" required>
                            </div>
                            <div class="form-group">
                                <label for="container-storage">Storage Pool:</label>
                                <select id="container-storage" name="storage_pool" required>
                                    <option value="">Select storage...</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="container-bridge">Network Bridge:</label>
                                <input type="text" id="container-bridge" name="bridge" 
                                       value="vmbr0" required>
                            </div>
                            <div class="form-group">
                                <label for="container-ip-type">IP Configuration:</label>
                                <select id="container-ip-type" name="ip_type" onchange="toggleIpConfig()">
                                    <option value="dhcp">DHCP (Automatic)</option>
                                    <option value="static">Static IP</option>
                                </select>
                            </div>
                            <div class="form-group" id="static-ip-group" style="display: none;">
                                <label for="container-ip">IP Address:</label>
                                <input type="text" id="container-ip" name="ip_address" 
                                       placeholder="e.g., 192.168.1.100/24">
                            </div>
                            <div class="form-group" id="gateway-group" style="display: none;">
                                <label for="container-gateway">Gateway:</label>
                                <input type="text" id="container-gateway" name="gateway" 
                                       placeholder="e.g., 192.168.1.1">
                            </div>
                        </div>
                        <div class="form-actions">
                            <button type="button" id="create-container-btn" class="btn btn-primary">
                                Create Container
                            </button>
                            <button type="button" id="refresh-data-btn" class="btn btn-outline">
                                Refresh Data
                            </button>
                        </div>
                    </form>
                </div>
            </div>

            <!-- Data Display -->
            <div class="card">
                <div class="card-header">
                    <h3>Proxmox Data</h3>
                </div>
                <div class="card-content">
                    <div id="proxmox-data">
                        <p>Loading Proxmox data...</p>
                    </div>
                </div>
            </div>
        `;

        this.attachEventListeners();
        console.log('ProxmoxManager: Section created');
    }

    attachEventListeners() {
        const refreshBtn = document.getElementById('refresh-proxmox-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                console.log('ProxmoxManager: Refresh button clicked');
                this.loadHosts();
            });
        }

        // Container creation form listeners
        const createBtn = document.getElementById('create-container-btn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                this.createContainer();
            });
        }

        const refreshDataBtn = document.getElementById('refresh-data-btn');
        if (refreshDataBtn) {
            refreshDataBtn.addEventListener('click', () => {
                this.loadAllData();
            });
        }

        // IP type change handler - using global function to avoid scope issues
        window.toggleIpConfig = () => {
            const ipType = document.getElementById('container-ip-type').value;
            const staticGroup = document.getElementById('static-ip-group');
            const gatewayGroup = document.getElementById('gateway-group');
            
            if (ipType === 'static') {
                staticGroup.style.display = 'block';
                gatewayGroup.style.display = 'block';
            } else {
                staticGroup.style.display = 'none';
                gatewayGroup.style.display = 'none';
            }
        };
    }

    async loadHosts() {
        try {
            console.log('ProxmoxManager: Loading hosts...');
            const hosts = await this.apiCall('/proxmox/api/hosts/');
            console.log('ProxmoxManager: Hosts loaded:', hosts);
            
            this.displayHosts(hosts);
            
            if (hosts && hosts.length > 0) {
                const connectedHost = hosts.find(h => h.is_connected);
                if (connectedHost) {
                    this.currentHost = connectedHost;
                    this.updateConnectionStatus(true, connectedHost);
                    this.loadAllData();
                } else {
                    this.updateConnectionStatus(false);
                }
            }
        } catch (error) {
            console.error('Error loading Proxmox hosts:', error);
            this.displayError('Failed to load Proxmox hosts: ' + error.message);
        }
    }

    async loadAllData() {
        if (!this.currentHost) {
            console.log('ProxmoxManager: No current host, skipping data load');
            return;
        }

        try {
            console.log('ProxmoxManager: Loading all data...');
            
            // Show loading state in UI
            const dataElement = document.getElementById('proxmox-data');
            if (dataElement) {
                dataElement.innerHTML = '<p>🔄 Loading Proxmox data...</p>';
            }
            
            // Load data sequentially to avoid overwhelming the API
            console.log('ProxmoxManager: Fetching nodes...');
            const nodes = await this.apiCall('/proxmox/api/nodes/');
            console.log('ProxmoxManager: Nodes loaded:', nodes);

            console.log('ProxmoxManager: Fetching containers...');
            const containers = await this.apiCall('/proxmox/api/containers/');
            console.log('ProxmoxManager: Containers loaded:', containers);
            
            console.log('ProxmoxManager: Fetching storage...');
            const storage = await this.apiCall('/proxmox/api/storage/');
            console.log('ProxmoxManager: Storage loaded:', storage);
            
            console.log('ProxmoxManager: All data loaded, updating UI...');
            this.displayAllData({ nodes, containers, storage });
            this.populateFormOptions({ nodes, storage });
            
        } catch (error) {
            console.error('Error loading Proxmox data:', error);
            this.displayError('Failed to load Proxmox data: ' + error.message);
        }
    }

    populateFormOptions(data) {
        // Populate nodes dropdown
        const nodeSelect = document.getElementById('container-node');
        if (nodeSelect && data.nodes) {
            nodeSelect.innerHTML = '<option value="">Select a node...</option>';
            data.nodes.forEach(node => {
                const option = document.createElement('option');
                option.value = node.name;
                option.textContent = `${node.name} (${node.status})`;
                nodeSelect.appendChild(option);
            });
        }

        // Populate storage dropdown
        const storageSelect = document.getElementById('container-storage');
        if (storageSelect && data.storage) {
            storageSelect.innerHTML = '<option value="">Select storage...</option>';
            data.storage.forEach(storage => {
                const option = document.createElement('option');
                option.value = storage.storage || storage.storage_id || 'local-lvm';
                option.textContent = `${storage.storage || storage.storage_id} (${storage.type || 'unknown'})`;
                storageSelect.appendChild(option);
            });
        }
    }

    async createContainer() {
        try {
            console.log('ProxmoxManager: Creating container...');
            
            // Get form data
            const form = document.getElementById('create-container-form');
            const formData = new FormData(form);
            const containerData = Object.fromEntries(formData.entries());
            
            console.log('ProxmoxManager: Container data:', containerData);
            
            // Validate required fields
            const requiredFields = ['node', 'vmid', 'hostname', 'memory', 'cores', 'disk_size', 'storage_pool'];
            for (const field of requiredFields) {
                if (!containerData[field]) {
                    this.showNotification(`Please fill in the ${field} field`, 'error');
                    return;
                }
            }
            
            // Show loading state
            const createBtn = document.getElementById('create-container-btn');
            const originalText = createBtn.textContent;
            createBtn.textContent = 'Creating...';
            createBtn.disabled = true;
            
            // Make API call
            const response = await this.apiCall('/proxmox/api/containers/create_container/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(containerData)
            });
            
            console.log('ProxmoxManager: Container creation response:', response);
            
            if (response.success) {
                this.showNotification(`Container ${containerData.vmid} created successfully!`, 'success');
                // Reset form
                form.reset();
                // Refresh data
                this.loadAllData();
            } else {
                this.showNotification(`Failed to create container: ${response.error || 'Unknown error'}`, 'error');
            }
            
        } catch (error) {
            console.error('Error creating container:', error);
            this.showNotification(`Error creating container: ${error.message}`, 'error');
        } finally {
            // Restore button state
            const createBtn = document.getElementById('create-container-btn');
            createBtn.textContent = 'Create Container';
            createBtn.disabled = false;
        }
    }

    updateConnectionStatus(connected, hostInfo = null) {
        const statusElement = document.getElementById('proxmox-status');
        const infoElement = document.getElementById('proxmox-host-info');
        
        if (statusElement && infoElement) {
            if (connected && hostInfo) {
                statusElement.innerHTML = '<span class="status-indicator online">Connected</span>';
                infoElement.textContent = `${hostInfo.host}:${hostInfo.port} (${hostInfo.user})`;
            } else {
                statusElement.innerHTML = '<span class="status-indicator offline">Disconnected</span>';
                infoElement.textContent = 'No Proxmox host configured or connected';
            }
        }
    }

    displayHosts(hosts) {
        const dataElement = document.getElementById('proxmox-data');
        if (!dataElement) return;

        let html = '<h4>Proxmox Hosts:</h4>';
        if (hosts && hosts.length > 0) {
            html += '<ul>';
            hosts.forEach(host => {
                html += `
                    <li>
                        <strong>${host.name}</strong> - ${host.host}:${host.port} 
                        <span class="status-badge ${host.is_connected ? 'online' : 'offline'}">
                            ${host.is_connected ? 'Connected' : 'Disconnected'}
                        </span>
                    </li>
                `;
            });
            html += '</ul>';
        } else {
            html += '<p>No hosts found.</p>';
        }

        dataElement.innerHTML = html;
    }

    displayAllData(data) {
        const dataElement = document.getElementById('proxmox-data');
        if (!dataElement) return;

        let html = '<div class="proxmox-data-display">';
        
        // Nodes
        html += '<h4>Nodes:</h4>';
        if (data.nodes && data.nodes.length > 0) {
            html += '<ul>';
            data.nodes.forEach(node => {
                html += `<li><strong>${node.name}</strong> - Status: ${node.status} (${node.type})</li>`;
            });
            html += '</ul>';
        } else {
            html += '<p>No nodes found.</p>';
        }

        // Containers
        html += '<h4>Containers:</h4>';
        if (data.containers && data.containers.length > 0) {
            html += '<ul>';
            data.containers.forEach(container => {
                html += `
                    <li>
                        <strong>CT${container.vmid}</strong> - ${container.name} 
                        <span class="status-badge ${container.status === 'running' ? 'online' : 'offline'}">
                            ${container.status}
                        </span>
                        (Node: ${container.node}, Memory: ${container.memory}MB, Cores: ${container.cores})
                    </li>
                `;
            });
            html += '</ul>';
        } else {
            html += '<p>No containers found.</p>';
        }

        // Storage
        html += '<h4>Storage:</h4>';
        if (data.storage && data.storage.length > 0) {
            html += '<ul>';
            data.storage.forEach(store => {
                const storageId = store.storage || store.storage_id || 'Unknown';
                const storageType = store.type || store.storage_type || 'Unknown';
                const nodeInfo = store.node || 'Unknown';
                html += `<li><strong>${storageId}</strong> - ${storageType} (Node: ${nodeInfo})</li>`;
            });
            html += '</ul>';
        } else {
            html += '<p>No storage found.</p>';
        }

        html += '</div>';
        dataElement.innerHTML = html;
    }

    displayError(message) {
        const dataElement = document.getElementById('proxmox-data');
        if (dataElement) {
            dataElement.innerHTML = `<div class="error-message"><strong>Error:</strong> ${message}</div>`;
        }
    }

    // Add utility method for notifications
    showNotification(message, type = 'info') {
        console.log(`ProxmoxManager Notification [${type}]:`, message);
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.remove()">&times;</button>
        `;
        
        // Add to page
        const container = document.getElementById('proxmox-manager-container');
        if (container) {
            container.insertBefore(notification, container.firstChild);
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 5000);
        }
    }
}

// Make ProxmoxManager available globally
window.ProxmoxManager = ProxmoxManager;
