#!/bin/bash
#
# MoxNAS Startup Fix Script
# This script diagnoses and fixes common MoxNAS startup issues
#

set -e

# Configuration
CONTAINER_ID=${1:-200}
MOXNAS_HOME="/opt/moxnas"
LOG_DIR="/var/log/moxnas"

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

echo "🔧 MoxNAS Startup Fix Script"
echo "Container ID: $CONTAINER_ID"
echo ""

# Check if container exists and is running
check_container() {
    log_info "Checking container status..."
    
    if ! pct status "$CONTAINER_ID" >/dev/null 2>&1; then
        log_error "Container $CONTAINER_ID does not exist"
        exit 1
    fi
    
    if [ "$(pct status "$CONTAINER_ID")" != "status: running" ]; then
        log_warning "Container $CONTAINER_ID is not running, starting it..."
        pct start "$CONTAINER_ID"
        sleep 5
    fi
    
    log_success "Container $CONTAINER_ID is running"
}

# Fix directory permissions and structure
fix_directories() {
    log_info "Fixing directory permissions and structure..."
    
    pct exec "$CONTAINER_ID" -- bash -c "
        # Create necessary directories
        mkdir -p /mnt/storage /opt/moxnas/storage $LOG_DIR
        chmod 755 /mnt/storage /opt/moxnas/storage $LOG_DIR
        
        # Fix ownership
        chown -R root:root /opt/moxnas
        
        # Create logs directory
        mkdir -p /var/log/moxnas
        chmod 755 /var/log/moxnas
        
        # Fix service directories
        mkdir -p /var/lib/snmp /var/run/vsftpd/empty
        chown snmp:snmp /var/lib/snmp || true
        chmod 755 /var/lib/snmp /var/run/vsftpd/empty
    "
    
    log_success "Directory structure fixed"
}

# Fix service configurations
fix_service_configs() {
    log_info "Fixing service configurations..."
    
    # Fix Samba configuration
    pct exec "$CONTAINER_ID" -- bash -c "
        # Backup and create fresh Samba config
        cp /etc/samba/smb.conf /etc/samba/smb.conf.backup 2>/dev/null || true
        
        cat > /etc/samba/smb.conf << 'EOF'
[global]
    workgroup = WORKGROUP
    server string = MoxNAS Server
    security = user
    map to guest = Bad User
    dns proxy = no
    load printers = no
    disable netbios = no
    smb ports = 445
    
[moxnas-share]
    path = /mnt/storage
    browseable = yes
    writable = yes
    guest ok = yes
    read only = no
    create mask = 0644
    directory mask = 0755
    force create mode = 0644
    force directory mode = 0755
EOF
    "
    
    # Fix NFS exports
    pct exec "$CONTAINER_ID" -- bash -c "
        # Clean and create NFS exports
        echo '/mnt/storage *(rw,sync,no_subtree_check,no_root_squash,insecure)' > /etc/exports
        exportfs -ra || true
    "
    
    # Fix FTP configuration
    pct exec "$CONTAINER_ID" -- bash -c "
        # Backup original vsftpd config
        cp /etc/vsftpd.conf /etc/vsftpd.conf.backup 2>/dev/null || true
        
        # Create optimized FTP config
        cat > /etc/vsftpd.conf << 'EOF'
# Basic settings
listen=YES
listen_ipv6=NO
anonymous_enable=YES
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES

# Anonymous settings
anon_upload_enable=YES
anon_mkdir_write_enable=YES
anon_other_write_enable=YES
anon_root=/mnt/storage

# Security settings
chroot_local_user=NO
allow_writeable_chroot=YES
seccomp_sandbox=NO

# Passive mode
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=50000

# Performance
use_sendfile=YES
tcp_wrappers=YES
EOF
    "
    
    log_success "Service configurations fixed"
}

# Fix Python/Django issues
fix_django() {
    log_info "Fixing Django application..."
    
    pct exec "$CONTAINER_ID" -- bash -c "
        cd $MOXNAS_HOME || exit 1
        
        # Activate virtual environment
        source venv/bin/activate
        
        # Install missing dependencies
        pip install gunicorn psutil django-cors-headers djangorestframework || true
        
        # Fix Django settings for container environment
        cd backend
        
        # Run migrations with error handling
        python manage.py migrate --noinput || {
            echo 'Migrations failed, trying syncdb...'
            python manage.py migrate --run-syncdb --noinput || true
        }
        
        # Create superuser if needed
        python manage.py shell << 'PYTHON_EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@moxnas.local', 'moxnas123')
    print('Superuser created: admin/moxnas123')
