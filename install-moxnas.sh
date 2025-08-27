#!/usr/bin/env bash
#
# MoxNAS One-Line Installation Script
# Professional Network Attached Storage for Proxmox LXC Containers
#
# Usage: bash <(curl -s https://raw.githubusercontent.com/moxnas/moxnas/main/install-moxnas.sh)
#
# Copyright (c) 2024 MoxNAS Team
# License: MIT

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
MOXNAS_USER="moxnas"
MOXNAS_HOME="/opt/moxnas"
MOXNAS_DB="moxnas"
MOXNAS_DB_USER="moxnas"
INSTALL_LOG="/var/log/moxnas-install.log"

# Global variables for generated passwords
MOXNAS_DB_PASS=""
REDIS_PASS=""
ADMIN_PASSWORD=""
SECRET_KEY=""

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $1" | tee -a "$INSTALL_LOG"
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] $1" | tee -a "$INSTALL_LOG"
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $1" | tee -a "$INSTALL_LOG"
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $1" | tee -a "$INSTALL_LOG"
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        exit 1
    fi
}

# Check if running on supported OS
check_os() {
    if [[ -f /etc/debian_version ]]; then
        OS="debian"
        DISTRO=$(lsb_release -si 2>/dev/null || echo "Debian")
        VERSION=$(lsb_release -sr 2>/dev/null || cat /etc/debian_version)
        log "Detected OS: $DISTRO $VERSION"
    elif [[ -f /etc/ubuntu_version ]] || grep -q "Ubuntu" /etc/issue 2>/dev/null; then
        OS="ubuntu"
        DISTRO="Ubuntu"
        VERSION=$(lsb_release -sr 2>/dev/null || grep -oP 'Ubuntu \K[\d.]+' /etc/issue)
        log "Detected OS: $DISTRO $VERSION"
    else
        error "This installer only supports Debian and Ubuntu systems"
        exit 1
    fi
}

# Generate secure random passwords
generate_passwords() {
    log "Generating secure random passwords..."
    MOXNAS_DB_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    REDIS_PASS=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-12)
    SECRET_KEY=$(openssl rand -base64 64 | tr -d "=+/")
    success "Secure passwords generated"
}

# Display banner
show_banner() {
    echo -e "${PURPLE}"
    cat << "EOF"
    __  __            _   _          ____  
   |  \/  | _____  __| \ | |   /\   / ___| 
   | |\/| |/ _ \ \/ /|  \| |  /  \  \___ \ 
   | |  | | (_) >  < | |\  | / /\ \  ___) |
   |_|  |_|\___/_/\_\|_| \_|/_/  \_\|____/ 
                                           
   Professional Network Attached Storage
   
EOF
    echo -e "${NC}"
    echo -e "${WHITE}Welcome to MoxNAS Installation${NC}"
    echo -e "${CYAN}Version: 1.0.0 | Target: Debian/Ubuntu LXC${NC}"
    echo ""
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    # Check memory
    total_mem=$(free -m | awk 'NR==2{print $2}')
    if [[ $total_mem -lt 1024 ]]; then
        warn "System has less than 1GB RAM ($total_mem MB). Minimum 2GB recommended."
    fi
    
    # Check disk space
    available_space=$(df / | awk 'NR==2 {print $4}')
    required_space=10485760  # 10GB in KB
    if [[ $available_space -lt $required_space ]]; then
        error "Insufficient disk space. Need at least 10GB, available: $(($available_space/1024/1024))GB"
        exit 1
    fi
    
    # Check internet connectivity
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        error "No internet connection. Please check your network settings."
        exit 1
    fi
    
    success "System requirements check passed"
}

# Update system packages
update_system() {
    log "Updating system packages..."
    export DEBIAN_FRONTEND=noninteractive
    
    apt-get update -qq
    apt-get upgrade -y -qq
    
    # Install essential packages
    apt-get install -y -qq \
        curl \
        wget \
        gnupg2 \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        lsb-release \
        sudo \
        systemctl \
        openssl \
        unzip
    
    success "System packages updated"
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    export DEBIAN_FRONTEND=noninteractive
    
    apt-get install -y -qq \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        python3-setuptools \
        python3-wheel \
        postgresql \
        postgresql-contrib \
        postgresql-client \
        redis-server \
        nginx \
        supervisor \
        mdadm \
        smartmontools \
        nfs-kernel-server \
        samba \
        samba-common-bin \
        vsftpd \
        git \
        htop \
        iotop \
        ncdu \
        tree \
        vim \
        build-essential \
        libpq-dev \
        libffi-dev \
        libssl-dev \
        libsasl2-dev \
        libldap2-dev \
        pkg-config \
        gcc \
        g++ \
        make \
        ufw \
        fail2ban \
        logrotate \
        cron
    
    success "System dependencies installed"
}

