#!/bin/bash
#
# MoxNAS Installation Verification Script
# Usage: ./verify_installation.sh [container_id]
#

set -e

CONTAINER_ID=${1:-200}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_container() {
    log_info "Checking if container $CONTAINER_ID exists..."
    if ! pct status "$CONTAINER_ID" &> /dev/null; then
        log_error "Container $CONTAINER_ID does not exist"
        exit 1
    fi
    
    local status=$(pct status "$CONTAINER_ID")
    if [[ "$status" != "status: running" ]]; then
        log_warning "Container is not running. Status: $status"
        log_info "Starting container..."
        pct start "$CONTAINER_ID"
        sleep 5
    fi
    
    log_success "Container $CONTAINER_ID is running"
}

get_container_ip() {
    log_info "Getting container IP address..."
    CONTAINER_IP=$(pct exec "$CONTAINER_ID" -- hostname -I | awk '{print $1}')
    if [[ -z "$CONTAINER_IP" ]]; then
        log_error "Could not get container IP address"
        exit 1
    fi
    log_success "Container IP: $CONTAINER_IP"
}

check_moxnas_service() {
    log_info "Checking MoxNAS service status..."
    
    if pct exec "$CONTAINER_ID" -- systemctl is-active moxnas &> /dev/null; then
        log_success "MoxNAS service is running"
    else
        log_warning "MoxNAS service is not running"
        log_info "Attempting to start MoxNAS service..."
        pct exec "$CONTAINER_ID" -- systemctl start moxnas
        sleep 5
        
        if pct exec "$CONTAINER_ID" -- systemctl is-active moxnas &> /dev/null; then
            log_success "MoxNAS service started successfully"
        else
            log_error "Failed to start MoxNAS service"
            log_info "Checking service logs..."
            pct exec "$CONTAINER_ID" -- journalctl -u moxnas --no-pager -n 20
            return 1
        fi
    fi
}

check_nas_services() {
    log_info "Checking NAS services..."
    
    local services=("ssh" "smbd" "nmbd" "nfs-kernel-server" "vsftpd" "snmpd" "tgt")
    
    for service in "${services[@]}"; do
        if pct exec "$CONTAINER_ID" -- systemctl is-active "$service" &> /dev/null; then
            log_success "$service is running"
        else
            log_warning "$service is not running"
        fi
    done
}

check_web_interface() {
    log_info "Checking web interface accessibility..."
    
    # Wait a moment for services to be ready
    sleep 3
    
    if curl -s --connect-timeout 10 "http://$CONTAINER_IP:8000" > /dev/null; then
        log_success "Web interface is accessible at http://$CONTAINER_IP:8000"
    else
        log_error "Web interface is not accessible"
        log_info "Checking if port 8000 is listening..."
        pct exec "$CONTAINER_ID" -- netstat -ln | grep :8000 || log_warning "Port 8000 is not listening"
        return 1
    fi
}

check_api_endpoints() {
    log_info "Checking API endpoints..."
    
    # Test core API endpoint
    if curl -s --connect-timeout 5 "http://$CONTAINER_IP:8000/api/" > /dev/null; then
        log_success "API is responding"
    else
        log_warning "API is not responding"
    fi
}

check_storage_directory() {
    log_info "Checking storage directory..."
    
    if pct exec "$CONTAINER_ID" -- test -d /mnt/storage; then
        log_success "Storage directory exists at /mnt/storage"
        
        # Check permissions
        local perms=$(pct exec "$CONTAINER_ID" -- stat -c "%a" /mnt/storage)
        log_info "Storage directory permissions: $perms"
    else
        log_warning "Storage directory does not exist"
    fi
}

check_configuration_files() {
    log_info "Checking configuration files..."
    
    local configs=(
        "/opt/moxnas/.env:MoxNAS environment"
        "/etc/samba/smb.conf:Samba configuration"
        "/etc/exports:NFS exports"
        "/etc/systemd/system/moxnas.service:MoxNAS systemd service"
    )
    
    for config in "${configs[@]}"; do
        local file="${config%:*}"
        local desc="${config#*:}"
        
        if pct exec "$CONTAINER_ID" -- test -f "$file"; then
            log_success "$desc exists"
        else
            log_warning "$desc is missing"
        fi
    done
}

test_database() {
    log_info "Testing database connectivity..."
    
    if pct exec "$CONTAINER_ID" -- /opt/moxnas/venv/bin/python /opt/moxnas/backend/manage.py check &> /dev/null; then
        log_success "Database is accessible"
    else
        log_warning "Database check failed"
    fi
}

show_summary() {
    echo ""
    echo "=========================================="
    echo "       MoxNAS Verification Complete       "
    echo "=========================================="
    echo ""
    echo "Container Information:"
    echo "  ID: $CONTAINER_ID"
    echo "  IP Address: $CONTAINER_IP"
    echo ""
    echo "Access Points:"
    echo "  Web Interface: http://$CONTAINER_IP:8000"
    echo "  API Base: http://$CONTAINER_IP:8000/api/"
    echo "  Admin Panel: http://$CONTAINER_IP:8000/admin/"
    echo ""
    echo "Default Credentials:"
    echo "  Username: admin"
    echo "  Password: moxnas123"
    echo ""
    echo "NAS Services:"
    echo "  SMB/CIFS: //$CONTAINER_IP/moxnas-share"
    echo "  NFS: $CONTAINER_IP:/mnt/storage"
    echo "  FTP: ftp://$CONTAINER_IP"
    echo "  SSH: ssh root@$CONTAINER_IP"
    echo ""
    echo "Container Management:"
    echo "  Start: pct start $CONTAINER_ID"
    echo "  Stop: pct stop $CONTAINER_ID"
    echo "  Shell: pct enter $CONTAINER_ID"
    echo "  Logs: pct exec $CONTAINER_ID -- journalctl -u moxnas -f"
    echo ""
}

main() {
    echo "=========================================="
    echo "       MoxNAS Installation Verification   "
    echo "=========================================="
    echo ""
    
    check_container
    get_container_ip
    check_moxnas_service
    check_nas_services
    check_web_interface
    check_api_endpoints
    check_storage_directory
    check_configuration_files
    test_database
    show_summary
    
    log_success "Verification completed successfully!"
}

# Check if running on Proxmox
if ! command -v pct &> /dev/null; then
    log_error "This script must be run on a Proxmox VE host"
    exit 1
fi

# Run main function
main "$@"