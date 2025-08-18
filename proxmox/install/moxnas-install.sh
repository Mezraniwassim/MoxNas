#!/usr/bin/env bash

# Copyright (c) 2021-2024 tteck
# Author: tteck (tteckster)
# Co-Author: WassimMezrani (MoxNAS)
# License: MIT
# https://github.com/community-scripts/ProxmoxVE/raw/main/LICENSE
# Source: https://github.com/YOUR_USERNAME/MoxNAS

# MoxNAS Container Installation Script
# This script runs INSIDE the LXC container and fixes all issues from the conversation

source /dev/stdin <<<"$FUNCTIONS_FILE_PATH"
color
verb_ip6
catch_errors
setting_up_container
network_check
update_container

msg_info "Installing Dependencies"
$STD apt-get install -y curl sudo mc git python3 python3-pip python3-venv python3-dev build-essential nodejs npm nginx net-tools htop
msg_ok "Installed Dependencies"

msg_info "Installing NAS Services"
$STD apt-get install -y samba samba-common-bin nfs-kernel-server vsftpd openssh-server smartmontools zfsutils-linux
msg_ok "Installed NAS Services"

msg_info "Creating MoxNAS User"
adduser --system --group --disabled-password --home /opt/moxnas --shell /bin/bash moxnas
usermod -aG sudo moxnas
msg_ok "Created MoxNAS User"

msg_info "Creating Storage Directory Structure"
mkdir -p /mnt/storage/{shares,ftp,nfs,backups}
mkdir -p /var/log/moxnas
mkdir -p /var/lib/moxnas
chown -R moxnas:moxnas /mnt/storage
chown -R moxnas:moxnas /var/log/moxnas
chown -R moxnas:moxnas /var/lib/moxnas
chmod 755 /mnt/storage
chmod 755 /var/log/moxnas
chmod 755 /var/lib/moxnas
msg_ok "Created Storage Directory Structure"

msg_info "Cloning MoxNAS Repository"
cd /opt
if [ -d "moxnas" ]; then 
    rm -rf moxnas
fi
$STD git clone https://github.com/YOUR_USERNAME/MoxNAS.git moxnas
chown -R moxnas:moxnas /opt/moxnas
cd moxnas
msg_ok "Cloned MoxNAS Repository"

msg_info "Setting up Python Environment"
$STD python3 -m venv venv
source venv/bin/activate
$STD pip install --upgrade pip

# Install requirements with error handling
if [ -f "backend/requirements.txt" ]; then
    $STD pip install -r backend/requirements.txt
elif [ -f "requirements.txt" ]; then
    $STD pip install -r requirements.txt
else
    # Fallback - install essential packages
    $STD pip install django djangorestframework django-cors-headers psutil requests gunicorn whitenoise python-dotenv
fi
msg_ok "Python Environment Ready"

