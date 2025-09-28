#!/usr/bin/env bash

# MoxNAS LXC Container Creation Script
# This script should be run on the Proxmox host

set -euo pipefail

# Script configuration
SCRIPT_VERSION="2.0.0"
SCRIPT_NAME="MoxNAS"

# Colors for output
YW='\033[33m'
RD='\033[01;31m'
BL='\033[36m'
GN='\033[1;92m'
CL='\033[m'
BOLD='\033[1m'

# Default LXC configuration - Optimized for NAS workloads
DEFAULT_CTID="200"
DEFAULT_HOSTNAME="moxnas"
DEFAULT_CORES="4"
DEFAULT_MEMORY="4096"
DEFAULT_DISK_SIZE="20"
DEFAULT_BRIDGE="vmbr0"
DEFAULT_TEMPLATE="ubuntu-24.04-standard_24.04-2_amd64.tar.xz"
DEFAULT_STORAGE="local-lvm"

# Storage optimization settings
THIN_PROVISION="1"
PREALLOCATION="metadata"  # For faster allocation
DISCARD_SUPPORT="1"       # Enable TRIM/discard for SSDs
COMPRESS_LEVEL="6"        # Balance between compression and performance

# Function definitions
header_info() {
    cat << 'EOF'
    __  ___          _   ___   ___   _____
   /  |/  /___  _  _/ | / / | / __\ / ___/
  / /|_/ / __ \| |/_/  |/ /  |/ /_\  \__ \ 
 / /  / / /_/ />  </ /|  / /|  __/  ___/ /
/_/  /_/\____/_/|_/_/ |_/_/ |_/    /____/ 

Network Attached Storage for Proxmox LXC
Version: 2.0.0
EOF
}

msg_info() {
    echo -e "${BL}[INFO]${CL} $1"
}

msg_ok() {
    echo -e "${GN}[OK]${CL} $1"
}

msg_error() {
    echo -e "${RD}[ERROR]${CL} $1"
    exit 1
}

msg_warn() {
    echo -e "${YW}[WARN]${CL} $1"
}

# Cleanup function
cleanup() {
    if [ -n "${CTID:-}" ] && pct status $CTID >/dev/null 2>&1; then
        if [ "$(pct status $CTID | awk '{print $2}')" == "running" ]; then
            msg_warn "Stopping container $CTID due to error"
            pct stop $CTID >/dev/null 2>&1 || true
        fi
        if [ "${CLEANUP_ON_ERROR:-true}" == "true" ]; then
            msg_warn "Destroying container $CTID due to error"
            pct destroy $CTID >/dev/null 2>&1 || true
        fi
    fi
}

# Set trap for cleanup on error
trap cleanup ERR

# Validate Proxmox environment
check_proxmox() {
    if ! command -v pct >/dev/null 2>&1; then
        msg_error "This script must be run on a Proxmox VE host"
    fi
    
    if ! command -v pvesh >/dev/null 2>&1; then
        msg_error "Proxmox VE API tools not found"
    fi
    
    if [ $EUID -ne 0 ]; then
        msg_error "This script must be run as root"
    fi
    
    msg_ok "Proxmox VE environment validated"
}

# Get next available CT ID
get_next_ctid() {
    for ((i=200; i<=999; i++)); do
        if ! pct status $i >/dev/null 2>&1; then
            echo $i
            return
        fi
    done
    msg_error "No available container IDs found (200-999)"
}

# Validate container template
check_template() {
    local template_path="/var/lib/vz/template/cache/$DEFAULT_TEMPLATE"
    if [ ! -f "$template_path" ]; then
        msg_warn "Ubuntu 24.04 template not found, downloading..."
        if ! pveam download local $DEFAULT_TEMPLATE; then
            msg_error "Failed to download container template"
        fi
    fi
    msg_ok "Container template validated"
}

