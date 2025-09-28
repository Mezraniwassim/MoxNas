#!/bin/bash

# MoxNAS GitHub Installation Script
# Downloads and installs MoxNAS directly from GitHub repository

set -euo pipefail

# Colors for output
YW='\033[33m'
RD='\033[01;31m'
BL='\033[36m'
GN='\033[1;92m'
CL='\033[m'
BOLD='\033[1m'

# Configuration
GITHUB_REPO="https://github.com/Mezraniwassim/MoxNas.git"
MOXNAS_USER="moxnas"
MOXNAS_HOME="/opt/moxnas"
DB_NAME="moxnas_db"
DB_USER="moxnas"
DB_PASS="moxnas1234"
ADMIN_PASS="moxnas1234"

msg_info() { echo -e "${BL}[INFO]${CL} $1"; }
msg_ok() { echo -e "${GN}[OK]${CL} $1"; }
msg_error() { echo -e "${RD}[ERROR]${CL} $1"; exit 1; }
msg_warn() { echo -e "${YW}[WARN]${CL} $1"; }

header_info() {
    cat << 'EOF'
    __  ___          _   ___   ___   _____
   /  |/  /___  _  _/ | / / | / __\ / ___/
  / /|_/ / __ \| |/_/  |/ /  |/ /_\  \__ \ 
 / /  / / /_/ />  </ /|  / /|  __/  ___/ /
/_/  /_/\____/_/|_/_/ |_/_/ |_/    /____/ 

Network Attached Storage - GitHub Installation
Repository: https://github.com/Mezraniwassim/MoxNas
EOF
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        msg_error "This script must be run as root. Use: sudo $0"
    fi
}

install_system_packages() {
    msg_info "Updating system and installing packages..."
    
    export DEBIAN_FRONTEND=noninteractive
    
    # Update package lists
    apt-get update
    
    # Install essential packages
    apt-get install -y \
        curl wget git sudo mc htop nano net-tools \
        python3 python3-pip python3-venv python3-dev build-essential \
        postgresql postgresql-contrib redis-server \
        nginx \
        nfs-kernel-server samba samba-common-bin vsftpd \
        lvm2 smartmontools parted \
        supervisor
    
    msg_ok "System packages installed"
}

download_moxnas() {
    msg_info "Downloading MoxNAS from GitHub..."
    
    # Remove existing directory if it exists
    if [ -d "$MOXNAS_HOME" ]; then
        rm -rf "$MOXNAS_HOME"
    fi
    
    # Create MoxNAS user if doesn't exist
    if ! id "$MOXNAS_USER" &>/dev/null; then
        adduser --system --group --disabled-password --home "$MOXNAS_HOME" --shell /bin/bash "$MOXNAS_USER"
    fi
    
    # Clone repository
    git clone "$GITHUB_REPO" "$MOXNAS_HOME"
    
    # Create additional directories
    mkdir -p /mnt/storage /mnt/backups
    
    # Set ownership
    chown -R "$MOXNAS_USER:$MOXNAS_USER" "$MOXNAS_HOME"
    chmod 755 /mnt/storage /mnt/backups
    
    msg_ok "MoxNAS downloaded and user created"
}

setup_python_environment() {
    msg_info "Setting up Python environment..."
    
    cd "$MOXNAS_HOME"
    
    # Create Python virtual environment
    sudo -u "$MOXNAS_USER" python3 -m venv venv
    sudo -u "$MOXNAS_USER" bash -c "source venv/bin/activate && pip install --upgrade pip setuptools wheel"
    sudo -u "$MOXNAS_USER" bash -c "source venv/bin/activate && pip install -r requirements.txt"
    
    msg_ok "Python environment setup completed"
}

configure_database() {
    msg_info "Configuring PostgreSQL database..."
    
    # Start PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;" || true
    sudo -u postgres psql -c "DROP USER IF EXISTS $DB_USER;" || true
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    
    msg_ok "Database configured"
}

configure_redis() {
    msg_info "Configuring Redis..."
    
    # Configure Redis with password
    if ! grep -q "requirepass" /etc/redis/redis.conf; then
        echo "requirepass $DB_PASS" >> /etc/redis/redis.conf
    fi
    systemctl restart redis-server
    systemctl enable redis-server
    
    msg_ok "Redis configured"
}

