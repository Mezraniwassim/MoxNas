#!/bin/bash

# MoxNAS Production Startup Script
# This script starts all MoxNAS services in production mode

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

warn() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

# Set working directory
cd /opt/moxnas

log "🚀 Starting MoxNAS Production Services..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    error "This script must be run as root"
    exit 1
fi

# Create required directories
log "📁 Creating required directories..."
mkdir -p /mnt/storage/{shares,users,ftp_users,datasets}
mkdir -p /var/log/moxnas
mkdir -p /run/moxnas
chown -R www-data:www-data /mnt/storage
success "Directories created"

# Start NAS services
log "🔧 Starting NAS services..."
systemctl start smbd nmbd nfs-kernel-server vsftpd
systemctl enable smbd nmbd nfs-kernel-server vsftpd
success "NAS services started"

# Start nginx
log "🌐 Starting nginx..."
systemctl start nginx
systemctl enable nginx
success "Nginx started"

# Activate Python virtual environment
log "🐍 Activating Python environment..."
source venv/bin/activate

# Run Django migrations
log "🗄️ Running database migrations..."
python backend/manage.py migrate --noinput
success "Migrations completed"

# Collect static files
log "📦 Collecting static files..."
python backend/manage.py collectstatic --noinput
success "Static files collected"

# Create initial services and data
log "⚡ Initializing services..."
python backend/manage.py shell -c "
from core.models import ServiceStatus
from django.contrib.auth import get_user_model

# Create service status entries
services = ['samba', 'nfs', 'ftp', 'ssh']
for service in services:
    ServiceStatus.objects.get_or_create(
        name=service,
        defaults={'enabled': True, 'status': 'running'}
    )

# Ensure admin user exists
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@moxnas.com', 'moxnas123')
    print('Admin user created')
else:
    print('Admin user already exists')
"
success "Services initialized"

# Start Django application with gunicorn
log "🦄 Starting Django application..."
pkill -f gunicorn || true  # Kill any existing gunicorn processes
gunicorn --bind 127.0.0.1:8000 \
         --workers 3 \
         --chdir backend \
         --daemon \
         --pid /run/moxnas/gunicorn.pid \
         --log-file /var/log/moxnas/gunicorn.log \
         --log-level info \
         moxnas.wsgi:application

# Wait for gunicorn to start
sleep 2

# Check if gunicorn is running
if pgrep -f gunicorn > /dev/null; then
    success "Django application started"
else
    error "Failed to start Django application"
    exit 1
fi

# Final service status check
log "🔍 Checking service status..."
services=("smbd" "nmbd" "nfs-server" "vsftpd" "nginx")
for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        success "$service is running"
    else
        warn "$service is not running"
    fi
done

# Check gunicorn
if pgrep -f gunicorn > /dev/null; then
    success "Django backend is running"
else
    error "Django backend is not running"
fi

# Get container IP
CONTAINER_IP=$(hostname -I | awk '{print $1}')

echo
success "🎉 MoxNAS Production Deployment Complete!"
echo
log "📍 Access Information:"
log "   Web Interface: http://$CONTAINER_IP"
log "   Admin Panel: http://$CONTAINER_IP/admin"
log "   API Base: http://$CONTAINER_IP/api"
log "   Default Login: admin / moxnas123"
echo
log "📋 Available Services:"
log "   ✅ SMB/CIFS File Sharing"
log "   ✅ NFS File Sharing" 
log "   ✅ FTP File Transfer"
log "   ✅ Web Management Interface"
log "   ✅ User & Group Management"
log "   ✅ Dataset & Share Management"
log "   ✅ Access Control Lists (ACLs)"
echo
log "📚 Service Management:"
log "   Start: systemctl start moxnas"
log "   Stop: systemctl stop moxnas"
log "   Status: systemctl status moxnas"
log "   Logs: journalctl -u moxnas -f"
echo
success "MoxNAS is ready for production use!"