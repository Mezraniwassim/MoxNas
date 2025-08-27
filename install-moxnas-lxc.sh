#!/usr/bin/env bash

# MoxNAS LXC Container Creation and Installation Script
# One-line deployment for Proxmox VE
# Usage: bash -c "$(wget -qLO - https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas-lxc.sh)"

set -euo pipefail

# Colors for output
RD="\033[01;31m"
YW="\033[33m"
GN="\033[1;92m"
CL="\033[m"
BFR="\\r\\033[K"
HOLD="-"

# Display functions
function msg_info() {
    local msg="$1"
    echo -ne " ${HOLD} ${YW}${msg}..."
    echo -e "${CL}"
}

function msg_ok() {
    local msg="$1"
    echo -e "${BFR} ✓ ${GN}${msg}${CL}"
}

function msg_error() {
    local msg="$1"
    echo -e "${BFR} ✗ ${RD}${msg}${CL}"
}

# Check if running on Proxmox
if ! command -v pct &> /dev/null; then
    msg_error "This script must be run on a Proxmox VE host"
    exit 1
fi

# Configuration variables with defaults
CTID=${CTID:-$(pvesh get /cluster/nextid)}
CT_HOSTNAME=${CT_HOSTNAME:-"moxnas"}
STORAGE=${STORAGE:-"local-lvm"}
TEMPLATE=${TEMPLATE:-"local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"}
PASSWORD=${PASSWORD:-"$(openssl rand -base64 12)"}
CORES=${CORES:-4}
MEMORY=${MEMORY:-4096}
DISK_SIZE=${DISK_SIZE:-20}
NETWORK=${NETWORK:-"vmbr0"}
IP_CONFIG=${IP_CONFIG:-"dhcp"}
GITHUB_REPO=${GITHUB_REPO:-"https://github.com/Mezraniwassim/MoxNAS.git"}
BRANCH=${BRANCH:-"master"}

# Check if template exists
msg_info "Checking Debian template"
TEMPLATE="local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"
if ! pveam list local 2>/dev/null | grep -q "debian-12-standard_12.7-1_amd64.tar.zst"; then
    msg_info "Downloading Debian 12 template"
    pveam update >/dev/null 2>&1
    pveam download local debian-12-standard_12.7-1_amd64.tar.zst >/dev/null 2>&1
fi
msg_ok "Template ready"

# Display configuration
echo -e "\n${GN}MoxNAS LXC Container Configuration:${CL}"
echo -e "CT ID: ${YW}${CTID}${CL}"
echo -e "Hostname: ${YW}${CT_HOSTNAME}${CL}"
echo -e "Password: ${YW}${PASSWORD}${CL}"
echo -e "Cores: ${YW}${CORES}${CL}"
echo -e "Memory: ${YW}${MEMORY}MB${CL}"
echo -e "Disk: ${YW}${DISK_SIZE}GB${CL}"
echo -e "Network: ${YW}${IP_CONFIG}${CL}"
echo ""

# Create container
msg_info "Creating LXC container"
pct create ${CTID} ${TEMPLATE} \
    --arch amd64 \
    --cores ${CORES} \
    --hostname ${CT_HOSTNAME} \
    --memory ${MEMORY} \
    --net0 name=eth0,bridge=${NETWORK},ip=${IP_CONFIG} \
    --ostype debian \
    --password ${PASSWORD} \
    --rootfs ${STORAGE}:${DISK_SIZE} \
    --swap 512 \
    --unprivileged 1 \
    --features nesting=1 \
    --startup order=1 \
    --onboot 1

msg_ok "Container created (ID: ${CTID})"

# Configure container for NAS functionality
msg_info "Configuring container for NAS functionality"
cat >> /etc/pve/lxc/${CTID}.conf << EOF

# MoxNAS specific configuration
lxc.apparmor.profile: unconfined
lxc.cap.drop: 
lxc.cgroup.devices.allow: a
lxc.mount.auto: "proc:rw sys:rw"
EOF

msg_ok "Container configured"

# Start container
msg_info "Starting container"
pct start ${CTID}

# Wait for container to be ready
sleep 10