setup_environment() {
    msg_info "Setting up environment configuration..."
    
    # Create environment file
    cat > "$MOXNAS_HOME/.env" << EOF
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost/$DB_NAME
REDIS_URL=redis://:$DB_PASS@localhost:6379/0
CELERY_BROKER_URL=redis://:$DB_PASS@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:$DB_PASS@localhost:6379/0
FLASK_ENV=production
FLASK_CONFIG=production
MOXNAS_STORAGE_ROOT=/mnt/storage
MOXNAS_BACKUP_ROOT=/mnt/backups
EOF
    
    chown "$MOXNAS_USER:$MOXNAS_USER" "$MOXNAS_HOME/.env"
    
    msg_ok "Environment configured"
}

initialize_database() {
    msg_info "Initializing database and creating admin user..."
    
    cd "$MOXNAS_HOME"
    
    # Initialize database
    sudo -u "$MOXNAS_USER" bash -c "source venv/bin/activate && source .env && python migrate.py upgrade"
    
    # Create admin user
    sudo -u "$MOXNAS_USER" bash -c "source venv/bin/activate && source .env && python -c \"
from app import create_app, db
from app.models import User, UserRole
import sys

app = create_app('production')
with app.app_context():
    try:
        # Delete existing admin if exists
        existing_admin = User.query.filter_by(username='admin').first()
        if existing_admin:
            db.session.delete(existing_admin)
            db.session.commit()
        
        # Create new admin user
        admin = User(
            username='admin',
            email='admin@moxnas.local',
            first_name='System',
            last_name='Administrator',
            role=UserRole.ADMIN,
            is_active=True
        )
        admin.set_password('$ADMIN_PASS')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created successfully')
    except Exception as e:
        print(f'Error creating admin user: {e}')
        sys.exit(1)
\""
    
    msg_ok "Database initialized"
}

setup_systemd_services() {
    msg_info "Setting up systemd services..."
    
    # MoxNAS main service
    cat > /etc/systemd/system/moxnas.service << EOF
[Unit]
Description=MoxNAS Web Application
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=exec
User=$MOXNAS_USER
Group=$MOXNAS_USER
WorkingDirectory=$MOXNAS_HOME
EnvironmentFile=$MOXNAS_HOME/.env
ExecStart=$MOXNAS_HOME/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 wsgi:app
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

    # MoxNAS worker service
    cat > /etc/systemd/system/moxnas-worker.service << EOF
[Unit]
Description=MoxNAS Celery Worker
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=exec
User=$MOXNAS_USER
Group=$MOXNAS_USER
WorkingDirectory=$MOXNAS_HOME
EnvironmentFile=$MOXNAS_HOME/.env
ExecStart=$MOXNAS_HOME/venv/bin/python celery_worker.py
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF
    
    msg_ok "Services configured"
}

configure_nginx() {
    msg_info "Configuring Nginx..."
    
    # Create SSL certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/moxnas.key \
        -out /etc/ssl/certs/moxnas.crt \
        -subj '/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas' 2>/dev/null
    
    # Nginx configuration
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
        add_header Cache-Control "public, immutable";
    }
}
EOF
    
    # Enable site
    ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    msg_ok "Nginx configured"
}

configure_file_sharing() {
    msg_info "Configuring file sharing services..."
    
    # SMB configuration
    cat >> /etc/samba/smb.conf << EOF

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
    (echo "$ADMIN_PASS"; echo "$ADMIN_PASS") | smbpasswd -a root
    
    # NFS exports
    if ! grep -q "/mnt/storage" /etc/exports; then
        echo '/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)' >> /etc/exports
    fi
    if ! grep -q "/mnt/backups" /etc/exports; then
        echo '/mnt/backups *(rw,sync,no_subtree_check,no_root_squash)' >> /etc/exports
    fi
    
    # Configure FTP
    sed -i 's/#write_enable=YES/write_enable=YES/' /etc/vsftpd.conf
    sed -i 's/#local_enable=YES/local_enable=YES/' /etc/vsftpd.conf
    
    msg_ok "File sharing configured"
}

