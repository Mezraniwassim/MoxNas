#!/usr/bin/env bash
# Copyright (c) 2021-2024 community-scripts ORG
# Author: MoxNAS Team
# License: MIT
# https://github.com/community-scripts/ProxmoxVE/raw/main/LICENSE

source /dev/stdin <<< "$FUNCTIONS_FILE_PATH"
color
verb_ip6
catch_errors
setting_up_container
network_check
update_os

msg_info "Installing Dependencies"
$STD apt-get update
$STD apt-get install -y \
    curl \
    sudo \
    mc \
    git \
    ca-certificates \
    gnupg \
    lsb-release \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    supervisor \
    mdadm \
    smartmontools \
    nfs-kernel-server \
    samba \
    vsftpd \
    htop \
    iotop \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    openssl \
    ufw
msg_ok "Installed Dependencies"

msg_info "Setting up PostgreSQL"
systemctl start postgresql
systemctl enable postgresql
POSTGRES_PASSWORD=$(openssl rand -base64 32)
sudo -u postgres psql -c "CREATE DATABASE moxnas;"
sudo -u postgres psql -c "CREATE USER moxnas WITH PASSWORD '$POSTGRES_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE moxnas TO moxnas;"
sudo -u postgres psql -c "ALTER USER moxnas CREATEDB;"
msg_ok "PostgreSQL Setup Complete"

msg_info "Setting up Redis"
REDIS_PASSWORD=$(openssl rand -base64 32)
sed -i "s/# requirepass foobared/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
systemctl restart redis-server
systemctl enable redis-server
msg_ok "Redis Setup Complete"

msg_info "Creating MoxNAS User"
useradd -r -s /bin/bash -d /opt/moxnas -m moxnas
msg_ok "MoxNAS User Created"

msg_info "Installing MoxNAS Application"
cd /opt/moxnas