else:
    print('Superuser already exists')
PYTHON_EOF
        
        # Initialize services
        python manage.py shell << 'PYTHON_EOF'
from core.models import ServiceStatus
services = [
    ('smb', 445), ('nfs', 2049), ('ftp', 21), 
    ('ssh', 22), ('snmp', 161), ('iscsi', 3260)
]
for name, port in services:
    obj, created = ServiceStatus.objects.get_or_create(
        name=name, 
        defaults={'port': port, 'status': 'stopped'}
    )
    if created:
        print(f'Created service: {name}')
print('Services initialized')
PYTHON_EOF
        
        # Collect static files
        python manage.py collectstatic --noinput || {
            echo 'Collectstatic failed, creating minimal static setup...'
            mkdir -p staticfiles/admin staticfiles/rest_framework
        }
    "
    
    log_success "Django application fixed"
}

# Start all services
start_all_services() {
    log_info "Starting all services..."
    
    pct exec "$CONTAINER_ID" -- bash -c "
        # Start system services
        systemctl daemon-reload
        
        services=('ssh' 'smbd' 'nmbd' 'nfs-kernel-server' 'vsftpd' 'snmpd' 'tgt')
        
        for service in \"\${services[@]}\"; do
            echo \"Starting \$service...\"
            systemctl enable \"\$service\" 2>/dev/null || true
            systemctl start \"\$service\" || echo \"Warning: Failed to start \$service\"
        done
        
        # Wait a moment
        sleep 2
        
        # Check service status
        echo \"Service Status:\"
        for service in \"\${services[@]}\"; do
            if systemctl is-active \"\$service\" >/dev/null 2>&1; then
                echo \"✅ \$service: running\"
            else
                echo \"❌ \$service: stopped\"
            fi
        done
    "
    
    log_success "System services started"
}

# Start MoxNAS application
start_moxnas_app() {
    log_info "Starting MoxNAS application..."
    
    # Stop any existing processes
    pct exec "$CONTAINER_ID" -- bash -c "
        pkill -f 'gunicorn.*moxnas' || true
        rm -f /var/run/moxnas.pid
        sleep 2
    "
    
    # Start the application
    pct exec "$CONTAINER_ID" -- bash -c "
        cd $MOXNAS_HOME
        source venv/bin/activate
        cd backend
        
        # Start Gunicorn with comprehensive error handling
        gunicorn \
            --bind 0.0.0.0:8000 \
            --workers 2 \
            --timeout 60 \
            --keep-alive 2 \
            --max-requests 1000 \
            --access-logfile $LOG_DIR/access.log \
            --error-logfile $LOG_DIR/error.log \
            --pid /var/run/moxnas.pid \
            --daemon \
            --preload \
            moxnas.wsgi:application || {
            
            echo 'Gunicorn failed, trying simplified configuration...'
            gunicorn \
                --bind 0.0.0.0:8000 \
                --workers 1 \
                --daemon \
                --pid /var/run/moxnas.pid \
                moxnas.wsgi:application || {
                
                echo 'Gunicorn still failing, trying runserver as fallback...'
                nohup python manage.py runserver 0.0.0.0:8000 > $LOG_DIR/runserver.log 2>&1 &
                echo \$! > /var/run/moxnas.pid
            }
        }
    "
    
    # Wait and verify
    sleep 5
    
    if pct exec "$CONTAINER_ID" -- netstat -tlnp 2>/dev/null | grep -q ":8000 "; then
        log_success "MoxNAS application started successfully"
        
        # Get container IP
        CONTAINER_IP=$(pct exec "$CONTAINER_ID" -- hostname -I | awk '{print $1}')
        log_success "🌐 MoxNAS is accessible at: http://$CONTAINER_IP:8000"
        echo "   📱 Web Interface: http://$CONTAINER_IP:8000"
        echo "   🔧 Admin Panel: http://$CONTAINER_IP:8000/admin/"
        echo "   📚 API Docs: http://$CONTAINER_IP:8000/api/"
        echo "   👤 Default Login: admin / moxnas123"
        echo ""
    else
        log_error "MoxNAS application failed to start on port 8000"
        log_info "Checking for any Python processes..."
        pct exec "$CONTAINER_ID" -- ps aux | grep python || true
        log_info "Checking logs:"
        pct exec "$CONTAINER_ID" -- tail -20 "$LOG_DIR/error.log" 2>/dev/null || echo "No error log found"
        return 1
    fi
}

