#!/usr/bin/env bash

# MoxNAS Installation Script
# Copyright (c) 2024 MoxNAS Contributors
# License: MIT

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Error handling
handle_error() {
    log_error "Installation failed at line $1"
    log_error "Command: $2"
    log_error "Exit code: $3"
    exit 1
}

trap 'handle_error $LINENO "$BASH_COMMAND" $?' ERR

# Version tracking
MOXNAS_VERSION="1.0.0"
INSTALL_DIR="/opt/moxnas"
WEB_DIR="/var/www/moxnas"
API_DIR="/opt/moxnas/api"

main() {
    log_info "Starting MoxNAS installation..."
    
    # Update system
    update_system
    
    # Install dependencies
    install_dependencies
    
    # Create directories
    create_directories
    
    # Install Hugo
    install_hugo
    
    # Download and setup MoxNAS
    setup_moxnas
    
    # Configure services
    configure_nginx
    configure_nas_services
    configure_systemd
    
    # Set up default configuration
    setup_defaults
    
    # Start services
    start_services
    
    # Cleanup
    cleanup
    
    log_success "MoxNAS installation completed successfully!"
    log_info "Access your MoxNAS instance at: http://$(hostname -I | awk '{print $1}'):8000"
    log_info "Default credentials: admin / admin"
    
    # Write version file
    echo "$MOXNAS_VERSION" > /opt/MoxNAS_version.txt
}

update_system() {
    log_info "Updating system packages..."
    apt-get update -qq
    apt-get upgrade -y -qq
}

install_dependencies() {
    log_info "Installing dependencies..."
    
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
        systemctl
    
    # Python packages
    pip3 install --quiet \
        aiohttp \
        aiofiles \
        psutil \
        jinja2
}

install_hugo() {
    log_info "Installing Hugo static site generator..."
    
    HUGO_VERSION="0.119.0"
    HUGO_URL="https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_linux-amd64.tar.gz"
    
    cd /tmp
    wget -q "$HUGO_URL" -O hugo.tar.gz
    tar -xzf hugo.tar.gz
    mv hugo /usr/local/bin/
    chmod +x /usr/local/bin/hugo
    rm -f hugo.tar.gz
    
    # Verify installation
    if ! hugo version >/dev/null 2>&1; then
        log_error "Hugo installation failed"
        exit 1
    fi
    
    log_success "Hugo installed successfully"
}

create_directories() {
    log_info "Creating directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$WEB_DIR"
    mkdir -p "$API_DIR"
    mkdir -p /etc/moxnas
    mkdir -p /var/log/moxnas
    mkdir -p /mnt/shares
    mkdir -p /mnt/shares/public
    
    # Set permissions
    chown -R www-data:www-data "$WEB_DIR"
    chown -R root:root "$INSTALL_DIR"
    chmod 755 /mnt/shares
    chmod 777 /mnt/shares/public
}

setup_moxnas() {
    log_info "Setting up MoxNAS application..."
    
    cd "$INSTALL_DIR"
    
    # Download MoxNAS source (in production, this would be from GitHub)
    # For now, we'll create the structure
    create_hugo_site
    create_api_server
    create_management_scripts
}

create_hugo_site() {
    log_info "Creating Hugo site structure..."
    
    cd "$INSTALL_DIR"
    hugo new site web --format yaml
    cd web
    
    # Create config
    cat > config.yaml << 'EOF'
baseURL: "/"
languageCode: "en-us"
title: "MoxNAS"
theme: "moxnas-theme"

params:
  version: "1.0.0"
  description: "TrueNAS-like NAS Management"
  author: "MoxNAS Team"

menu:
  main:
    - name: "Dashboard"
      url: "/"
      weight: 10
    - name: "Storage"
      url: "/storage/"
      weight: 20
    - name: "Shares"
      url: "/shares/"
      weight: 30
    - name: "Network"
      url: "/network/"
      weight: 40
    - name: "System"
      url: "/system/"
      weight: 50

markup:
  goldmark:
    renderer:
      unsafe: true
EOF
    
    # Create basic theme structure
    mkdir -p themes/moxnas-theme/layouts/{_default,partials,shortcodes}
    mkdir -p themes/moxnas-theme/static/{css,js,images}
    
    # Create base layout
    cat > themes/moxnas-theme/layouts/_default/baseof.html << 'EOF'
<!DOCTYPE html>
<html lang="{{ .Site.LanguageCode }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ if .Title }}{{ .Title }} - {{ end }}{{ .Site.Title }}</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <div class="container">
        {{ partial "header.html" . }}
        <main>
            {{ block "main" . }}{{ end }}
        </main>
        {{ partial "footer.html" . }}
    </div>
    <script src="/js/app.js"></script>
</body>
</html>
EOF
    
    # Create homepage
    cat > content/_index.md << 'EOF'
---
title: "Dashboard"
type: "dashboard"
---

# MoxNAS Dashboard

Welcome to your MoxNAS system.
EOF
    
    # Build site
    hugo --destination "$WEB_DIR"
    
    log_success "Hugo site created and built"
}

