#!/bin/bash

# MoxNAS Production Deployment Script
# This script handles production deployment with optimization and validation

set -euo pipefail

# Configuration
MOXNAS_ROOT="/opt/moxnas"
MOXNAS_USER="moxnas"
MOXNAS_GROUP="moxnas"
PYTHON_VERSION="3.9"
NODE_VERSION="18"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    # Check OS
    if ! grep -q "Ubuntu\|Debian" /etc/os-release; then
        warn "This script is optimized for Ubuntu/Debian. Proceed with caution."
    fi
    
    # Check available disk space (minimum 5GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 5242880 ]]; then  # 5GB in KB
        error "Insufficient disk space. Minimum 5GB required."
    fi
    
    # Check memory (minimum 2GB)
    available_mem=$(free -k | awk 'NR==2{print $2}')
    if [[ $available_mem -lt 2097152 ]]; then  # 2GB in KB
        warn "Less than 2GB RAM available. Performance may be affected."
    fi
    
    log "✓ System requirements check passed"
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package lists
    apt-get update -qq
    
    # Install essential packages
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        nodejs \
        npm \
        nginx \
        supervisor \
        redis-server \
        sqlite3 \
        git \
        curl \
        wget \
        unzip \
        build-essential \
        libffi-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        zlib1g-dev \
        samba \
        nfs-kernel-server \
        vsftpd \
        ufw
    
    # Install specific Node.js version if needed
    node_version=$(node --version 2>/dev/null | cut -d'v' -f2 | cut -d'.' -f1 || echo "0")
    if [[ $node_version -lt 16 ]]; then
        log "Installing Node.js $NODE_VERSION..."
        curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
        apt-get install -y nodejs
    fi
    
    log "✓ System dependencies installed"
}

# Create MoxNAS user and directories
setup_user_and_directories() {
    log "Setting up MoxNAS user and directories..."
    
    # Create moxnas user if it doesn't exist
    if ! id "$MOXNAS_USER" &>/dev/null; then
        useradd -r -s /bin/bash -d "$MOXNAS_ROOT" -m "$MOXNAS_USER"
        usermod -aG sudo "$MOXNAS_USER"
    fi
    
    # Create necessary directories
    mkdir -p "$MOXNAS_ROOT"/{backend,frontend,logs,config,data}
    mkdir -p /var/log/moxnas
    mkdir -p /var/lib/moxnas
    mkdir -p /etc/moxnas
    mkdir -p /mnt/storage
    
    # Set ownership
    chown -R "$MOXNAS_USER:$MOXNAS_GROUP" "$MOXNAS_ROOT"
    chown -R "$MOXNAS_USER:$MOXNAS_GROUP" /var/log/moxnas
    chown -R "$MOXNAS_USER:$MOXNAS_GROUP" /var/lib/moxnas
    chown -R "$MOXNAS_USER:$MOXNAS_GROUP" /etc/moxnas
    
    # Set permissions
    chmod 755 "$MOXNAS_ROOT"
    chmod 755 /var/log/moxnas
    chmod 755 /var/lib/moxnas
    chmod 755 /etc/moxnas
    
    log "✓ User and directories setup complete"
}

