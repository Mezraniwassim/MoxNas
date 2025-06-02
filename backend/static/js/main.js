// MoxNAS - TrueNAS-style JavaScript functionality

class MoxNAS {
    constructor() {
        this.sidebar = document.querySelector('.sidebar');
        this.mainContent = document.querySelector('.main-content');
        this.sidebarToggle = document.querySelector('.sidebar-toggle');
        this.isSidebarCollapsed = false;
        
        // Task management
        this.tasks = new Map();
        this.taskCounter = 0;
        
        // Alert system
        this.alerts = [];
        this.alertCounter = 0;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupDropdowns();
        this.updateSystemStatus();
        this.startSystemMonitoring();
        this.setupNavigation();
        this.initializeTaskManager();
        this.initializeAlertSystem();
        this.loadSavedPreferences();
        this.setupDashboardInteractions();
        this.initializeThemeManager();
        this.setupFieldAutocomplete();
    }

    setupEventListeners() {
        // Sidebar toggle
        if (this.sidebarToggle) {
            this.sidebarToggle.addEventListener('click', () => this.toggleSidebar());
        }

        // Navigation highlighting
        this.setupNavHighlighting();

        // Modal handlers
        this.setupModals();

        // Table interactions
        this.setupTables();

        // Form enhancements
        this.setupForms();

        // Keyboard shortcuts
        this.setupKeyboardShortcuts();
    }

