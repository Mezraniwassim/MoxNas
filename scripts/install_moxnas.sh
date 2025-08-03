#!/bin/bash

# MoxNas Installation Script
# This script installs MoxNas in an LXC container on Proxmox
# Usage: ./install_moxnas.sh [container_id]

set -e

# Configuration
DEFAULT_CONTAINER_ID=200
CONTAINER_ID=${1:-$DEFAULT_CONTAINER_ID}
CONTAINER_HOSTNAME="moxnas-${CONTAINER_ID}"
CONTAINER_PASSWORD="moxnas123"
CONTAINER_MEMORY=3072
CONTAINER_CORES=2
CONTAINER_SWAP=1024
CONTAINER_STORAGE="local-lvm"
CONTAINER_TEMPLATE="ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
MOXNAS_REPO="https://github.com/Mezraniwassim/MoxNas.git"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        exit 1
    fi
}

# Check if running on Proxmox
check_proxmox() {
    if ! command -v pct &> /dev/null; then
        error "This script must be run on a Proxmox host"
        exit 1
    fi
}

# Check if container already exists
check_container_exists() {
    if pct list | grep -q "^$CONTAINER_ID "; then
        error "Container $CONTAINER_ID already exists"
        exit 1
    fi
}

# Test network connectivity (with optional ping bypass)
test_network() {
    local container_id=$1
    local max_attempts=30
    local attempt=1
    
    log "Testing network connectivity in container $container_id..."
    
    while [ $attempt -le $max_attempts ]; do
        if pct exec $container_id -- bash -c 'curl -s --connect-timeout 5 http://google.com &>/dev/null || wget -q --timeout=5 --tries=1 http://google.com -O /dev/null &>/dev/null'; then
            success "Network connectivity confirmed"
            return 0
        fi
        
        if [ $attempt -eq 5 ]; then
            warning "Ping test failed, but continuing installation (ICMP may be blocked by firewall)"
        fi
        
        log "Network test attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
        ((attempt++))
    done
    
    warning "Network connectivity could not be confirmed, but continuing installation"
    return 0
}

# Create LXC container
create_container() {
    log "Creating LXC container $CONTAINER_ID..."
    
    pct create $CONTAINER_ID local:vztmpl/$CONTAINER_TEMPLATE \
        --hostname $CONTAINER_HOSTNAME \
        --password $CONTAINER_PASSWORD \
        --memory $CONTAINER_MEMORY \
        --cores $CONTAINER_CORES \
        --swap $CONTAINER_SWAP \
        --storage $CONTAINER_STORAGE \
        --rootfs $CONTAINER_STORAGE:8 \
        --net0 name=eth0,bridge=vmbr0,ip=dhcp \
        --unprivileged 1 \
        --onboot 1 \
        --features nesting=1,keyctl=1 \
        --start 1
    
    success "Container $CONTAINER_ID created successfully"
}

# Wait for container to be ready
wait_for_container() {
    local container_id=$1
    local max_attempts=60
    local attempt=1
    
    log "Waiting for container $container_id to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if pct exec $container_id -- bash -c 'systemctl is-system-running --quiet || systemctl is-system-running | grep -q "degraded"' 2>/dev/null; then
            success "Container $container_id is ready"
            return 0
        fi
        
        log "Container startup attempt $attempt/$max_attempts, waiting 5 seconds..."
        sleep 5
        ((attempt++))
    done
    
    warning "Container may not be fully ready, but continuing installation"
    return 0
}

# Install dependencies in container
install_dependencies() {
    local container_id=$1
    
    log "Installing system dependencies..."
    
    pct exec $container_id -- bash -c "
        export DEBIAN_FRONTEND=noninteractive
        apt-get update
        apt-get install -y \
            python3 \
            python3-pip \
            python3-venv \
            nodejs \
            npm \
            git \
            curl \
            wget \
            nginx \
            supervisor \
            sqlite3 \
            locales \
            tzdata \
            openssh-server \
            vsftpd \
            nfs-kernel-server \
            samba \
            samba-common-bin \
            net-tools \
            htop \
            nano \
            sudo
        
        # Generate locales
        locale-gen en_US.UTF-8
        
        # Set timezone
        ln -sf /usr/share/zoneinfo/UTC /etc/localtime
        
        # Configure SSH
        systemctl enable ssh
        
        # Configure FTP
        systemctl enable vsftpd
        
        # Configure NFS
        systemctl enable nfs-kernel-server
        systemctl enable rpcbind
        
        # Configure Samba
        systemctl enable smbd
        systemctl enable nmbd
        
        # Create basic directories
        mkdir -p /srv/ftp
        mkdir -p /mnt/data
        mkdir -p /etc/moxnas
        
        # Set proper permissions
        chmod 755 /srv/ftp
        chmod 755 /mnt/data
    "
    
    success "System dependencies installed"
}