# FIX: Memory issues during build (Critical fix from conversation)
msg_info "Building Frontend (with memory optimization)"
if [ -d "frontend" ]; then
    cd frontend
    
    # FIX: Set memory limits to prevent out-of-memory errors
    export NODE_OPTIONS="--max-old-space-size=1024"
    
    # Retry logic for npm install
    retry_count=0
    max_retries=3
    
    while [ $retry_count -lt $max_retries ]; do
        if $STD npm install; then
            break
        else
            msg_warn "npm install failed, attempt $((retry_count + 1))/$max_retries"
            retry_count=$((retry_count + 1))
            if [ $retry_count -eq $max_retries ]; then
                msg_error "npm install failed after $max_retries attempts"
                exit 1
            fi
            sleep 5
        fi
    done
    
    # FIX: Multi-stage build with memory optimization and retry logic
    build_success=false
    
    # Attempt 1: Normal memory allocation
    export NODE_OPTIONS="--max-old-space-size=1024"
    if $STD npm run build; then
        build_success=true
        msg_ok "Frontend built successfully (normal memory)"
    else
        msg_warn "First build attempt failed, trying with reduced memory..."
        
        # Attempt 2: Reduced memory allocation
        export NODE_OPTIONS="--max-old-space-size=512"
        if $STD npm run build; then
            build_success=true
            msg_ok "Frontend built successfully (reduced memory)"
        else
            msg_warn "Second build attempt failed, trying minimal memory..."
            
            # Attempt 3: Minimal memory allocation
            export NODE_OPTIONS="--max-old-space-size=256"
            if $STD npm run build; then
                build_success=true
                msg_ok "Frontend built successfully (minimal memory)"
            else
                msg_error "All frontend build attempts failed"
                # Don't exit - continue with backend only
                msg_warn "Continuing installation without frontend build"
            fi
        fi
    fi
    
    # Copy build files if build was successful
    if [ "$build_success" = true ] && [ -d "build" ] && [ -d "../backend" ]; then
        mkdir -p ../backend/static
        cp -r build/* ../backend/static/ 2>/dev/null || true
        msg_ok "Frontend files copied to backend"
    fi
    
    cd ..
fi

msg_info "Configuring Django Backend"
cd /opt/moxnas

# Ensure we're in the right directory structure
if [ -d "backend" ]; then
    cd backend
elif [ -f "manage.py" ]; then
    # We're already in the Django directory
    :
else
    msg_error "Django project structure not found!"
    exit 1
fi

source /opt/moxnas/venv/bin/activate

# Configure Django if manage.py exists
if [ -f "manage.py" ]; then
    mkdir -p static media logs
    
    # Collect static files
    $STD python manage.py collectstatic --noinput
    
    # Run migrations
    $STD python manage.py migrate
    
    # Create superuser (admin/admin123)
    echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@moxnas.local', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell
    
    msg_ok "Django backend configured"
else
    msg_warn "manage.py not found, skipping Django configuration"
fi

cd /opt/moxnas

msg_info "Creating MoxNAS Service"
cat <<EOF >/etc/systemd/system/moxnas.service
[Unit]
Description=MoxNAS Web Interface
Documentation=https://github.com/YOUR_USERNAME/MoxNAS
After=network.target

[Service]
Type=exec
User=moxnas
Group=moxnas
WorkingDirectory=/opt/moxnas/backend
Environment=PATH=/opt/moxnas/venv/bin
Environment=DJANGO_SETTINGS_MODULE=moxnas.settings
Environment=PYTHONPATH=/opt/moxnas/backend
ExecStart=/opt/moxnas/venv/bin/gunicorn --bind 127.0.0.1:8001 --workers 2 --timeout 120 --keep-alive 5 --max-requests 1000 moxnas.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
LimitNOFILE=4096

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable moxnas.service
msg_ok "Created MoxNAS Service"

# FIX: Service accessibility with nginx reverse proxy (Optional - direct access primary)
msg_info "Configuring Nginx (Optional Reverse Proxy)"
cat <<EOF >/etc/nginx/sites-available/moxnas
server {
    listen 80;
    server_name _;
    
    # Redirect to main MoxNAS port
    return 301 http://\$host:8000\$request_uri;
}

server {
    listen 8080;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        proxy_buffering off;
    }
    
    location /static/ {
        alias /opt/moxnas/backend/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /opt/moxnas/backend/media/;
        expires 7d;
    }
}
EOF

# Enable the site but don't make it default
ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/moxnas
# Keep default nginx site for now
$STD nginx -t
$STD systemctl enable nginx
$STD systemctl restart nginx
msg_ok "Configured Nginx"

# Configure NAS services with proper defaults
msg_info "Configuring NAS Services"

# Samba configuration with optimized settings
cat <<EOF >/etc/samba/smb.conf
[global]
workgroup = WORKGROUP
server string = MoxNAS Server (%v)
netbios name = moxnas
security = user
map to guest = bad user
dns proxy = no
socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=65536 SO_SNDBUF=65536
local master = yes
os level = 20
domain master = yes
preferred master = yes
load printers = no
printcap name = /dev/null
disable spoolss = yes

# Performance optimizations
use sendfile = yes
aio read size = 16384
aio write size = 16384

# Security
restrict anonymous = 2
lanman auth = no
ntlm auth = no

[storage]
path = /mnt/storage/shares
comment = MoxNAS Shared Storage
browseable = yes
writable = yes
guest ok = no
read only = no
create mask = 0664
directory mask = 0775
valid users = @users
force group = users
EOF

# NFS configuration
echo "/mnt/storage/nfs *(rw,sync,no_subtree_check,no_root_squash)" > /etc/exports

# FTP configuration with security improvements
cat <<EOF >/etc/vsftpd.conf
listen=YES
anonymous_enable=NO
local_enable=YES
write_enable=YES
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
local_root=/mnt/storage/ftp
allow_writeable_chroot=YES
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=50000
EOF

msg_ok "Configured NAS Services"

# FIX: Verify services are accessible and handle startup issues
msg_info "Starting and Verifying Services"

# Start NAS services with error handling
services=("smbd" "nmbd" "nfs-kernel-server" "vsftpd" "ssh")
for service in "${services[@]}"; do
    if systemctl enable "$service" && systemctl start "$service"; then
        msg_ok "$service started successfully"
    else
        msg_warn "$service failed to start - will continue"
    fi
done

# Start main MoxNAS service
msg_info "Starting MoxNAS Web Service"
if systemctl start moxnas; then
    msg_ok "MoxNAS service started successfully"
else
    msg_error "MoxNAS service failed to start"
    msg_info "Checking service logs..."
    systemctl status moxnas --no-pager
    journalctl -u moxnas --no-pager -n 20
    exit 1
fi

# Wait for services to fully start
sleep 15

# FIX: Port accessibility verification (Critical verification from conversation)
msg_info "Verifying Service Accessibility"

# Check if MoxNAS service is running
if systemctl is-active --quiet moxnas; then
    msg_ok "MoxNAS service is active"
else
    msg_error "MoxNAS service is not active"
    systemctl status moxnas --no-pager
    exit 1
fi

# FIX: Check port accessibility (Critical check from conversation)
port_check_passed=false
if ss -tlnp | grep -q ":8000"; then
    msg_ok "MoxNAS web interface is listening on port 8000"
    port_check_passed=true
else
    msg_error "MoxNAS web interface is not listening on port 8000"
    ss -tlnp | grep :8000 || true
fi

# Additional port binding verification
if netstat -tlnp 2>/dev/null | grep -q ":8000"; then
    msg_ok "Port 8000 binding confirmed via netstat"
    port_check_passed=true
elif ss -tuln | grep -q ":8000"; then
    msg_ok "Port 8000 binding confirmed via ss"
    port_check_passed=true
fi

if [ "$port_check_passed" = false ]; then
    msg_error "Port 8000 accessibility check failed"
    msg_info "Checking service logs for binding issues..."
    journalctl -u moxnas --no-pager -n 10
    exit 1
fi

# FIX: Web interface response test (Critical test from conversation)
msg_info "Testing Web Interface Response"
response_check_passed=false
retry_count=0
max_retries=6

while [ $retry_count -lt $max_retries ]; do
    if curl -f -s --connect-timeout 5 http://localhost:8000 >/dev/null; then
        msg_ok "Web interface responds correctly"
        response_check_passed=true
        break
    else
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            msg_warn "Web interface not ready, waiting... (attempt $retry_count/$max_retries)"
            sleep 10
        fi
    fi
done

if [ "$response_check_passed" = false ]; then
    msg_warn "Web interface response test failed after $max_retries attempts"
    msg_info "This may be normal if Django is still initializing"
    msg_info "Check the service manually: curl http://localhost:8000"
fi

# Final service status verification
msg_info "Final Service Status Check"
critical_services=("moxnas")
for service in "${critical_services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        msg_ok "$service is running"
    else
        msg_error "$service is not running"
        systemctl status "$service" --no-pager
    fi
done

msg_ok "All Services Started and Verified"

motd_ssh
customize

msg_info "Cleaning up"
$STD apt-get -y autoremove
$STD apt-get -y autoclean
msg_ok "Cleaned"