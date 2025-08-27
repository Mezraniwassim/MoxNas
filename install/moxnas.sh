#!/usr/bin/env bash

# MoxNAS Installation Script for Community Scripts
# This script runs inside the LXC container

set -e

# Colors for output
YW='\033[33m'
RD='\033[01;31m'
BL='\033[36m'
GN='\033[1;92m'
CL='\033[m'

function msg_info() {
    echo -e "${BL}[INFO]${CL} $1"
}

function msg_ok() {
    echo -e "${GN}[OK]${CL} $1"
}

function msg_error() {
    echo -e "${RD}[ERROR]${CL} $1"
    exit 1
}

msg_info "Starting MoxNAS installation"

# Update system and install dependencies
msg_info "Updating system packages"
apt-get update && apt-get -y upgrade

# Install system packages
msg_info "Installing system packages"
apt-get -y install curl wget git sudo mc htop

# Install Python and development tools
msg_info "Installing Python and development tools"
apt-get -y install python3 python3-pip python3-venv python3-dev build-essential

# Install database and cache services
msg_info "Installing database services"
apt-get -y install postgresql postgresql-contrib redis-server

# Install web server
msg_info "Installing web server"
apt-get -y install nginx

# Install NFS and SMB services
msg_info "Installing network services"
apt-get -y install nfs-kernel-server samba samba-common-bin

# Install FTP server
msg_info "Installing FTP server"
apt-get -y install vsftpd

# Install storage management tools
msg_info "Installing storage tools"
apt-get -y install lvm2 smartmontools parted

# Create MoxNAS user and application directory
msg_info "Creating MoxNAS user and directory"
adduser --system --group --disabled-password --home /opt/moxnas moxnas
mkdir -p /opt/moxnas
chown moxnas:moxnas /opt/moxnas

# Clone MoxNAS repository
msg_info "Cloning MoxNAS repository"
cd /opt/moxnas
git clone https://github.com/Mezraniwassim/MoxNas.git .
rm -rf .git

# Set ownership
chown -R moxnas:moxnas /opt/moxnas

# Create Python virtual environment
msg_info "Setting up Python environment"
sudo -u moxnas python3 -m venv venv
sudo -u moxnas bash -c 'source venv/bin/activate && pip install --upgrade pip'
sudo -u moxnas bash -c 'source venv/bin/activate && pip install -r requirements.txt'

# Configure PostgreSQL
msg_info "Configuring PostgreSQL database"
sudo -u postgres psql -c "CREATE USER moxnas WITH PASSWORD 'moxnas1234';"
sudo -u postgres psql -c "CREATE DATABASE moxnas_db OWNER moxnas;"

# Configure Redis
msg_info "Configuring Redis"
echo 'requirepass moxnas1234' >> /etc/redis/redis.conf
systemctl restart redis-server

# Create application configuration
msg_info "Creating application configuration"
mkdir -p /opt/moxnas/config
cat > /opt/moxnas/config/production.py << 'EOF'
import os

class ProductionConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'moxnas-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = 'postgresql://moxnas:moxnas1234@localhost/moxnas_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CELERY_BROKER_URL = 'redis://:moxnas1234@localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://:moxnas1234@localhost:6379/0'
    REDIS_URL = 'redis://:moxnas1234@localhost:6379/1'
EOF

# Initialize database
msg_info "Initializing database"
sudo -u moxnas bash -c 'cd /opt/moxnas && source venv/bin/activate && python migrate.py'

# Create admin user
msg_info "Creating admin user"
sudo -u moxnas bash -c 'cd /opt/moxnas && source venv/bin/activate && python -c "
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app(\"production\")
with app.app_context():
    admin = User.query.filter_by(username=\"admin\").first()
    if not admin:
        admin = User(
            username=\"admin\",
            email=\"admin@moxnas.local\",
            password_hash=generate_password_hash(\"moxnas1234\"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print(\"Admin user created\")
    else:
        print(\"Admin user already exists\")
"'

# Configure systemd services
msg_info "Setting up systemd services"
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
msg_info "Configuring web server"
cat > /etc/nginx/sites-available/moxnas << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name _;
    return 301 https://$server_name$request_uri;
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
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Generate SSL certificate
msg_info "Generating SSL certificate"
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/moxnas.key \
    -out /etc/ssl/certs/moxnas.crt \
    -subj '/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas' 2>/dev/null

# Enable Nginx site
ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Configure SMB
msg_info "Configuring network shares"
mkdir -p /mnt/storage
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

# Set SMB password
(echo 'moxnas1234'; echo 'moxnas1234') | smbpasswd -a root

# Configure NFS
echo '/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)' >> /etc/exports

# Configure FTP
sed -i 's/#write_enable=YES/write_enable=YES/' /etc/vsftpd.conf
sed -i 's/#local_enable=YES/local_enable=YES/' /etc/vsftpd.conf

# Enable and start all services
msg_info "Starting services"
systemctl daemon-reload
systemctl enable postgresql redis-server nginx smbd nmbd nfs-kernel-server vsftpd
systemctl enable moxnas moxnas-worker

# Start services
systemctl start postgresql redis-server
systemctl start nginx smbd nmbd nfs-kernel-server vsftpd
systemctl start moxnas moxnas-worker

# Save credentials
echo 'Username: admin' > /opt/moxnas/.admin_credentials
echo 'Password: moxnas1234' >> /opt/moxnas/.admin_credentials

# Create storage test
echo 'MoxNAS Storage Test' > /mnt/storage/README.txt

msg_ok "MoxNAS installation completed successfully!"

# Cleanup
apt-get autoremove -y
apt-get autoclean
msg_ok "Cleanup completed"