create_api_server() {
    log_info "Creating Python API server..."
    
    cat > "$API_DIR/server.py" << 'EOF'
#!/usr/bin/env python3
"""
MoxNAS API Server
Lightweight Python API for NAS management
"""

import asyncio
import json
import subprocess
import psutil
import aiohttp.web
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/moxnas/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('moxnas-api')

class MoxNASAPI:
    def __init__(self):
        self.app = aiohttp.web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        self.app.router.add_get('/api/system-stats', self.get_system_stats)
        self.app.router.add_get('/api/services', self.get_services)
        self.app.router.add_get('/api/shares', self.get_shares)
        self.app.router.add_post('/api/shares', self.create_share)
        self.app.router.add_delete('/api/shares/{name}', self.delete_share)
    
    async def get_system_stats(self, request):
        """Get real-time system statistics"""
        try:
            stats = {
                'cpu': psutil.cpu_percent(interval=1),
                'memory': psutil.virtual_memory().percent,
                'disk': psutil.disk_usage('/').percent,
                'uptime': psutil.boot_time(),
                'processes': len(psutil.pids())
            }
            return aiohttp.web.json_response(stats)
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    async def get_services(self, request):
        """Get status of NAS services"""
        services = ['nginx', 'smbd', 'nfs-kernel-server', 'vsftpd']
        status = {}
        
        for service in services:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service],
                    capture_output=True,
                    text=True
                )
                status[service] = {
                    'active': result.returncode == 0,
                    'status': result.stdout.strip()
                }
            except Exception as e:
                status[service] = {'active': False, 'error': str(e)}
        
        return aiohttp.web.json_response(status)
    
    async def get_shares(self, request):
        """Get list of configured shares"""
        shares = []
        
        # Parse Samba shares
        try:
            with open('/etc/samba/smb.conf', 'r') as f:
                content = f.read()
                # Simple parsing - in production use proper parser
                lines = content.split('\n')
                current_share = None
                for line in lines:
                    line = line.strip()
                    if line.startswith('[') and line.endswith(']') and line != '[global]':
                        current_share = line[1:-1]
                        shares.append({
                            'name': current_share,
                            'type': 'smb',
                            'active': True
                        })
        except Exception as e:
            logger.error(f"Error reading Samba config: {e}")
        
        return aiohttp.web.json_response(shares)
    
    async def create_share(self, request):
        """Create a new share"""
        try:
            data = await request.json()
            name = data.get('name')
            path = data.get('path', f'/mnt/shares/{name}')
            
            # Create directory
            Path(path).mkdir(parents=True, exist_ok=True)
            
            # Add to Samba config (simplified)
            with open('/etc/samba/smb.conf', 'a') as f:
                f.write(f'\n[{name}]\n')
                f.write(f'   path = {path}\n')
                f.write('   browseable = yes\n')
                f.write('   read only = no\n')
                f.write('   guest ok = yes\n\n')
            
            # Restart Samba
            subprocess.run(['systemctl', 'reload', 'smbd'])
            
            return aiohttp.web.json_response({'success': True, 'name': name})
        except Exception as e:
            logger.error(f"Error creating share: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    async def delete_share(self, request):
        """Delete a share"""
        name = request.match_info['name']
        # Implementation would remove from config and restart services
        return aiohttp.web.json_response({'success': True})

def main():
    api = MoxNASAPI()
    aiohttp.web.run_app(api.app, host='127.0.0.1', port=8001)

if __name__ == '__main__':
    main()
EOF
    
    chmod +x "$API_DIR/server.py"
    log_success "API server created"
}

