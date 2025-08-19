#!/bin/bash
# MoxNAS Local Installation Script
# For testing and development purposes
# Copyright (c) 2024 MoxNAS Contributors
# License: MIT

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
MOXNAS_VERSION="1.0.0"
INSTALL_DIR="/opt/moxnas"
WEB_DIR="/var/www/moxnas"
CONFIG_DIR="/etc/moxnas"
LOG_DIR="/var/log/moxnas"

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

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

check_system() {
    log_info "Checking system requirements..."
    
    # Check if running on Ubuntu/Debian
    if ! command -v apt-get >/dev/null 2>&1; then
        log_error "This installer requires Ubuntu/Debian with apt-get"
        exit 1
    fi
    
    # Check available space
    available_space=$(df / | awk 'NR==2 {print $4}')
    required_space=2097152  # 2GB in KB
    
    if [[ $available_space -lt $required_space ]]; then
        log_error "Insufficient disk space. Required: 2GB, Available: $((available_space/1024/1024))GB"
        exit 1
    fi
    
    log_success "System requirements met"
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
    
    if hugo version >/dev/null 2>&1; then
        log_success "Hugo installed successfully"
    else
        log_error "Hugo installation failed"
        exit 1
    fi
}

install_dependencies() {
    log_info "Installing system dependencies..."
    
    apt-get update -qq
    
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
        systemctl \
        ca-certificates
    
    # Python packages
    pip3 install --quiet --upgrade pip
    pip3 install --quiet \
        aiohttp \
        aiofiles \
        psutil \
        jinja2
    
    log_success "Dependencies installed"
}

setup_directories() {
    log_info "Setting up directories..."
    
    # Create directories
    mkdir -p "$INSTALL_DIR"/{api,scripts,config}
    mkdir -p "$WEB_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p /mnt/shares/{public,ftp}
    
    # Set permissions
    chown -R root:root "$INSTALL_DIR"
    chown -R www-data:www-data "$WEB_DIR"
    chown -R root:root "$CONFIG_DIR"
    chown -R root:root "$LOG_DIR"
    chmod 755 /mnt/shares
    chmod 777 /mnt/shares/public /mnt/shares/ftp
    chown nobody:nogroup /mnt/shares/public /mnt/shares/ftp
    
    log_success "Directories created"
}

