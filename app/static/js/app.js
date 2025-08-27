/* MoxNAS JavaScript Application */

class MoxNAS {
    constructor() {
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.initTooltips();
        this.initAutoRefresh();
    }
    
    bindEvents() {
        // Global AJAX error handling
        $(document).ajaxError((event, xhr, settings, thrownError) => {
            if (xhr.status === 403) {
                this.showAlert('Access denied. Please check your permissions.', 'danger');
            } else if (xhr.status === 500) {
                this.showAlert('Internal server error. Please try again later.', 'danger');
            } else if (xhr.status !== 200) {
                this.showAlert(`Request failed: ${xhr.status} ${thrownError}`, 'danger');
            }
        });
        
        // Auto-hide alerts after 5 seconds
        $('.alert[data-auto-hide]').each(function() {
            setTimeout(() => {
                $(this).fadeOut();
            }, 5000);
        });
        
        // Confirm dialogs
        $('[data-confirm]').on('click', function(e) {
            const message = $(this).data('confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
        
        // Loading states for forms
        $('form').on('submit', function() {
            const $form = $(this);
            const $submitBtn = $form.find('button[type=\"submit\"]');
            
            $submitBtn.prop('disabled', true);
            $submitBtn.find('.spinner-border').removeClass('d-none');
        });
        
        // Real-time updates
        this.initWebSocket();
    }
    
    initTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle=\"tooltip\"]'));
        tooltipTriggerList.map(tooltipTriggerEl => {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    initAutoRefresh() {
        // Auto-refresh status indicators every 30 seconds
        setInterval(() => {
            this.refreshStatusIndicators();
        }, 30000);
    }
    
    initWebSocket() {
        // WebSocket connection for real-time updates
        // This would be implemented with Flask-SocketIO in production
        console.log('WebSocket support not implemented yet');
    }
    
    showAlert(message, type = 'info', timeout = 5000) {
        const alertHtml = `
            <div class=\"alert alert-${type} alert-dismissible fade show\" role=\"alert\">
                ${message}
                <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"alert\"></button>
            </div>
        `;
        
        $('.main-content .container-fluid').prepend(alertHtml);
        
        if (timeout > 0) {
            setTimeout(() => {
                $('.alert').first().fadeOut();
            }, timeout);
        }
    }
    
    refreshStatusIndicators() {
        // Refresh status indicators on the page
        $('.status-refresh').each(function() {
            const $indicator = $(this);
            const url = $indicator.data('refresh-url');
            
            if (url) {
                $.get(url)
                    .done(data => {
                        $indicator.removeClass('healthy warning failed offline')
                                  .addClass(data.status);
                        $indicator.attr('title', data.message || data.status);
                    })
                    .fail(() => {
                        $indicator.removeClass('healthy warning failed offline')
                                  .addClass('offline');
                    });
            }
        });
    }
    
    // Storage management functions
    scanDevices() {
        this.showAlert('Scanning storage devices...', 'info');
        
        return $.post('/storage/devices/scan')
            .done(data => {
                if (data.success) {
                    this.showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    this.showAlert(data.error, 'danger');
                }
            })
            .fail(() => {
                this.showAlert('Failed to scan devices', 'danger');
            });
    }
    
    startPoolScrub(poolId) {
        if (!confirm('Start scrubbing this storage pool? This may take several hours.')) {
            return;
        }
        
        this.showAlert('Starting pool scrub...', 'info');
        
        return $.post(`/storage/pools/${poolId}/scrub`)
            .done(data => {
                if (data.success) {
                    this.showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    this.showAlert(data.error, 'danger');
                }
            })
            .fail(() => {
                this.showAlert('Failed to start scrub', 'danger');
            });
    }
    
    deletePool(poolId, poolName) {
        const confirmMessage = `Are you sure you want to delete pool \"${poolName}\"? This action cannot be undone and will permanently destroy all data.`;
        
        if (!confirm(confirmMessage)) {
            return;
        }
        
        if (!confirm('This will PERMANENTLY DELETE ALL DATA in this pool. Type \"DELETE\" to confirm.') ||
            prompt('Type \"DELETE\" to confirm:') !== 'DELETE') {
            return;
        }
        
        this.showAlert('Deleting storage pool...', 'warning');
        
        return $.post(`/storage/pools/${poolId}/delete`)
            .done(data => {
                if (data.success) {
                    this.showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.href = '/storage/pools';
                    }, 2000);
                } else {
                    this.showAlert(data.error, 'danger');
                }
            })
            .fail(() => {
                this.showAlert('Failed to delete pool', 'danger');
            });
    }
    
    // Share management functions
    toggleShare(shareId, shareName) {
        this.showAlert(`Toggling share \"${shareName}\"...`, 'info');
        
        return $.post(`/shares/${shareId}/toggle`)
            .done(data => {
                if (data.success) {
                    this.showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    this.showAlert(data.error, 'danger');
                }
            })
            .fail(() => {
                this.showAlert('Failed to toggle share', 'danger');
            });
    }
    
    deleteShare(shareId, shareName) {
        if (!confirm(`Are you sure you want to delete share \"${shareName}\"?`)) {
            return;
        }
        
        this.showAlert('Deleting share...', 'warning');
        
        return $.post(`/shares/${shareId}/delete`)
            .done(data => {
                if (data.success) {
                    this.showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    this.showAlert(data.error, 'danger');
                }
            })
            .fail(() => {
                this.showAlert('Failed to delete share', 'danger');
            });
    }
    
    // Backup management functions
    startBackup(jobId, jobName) {
        if (!confirm(`Start backup job \"${jobName}\"?`)) {
            return;
        }
        
        this.showAlert('Starting backup...', 'info');
        
        return $.post(`/backups/${jobId}/start`)
            .done(data => {
                if (data.success) {
                    this.showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    this.showAlert(data.error, 'danger');
                }
            })
            .fail(() => {
                this.showAlert('Failed to start backup', 'danger');
            });
    }
    
    stopBackup(jobId, jobName) {
        if (!confirm(`Stop backup job \"${jobName}\"?`)) {
            return;
        }
        
        this.showAlert('Stopping backup...', 'warning');
        
        return $.post(`/backups/${jobId}/stop`)
            .done(data => {
                if (data.success) {
                    this.showAlert(data.message, 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    this.showAlert(data.error, 'danger');
                }
            })
            .fail(() => {
                this.showAlert('Failed to stop backup', 'danger');
            });
    }
    
    // Utility functions
    formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
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
    
    copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showAlert('Copied to clipboard', 'success', 2000);
        }).catch(() => {
            this.showAlert('Failed to copy to clipboard', 'danger');
        });
    }
}

// Chart utilities
class ChartUtils {
    static createLineChart(ctx, data, options = {}) {
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                }
            }
        };
        
        return new Chart(ctx, {
            type: 'line',
            data: data,
            options: { ...defaultOptions, ...options }
        });
    }
    
    static createDoughnutChart(ctx, data, options = {}) {
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                }
            }
        };
        
        return new Chart(ctx, {
            type: 'doughnut',
            data: data,
            options: { ...defaultOptions, ...options }
        });
    }
    
    static createBarChart(ctx, data, options = {}) {
        const defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        };
        
        return new Chart(ctx, {
            type: 'bar',
            data: data,
            options: { ...defaultOptions, ...options }
        });
    }
}