# Download and extract MoxNAS
LATEST_VERSION=$(curl -s https://api.github.com/repos/Mezraniwassim/MoxNas/releases/latest | grep tag_name | cut -d '"' -f 4)
if [ -z "$LATEST_VERSION" ]; then
    # Fallback: download from main branch if no releases
    $STD wget -O moxnas.tar.gz https://github.com/Mezraniwassim/MoxNas/archive/refs/heads/master.tar.gz
    $STD tar -xzf moxnas.tar.gz --strip-components=1
    rm moxnas.tar.gz
else
    $STD wget -O moxnas.tar.gz https://github.com/Mezraniwassim/MoxNas/archive/refs/tags/$LATEST_VERSION.tar.gz
    $STD tar -xzf moxnas.tar.gz --strip-components=1
    rm moxnas.tar.gz
fi

# Set ownership
chown -R moxnas:moxnas /opt/moxnas

# Create Python virtual environment
sudo -u moxnas python3 -m venv venv
sudo -u moxnas bash -c "source venv/bin/activate && pip install --upgrade pip"
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

msg_ok "MoxNAS Application Installed"

msg_info "Initializing Database"
cd /opt/moxnas
sudo -u moxnas bash -c "source venv/bin/activate && python migrate.py init"

# Create admin user
ADMIN_PASSWORD=$(openssl rand -base64 16)
sudo -u moxnas bash -c "source venv/bin/activate && python migrate.py create-admin --username admin --email admin@moxnas.local --password '$ADMIN_PASSWORD' --first-name Admin --last-name User"
msg_ok "Database Initialized"

msg_info "Configuring Nginx"
cat > /etc/nginx/sites-available/moxnas << 'EOF'
server {
    listen 80;
    server_name _;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;
    
    # SSL configuration - self-signed cert
    ssl_certificate /etc/ssl/certs/moxnas-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/moxnas-selfsigned.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # File upload size limit
    client_max_body_size 10G;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
        
        # WebSocket support
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

# Generate self-signed SSL certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/moxnas-selfsigned.key \
    -out /etc/ssl/certs/moxnas-selfsigned.crt \
    -subj "/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas.local"

# Enable site
ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx
msg_ok "Nginx Configured"

msg_info "Configuring Supervisor"
cat > /etc/supervisor/conf.d/moxnas.conf << 'EOF'
[program:moxnas-web]
command=/opt/moxnas/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app
directory=/opt/moxnas
user=moxnas
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/moxnas-web.log

[program:moxnas-worker]
command=/opt/moxnas/venv/bin/celery -A celery_worker.celery worker --loglevel=info
directory=/opt/moxnas
user=moxnas
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/moxnas-worker.log

[program:moxnas-beat]
command=/opt/moxnas/venv/bin/celery -A celery_worker.celery beat --loglevel=info
directory=/opt/moxnas
user=moxnas
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/moxnas-beat.log
EOF

supervisorctl reread
supervisorctl update
supervisorctl start moxnas-web moxnas-worker moxnas-beat
msg_ok "Supervisor Configured"

msg_info "Setting up Storage Directories"
mkdir -p /mnt/storage /mnt/backups /srv/ftp
chown moxnas:moxnas /mnt/storage /mnt/backups
chown ftp:ftp /srv/ftp
msg_ok "Storage Directories Created"

msg_info "Configuring NFS"
echo "/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)" >> /etc/exports
systemctl enable nfs-kernel-server
systemctl start nfs-kernel-server
msg_ok "NFS Configured"

msg_info "Configuring Samba"
cp /etc/samba/smb.conf /etc/samba/smb.conf.backup
cat >> /etc/samba/smb.conf << 'EOF'

# MoxNAS Samba Configuration
[global]
    workgroup = WORKGROUP
    security = user
    map to guest = bad user
    dns proxy = no
    
[moxnas-storage]
    path = /mnt/storage
    browseable = yes
    writable = yes
    guest ok = no
    valid users = moxnas
    create mask = 0755
    directory mask = 0755
EOF

# Set Samba password for moxnas user
echo -e "$ADMIN_PASSWORD\n$ADMIN_PASSWORD" | smbpasswd -a moxnas
systemctl enable smbd nmbd
systemctl start smbd nmbd
msg_ok "Samba Configured"

msg_info "Configuring FTP"
cp /etc/vsftpd.conf /etc/vsftpd.conf.backup
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
msg_ok "FTP Configured"

msg_info "Configuring Firewall"
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw allow 139,445/tcp  # Samba
ufw allow 2049/tcp     # NFS
ufw allow 21/tcp       # FTP
ufw allow 10000:10100/tcp  # FTP passive
msg_ok "Firewall Configured"

msg_info "Setting up Health Monitoring"
cp /opt/moxnas/health_monitor.py /usr/local/bin/moxnas-health-monitor
chmod +x /usr/local/bin/moxnas-health-monitor

# Create systemd service for health monitoring
cat > /etc/systemd/system/moxnas-health.service << 'EOF'
[Unit]
Description=MoxNAS Health Monitor
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/moxnas-health-monitor --monitor --interval 60
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable moxnas-health.service
systemctl start moxnas-health.service
msg_ok "Health Monitoring Setup Complete"

msg_info "Setting up Maintenance Tasks"
cat > /usr/local/bin/moxnas-maintenance << 'EOF'
#!/bin/bash
# MoxNAS maintenance script

cd /opt/moxnas
sudo -u moxnas bash -c "source venv/bin/activate && python -c '
from app import create_app
from app.storage.manager import storage_manager
from app.tasks import device_health_check, cleanup_old_alerts
app = create_app()
app.app_context().push()

# Update device database
storage_manager.update_device_database()

# Run health checks
device_health_check.delay()

# Clean up old alerts
cleanup_old_alerts.delay()

print(\"Health checks initiated\")
'"

# Clean up old logs
find /var/log/supervisor/ -name "moxnas-*.log.*" -mtime +30 -delete
find /opt/moxnas/logs/ -name "*.log.*" -mtime +30 -delete 2>/dev/null || true

# Clean up old backup files
find /mnt/backups/ -type f -mtime +90 -delete 2>/dev/null || true

# Check for security updates
apt update -qq
security_updates=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)
if [ $security_updates -gt 0 ]; then
    echo "Warning: $security_updates security updates available"
fi

echo "Maintenance completed at $(date)"
EOF

chmod +x /usr/local/bin/moxnas-maintenance

# Add to cron
echo "0 2 * * * root /usr/local/bin/moxnas-maintenance >> /var/log/moxnas-maintenance.log 2>&1" >> /etc/crontab

msg_ok "Maintenance Tasks Configured"

msg_info "Creating Installation Info File"
cat > /opt/moxnas/INSTALLATION_INFO.txt << EOF
MoxNAS Installation Information
===============================

Installation Date: $(date)
Server IP: $(hostname -I | awk '{print $1}')
Web Interface: https://$(hostname -I | awk '{print $1}')

Admin Credentials:
Username: admin
Password: $ADMIN_PASSWORD

Database:
Database: moxnas
Username: moxnas
Password: $POSTGRES_PASSWORD

Redis Password: $REDIS_PASSWORD

Important Files:
- Application: /opt/moxnas
- Configuration: /opt/moxnas/.env
- Logs: /var/log/supervisor/moxnas-*.log
- Storage: /mnt/storage
- Backups: /mnt/backups

Service Management:
- Restart all: supervisorctl restart moxnas-web moxnas-worker moxnas-beat
- Check status: supervisorctl status
- View logs: supervisorctl tail -f moxnas-web
- Health monitor: systemctl status moxnas-health

Network Shares:
- SMB: //$(hostname -I | awk '{print $1}')/moxnas-storage (username: moxnas, password: $ADMIN_PASSWORD)
- NFS: $(hostname -I | awk '{print $1}'):/mnt/storage
- FTP: ftp://$(hostname -I | awk '{print $1}') (username: moxnas, password: $ADMIN_PASSWORD)
EOF

chown moxnas:moxnas /opt/moxnas/INSTALLATION_INFO.txt
chmod 600 /opt/moxnas/INSTALLATION_INFO.txt
msg_ok "Installation Info Created"

msg_info "Finalizing Installation"
systemctl daemon-reload
systemctl restart supervisor
systemctl restart nginx

# Wait for services to start
sleep 5

# Verify services are running
if systemctl is-active --quiet moxnas-health; then
    msg_ok "Health monitoring service is running"
else
    msg_warn "Health monitoring service failed to start"
fi

if supervisorctl status moxnas-web | grep -q RUNNING; then
    msg_ok "MoxNAS web service is running"
else
    msg_warn "MoxNAS web service failed to start"
fi

msg_ok "Installation Complete"

# Create motd
cat > /etc/motd << EOF

    __  __            _   _          ____  
   |  \/  | _____  __| \ | |   /\   / ___| 
   | |\/| |/ _ \ \/ /|  \| |  /  \  \___ \ 
   | |  | | (_) >  < | |\  | / /\ \  ___) |
   |_|  |_|\___/_/\_\|_| \_|/_/  \_\|____/ 
                                           
   Professional Network Attached Storage
   
   Web Interface: https://$(hostname -I | awk '{print $1}')
   Username: admin
   Password: $ADMIN_PASSWORD
   
   Documentation: /opt/moxnas/INSTALLATION_INFO.txt
   
   System Status:
   - $(supervisorctl status moxnas-web | grep -q RUNNING && echo "✓ Web Service: Running" || echo "✗ Web Service: Stopped")
   - $(systemctl is-active --quiet postgresql && echo "✓ Database: Running" || echo "✗ Database: Stopped")
   - $(systemctl is-active --quiet redis-server && echo "✓ Redis: Running" || echo "✗ Redis: Stopped")
   - $(systemctl is-active --quiet smbd && echo "✓ SMB: Running" || echo "✗ SMB: Stopped")
   - $(systemctl is-active --quiet nfs-kernel-server && echo "✓ NFS: Running" || echo "✗ NFS: Stopped")

EOF

motd_ssh
customize

msg_info "Cleaning up"
$STD apt-get autoremove
$STD apt-get autoclean
msg_ok "Cleaned"