    setupDropdowns() {
        const dropdowns = document.querySelectorAll('.dropdown');
        
        dropdowns.forEach(dropdown => {
            const trigger = dropdown.querySelector('.nav-item-btn');
            const content = dropdown.querySelector('.dropdown-content');
            
            if (trigger && content) {
                // Toggle dropdown on click
                trigger.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.toggleDropdown(dropdown);
                });
                
                // Close dropdown when clicking outside
                document.addEventListener('click', (e) => {
                    if (!dropdown.contains(e.target)) {
                        this.closeDropdown(dropdown);
                    }
                });
                
                // Keep dropdown open when clicking inside content
                content.addEventListener('click', (e) => {
                    e.stopPropagation();
                });
            }
        });
    }

    toggleDropdown(dropdown) {
        const isActive = dropdown.classList.contains('active');
        
        // Close all other dropdowns
        document.querySelectorAll('.dropdown.active').forEach(d => {
            if (d !== dropdown) {
                this.closeDropdown(d);
            }
        });
        
        // Toggle current dropdown
        if (isActive) {
            this.closeDropdown(dropdown);
        } else {
            dropdown.classList.add('active');
        }
    }

    closeDropdown(dropdown) {
        dropdown.classList.remove('active');
    }

    // Task Manager Functions
    initializeTaskManager() {
        this.updateTaskCounter();
        this.renderTaskList();
        // Start periodic task updates
        this.fetchTasksFromAPI();
        setInterval(() => this.fetchTasksFromAPI(), 30000); // Update every 30 seconds
    }

    addTask(title, description, type = 'system') {
        const taskId = `task_${++this.taskCounter}`;
        const task = {
            id: taskId,
            title,
            description,
            type,
            status: 'running',
            progress: 0,
            startTime: new Date(),
            endTime: null
        };
        
        this.tasks.set(taskId, task);
        this.updateTaskCounter();
        this.renderTaskList();
        
        return taskId;
    }

    updateTaskProgress(taskId, progress, status = null) {
        const task = this.tasks.get(taskId);
        if (task) {
            task.progress = Math.min(100, Math.max(0, progress));
            if (status) {
                task.status = status;
                if (status === 'completed' || status === 'failed') {
                    task.endTime = new Date();
                }
            }
            this.renderTaskList();
        }
    }

    removeTask(taskId) {
        this.tasks.delete(taskId);
        this.updateTaskCounter();
        this.renderTaskList();
    }

    clearAllTasks() {
        this.tasks.clear();
        this.updateTaskCounter();
        this.renderTaskList();
        this.showToast('All tasks cleared', 'info');
    }

    updateTaskCounter() {
        const runningTasks = Array.from(this.tasks.values()).filter(t => t.status === 'running').length;
        const counter = document.getElementById('task-counter');
        if (counter) {
            counter.textContent = runningTasks;
            counter.style.display = runningTasks > 0 ? 'flex' : 'none';
        }
    }

    renderTaskList() {
        const taskList = document.getElementById('task-list');
        if (!taskList) return;

        const taskArray = Array.from(this.tasks.values()).sort((a, b) => b.startTime - a.startTime);
        
        if (taskArray.length === 0) {
            taskList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-check-circle"></i>
                    <p>No active tasks</p>
                </div>
            `;
            return;
        }

        taskList.innerHTML = taskArray.map(task => `
            <div class="task-item">
                <div class="task-header">
                    <div class="task-title">${task.title}</div>
                    <div class="task-status ${task.status}">${task.status.toUpperCase()}</div>
                </div>
                <div class="task-description">${task.description}</div>
                ${task.status === 'running' ? `
                    <div class="task-progress">
                        <div class="task-progress-fill" style="width: ${task.progress}%"></div>
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    async fetchTasksFromAPI() {
        try {
            const response = await fetch('/web_interface/api/tasks/');
            if (!response.ok) throw new Error('Failed to fetch tasks');
            const data = await response.json();
            
            // Update tasks from API
            this.tasks.clear();
            if (data.tasks) {
                data.tasks.forEach(task => {
                    this.tasks.set(task.id, {
                        id: task.id,
                        title: task.title,
                        description: task.description,
                        status: task.status,
                        progress: task.progress,
                        startTime: new Date(task.started),
                        endTime: task.completed ? new Date(task.completed) : null,
                        estimatedCompletion: task.estimated_completion ? new Date(task.estimated_completion) : null
                    });
                });
            }
            
            this.updateTaskCounter();
            this.renderTaskList();
        } catch (error) {
            console.error('Error fetching tasks:', error);
            // Keep existing tasks if API fails
        }
    }

    // Alert System Functions
    initializeAlertSystem() {
        this.renderAlertList();
        this.updateAlertBadge();
        // Start periodic alert updates
        this.fetchAlertsFromAPI();
        setInterval(() => this.fetchAlertsFromAPI(), 30000); // Update every 30 seconds
    }

    addAlert(title, message, level = 'info', source = 'System') {
        const alertId = `alert_${++this.alertCounter}`;
        const alert = {
            id: alertId,
            title,
            message,
            level,
            source,
            timestamp: new Date(),
            read: false
        };
        
        this.alerts.unshift(alert);
        this.updateAlertBadge();
        this.renderAlertList();
        
        return alertId;
    }

    dismissAlert(alertElement) {
        const alertItem = alertElement.closest('.alert-item');
        if (alertItem) {
            alertItem.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => {
                alertItem.remove();
                // Update alerts array if needed
                this.updateAlertBadge();
            }, 300);
        }
    }

    markAllRead() {
        this.alerts.forEach(alert => alert.read = true);
        this.updateAlertBadge();
        this.renderAlertList();
    }

    updateAlertBadge() {
        const unreadCount = this.alerts.filter(a => !a.read).length;
        const badge = document.querySelector('.alert-badge');
        if (badge) {
            if (unreadCount > 0) {
                badge.textContent = unreadCount;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    updateAlertCounter() {
        const unreadCount = this.alerts.filter(a => !a.read).length;
        const badge = document.querySelector('.alert-badge');
        if (badge) {
            if (unreadCount > 0) {
                badge.textContent = unreadCount;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }
    }

    renderAlertList() {
        const alertList = document.getElementById('alert-list');
        if (!alertList) return;

        if (this.alerts.length === 0) {
            alertList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-check-shield"></i>
                    <p>No alerts</p>
                </div>
            `;
            return;
        }

        alertList.innerHTML = this.alerts.slice(0, 10).map(alert => `
            <div class="alert-item ${alert.level}">
                <div class="alert-icon">
                    <i class="fas fa-${this.getAlertIcon(alert.level)}"></i>
                </div>
                <div class="alert-content">
                    <div class="alert-title">${alert.title}</div>
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-time">${this.formatTimeAgo(alert.timestamp)}</div>
                </div>
                <button class="alert-dismiss" onclick="window.moxnas.dismissAlert(this)">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
    }

    async fetchAlertsFromAPI() {
        try {
            const response = await fetch('/web_interface/api/system/');
            if (!response.ok) throw new Error('Failed to fetch alerts');
            const data = await response.json();
            
            if (data.alerts && Array.isArray(data.alerts)) {
                // Clear existing alerts and add new ones from API
                this.alerts = [];
                data.alerts.forEach(alert => {
                    this.alerts.push({
                        id: alert.id,
                        title: alert.title,
                        message: alert.message,
                        level: alert.level,
                        timestamp: new Date(alert.timestamp),
                        source: alert.source
                    });
                });
                
                this.updateAlertBadge();
                this.renderAlertList();
            }
        } catch (error) {
            console.error('Error fetching alerts:', error);
            // Keep existing alerts if API fails
        }
    }

    async controlService(serviceName, action) {
        try {
            const response = await fetch('/web_interface/api/services/control/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    service: serviceName,
                    action: action
                })
            });
            
            if (!response.ok) throw new Error('Failed to control service');
            const data = await response.json();
            
            if (data.success) {
                this.showToast(`Service ${serviceName} ${action} successful`, 'success');
                // Refresh service status
                setTimeout(() => this.updateServiceStatus(), 1000);
            } else {
                this.showToast(`Service ${serviceName} ${action} failed`, 'error');
            }
            
            return data;
        } catch (error) {
            console.error('Error controlling service:', error);
            this.showToast(`Error controlling service: ${error.message}`, 'error');
            return { success: false, error: error.message };
        }
    }

    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }

    // System Functions
    loadSavedPreferences() {
        const collapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (collapsed !== this.isSidebarCollapsed) {
            this.toggleSidebar();
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + B: Toggle sidebar
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                e.preventDefault();
                this.toggleSidebar();
            }
            
            // Escape: Close all dropdowns
            if (e.key === 'Escape') {
                document.querySelectorAll('.dropdown.active').forEach(dropdown => {
                    this.closeDropdown(dropdown);
                });
            }
        });
    }

    toggleSidebar() {
        this.isSidebarCollapsed = !this.isSidebarCollapsed;
        
        if (this.sidebar) {
            this.sidebar.classList.toggle('collapsed', this.isSidebarCollapsed);
        }
        
        if (this.mainContent) {
            this.mainContent.classList.toggle('sidebar-collapsed', this.isSidebarCollapsed);
        }

        // Store preference
        localStorage.setItem('sidebarCollapsed', this.isSidebarCollapsed);
    }

    setupNavHighlighting() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.nav-menu-link');
        
        navLinks.forEach(link => {
            if (link.getAttribute('href') === currentPath) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    setupNavigation() {
        // Load saved sidebar state
        const savedState = localStorage.getItem('sidebarCollapsed');
        if (savedState === 'true') {
            this.toggleSidebar();
        }

        // Handle mobile navigation
        this.setupMobileNav();
    }

    setupMobileNav() {
        if (window.innerWidth <= 768) {
            this.isSidebarCollapsed = true;
            if (this.sidebar) {
                this.sidebar.classList.add('collapsed');
            }
            if (this.mainContent) {
                this.mainContent.classList.add('sidebar-collapsed');
            }
        }

        window.addEventListener('resize', () => {
            if (window.innerWidth <= 768 && !this.isSidebarCollapsed) {
                this.toggleSidebar();
            }
        });
    }

    // Enhanced System Monitoring
    updateSystemStatus() {
        this.updateSystemMetrics();
        this.updateStorageInfo();
        this.updateNetworkInfo();
        this.updateServiceStatus();
        this.updateSystemUptime();
    }

    updateSystemMetrics() {
        // Simulate real-time CPU and memory updates
        this.fetchSystemMetrics().then(data => {
            this.updateCPUUsage(data.cpu);
            this.updateMemoryUsage(data.memory);
            this.updateLoadAverage(data.load);
            this.updateTemperature(data.temperature);
        }).catch(error => {
            console.warn('Failed to fetch system metrics:', error);
            // Use simulated data for demo
            this.updateCPUUsage(Math.floor(Math.random() * 30) + 10);
            this.updateMemoryUsage(Math.floor(Math.random() * 40) + 50);
        });
    }

    async fetchSystemMetrics() {
        try {
            // Try to fetch real-time metrics
            const realtimeResponse = await fetch('/web_interface/api/realtime/');
            if (!realtimeResponse.ok) throw new Error('Failed to fetch metrics');
            const realtimeData = await realtimeResponse.json();
            
            // Try to fetch system info for temperature data
            let temperature = null;
            try {
                const systemResponse = await fetch('/web_interface/api/system/');
                if (systemResponse.ok) {
                    const systemData = await systemResponse.json();
                    temperature = systemData.system_info.temperature;
                }
            } catch (tempError) {
                console.warn('Could not fetch temperature data:', tempError);
            }
            
            return {
                cpu: realtimeData.cpu_usage || 0,
                memory: realtimeData.memory_usage || 0,
                load: realtimeData.load_average || [0, 0, 0],
                temperature: temperature
            };
        } catch (error) {
            console.warn('API unavailable, using simulated data:', error);
            // Fallback to simulated data
            return {
                cpu: Math.floor(Math.random() * 30) + 10,
                memory: Math.floor(Math.random() * 40) + 50,
                load: [0.15 + Math.random() * 0.5, 0.18 + Math.random() * 0.3, 0.22 + Math.random() * 0.2],
                temperature: 35 + Math.random() * 15
            };
        }
    }

    updateCPUUsage(usage) {
        const cpuUsageEl = document.getElementById('cpu-usage');
        const cpuProgressEl = document.getElementById('cpu-progress');
        
        if (cpuUsageEl && cpuProgressEl) {
            cpuUsageEl.textContent = `${usage}%`;
            cpuProgressEl.style.width = `${usage}%`;
            
            // Update progress text
            const progressText = cpuProgressEl.querySelector('.progress-text');
            if (progressText) {
                progressText.textContent = `${usage}%`;
            }
            
            // Add color based on usage
            cpuProgressEl.className = 'progress-fill cpu-progress';
            if (usage > 80) cpuProgressEl.classList.add('high');
            else if (usage > 60) cpuProgressEl.classList.add('medium');
        }
    }

    updateMemoryUsage(usage) {
        const memUsageEl = document.getElementById('memory-usage');
        const memProgressEl = document.getElementById('memory-progress');
        
        if (memUsageEl && memProgressEl) {
            memUsageEl.textContent = `${usage}%`;
            memProgressEl.style.width = `${usage}%`;
            
            // Update progress text
            const progressText = memProgressEl.querySelector('.progress-text');
            if (progressText) {
                progressText.textContent = `${usage}%`;
            }
            
            // Add color based on usage
            memProgressEl.className = 'progress-fill memory-progress';
            if (usage > 85) memProgressEl.classList.add('high');
            else if (usage > 70) memProgressEl.classList.add('medium');
        }
    }

    updateLoadAverage(loadArray) {
        const loadEl = document.getElementById('load-average');
        if (loadEl && Array.isArray(loadArray)) {
            loadEl.textContent = loadArray.map(l => l.toFixed(2)).join(', ');
        }
    }

    updateTemperature(temp) {
        const tempEl = document.getElementById('system-temp');
        const cpuTempEl = document.getElementById('cpu-temp');
        
        if (tempEl) {
            tempEl.textContent = `${Math.round(temp)}°C`;
            tempEl.className = temp > 70 ? 'high-temp' : temp > 50 ? 'medium-temp' : '';
        }
        
        if (cpuTempEl) {
            cpuTempEl.textContent = `${Math.round(temp + 5)}°C`;
        }
    }

    updateSystemUptime() {
        // Update uptime display
        this.fetchUptime().then(uptime => {
            const uptimeEl = document.getElementById('system-uptime');
            if (uptimeEl) {
                uptimeEl.textContent = this.formatUptime(uptime);
            }
        });
    }

    async fetchUptime() {
        try {
            const response = await fetch('/web_interface/api/system/');
            if (!response.ok) throw new Error('Failed to fetch system data');
            const data = await response.json();
            return data.system_info.uptime_seconds * 1000; // Convert to milliseconds
        } catch (error) {
            console.warn('API unavailable for uptime, using fallback');
            // Fallback to current session time
            return Date.now() - this.startTime;
        }
    }

    formatUptime(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) return `${days}d ${hours}h ${minutes}m`;
        if (hours > 0) return `${hours}h ${minutes}m`;
        return `${minutes}m`;
    }

    updateStorageInfo() {
        this.fetchStorageData().then(pools => {
            pools.forEach(pool => {
                this.updatePoolUsage(pool.name, pool.usage_percent, pool.used, pool.total);
            });
        });
    }

    async fetchStorageData() {
        try {
            const response = await fetch('/web_interface/api/system/');
            if (!response.ok) throw new Error('Failed to fetch storage data');
            const data = await response.json();
            return data.storage_pools.map(pool => ({
                name: pool.name,
                usage_percent: pool.percent,
                used: `${pool.used} GB`,
                total: `${pool.total} GB`
            }));
        } catch (error) {
            console.warn('API unavailable for storage, using simulated data');
            // Return simulated data
            return [
                { name: 'tank', usage_percent: 45 + Math.random() * 10, used: '2.1 TB', total: '4.7 TB' },
                { name: 'backup', usage_percent: 23 + Math.random() * 5, used: '460 GB', total: '2.0 TB' }
            ];
        }
    }

    updatePoolUsage(poolName, usagePercent, used, total) {
        const poolEl = document.querySelector(`[data-pool="${poolName}"]`);
        if (poolEl) {
            const usageFill = poolEl.querySelector('.usage-fill');
            const usageText = poolEl.querySelector('.usage-text');
            
            if (usageFill) {
                usageFill.style.width = `${usagePercent}%`;
            }
            
            if (usageText) {
                usageText.textContent = `${used} / ${total} (${Math.round(usagePercent)}%)`;
            }
        }
    }

    updateNetworkInfo() {
        this.fetchNetworkData().then(interfaces => {
            interfaces.forEach(iface => {
                this.updateInterfaceStats(iface.name, iface.rx_bytes, iface.tx_bytes, iface.errors);
            });
        });
    }

    async fetchNetworkData() {
        try {
            const response = await fetch('/web_interface/api/system/');
            if (!response.ok) throw new Error('Failed to fetch network data');
            const data = await response.json();
            return data.network_interfaces.map(iface => ({
                name: iface.name,
                rx_bytes: this.formatBytes(iface.statistics.bytes_recv),
                tx_bytes: this.formatBytes(iface.statistics.bytes_sent),
                errors: iface.statistics.errors_in + iface.statistics.errors_out
            }));
        } catch (error) {
            console.warn('API unavailable for network, using simulated data');
            // Return simulated data
            return [
                { 
                    name: 'eth0', 
                    rx_bytes: this.formatBytes(Math.random() * 100000000000),
                    tx_bytes: this.formatBytes(Math.random() * 50000000000),
                    errors: Math.floor(Math.random() * 5)
                }
            ];
        }
    }

    updateInterfaceStats(interfaceName, rxBytes, txBytes, errors) {
        const rxEl = document.getElementById(`rx-${interfaceName}`);
        const txEl = document.getElementById(`tx-${interfaceName}`);
        const errorsEl = document.getElementById(`errors-${interfaceName}`);
        
        if (rxEl) rxEl.textContent = rxBytes;
        if (txEl) txEl.textContent = txBytes;
        if (errorsEl) {
            errorsEl.textContent = errors;
            errorsEl.className = errors > 0 ? 'stat-value error' : 'stat-value';
        }
    }

    formatBytes(bytes) {
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        if (bytes === 0) return '0 B';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
    }

    updateServiceStatus() {
        this.fetchServiceData().then(services => {
            services.forEach(service => {
                this.updateServiceDisplay(service.name, service.status);
            });
        });
    }

    async fetchServiceData() {
        try {
            const response = await fetch('/web_interface/api/system/');
            if (!response.ok) throw new Error('Failed to fetch service data');
            const data = await response.json();
            return data.services || [];
        } catch (error) {
            console.error('Error fetching service data:', error);
            // Return default service states
            return [
                { name: 'smb', status: 'RUNNING', description: 'SMB/CIFS File Sharing' },
                { name: 'nfs', status: 'RUNNING', description: 'Network File System' },
                { name: 'ssh', status: 'RUNNING', description: 'Secure Shell' },
                { name: 'ftp', status: 'STOPPED', description: 'File Transfer Protocol' }
            ];
        }
    }

    updateServiceDisplay(serviceName, status) {
        const serviceEl = document.querySelector(`[data-service="${serviceName}"]`);
        if (serviceEl) {
            const statusEl = serviceEl.querySelector('.service-status .status');
            const actionBtn = serviceEl.querySelector('.service-action i');
            
            if (statusEl) {
                statusEl.className = `status ${status.toLowerCase()}`;
                statusEl.textContent = status;
            }
            
            if (actionBtn) {
                actionBtn.className = status === 'RUNNING' ? 'fas fa-stop' : 'fas fa-play';
            }
        }
    }

    startSystemMonitoring() {
        // Set monitoring intervals
        this.startTime = Date.now();
        
        // Update system metrics every 10 seconds
        setInterval(() => this.updateSystemMetrics(), 10000);
        
        // Update storage info every 30 seconds
        setInterval(() => this.updateStorageInfo(), 30000);
        
        // Update network stats every 15 seconds
        setInterval(() => this.updateNetworkInfo(), 15000);
        
        // Update service status every 60 seconds
        setInterval(() => this.updateServiceStatus(), 60000);
        
        // Update uptime every 60 seconds
        setInterval(() => this.updateSystemUptime(), 60000);
        
        // Check system health every 30 seconds
        setInterval(() => this.checkSystemHealth(), 30000);
        
        // Add random alerts for demo
        setTimeout(() => this.initializeDemoAlerts(), 5000);
        
        // Perform initial health check
        setTimeout(() => this.checkSystemHealth(), 2000);
        
        // Show real-time monitoring indicator
        this.showRealtimeIndicator();
    }
    
    showRealtimeIndicator() {
        // Create real-time update indicator if it doesn't exist
        let indicator = document.getElementById('realtime-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'realtime-indicator';
            indicator.className = 'update-indicator';
            indicator.innerHTML = `
                <div class="update-pulse"></div>
                <span>Real-time monitoring active</span>
            `;
            document.body.appendChild(indicator);
            
            // Make it draggable for better user experience
            this.makeElementDraggable(indicator);
        }
        
        // Show it as active
        indicator.classList.add('active');
    }
    
    makeElementDraggable(element) {
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
        
        element.addEventListener('mousedown', dragMouseDown);
        
        function dragMouseDown(e) {
            e.preventDefault();
            // Get mouse position at startup
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.addEventListener('mouseup', closeDragElement);
            document.addEventListener('mousemove', elementDrag);
        }
        
        function elementDrag(e) {
            e.preventDefault();
            // Calculate new position
            pos1 = pos3 - e.clientX;
            pos2 = pos4 - e.clientY;
            pos3 = e.clientX;
            pos4 = e.clientY;
            // Set element's new position
            element.style.top = (element.offsetTop - pos2) + "px";
            element.style.left = (element.offsetLeft - pos1) + "px";
            element.style.bottom = "auto";
            element.style.right = "auto";
        }
        
        function closeDragElement() {
            // Stop moving when mouse button is released
            document.removeEventListener('mouseup', closeDragElement);
            document.removeEventListener('mousemove', elementDrag);
        }
    }

    initializeDemoAlerts() {
        // Add some demo alerts
        this.addAlert(
            'Storage Warning',
            'Pool "tank" is 85% full. Consider adding more storage.',
            'warning',
            'Storage Manager'
        );
        
        setTimeout(() => {
            this.addAlert(
                'Backup Complete',
                'Scheduled backup completed successfully.',
                'success',
                'Backup Service'
            );
        }, 3000);
        
        setTimeout(() => {
            this.addAlert(
                'System Update',
                'New system update available: MoxNAS 1.0.1',
                'info',
                'Update Manager'
            );
        }, 7000);
    }

    // System health monitoring
    checkSystemHealth() {
        return this.fetchSystemMetrics().then(data => {
            let status = 'healthy';
            let issues = [];
            
            // Check CPU usage
            if (data.cpu > 90) {
                status = 'critical';
                issues.push('CPU usage critical (>' + data.cpu + '%)');
            } else if (data.cpu > 75) {
                status = status === 'critical' ? status : 'warning';
                issues.push('CPU usage high (' + data.cpu + '%)');
            }
            
            // Check memory usage
            if (data.memory > 90) {
                status = 'critical';
                issues.push('Memory usage critical (>' + data.memory + '%)');
            } else if (data.memory > 80) {
                status = status === 'critical' ? status : 'warning';
                issues.push('Memory usage high (' + data.memory + '%)');
            }
            
            // Check temperature
            if (data.temperature && data.temperature > 80) {
                status = 'critical';
                issues.push('CPU temperature critical (' + Math.round(data.temperature) + '°C)');
            } else if (data.temperature && data.temperature > 70) {
                status = status === 'critical' ? status : 'warning';
                issues.push('CPU temperature high (' + Math.round(data.temperature) + '°C)');
            }
            
            // Update system health indicator
            const healthIndicator = document.getElementById('system-health');
            if (healthIndicator) {
                healthIndicator.className = 'health-indicator ' + status;
                healthIndicator.setAttribute('title', issues.join(', ') || 'System healthy');
                
                // Show toast for critical issues
                if (status === 'critical' && issues.length > 0) {
                    this.showToast('System health critical: ' + issues.join(', '), 'error');
                }
            }
            
            return { status, issues };
        });
    }

    // Enhanced modal handling
    setupModals() {
        // Close modals on backdrop click
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-backdrop')) {
                this.closeModal(e.target.closest('.modal'));
            }
        });
        
        // Close modals on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const activeModal = document.querySelector('.modal.active');
                if (activeModal) {
                    this.closeModal(activeModal);
                }
            }
        });
    }

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.classList.add('modal-open');
        }
    }

    closeModal(modal) {
        if (modal) {
            modal.classList.remove('active');
            document.body.classList.remove('modal-open');
        }
    }

    // Confirmation system for important actions
    confirmAction(message, confirmCallback, cancelCallback = null) {
        // Create modal if it doesn't exist
        let confirmModal = document.getElementById('confirm-modal');
        if (!confirmModal) {
            confirmModal = document.createElement('div');
            confirmModal.id = 'confirm-modal';
            confirmModal.className = 'modal';
            confirmModal.innerHTML = `
                <div class="modal-backdrop"></div>
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Confirm Action</h3>
                        <button class="modal-close" id="confirm-close">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <p id="confirm-message"></p>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" id="confirm-cancel">Cancel</button>
                        <button class="btn btn-danger" id="confirm-ok">Confirm</button>
                    </div>
                </div>
            `;
            document.body.appendChild(confirmModal);
        }
        
        // Set message
        document.getElementById('confirm-message').textContent = message;
        
        // Show modal
        confirmModal.classList.add('active');
        document.body.classList.add('modal-open');
        
        // Setup handlers
        const handleConfirm = () => {
            confirmModal.classList.remove('active');
            document.body.classList.remove('modal-open');
            if (typeof confirmCallback === 'function') {
                confirmCallback();
            }
            cleanup();
        };
        
        const handleCancel = () => {
            confirmModal.classList.remove('active');
            document.body.classList.remove('modal-open');
            if (typeof cancelCallback === 'function') {
                cancelCallback();
            }
            cleanup();
        };
        
        const cleanup = () => {
            document.getElementById('confirm-ok').removeEventListener('click', handleConfirm);
            document.getElementById('confirm-cancel').removeEventListener('click', handleCancel);
            document.getElementById('confirm-close').removeEventListener('click', handleCancel);
        };
        
        // Add listeners
        document.getElementById('confirm-ok').addEventListener('click', handleConfirm);
        document.getElementById('confirm-cancel').addEventListener('click', handleCancel);
        document.getElementById('confirm-close').addEventListener('click', handleCancel);
    }

    // Enhanced table functionality
    setupTables() {
        // Add sorting functionality
        const sortableHeaders = document.querySelectorAll('th[data-sort]');
        sortableHeaders.forEach(header => {
            header.addEventListener('click', () => {
                const table = header.closest('table');
                const column = header.dataset.sort;
                this.sortTable(table, column);
            });
        });
        
        // Add row selection
        const selectableRows = document.querySelectorAll('tr[data-selectable]');
        selectableRows.forEach(row => {
            row.addEventListener('click', () => {
                row.classList.toggle('selected');
            });
        });
    }

    sortTable(table, column) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const columnIndex = Array.from(table.querySelectorAll('th')).findIndex(th => th.dataset.sort === column);
        
        if (columnIndex === -1) return;
        
        const isNumeric = table.dataset.sortType === 'numeric';
        const isDescending = table.dataset.sortDirection === 'desc';
        
        rows.sort((a, b) => {
            const aVal = a.cells[columnIndex].textContent.trim();
            const bVal = b.cells[columnIndex].textContent.trim();
            
            if (isNumeric) {
                return isDescending ? 
                    parseFloat(bVal) - parseFloat(aVal) :
                    parseFloat(aVal) - parseFloat(bVal);
            } else {
                return isDescending ?
                    bVal.localeCompare(aVal) :
                    aVal.localeCompare(bVal);
            }
        });
        
        // Update table
        rows.forEach(row => tbody.appendChild(row));
        
        // Toggle sort direction
        table.dataset.sortDirection = isDescending ? 'asc' : 'desc';
    }

    // Enhanced form handling
    setupForms() {
        // Add form validation
        const forms = document.querySelectorAll('form[data-validate]');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!this.validateForm(form)) {
                    e.preventDefault();
                    this.showToast('Please correct the errors in the form', 'warning');
                }
            });
        });
        
        // Add real-time validation
        const inputs = document.querySelectorAll('input[data-validate], select[data-validate], textarea[data-validate]');
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this.validateField(input);
            });
            
            // Add real-time validation for password fields and their confirmation
            if (input.type === 'password' && input.dataset.confirm) {
                input.addEventListener('input', () => {
                    const confirmField = document.getElementById(input.dataset.confirm);
                    if (confirmField && confirmField.value) {
                        this.validateField(confirmField);
                    }
                });
            }
        });
        
        // Add dynamic form field handling
        this.setupDynamicFormFields();
        
        // Add masked input support
        this.setupMaskedInputs();
    }

    validateForm(form) {
        const fields = form.querySelectorAll('[data-validate]');
        let isValid = true;
        
        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        return isValid;
    }

    validateField(field) {
        const rules = field.dataset.validate.split(',');
        let isValid = true;
        let errorMessage = '';
        
        for (const rule of rules) {
            const ruleParts = rule.trim().split(':');
            const ruleName = ruleParts[0];
            const ruleValue = ruleParts.length > 1 ? ruleParts[1] : null;
            
            switch (ruleName) {
                case 'required':
                    if (!field.value.trim()) {
                        isValid = false;
                        errorMessage = 'This field is required';
                    }
                    break;
                case 'email':
                    if (field.value && !this.isValidEmail(field.value)) {
                        isValid = false;
                        errorMessage = 'Please enter a valid email address';
                    }
                    break;
                case 'min-length':
                    if (field.value && field.value.length < parseInt(ruleValue, 10)) {
                        isValid = false;
                        errorMessage = `Minimum ${ruleValue} characters required`;
                    }
                    break;
                case 'max-length':
                    if (field.value && field.value.length > parseInt(ruleValue, 10)) {
                        isValid = false;
                        errorMessage = `Maximum ${ruleValue} characters allowed`;
                    }
                    break;
                case 'pattern':
                    if (field.value && !this.validatePattern(field.value, ruleValue)) {
                        isValid = false;
                        errorMessage = field.dataset.patternMessage || 'Invalid format';
                    }
                    break;
                case 'match':
                    const matchField = document.getElementById(ruleValue);
                    if (matchField && field.value !== matchField.value) {
                        isValid = false;
                        errorMessage = field.dataset.matchMessage || 'Fields do not match';
                    }
                    break;
                case 'ip':
                    if (field.value && !this.isValidIP(field.value)) {
                        isValid = false;
                        errorMessage = 'Please enter a valid IP address';
                    }
                    break;
                case 'hostname':
                    if (field.value && !this.isValidHostname(field.value)) {
                        isValid = false;
                        errorMessage = 'Please enter a valid hostname';
                    }
                    break;
                case 'numeric':
                    if (field.value && !/^-?\d+(\.\d+)?$/.test(field.value)) {
                        isValid = false;
                        errorMessage = 'Please enter a valid number';
                    }
                    break;
                case 'integer':
                    if (field.value && !/^-?\d+$/.test(field.value)) {
                        isValid = false;
                        errorMessage = 'Please enter a valid integer';
                    }
                    break;
                case 'port':
                    const port = parseInt(field.value, 10);
                    if (field.value && (isNaN(port) || port < 1 || port > 65535)) {
                        isValid = false;
                        errorMessage = 'Please enter a valid port (1-65535)';
                    }
                    break;
            }
            
            if (!isValid) break;
        }
        
        this.showFieldValidation(field, isValid, errorMessage);
        return isValid;
    }

    isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }
    
    isValidIP(ip) {
        // IPv4 validation
        const ipv4Pattern = /^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        return ipv4Pattern.test(ip);
    }
    
    isValidHostname(hostname) {
        // Hostname validation (based on RFC 1123)
        const hostnamePattern = /^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$/;
        return hostnamePattern.test(hostname) && hostname.length <= 255;
    }
    
    validatePattern(value, patternName) {
        const patterns = {
            'alphanumeric': /^[a-zA-Z0-9]+$/,
            'password': /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$/,
            'username': /^[a-zA-Z0-9_]{3,20}$/,
            'decimal': /^\d+(\.\d{1,2})?$/,
            'date': /^\d{4}-\d{2}-\d{2}$/,
            'time': /^([01]\d|2[0-3]):([0-5]\d)$/,
            'mac': /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/
        };
        
        if (patterns[patternName]) {
            return patterns[patternName].test(value);
        }
        
        // If pattern is provided as a raw regex string
        try {
            const regex = new RegExp(patternName);
            return regex.test(value);
        } catch (e) {
            console.error('Invalid pattern:', patternName, e);
            return false;
        }
    }

    showFieldValidation(field, isValid, message) {
        const container = field.closest('.form-group') || field.parentElement;
        let errorEl = container.querySelector('.field-error');
        
        if (!errorEl) {
            errorEl = document.createElement('div');
            errorEl.className = 'field-error';
            container.appendChild(errorEl);
        }
        
        if (isValid) {
            field.classList.remove('error');
            field.classList.add('valid');
            errorEl.textContent = '';
            errorEl.style.display = 'none';
        } else {
            field.classList.add('error');
            field.classList.remove('valid');
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
    }
    
    setupDynamicFormFields() {
        // Handle repeatable field groups
        document.querySelectorAll('[data-repeatable]').forEach(container => {
            const addButton = container.querySelector('[data-add-item]');
            if (addButton) {
                addButton.addEventListener('click', () => {
                    this.addRepeatableItem(container);
                });
            }
            
            // Set up remove buttons for existing items
            container.querySelectorAll('[data-remove-item]').forEach(button => {
                button.addEventListener('click', () => {
                    this.removeRepeatableItem(button.closest('[data-repeatable-item]'));
                });
            });
        });
        
        // Handle conditional fields
        document.querySelectorAll('[data-condition-field]').forEach(field => {
            const targetFieldId = field.dataset.conditionField;
            const targetField = document.getElementById(targetFieldId);
            
            if (targetField) {
                targetField.addEventListener('change', () => {
                    this.evaluateFieldCondition(field, targetField);
                });
                
                // Initial evaluation
                this.evaluateFieldCondition(field, targetField);
            }
        });
    }
    
    addRepeatableItem(container) {
        const template = container.querySelector('[data-repeatable-template]');
        if (!template) return;
        
        const newItem = document.createElement('div');
        newItem.innerHTML = template.innerHTML;
        newItem.classList.add('repeatable-item');
        newItem.setAttribute('data-repeatable-item', '');
        
        // Update IDs and names to make them unique
        const timestamp = Date.now();
        newItem.querySelectorAll('[id]').forEach(el => {
            const oldId = el.id;
            const newId = `${oldId}_${timestamp}`;
            el.id = newId;
            
            // Update labels
            newItem.querySelectorAll(`label[for="${oldId}"]`).forEach(label => {
                label.setAttribute('for', newId);
            });
        });
        
        // Add remove button functionality
        const removeButton = newItem.querySelector('[data-remove-item]');
        if (removeButton) {
            removeButton.addEventListener('click', () => {
                this.removeRepeatableItem(newItem);
            });
        }
        
        // Add new item to container
        const itemsContainer = container.querySelector('[data-repeatable-items]') || container;
        itemsContainer.appendChild(newItem);
        
        // Initialize validation on new fields
        newItem.querySelectorAll('[data-validate]').forEach(field => {
            field.addEventListener('blur', () => {
                this.validateField(field);
            });
        });
    }
    
    removeRepeatableItem(item) {
        if (item) {
            item.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => {
                item.remove();
            }, 300);
        }
    }
    
    evaluateFieldCondition(field, targetField) {
        const condition = field.dataset.condition || 'equals';
        const value = field.dataset.conditionValue;
        let shouldShow = false;
        
        switch (condition) {
            case 'equals':
                shouldShow = targetField.value === value;
                break;
            case 'not-equals':
                shouldShow = targetField.value !== value;
                break;
            case 'contains':
                shouldShow = targetField.value.includes(value);
                break;
            case 'checked':
                shouldShow = targetField.checked;
                break;
            case 'not-checked':
                shouldShow = !targetField.checked;
                break;
            case 'not-empty':
                shouldShow = targetField.value.trim() !== '';
                break;
            case 'empty':
                shouldShow = targetField.value.trim() === '';
                break;
        }
        
        const container = field.closest('.form-group') || field;
        if (shouldShow) {
            container.style.display = '';
            field.disabled = false;
        } else {
            container.style.display = 'none';
            field.disabled = true;
        }
    }
    
    setupMaskedInputs() {
        document.querySelectorAll('[data-mask]').forEach(input => {
            const maskType = input.dataset.mask;
            
            input.addEventListener('input', (e) => {
                const cursorPosition = e.target.selectionStart;
                const oldValue = e.target.value;
                let newValue = oldValue;
                
                switch (maskType) {
                    case 'ip':
                        newValue = this.formatIPAddress(oldValue);
                        break;
                    case 'mac':
                        newValue = this.formatMACAddress(oldValue);
                        break;
                    case 'date':
                        newValue = this.formatDate(oldValue);
                        break;
                    case 'time':
                        newValue = this.formatTime(oldValue);
                        break;
                    case 'phone':
                        newValue = this.formatPhone(oldValue);
                        break;
                    case 'currency':
                        newValue = this.formatCurrency(oldValue);
                        break;
                }
                
                if (newValue !== oldValue) {
                    e.target.value = newValue;
                    
                    // Try to maintain cursor position after formatting
                    if (cursorPosition <= newValue.length) {
                        e.target.setSelectionRange(cursorPosition, cursorPosition);
                    }
                }
            });
        });
    }
    
    formatIPAddress(value) {
        // Only allow digits and dots
        value = value.replace(/[^\d.]/g, '');
        
        // Ensure no more than 3 digits per octet
        const octets = value.split('.');
        return octets.map(octet => {
            if (octet.length > 3) {
                return octet.slice(0, 3);
            }
            return octet;
        }).join('.');
    }
    
    formatMACAddress(value) {
        // Remove non-hex characters
        value = value.replace(/[^0-9a-fA-F]/g, '');
        
        // Format with colons XX:XX:XX:XX:XX:XX
        let formatted = '';
        for (let i = 0; i < value.length && i < 12; i++) {
            if (i > 0 && i % 2 === 0) {
                formatted += ':';
            }
            formatted += value[i];
        }
        
        return formatted;
    }
    
    formatDate(value) {
        // Remove non-digits
        value = value.replace(/\D/g, '');
        
        // Format as YYYY-MM-DD
        if (value.length > 0) {
            let formatted = '';
            if (value.length > 4) {
                formatted = value.slice(0, 4) + '-' + value.slice(4);
            } else {
                formatted = value;
            }
            
            if (value.length > 6) {
                formatted = formatted.slice(0, 7) + '-' + value.slice(6, 8);
            }
            
            return formatted.slice(0, 10); // Limit to 10 characters
        }
        
        return value;
    }
    
    formatTime(value) {
        // Remove non-digits
        value = value.replace(/\D/g, '');
        
        // Format as HH:MM
        if (value.length > 0) {
            if (value.length > 2) {
                return value.slice(0, 2) + ':' + value.slice(2, 4);
            }
        }
        
        return value;
    }
    
    formatPhone(value) {
        // Remove non-digits
        value = value.replace(/\D/g, '');
        
        // Format as (XXX) XXX-XXXX
        if (value.length > 0) {
            let formatted = '';
            if (value.length > 3) {
                formatted = '(' + value.slice(0, 3) + ') ' + value.slice(3);
            } else {
                formatted = '(' + value;
            }
            
            if (value.length > 6) {
                formatted = formatted.slice(0, 9) + '-' + value.slice(6);
            }
            
            return formatted;
        }
        
        return value;
    }
    
    formatCurrency(value) {
        // Remove non-digits and non-decimal points
        value = value.replace(/[^\d.]/g, '');
        
        // Ensure only one decimal point
        const parts = value.split('.');
        if (parts.length > 2) {
            value = parts[0] + '.' + parts.slice(1).join('');
        }
        
        // Limit to 2 decimal places
        if (parts.length > 1 && parts[1].length > 2) {
            value = parts[0] + '.' + parts[1].slice(0, 2);
        }
        
        return value;
    }

    // Form submission handler with API integration
    async submitFormToAPI(form, endpoint, method = 'POST', options = {}) {
        // Default options
        const defaults = {
            showLoading: true,
            loadingMessage: 'Processing...',
            successMessage: 'Form submitted successfully',
            errorMessage: 'Error submitting form',
            redirectUrl: null,
            onSuccess: null,
            onError: null
        };
        
        // Merge options
        const settings = { ...defaults, ...options };
        
        // Validate form if data-validate attribute is present
        if (form.hasAttribute('data-validate') && !this.validateForm(form)) {
            this.showToast('Please correct the errors in the form', 'warning');
            return false;
        }
        
        // Show loading state
        if (settings.showLoading) {
            this.showFormLoading(form, settings.loadingMessage);
        }
        
        // Get form data
        const formData = new FormData(form);
        const jsonData = {};
        
        // Convert FormData to JSON object if not multipart/form-data
        if (!form.enctype || form.enctype !== 'multipart/form-data') {
            formData.forEach((value, key) => {
                // Handle array fields (fields with name attribute like name[])
                if (key.endsWith('[]')) {
                    const baseKey = key.slice(0, -2);
                    if (!jsonData[baseKey]) {
                        jsonData[baseKey] = [];
                    }
                    jsonData[baseKey].push(value);
                } else {
                    jsonData[key] = value;
                }
            });
        }
        
        try {
            // Make API call
            const response = await fetch(endpoint, {
                method: method.toUpperCase(),
                headers: {
                    'Content-Type': form.enctype === 'multipart/form-data' ? undefined : 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: form.enctype === 'multipart/form-data' ? formData : JSON.stringify(jsonData)
            });
            
            // Hide loading state
            if (settings.showLoading) {
                this.hideFormLoading(form);
            }
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || errorData.error || `Error ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json().catch(() => ({}));
            
            // Show success message
            this.showToast(data.message || settings.successMessage, 'success');
            
            // Clear form if needed
            if (form.hasAttribute('data-reset-on-success')) {
                form.reset();
                
                // Clear validation styling
                form.querySelectorAll('.error, .valid').forEach(field => {
                    field.classList.remove('error', 'valid');
                });
                
                form.querySelectorAll('.field-error').forEach(error => {
                    error.style.display = 'none';
                    error.textContent = '';
                });
            }
            
            // Call onSuccess callback if provided
            if (typeof settings.onSuccess === 'function') {
                settings.onSuccess(data);
            }
            
            // Redirect if needed
            if (settings.redirectUrl) {
                window.location.href = settings.redirectUrl;
            }
            
            return data;
        } catch (error) {
            // Hide loading state
            if (settings.showLoading) {
                this.hideFormLoading(form);
            }
            
            console.error('Form submission error:', error);
            
            // Show error message
            this.showToast(error.message || settings.errorMessage, 'error');
            
            // Call onError callback if provided
            if (typeof settings.onError === 'function') {
                settings.onError(error);
            }
            
            return false;
        }
    }
    
    showFormLoading(form, message = 'Processing...') {
        // Disable all form inputs
        form.querySelectorAll('input, select, textarea, button').forEach(el => {
            el.disabled = true;
            if (el.tagName.toLowerCase() === 'button') {
                el.setAttribute('data-original-text', el.innerHTML);
                el.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + message;
            }
        });
        
        // Add loading overlay
        const overlay = document.createElement('div');
        overlay.className = 'form-loading-overlay';
        overlay.innerHTML = `
            <div class="spinner-container">
                <div class="spinner"></div>
                <p>${message}</p>
            </div>
        `;
        
        form.appendChild(overlay);
        form.classList.add('loading');
    }
    
    hideFormLoading(form) {
        // Remove overlay
        const overlay = form.querySelector('.form-loading-overlay');
        if (overlay) {
            overlay.remove();
        }
        
        // Re-enable inputs
        form.querySelectorAll('input, select, textarea, button').forEach(el => {
            el.disabled = false;
            if (el.tagName.toLowerCase() === 'button' && el.hasAttribute('data-original-text')) {
                el.innerHTML = el.getAttribute('data-original-text');
                el.removeAttribute('data-original-text');
            }
        });
        
        form.classList.remove('loading');
    }
    
    // Form field search and autocomplete
    setupFieldAutocomplete() {
        document.querySelectorAll('[data-autocomplete]').forEach(field => {
            const source = field.dataset.autocomplete;
            const minLength = parseInt(field.dataset.minLength || '2', 10);
            
            // Create results container
            const resultsContainer = document.createElement('div');
            resultsContainer.className = 'autocomplete-results';
            resultsContainer.style.display = 'none';
            field.parentNode.insertBefore(resultsContainer, field.nextSibling);
            
            // Store reference to results container
            field.autocompleteResults = resultsContainer;
            
            // Add input event listener
            field.addEventListener('input', async () => {
                const query = field.value.trim();
                
                if (query.length < minLength) {
                    resultsContainer.style.display = 'none';
                    return;
                }
                
                try {
                    // Get autocomplete results from API or predefined list
                    let results = [];
                    
                    if (source.startsWith('/')) {
                        // API source
                        const response = await fetch(`${source}?q=${encodeURIComponent(query)}`);
                        if (!response.ok) throw new Error('Failed to fetch suggestions');
                        const data = await response.json();
                        results = data.results || data;
                    } else if (source === 'countries') {
                        // Predefined country list
                        results = this.getCountrySuggestions(query);
                    } else if (source === 'timezones') {
                        // Predefined timezone list
                        results = this.getTimezoneSuggestions(query);
                    }
                    
                    // Display results
                    if (results.length > 0) {
                        this.showAutocompleteResults(field, results);
                    } else {
                        resultsContainer.style.display = 'none';
                    }
                } catch (error) {
                    console.error('Autocomplete error:', error);
                    resultsContainer.style.display = 'none';
                }
            });
            
            // Handle blur event
            field.addEventListener('blur', () => {
                // Delay hiding to allow for item selection
                setTimeout(() => {
                    resultsContainer.style.display = 'none';
                }, 200);
            });
            
            // Handle focus event
            field.addEventListener('focus', () => {
                if (field.value.trim().length >= minLength) {
                    resultsContainer.style.display = 'block';
                }
            });
        });
    }
    
    showAutocompleteResults(field, results) {
        const container = field.autocompleteResults;
        
        // Clear previous results
        container.innerHTML = '';
        
        // Add new results
        results.forEach(item => {
            const resultItem = document.createElement('div');
            resultItem.className = 'autocomplete-item';
            resultItem.textContent = typeof item === 'string' ? item : (item.label || item.name || item.value);
            
            // Store value
            resultItem.dataset.value = typeof item === 'string' ? item : (item.value || item.id || item.code || resultItem.textContent);
            
            // Add click handler
            resultItem.addEventListener('click', () => {
                field.value = resultItem.textContent;
                
                // If there's a hidden value field
                if (field.dataset.valueField) {
                    const valueField = document.getElementById(field.dataset.valueField);
                    if (valueField) {
                        valueField.value = resultItem.dataset.value;
                    }
                }
                
                container.style.display = 'none';
                field.focus();
                
                // Trigger change event
                field.dispatchEvent(new Event('change', { bubbles: true }));
            });
            
            container.appendChild(resultItem);
        });
        
        // Show the container
        container.style.display = 'block';
    }
    
    getCountrySuggestions(query) {
        // List of common countries (abbreviated for example)
        const countries = [
            { name: 'United States', code: 'US' },
            { name: 'United Kingdom', code: 'UK' },
            { name: 'Canada', code: 'CA' },
            { name: 'Australia', code: 'AU' },
            { name: 'Germany', code: 'DE' },
            { name: 'France', code: 'FR' },
            { name: 'Japan', code: 'JP' },
            { name: 'China', code: 'CN' },
            { name: 'India', code: 'IN' },
            { name: 'Brazil', code: 'BR' }
        ];
        
        query = query.toLowerCase();
        return countries.filter(country => 
            country.name.toLowerCase().includes(query) || 
            country.code.toLowerCase().includes(query)
        );
    }
    
    getTimezoneSuggestions(query) {
        // List of common timezones (abbreviated for example)
        const timezones = [
            'America/New_York',
            'America/Los_Angeles',
            'America/Chicago',
            'Europe/London',
            'Europe/Paris',
            'Europe/Berlin',
            'Asia/Tokyo',
            'Asia/Shanghai',
            'Australia/Sydney',
            'Pacific/Auckland'
        ];
        
        query = query.toLowerCase();
        return timezones.filter(tz => tz.toLowerCase().includes(query));
    }
}