// Form validation utilities
class FormValidator {
    static validateRequired(value, fieldName) {
        if (!value || value.trim() === '') {
            return `${fieldName} is required`;
        }
        return null;
    }
    
    static validateEmail(email) {
        const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
        if (!emailRegex.test(email)) {
            return 'Please enter a valid email address';
        }
        return null;
    }
    
    static validatePassword(password) {
        const errors = [];
        
        if (password.length < 8) {
            errors.push('Password must be at least 8 characters long');
        }
        
        if (!/[A-Z]/.test(password)) {
            errors.push('Password must contain at least one uppercase letter');
        }
        
        if (!/[a-z]/.test(password)) {
            errors.push('Password must contain at least one lowercase letter');
        }
        
        if (!/[0-9]/.test(password)) {
            errors.push('Password must contain at least one number');
        }
        
        if (!/[!@#$%^&*()_+\\-=\\[\\]{};':\"\\|,.<>?]/.test(password)) {
            errors.push('Password must contain at least one special character');
        }
        
        return errors.length > 0 ? errors : null;
    }
    
    static validateForm(formData, rules) {
        const errors = {};
        
        for (const [field, rule] of Object.entries(rules)) {
            const value = formData[field];
            let fieldErrors = [];
            
            if (rule.required) {
                const error = this.validateRequired(value, rule.label || field);
                if (error) fieldErrors.push(error);
            }
            
            if (value && rule.type === 'email') {
                const error = this.validateEmail(value);
                if (error) fieldErrors.push(error);
            }
            
            if (value && rule.type === 'password') {
                const passwordErrors = this.validatePassword(value);
                if (passwordErrors) fieldErrors = fieldErrors.concat(passwordErrors);
            }
            
            if (fieldErrors.length > 0) {
                errors[field] = fieldErrors;
            }
        }
        
        return Object.keys(errors).length > 0 ? errors : null;
    }
}

// Initialize MoxNAS application
let moxnas;

document.addEventListener('DOMContentLoaded', function() {
    moxnas = new MoxNAS();
    
    // Make utilities available globally
    window.ChartUtils = ChartUtils;
    window.FormValidator = FormValidator;
});

// Global utility functions
window.scanDevices = () => moxnas.scanDevices();
window.startPoolScrub = (poolId) => moxnas.startPoolScrub(poolId);
window.deletePool = (poolId, poolName) => moxnas.deletePool(poolId, poolName);
window.toggleShare = (shareId, shareName) => moxnas.toggleShare(shareId, shareName);
window.deleteShare = (shareId, shareName) => moxnas.deleteShare(shareId, shareName);
window.startBackup = (jobId, jobName) => moxnas.startBackup(jobId, jobName);
window.stopBackup = (jobId, jobName) => moxnas.stopBackup(jobId, jobName);