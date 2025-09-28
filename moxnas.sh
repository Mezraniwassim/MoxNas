#!/usr/bin/env bash
# MoxNAS Proxmox LXC Installation Script
# Copyright (c) 2024 MoxNAS Contributors
# Author: MoxNAS Team  
# License: MIT

set -euo pipefail

# Colors for output
YW='\033[33m'
RD='\033[01;31m'
BL='\033[36m'
GN='\033[1;92m'
CL='\033[m'
BOLD='\033[1m'

# App Default Values
APP="MoxNAS"
var_tags="nas;storage;samba;nfs;ftp;truenas"
var_cpu="4"
var_ram="4096"
var_disk="20"
var_os="debian"
var_version="12"
var_unprivileged="0"

# Default LXC configuration
DEFAULT_CTID=""
DEFAULT_HOSTNAME="moxnas"
DEFAULT_TEMPLATE="debian-12-standard_12.7-1_amd64.tar.zst"
DEFAULT_STORAGE="local-lvm"
DEFAULT_BRIDGE="vmbr0"

# Function definitions
msg_info() { echo -e "${BL}[INFO]${CL} $1"; }
msg_ok() { echo -e "${GN}[OK]${CL} $1"; }
msg_error() { echo -e "${RD}[ERROR]${CL} $1"; exit 1; }
msg_warn() { echo -e "${YW}[WARN]${CL} $1"; }

header_info() {
    clear
    cat << 'EOF'
    __  ___          _   ___   ___   _____
   /  |/  /___  _  _/ | / / | / __\ / ___/
  / /|_/ / __ \| |/_/  |/ /  |/ /_\  \__ \ 
 / /  / / /_/ />  </ /|  / /|  __/  ___/ /
/_/  /_/\____/_/|_/_/ |_/_/ |_/    /____/ 

Network Attached Storage for Proxmox LXC
Automated Installation Script
EOF
}