# Install MoxNAS inside the container
msg_info "Installing MoxNAS application"
pct exec ${CTID} -- bash -c "$(cat << 'INSTALL_SCRIPT'
#!/bin/bash
set -euo pipefail

# Standard output suppression function
silent() {
    "$@" >/dev/null 2>&1
}

# Color functions for container
function msg_info() { echo -e " ⏳ \e[33m$1...\e[0m"; }
function msg_ok() { echo -e " ✅ \e[32m$1\e[0m"; }

msg_info "Updating system"
silent apt-get update
silent apt-get upgrade -y

msg_info "Installing dependencies"
silent apt-get install -y \
    curl wget git sudo mc \
    python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib \
    redis-server nginx supervisor \
    mdadm smartmontools \
    nfs-kernel-server samba vsftpd \
    htop iotop build-essential \
    libpq-dev libffi-dev libssl-dev openssl ufw

msg_info "Setting up PostgreSQL"
systemctl start postgresql
systemctl enable postgresql
POSTGRES_PASSWORD=$(openssl rand -base64 32)
sudo -u postgres psql -c "CREATE DATABASE moxnas;"
sudo -u postgres psql -c "CREATE USER moxnas WITH PASSWORD '$POSTGRES_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE moxnas TO moxnas;"
sudo -u postgres psql -c "ALTER USER moxnas CREATEDB;"

msg_info "Setting up Redis"
REDIS_PASSWORD=$(openssl rand -base64 32)
sed -i "s/# requirepass foobared/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
systemctl restart redis-server
systemctl enable redis-server

msg_info "Creating MoxNAS user"
useradd -r -s /bin/bash -d /opt/moxnas -m moxnas

msg_info "Installing MoxNAS application"
cd /opt/moxnas

# Download MoxNAS from GitHub
wget -O moxnas.tar.gz https://github.com/Mezraniwassim/MoxNas/archive/refs/heads/master.tar.gz
tar -xzf moxnas.tar.gz --strip-components=1
rm moxnas.tar.gz

# Set ownership
chown -R moxnas:moxnas /opt/moxnas

# Create Python virtual environment
sudo -u moxnas python3 -m venv venv
sudo -u moxnas bash -c "source venv/bin/activate && pip install --upgrade pip"
sudo -u moxnas bash -c "source venv/bin/activate && pip install gunicorn"
sudo -u moxnas bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Create configuration file
cat > /opt/moxnas/.env << EOF
FLASK_ENV=production
SECRET_KEY=$(openssl rand -base64 64)
DATABASE_URL=postgresql://moxnas:$POSTGRES_PASSWORD@localhost/moxnas
REDIS_URL=redis://:$REDIS_PASSWORD@localhost:6379/0
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@localhost:6379/0
MOXNAS_ADMIN_EMAIL=admin@moxnas.local
SESSION_COOKIE_SECURE=true
EOF

chmod 600 /opt/moxnas/.env
chown moxnas:moxnas /opt/moxnas/.env

msg_info "Setting up storage directories"
mkdir -p /mnt/storage /mnt/backups /var/log/moxnas
chown -R moxnas:moxnas /mnt/storage /mnt/backups /var/log/moxnas

msg_info "Initializing database"
cd /opt/moxnas
sudo -u moxnas bash -c "source venv/bin/activate && python -c 'from app import create_app, db; app = create_app(\"production\"); app.app_context().push(); db.create_all()'"

