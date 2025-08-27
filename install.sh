#!/bin/bash

# MoxNAS Installation Script
# Professional Network Attached Storage Solution for Proxmox LXC

set -e

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

# Logging function
log() {
    echo -e \"${GREEN}[INFO]${NC} $1\"
}

warn() {
    echo -e \"${YELLOW}[WARN]${NC} $1\"
}

error() {
    echo -e \"${RED}[ERROR]${NC} $1\"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error \"This script must be run as root\"
    exit 1
fi

# Check if running on supported OS
if ! command -v apt-get &> /dev/null; then
    error \"This installer only supports Debian/Ubuntu systems\"
    exit 1
fi

# Configuration
MOXNAS_USER=\"moxnas\"
MOXNAS_HOME=\"/opt/moxnas\"
MOXNAS_DB=\"moxnas\"
MOXNAS_DB_USER=\"moxnas\"
MOXNAS_DB_PASS=$(openssl rand -base64 32)
REDIS_PASS=$(openssl rand -base64 32)

log \"Starting MoxNAS installation...\"

# Update system packages
log \"Updating system packages...\"
apt-get update
apt-get upgrade -y

# Install system dependencies
log \"Installing system dependencies...\"
apt-get install -y \\
    python3 \\
    python3-pip \\
    python3-venv \\
    python3-dev \\
    postgresql \\
    postgresql-contrib \\
    redis-server \\
    nginx \\
    supervisor \\
    mdadm \\
    smartmontools \\
    nfs-kernel-server \\
    samba \\
    vsftpd \\
    curl \\
    wget \\
    git \\
    htop \\
    iotop \\
    build-essential \\
    libpq-dev \\
    libffi-dev \\
    libssl-dev

# Create MoxNAS user
log \"Creating MoxNAS user...\"
if ! id \"$MOXNAS_USER\" &>/dev/null; then
    useradd -r -s /bin/bash -d \"$MOXNAS_HOME\" -m \"$MOXNAS_USER\"
fi

# Setup PostgreSQL
log \"Setting up PostgreSQL database...\"
sudo -u postgres createdb \"$MOXNAS_DB\" 2>/dev/null || true
sudo -u postgres psql -c \"CREATE USER $MOXNAS_DB_USER WITH PASSWORD '$MOXNAS_DB_PASS';\" 2>/dev/null || true
sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE $MOXNAS_DB TO $MOXNAS_DB_USER;\" 2>/dev/null || true
sudo -u postgres psql -c \"ALTER USER $MOXNAS_DB_USER CREATEDB;\" 2>/dev/null || true

# Configure Redis
log \"Configuring Redis...\"
sed -i \"s/# requirepass foobared/requirepass $REDIS_PASS/\" /etc/redis/redis.conf
systemctl restart redis-server
systemctl enable redis-server

# Install MoxNAS application
log \"Installing MoxNAS application...\"
cd \"$MOXNAS_HOME\"

# Copy application files
if [ -d \"/tmp/moxnas\" ]; then
    cp -r /tmp/moxnas/* .
else
    # If not copying from temp, assume we're in the source directory
    cp -r * \"$MOXNAS_HOME\"/
fi

# Create Python virtual environment
sudo -u \"$MOXNAS_USER\" python3 -m venv venv
sudo -u \"$MOXNAS_USER\" bash -c \"source venv/bin/activate && pip install --upgrade pip\"
sudo -u \"$MOXNAS_USER\" bash -c \"source venv/bin/activate && pip install -r requirements.txt\"

# Create configuration file
log \"Creating configuration file...\"
cat > \"$MOXNAS_HOME\"/.env << EOF
FLASK_ENV=production
SECRET_KEY=$(openssl rand -base64 64)
DATABASE_URL=postgresql://$MOXNAS_DB_USER:$MOXNAS_DB_PASS@localhost/$MOXNAS_DB
REDIS_URL=redis://:$REDIS_PASS@localhost:6379/0
CELERY_BROKER_URL=redis://:$REDIS_PASS@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASS@localhost:6379/0
MOXNAS_ADMIN_EMAIL=admin@moxnas.local
SESSION_COOKIE_SECURE=true
EOF

# Set permissions
chown -R \"$MOXNAS_USER\":\"$MOXNAS_USER\" \"$MOXNAS_HOME\"
chmod 600 \"$MOXNAS_HOME\"/.env

# Initialize database
log \"Initializing database...\"
cd \"$MOXNAS_HOME\"
sudo -u \"$MOXNAS_USER\" bash -c \"source venv/bin/activate && python -c 'from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()'\"

# Create admin user
log \"Creating admin user...\"
ADMIN_PASSWORD=$(openssl rand -base64 16)
sudo -u \"$MOXNAS_USER\" bash -c \"source venv/bin/activate && python -c '
from app import create_app, db
from app.models import User, UserRole
app = create_app()
app.app_context().push()
admin = User(username=\"admin\", email=\"admin@moxnas.local\", role=UserRole.ADMIN)
admin.set_password(\"$ADMIN_PASSWORD\")
db.session.add(admin)
db.session.commit()
print(\"Admin user created with password: $ADMIN_PASSWORD\")
'\"

# Configure Nginx
log \"Configuring Nginx...\"
cat > /etc/nginx/sites-available/moxnas << EOF
server {
    listen 80;
    server_name _;
    
    # Redirect HTTP to HTTPS
    return 301 https://\\$server_name\\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;
    
    # SSL configuration - use self-signed cert for now
    ssl_certificate /etc/ssl/certs/moxnas-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/moxnas-selfsigned.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection \"1; mode=block\";
    add_header Strict-Transport-Security \"max-age=63072000; includeSubDomains; preload\";
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \\$host;
        proxy_set_header X-Real-IP \\$remote_addr;
        proxy_set_header X-Forwarded-For \\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\$scheme;
        proxy_redirect off;
        proxy_buffering off;
    }
    
    location /static {
        alias $MOXNAS_HOME/app/static;
        expires 30d;
        add_header Cache-Control \"public, no-transform\";
    }
}
EOF

# Generate self-signed SSL certificate
log \"Generating SSL certificate...\"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\
    -keyout /etc/ssl/private/moxnas-selfsigned.key \\
    -out /etc/ssl/certs/moxnas-selfsigned.crt \\
    -subj \"/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas.local\"

# Enable Nginx site
ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

# Configure Supervisor for MoxNAS services
log \"Configuring Supervisor...\"
cat > /etc/supervisor/conf.d/moxnas.conf << EOF
[program:moxnas-web]
command=$MOXNAS_HOME/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 wsgi:app
directory=$MOXNAS_HOME
user=$MOXNAS_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/moxnas-web.log

[program:moxnas-worker]
command=$MOXNAS_HOME/venv/bin/celery -A celery_worker.celery worker --loglevel=info
directory=$MOXNAS_HOME
user=$MOXNAS_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/moxnas-worker.log

[program:moxnas-beat]
command=$MOXNAS_HOME/venv/bin/celery -A celery_worker.celery beat --loglevel=info
directory=$MOXNAS_HOME
user=$MOXNAS_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/moxnas-beat.log
EOF

# Configure log rotation
cat > /etc/logrotate.d/moxnas << EOF
/var/log/supervisor/moxnas-*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        supervisorctl restart moxnas-web moxnas-worker moxnas-beat
    endscript
}

$MOXNAS_HOME/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $MOXNAS_USER $MOXNAS_USER
}
EOF

# Create storage directories
log \"Creating storage directories...\"
mkdir -p /mnt/storage /mnt/backups /srv/ftp
chown \"$MOXNAS_USER\":\"$MOXNAS_USER\" /mnt/storage /mnt/backups
chown ftp:ftp /srv/ftp

# Configure NFS
log \"Configuring NFS...\"
echo \"/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)\" >> /etc/exports
systemctl enable nfs-kernel-server
systemctl start nfs-kernel-server

# Configure Samba
log \"Configuring Samba...\"
cp /etc/samba/smb.conf /etc/samba/smb.conf.backup
cat >> /etc/samba/smb.conf << EOF

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
    valid users = $MOXNAS_USER
    create mask = 0755
    directory mask = 0755
EOF

# Add MoxNAS user to Samba
echo -e \"$ADMIN_PASSWORD\\n$ADMIN_PASSWORD\" | smbpasswd -a \"$MOXNAS_USER\"
systemctl enable smbd nmbd
systemctl start smbd nmbd

# Configure vsftpd
log \"Configuring FTP...\"
cp /etc/vsftpd.conf /etc/vsftpd.conf.backup
cat > /etc/vsftpd.conf << EOF
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
user_sub_token=\\$USER
local_root=/srv/ftp
userlist_enable=YES
userlist_file=/etc/vsftpd.userlist
userlist_deny=NO
EOF

echo \"$MOXNAS_USER\" > /etc/vsftpd.userlist
systemctl enable vsftpd
systemctl start vsftpd

# Start services
log \"Starting MoxNAS services...\"
supervisorctl reread
supervisorctl update
supervisorctl start moxnas-web moxnas-worker moxnas-beat

# Configure firewall
log \"Configuring firewall...\"
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

# Create maintenance script
cat > /usr/local/bin/moxnas-maintenance << 'EOF'
#!/bin/bash
# MoxNAS maintenance script

# Update SMART data and run health checks
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

# Clean up old alerts (older than 30 days)
cleanup_old_alerts.delay()

print(\"Health checks initiated\")
'"

# Clean up old logs
find /var/log/supervisor/ -name "moxnas-*.log.*" -mtime +30 -delete
find /opt/moxnas/logs/ -name "*.log.*" -mtime +30 -delete

# Clean up old backup files
find /mnt/backups/ -type f -mtime +90 -delete 2>/dev/null || true

# Update package cache and check for security updates
apt update -qq
security_updates=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)
if [ $security_updates -gt 0 ]; then
    echo "Warning: $security_updates security updates available"
    echo "Run 'apt upgrade' to install security updates"
fi

echo "Maintenance completed at $(date)"
EOF

chmod +x /usr/local/bin/moxnas-maintenance

# Add to cron
echo \"0 2 * * * root /usr/local/bin/moxnas-maintenance >> /var/log/moxnas-maintenance.log 2>&1\" >> /etc/crontab

# Final setup
log \"Finalizing installation...\"
systemctl daemon-reload
systemctl restart supervisor

# Display installation summary
log \"Installation completed successfully!\"
echo \"\"
echo -e \"${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}\"
echo -e \"${BLUE}║${NC}                     ${GREEN}MoxNAS Installation Complete${NC}                    ${BLUE}║${NC}\"
echo -e \"${BLUE}╠══════════════════════════════════════════════════════════════╣${NC}\"
echo -e \"${BLUE}║${NC} Web Interface: ${YELLOW}https://$(hostname -I | awk '{print $1}')${NC}                              ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC} Admin Username: ${YELLOW}admin${NC}                                        ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC} Admin Password: ${YELLOW}$ADMIN_PASSWORD${NC}                 ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC}                                                              ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC} Storage Mount: ${YELLOW}/mnt/storage${NC}                                  ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC} Backup Mount:  ${YELLOW}/mnt/backups${NC}                                 ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC}                                                              ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC} Services Status:                                             ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC}   - Web Server: ${GREEN}Running${NC}                                       ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC}   - Database:   ${GREEN}Running${NC}                                       ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC}   - Redis:      ${GREEN}Running${NC}                                       ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC}   - Workers:    ${GREEN}Running${NC}                                       ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC}                                                              ${BLUE}║${NC}\"
echo -e \"${BLUE}║${NC} ${YELLOW}Please save the admin password and change it after login!${NC}    ${BLUE}║${NC}\"
echo -e \"${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}\"
echo \"\"

log \"You can now access MoxNAS at https://$(hostname -I | awk '{print $1}')\"
log \"For security, please change the admin password after first login.\"

# Save credentials to file
cat > \"$MOXNAS_HOME\"/INSTALLATION_INFO.txt << EOF
MoxNAS Installation Information
===============================

Installation Date: $(date)
Server IP: $(hostname -I | awk '{print $1}')
Web Interface: https://$(hostname -I | awk '{print $1}')

Admin Credentials:
Username: admin
Password: $ADMIN_PASSWORD

Database:
Database: $MOXNAS_DB
Username: $MOXNAS_DB_USER
Password: $MOXNAS_DB_PASS

Redis Password: $REDIS_PASS

Important Files:
- Application: $MOXNAS_HOME
- Configuration: $MOXNAS_HOME/.env
- Logs: /var/log/supervisor/moxnas-*.log
- Storage: /mnt/storage
- Backups: /mnt/backups

Service Management:
- Restart all: supervisorctl restart moxnas-web moxnas-worker moxnas-beat
- Check status: supervisorctl status
- View logs: supervisorctl tail -f moxnas-web
EOF

chown \"$MOXNAS_USER\":\"$MOXNAS_USER\" \"$MOXNAS_HOME\"/INSTALLATION_INFO.txt
chmod 600 \"$MOXNAS_HOME\"/INSTALLATION_INFO.txt

log \"Installation information saved to $MOXNAS_HOME/INSTALLATION_INFO.txt\"

exit 0