# Clone and setup MoxNas
setup_moxnas() {
    local container_id=$1
    
    log "Setting up MoxNas application..."
    
    pct exec $container_id -- bash -c "
        # Create application directory
        mkdir -p /opt/moxnas
        cd /opt/moxnas
        
        # Clone repository
        git clone $MOXNAS_REPO .
        
        # Setup Python virtual environment
        python3 -m venv venv
        source venv/bin/activate
        
        # Install Python dependencies
        pip install --upgrade pip
        pip install -r requirements.txt
        
        # Setup Django
        cd backend
        python manage.py migrate
        python manage.py collectstatic --noinput
        
        # Create superuser (optional)
        echo \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@moxnas.local', 'admin123') if not User.objects.filter(username='admin').exists() else None\" | python manage.py shell
        
        # Setup frontend with memory optimization
        cd ../frontend
        
        # Increase memory limit for Node.js build process
        export NODE_OPTIONS=\"--max-old-space-size=1536\"
        
        # Install with specific flags to reduce memory usage
        npm install --silent --no-audit --no-fund --prefer-offline
        
        # Build with optimizations for limited memory
        npm run build:prod --silent
        
        # Set permissions
        chown -R root:root /opt/moxnas
        chmod +x /opt/moxnas/scripts/*.sh 2>/dev/null || true
    "
    
    success "MoxNas application setup completed"
}

# Configure services
configure_services() {
    local container_id=$1
    
    log "Configuring system services..."
    
    # Create systemd service file with improved configuration
    pct exec $container_id -- bash -c "
        cat > /etc/systemd/system/moxnas.service << 'EOF'
[Unit]
Description=MoxNas Web Interface
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/opt/moxnas
Environment=PATH=/opt/moxnas/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/opt/moxnas/backend
Environment=DJANGO_SETTINGS_MODULE=moxnas.settings
Environment=GUNICORN_CMD_ARGS=\"--bind 0.0.0.0:8000 --workers 3 --chdir backend --timeout 120 --worker-class sync\"
ExecStartPre=/bin/sleep 10
ExecStart=/opt/moxnas/venv/bin/gunicorn moxnas.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStartSec=60
TimeoutStopSec=30
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        # Create startup script for reliability
        cat > /opt/moxnas/start_service.sh << 'EOF'
#!/bin/bash
cd /opt/moxnas
source venv/bin/activate
cd backend

# Ensure database is migrated
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Start gunicorn
exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 --worker-class sync --chdir /opt/moxnas/backend moxnas.wsgi:application
EOF

        chmod +x /opt/moxnas/start_service.sh

        # Update service to use startup script
        cat > /etc/systemd/system/moxnas.service << 'EOF'
[Unit]
Description=MoxNas Web Interface
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/moxnas
ExecStartPre=/bin/sleep 5
ExecStart=/opt/moxnas/start_service.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

        # Enable and start the service
        systemctl daemon-reload
        systemctl enable moxnas
        
        # Wait a moment then start
        sleep 3
        systemctl start moxnas
        
        # Wait and check status
        sleep 5
        systemctl status moxnas --no-pager
        
        # Configure NAS services
        
        # Configure Samba
        cat > /etc/samba/smb.conf << 'EOF'
[global]
    workgroup = WORKGROUP
    server string = %h server (Samba, MoxNas)
    log file = /var/log/samba/log.%m
    max log size = 1000
    logging = file
    panic action = /usr/share/samba/panic-action %d
    server role = standalone server
    obey pam restrictions = yes
    unix password sync = yes
    passwd program = /usr/bin/passwd %u
    passwd chat = *Enter\snew\s*\spassword:* %n\n *Retype\snew\s*\spassword:* %n\n *password\supdated\ssuccessfully* .
    pam password change = yes
    map to guest = bad user
    usershare allow guests = yes

[homes]
    comment = Home Directories
    browseable = no
    read only = no
    create mask = 0700
    directory mask = 0700
    valid users = %S

[printers]
    comment = All Printers
    browseable = no
    path = /var/spool/samba
    printable = yes
    guest ok = no
    read only = yes
    create mask = 0700

[print$]
    comment = Printer Drivers
    path = /var/lib/samba/printers
    browseable = yes
    read only = yes
    guest ok = no
EOF

        # Configure vsftpd
        cat > /etc/vsftpd.conf << 'EOF'
listen=NO
listen_ipv6=YES
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
chroot_local_user=YES
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
rsa_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
rsa_private_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
ssl_enable=NO
user_sub_token=\$USER
local_root=/srv/ftp/\$USER
userlist_enable=YES
userlist_file=/etc/vsftpd.userlist
userlist_deny=NO
EOF

        # Configure NFS
        cat > /etc/exports << 'EOF'
# /etc/exports: the access control list for filesystems which may be exported
#		to NFS clients.  See exports(5).
EOF

        # Start services
        systemctl restart smbd
        systemctl restart nmbd  
        systemctl restart vsftpd
        systemctl restart nfs-kernel-server
        systemctl restart rpcbind
        
        # Configure nginx (optional reverse proxy)
        cat > /etc/nginx/sites-available/moxnas << 'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /static/ {
        alias /opt/moxnas/backend/staticfiles/;
    }
}
EOF

        # Enable nginx site
        rm -f /etc/nginx/sites-enabled/default
        ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
        systemctl enable nginx
        systemctl restart nginx
    "
    
    success "System services configured"
}

# Get container IP address
get_container_ip() {
    local container_id=$1
    local ip_address
    
    # Wait for IP assignment
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        ip_address=$(pct exec $container_id -- hostname -I 2>/dev/null | awk '{print $1}' | tr -d '\n')
        
        if [[ $ip_address =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo $ip_address
            return 0
        fi
        
        log "Waiting for IP address assignment (attempt $attempt/$max_attempts)..."
        sleep 5
        ((attempt++))
    done
    
    return 1
}

# Display completion message
show_completion_message() {
    local container_id=$1
    local ip_address=$2
    
    echo
    success "============================================="
    success "MoxNas installation completed successfully!"
    success "============================================="
    echo
    log "Container ID: $container_id"
    log "Container Name: $CONTAINER_HOSTNAME"
    log "Default Password: $CONTAINER_PASSWORD"
    
    if [ -n "$ip_address" ]; then
        log "Container IP: $ip_address"
        log "Web Interface: http://$ip_address:8000"
        log "Admin Interface: http://$ip_address:8000/admin"
        log "Admin Credentials: admin / admin123"
    else
        warning "Could not determine container IP address"
        log "You can find the IP with: pct exec $container_id -- hostname -I"
    fi
    
    echo
    log "To manage the container:"
    log "  Start:   pct start $container_id"
    log "  Stop:    pct stop $container_id"
    log "  Enter:   pct enter $container_id"
    log "  Destroy: pct destroy $container_id"
    echo
    log "To check service status:"
    log "  pct exec $container_id -- systemctl status moxnas"
    echo
}

# Main installation function
main() {
    echo "MoxNas Installation Script"
    echo "=========================="
    echo
    
    # Pre-installation checks
    check_root
    check_proxmox
    check_container_exists
    
    log "Starting installation of MoxNas in container $CONTAINER_ID..."
    
    # Installation steps
    create_container
    wait_for_container $CONTAINER_ID
    test_network $CONTAINER_ID
    install_dependencies $CONTAINER_ID
    setup_moxnas $CONTAINER_ID
    configure_services $CONTAINER_ID
    
    # Get IP address and show completion message
    log "Getting container IP address..."
    IP_ADDRESS=$(get_container_ip $CONTAINER_ID)
    show_completion_message $CONTAINER_ID "$IP_ADDRESS"
}

# Trap errors and cleanup
trap 'error "Installation failed at line $LINENO. Check the logs above for details."' ERR

# Run main function
main "$@"