# Setup PostgreSQL database
setup_postgresql() {
    log "Setting up PostgreSQL database..."
    
    # Start and enable PostgreSQL
    systemctl start postgresql
    systemctl enable postgresql
    
    # Create database and user
    sudo -u postgres psql -c "CREATE DATABASE $MOXNAS_DB;" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE USER $MOXNAS_DB_USER WITH PASSWORD '$MOXNAS_DB_PASS';" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $MOXNAS_DB TO $MOXNAS_DB_USER;" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER USER $MOXNAS_DB_USER CREATEDB;" 2>/dev/null || true
    sudo -u postgres psql -c "ALTER DATABASE $MOXNAS_DB OWNER TO $MOXNAS_DB_USER;" 2>/dev/null || true
    
    # Configure PostgreSQL for better performance
    PG_VERSION=$(sudo -u postgres psql -t -c "SELECT version();" | grep -oP "PostgreSQL \K[0-9]+")
    PG_CONFIG_DIR="/etc/postgresql/$PG_VERSION/main"
    
    if [[ -f "$PG_CONFIG_DIR/postgresql.conf" ]]; then
        # Backup original config
        cp "$PG_CONFIG_DIR/postgresql.conf" "$PG_CONFIG_DIR/postgresql.conf.backup"
        
        # Optimize for small to medium workloads
        cat >> "$PG_CONFIG_DIR/postgresql.conf" << EOF

# MoxNAS optimizations
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 8
max_parallel_workers_per_gather = 2
max_parallel_workers = 8
max_parallel_maintenance_workers = 2
EOF
        
        # Restart PostgreSQL to apply changes
        systemctl restart postgresql
    fi
    
    success "PostgreSQL database setup complete"
}

# Setup Redis
setup_redis() {
    log "Setting up Redis cache server..."
    
    # Configure Redis
    if [[ -f /etc/redis/redis.conf ]]; then
        cp /etc/redis/redis.conf /etc/redis/redis.conf.backup
        
        # Set password and optimize settings
        sed -i "s/# requirepass foobared/requirepass $REDIS_PASS/" /etc/redis/redis.conf
        sed -i "s/# maxmemory <bytes>/maxmemory 512mb/" /etc/redis/redis.conf
        sed -i "s/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/" /etc/redis/redis.conf
        
        # Enable persistence
        sed -i "s/save 900 1/save 900 1/" /etc/redis/redis.conf
        sed -i "s/save 300 10/save 300 10/" /etc/redis/redis.conf
        sed -i "s/save 60 10000/save 60 10000/" /etc/redis/redis.conf
    fi
    
    systemctl restart redis-server
    systemctl enable redis-server
    
    success "Redis cache server setup complete"
}

# Create MoxNAS user
create_moxnas_user() {
    log "Creating MoxNAS system user..."
    
    if ! id "$MOXNAS_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$MOXNAS_HOME" -m "$MOXNAS_USER"
        usermod -aG sudo "$MOXNAS_USER"
    fi
    
    # Create necessary directories
    mkdir -p "$MOXNAS_HOME"/{logs,backups,uploads,temp}
    mkdir -p /mnt/{storage,backups}
    mkdir -p /srv/ftp
    
    # Set proper ownership
    chown -R "$MOXNAS_USER":"$MOXNAS_USER" "$MOXNAS_HOME"
    chown "$MOXNAS_USER":"$MOXNAS_USER" /mnt/{storage,backups}
    chown ftp:ftp /srv/ftp
    
    success "MoxNAS user created successfully"
}

# Download and install MoxNAS application
install_moxnas_app() {
    log "Installing MoxNAS application..."
    
    cd "$MOXNAS_HOME"
    
    # Download MoxNAS source code
    if command -v git &> /dev/null; then
        if [[ -d .git ]]; then
            sudo -u "$MOXNAS_USER" git pull origin main
        else
            sudo -u "$MOXNAS_USER" git clone https://github.com/moxnas/moxnas.git .
        fi
    else
        # Fallback: download as archive
        wget -O moxnas.tar.gz https://github.com/moxnas/moxnas/archive/refs/heads/main.tar.gz
        tar -xzf moxnas.tar.gz --strip-components=1
        rm moxnas.tar.gz
        chown -R "$MOXNAS_USER":"$MOXNAS_USER" .
    fi
    
    # Create Python virtual environment
    sudo -u "$MOXNAS_USER" python3 -m venv venv
    
    # Upgrade pip and install requirements
    sudo -u "$MOXNAS_USER" bash -c "source venv/bin/activate && pip install --upgrade pip setuptools wheel"
    sudo -u "$MOXNAS_USER" bash -c "source venv/bin/activate && pip install -r requirements.txt"
    
    # Create configuration file
    cat > "$MOXNAS_HOME"/.env << EOF
# MoxNAS Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=$SECRET_KEY

# Database
DATABASE_URL=postgresql://$MOXNAS_DB_USER:$MOXNAS_DB_PASS@localhost/$MOXNAS_DB

# Redis
REDIS_URL=redis://:$REDIS_PASS@localhost:6379/0
CELERY_BROKER_URL=redis://:$REDIS_PASS@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASS@localhost:6379/0

# Application Settings
MOXNAS_ADMIN_EMAIL=admin@moxnas.local
MOXNAS_BRAND_NAME=MoxNAS
MOXNAS_BRAND_URL=https://moxnas.com

# Security Settings
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=28800

# File Upload Settings
MAX_CONTENT_LENGTH=10737418240
UPLOAD_FOLDER=$MOXNAS_HOME/uploads

# Logging
LOG_LEVEL=INFO
LOG_FILE=$MOXNAS_HOME/logs/moxnas.log

# Storage Settings
STORAGE_ROOT=/mnt/storage
BACKUP_ROOT=/mnt/backups
EOF
    
    chmod 600 "$MOXNAS_HOME"/.env
    chown "$MOXNAS_USER":"$MOXNAS_USER" "$MOXNAS_HOME"/.env
    
    success "MoxNAS application installed successfully"
}

