#!/usr/bin/env bash

# MoxNAS Deployment Script for LXC Containers
# This script can be run inside any LXC container to install MoxNAS
# Compatible with containers created by Proxmox VE Helper-Scripts

set -euo pipefail

# Script Configuration
SCRIPT_VERSION="2.0.0"
APP_NAME="MoxNAS"
INSTALL_DIR="/opt/moxnas"
MOXNAS_USER="moxnas"
DB_NAME="moxnas_db"
DB_USER="moxnas"
DB_PASS="moxnas1234"
ADMIN_PASS="moxnas1234"

# Colors for output
YW='\033[33m'
RD='\033[01;31m'
BL='\033[36m'
GN='\033[1;92m'
CL='\033[m'
BOLD='\033[1m'

# Logging functions
log() {
    echo -e "${BL}[INFO]${CL} $1"
}

success() {
    echo -e "${GN}[OK]${CL} $1"
}

error() {
    echo -e "${RD}[ERROR]${CL} $1"
    exit 1
}

warn() {
    echo -e "${YW}[WARN]${CL} $1"
}

# Header
header() {
    cat << 'EOF'
    __  ___          _   ___   ___   _____
   /  |/  /___  _  _/ | / / | / __\ / ___/
  / /|_/ / __ \| |/_/  |/ /  |/ /_\  \__ \ 
 / /  / / /_/ />  </ /|  / /|  __/  ___/ /
/_/  /_/\____/_/|_/_/ |_/_/ |_/    /____/ 

Professional NAS Solution for LXC Containers
EOF
}

# Check if running in container
check_container() {
    if [[ ! -f /proc/1/environ ]] || ! grep -q container /proc/1/environ 2>/dev/null; then
        warn "This script is designed to run inside an LXC container"
        warn "Detected environment may not be containerized"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    success "Container environment detected"
}

# Check if script is run as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi
    success "Running as root"
}

# Update system packages
update_system() {
    log "Updating system packages..."
    
    export DEBIAN_FRONTEND=noninteractive
    
    # Update package lists
    apt-get update
    
    # Upgrade existing packages
    apt-get -y upgrade
    
    # Install essential packages
    apt-get -y install \
        curl wget git sudo mc htop nano \
        build-essential pkg-config \
        ca-certificates gnupg lsb-release \
        software-properties-common \
        apt-transport-https
    
    success "System packages updated"
}

# Install Python ecosystem
install_python() {
    log "Installing Python development environment..."
    
    apt-get -y install \
        python3 python3-pip python3-venv \
        python3-dev python3-setuptools \
        libpython3-dev
    
    # Ensure pip is up to date
    python3 -m pip install --upgrade pip
    
    success "Python environment installed"
}

# Install database services
install_databases() {
    log "Installing database services..."
    
    # Install PostgreSQL
    apt-get -y install postgresql postgresql-contrib postgresql-client
    
    # Install Redis
    apt-get -y install redis-server
    
    # Start and enable services
    systemctl start postgresql redis-server
    systemctl enable postgresql redis-server
    
    success "Database services installed and started"
}

# Install web server and networking
install_web_services() {
    log "Installing web server and file sharing services..."
    
    # Web server
    apt-get -y install nginx
    
    # File sharing services
    apt-get -y install \
        nfs-kernel-server \
        samba samba-common-bin \
        vsftpd
    
    # Networking tools
    apt-get -y install \
        net-tools nmap netcat \
        rsync cifs-utils
    
    success "Web and file sharing services installed"
}

# Install storage management tools
install_storage_tools() {
    log "Installing storage management tools..."
    
    apt-get -y install \
        lvm2 mdadm smartmontools \
        parted gdisk fdisk \
        xfsprogs e2fsprogs \
        zfsutils-linux || warn "ZFS tools not available (normal for some containers)"
    
    # System monitoring tools
    apt-get -y install \
        htop iotop lsof \
        sysstat vnstat
    
    success "Storage management tools installed"
}

