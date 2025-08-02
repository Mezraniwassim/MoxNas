#!/bin/bash

# MoxNAS Installation Script
# Designed for LXC containers in Proxmox environments

set -e

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
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        exit 1
    fi
}

# Improved network connectivity check
check_network() {
    log "Checking network connectivity..."
    
    # Try multiple methods to check connectivity
    local connectivity=false
    
    # Method 1: Try ping (may fail due to ICMP blocking)
    if ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1; then
        log "Network connectivity confirmed via ping"
        connectivity=true
    else
        warn "Ping failed (likely due to ICMP blocking)"
    fi
    
    # Method 2: Try wget/curl to download something
    if ! $connectivity; then
        if command -v wget >/dev/null 2>&1; then
            if wget --timeout=10 --tries=1 --spider http://archive.ubuntu.com >/dev/null 2>&1; then
                log "Network connectivity confirmed via wget"
                connectivity=true
            fi
        elif command -v curl >/dev/null 2>&1; then
            if curl --max-time 10 --silent --head http://archive.ubuntu.com >/dev/null 2>&1; then
                log "Network connectivity confirmed via curl"
                connectivity=true
            fi
        fi
    fi
    
    # Method 3: Try DNS resolution
    if ! $connectivity; then
        if nslookup google.com >/dev/null 2>&1; then
            log "Network connectivity confirmed via DNS resolution"
            connectivity=true
        fi
    fi
    
    if ! $connectivity; then
        error "No network connectivity detected. Please check your network configuration."
        read -p "Do you want to continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        warn "Continuing without network verification..."
    fi
}

# Check if running in a container
detect_container() {
    if [ -f /.dockerenv ] || [ -f /run/.containerenv ]; then
        log "Container environment detected"
        export CONTAINER_ENV=true
    elif grep -q 'container=lxc' /proc/1/environ 2>/dev/null; then
        log "LXC container environment detected"
        export CONTAINER_ENV=true
    elif systemd-detect-virt -c >/dev/null 2>&1; then
        log "Container environment detected via systemd"
        export CONTAINER_ENV=true
    else
        export CONTAINER_ENV=false
    fi
}

# Fix locale issues
fix_locales() {
    log "Fixing locale configuration..."
    
    # Set proper locale
    export LANG=C.UTF-8
    export LC_ALL=C.UTF-8
    
    # Update locale configuration
    if [ -f /etc/locale.gen ]; then
        sed -i 's/^# en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen 2>/dev/null || true
        locale-gen >/dev/null 2>&1 || warn "locale-gen failed"
    fi
    
    # Set locale for the session
    echo 'export LANG=C.UTF-8' >> /etc/environment
    echo 'export LC_ALL=C.UTF-8' >> /etc/environment
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package list with retry
    for i in {1..3}; do
        if apt-get update -qq; then
            break
        else
            warn "Package update attempt $i failed, retrying..."
            sleep 5
        fi
    done
    
    # Install essential packages with error handling
    log "Installing core packages..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        wget \
        unzip \
        build-essential \
        pkg-config \
        libffi-dev \
        libssl-dev \
        sqlite3 \
        libsqlite3-dev || {
        error "Failed to install core packages"
        exit 1
    }
    
    # Install Node.js (try multiple methods for different Ubuntu versions)
    log "Installing Node.js..."
    if ! command -v node >/dev/null 2>&1; then
        # Try system package first
        if DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs npm; then
            log "Node.js installed from system packages"
        else
            # Fallback: install from NodeSource
            warn "System Node.js failed, trying NodeSource..."
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash - || true
            DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs || warn "Node.js installation failed"
        fi
    else
        log "Node.js already installed"
    fi
    
    # Install optional packages (don't fail if these don't work)
    log "Installing optional packages..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        nginx \
        supervisor \
        net-tools \
        lsof \
        psmisc \
        htop \
        nano \
        vim 2>/dev/null || warn "Some optional packages failed to install"
    
    log "System dependencies installation completed"
}

# Install NAS services
install_nas_services() {
    log "Installing NAS services..."
    
    # Install each service with error handling
    local services=(
        "samba samba-common-bin:SMB/CIFS"
        "nfs-kernel-server nfs-common:NFS"
        "vsftpd:FTP"
        "openssh-server:SSH"
        "rsync:Rsync"
    )
    
    for service_info in "${services[@]}"; do
        local packages="${service_info%:*}"
        local name="${service_info#*:}"
        
        log "Installing $name service..."
        if DEBIAN_FRONTEND=noninteractive apt-get install -y $packages; then
            log "✅ $name service installed"
        else
            warn "⚠️ $name service installation failed (will continue)"
        fi
    done
    
    # Optional services (don't fail installation if these don't work)
    log "Installing optional services..."
    local optional_services=(
        "snmpd:SNMP"
        "tgt:iSCSI"
    )
    
    for service_info in "${optional_services[@]}"; do
        local packages="${service_info%:*}"
        local name="${service_info#*:}"
        
        if DEBIAN_FRONTEND=noninteractive apt-get install -y $packages 2>/dev/null; then
            log "✅ $name service installed"
        else
            warn "⚠️ $name service not available (optional)"
        fi
    done
    
    log "NAS services installation completed"
}