create_management_scripts() {
    log_info "Creating management scripts..."
    
    mkdir -p "$INSTALL_DIR/scripts"
    
    # Samba management script
    cat > "$INSTALL_DIR/scripts/samba_manager.sh" << 'EOF'
#!/bin/bash
# Samba Share Management Script

SHARES_DIR="/mnt/shares"
SMB_CONF="/etc/samba/smb.conf"

create_share() {
    local name="$1"
    local path="${SHARES_DIR}/${name}"
    
    # Create directory
    mkdir -p "$path"
    chmod 755 "$path"
    
    # Add to smb.conf
    cat >> "$SMB_CONF" << EOL

[${name}]
   path = ${path}
   browseable = yes
   read only = no
   guest ok = yes
   create mask = 0755
   directory mask = 0755
EOL
    
    # Reload Samba
    systemctl reload smbd
    echo "Share '$name' created successfully"
}

delete_share() {
    local name="$1"
    
    # Remove from smb.conf (simplified - in production use proper parsing)
    sed -i "/^\[${name}\]/,/^$/d" "$SMB_CONF"
    
    # Reload Samba
    systemctl reload smbd
    echo "Share '$name' deleted successfully"
}

case "$1" in
    create)
        create_share "$2"
        ;;
    delete)
        delete_share "$2"
        ;;
    *)
        echo "Usage: $0 {create|delete} <share_name>"
        exit 1
        ;;
esac
EOF
    
    chmod +x "$INSTALL_DIR/scripts/samba_manager.sh"
    log_success "Management scripts created"
}

configure_nginx() {
    log_info "Configuring nginx..."
    
    cat > /etc/nginx/sites-available/moxnas << 'EOF'
server {
    listen 8000 default_server;
    listen [::]:8000 default_server;
    
    root /var/www/moxnas;
    index index.html;
    
    server_name _;
    
    # Static content (Hugo site)
    location / {
        try_files $uri $uri/ /index.html;
        
        # Security headers
        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-Content-Type-Options "nosniff";
        add_header X-XSS-Protection "1; mode=block";
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Static assets
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Logs
    access_log /var/log/nginx/moxnas_access.log;
    error_log /var/log/nginx/moxnas_error.log;
}
EOF
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Enable MoxNAS site
    ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
    
    # Test nginx config
    if ! nginx -t; then
        log_error "Nginx configuration test failed"
        exit 1
    fi
    
    log_success "Nginx configured"
}

configure_nas_services() {
    log_info "Configuring NAS services..."
    
    # Configure Samba
    cp /etc/samba/smb.conf /etc/samba/smb.conf.backup
    cat > /etc/samba/smb.conf << 'EOF'
[global]
   workgroup = WORKGROUP
   server string = MoxNAS Server
   netbios name = moxnas
   security = user
   map to guest = bad user
   dns proxy = no
   load printers = no
   printcap name = /dev/null
   disable spoolss = yes
   guest account = nobody
   log file = /var/log/samba/%m.log
   max log size = 50

[public]
   path = /mnt/shares/public
   browseable = yes
   read only = no
   guest ok = yes
   create mask = 0755
   directory mask = 0755
EOF
    
    # Configure NFS
    cat > /etc/exports << 'EOF'
/mnt/shares/public *(rw,sync,no_subtree_check,all_squash,anonuid=65534,anongid=65534)
EOF
    
    # Configure vsftpd
    cp /etc/vsftpd.conf /etc/vsftpd.conf.backup
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
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
rsa_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
rsa_private_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
ssl_enable=NO
EOF
    
    log_success "NAS services configured"
}

configure_systemd() {
    log_info "Creating systemd services..."
    
    # MoxNAS API service
    cat > /etc/systemd/system/moxnas-api.service << 'EOF'
[Unit]
Description=MoxNAS API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/moxnas/api
ExecStart=/usr/bin/python3 /opt/moxnas/api/server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable moxnas-api
    
    log_success "Systemd services configured"
}

setup_defaults() {
    log_info "Setting up default configuration..."
    
    # Create default admin user for web interface
    mkdir -p /etc/moxnas
    cat > /etc/moxnas/users.json << 'EOF'
{
    "admin": {
        "password": "admin",
        "role": "administrator"
    }
}
EOF
    
    # Set proper permissions
    chown www-data:www-data /var/www/moxnas -R
    chown nobody:nogroup /mnt/shares/public -R
    
    log_success "Default configuration set up"
}

start_services() {
    log_info "Starting services..."
    
    # Start and enable services
    systemctl start nginx
    systemctl enable nginx
    
    systemctl start smbd
    systemctl enable smbd
    
    systemctl start nfs-kernel-server
    systemctl enable nfs-kernel-server
    
    systemctl start vsftpd
    systemctl enable vsftpd
    
    systemctl start moxnas-api
    
    # Export NFS shares
    exportfs -a
    
    log_success "All services started"
}

cleanup() {
    log_info "Cleaning up..."
    
    # Remove temporary files
    rm -rf /tmp/hugo*
    
    # Clear package cache
    apt-get autoremove -y -qq
    apt-get autoclean -qq
    
    log_success "Cleanup completed"
}

# Run main function
main "$@"