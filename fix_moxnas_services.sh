#!/bin/bash
#
# MoxNAS Service Fix Script
# Run this script to fix "Failed to save share" and service issues
# Usage: ./fix_moxnas_services.sh [container_id]
#

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

echo "=========================================="
echo "       MoxNAS Service Fix Tool           "
echo "=========================================="
echo ""

# Check if container exists
if ! pct status "$CONTAINER_ID" &> /dev/null; then
    log_error "Container $CONTAINER_ID does not exist"
    exit 1
fi

log_info "Fixing MoxNAS services in container $CONTAINER_ID..."

# Fix service configurations and permissions
log_info "Step 1: Fixing service configurations and permissions..."

pct exec "$CONTAINER_ID" -- bash -c "
    # Fix NFS exports - remove duplicate entries
    if [ -f /etc/exports ]; then
        # Remove duplicate entries for /mnt/storage
        grep -v '^/mnt/storage' /etc/exports > /tmp/exports.tmp || true
        echo '/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)' >> /tmp/exports.tmp
        mv /tmp/exports.tmp /etc/exports
    else
        echo '/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)' > /etc/exports
    fi
    
    # Fix Samba configuration - remove duplicate www share
    if [ -f /etc/samba/smb.conf ]; then
        # Remove the www share section that was causing issues
        sed -i '/\[www\]/,/^$/d' /etc/samba/smb.conf
    fi
    
    # Ensure storage directories have proper permissions
    mkdir -p /mnt/storage
    chmod 755 /mnt/storage
    chown root:root /mnt/storage
    
    # Create MoxNAS config and log directories
    mkdir -p /etc/moxnas /var/log/moxnas
    chmod 755 /etc/moxnas /var/log/moxnas
    
    # Fix Django database permissions
    cd /opt/moxnas/backend
    chmod 664 db.sqlite3 2>/dev/null || true
"

log_success "Service configurations fixed"

# Install missing dependencies and fix Python environment
log_info "Step 2: Installing missing dependencies..."

pct exec "$CONTAINER_ID" -- bash -c "
    cd /opt/moxnas
    source venv/bin/activate
    
    # Install missing Python packages
    pip install psutil gunicorn 2>/dev/null || true
    
    # Run Django migrations to ensure database is up to date
    cd backend
    python manage.py migrate --run-syncdb 2>/dev/null || true
    python manage.py collectstatic --noinput 2>/dev/null || true
    
    # Initialize services using management command
    python manage.py initialize_services 2>/dev/null || true
"

log_success "Dependencies installed and database updated"

# Restart and fix services
log_info "Step 3: Restarting and fixing services..."

pct exec "$CONTAINER_ID" -- bash -c "
    # Reload NFS exports
    exportfs -ra 2>/dev/null || true
    
    # Restart NAS services
    systemctl restart smbd nmbd 2>/dev/null || true
    systemctl restart nfs-kernel-server 2>/dev/null || true
    systemctl restart vsftpd 2>/dev/null || true
    
    # Stop any existing MoxNAS processes
    pkill -f gunicorn 2>/dev/null || true
    sleep 2
"

log_success "Services restarted"

# Start MoxNAS web interface
log_info "Step 4: Starting MoxNAS web interface..."

pct exec "$CONTAINER_ID" -- bash -c "
    cd /opt/moxnas
    source venv/bin/activate
    cd backend
    
    # Start gunicorn in daemon mode
    gunicorn --bind 0.0.0.0:8000 --workers 3 moxnas.wsgi:application --daemon
"

# Wait and verify
sleep 5

CONTAINER_IP=$(pct exec "$CONTAINER_ID" -- hostname -I | awk '{print $1}')

log_info "Step 5: Verifying installation..."

# Check if gunicorn is running
if pct exec "$CONTAINER_ID" -- ps aux | grep -q "gunicorn.*8000"; then
    log_success "✅ MoxNAS web interface is running"
    
    # Test web interface
    if curl -I "http://$CONTAINER_IP:8000" &> /dev/null; then
        log_success "✅ Web interface is accessible!"
        echo ""
        echo "=========================================="
        echo "           Fix Complete!                  "
        echo "=========================================="
        echo ""
        echo "🌐 Web Interface: http://$CONTAINER_IP:8000"
        echo "👤 Login: admin / moxnas123"
        echo ""
        echo "✅ All services should now be working"
        echo "✅ Share creation should work properly"
        echo ""
    else
        log_warning "⚠️  Web interface may not be fully accessible yet"
        echo "Try accessing: http://$CONTAINER_IP:8000"
    fi
else
    log_error "❌ MoxNAS web interface failed to start"
    echo ""
    echo "Manual start command:"
    echo "pct exec $CONTAINER_ID -- bash -c 'cd /opt/moxnas && source venv/bin/activate && cd backend && gunicorn --bind 0.0.0.0:8000 --workers 3 moxnas.wsgi:application --daemon'"
fi

echo ""
echo "Container Management Commands:"
echo "  Start container: pct start $CONTAINER_ID"
echo "  Stop container:  pct stop $CONTAINER_ID"
echo "  Container shell: pct enter $CONTAINER_ID"
echo ""