# Create MoxNAS user and directories
create_user_directories() {
    log "Creating MoxNAS user and directory structure..."
    
    # Create system user for MoxNAS
    if ! id "$MOXNAS_USER" &>/dev/null; then
        adduser --system --group --disabled-password \
                --home "$INSTALL_DIR" \
                --shell /bin/bash \
                --gecos "MoxNAS System User" \
                "$MOXNAS_USER"
    fi
    
    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p /mnt/storage /mnt/backups
    mkdir -p /var/log/moxnas
    mkdir -p /etc/moxnas
    
    # Set ownership
    chown "$MOXNAS_USER:$MOXNAS_USER" "$INSTALL_DIR"
    chown "$MOXNAS_USER:$MOXNAS_USER" /var/log/moxnas
    chmod 755 /mnt/storage /mnt/backups
    
    success "User and directories created"
}

# Download and install MoxNAS application
install_moxnas_app() {
    log "Downloading MoxNAS application..."
    
    cd "$INSTALL_DIR"
    
    # Clone repository
    if [[ -d .git ]]; then
        log "Updating existing MoxNAS installation..."
        sudo -u "$MOXNAS_USER" git pull origin master
    else
        log "Cloning MoxNAS repository..."
        sudo -u "$MOXNAS_USER" git clone https://github.com/Mezraniwassim/MoxNas.git .
        sudo -u "$MOXNAS_USER" rm -rf .git
    fi
    
    # Ensure ownership
    chown -R "$MOXNAS_USER:$MOXNAS_USER" "$INSTALL_DIR"
    
    success "MoxNAS application downloaded"
}

# Setup Python virtual environment
setup_python_env() {
    log "Setting up Python virtual environment..."
    
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    if [[ ! -d venv ]]; then
        sudo -u "$MOXNAS_USER" python3 -m venv venv
    fi
    
    # Upgrade pip and install dependencies
    sudo -u "$MOXNAS_USER" bash -c '
        source venv/bin/activate
        pip install --upgrade pip setuptools wheel
        pip install -r requirements.txt
    '
    
    success "Python environment configured"
}

# Configure PostgreSQL database
configure_database() {
    log "Configuring PostgreSQL database..."
    
    # Start PostgreSQL if not running
    systemctl start postgresql
    
    # Create database and user
    sudo -u postgres psql << EOF
CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
CREATE DATABASE $DB_NAME OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;
EOF
    
    success "PostgreSQL database configured"
}

# Configure Redis
configure_redis() {
    log "Configuring Redis cache..."
    
    # Configure Redis authentication
    if ! grep -q "^requirepass" /etc/redis/redis.conf; then
        echo "requirepass $DB_PASS" >> /etc/redis/redis.conf
        systemctl restart redis-server
    fi
    
    success "Redis cache configured"
}

# Create application configuration
create_app_config() {
    log "Creating application configuration..."
    
    # Create production configuration
    cat > "$INSTALL_DIR/config/production.py" << EOF
import os
from datetime import timedelta

class ProductionConfig:
    # Basic Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'moxnas-secret-key-$(openssl rand -hex 32)')
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = 'postgresql://$DB_USER:$DB_PASS@localhost/$DB_NAME'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Redis configuration
    REDIS_URL = 'redis://localhost:6379/0'
    CELERY_BROKER_URL = 'redis://localhost:6379/0' 
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    
    # Security settings
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Application settings
    MAIL_SERVER = 'localhost'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    
    # File upload settings
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = '/var/log/moxnas/moxnas.log'
    
    # Storage paths
    STORAGE_ROOT = '/mnt/storage'
    BACKUP_ROOT = '/mnt/backups'
EOF

    chown "$MOXNAS_USER:$MOXNAS_USER" "$INSTALL_DIR/config/production.py"
    
    success "Application configuration created"
}

# Initialize database
initialize_database() {
    log "Initializing MoxNAS database..."
    
    cd "$INSTALL_DIR"
    
    # Run database migrations
    sudo -u "$MOXNAS_USER" bash -c '
        export FLASK_ENV=production
        source venv/bin/activate
        python migrate.py upgrade
    '
    
    success "Database initialized"
}