install_moxnas() {
    log_info "Installing MoxNAS application..."
    
    local current_dir=$(pwd)
    
    # Copy API server
    cp "$current_dir/api-server.py" "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/api-server.py"
    
    # Copy management scripts
    cp -r "$current_dir/scripts/"* "$INSTALL_DIR/scripts/"
    chmod +x "$INSTALL_DIR/scripts"/*/*.sh
    
    # Copy configuration templates
    cp -r "$current_dir/config/templates" "$INSTALL_DIR/config/"
    
    # Install Hugo site if not already built
    if [[ -d "$current_dir/public" ]]; then
        cp -r "$current_dir/public/"* "$WEB_DIR/"
    else
        log_info "Building Hugo site..."
        cd "$current_dir"
        hugo --destination "$WEB_DIR"
        cd "$current_dir"
    fi
    
    log_success "MoxNAS application installed"
}

configure_nginx() {
    log_info "Configuring nginx..."
    
    # Copy nginx configuration
    cp config/nginx/moxnas.conf /etc/nginx/sites-available/
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Enable MoxNAS site
    ln -sf /etc/nginx/sites-available/moxnas.conf /etc/nginx/sites-enabled/
    
    # Test configuration
    if nginx -t; then
        log_success "Nginx configured successfully"
    else
        log_error "Nginx configuration test failed"
        exit 1
    fi
}

configure_services() {
    log_info "Configuring NAS services..."
    
    # Backup original configurations
    [[ -f /etc/samba/smb.conf ]] && cp /etc/samba/smb.conf /etc/samba/smb.conf.backup
    [[ -f /etc/exports ]] && cp /etc/exports /etc/exports.backup
    [[ -f /etc/vsftpd.conf ]] && cp /etc/vsftpd.conf /etc/vsftpd.conf.backup
    
    # Install default configurations
    cp config/templates/smb.conf.template /etc/samba/smb.conf
    cp config/templates/exports.template /etc/exports
    cp config/templates/vsftpd.conf.template /etc/vsftpd.conf
    
    # Create default public share in Samba
    cat >> /etc/samba/smb.conf << 'EOF'

[public]
   comment = MoxNAS public share
   path = /mnt/shares/public
   browseable = yes
   read only = no
   guest ok = yes
   create mask = 0755
   directory mask = 0755
   force user = nobody
   force group = nogroup
   map archive = no
   store dos attributes = yes
   vfs objects = catia fruit streams_xattr
   fruit:time machine = no
EOF
    
    # Add public share to NFS exports
    echo "/mnt/shares/public *(rw,sync,no_subtree_check,all_squash,anonuid=65534,anongid=65534)" >> /etc/exports
    
    log_success "NAS services configured"
}

setup_systemd() {
    log_info "Setting up systemd services..."
    
    # Install systemd service files
    cp config/systemd/moxnas-api.service /etc/systemd/system/
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable services
    systemctl enable moxnas-api
    systemctl enable nginx
    systemctl enable smbd
    systemctl enable nfs-kernel-server
    systemctl enable vsftpd
    
    log_success "Systemd services configured"
}

start_services() {
    log_info "Starting services..."
    
    # Start MoxNAS API
    systemctl start moxnas-api
    sleep 2
    
    # Start web server
    systemctl start nginx
    
    # Start NAS services
    systemctl start smbd
    systemctl start nfs-kernel-server
    systemctl start vsftpd
    
    # Export NFS shares
    exportfs -ra
    
    # Check service status
    local failed_services=()
    
    for service in moxnas-api nginx smbd nfs-kernel-server vsftpd; do
        if ! systemctl is-active --quiet "$service"; then
            failed_services+=("$service")
        fi
    done
    
    if [[ ${#failed_services[@]} -eq 0 ]]; then
        log_success "All services started successfully"
    else
        log_warning "Some services failed to start: ${failed_services[*]}"
        log_info "Check service status with: systemctl status <service-name>"
    fi
}

create_default_config() {
    log_info "Creating default configuration..."
    
    # Create users configuration
    cat > "$CONFIG_DIR/users.json" << 'EOF'
{
    "admin": {
        "password": "admin",
        "role": "administrator",
        "created": "2024-01-01T00:00:00.000Z"
    }
}
EOF
    
    # Create shares configuration
    cat > "$CONFIG_DIR/shares.json" << 'EOF'
{
    "shares": [
        {
            "name": "public",
            "type": "smb",
            "path": "/mnt/shares/public",
            "active": true,
            "guest_access": true
        }
    ]
}
EOF
    
    # Set proper permissions
    chmod 600 "$CONFIG_DIR/users.json"
    chmod 644 "$CONFIG_DIR/shares.json"
    
    log_success "Default configuration created"
}

show_completion_info() {
    local ip_address
    ip_address=$(hostname -I | awk '{print $1}' || echo "localhost")
    
    log_success "MoxNAS installation completed successfully!"
    echo
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}                                   MoxNAS Ready                                     ${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo
    echo -e "${BLUE}Web Interface:${NC} http://${ip_address}:8000"
    echo -e "${BLUE}Default Login:${NC} admin / admin"
    echo
    echo -e "${BLUE}Services:${NC}"
    echo "  • SMB/CIFS: //$(hostname)/public or //${ip_address}/public"
    echo "  • NFS: ${ip_address}:/mnt/shares/public"
    echo "  • FTP: ftp://${ip_address} (anonymous access enabled)"
    echo
    echo -e "${BLUE}Management:${NC}"
    echo "  • Service status: systemctl status moxnas-api"
    echo "  • View logs: journalctl -u moxnas-api -f"
    echo "  • Configuration: ${CONFIG_DIR}/"
    echo
    echo -e "${YELLOW}Important:${NC}"
    echo "  • Change default password immediately"
    echo "  • Configure firewall rules as needed"
    echo "  • Check service logs for any issues"
    echo
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

cleanup() {
    log_info "Cleaning up..."
    
    # Remove temporary files
    rm -rf /tmp/hugo*
    
    # Clean package cache
    apt-get autoremove -y -qq
    apt-get autoclean -qq
    
    log_success "Cleanup completed"
}

main() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                        MoxNAS Installer                          ║"
    echo "║                   TrueNAS-like NAS for LXC                       ║"
    echo "║                        Version ${MOXNAS_VERSION}                            ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    check_root
    check_system
    
    log_info "Starting MoxNAS installation..."
    
    install_dependencies
    install_hugo
    setup_directories
    install_moxnas
    configure_nginx
    configure_services
    setup_systemd
    create_default_config
    start_services
    cleanup
    
    # Write version file
    echo "$MOXNAS_VERSION" > /opt/MoxNAS_version.txt
    
    show_completion_info
}

# Handle errors
handle_error() {
    log_error "Installation failed at line $1"
    log_error "Command: $2"
    log_error "Exit code: $3"
    log_info "Check the logs above for more details"
    exit 1
}

trap 'handle_error $LINENO "$BASH_COMMAND" $?' ERR

# Run main function
main "$@"