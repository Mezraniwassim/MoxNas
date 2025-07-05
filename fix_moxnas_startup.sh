#!/bin/bash
#
# MoxNAS Startup Fix Script
# Fixes common startup and service configuration issues
#

set -e

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

# Configuration
CONTAINER_ID=${1:-200}
MOXNAS_PATH="/opt/moxnas"

fix_moxnas_startup() {
    log_info "Fixing MoxNAS startup issues in container $CONTAINER_ID..."
    
    # Fix 1: Ensure all required directories exist
    pct exec "$CONTAINER_ID" -- bash -c "
        mkdir -p /mnt/storage /etc/moxnas /var/log/moxnas /var/run/vsftpd/empty
        chmod 755 /mnt/storage /etc/moxnas /var/log/moxnas /var/run/vsftpd/empty
        chown root:root /mnt/storage /etc/moxnas /var/log/moxnas
    "
    
    # Fix 2: Stop any running gunicorn processes
    pct exec "$CONTAINER_ID" -- bash -c "
        pkill -f gunicorn || true
        sleep 3
    "
    
    # Fix 3: Fix Django database and run migrations
    pct exec "$CONTAINER_ID" -- bash -c "
        cd $MOXNAS_PATH
        source venv/bin/activate
        cd backend
        
        # Fix database permissions
        chmod 664 db.sqlite3 2>/dev/null || true
        
        # Run migrations
        python manage.py migrate --run-syncdb || true
        
        # Initialize services
        python manage.py shell -c \"
from core.models import ServiceStatus
services = [('smb', 445), ('nfs', 2049), ('ftp', 21), ('ssh', 22), ('snmp', 161), ('iscsi', 3260)]
for name, port in services:
    ServiceStatus.objects.get_or_create(name=name, defaults={'port': port, 'status': 'stopped'})
print('Services initialized')
\" || true
        
        # Collect static files
        python manage.py collectstatic --noinput || true
    "
    
    # Fix 4: Configure NFS exports properly
    pct exec "$CONTAINER_ID" -- bash -c "
        # Fix NFS exports
        echo '/mnt/storage *(rw,sync,no_subtree_check,no_root_squash,insecure)' > /etc/exports
        chmod 644 /etc/exports
        exportfs -ra || true
        systemctl restart nfs-kernel-server || true
    "
    
    # Fix 5: Configure Samba properly  
    pct exec "$CONTAINER_ID" -- bash -c "
        # Backup original samba config
        cp /etc/samba/smb.conf /etc/samba/smb.conf.backup || true
        
        # Create proper samba config
        cat > /etc/samba/smb.conf << 'EOF'
[global]
    workgroup = WORKGROUP
    server string = MoxNAS
    security = user
    map to guest = Bad User
    dns proxy = no
    log file = /var/log/samba/%m.log
    max log size = 1000
    
[moxnas-share]
    path = /mnt/storage
    browseable = yes
    writable = yes
    guest ok = yes
    read only = no
    create mask = 0664
    directory mask = 0775
    force create mode = 0664
    force directory mode = 0775
EOF
        
        # Test and restart samba
        testparm -s || true
        systemctl restart smbd nmbd || true
    "
    
    # Fix 6: Configure FTP properly
    pct exec "$CONTAINER_ID" -- bash -c "
        # Backup original FTP config
        cp /etc/vsftpd.conf /etc/vsftpd.conf.backup || true
        
        # Create proper FTP config
        cat >> /etc/vsftpd.conf << 'EOF'

# MoxNAS FTP Configuration
anonymous_enable=YES
local_enable=YES
write_enable=YES
anon_upload_enable=YES
anon_mkdir_write_enable=YES
anon_other_write_enable=YES
anon_root=/mnt/storage
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=50000
seccomp_sandbox=NO
allow_writeable_chroot=YES
listen=YES
listen_ipv6=NO
chroot_local_user=NO
secure_chroot_dir=/var/run/vsftpd/empty
EOF
        
        # Restart FTP
        systemctl restart vsftpd || true
    "
    
    # Fix 7: Start MoxNAS web service
    pct exec "$CONTAINER_ID" -- bash -c "
        cd $MOXNAS_PATH
        source venv/bin/activate
        cd backend
        
        # Start gunicorn with optimized settings
        gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 60 \
                 --access-logfile /var/log/moxnas/access.log \
                 --error-logfile /var/log/moxnas/error.log \
                 --daemon moxnas.wsgi:application || {
            echo 'Gunicorn start failed, trying simple mode...'
            gunicorn --bind 0.0.0.0:8000 --workers 1 --daemon moxnas.wsgi:application
        }
    "
    
    # Fix 8: Create startup script for auto-restart
    pct exec "$CONTAINER_ID" -- bash -c "
        cat > /usr/local/bin/start-moxnas.sh << 'EOF'
#!/bin/bash
cd /opt/moxnas
source venv/bin/activate
cd backend

# Kill any existing gunicorn
pkill -f gunicorn || true
sleep 2

# Start gunicorn
gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 60 \
         --access-logfile /var/log/moxnas/access.log \
         --error-logfile /var/log/moxnas/error.log \
         --daemon moxnas.wsgi:application
EOF
        chmod +x /usr/local/bin/start-moxnas.sh
        
        # Add to rc.local for auto-start
        if ! grep -q 'start-moxnas.sh' /etc/rc.local 2>/dev/null; then
            echo '/usr/local/bin/start-moxnas.sh' >> /etc/rc.local
        fi
    "
    
    # Fix 9: Verify services are running
    sleep 5
    
    log_info "Verifying services..."
    
    # Check gunicorn
    if pct exec "$CONTAINER_ID" -- ps aux | grep -q "gunicorn.*8000"; then
        log_success "✅ MoxNAS web interface is running"
    else
        log_warning "⚠️ MoxNAS web interface failed to start"
    fi
    
    # Check Samba
    if pct exec "$CONTAINER_ID" -- systemctl is-active smbd &>/dev/null; then
        log_success "✅ Samba service is running"
    else
        log_warning "⚠️ Samba service is not running"
    fi
    
    # Check NFS
    if pct exec "$CONTAINER_ID" -- systemctl is-active nfs-kernel-server &>/dev/null; then
        log_success "✅ NFS service is running"
    else
        log_warning "⚠️ NFS service is not running"
    fi
    
    # Check FTP
    if pct exec "$CONTAINER_ID" -- systemctl is-active vsftpd &>/dev/null; then
        log_success "✅ FTP service is running"
    else
        log_warning "⚠️ FTP service is not running"
    fi
    
    # Get container IP
    CONTAINER_IP=$(pct exec "$CONTAINER_ID" -- hostname -I | awk '{print $1}')
    
    log_success "MoxNAS startup fixes completed!"
    echo ""
    echo "🌐 Access MoxNAS at: http://$CONTAINER_IP:8000"
    echo "📂 SMB Share: //$CONTAINER_IP/moxnas-share"
    echo "📁 NFS Export: $CONTAINER_IP:/mnt/storage"
    echo "🔗 FTP: ftp://$CONTAINER_IP"
    echo ""
    echo "🔧 Troubleshooting commands:"
    echo "   Manual start: pct exec $CONTAINER_ID -- /usr/local/bin/start-moxnas.sh"
    echo "   Check logs: pct exec $CONTAINER_ID -- tail -f /var/log/moxnas/error.log"
    echo "   Container shell: pct enter $CONTAINER_ID"
}

# Main execution
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [container_id]"
    echo "Fix MoxNAS startup issues in LXC container"
    echo "Default container ID: 200"
    exit 0
fi

fix_moxnas_startup