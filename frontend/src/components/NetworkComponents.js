/**
 * Network Components for MoxNAS Frontend
 * Handles network interface management and display
 */

class NetworkComponents {
    constructor() {
        this.interfaces = [];
        this.services = [];
    }

    /**
     * Initialize network components
     */
    init() {
        this.bindEvents();
        this.loadNetworkData();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // DHCP toggle handler
        const dhcpCheckbox = document.getElementById('dhcp-enabled');
        if (dhcpCheckbox) {
            dhcpCheckbox.addEventListener('change', this.toggleDHCP.bind(this));
        }

        const editDhcpCheckbox = document.getElementById('edit-dhcp-enabled');
        if (editDhcpCheckbox) {
            editDhcpCheckbox.addEventListener('change', this.toggleEditDHCP.bind(this));
        }
    }

    /**
     * Toggle DHCP configuration fields
     */
    toggleDHCP(event) {
        const staticConfig = document.getElementById('static-config');
        if (staticConfig) {
            staticConfig.style.display = event.target.checked ? 'none' : 'block';
        }
    }

    /**
     * Toggle DHCP configuration fields in edit modal
     */
    toggleEditDHCP(event) {
        const staticConfig = document.getElementById('edit-static-config');
        if (staticConfig) {
            staticConfig.style.display = event.target.checked ? 'none' : 'block';
        }
    }

    /**
     * Load network data
     */
    async loadNetworkData() {
        try {
            // Load interfaces and services in parallel
            const [interfacesData, servicesData] = await Promise.all([
                this.loadInterfaces(),
                this.loadServices()
            ]);

            this.interfaces = interfacesData || [];
            this.services = servicesData || [];

            this.renderInterfaces();
            this.renderServices();
            this.updateNetworkStats();

        } catch (error) {
            console.error('Error loading network data:', error);
            this.showNetworkError('Failed to load network data');
        }
    }

    /**
     * Load network interfaces
     */
    async loadInterfaces() {
        try {
            return await window.moxnasAPI.getNetworkInterfaces();
        } catch (error) {
            console.error('Error loading network interfaces:', error);
            return this.getMockInterfaces();
        }
    }

    /**
     * Load network services
     */
    async loadServices() {
        try {
            return await window.moxnasAPI.getNetworkServices();
        } catch (error) {
            console.error('Error loading network services:', error);
            return this.getMockServices();
        }
    }

