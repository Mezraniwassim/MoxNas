#!/bin/bash
#
# MoxNAS Deployment Verification Script
# Verifies that MoxNAS is properly installed and accessible
#

set -e

# Configuration
CONTAINER_ID=${1}
TIMEOUT=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Usage information
usage() {
    echo "Usage: $0 <container-id>"
    echo ""
    echo "Example: $0 200"
    echo ""
    echo "This script verifies that MoxNAS is properly installed and accessible."
    exit 1
}

# Check parameters
if [ -z "$CONTAINER_ID" ]; then
    log_error "Container ID is required"
    usage
fi

# Check if running on Proxmox
if ! command -v pct &> /dev/null; then
    log_error "This script must be run on a Proxmox VE host"
    exit 1
fi

echo "=========================================="
echo "       MoxNAS Deployment Verification    "
echo "=========================================="
echo ""
echo "Container ID: $CONTAINER_ID"
echo ""

# Step 1: Check if container exists
log_info "Checking if container exists..."
if ! pct status "$CONTAINER_ID" &> /dev/null; then
    log_error "Container $CONTAINER_ID does not exist"
    exit 1
fi
log_success "Container $CONTAINER_ID exists"

# Step 2: Check if container is running
log_info "Checking container status..."
if ! pct status "$CONTAINER_ID" | grep -q "running"; then
    log_warning "Container is not running. Starting..."
    pct start "$CONTAINER_ID"
    sleep 10
fi

if pct status "$CONTAINER_ID" | grep -q "running"; then
    log_success "Container is running"
else
    log_error "Container failed to start"
    exit 1
fi

# Step 3: Get container IP
log_info "Getting container IP address..."
CONTAINER_IP=$(pct exec "$CONTAINER_ID" -- hostname -I | awk '{print $1}' 2>/dev/null)

if [ -z "$CONTAINER_IP" ]; then
    log_error "Could not determine container IP address"
    exit 1
fi

log_success "Container IP: $CONTAINER_IP"

# Step 4: Check if MoxNAS service is running
log_info "Checking MoxNAS service status..."
if pct exec "$CONTAINER_ID" -- systemctl is-active moxnas &> /dev/null; then
    log_success "MoxNAS service is running"
else
    log_warning "MoxNAS service is not running. Checking status..."
    pct exec "$CONTAINER_ID" -- systemctl status moxnas --no-pager
    
    # Try to start the service
    log_info "Attempting to start MoxNAS service..."
    if pct exec "$CONTAINER_ID" -- systemctl start moxnas; then
        sleep 5
        if pct exec "$CONTAINER_ID" -- systemctl is-active moxnas &> /dev/null; then
            log_success "MoxNAS service started successfully"
        else
            log_error "Failed to start MoxNAS service"
            exit 1
        fi
    else
        log_error "Failed to start MoxNAS service"
        exit 1
    fi
fi

# Step 5: Check if web interface is accessible
log_info "Testing web interface accessibility..."
WEB_URL="http://$CONTAINER_IP:8000"

# Wait for web interface to be ready
counter=0
while [ $counter -lt $TIMEOUT ]; do
    if curl -s --connect-timeout 5 "$WEB_URL" > /dev/null 2>&1; then
        log_success "Web interface is accessible at $WEB_URL"
        break
    fi
    
    sleep 2
    counter=$((counter + 1))
    
    if [ $counter -eq $TIMEOUT ]; then
        log_error "Web interface not accessible after $TIMEOUT attempts"
        log_info "Checking port 8000..."
        pct exec "$CONTAINER_ID" -- netstat -tlnp | grep :8000 || log_warning "Port 8000 not listening"
        
        log_info "Checking MoxNAS logs..."
        pct exec "$CONTAINER_ID" -- journalctl -u moxnas --no-pager -n 10
        exit 1
    fi
done

# Step 6: Test API endpoints
log_info "Testing API endpoints..."
API_BASE="http://$CONTAINER_IP:8000/api"

# Test system endpoint
if curl -s --connect-timeout 5 "$API_BASE/core/system/current/" > /dev/null 2>&1; then
    log_success "System API endpoint responding"
else
    log_warning "System API endpoint not responding"
fi

# Test services endpoint
if curl -s --connect-timeout 5 "$API_BASE/services/status/" > /dev/null 2>&1; then
    log_success "Services API endpoint responding"
else
    log_warning "Services API endpoint not responding"
fi

# Step 7: Check NAS services
log_info "Checking NAS services..."
services=("smbd" "nfs-kernel-server" "vsftpd" "ssh" "snmpd")

for service in "${services[@]}"; do
    if pct exec "$CONTAINER_ID" -- systemctl is-active "$service" &> /dev/null; then
        log_success "$service is running"
    else
        log_warning "$service is not running"
    fi
done

# Step 8: Check storage directory
log_info "Checking storage configuration..."
if pct exec "$CONTAINER_ID" -- test -d "/mnt/storage"; then
    log_success "Storage directory exists"
    
    # Check if writable
    if pct exec "$CONTAINER_ID" -- test -w "/mnt/storage"; then
        log_success "Storage directory is writable"
    else
        log_warning "Storage directory is not writable"
    fi
else
    log_error "Storage directory missing"
fi

# Step 9: Check container resources
log_info "Checking container resources..."
memory_mb=$(pct config "$CONTAINER_ID" | grep memory | cut -d' ' -f2)
cores=$(pct config "$CONTAINER_ID" | grep cores | cut -d' ' -f2)

log_info "Container configuration:"
log_info "  Memory: ${memory_mb}MB"
log_info "  CPU Cores: $cores"

if [ "$memory_mb" -lt 2048 ]; then
    log_warning "Container has less than 2GB RAM (recommended minimum)"
fi

# Step 10: Final summary
echo ""
echo "=========================================="
echo "         Verification Summary             "
echo "=========================================="
echo ""
echo "✅ Container Status: Running"
echo "✅ IP Address: $CONTAINER_IP"
echo "✅ Web Interface: $WEB_URL"
echo "✅ MoxNAS Service: Running"
echo ""
echo "📝 Next Steps:"
echo "1. Open your web browser"
echo "2. Navigate to: $WEB_URL"
echo "3. Login with: admin / moxnas123"
echo "4. Configure your storage and shares"
echo ""
echo "📋 Useful Commands:"
echo "  Container shell:  pct enter $CONTAINER_ID"
echo "  View logs:        pct exec $CONTAINER_ID -- journalctl -u moxnas -f"
echo "  Restart service:  pct exec $CONTAINER_ID -- systemctl restart moxnas"
echo "  Container stop:   pct stop $CONTAINER_ID"
echo "  Container start:  pct start $CONTAINER_ID"
echo ""

log_success "MoxNAS verification completed successfully!"