# Create admin user
create_admin_user() {
    log "Creating admin user..."
    
    cd "$INSTALL_DIR"
    
    # Create admin user with all required fields
    sudo -u "$MOXNAS_USER" bash -c "
        export FLASK_ENV=production
        source venv/bin/activate
        python -c \"
from app import create_app, db
from app.models import User, UserRole

app = create_app('production')
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
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
    else:
        print('Admin user already exists')
\"
    "
    
    success "Admin user configured"
}

# Create systemd services
create_services() {
    log "Creating systemd services..."
    
    # Main MoxNAS service
    cat > /etc/systemd/system/moxnas.service << EOF
[Unit]
Description=MoxNAS Web Application
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=exec
User=$MOXNAS_USER
Group=$MOXNAS_USER
WorkingDirectory=$INSTALL_DIR
Environment=FLASK_ENV=production
Environment=FLASK_CONFIG=production
ExecStart=$INSTALL_DIR/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 4 --timeout 120 wsgi:app
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

    # Celery worker service
    cat > /etc/systemd/system/moxnas-worker.service << EOF
[Unit]
Description=MoxNAS Celery Worker
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=exec
User=$MOXNAS_USER
Group=$MOXNAS_USER
WorkingDirectory=$INSTALL_DIR
Environment=FLASK_ENV=production
Environment=FLASK_CONFIG=production
ExecStart=$INSTALL_DIR/venv/bin/python celery_worker.py
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

    # Celery beat scheduler service
    cat > /etc/systemd/system/moxnas-beat.service << EOF
[Unit]
Description=MoxNAS Celery Beat Scheduler
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=exec
User=$MOXNAS_USER
Group=$MOXNAS_USER
WorkingDirectory=$INSTALL_DIR
Environment=FLASK_ENV=production
Environment=FLASK_CONFIG=production
ExecStart=$INSTALL_DIR/venv/bin/python celery_beat_config.py
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    
    success "Systemd services created"
}

# Configure Nginx reverse proxy
configure_nginx() {
    log "Configuring Nginx reverse proxy..."
    
    # Generate SSL certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/moxnas.key \
        -out /etc/ssl/certs/moxnas.crt \
        -subj "/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas" 2>/dev/null
    
    # Create Nginx configuration
    cat > /etc/nginx/sites-available/moxnas << 'EOF'
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name _;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name _;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/moxnas.crt;
    ssl_certificate_key /etc/ssl/private/moxnas.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains";
    
    # File upload size
    client_max_body_size 500M;
    
    # Proxy to MoxNAS
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files
    location /static {
        alias $INSTALL_DIR/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test configuration
    nginx -t
    
    success "Nginx configuration completed"
}

# Configure file sharing services
configure_file_sharing() {
    log "Configuring file sharing services..."
    
    # SMB/CIFS configuration
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
    force user = root
    force group = root

[moxnas-backups]
    comment = MoxNAS Backups
    path = /mnt/backups
    browseable = yes
    writable = yes
    guest ok = no
    valid users = root
    create mask = 0755
    directory mask = 0755
    force user = root
    force group = root
EOF

    # Set SMB password
    (echo "$ADMIN_PASS"; echo "$ADMIN_PASS") | smbpasswd -a root -s
    
    # NFS exports
    cat >> /etc/exports << EOF
/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)
/mnt/backups *(rw,sync,no_subtree_check,no_root_squash)
EOF

    # FTP configuration
    sed -i 's/#write_enable=YES/write_enable=YES/' /etc/vsftpd.conf
    sed -i 's/#local_enable=YES/local_enable=YES/' /etc/vsftpd.conf
    
    success "File sharing configured"
}

# Start all services
start_services() {
    log "Starting all services..."
    
    # Enable services
    systemctl enable postgresql redis-server nginx
    systemctl enable smbd nmbd nfs-kernel-server vsftpd  
    systemctl enable moxnas moxnas-worker moxnas-beat
    
    # Start core services
    systemctl start postgresql redis-server
    systemctl start nginx
    systemctl start smbd nmbd nfs-kernel-server vsftpd
    
    # Start MoxNAS services
    systemctl start moxnas moxnas-worker moxnas-beat
    
    success "All services started"
}