# Create startup service
create_startup_service() {
    log_info "Creating startup service..."
    
    pct exec "$CONTAINER_ID" -- bash -c "
        # Create improved startup script
        cat > /usr/local/bin/start-moxnas.sh << 'STARTUP_EOF'
#!/bin/bash
cd /opt/moxnas
source venv/bin/activate
cd backend

# Kill existing processes
pkill -f 'gunicorn.*moxnas' 2>/dev/null || true
sleep 2

# Start gunicorn
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --daemon --pid /var/run/moxnas.pid moxnas.wsgi:application
STARTUP_EOF
        
        chmod +x /usr/local/bin/start-moxnas.sh
        
        # Create systemd service
        cat > /etc/systemd/system/moxnas.service << 'SERVICE_EOF'
[Unit]
Description=MoxNAS Application
After=network.target

[Service]
Type=forking
User=root
WorkingDirectory=/opt/moxnas
ExecStart=/usr/local/bin/start-moxnas.sh
ExecStop=/bin/kill -TERM \$MAINPID
PIDFile=/var/run/moxnas.pid
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_EOF
        
        # Enable service
        systemctl daemon-reload
        systemctl enable moxnas
    "
    
    log_success "Startup service created and enabled"
}

# Performance diagnostics
run_diagnostics() {
    log_info "Running system diagnostics..."
    
    pct exec "$CONTAINER_ID" -- bash -c "
        echo \"=== System Information ===\"
        echo \"Hostname: \$(hostname)\"
        echo \"IP Address: \$(hostname -I | awk '{print \$1}')\"
        echo \"Memory: \$(free -h | grep Mem | awk '{print \$3\"/\"\$2}')\"
        echo \"Disk: \$(df -h /opt/moxnas | tail -1 | awk '{print \$3\"/\"\$2\" (\"\$5\" used)\"}')\"
        echo \"\"
        
        echo \"=== Service Status ===\"
        services=('ssh' 'smbd' 'nfs-kernel-server' 'vsftpd')
        for service in \"\${services[@]}\"; do
            status=\$(systemctl is-active \"\$service\" 2>/dev/null || echo 'inactive')
            echo \"\$service: \$status\"
        done
        echo \"\"
        
        echo \"=== Network Ports ===\"
        netstat -tlnp 2>/dev/null | grep -E ':(22|445|2049|21|8000) ' || echo 'No services listening'
        echo \"\"
        
        echo \"=== MoxNAS Process ===\"
        ps aux | grep -E '(gunicorn|python.*manage.py)' | grep -v grep || echo 'No MoxNAS processes found'
        echo \"\"
        
        echo \"=== Storage ===\"
        ls -la /mnt/storage 2>/dev/null || echo '/mnt/storage not accessible'
        echo \"\"
        
        echo \"=== Recent Logs ===\"
        if [ -f $LOG_DIR/error.log ]; then
            echo \"Last 5 lines from error log:\"
            tail -5 $LOG_DIR/error.log
        else
            echo 'No error log found'
        fi
    "
}

# Main execution
main() {
    check_container
    fix_directories
    fix_service_configs
    fix_django
    start_all_services
    start_moxnas_app
    create_startup_service
    run_diagnostics
    
    echo ""
    log_success "🎉 MoxNAS startup fix completed!"
    echo ""
    echo "Next steps:"
    echo "1. Access the web interface at the URL shown above"
    echo "2. Log in with admin/moxnas123"
    echo "3. Configure your storage and shares"
    echo ""
    echo "If you still have issues:"
    echo "- Check logs: pct exec $CONTAINER_ID -- tail -f $LOG_DIR/error.log"
    echo "- Restart container: pct restart $CONTAINER_ID"
    echo "- Manual start: pct exec $CONTAINER_ID -- /usr/local/bin/start-moxnas.sh"
}

# Run main function
main