    /**
     * Render network interfaces
     */
    renderInterfaces() {
        const container = document.getElementById('network-interfaces');
        if (!container) return;

        if (this.interfaces.length === 0) {
            container.innerHTML = `
                <div class="truenas-empty-state">
                    <i class="fas fa-network-wired"></i>
                    <p>No network interfaces found</p>
                    <button class="truenas-btn truenas-btn-primary" onclick="moxnas.showModal('add-interface-modal')">
                        <i class="fas fa-plus"></i> Add Interface
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = this.interfaces.map(interface => `
            <div class="truenas-interface-item" data-interface-id="${interface.id}">
                <div class="interface-info">
                    <div class="interface-header">
                        <h4>${interface.name}</h4>
                        <span class="truenas-badge ${interface.status === 'up' ? 'truenas-badge-success' : 'truenas-badge-danger'}">
                            ${interface.status || 'unknown'}
                        </span>
                    </div>
                    <div class="interface-details">
                        <span class="interface-type">${interface.type || 'ethernet'}</span>
                        <span class="interface-ip">${interface.ip_address || 'No IP'}</span>
                        <span class="interface-speed">${interface.speed || 'Unknown'}</span>
                    </div>
                </div>
                <div class="interface-actions">
                    <button class="truenas-btn truenas-btn-sm truenas-btn-secondary" onclick="networkComponents.editInterface(${interface.id})">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="truenas-btn truenas-btn-sm truenas-btn-danger" onclick="networkComponents.deleteInterface(${interface.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }

    /**
     * Render network services
     */
    renderServices() {
        // Services are already rendered in HTML, just update status
        this.services.forEach(service => {
            const statusElement = document.getElementById(`${service.name}-status`);
            if (statusElement) {
                statusElement.textContent = service.status;
                statusElement.className = `truenas-badge ${service.enabled ? 'truenas-badge-success' : 'truenas-badge-danger'}`;
            }
        });
    }

    /**
     * Update network statistics
     */
    updateNetworkStats() {
        // Mock network statistics
        const stats = {
            rx_bytes: '1.2 GB',
            tx_bytes: '856 MB',
            rx_packets: '15,432',
            tx_packets: '12,876'
        };

        document.getElementById('network-rx-bytes').textContent = stats.rx_bytes;
        document.getElementById('network-tx-bytes').textContent = stats.tx_bytes;
        document.getElementById('network-rx-packets').textContent = stats.rx_packets;
        document.getElementById('network-tx-packets').textContent = stats.tx_packets;
    }

    /**
     * Edit network interface
     */
    editInterface(interfaceId) {
        const interface = this.interfaces.find(i => i.id === interfaceId);
        if (!interface) return;

        // Populate edit form
        document.getElementById('edit-interface-id').value = interface.id;
        document.getElementById('edit-interface-name').value = interface.name;
        document.getElementById('edit-interface-type').value = interface.type;
        document.getElementById('edit-dhcp-enabled').checked = interface.dhcp_enabled;
        document.getElementById('edit-ip-address').value = interface.ip_address || '';
        document.getElementById('edit-netmask').value = interface.netmask || '';
        document.getElementById('edit-gateway').value = interface.gateway || '';
        document.getElementById('edit-dns-servers').value = interface.dns_servers ? interface.dns_servers.join(', ') : '';
        document.getElementById('edit-mtu').value = interface.mtu || 1500;
        document.getElementById('edit-interface-enabled').checked = interface.enabled;

        // Show/hide static config based on DHCP setting
        const staticConfig = document.getElementById('edit-static-config');
        if (staticConfig) {
            staticConfig.style.display = interface.dhcp_enabled ? 'none' : 'block';
        }

        // Show modal
        if (window.moxnas) {
            window.moxnas.showModal('edit-interface-modal');
        }
    }

    /**
     * Delete network interface
     */
    async deleteInterface(interfaceId) {
        if (!confirm('Are you sure you want to delete this interface?')) {
            return;
        }

        try {
            await window.moxnasAPI.deleteNetworkInterface(interfaceId);
            this.interfaces = this.interfaces.filter(i => i.id !== interfaceId);
            this.renderInterfaces();
            this.showNetworkSuccess('Interface deleted successfully');
        } catch (error) {
            console.error('Error deleting interface:', error);
            this.showNetworkError('Failed to delete interface');
        }
    }

    /**
     * Get mock interfaces for development
     */
    getMockInterfaces() {
        return [
            {
                id: 1,
                name: 'eth0',
                type: 'ethernet',
                status: 'up',
                ip_address: '192.168.1.100',
                netmask: '255.255.255.0',
                gateway: '192.168.1.1',
                speed: '1000 Mbps',
                dhcp_enabled: false,
                enabled: true,
                mtu: 1500
            },
            {
                id: 2,
                name: 'wlan0',
                type: 'wireless',
                status: 'down',
                ip_address: null,
                dhcp_enabled: true,
                enabled: false,
                mtu: 1500
            }
        ];
    }

    /**
     * Get mock services for development
     */
    getMockServices() {
        return [
            { name: 'smb', status: 'running', enabled: true },
            { name: 'nfs', status: 'stopped', enabled: false },
            { name: 'ssh', status: 'running', enabled: true },
            { name: 'ftp', status: 'stopped', enabled: false }
        ];
    }

    /**
     * Show network success message
     */
    showNetworkSuccess(message) {
        if (window.moxnas && window.moxnas.showAlert) {
            window.moxnas.showAlert('success', message);
        } else {
            console.log('SUCCESS:', message);
        }
    }

    /**
     * Show network error message
     */
    showNetworkError(message) {
        if (window.moxnas && window.moxnas.showAlert) {
            window.moxnas.showAlert('error', message);
        } else {
            console.error('ERROR:', message);
        }
    }
}

// Create global instance
window.networkComponents = new NetworkComponents();