# Check Proxmox environment
check_proxmox() {
    if ! command -v pct >/dev/null 2>&1; then
        msg_error "This script must be run on a Proxmox VE host"
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

# Check if template exists
check_template() {
    # Check if the default template exists locally
    if ! pveam list local | grep -q "debian-12-standard_12.7-1_amd64.tar.zst"; then
        msg_error "Template debian-12-standard_12.7-1_amd64.tar.zst not found. Please download it first: pveam download local debian-12-standard_12.7-1_amd64.tar.zst"
    fi
    msg_ok "Container template ready: $DEFAULT_TEMPLATE"
}

# Create LXC container
create_container() {
    msg_info "Creating LXC container..."
    
    # Get next available CT ID
    if [ -z "$DEFAULT_CTID" ]; then
        DEFAULT_CTID=$(get_next_ctid)
    fi
    
    local template_path="local:vztmpl/$DEFAULT_TEMPLATE"
    
    # Create container
    if ! pct create $DEFAULT_CTID $template_path \
        --hostname $DEFAULT_HOSTNAME \
        --memory $var_ram \
        --cores $var_cpu \
        --rootfs $DEFAULT_STORAGE:$var_disk \
        --password "moxnas1234" \
        --net0 name=eth0,bridge=$DEFAULT_BRIDGE,ip=dhcp \
        --ostype debian \
        --arch amd64 \
        --unprivileged $var_unprivileged \
        --features nesting=1,keyctl=1 \
        --onboot 1 \
        --timezone host \
        --protection 0 \
        --start 0; then
        msg_error "Failed to create container"
    fi
    
    msg_ok "Container $DEFAULT_CTID created successfully"
    CTID=$DEFAULT_CTID
}

# Start container and wait for it to be ready
start_container() {
    msg_info "Starting container $CTID..."
    
    if ! pct start $CTID; then
        msg_error "Failed to start container"
    fi
    
    # Wait for container to be ready
    msg_info "Waiting for container to initialize..."
    sleep 15
    
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
}

# Install MoxNAS in container
install_moxnas() {
    msg_info "Installing MoxNAS in container $CTID..."
    
    # Copy GitHub installation script to container
    cat > /tmp/moxnas-container-install.sh << 'EOF_INSTALL'
#!/bin/bash
set -e

export DEBIAN_FRONTEND=noninteractive

# Update system
apt-get update && apt-get -y upgrade

# Install system packages
apt-get -y install curl wget git sudo mc htop nano net-tools
apt-get -y install python3 python3-pip python3-venv python3-dev build-essential
apt-get -y install postgresql postgresql-contrib redis-server nginx
apt-get -y install nfs-kernel-server samba samba-common-bin vsftpd
apt-get -y install lvm2 smartmontools parted

# Create MoxNAS user and directories
adduser --system --group --disabled-password --home /opt/moxnas --shell /bin/bash moxnas
mkdir -p /opt/moxnas /mnt/storage /mnt/backups
chown moxnas:moxnas /opt/moxnas
chmod 755 /mnt/storage /mnt/backups

# Clone MoxNAS from GitHub
cd /opt/moxnas
git clone https://github.com/Mezraniwassim/MoxNas.git .
chown -R moxnas:moxnas /opt/moxnas

# Setup Python environment
sudo -u moxnas python3 -m venv venv
sudo -u moxnas bash -c 'source venv/bin/activate && pip install --upgrade pip setuptools wheel'
sudo -u moxnas bash -c 'source venv/bin/activate && pip install -r requirements.txt'

# Configure PostgreSQL
systemctl start postgresql
systemctl enable postgresql
sudo -u postgres psql -c "CREATE USER moxnas WITH PASSWORD 'moxnas1234';"
sudo -u postgres psql -c "CREATE DATABASE moxnas_db OWNER moxnas;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE moxnas_db TO moxnas;"

# Configure Redis
systemctl start redis-server
systemctl enable redis-server
echo "requirepass moxnas1234" >> /etc/redis/redis.conf
systemctl restart redis-server

# Create environment file
cat > /opt/moxnas/.env << 'EOF'
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql://moxnas:moxnas1234@localhost/moxnas_db
REDIS_URL=redis://:moxnas1234@localhost:6379/0
CELERY_BROKER_URL=redis://:moxnas1234@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:moxnas1234@localhost:6379/0
FLASK_ENV=production
FLASK_CONFIG=production
MOXNAS_STORAGE_ROOT=/mnt/storage
MOXNAS_BACKUP_ROOT=/mnt/backups
EOF
chown moxnas:moxnas /opt/moxnas/.env

# Initialize database
cd /opt/moxnas
sudo -u moxnas bash -c 'source venv/bin/activate && source .env && python migrate.py upgrade'

# Create admin user
sudo -u moxnas bash -c 'source venv/bin/activate && source .env && python -c "
from app import create_app, db
from app.models import User, UserRole
import sys

app = create_app(\"production\")
with app.app_context():
    try:
        # Delete existing admin if exists
        existing_admin = User.query.filter_by(username=\"admin\").first()
        if existing_admin:
            db.session.delete(existing_admin)
            db.session.commit()
        
        # Create new admin user
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
    except Exception as e:
        print(f\"Error creating admin user: {e}\")
        sys.exit(1)
"'

# Configure systemd services
cat > /etc/systemd/system/moxnas.service << 'EOF'
[Unit]
Description=MoxNAS Web Application
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/moxnas
Environment=FLASK_ENV=production
Environment=FLASK_CONFIG=production
ExecStart=/opt/moxnas/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 wsgi:app
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=false
NoNewPrivileges=no
ProtectSystem=false
ProtectHome=false

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/moxnas-worker.service << 'EOF'
[Unit]
Description=MoxNAS Celery Worker
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/moxnas
Environment=FLASK_ENV=production
Environment=FLASK_CONFIG=production
ExecStart=/opt/moxnas/venv/bin/python celery_worker.py
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30
PrivateTmp=false
NoNewPrivileges=no
ProtectSystem=false
ProtectHome=false

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
cat > /etc/nginx/sites-available/moxnas << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name _;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name _;

    ssl_certificate /etc/ssl/certs/moxnas.crt;
    ssl_certificate_key /etc/ssl/private/moxnas.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Generate SSL certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/moxnas.key \
    -out /etc/ssl/certs/moxnas.crt \
    -subj '/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas' 2>/dev/null

# Enable Nginx site
ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Configure file sharing
mkdir -p /mnt/storage /mnt/backups

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

# Enable and start all services
systemctl daemon-reload
systemctl enable postgresql redis-server nginx smbd nmbd nfs-kernel-server vsftpd
systemctl enable moxnas moxnas-worker

# Start services
systemctl start postgresql redis-server
systemctl restart nginx
systemctl start smbd nmbd nfs-kernel-server vsftpd
systemctl start moxnas moxnas-worker

# Save credentials
cat > /opt/moxnas/.admin_credentials << 'EOF'
Installation completed: $(date)
Web Interface: https://localhost
Username: admin
Password: moxnas1234

Database: moxnas_db
DB User: moxnas
DB Password: moxnas1234

SMB Share: //localhost/moxnas-storage
NFS Share: localhost:/mnt/storage
FTP: ftp://localhost
EOF

# Create test data
echo 'MoxNAS Storage Test - $(date)' > /mnt/storage/README.txt
echo 'Welcome to MoxNAS - Your Network Attached Storage Solution' > /mnt/storage/welcome.txt

# Cleanup
apt-get autoremove -y
apt-get autoclean

echo 'Installation completed successfully!'
EOF_INSTALL

    # Copy and execute installation script
    pct push $CTID /tmp/moxnas-container-install.sh /tmp/moxnas-container-install.sh
    pct exec $CTID -- chmod +x /tmp/moxnas-container-install.sh
    
    msg_info "Running MoxNAS installation (this may take 10-15 minutes)..."
    if ! pct exec $CTID -- bash /tmp/moxnas-container-install.sh; then
        msg_error "MoxNAS installation failed"
    fi
    
    # Clean up installation script
    pct exec $CTID -- rm -f /tmp/moxnas-container-install.sh
    rm -f /tmp/moxnas-container-install.sh
    
    msg_ok "MoxNAS installation completed"
}

# Display final information
show_completion() {
    local container_ip
    container_ip=$(pct exec $CTID -- hostname -I | awk '{print $1}')
    
    echo -e "\n${BOLD}🎉 MoxNAS Installation Completed Successfully!${CL}"
    echo "================================================================"
    echo -e "${BOLD}Container Details:${CL}"
    echo "  Container ID: $CTID"
    echo "  Hostname: $DEFAULT_HOSTNAME" 
    echo "  IP Address: $container_ip"
    echo "  CPU Cores: $var_cpu"
    echo "  Memory: ${var_ram}MB"
    echo "  Storage: ${var_disk}GB"
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
    header_info
    echo
    
    # Validate environment
    check_proxmox
    check_template
    
    # Create and configure container
    create_container
    start_container
    install_moxnas
    
    # Show completion information
    show_completion
}

# Run main function
main "$@"