start_services() {
    msg_info "Starting all services..."
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable postgresql redis-server nginx smbd nmbd nfs-kernel-server vsftpd
    systemctl enable moxnas moxnas-worker
    
    # Start services
    systemctl start postgresql redis-server
    systemctl restart nginx
    systemctl start smbd nmbd nfs-kernel-server vsftpd
    systemctl start moxnas moxnas-worker
    
    msg_ok "Services started"
}

create_test_data() {
    msg_info "Creating test data..."
    
    # Create test files
    echo "MoxNAS Storage Test - $(date)" > /mnt/storage/README.txt
    echo "Welcome to MoxNAS - Your Network Attached Storage Solution" > /mnt/storage/welcome.txt
    
    # Create credentials file
    cat > "$MOXNAS_HOME/.admin_credentials" << EOF
Installation completed: $(date)
Repository: $GITHUB_REPO

Web Interface: https://localhost
Web Interface: https://$(hostname -I | awk '{print $1}')
Username: admin
Password: $ADMIN_PASS

Database: $DB_NAME
DB User: $DB_USER
DB Password: $DB_PASS

SMB Share: //localhost/moxnas-storage
NFS Share: localhost:/mnt/storage
FTP: ftp://localhost
EOF
    
    chown "$MOXNAS_USER:$MOXNAS_USER" "$MOXNAS_HOME/.admin_credentials"
    
    msg_ok "Test data created"
}

show_completion() {
    local server_ip=$(hostname -I | awk '{print $1}')
    
    echo -e "\n${BOLD}🎉 MoxNAS Installation Completed Successfully!${CL}"
    echo "================================================================"
    echo -e "${BOLD}Repository:${CL} $GITHUB_REPO"
    echo -e "${BOLD}Installation Time:${CL} $(date)"
    echo
    echo -e "${BOLD}Access Information:${CL}"
    echo "  Web Interface: https://localhost"
    echo "  Web Interface: https://$server_ip"
    echo "  Username: admin"
    echo "  Password: $ADMIN_PASS"
    echo
    echo -e "${BOLD}File Sharing:${CL}"
    echo "  SMB/CIFS: //localhost/moxnas-storage"
    echo "  SMB/CIFS: //$server_ip/moxnas-storage"
    echo "  NFS: localhost:/mnt/storage"
    echo "  NFS: $server_ip:/mnt/storage"
    echo "  FTP: ftp://localhost"
    echo "  FTP: ftp://$server_ip"
    echo
    echo -e "${BOLD}Service Management:${CL}"
    echo "  Start: sudo systemctl start moxnas moxnas-worker"
    echo "  Stop: sudo systemctl stop moxnas moxnas-worker"
    echo "  Status: sudo systemctl status moxnas"
    echo "  Logs: sudo journalctl -u moxnas -f"
    echo
    echo -e "${BOLD}Storage Locations:${CL}"
    echo "  Application: $MOXNAS_HOME"
    echo "  Storage: /mnt/storage"
    echo "  Backups: /mnt/backups"
    echo "  Credentials: $MOXNAS_HOME/.admin_credentials"
    echo
    echo -e "${BOLD}One-liner Installation Command:${CL}"
    echo "  curl -fsSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-from-github.sh | sudo bash"
    echo
    echo -e "${YW}⚠️  Important Security Notes:${CL}"
    echo "  - Change default passwords immediately"
    echo "  - Configure firewall rules as needed"
    echo "  - Set up proper SSL certificates for production"
    echo "  - Review and adjust file sharing permissions"
    echo
    echo -e "${GN}✅ MoxNAS is ready for use!${CL}"
}

main() {
    clear
    header_info
    echo
    
    msg_info "Starting automated MoxNAS installation from GitHub..."
    
    check_root
    install_system_packages
    download_moxnas
    setup_python_environment
    configure_database
    configure_redis
    setup_environment
    initialize_database
    setup_systemd_services
    configure_nginx
    configure_file_sharing
    start_services
    create_test_data
    
    show_completion
}

# Run main function
main "$@"