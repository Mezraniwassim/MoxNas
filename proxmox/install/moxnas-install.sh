#!/usr/bin/env bash

# Copyright (c) 2021-2025 community-scripts ORG
# Author: MoxNAS Contributors  
# License: MIT | https://github.com/community-scripts/ProxmoxVE/raw/main/LICENSE
# Source: https://github.com/Mezraniwassim/MoxNas

set -euo pipefail

# Colors for output  
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
msg_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

msg_ok() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

msg_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
MOXNAS_VERSION="1.0.0"
INSTALL_DIR="/opt/moxnas"
WEB_DIR="/var/www/moxnas"
CONFIG_DIR="/etc/moxnas"
LOG_DIR="/var/log/moxnas"

# Main installation function
main() {
    msg_info "Starting MoxNAS installation..."
    
    # System update
    update_system
    
    # Install dependencies
    install_dependencies
    
    # Install Hugo
    install_hugo
    
    # Setup directories
    setup_directories
    
    # Install MoxNAS
    install_moxnas
    
    # Configure services
    configure_nginx
    configure_nas_services
    configure_systemd
    
    # Setup defaults
    setup_defaults
    
    # Start services
    start_services
    
    # Cleanup
    cleanup
    
    msg_ok "MoxNAS installation completed successfully!"
    
    # Write version file
    echo "$MOXNAS_VERSION" > /opt/MoxNAS_version.txt
}

update_system() {
    msg_info "Updating system packages..."
    apt-get update -qq >/dev/null 2>&1
    apt-get upgrade -y -qq >/dev/null 2>&1
}

install_dependencies() {
    msg_info "Installing dependencies..."
    
    # Core dependencies
    apt-get install -y -qq \
        curl \
        wget \
        unzip \
        git \
        nginx \
        python3 \
        python3-pip \
        python3-venv \
        samba \
        nfs-kernel-server \
        vsftpd \
        sudo \
        ca-certificates >/dev/null 2>&1
    
    # Python packages
    pip3 install --quiet --upgrade pip >/dev/null 2>&1
    pip3 install --quiet \
        aiohttp \
        aiofiles \
        psutil \
        jinja2 >/dev/null 2>&1
}

install_hugo() {
    msg_info "Installing Hugo static site generator..."
    
    HUGO_VERSION="0.119.0"
    HUGO_URL="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_linux-amd64.tar.gz"
    
    cd /tmp
    wget -q "$HUGO_URL" -O hugo.tar.gz
    tar -xzf hugo.tar.gz
    mv hugo /usr/local/bin/
    chmod +x /usr/local/bin/hugo
    rm -f hugo.tar.gz
    
    if ! hugo version >/dev/null 2>&1; then
        msg_error "Hugo installation failed"
        exit 1
    fi
    
    msg_ok "Hugo installed successfully"
}

setup_directories() {
    msg_info "Setting up directories..."
    
    # Create directories
    mkdir -p "$INSTALL_DIR"/{api,scripts,config}
    mkdir -p "$WEB_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p /mnt/shares/{public,ftp}
    
    # Set permissions
    chown -R root:root "$INSTALL_DIR"
    chown -R www-data:www-data "$WEB_DIR"
    chmod 755 /mnt/shares
    chmod 777 /mnt/shares/public /mnt/shares/ftp
    chown nobody:nogroup /mnt/shares/public /mnt/shares/ftp
}