# Create admin user
ADMIN_PASSWORD=$(openssl rand -base64 16)
sudo -u moxnas bash -c "source venv/bin/activate && python -c '
from app import create_app, db
from app.models import User, UserRole
from werkzeug.security import generate_password_hash
import os
app = create_app(\"production\")
with app.app_context():
    admin = User(
        username=\"admin\",
        email=\"admin@moxnas.local\",
        role=UserRole.ADMIN,
        is_active=True,
        password_hash=generate_password_hash(\"'$ADMIN_PASSWORD'\")
    )
    db.session.add(admin)
    db.session.commit()
    print(\"Admin user created successfully\")
'"

# Save admin credentials
echo "Admin Username: admin" > /opt/moxnas/.admin_credentials
echo "Admin Password: $ADMIN_PASSWORD" >> /opt/moxnas/.admin_credentials
chmod 600 /opt/moxnas/.admin_credentials
chown moxnas:moxnas /opt/moxnas/.admin_credentials

msg_info "Configuring Nginx"
# Generate self-signed SSL certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/moxnas-selfsigned.key \
    -out /etc/ssl/certs/moxnas-selfsigned.crt \
    -subj "/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas.local"

cat > /etc/nginx/sites-available/moxnas << 'EOF'
server {
    listen 80;
    server_name _;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;
    
    ssl_certificate /etc/ssl/certs/moxnas-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/moxnas-selfsigned.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    client_max_body_size 10G;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /static {
        alias /opt/moxnas/app/static;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
EOF

ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

msg_info "Configuring systemd services"
# Create MoxNAS systemd service
cat > /etc/systemd/system/moxnas.service << 'EOF'
[Unit]
Description=MoxNAS Web Application
Documentation=https://github.com/Mezraniwassim/MoxNAS
After=network-online.target postgresql.service redis-server.service
Wants=network-online.target
Requires=postgresql.service redis-server.service

[Service]
Type=exec
User=moxnas
Group=moxnas
WorkingDirectory=/opt/moxnas
Environment="PATH=/opt/moxnas/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/moxnas"
EnvironmentFile=/opt/moxnas/.env

ExecStart=/opt/moxnas/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 wsgi:app
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID

Restart=always
RestartSec=10
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Security settings for LXC
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/moxnas /mnt/storage /mnt/backups /tmp /var/log
PrivateTmp=yes
PrivateDevices=no
ProtectKernelTunables=no
ProtectKernelModules=no
ProtectControlGroups=yes
RestrictRealtime=yes
LockPersonality=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096
MemoryMax=1G
CPUQuota=100%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=moxnas

[Install]
WantedBy=multi-user.target
EOF

# Create MoxNAS worker service
cat > /etc/systemd/system/moxnas-worker.service << 'EOF'
[Unit]
Description=MoxNAS Background Worker
After=network-online.target postgresql.service redis-server.service moxnas.service
Wants=network-online.target
Requires=postgresql.service redis-server.service

[Service]
Type=exec
User=moxnas
Group=moxnas
WorkingDirectory=/opt/moxnas
Environment="PATH=/opt/moxnas/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/moxnas"
EnvironmentFile=/opt/moxnas/.env

ExecStart=/opt/moxnas/venv/bin/celery -A celery_worker.celery worker --loglevel=info --concurrency=2
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID

Restart=always
RestartSec=10
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/moxnas /mnt/storage /mnt/backups /tmp /var/log
PrivateTmp=yes
PrivateDevices=no
ProtectKernelTunables=no
ProtectKernelModules=no

# Resource limits
LimitNOFILE=65536
LimitNPROC=2048
MemoryMax=512M
CPUQuota=50%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=moxnas-worker

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start services
systemctl daemon-reload
systemctl enable moxnas moxnas-worker
systemctl start moxnas moxnas-worker

msg_info "Setting up storage and shares"
mkdir -p /mnt/storage /mnt/backups /srv/ftp
chown moxnas:moxnas /mnt/storage /mnt/backups
chown ftp:ftp /srv/ftp

# NFS configuration
echo "/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)" >> /etc/exports
systemctl enable nfs-kernel-server
systemctl start nfs-kernel-server

# Samba configuration
cp /etc/samba/smb.conf /etc/samba/smb.conf.backup
cat >> /etc/samba/smb.conf << 'EOF'

[moxnas-storage]
    path = /mnt/storage
    browseable = yes
    writable = yes
    guest ok = no
    valid users = moxnas
    create mask = 0755
    directory mask = 0755
EOF

echo -e "$ADMIN_PASSWORD\n$ADMIN_PASSWORD" | smbpasswd -a moxnas
systemctl enable smbd nmbd
systemctl start smbd nmbd

# FTP configuration
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
allow_writeable_chroot=YES
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
rsa_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
rsa_private_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
ssl_enable=YES
pasv_enable=Yes
pasv_min_port=10000
pasv_max_port=10100
user_sub_token=$USER
local_root=/srv/ftp
userlist_enable=YES
userlist_file=/etc/vsftpd.userlist
userlist_deny=NO
EOF

echo "moxnas" > /etc/vsftpd.userlist
systemctl enable vsftpd
systemctl start vsftpd

msg_info "Configuring firewall"
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw allow 139,445/tcp
ufw allow 2049/tcp
ufw allow 21/tcp
ufw allow 10000:10100/tcp

# Create installation summary
SERVER_IP=$(hostname -I | awk '{print $1}')
cat > /opt/moxnas/INSTALLATION_INFO.txt << EOF
MoxNAS Installation Complete!
=============================

Web Interface: https://$SERVER_IP
Admin Username: admin
Admin Password: $ADMIN_PASSWORD

Database Password: $POSTGRES_PASSWORD
Redis Password: $REDIS_PASSWORD

Network Shares:
- SMB: //$SERVER_IP/moxnas-storage (user: moxnas, pass: $ADMIN_PASSWORD)
- NFS: $SERVER_IP:/mnt/storage
- FTP: ftp://$SERVER_IP (user: moxnas, pass: $ADMIN_PASSWORD)

Installation Date: $(date)
EOF

chmod 600 /opt/moxnas/INSTALLATION_INFO.txt
chown moxnas:moxnas /opt/moxnas/INSTALLATION_INFO.txt

# Create welcome motd
cat > /etc/motd << EOF

    __  __            _   _          ____  
   |  \/  | _____  __| \ | |   /\   / ___| 
   | |\/| |/ _ \ \/ /|  \| |  /  \  \___ \ 
   | |  | | (_) >  < | |\  | / /\ \  ___) |
   |_|  |_|\___/_/\_\|_| \_|/_/  \_\|____/ 

   Professional Network Attached Storage
   
   🌐 Web Interface: https://$SERVER_IP
   👤 Username: admin
   🔑 Password: $ADMIN_PASSWORD
   
   📁 Installation Info: /opt/moxnas/INSTALLATION_INFO.txt

EOF

msg_info "Finalizing installation"
systemctl daemon-reload
systemctl restart supervisor
sleep 3

msg_ok "MoxNAS installation completed successfully!"
echo ""
echo "🎉 Installation Summary:"
echo "📱 Web Interface: https://$SERVER_IP"
echo "👤 Username: admin"
echo "🔑 Password: $ADMIN_PASSWORD"
echo ""
echo "📋 View full details: cat /opt/moxnas/INSTALLATION_INFO.txt"

INSTALL_SCRIPT
)"

msg_ok "MoxNAS installed successfully"

# Get container IP
CONTAINER_IP=$(pct exec ${CTID} -- hostname -I | awk '{print $1}')
INSTALL_INFO=$(pct exec ${CTID} -- cat /opt/moxnas/INSTALLATION_INFO.txt)

echo ""
echo -e "${GN}🎉 MoxNAS Deployment Complete! 🎉${CL}"
echo ""
echo -e "${YW}Container Details:${CL}"
echo -e "CT ID: ${GN}${CTID}${CL}"
echo -e "Hostname: ${GN}${HOSTNAME}${CL}"
echo -e "IP Address: ${GN}${CONTAINER_IP}${CL}"
echo ""
echo -e "${YW}Access Information:${CL}"
echo -e "🌐 Web Interface: ${GN}https://${CONTAINER_IP}${CL}"
echo -e "👤 Username: ${GN}admin${CL}"
echo -e "🔑 Root Password: ${GN}${PASSWORD}${CL}"
echo ""
echo -e "${YW}Management Commands:${CL}"
echo -e "Enter Container: ${GN}pct enter ${CTID}${CL}"
echo -e "View Logs: ${GN}pct exec ${CTID} -- supervisorctl tail -f moxnas-web${CL}"
echo -e "Restart Services: ${GN}pct exec ${CTID} -- supervisorctl restart all${CL}"
echo ""
echo -e "${YW}Installation Details:${CL}"
echo -e "${GN}pct exec ${CTID} -- cat /opt/moxnas/INSTALLATION_INFO.txt${CL}"
echo ""
echo -e "🚀 ${GN}Ready to manage your storage!${CL}"