# Interactive configuration
interactive_config() {
    echo -e "\n${BOLD}=== MoxNAS Container Configuration ===${CL}"
    
    # Container ID
    while true; do
        read -p "Container ID [$DEFAULT_CTID]: " CTID
        CTID=${CTID:-$DEFAULT_CTID}
        if [[ "$CTID" =~ ^[0-9]+$ ]] && [ "$CTID" -ge 100 ] && [ "$CTID" -le 999 ]; then
            if ! pct status $CTID >/dev/null 2>&1; then
                break
            else
                echo "Container ID $CTID already exists"
            fi
        else
            echo "Invalid container ID (100-999)"
        fi
    done
    
    # Hostname
    read -p "Hostname [$DEFAULT_HOSTNAME]: " CT_HOSTNAME
    CT_HOSTNAME=${CT_HOSTNAME:-$DEFAULT_HOSTNAME}
    
    # Resources
    read -p "CPU Cores [$DEFAULT_CORES]: " CORES
    CORES=${CORES:-$DEFAULT_CORES}
    
    read -p "Memory MB [$DEFAULT_MEMORY]: " MEMORY
    MEMORY=${MEMORY:-$DEFAULT_MEMORY}
    
    read -p "Disk Size GB [$DEFAULT_DISK_SIZE]: " DISK_SIZE
    DISK_SIZE=${DISK_SIZE:-$DEFAULT_DISK_SIZE}
    
    # Network
    read -p "Network Bridge [$DEFAULT_BRIDGE]: " BRIDGE
    BRIDGE=${BRIDGE:-$DEFAULT_BRIDGE}
    
    # Storage
    read -p "Storage Pool [$DEFAULT_STORAGE]: " STORAGE
    STORAGE=${STORAGE:-$DEFAULT_STORAGE}
    
    # Password
    while true; do
        read -s -p "Root Password: " PASSWORD
        echo
        read -s -p "Confirm Password: " PASSWORD_CONFIRM
        echo
        if [ "$PASSWORD" = "$PASSWORD_CONFIRM" ] && [ -n "$PASSWORD" ]; then
            break
        else
            echo "Passwords do not match or are empty"
        fi
    done
    
    # Confirm configuration
    echo -e "\n${BOLD}=== Configuration Summary ===${CL}"
    echo "Container ID: $CTID"
    echo "Hostname: $CT_HOSTNAME"
    echo "CPU Cores: $CORES"
    echo "Memory: ${MEMORY}MB"
    echo "Disk Size: ${DISK_SIZE}GB"
    echo "Network Bridge: $BRIDGE"
    echo "Storage: $STORAGE"
    
    echo
    read -p "Continue with installation? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        msg_error "Installation cancelled"
    fi
}

# Create LXC container
create_container() {
    msg_info "Creating LXC container..."
    
    local template_path="local:vztmpl/$DEFAULT_TEMPLATE"
    
    # Create container with advanced features
    if ! pct create $CTID $template_path \
        --hostname $CT_HOSTNAME \
        --memory $MEMORY \
        --cores $CORES \
        --rootfs $STORAGE:$DISK_SIZE \
        --password "$PASSWORD" \
        --net0 name=eth0,bridge=$BRIDGE,ip=dhcp \
        --ostype ubuntu \
        --arch amd64 \
        --unprivileged 1 \
        --features nesting=1,keyctl=1 \
        --onboot 1 \
        --timezone host \
        --protection 0 \
        --start 0; then
        msg_error "Failed to create container"
    fi
    
    msg_ok "Container $CTID created successfully"
}

# Configure container for MoxNAS
configure_container() {
    msg_info "Configuring container for MoxNAS..."
    
    # Add additional mount points for storage
    pct set $CTID -mp0 /mnt/pve/storage,mp=/mnt/storage,backup=0 2>/dev/null || true
    pct set $CTID -mp1 /mnt/pve/backups,mp=/mnt/backups,backup=0 2>/dev/null || true
    
    # Set container options for NAS functionality
    pct set $CTID -swap 2048
    pct set $CTID -description "MoxNAS - Network Attached Storage Solution v$SCRIPT_VERSION
Created: $(date)
Web Interface: https://container-ip
Default Login: admin/moxnas1234

Features:
- Web-based NAS management
- SMB/NFS/FTP file sharing  
- RAID storage management
- Backup & restore
- System monitoring
- Multi-user support"
    
    msg_ok "Container configuration completed"
}