# Setup MoxNAS application
setup_moxnas() {
    log "Setting up MoxNAS application..."
    
    local INSTALL_DIR="/opt/moxnas"
    local CURRENT_DIR="$(pwd)"
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Copy files to installation directory
    if [ -d "$CURRENT_DIR/backend" ] && [ -d "$CURRENT_DIR/frontend" ]; then
        log "Copying MoxNAS files..."
        cp -r "$CURRENT_DIR"/* "$INSTALL_DIR/"
        chown -R root:root "$INSTALL_DIR"
        chmod -R 755 "$INSTALL_DIR"
    else
        error "MoxNAS source files not found in current directory"
        exit 1
    fi
    
    cd "$INSTALL_DIR"
    
    # Create Python virtual environment
    log "Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    
    # Install Python dependencies
    log "Installing Python dependencies..."
    pip install --upgrade pip
    
    # Install dependencies from requirements files
    if [ -f "backend/requirements.txt" ]; then
        pip install -r backend/requirements.txt
    else
        # Install essential packages manually
        pip install \
            django>=4.2 \
            djangorestframework \
            django-cors-headers \
            python-decouple \
            psutil \
            gunicorn \
            whitenoise \
            requests
    fi
    
    # Install Node.js dependencies and build frontend
    if [ -d "frontend" ]; then
        log "Building frontend..."
        cd frontend
        npm install --production
        
        # Build React app
        if npm run build; then
            log "Frontend built successfully"
        else
            warn "Frontend build failed, but continuing..."
        fi
        cd ..
    fi
    
    deactivate
    log "MoxNAS application setup completed"
}

# Configure services for container environment
configure_services() {
    log "Configuring services for container environment..."
    
    # Create required directories
    mkdir -p /mnt/storage
    mkdir -p /var/log/moxnas
    mkdir -p /etc/moxnas
    mkdir -p /var/run/moxnas
    
    # Set proper permissions
    chmod 755 /mnt/storage
    chmod 755 /var/log/moxnas
    chmod 755 /etc/moxnas
    chmod 755 /var/run/moxnas
    
    # Configure Samba for container
    if [ "$CONTAINER_ENV" = true ]; then
        log "Configuring Samba for container environment..."
        
        # Basic Samba configuration
        cat > /etc/samba/smb.conf << 'EOF'
[global]
    workgroup = WORKGROUP
    server string = MoxNAS Server
    netbios name = MOXNAS
    security = user
    map to guest = bad user
    dns proxy = no
    load printers = no
    printcap name = /dev/null
    disable spoolss = yes
    socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=131072 SO_SNDBUF=131072
    local master = no
    domain master = no
    preferred master = no
    os level = 20
    
[storage]
    comment = MoxNAS Storage
    path = /mnt/storage
    browseable = yes
    writable = yes
    guest ok = yes
    read only = no
    create mask = 0664
    directory mask = 0775
EOF
    fi
    
    # Configure NFS exports
    echo "/mnt/storage *(rw,sync,no_subtree_check,no_root_squash,insecure)" > /etc/exports
    
    # Configure FTP
    if [ "$CONTAINER_ENV" = true ]; then
        log "Configuring FTP for container environment..."
        
        cat > /etc/vsftpd.conf << 'EOF'
anonymous_enable=YES
local_enable=YES
write_enable=YES
anon_upload_enable=YES
anon_mkdir_write_enable=YES
anon_root=/mnt/storage
anon_other_write_enable=YES
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=50000
seccomp_sandbox=NO
allow_writeable_chroot=YES
listen=YES
listen_ipv6=NO
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
chroot_local_user=NO
secure_chroot_dir=/var/run/vsftpd/empty
EOF
        
        # Create FTP secure directory
        mkdir -p /var/run/vsftpd/empty
        chmod 755 /var/run/vsftpd/empty
    fi
}

# Start MoxNAS services
start_moxnas() {
    log "Starting MoxNAS services..."
    
    cd /opt/moxnas
    
    # Start Django application
    if [ -f "backend/start_moxnas.py" ]; then
        log "Starting MoxNAS web interface..."
        nohup python3 backend/start_moxnas.py > /var/log/moxnas/startup.log 2>&1 &
        sleep 5
        
        # Check if it started successfully
        if pgrep -f "start_moxnas.py" > /dev/null; then
            log "MoxNAS web interface started successfully"
        else
            warn "MoxNAS web interface may not have started properly"
        fi
    else
        warn "MoxNAS startup script not found"
    fi
}

# Get container IP
get_container_ip() {
    local ip=$(hostname -I | awk '{print $1}')
    if [ -n "$ip" ]; then
        echo "$ip"
    else
        echo "localhost"
    fi
}

# Main installation process
main() {
    log "Starting MoxNAS installation..."
    
    check_root
    detect_container
    fix_locales
    check_network
    
    install_dependencies
    install_nas_services
    setup_moxnas
    configure_services
    start_moxnas
    
    local container_ip=$(get_container_ip)
    
    log "=================================================="
    log "✅ MoxNAS installation completed successfully!"
    log "=================================================="
    log ""
    log "🌐 Access MoxNAS at:"
    log "   http://$container_ip:8000"
    log "   http://localhost:8000 (if accessing from host)"
    log ""
    log "📊 Admin interface:"
    log "   http://$container_ip:8000/admin"
    log ""
    log "🔧 API documentation:"
    log "   http://$container_ip:8000/api"
    log ""
    log "📁 Storage directory: /mnt/storage"
    log "📝 Logs directory: /var/log/moxnas"
    log ""
    log "To manage services:"
    log "  - Start: systemctl start [service]"
    log "  - Stop: systemctl stop [service]"
    log "  - Status: systemctl status [service]"
    log ""
    log "Services: smbd, nmbd, vsftpd, nfs-kernel-server, ssh"
    log "=================================================="
}

# Run main installation
main "$@"