# Initialize database
initialize_database() {
    log "Initializing MoxNAS database..."
    
    cd "$MOXNAS_HOME"
    
    # Run database migrations
    sudo -u "$MOXNAS_USER" bash -c "source venv/bin/activate && python migrate.py init"
    
    # Create admin user
    sudo -u "$MOXNAS_USER" bash -c "source venv/bin/activate && python migrate.py create-admin \
        --username admin \
        --email admin@moxnas.local \
        --password '$ADMIN_PASSWORD' \
        --first-name Admin \
        --last-name User"
    
    success "Database initialization complete"
}

# Configure Nginx web server
configure_nginx() {
    log "Configuring Nginx web server..."
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Create MoxNAS site configuration
    cat > /etc/nginx/sites-available/moxnas << 'EOF'
# MoxNAS Nginx Configuration

# Rate limiting
limit_req_zone $binary_remote_addr zone=moxnas_limit:10m rate=10r/s;

# Upstream backend
upstream moxnas_backend {
    server 127.0.0.1:5000;
    keepalive 32;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name _;
    
    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    # Redirect all HTTP traffic to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name _;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/certs/moxnas-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/moxnas-selfsigned.key;
    
    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; font-src 'self' https://cdn.jsdelivr.net;" always;
    
    # File upload size limit (10GB)
    client_max_body_size 10G;
    client_body_buffer_size 128k;
    client_body_timeout 60s;
    client_header_timeout 60s;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types
        application/atom+xml
        application/javascript
        application/json
        application/ld+json
        application/manifest+json
        application/rss+xml
        application/vnd.geo+json
        application/vnd.ms-fontobject
        application/x-font-ttf
        application/x-web-app-manifest+json
        application/xhtml+xml
        application/xml
        font/opentype
        image/bmp
        image/svg+xml
        image/x-icon
        text/cache-manifest
        text/css
        text/plain
        text/vcard
        text/vnd.rim.location.xloc
        text/vtt
        text/x-component
        text/x-cross-domain-policy;
    
    # Static files
    location /static {
        alias /opt/moxnas/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
        
        # Handle font files
        location ~* \.(woff|woff2|ttf|eot)$ {
            add_header Access-Control-Allow-Origin *;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # API endpoints with rate limiting
    location /api {
        limit_req zone=moxnas_limit burst=20 nodelay;
        
        proxy_pass http://moxnas_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_cache_bypass $http_upgrade;
        
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # Main application
    location / {
        limit_req zone=moxnas_limit burst=10 nodelay;
        
        proxy_pass http://moxnas_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_cache_bypass $http_upgrade;
        
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # Health check endpoint (no rate limiting)
    location /health {
        proxy_pass http://moxnas_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        access_log off;
    }
    
    # Security - deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~ ~$ {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    location ~* \.(env|log|ini)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF
    
    # Enable the site
    ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
    
    # Generate self-signed SSL certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/moxnas-selfsigned.key \
        -out /etc/ssl/certs/moxnas-selfsigned.crt \
        -subj "/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas.local"
    
    # Secure SSL files
    chmod 600 /etc/ssl/private/moxnas-selfsigned.key
    chmod 644 /etc/ssl/certs/moxnas-selfsigned.crt
    
    # Test Nginx configuration
    nginx -t
    
    # Start and enable Nginx
    systemctl restart nginx
    systemctl enable nginx
    
    success "Nginx web server configured successfully"
}

# Configure Supervisor process manager
configure_supervisor() {
    log "Configuring Supervisor process manager..."
    
    cat > /etc/supervisor/conf.d/moxnas.conf << EOF
[program:moxnas-web]
command=$MOXNAS_HOME/venv/bin/gunicorn -c $MOXNAS_HOME/gunicorn.conf.py wsgi:app
directory=$MOXNAS_HOME
user=$MOXNAS_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$MOXNAS_HOME/logs/web.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
environment=PATH="$MOXNAS_HOME/venv/bin"

[program:moxnas-worker]
command=$MOXNAS_HOME/venv/bin/celery -A celery_worker.celery worker --loglevel=info --concurrency=4
directory=$MOXNAS_HOME
user=$MOXNAS_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$MOXNAS_HOME/logs/worker.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
environment=PATH="$MOXNAS_HOME/venv/bin"

[program:moxnas-scheduler]
command=$MOXNAS_HOME/venv/bin/celery -A celery_worker.celery beat --loglevel=info
directory=$MOXNAS_HOME
user=$MOXNAS_USER
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=$MOXNAS_HOME/logs/scheduler.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
environment=PATH="$MOXNAS_HOME/venv/bin"
EOF

    # Create Gunicorn configuration
    cat > "$MOXNAS_HOME"/gunicorn.conf.py << EOF
# Gunicorn configuration for MoxNAS

import multiprocessing

# Server socket
bind = "127.0.0.1:5000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "$MOXNAS_HOME/logs/gunicorn-access.log"
errorlog = "$MOXNAS_HOME/logs/gunicorn-error.log"
loglevel = "info"
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(O)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "moxnas"

# Daemonize the Gunicorn process
daemon = False

# The socket to bind
pidfile = "$MOXNAS_HOME/gunicorn.pid"

# SSL (handled by Nginx)
# keyfile = None
# certfile = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
preload_app = True
EOF
    
    chown "$MOXNAS_USER":"$MOXNAS_USER" "$MOXNAS_HOME"/gunicorn.conf.py
    
    # Start Supervisor services
    systemctl enable supervisor
    systemctl start supervisor
    supervisorctl reread
    supervisorctl update
    
    # Wait for services to start
    sleep 5
    
    supervisorctl start moxnas-web moxnas-worker moxnas-scheduler
    
    success "Supervisor process manager configured successfully"
}

# Configure NFS server
configure_nfs() {
    log "Configuring NFS server..."
    
    # Add default export
    if ! grep -q "/mnt/storage" /etc/exports; then
        echo "/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)" >> /etc/exports
    fi
    
    # Start and enable NFS services
    systemctl enable nfs-kernel-server
    systemctl start nfs-kernel-server
    systemctl enable rpcbind
    systemctl start rpcbind
    
    # Export the shares
    exportfs -ra
    
    success "NFS server configured successfully"
}

# Configure Samba server
configure_samba() {
    log "Configuring Samba server..."
    
    # Backup original configuration
    cp /etc/samba/smb.conf /etc/samba/smb.conf.backup
    
    # Create optimized Samba configuration
    cat > /etc/samba/smb.conf << EOF
# MoxNAS Samba Configuration
[global]
    # Server identification
    workgroup = WORKGROUP
    server string = MoxNAS Server %v
    netbios name = MOXNAS
    
    # Protocol settings
    server role = standalone server
    security = user
    map to guest = bad user
    guest account = nobody
    
    # Performance optimizations
    socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=524288 SO_SNDBUF=524288
    read raw = yes
    write raw = yes
    max xmit = 65535
    dead time = 15
    getwd cache = yes
    
    # Logging
    log file = /var/log/samba/log.%m
    max log size = 1000
    log level = 1
    
    # Character set
    unix charset = UTF-8
    dos charset = CP850
    
    # Networking
    bind interfaces only = no
    interfaces = lo eth0
    
    # Time server
    time server = yes
    
    # Disable printers
    load printers = no
    printing = bsd
    printcap name = /dev/null
    disable spoolss = yes
    
    # Security
    restrict anonymous = 2
    null passwords = no
    obey pam restrictions = yes
    unix password sync = yes
    passwd program = /usr/bin/passwd %u
    passwd chat = *Enter\snew\s*\spassword:* %n\n *Retype\snew\s*\spassword:* %n\n *password\supdated\ssuccessfully* .
    pam password change = yes
    
    # File system options
    ea support = yes
    store dos attributes = yes
    map system = no
    map hidden = no
    map archive = yes
    map readonly = no
    
    # Recycle bin (optional)
    # vfs objects = recycle
    # recycle:repository = .recycle
    # recycle:keeptree = yes
    # recycle:versions = yes

# Default storage share
[storage]
    comment = MoxNAS Storage
    path = /mnt/storage
    browseable = yes
    writable = yes
    guest ok = no
    valid users = $MOXNAS_USER
    create mask = 0755
    directory mask = 0755
    force user = $MOXNAS_USER
    force group = $MOXNAS_USER

# Backup share
[backups]
    comment = MoxNAS Backups
    path = /mnt/backups
    browseable = yes
    writable = yes
    guest ok = no
    valid users = $MOXNAS_USER
    create mask = 0755
    directory mask = 0755
    force user = $MOXNAS_USER
    force group = $MOXNAS_USER
EOF
    
    # Add MoxNAS user to Samba
    echo -e "$ADMIN_PASSWORD\n$ADMIN_PASSWORD" | smbpasswd -a "$MOXNAS_USER"
    smbpasswd -e "$MOXNAS_USER"
    
    # Start and enable Samba services
    systemctl enable smbd nmbd
    systemctl start smbd nmbd
    
    success "Samba server configured successfully"
}

# Configure FTP server
configure_ftp() {
    log "Configuring FTP server..."
    
    # Backup original configuration
    cp /etc/vsftpd.conf /etc/vsftpd.conf.backup
    
    # Create secure FTP configuration
    cat > /etc/vsftpd.conf << EOF
# MoxNAS FTP Configuration

# Standalone mode
listen=NO
listen_ipv6=YES
dirmessage_enable=YES
use_localtime=YES

# User settings
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022

# Security settings
chroot_local_user=YES
allow_writeable_chroot=YES
secure_chroot_dir=/var/run/vsftpd/empty

# Logging
xferlog_enable=YES
xferlog_file=/var/log/vsftpd.log
xferlog_std_format=YES
log_ftp_protocol=NO

# Connection settings
connect_from_port_20=YES
pam_service_name=vsftpd

# SSL/TLS settings
rsa_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
rsa_private_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
ssl_enable=YES
ssl_tlsv1=YES
ssl_sslv2=NO
ssl_sslv3=NO
force_local_data_ssl=NO
force_local_logins_ssl=NO

# Passive mode settings
pasv_enable=YES
pasv_min_port=10000
pasv_max_port=10100

# User restrictions
userlist_enable=YES
userlist_file=/etc/vsftpd.userlist
userlist_deny=NO

# Performance
dual_log_enable=YES
connect_timeout=60
data_connection_timeout=120
idle_session_timeout=600
max_clients=50
max_per_ip=5

# Directory settings
user_sub_token=\$USER
local_root=/srv/ftp
EOF
    
    # Create FTP user list
    echo "$MOXNAS_USER" > /etc/vsftpd.userlist
    
    # Create FTP directory structure
    mkdir -p /srv/ftp
    chown "$MOXNAS_USER":"$MOXNAS_USER" /srv/ftp
    
    # Start and enable FTP service
    systemctl enable vsftpd
    systemctl start vsftpd
    
    success "FTP server configured successfully"
}

# Configure firewall
configure_firewall() {
    log "Configuring UFW firewall..."
    
    # Reset UFW to defaults
    ufw --force reset
    
    # Set default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (be careful not to lock yourself out)
    ufw allow ssh
    
    # Allow web services
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    
    # Allow file sharing services
    ufw allow 139/tcp comment 'SMB NetBIOS'
    ufw allow 445/tcp comment 'SMB'
    ufw allow 2049/tcp comment 'NFS'
    ufw allow 111/tcp comment 'RPC'
    
    # Allow FTP
    ufw allow 21/tcp comment 'FTP'
    ufw allow 10000:10100/tcp comment 'FTP Passive'
    
    # Enable firewall
    ufw --force enable
    
    # Configure fail2ban for additional security
    if command -v fail2ban-server &> /dev/null; then
        systemctl enable fail2ban
        systemctl start fail2ban
        
        # Create jail for MoxNAS
        cat > /etc/fail2ban/jail.d/moxnas.conf << EOF
[moxnas]
enabled = true
port = http,https
filter = moxnas
logpath = $MOXNAS_HOME/logs/gunicorn-access.log
maxretry = 5
bantime = 3600
findtime = 600

[sshd]
enabled = true
maxretry = 3
bantime = 3600
EOF
        
        systemctl restart fail2ban
    fi
    
    success "Firewall configured successfully"
}

# Setup health monitoring
setup_health_monitoring() {
    log "Setting up health monitoring..."
    
    # Create health monitoring script
    cp "$MOXNAS_HOME"/health_monitor.py /usr/local/bin/moxnas-health-monitor
    chmod +x /usr/local/bin/moxnas-health-monitor
    
    # Create systemd service for health monitoring
    cat > /etc/systemd/system/moxnas-health.service << EOF
[Unit]
Description=MoxNAS Health Monitor
After=network.target postgresql.service redis-server.service
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$MOXNAS_HOME
ExecStart=/usr/local/bin/moxnas-health-monitor --monitor --interval 60
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$MOXNAS_HOME /var/log /tmp

[Install]
WantedBy=multi-user.target
EOF
    
    # Enable and start health monitoring service
    systemctl daemon-reload
    systemctl enable moxnas-health.service
    systemctl start moxnas-health.service
    
    success "Health monitoring setup complete"
}

# Setup maintenance tasks
setup_maintenance() {
    log "Setting up maintenance tasks..."
    
    # Create maintenance script
    cat > /usr/local/bin/moxnas-maintenance << EOF
#!/bin/bash
# MoxNAS Maintenance Script

LOGFILE="/var/log/moxnas-maintenance.log"

log_message() {
    echo "\$(date '+%Y-%m-%d %H:%M:%S') \$1" >> "\$LOGFILE"
}

log_message "Starting maintenance tasks..."

# Update device database and run health checks
cd $MOXNAS_HOME
sudo -u $MOXNAS_USER bash -c "source venv/bin/activate && python -c '
from app import create_app
from app.storage.manager import storage_manager
from app.tasks import device_health_check, cleanup_old_alerts
app = create_app()
app.app_context().push()

# Update device database
try:
    storage_manager.update_device_database()
    print(\"Device database updated\")
except Exception as e:
    print(f\"Error updating device database: {e}\")

# Run health checks
try:
    device_health_check.delay()
    print(\"Health check initiated\")
except Exception as e:
    print(f\"Error initiating health check: {e}\")

# Clean up old alerts (older than 30 days)
try:
    cleanup_old_alerts.delay()
    print(\"Alert cleanup initiated\")
except Exception as e:
    print(f\"Error initiating alert cleanup: {e}\")
'"

# Clean up old log files
find /var/log/supervisor/ -name "*.log.*" -mtime +30 -delete 2>/dev/null || true
find $MOXNAS_HOME/logs/ -name "*.log.*" -mtime +30 -delete 2>/dev/null || true

# Clean up old backup files (older than 90 days)
find /mnt/backups/ -type f -mtime +90 -delete 2>/dev/null || true

# Clean up temporary files
find $MOXNAS_HOME/temp/ -type f -mtime +7 -delete 2>/dev/null || true

# Update package information
apt-get update -qq 2>/dev/null || true

# Check for security updates
security_updates=\$(apt list --upgradable 2>/dev/null | grep -c security || echo "0")
if [ "\$security_updates" -gt 0 ]; then
    log_message "Warning: \$security_updates security updates available"
fi

# Vacuum PostgreSQL database (weekly)
if [ "\$(date +%u)" = "1" ]; then
    sudo -u postgres vacuumdb --analyze --quiet $MOXNAS_DB 2>/dev/null || true
    log_message "Database maintenance completed"
fi

# Restart services if needed (check for memory leaks)
total_mem=\$(free -m | awk 'NR==2{print \$2}')
used_mem=\$(free -m | awk 'NR==2{print \$3}')
mem_usage=\$((used_mem * 100 / total_mem))

if [ "\$mem_usage" -gt 90 ]; then
    log_message "High memory usage detected: \${mem_usage}%"
    supervisorctl restart moxnas-web
fi

log_message "Maintenance tasks completed"
EOF
    
    chmod +x /usr/local/bin/moxnas-maintenance
    
    # Add to crontab (daily at 2 AM)
    cat > /etc/cron.d/moxnas-maintenance << EOF
# MoxNAS Maintenance Tasks
0 2 * * * root /usr/local/bin/moxnas-maintenance
EOF
    
    # Setup log rotation
    cat > /etc/logrotate.d/moxnas << EOF
$MOXNAS_HOME/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $MOXNAS_USER $MOXNAS_USER
    postrotate
        supervisorctl restart moxnas-web moxnas-worker moxnas-scheduler >/dev/null 2>&1 || true
    endscript
}

/var/log/moxnas-maintenance.log {
    weekly
    missingok
    rotate 12
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF
    
    success "Maintenance tasks configured successfully"
}

# Create installation summary
create_installation_summary() {
    log "Creating installation summary..."
    
    # Get system information
    SYSTEM_IP=$(hostname -I | awk '{print $1}')
    SYSTEM_HOSTNAME=$(hostname)
    
    cat > "$MOXNAS_HOME"/INSTALLATION_INFO.txt << EOF
╔══════════════════════════════════════════════════════════════╗
║                    MoxNAS Installation Summary              ║
╠══════════════════════════════════════════════════════════════╣
║ Installation Date: $(date)                                  ║
║ System IP: $SYSTEM_IP                                       ║
║ Hostname: $SYSTEM_HOSTNAME                                  ║
╠══════════════════════════════════════════════════════════════╣
║                        ACCESS INFORMATION                    ║
╠══════════════════════════════════════════════════════════════╣
║ Web Interface: https://$SYSTEM_IP                          ║
║ Admin Username: admin                                        ║
║ Admin Password: $ADMIN_PASSWORD                             ║
╠══════════════════════════════════════════════════════════════╣
║                      NETWORK SHARES                          ║
╠══════════════════════════════════════════════════════════════╣
║ SMB Share: \\\\$SYSTEM_IP\\storage                          ║
║ SMB Username: $MOXNAS_USER                                   ║
║ SMB Password: $ADMIN_PASSWORD                               ║
║                                                              ║
║ NFS Share: $SYSTEM_IP:/mnt/storage                          ║
║                                                              ║
║ FTP Server: ftp://$SYSTEM_IP                               ║
║ FTP Username: $MOXNAS_USER                                   ║
║ FTP Password: $ADMIN_PASSWORD                               ║
╠══════════════════════════════════════════════════════════════╣
║                    SYSTEM INFORMATION                        ║
╠══════════════════════════════════════════════════════════════╣
║ Application Directory: $MOXNAS_HOME                         ║
║ Configuration File: $MOXNAS_HOME/.env                       ║
║ Log Directory: $MOXNAS_HOME/logs/                           ║
║ Storage Directory: /mnt/storage/                             ║
║ Backup Directory: /mnt/backups/                              ║
║                                                              ║
║ Database: PostgreSQL ($MOXNAS_DB)                           ║
║ Database User: $MOXNAS_DB_USER                               ║
║ Cache: Redis (password protected)                            ║
╠══════════════════════════════════════════════════════════════╣
║                    SERVICE MANAGEMENT                        ║
╠══════════════════════════════════════════════════════════════╣
║ Check Status: supervisorctl status                           ║
║ Restart All: supervisorctl restart all                      ║
║ View Logs: supervisorctl tail -f moxnas-web                 ║
║                                                              ║
║ Health Monitor: systemctl status moxnas-health              ║
║ Run Health Check: /usr/local/bin/moxnas-health-monitor --check ║
║                                                              ║
║ Maintenance: /usr/local/bin/moxnas-maintenance              ║
║ Update System: apt update && apt upgrade                    ║
╠══════════════════════════════════════════════════════════════╣
║                         SECURITY                             ║
╠══════════════════════════════════════════════════════════════╣
║ Firewall Status: ufw status                                 ║
║ SSL Certificate: Self-signed (replace with Let's Encrypt)   ║
║ Fail2ban Status: systemctl status fail2ban                 ║
║                                                              ║
║ IMPORTANT: Change default passwords after first login!      ║
╚══════════════════════════════════════════════════════════════╝

Next Steps:
1. Access the web interface at https://$SYSTEM_IP
2. Log in with the admin credentials above
3. Change the default admin password in Settings
4. Configure your storage drives in Storage Management
5. Create network shares as needed
6. Set up backup jobs for data protection
7. Replace the self-signed SSL certificate for production use

For support and documentation, visit: https://github.com/moxnas/moxnas
EOF
    
    chown "$MOXNAS_USER":"$MOXNAS_USER" "$MOXNAS_HOME"/INSTALLATION_INFO.txt
    chmod 600 "$MOXNAS_HOME"/INSTALLATION_INFO.txt
    
    success "Installation summary created"
}

# Create system MOTD
create_motd() {
    log "Creating system message of the day..."
    
    cat > /etc/motd << EOF

    __  __            _   _          ____  
   |  \/  | _____  __| \ | |   /\   / ___| 
   | |\/| |/ _ \ \/ /|  \| |  /  \  \___ \ 
   | |  | | (_) >  < | |\  | / /\ \  ___) |
   |_|  |_|\___/_/\_\|_| \_|/_/  \_\|____/ 
                                           
   Professional Network Attached Storage
   
   System IP: $(hostname -I | awk '{print $1}')
   Web Interface: https://$(hostname -I | awk '{print $1}')
   
   Admin Username: admin
   Admin Password: $ADMIN_PASSWORD
   
   Quick Commands:
   - supervisorctl status          (check services)
   - systemctl status moxnas-health (health monitor)
   - cat $MOXNAS_HOME/INSTALLATION_INFO.txt (full info)
   
   System Status:
   - $(supervisorctl status moxnas-web 2>/dev/null | grep -q RUNNING && echo "✓ Web Service: Running" || echo "✗ Web Service: Stopped")
   - $(systemctl is-active --quiet postgresql && echo "✓ Database: Running" || echo "✗ Database: Stopped")
   - $(systemctl is-active --quiet redis-server && echo "✓ Cache: Running" || echo "✗ Cache: Stopped")
   - $(systemctl is-active --quiet smbd && echo "✓ SMB: Running" || echo "✗ SMB: Stopped")
   - $(systemctl is-active --quiet nfs-kernel-server && echo "✓ NFS: Running" || echo "✗ NFS: Stopped")
   
   Documentation: https://github.com/moxnas/moxnas

EOF
    
    success "System MOTD created"
}

# Verify installation
verify_installation() {
    log "Verifying installation..."
    
    # Check if all services are running
    services_status=0
    
    # Check PostgreSQL
    if systemctl is-active --quiet postgresql; then
        success "PostgreSQL is running"
    else
        error "PostgreSQL is not running"
        services_status=1
    fi
    
    # Check Redis
    if systemctl is-active --quiet redis-server; then
        success "Redis is running"
    else
        error "Redis is not running"
        services_status=1
    fi
    
    # Check Nginx
    if systemctl is-active --quiet nginx; then
        success "Nginx is running"
    else
        error "Nginx is not running"
        services_status=1
    fi
    
    # Check Supervisor services
    if supervisorctl status moxnas-web | grep -q RUNNING; then
        success "MoxNAS web service is running"
    else
        error "MoxNAS web service is not running"
        services_status=1
    fi
    
    if supervisorctl status moxnas-worker | grep -q RUNNING; then
        success "MoxNAS worker is running"
    else
        error "MoxNAS worker is not running"
        services_status=1
    fi
    
    if supervisorctl status moxnas-scheduler | grep -q RUNNING; then
        success "MoxNAS scheduler is running"
    else
        error "MoxNAS scheduler is not running"
        services_status=1
    fi
    
    # Check health monitor
    if systemctl is-active --quiet moxnas-health; then
        success "Health monitor is running"
    else
        warn "Health monitor is not running"
    fi
    
    # Check SMB
    if systemctl is-active --quiet smbd; then
        success "Samba is running"
    else
        warn "Samba is not running"
    fi
    
    # Check NFS
    if systemctl is-active --quiet nfs-kernel-server; then
        success "NFS is running"
    else
        warn "NFS is not running"
    fi
    
    # Check FTP
    if systemctl is-active --quiet vsftpd; then
        success "FTP is running"
    else
        warn "FTP is not running"
    fi
    
    # Test web interface connectivity
    sleep 5
    if curl -k -s --connect-timeout 10 https://localhost/health > /dev/null; then
        success "Web interface is accessible"
    else
        warn "Web interface may not be fully ready yet (this is normal)"
    fi
    
    if [[ $services_status -eq 0 ]]; then
        success "All critical services are running properly"
        return 0
    else
        warn "Some services are not running. Check the logs for details."
        return 1
    fi
}

# Cleanup temporary files and optimize system
cleanup_and_optimize() {
    log "Cleaning up and optimizing system..."
    
    # Clean package cache
    apt-get autoremove -y
    apt-get autoclean
    
    # Clear temporary files
    rm -rf /tmp/*
    rm -rf /var/tmp/*
    
    # Optimize PostgreSQL
    sudo -u postgres vacuumdb --all --analyze --quiet
    
    # Update locate database
    if command -v updatedb &> /dev/null; then
        updatedb
    fi
    
    success "System cleanup and optimization complete"
}

# Main installation function
main() {
    # Start installation
    show_banner
    
    log "Starting MoxNAS installation on $(lsb_release -ds 2>/dev/null || cat /etc/issue | head -n1)"
    
    # Pre-installation checks
    check_root
    check_os
    check_requirements
    generate_passwords
    
    # System preparation
    update_system
    install_dependencies
    
    # Database and cache setup
    setup_postgresql
    setup_redis
    
    # Application installation
    create_moxnas_user
    install_moxnas_app
    initialize_database
    
    # Service configuration
    configure_nginx
    configure_supervisor
    
    # File sharing services
    configure_nfs
    configure_samba
    configure_ftp
    
    # Security and monitoring
    configure_firewall
    setup_health_monitoring
    setup_maintenance
    
    # Final steps
    create_installation_summary
    create_motd
    cleanup_and_optimize
    
    # Verify installation
    if verify_installation; then
        echo ""
        echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║${NC}                 ${WHITE}MoxNAS Installation Complete!${NC}                 ${GREEN}║${NC}"
        echo -e "${GREEN}╠══════════════════════════════════════════════════════════════╣${NC}"
        echo -e "${GREEN}║${NC} Web Interface: ${YELLOW}https://$(hostname -I | awk '{print $1}')${NC}                              ${GREEN}║${NC}"
        echo -e "${GREEN}║${NC} Username: ${YELLOW}admin${NC}                                        ${GREEN}║${NC}"
        echo -e "${GREEN}║${NC} Password: ${YELLOW}$ADMIN_PASSWORD${NC}                 ${GREEN}║${NC}"
        echo -e "${GREEN}║${NC}                                                              ${GREEN}║${NC}"
        echo -e "${GREEN}║${NC} ${YELLOW}Please save these credentials and change them after login!${NC}  ${GREEN}║${NC}"
        echo -e "${GREEN}║${NC}                                                              ${GREEN}║${NC}"
        echo -e "${GREEN}║${NC} Full documentation: ${CYAN}$MOXNAS_HOME/INSTALLATION_INFO.txt${NC}  ${GREEN}║${NC}"
        echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        
        success "MoxNAS is now ready to use!"
        success "Installation completed successfully in $(( $(date +%s) - $START_TIME )) seconds"
    else
        echo ""
        echo -e "${YELLOW}╔══════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║${NC}                 ${WHITE}Installation Completed with Warnings${NC}             ${YELLOW}║${NC}"
        echo -e "${YELLOW}╠══════════════════════════════════════════════════════════════╣${NC}"
        echo -e "${YELLOW}║${NC} MoxNAS has been installed but some services may need        ${YELLOW}║${NC}"
        echo -e "${YELLOW}║${NC} attention. Please check the service status and logs.       ${YELLOW}║${NC}"
        echo -e "${YELLOW}║${NC}                                                              ${YELLOW}║${NC}"
        echo -e "${YELLOW}║${NC} Web Interface: ${CYAN}https://$(hostname -I | awk '{print $1}')${NC}                              ${YELLOW}║${NC}"
        echo -e "${YELLOW}║${NC} Check Status: ${CYAN}supervisorctl status${NC}                        ${YELLOW}║${NC}"
        echo -e "${YELLOW}║${NC} View Logs: ${CYAN}tail -f $MOXNAS_HOME/logs/*.log${NC}           ${YELLOW}║${NC}"
        echo -e "${YELLOW}╚══════════════════════════════════════════════════════════════╝${NC}"
        echo ""
    fi
    
    log "Installation script completed"
}

# Script execution starts here
START_TIME=$(date +%s)

# Create log file
mkdir -p "$(dirname "$INSTALL_LOG")"
touch "$INSTALL_LOG"

# Handle interruption
trap 'error "Installation interrupted by user"; exit 130' INT TERM

# Run main installation
main "$@"

exit 0