install_moxnas() {
    msg_info "Installing MoxNAS application..."
    
    # Download and extract MoxNAS
    cd /tmp
    wget -q https://github.com/Mezraniwassim/MoxNas/archive/master.zip -O moxnas.zip
    unzip -q moxnas.zip
    cd MoxNas-master
    
    # Copy files
    cp api-server.py "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/api-server.py"
    
    # Copy scripts
    cp -r scripts/* "$INSTALL_DIR/scripts/" 2>/dev/null || true
    find "$INSTALL_DIR/scripts" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
    
    # Copy config templates
    cp -r config/* "$INSTALL_DIR/config/" 2>/dev/null || true
    
    # Build Hugo site
    if [[ -f "config.yaml" ]]; then
        hugo --destination "$WEB_DIR"
        msg_ok "Hugo site built successfully"
    else
        # Create minimal site
        mkdir -p "$WEB_DIR"
        cat > "$WEB_DIR/index.html" << 'EOF'
<!DOCTYPE html>
<html>
<head><title>MoxNAS</title></head>
<body><h1>MoxNAS - Loading...</h1><script>window.location.href='/dashboard';</script></body>
</html>
EOF
    fi
    
    # Cleanup
    cd /
    rm -rf /tmp/moxnas.zip /tmp/MoxNas-master
    
    msg_ok "MoxNAS application installed"
}

configure_nginx() {
    msg_info "Configuring nginx..."
    
    # Create nginx configuration
    cat > /etc/nginx/sites-available/moxnas << 'EOF'
server {
    listen 8000 default_server;
    listen [::]:8000 default_server;
    
    root /var/www/moxnas;
    index index.html;
    server_name _;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    access_log /var/log/nginx/moxnas_access.log;
    error_log /var/log/nginx/moxnas_error.log;
}
EOF
    
    # Remove default site and enable MoxNAS
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
    
    # Test configuration
    if nginx -t >/dev/null 2>&1; then
        msg_ok "Nginx configured successfully"
    else
        msg_error "Nginx configuration test failed"
        exit 1
    fi
}

configure_nas_services() {
    msg_info "Configuring NAS services..."
    
    # Configure Samba
    cp /etc/samba/smb.conf /etc/samba/smb.conf.backup 2>/dev/null || true
    cat > /etc/samba/smb.conf << 'EOF'
[global]
workgroup = WORKGROUP
server string = MoxNAS Server
netbios name = moxnas
security = user
map to guest = bad user
guest account = nobody
log file = /var/log/samba/%m.log
max log size = 50
load printers = no
disable spoolss = yes
vfs objects = catia fruit streams_xattr

[public]
comment = MoxNAS public share
path = /mnt/shares/public
browseable = yes
read only = no
guest ok = yes
create mask = 0755
directory mask = 0755
force user = nobody
force group = nogroup
EOF
    
    # Configure NFS
    echo "/mnt/shares/public *(rw,sync,no_subtree_check,all_squash,anonuid=65534,anongid=65534)" > /etc/exports
    
    # Configure vsftpd
    cp /etc/vsftpd.conf /etc/vsftpd.conf.backup 2>/dev/null || true
    cat > /etc/vsftpd.conf << 'EOF'
listen=YES
anonymous_enable=YES
local_enable=YES
write_enable=YES
anon_upload_enable=YES
anon_mkdir_write_enable=YES
anon_root=/mnt/shares/public
no_anon_password=YES
ftpd_banner=Welcome to MoxNAS FTP service.
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
pam_service_name=vsftpd
ssl_enable=NO
EOF
    
    msg_ok "NAS services configured"
}

configure_systemd() {
    msg_info "Creating systemd services..."
    
    # MoxNAS API service
    cat > /etc/systemd/system/moxnas-api.service << 'EOF'
[Unit]
Description=MoxNAS API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/moxnas
ExecStart=/usr/bin/python3 /opt/moxnas/api-server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable moxnas-api >/dev/null 2>&1
    
    msg_ok "Systemd services configured"
}

setup_defaults() {
    msg_info "Setting up default configuration..."
    
    # Create default users configuration
    mkdir -p "$CONFIG_DIR"
    cat > "$CONFIG_DIR/users.json" << 'EOF'
{
    "admin": {
        "password": "admin",
        "role": "administrator",
        "created": "2024-01-01T00:00:00.000Z"
    }
}
EOF
    
    chmod 600 "$CONFIG_DIR/users.json"
    chown www-data:www-data "$WEB_DIR" -R
    
    msg_ok "Default configuration set up"
}

start_services() {
    msg_info "Starting services..."
    
    # Enable and start services
    systemctl enable nginx smbd nfs-kernel-server vsftpd >/dev/null 2>&1
    
    systemctl start nginx >/dev/null 2>&1
    systemctl start smbd >/dev/null 2>&1
    systemctl start nfs-kernel-server >/dev/null 2>&1
    systemctl start vsftpd >/dev/null 2>&1
    systemctl start moxnas-api >/dev/null 2>&1
    
    # Export NFS shares
    exportfs -ra >/dev/null 2>&1 || true
    
    msg_ok "All services started"
}

cleanup() {
    msg_info "Cleaning up..."
    
    # Remove temporary files
    rm -rf /tmp/hugo* /tmp/moxnas* 2>/dev/null || true
    
    # Clear package cache
    apt-get autoremove -y -qq >/dev/null 2>&1
    apt-get autoclean -qq >/dev/null 2>&1
    
    msg_ok "Cleanup completed"
}

# Run main function
main "$@"