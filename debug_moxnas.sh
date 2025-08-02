#!/bin/bash

# MoxNAS Debug Script
# Usage: Run this on Proxmox host to debug MoxNAS container issues

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEBUG] $1${NC}"; }
warn() { echo -e "${YELLOW}[DEBUG] WARNING: $1${NC}"; }
error() { echo -e "${RED}[DEBUG] ERROR: $1${NC}"; }

# Find MoxNAS container
CONTAINER_ID=""
for id in $(pct list | grep -E "(200|179|906)" | awk '{print $1}'); do
    if pct list | grep "$id" | grep -q "moxnas\|running"; then
        CONTAINER_ID=$id
        break
    fi
done

if [ -z "$CONTAINER_ID" ]; then
    error "No MoxNAS container found. Looking for any container with 'moxnas' in name..."
    pct list | grep -i moxnas || echo "No MoxNAS containers found"
    exit 1
fi

log "Found MoxNAS container: $CONTAINER_ID"

# Check container status
log "Checking container status..."
pct status $CONTAINER_ID

# Get container IP
log "Getting container IP..."
CONTAINER_IP=$(pct exec $CONTAINER_ID -- hostname -I 2>/dev/null | awk '{print $1}' || echo "unknown")
log "Container IP: $CONTAINER_IP"

# Check if container is accessible
log "Testing container connectivity..."
if pct exec $CONTAINER_ID -- echo "Container is accessible" 2>/dev/null; then
    log "✅ Container is accessible"
else
    error "❌ Cannot access container"
    exit 1
fi

# Check if MoxNAS is installed
log "Checking MoxNAS installation..."
if pct exec $CONTAINER_ID -- test -d /opt/moxnas; then
    log "✅ MoxNAS directory exists"
else
    error "❌ MoxNAS not installed in /opt/moxnas"
    exit 1
fi

# Check Python and Django
log "Checking Python environment..."
pct exec $CONTAINER_ID -- bash -c 'cd /opt/moxnas && source venv/bin/activate && python --version'

# Check if Django is working
log "Testing Django installation..."
pct exec $CONTAINER_ID -- bash -c 'cd /opt/moxnas/backend && source ../venv/bin/activate && python manage.py check'

# Check what's running on port 8000
log "Checking port 8000..."
pct exec $CONTAINER_ID -- netstat -tuln | grep :8000 || log "Port 8000 not listening"

# Check processes
log "Checking running processes..."
pct exec $CONTAINER_ID -- ps aux | grep -E "(python|django|manage)" || log "No Python/Django processes found"

# Check logs
log "Checking logs..."
if pct exec $CONTAINER_ID -- test -f /var/log/moxnas.log; then
    log "Recent MoxNAS logs:"
    pct exec $CONTAINER_ID -- tail -20 /var/log/moxnas.log
else
    warn "No MoxNAS log file found"
fi

# Try to start MoxNAS manually
log "Attempting to start MoxNAS..."
pct exec $CONTAINER_ID -- bash -c '
cd /opt/moxnas/backend
source ../venv/bin/activate

# Kill any existing processes
pkill -f "python.*manage.py" 2>/dev/null || true
sleep 2

# Start Django in background
echo "Starting Django server..."
nohup python manage.py runserver 0.0.0.0:8000 > /var/log/moxnas.log 2>&1 &

# Wait a bit
sleep 5

# Check if it started
if netstat -tuln | grep -q :8000; then
    echo "✅ MoxNAS started successfully on port 8000"
    IP=$(hostname -I | awk "{print \$1}")
    echo "🌐 Try accessing: http://$IP:8000"
else
    echo "❌ Failed to start MoxNAS"
    echo "Log output:"
    tail -10 /var/log/moxnas.log 2>/dev/null || echo "No log file"
fi
'

log "Debug complete. Try accessing: http://$CONTAINER_IP:8000"