# Start container and run installation
install_moxnas() {
    msg_info "Starting container and installing MoxNAS..."
    
    # Start container
    if ! pct start $CTID; then
        msg_error "Failed to start container"
    fi
    
    # Wait for container to be ready
    msg_info "Waiting for container to initialize..."
    sleep 10
    
    # Check if container is accessible
    for i in {1..30}; do
        if pct exec $CTID -- systemctl is-active systemd-resolved >/dev/null 2>&1; then
            break
        fi
        if [ $i -eq 30 ]; then
            msg_error "Container failed to initialize properly"
        fi
        sleep 2
    done
    
    msg_ok "Container is ready"
    
    # Copy installation script to container
    msg_info "Copying installation files..."
    cat > /tmp/moxnas-install.sh << 'EOF_INSTALL'
#!/bin/bash
set -e

# Colors
YW='\033[33m'
RD='\033[01;31m'
BL='\033[36m'
GN='\033[1;92m'
CL='\033[m'

msg_info() { echo -e "${BL}[INFO]${CL} $1"; }
msg_ok() { echo -e "${GN}[OK]${CL} $1"; }
msg_error() { echo -e "${RD}[ERROR]${CL} $1"; exit 1; }

echo "🚀 Installing MoxNAS in LXC container..."

# Update system
msg_info "Updating system packages"
apt-get update && apt-get -y upgrade

# Install essential packages
msg_info "Installing essential packages"
apt-get -y install curl wget git sudo mc htop nano net-tools

# Install Python ecosystem
msg_info "Installing Python and development tools"
apt-get -y install python3 python3-pip python3-venv python3-dev build-essential

# Install database services
msg_info "Installing database services"
apt-get -y install postgresql postgresql-contrib redis-server

# Install web server
msg_info "Installing nginx web server"
apt-get -y install nginx

# Install file sharing services
msg_info "Installing file sharing services"
apt-get -y install nfs-kernel-server samba samba-common-bin vsftpd

# Install storage management tools
msg_info "Installing storage management tools"
apt-get -y install lvm2 mdadm smartmontools parted gdisk

# Install monitoring tools
msg_info "Installing monitoring tools"
apt-get -y install htop iotop lsof

# Create MoxNAS user and directory
msg_info "Creating MoxNAS user and application directory"
adduser --system --group --disabled-password --home /opt/moxnas --shell /bin/bash moxnas
mkdir -p /opt/moxnas
chown moxnas:moxnas /opt/moxnas

# Clone repository
msg_info "Downloading MoxNAS application"
cd /opt/moxnas
git clone https://github.com/Mezraniwassim/MoxNas.git .
chown -R moxnas:moxnas /opt/moxnas

# Setup Python environment  
msg_info "Setting up Python virtual environment"
sudo -u moxnas python3 -m venv venv
sudo -u moxnas bash -c 'source venv/bin/activate && pip install --upgrade pip setuptools wheel'
sudo -u moxnas bash -c 'source venv/bin/activate && pip install -r requirements.txt'

# Configure PostgreSQL
msg_info "Configuring PostgreSQL database"
systemctl start postgresql
systemctl enable postgresql

sudo -u postgres psql -c "CREATE USER moxnas WITH PASSWORD 'moxnas1234';"
sudo -u postgres psql -c "CREATE DATABASE moxnas_db OWNER moxnas;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE moxnas_db TO moxnas;"

# Configure Redis
msg_info "Configuring Redis cache"
systemctl start redis-server
systemctl enable redis-server

# Initialize database
msg_info "Initializing MoxNAS database"
cd /opt/moxnas
sudo -u moxnas bash -c 'export FLASK_ENV=production && source venv/bin/activate && python migrate.py upgrade'

# Create admin user
msg_info "Creating admin user"
sudo -u moxnas bash -c 'export FLASK_ENV=production && source venv/bin/activate && python -c "
from app import create_app, db
from app.models import User, UserRole
from werkzeug.security import generate_password_hash
import sys

app = create_app(\"production\")
with app.app_context():
    try:
        admin = User.query.filter_by(username=\"admin\").first()
        if not admin:
            admin = User(
                username=\"admin\",
                email=\"admin@moxnas.local\",
                first_name=\"System\",
                last_name=\"Administrator\",
                role=UserRole.ADMIN,
                is_active=True
            )
            admin.set_password(\"moxnas1234\")
            db.session.add(admin)
            db.session.commit()
            print(\"Admin user created successfully\")
        else:
            print(\"Admin user already exists\")
    except Exception as e:
        print(f\"Error creating admin user: {e}\")
        sys.exit(1)
"'

# Configure systemd services
msg_info "Setting up system services"

# MoxNAS main service
cat > /etc/systemd/system/moxnas.service << 'EOF'
[Unit]
Description=MoxNAS Web Application
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=exec
User=moxnas
Group=moxnas
WorkingDirectory=/opt/moxnas
Environment=FLASK_ENV=production
ExecStart=/opt/moxnas/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 wsgi:app
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

# MoxNAS worker service  
cat > /etc/systemd/system/moxnas-worker.service << 'EOF'
[Unit]
Description=MoxNAS Celery Worker
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=exec
User=moxnas
Group=moxnas
WorkingDirectory=/opt/moxnas
Environment=FLASK_ENV=production
ExecStart=/opt/moxnas/venv/bin/python celery_worker.py
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

# Configure nginx
msg_info "Configuring nginx reverse proxy"
cat > /etc/nginx/sites-available/moxnas << 'EOF'
server {
    listen 80;
    server_name _;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;

    ssl_certificate /etc/ssl/certs/moxnas.crt;
    ssl_certificate_key /etc/ssl/private/moxnas.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;

    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
    
    location /static {
        alias /opt/moxnas/app/static;
        expires 30d;
    }
}
EOF

# Generate self-signed SSL certificate
msg_info "Generating SSL certificate"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/moxnas.key \
    -out /etc/ssl/certs/moxnas.crt \
    -subj '/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas'

# Enable nginx site
ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Configure file sharing
msg_info "Configuring file sharing services"

# Create storage directories
mkdir -p /mnt/storage /mnt/backups
chmod 755 /mnt/storage /mnt/backups

# SMB configuration
cat >> /etc/samba/smb.conf << 'EOF'

[moxnas-storage]
    comment = MoxNAS Storage
    path = /mnt/storage
    browseable = yes
    writable = yes
    guest ok = no
    valid users = root
    create mask = 0755
    directory mask = 0755
EOF

# Set SMB password for root
(echo 'moxnas1234'; echo 'moxnas1234') | smbpasswd -a root

# NFS exports
echo '/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)' >> /etc/exports
echo '/mnt/backups *(rw,sync,no_subtree_check,no_root_squash)' >> /etc/exports

# Configure FTP
sed -i 's/#write_enable=YES/write_enable=YES/' /etc/vsftpd.conf
sed -i 's/#local_enable=YES/local_enable=YES/' /etc/vsftpd.conf

# Enable and start services
msg_info "Starting all services"
systemctl daemon-reload
systemctl enable postgresql redis-server nginx smbd nmbd nfs-kernel-server vsftpd
systemctl enable moxnas moxnas-worker

systemctl start postgresql redis-server
systemctl start nginx smbd nmbd nfs-kernel-server vsftpd  
systemctl start moxnas moxnas-worker

# Save credentials
echo 'Username: admin' > /opt/moxnas/.admin_credentials
echo 'Password: moxnas1234' >> /opt/moxnas/.admin_credentials
echo 'Database: moxnas_db' >> /opt/moxnas/.admin_credentials
echo 'DB Password: moxnas1234' >> /opt/moxnas/.admin_credentials

# Create test file
echo 'MoxNAS Storage Test - $(date)' > /mnt/storage/README.txt

# Cleanup
apt-get autoremove -y
apt-get autoclean

msg_ok "MoxNAS installation completed successfully!"

EOF_INSTALL

    # Copy and execute installation script
    pct push $CTID /tmp/moxnas-install.sh /tmp/moxnas-install.sh
    pct exec $CTID -- chmod +x /tmp/moxnas-install.sh
    
    msg_info "Running MoxNAS installation (this may take 10-15 minutes)..."
    if ! pct exec $CTID -- bash /tmp/moxnas-install.sh; then
        msg_error "MoxNAS installation failed"
    fi
    
    # Clean up installation script
    pct exec $CTID -- rm -f /tmp/moxnas-install.sh
    
    msg_ok "MoxNAS installation completed"
}

# Display final information
show_completion() {
    local container_ip
    container_ip=$(pct exec $CTID -- hostname -I | awk '{print $1}')
    
    echo -e "\n${BOLD}🎉 MoxNAS Installation Completed!${CL}"
    echo "=" * 50
    echo -e "${BOLD}Container Details:${CL}"
    echo "  Container ID: $CTID"
    echo "  Hostname: $CT_HOSTNAME" 
    echo "  IP Address: $container_ip"
    echo "  CPU Cores: $CORES"
    echo "  Memory: ${MEMORY}MB"
    echo "  Storage: ${DISK_SIZE}GB"
    echo
    echo -e "${BOLD}Access Information:${CL}"
    echo "  Web Interface: https://$container_ip"
    echo "  Username: admin"
    echo "  Password: moxnas1234"
    echo
    echo -e "${BOLD}File Sharing:${CL}"
    echo "  SMB/CIFS: //$container_ip/moxnas-storage"
    echo "  NFS: $container_ip:/mnt/storage"
    echo "  FTP: ftp://$container_ip"
    echo
    echo -e "${BOLD}Container Management:${CL}"
    echo "  Start: pct start $CTID"
    echo "  Stop: pct stop $CTID"
    echo "  Console: pct enter $CTID"
    echo "  Status: pct status $CTID"
    echo
    echo -e "${BOLD}Next Steps:${CL}"
    echo "  1. Access the web interface and change the default password"
    echo "  2. Configure storage pools and RAID arrays"
    echo "  3. Set up network shares and user accounts"
    echo "  4. Configure backup jobs and monitoring"
    echo "  5. Replace SSL certificate for production use"
    echo
    echo -e "${YW}⚠️  Important Security Notes:${CL}"
    echo "  - Change default passwords immediately"
    echo "  - Configure firewall rules as needed"
    echo "  - Set up proper SSL certificates"
    echo "  - Review and adjust file sharing permissions"
    echo
    echo -e "${GN}✅ MoxNAS is ready for use!${CL}"
}

# Main execution
main() {
    # Show header
    clear
    header_info
    echo
    
    # Validate environment
    check_proxmox
    check_template
    
    # Check for non-interactive mode
    if [[ "${1:-}" == "--auto" ]]; then
        # Auto mode with defaults
        CTID=$(get_next_ctid)
        CT_HOSTNAME=$DEFAULT_HOSTNAME
        CORES=$DEFAULT_CORES
        MEMORY=$DEFAULT_MEMORY
        DISK_SIZE=$DEFAULT_DISK_SIZE
        BRIDGE=$DEFAULT_BRIDGE
        STORAGE=$DEFAULT_STORAGE
        PASSWORD="moxnas1234"
        
        msg_info "Running in automatic mode with defaults"
    else
        # Interactive mode
        interactive_config
    fi
    
    # Create and configure container
    create_container
    configure_container
    install_moxnas
    
    # Disable cleanup on success
    trap - ERR
    
    # Show completion information
    show_completion
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "MoxNAS LXC Container Creation Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "Options:"
        echo "  --auto    Run with default settings (non-interactive)"
        echo "  --help    Show this help message"
        echo
        echo "Default Configuration:"
        echo "  Container ID: Next available (200+)"
        echo "  Hostname: $DEFAULT_HOSTNAME"
        echo "  CPU Cores: $DEFAULT_CORES"
        echo "  Memory: ${DEFAULT_MEMORY}MB"
        echo "  Disk: ${DEFAULT_DISK_SIZE}GB"
        echo "  Template: $DEFAULT_TEMPLATE"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