# Create test files and save credentials
finalize_installation() {
    log "Finalizing installation..."
    
    # Save credentials
    cat > "$INSTALL_DIR/.admin_credentials" << EOF
=== MoxNAS Admin Credentials ===
Username: admin
Password: $ADMIN_PASS
Database: $DB_NAME  
DB Password: $DB_PASS
Web Interface: https://$(hostname -I | awk '{print $1}')
Installation Date: $(date)
EOF

    chmod 600 "$INSTALL_DIR/.admin_credentials"
    chown "$MOXNAS_USER:$MOXNAS_USER" "$INSTALL_DIR/.admin_credentials"
    
    # Create test files
    echo "MoxNAS Storage Test - $(date)" > /mnt/storage/README.txt
    echo "MoxNAS Backup Directory - $(date)" > /mnt/backups/README.txt
    
    # Set permissions
    chmod 644 /mnt/storage/README.txt /mnt/backups/README.txt
    
    success "Installation finalized"
}

# Display completion information
show_completion() {
    local container_ip=$(hostname -I | awk '{print $1}')
    
    clear
    header
    echo
    echo -e "${BOLD}🎉 MoxNAS Installation Completed Successfully!${CL}"
    echo "=============================================="
    echo
    echo -e "${BOLD}Access Information:${CL}"
    echo "  Web Interface: https://$container_ip"
    echo "  Username: admin"
    echo "  Password: $ADMIN_PASS"
    echo
    echo -e "${BOLD}File Sharing:${CL}"
    echo "  SMB Share: //$container_ip/moxnas-storage"
    echo "  NFS Export: $container_ip:/mnt/storage"
    echo "  FTP Server: ftp://$container_ip"
    echo
    echo -e "${BOLD}Service Management:${CL}"
    echo "  Check status: systemctl status moxnas"
    echo "  View logs: journalctl -u moxnas -f"
    echo "  Restart: systemctl restart moxnas"
    echo
    echo -e "${BOLD}Next Steps:${CL}"
    echo "  1. Access the web interface and change default password"
    echo "  2. Configure storage pools and RAID arrays" 
    echo "  3. Set up network shares and user accounts"
    echo "  4. Configure backup jobs and monitoring alerts"
    echo "  5. Install proper SSL certificate for production use"
    echo
    echo -e "${YW}⚠️  Important Security Notes:${CL}"
    echo "  - Change all default passwords immediately"
    echo "  - Configure firewall rules as needed"
    echo "  - Review file sharing permissions"
    echo "  - Enable 2FA for admin accounts"
    echo
    echo -e "${GN}✅ MoxNAS is ready for use!${CL}"
    echo
}

# Main installation function
main() {
    clear
    header
    echo -e "\n${BOLD}Professional NAS Solution for LXC Containers v$SCRIPT_VERSION${CL}"
    echo
    
    log "Starting MoxNAS installation..."
    
    # Pre-installation checks
    check_root
    check_container
    
    # System preparation
    update_system
    install_python
    install_databases
    install_web_services
    install_storage_tools
    
    # Application installation
    create_user_directories
    install_moxnas_app
    setup_python_env
    
    # Database configuration
    configure_database
    configure_redis
    create_app_config
    initialize_database
    create_admin_user
    
    # Service configuration
    create_services
    configure_nginx
    configure_file_sharing
    
    # Start everything
    start_services
    finalize_installation
    
    # Show completion
    show_completion
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "MoxNAS Deployment Script for LXC Containers"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "This script installs MoxNAS inside an LXC container."
        echo "It's designed to work with containers created by Proxmox VE Helper-Scripts."
        echo
        echo "Options:"
        echo "  --help    Show this help message"
        echo
        echo "The script will:"
        echo "  - Install all required dependencies"
        echo "  - Configure PostgreSQL and Redis"
        echo "  - Set up MoxNAS web application"
        echo "  - Configure file sharing (SMB/NFS/FTP)"
        echo "  - Create systemd services"
        echo "  - Generate SSL certificates"
        echo
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
