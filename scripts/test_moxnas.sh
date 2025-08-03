#!/bin/bash

# MoxNas Testing Script
# Usage: ./test_moxnas.sh [container_id]

CONTAINER_ID=${1:-200}
CONTAINER_IP=""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Test container exists
test_container_exists() {
    log "Testing if container $CONTAINER_ID exists..."
    if pct status $CONTAINER_ID >/dev/null 2>&1; then
        success "Container $CONTAINER_ID exists"
        return 0
    else
        fail "Container $CONTAINER_ID does not exist"
        return 1
    fi
}

# Test container is running
test_container_running() {
    log "Testing if container $CONTAINER_ID is running..."
    if pct status $CONTAINER_ID | grep -q "status: running"; then
        success "Container $CONTAINER_ID is running"
        return 0
    else
        fail "Container $CONTAINER_ID is not running"
        return 1
    fi
}

# Get container IP
get_container_ip() {
    log "Getting container IP address..."
    CONTAINER_IP=$(pct exec $CONTAINER_ID -- hostname -I 2>/dev/null | awk '{print $1}' | tr -d '\n')
    if [[ $CONTAINER_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        success "Container IP: $CONTAINER_IP"
        return 0
    else
        fail "Could not get container IP"
        return 1
    fi
}

# Test MoxNas service
test_moxnas_service() {
    log "Testing MoxNas service status..."
    if pct exec $CONTAINER_ID -- systemctl is-active moxnas >/dev/null 2>&1; then
        success "MoxNas service is running"
        return 0
    else
        fail "MoxNas service is not running"
        return 1
    fi
}

# Test web interface
test_web_interface() {
    log "Testing web interface accessibility..."
    if curl -s --connect-timeout 10 http://$CONTAINER_IP:8000 >/dev/null; then
        success "Web interface is accessible at http://$CONTAINER_IP:8000"
        return 0
    else
        fail "Web interface is not accessible"
        return 1
    fi
}

# Test API endpoints
test_api_endpoints() {
    log "Testing API endpoints..."
    
    # Test dashboard API
    if curl -s --connect-timeout 5 http://$CONTAINER_IP:8000/api/proxmox/dashboard/ | grep -q "containers\|error"; then
        success "Dashboard API responds"
    else
        fail "Dashboard API not responding"
    fi
    
    # Test containers API
    if curl -s --connect-timeout 5 http://$CONTAINER_IP:8000/api/containers/ | grep -q "containers\|error"; then
        success "Containers API responds"
    else
        fail "Containers API not responding"
    fi
    
    # Test storage API
    if curl -s --connect-timeout 5 http://$CONTAINER_IP:8000/api/storage/datasets/ | grep -q "datasets\|error"; then
        success "Storage API responds"
    else
        fail "Storage API not responding"
    fi
}

# Test NAS services
test_nas_services() {
    log "Testing NAS services..."
    
    # SSH
    if pct exec $CONTAINER_ID -- systemctl is-enabled ssh >/dev/null 2>&1; then
        success "SSH service is enabled"
    else
        warning "SSH service not enabled"
    fi
    
    # FTP
    if pct exec $CONTAINER_ID -- systemctl is-enabled vsftpd >/dev/null 2>&1; then
        success "FTP service is enabled"
    else
        warning "FTP service not enabled"
    fi
    
    # SMB
    if pct exec $CONTAINER_ID -- systemctl is-enabled smbd >/dev/null 2>&1; then
        success "SMB service is enabled"
    else
        warning "SMB service not enabled"
    fi
    
    # NFS
    if pct exec $CONTAINER_ID -- systemctl is-enabled nfs-kernel-server >/dev/null 2>&1; then
        success "NFS service is enabled"
    else
        warning "NFS service not enabled"
    fi
}

# Test directory structure
test_directory_structure() {
    log "Testing directory structure..."
    
    if pct exec $CONTAINER_ID -- test -d /opt/moxnas; then
        success "MoxNas directory exists"
    else
        fail "MoxNas directory missing"
    fi
    
    if pct exec $CONTAINER_ID -- test -f /opt/moxnas/backend/manage.py; then
        success "Django backend exists"
    else
        fail "Django backend missing"
    fi
    
    if pct exec $CONTAINER_ID -- test -d /opt/moxnas/frontend/build; then
        success "Frontend build exists"
    else
        warning "Frontend build missing"
    fi
}

# Test resource usage
test_resource_usage() {
    log "Testing resource usage..."
    
    # Memory usage
    memory_used=$(pct exec $CONTAINER_ID -- free -m | awk 'NR==2{printf "%.1f", $3/$2*100}')
    log "Memory usage: ${memory_used}%"
    
    # Disk usage
    disk_used=$(pct exec $CONTAINER_ID -- df -h /opt/moxnas | awk 'NR==2{print $5}')
    log "Disk usage: $disk_used"
    
    # Process count
    process_count=$(pct exec $CONTAINER_ID -- ps aux | wc -l)
    log "Running processes: $process_count"
}

# Run all tests
run_all_tests() {
    echo "=================================="
    echo "MoxNas Comprehensive Test Suite"
    echo "Container ID: $CONTAINER_ID"
    echo "=================================="
    echo
    
    local failed_tests=0
    
    test_container_exists || ((failed_tests++))
    test_container_running || ((failed_tests++))
    get_container_ip || ((failed_tests++))
    
    if [ $failed_tests -eq 0 ]; then
        test_moxnas_service || ((failed_tests++))
        test_web_interface || ((failed_tests++))
        test_api_endpoints
        test_nas_services
        test_directory_structure
        test_resource_usage
    fi
    
    echo
    echo "=================================="
    if [ $failed_tests -eq 0 ]; then
        success "All critical tests passed!"
        echo -e "${GREEN}MoxNas is working correctly${NC}"
        echo -e "${BLUE}Web Interface: http://$CONTAINER_IP:8000${NC}"
        echo -e "${BLUE}Admin Panel: http://$CONTAINER_IP:8000/admin${NC}"
        echo -e "${BLUE}Login: admin / admin123${NC}"
    else
        fail "$failed_tests critical tests failed"
        echo -e "${RED}MoxNas needs troubleshooting${NC}"
        echo
        echo "Try these recovery commands:"
        echo "  pct exec $CONTAINER_ID -- systemctl restart moxnas"
        echo "  pct exec $CONTAINER_ID -- /opt/moxnas/start_service.sh"
        echo "  pct exec $CONTAINER_ID -- journalctl -u moxnas -n 20"
    fi
    echo "=================================="
}

# Main execution
main() {
    if [[ $EUID -ne 0 ]]; then
        fail "This script must be run as root on the Proxmox host"
        exit 1
    fi
    
    run_all_tests
}

main "$@"