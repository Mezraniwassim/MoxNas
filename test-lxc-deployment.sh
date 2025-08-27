#!/usr/bin/env bash
"""
Test LXC Deployment Script
Tests MoxNAS deployment in LXC container environment
"""

set -euo pipefail

# Colors for output
RD="\033[01;31m"
YW="\033[33m"
GN="\033[1;92m"
CL="\033[m"
BFR="\\r\\033[K"

function msg_info() {
    echo -e " ⏳ ${YW}$1...${CL}"
}

function msg_ok() {
    echo -e " ✅ ${GN}$1${CL}"
}

function msg_error() {
    echo -e " ❌ ${RD}$1${CL}"
}

# Test configuration
TEST_CTID=${TEST_CTID:-999}
TEST_HOSTNAME="moxnas-test"
TEST_PASSWORD="test123"

echo "🧪 MoxNAS LXC Deployment Test"
echo "=" * 50

# Check if we're on Proxmox
if ! command -v pct &> /dev/null; then
    msg_error "This test must be run on a Proxmox VE host"
    exit 1
fi

# Check if test container already exists
if pct status $TEST_CTID &>/dev/null; then
    msg_info "Cleaning up existing test container"
    pct stop $TEST_CTID 2>/dev/null || true
    pct destroy $TEST_CTID 2>/dev/null || true
    msg_ok "Test container cleaned up"
fi

# Deploy test container
msg_info "Deploying test MoxNAS container"
CTID=$TEST_CTID CT_HOSTNAME=$TEST_HOSTNAME PASSWORD=$TEST_PASSWORD \
CORES=2 MEMORY=2048 DISK_SIZE=10 \
bash install-moxnas-lxc.sh

if [ $? -eq 0 ]; then
    msg_ok "Container deployment completed"
else
    msg_error "Container deployment failed"
    exit 1
fi

# Wait for services to start
msg_info "Waiting for services to start"
sleep 30

# Get container IP
CONTAINER_IP=$(pct exec $TEST_CTID -- hostname -I | awk '{print $1}')
msg_ok "Container IP: $CONTAINER_IP"

# Test HTTP response
msg_info "Testing HTTP response"
if curl -k -s https://$CONTAINER_IP | grep -q "MoxNAS"; then
    msg_ok "MoxNAS web interface is accessible"
else
    msg_error "MoxNAS web interface is not responding"
    
    # Debug information
    echo "=== Container status ==="
    pct status $TEST_CTID
    
    echo "=== Service status ==="
    pct exec $TEST_CTID -- systemctl status moxnas --no-pager
    pct exec $TEST_CTID -- systemctl status nginx --no-pager
    pct exec $TEST_CTID -- systemctl status postgresql --no-pager
    pct exec $TEST_CTID -- systemctl status redis-server --no-pager
    
    echo "=== Logs ==="
    pct exec $TEST_CTID -- journalctl -u moxnas --no-pager --lines=20
fi

# Test admin credentials
msg_info "Checking admin credentials"
ADMIN_CREDS=$(pct exec $TEST_CTID -- cat /opt/moxnas/.admin_credentials 2>/dev/null || echo "Not found")
if [[ "$ADMIN_CREDS" != "Not found" ]]; then
    msg_ok "Admin credentials available"
    echo "$ADMIN_CREDS"
else
    msg_error "Admin credentials not found"
fi

# Test database connectivity
msg_info "Testing database connectivity"
if pct exec $TEST_CTID -- sudo -u moxnas bash -c "cd /opt/moxnas && source venv/bin/activate && python -c 'from app import create_app, db; app = create_app(\"production\"); app.app_context().push(); print(\"Database:\", db.engine.url)'"; then
    msg_ok "Database connectivity OK"
else
    msg_error "Database connectivity failed"
fi

# Test storage detection
msg_info "Testing storage device detection"
if pct exec $TEST_CTID -- sudo -u moxnas bash -c "cd /opt/moxnas && source venv/bin/activate && python -c 'from app.storage.manager import storage_manager; devices = storage_manager.scan_storage_devices(); print(f\"Detected {len(devices)} storage devices\")'"; then
    msg_ok "Storage device detection working"
else
    msg_error "Storage device detection failed"
fi

echo ""
echo "=" * 50
echo "🎯 Test Summary:"
echo "   Container ID: $TEST_CTID"
echo "   Hostname: $TEST_HOSTNAME"
echo "   IP Address: $CONTAINER_IP"
echo "   Web Interface: https://$CONTAINER_IP"
echo ""
echo "📋 Next steps:"
echo "   1. Access the web interface: https://$CONTAINER_IP"
echo "   2. Login with admin credentials shown above"
echo "   3. Test core functionality (storage, shares, etc.)"
echo "   4. Clean up test container: pct stop $TEST_CTID && pct destroy $TEST_CTID"
echo ""
echo "✨ MoxNAS LXC deployment test completed!"