# Deploy backend application
deploy_backend() {
    log "Deploying backend application..."
    
    cd "$MOXNAS_ROOT"
    
    # Copy backend files
    if [[ -d "./backend" ]]; then
        cp -r ./backend/* "$MOXNAS_ROOT/backend/"
    else
        error "Backend source directory not found"
    fi
    
    # Create virtual environment
    python3 -m venv "$MOXNAS_ROOT/venv"
    source "$MOXNAS_ROOT/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install Python dependencies
    if [[ -f "$MOXNAS_ROOT/backend/requirements.txt" ]]; then
        pip install -r "$MOXNAS_ROOT/backend/requirements.txt"
    else
        error "requirements.txt not found"
    fi
    
    # Install production-specific packages
    pip install gunicorn psycopg2-binary
    
    log "✓ Backend deployment complete"
}

# Deploy frontend application
deploy_frontend() {
    log "Deploying frontend application..."
    
    cd "$MOXNAS_ROOT"
    
    # Copy frontend files
    if [[ -d "./frontend" ]]; then
        cp -r ./frontend/* "$MOXNAS_ROOT/frontend/"
    else
        error "Frontend source directory not found"
    fi
    
    cd "$MOXNAS_ROOT/frontend"
    
    # Install dependencies
    npm ci --production
    
    # Build for production
    NODE_ENV=production npm run build
    
    # Copy build files to static directory
    mkdir -p "$MOXNAS_ROOT/backend/static/frontend"
    cp -r build/* "$MOXNAS_ROOT/backend/static/frontend/"
    
    log "✓ Frontend deployment complete"
}

# Configure database
configure_database() {
    log "Configuring database..."
    
    cd "$MOXNAS_ROOT/backend"
    source "$MOXNAS_ROOT/venv/bin/activate"
    
    # Run migrations
    python manage.py migrate --noinput
    
    # Collect static files
    python manage.py collectstatic --noinput
    
    # Validate database
    python manage.py validate_database --migrate --create-superuser
    
    log "✓ Database configuration complete"
}

# Configure services
configure_services() {
    log "Configuring system services..."
    
    cd "$MOXNAS_ROOT/backend"
    source "$MOXNAS_ROOT/venv/bin/activate"
    
    # Configure MoxNAS services
    python manage.py configure_services --service=all --test-only
    
    # Create systemd service files
    python manage.py configure_services --service=systemd
    
    # Enable and start services
    systemctl daemon-reload
    systemctl enable moxnas
    systemctl enable moxnas-monitor
    
    log "✓ Services configuration complete"
}

# Configure Nginx
configure_nginx() {
    log "Configuring Nginx..."
    
    # Generate Nginx configuration
    cd "$MOXNAS_ROOT/backend"
    source "$MOXNAS_ROOT/venv/bin/activate"
    python manage.py configure_services --service=nginx
    
    # Test Nginx configuration
    nginx -t
    
    # Enable and restart Nginx
    systemctl enable nginx
    systemctl restart nginx
    
    log "✓ Nginx configuration complete"
}

# Configure firewall
configure_firewall() {
    log "Configuring firewall..."
    
    # Enable UFW
    ufw --force enable
    
    # Allow SSH
    ufw allow ssh
    
    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow MoxNAS web interface
    ufw allow 8000/tcp
    
    # Allow Samba
    ufw allow 139/tcp
    ufw allow 445/tcp
    
    # Allow NFS
    ufw allow 2049/tcp
    
    # Allow FTP
    ufw allow 21/tcp
    ufw allow 20000:20100/tcp  # FTP passive mode
    
    log "✓ Firewall configuration complete"
}

# Optimize system performance
optimize_performance() {
    log "Optimizing system performance..."
    
    # Increase file descriptor limits
    cat > /etc/security/limits.d/moxnas.conf << EOF
$MOXNAS_USER soft nofile 65536
$MOXNAS_USER hard nofile 65536
$MOXNAS_USER soft nproc 4096
$MOXNAS_USER hard nproc 4096
EOF
    
    # Configure swap if needed
    if [[ $(free -m | awk 'NR==3{print $2}') -eq 0 ]]; then
        log "Creating swap file..."
        fallocate -l 2G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
    fi
    
    # Optimize Redis
    echo "vm.overcommit_memory = 1" >> /etc/sysctl.conf
    
    # Apply sysctl changes
    sysctl -p
    
    log "✓ Performance optimization complete"
}

# Run security hardening
security_hardening() {
    log "Applying security hardening..."
    
    # Set file permissions
    find "$MOXNAS_ROOT" -type f -name "*.py" -exec chmod 644 {} \;
    find "$MOXNAS_ROOT" -type d -exec chmod 755 {} \;
    
    # Secure configuration files
    chmod 600 "$MOXNAS_ROOT/backend/moxnas/settings.py"
    chmod 600 /etc/moxnas/*
    
    # Remove unnecessary packages
    apt-get autoremove -y
    apt-get autoclean
    
    log "✓ Security hardening complete"
}

# Start services
start_services() {
    log "Starting MoxNAS services..."
    
    # Start Redis
    systemctl start redis-server
    systemctl enable redis-server
    
    # Start MoxNAS services
    systemctl start moxnas
    systemctl start moxnas-monitor
    
    # Start Nginx
    systemctl start nginx
    
    # Verify services are running
    sleep 5
    
    if systemctl is-active --quiet moxnas; then
        log "✓ MoxNAS service is running"
    else
        error "MoxNAS service failed to start"
    fi
    
    if systemctl is-active --quiet nginx; then
        log "✓ Nginx service is running"
    else
        error "Nginx service failed to start"
    fi
    
    log "✓ All services started successfully"
}

# Validate deployment
validate_deployment() {
    log "Validating deployment..."
    
    # Check if MoxNAS is responding
    if curl -f -s http://localhost:8000/health/ > /dev/null; then
        log "✓ MoxNAS web interface is accessible"
    else
        warn "MoxNAS web interface may not be accessible"
    fi
    
    # Check database
    cd "$MOXNAS_ROOT/backend"
    source "$MOXNAS_ROOT/venv/bin/activate"
    if python manage.py validate_database; then
        log "✓ Database validation passed"
    else
        warn "Database validation issues detected"
    fi
    
    # Check services
    python manage.py configure_services --test-only
    
    log "✓ Deployment validation complete"
}

# Display deployment summary
display_summary() {
    log "=== MoxNAS Deployment Summary ==="
    echo
    info "🚀 MoxNAS has been successfully deployed!"
    echo
    info "📍 Installation Directory: $MOXNAS_ROOT"
    info "🌐 Web Interface: http://$(hostname -I | awk '{print $1}'):8000"
    info "👤 Default Admin User: admin"
    info "🔑 Default Admin Password: moxnas123"
    echo
    warn "⚠️  IMPORTANT: Change the default admin password after first login!"
    echo
    info "📊 Service Status:"
    systemctl is-active moxnas && echo "   ✓ MoxNAS: Running" || echo "   ✗ MoxNAS: Stopped"
    systemctl is-active nginx && echo "   ✓ Nginx: Running" || echo "   ✗ Nginx: Stopped"
    systemctl is-active redis-server && echo "   ✓ Redis: Running" || echo "   ✗ Redis: Stopped"
    echo
    info "📁 Log Files:"
    info "   • Application: /var/log/moxnas/"
    info "   • Nginx: /var/log/nginx/"
    info "   • System: journalctl -u moxnas"
    echo
    info "🔧 Management Commands:"
    info "   • Restart: systemctl restart moxnas"
    info "   • View logs: journalctl -u moxnas -f"
    info "   • Configure services: cd $MOXNAS_ROOT/backend && python manage.py configure_services"
    echo
}

# Main deployment function
main() {
    log "Starting MoxNAS production deployment..."
    
    check_root
    check_requirements
    install_dependencies
    setup_user_and_directories
    deploy_backend
    deploy_frontend
    configure_database
    configure_services
    configure_nginx
    configure_firewall
    optimize_performance
    security_hardening
    start_services
    validate_deployment
    display_summary
    
    log "🎉 MoxNAS deployment completed successfully!"
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "MoxNAS Production Deployment Script"
        echo
        echo "Usage: $0 [options]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --validate     Validate existing deployment"
        echo "  --update       Update existing installation"
        echo
        exit 0
        ;;
    --validate)
        log "Validating existing MoxNAS deployment..."
        validate_deployment
        exit 0
        ;;
    --update)
        log "Updating existing MoxNAS installation..."
        deploy_backend
        deploy_frontend
        configure_database
        configure_services
        systemctl restart moxnas
        validate_deployment
        log "✓ Update completed"
        exit 0
        ;;
    *)
        main
        ;;
esac