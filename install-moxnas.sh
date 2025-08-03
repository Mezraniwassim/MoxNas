#!/bin/bash

# MoxNas One-Command Installation 
# Usage: curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas.sh | bash
# Version: 2.0.0

set -euo pipefail

# Configuration
MOXNAS_VERSION="2.0.0"
TEST_MODE="false"
AUTO_MODE="false"
GITHUB_REPO="Mezraniwassim/MoxNas"
INSTALL_LOG="/tmp/moxnas-install.log"
REQUIREMENTS_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/master/requirements.txt"

# Colors and formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Logging functions
log() { 
    local msg="$1"
    echo -e "${BLUE}[$(date '+%H:%M:%S')] [MOXNAS]${NC} $msg" | tee -a "$INSTALL_LOG"
}
success() { 
    local msg="$1"
    echo -e "${GREEN}[$(date '+%H:%M:%S')] [SUCCESS]${NC} $msg" | tee -a "$INSTALL_LOG"
}
error() { 
    local msg="$1"
    echo -e "${RED}[$(date '+%H:%M:%S')] [ERROR]${NC} $msg" | tee -a "$INSTALL_LOG"
}
warning() { 
    local msg="$1"
    echo -e "${YELLOW}[$(date '+%H:%M:%S')] [WARNING]${NC} $msg" | tee -a "$INSTALL_LOG"
}
info() { 
    local msg="$1"
    echo -e "${CYAN}[$(date '+%H:%M:%S')] [INFO]${NC} $msg" | tee -a "$INSTALL_LOG"
}

# Progress bar function
show_progress() {
    local duration=$1
    local step_name="$2"
    local elapsed=0
    local bar_length=30
    
    while [ $elapsed -lt $duration ]; do
        local progress=$((elapsed * bar_length / duration))
        local bar=$(printf "%-${bar_length}s" "$(printf '%*s' $progress | tr ' ' '█')")
        printf "\r${BLUE}[PROGRESS]${NC} $step_name [${bar}] ${elapsed}s/${duration}s"
        sleep 1
        ((elapsed++))
    done
    printf "\n"
}

# Print banner
print_banner() {
    clear
    echo -e "${PURPLE}
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║    ${BOLD}${CYAN}███╗   ███╗ ██████╗ ██╗  ██╗███╗   ██╗ █████╗ ███████╗${NC}${PURPLE}              ║
║    ${BOLD}${CYAN}████╗ ████║██╔═══██╗╚██╗██╔╝████╗  ██║██╔══██╗██╔════╝${NC}${PURPLE}              ║
║    ${BOLD}${CYAN}██╔████╔██║██║   ██║ ╚███╔╝ ██╔██╗ ██║███████║███████╗${NC}${PURPLE}              ║
║    ${BOLD}${CYAN}██║╚██╔╝██║██║   ██║ ██╔██╗ ██║╚██╗██║██╔══██║╚════██║${NC}${PURPLE}              ║
║    ${BOLD}${CYAN}██║ ╚═╝ ██║╚██████╔╝██╔╝ ██╗██║ ╚████║██║  ██║███████║${NC}${PURPLE}              ║
║    ${BOLD}${CYAN}╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝${NC}${PURPLE}              ║
║                                                                      ║
║    ${BOLD}Professional NAS Management for Proxmox VE${NC}${PURPLE}                      ║
║    ${YELLOW}Version: $MOXNAS_VERSION${NC}${PURPLE}                                               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝${NC}
"
    echo -e "${BOLD}${GREEN}🚀 One-Command Installation Starting...${NC}\n"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        error "Installation failed! Check log: $INSTALL_LOG"
        echo -e "\n${YELLOW}Troubleshooting:${NC}"
        echo "1. Check Proxmox VE version (requires 8.0+)"
        echo "2. Ensure running as root"
        echo "3. Verify network connectivity"
        echo "4. Check available storage space"
        echo -e "\n${BLUE}Support: https://github.com/${GITHUB_REPO}/issues${NC}"
    fi
}
trap cleanup EXIT

# System requirements check
check_system_requirements() {
    log "Checking system requirements..."
    
    # Available memory
    local total_mem=$(free -m | awk 'NR==2{print $2}')
    if [ $total_mem -lt 4096 ]; then
        warning "Low memory detected (${total_mem}MB). Recommended: 4GB+"
    fi
    
    # Available disk space
    local available_space=$(df / | awk 'NR==2{print $4}')
    if [ $available_space -lt 10485760 ]; then  # 10GB in KB
        error "Insufficient disk space. Required: 10GB+"
        exit 1
    fi
    
    # Network connectivity
    if ! ping -c 1 8.8.8.8 &>/dev/null; then
        warning "Internet connectivity issues detected"
    fi
    
    success "System requirements check passed"
}

# Check Proxmox with enhanced validation
check_proxmox() {
    log "Validating Proxmox environment..."
    
    # Check if running on Proxmox (skip in test mode)
    if [[ "$TEST_MODE" != "true" ]]; then
        if ! command -v pct >/dev/null 2>&1; then
            error "This script must be run on a Proxmox VE host"
            error "Current system: $(uname -a)"
            exit 1
        fi
    fi
    
    # Check root privileges
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        error "Please run: sudo $0 $*"
        exit 1
    fi
    
    # Check Proxmox version
    if [[ "$TEST_MODE" != "true" ]]; then
        local pve_version=$(pveversion | head -1 | cut -d'/' -f2 | cut -d'-' -f1)
        log "Proxmox VE version: $pve_version"
        
        # Verify essential services
        if ! systemctl is-active --quiet pvedaemon; then
            error "Proxmox daemon is not running"
            exit 1
        fi
    else
        log "Proxmox VE version: 8.1.0 (test mode)"
    fi
    
    success "Proxmox VE environment validated"
}

# Enhanced environment detection
detect_environment() {
    log "Auto-detecting optimal Proxmox configuration..."
    
    # Storage detection with priority order
    info "Scanning available storage..."
    local storage_options=()
    
    # Check each storage type in priority order
    for storage in "local-lvm" "local-zfs" "local-btrfs"; do
        if pvesm status | grep -q "^${storage}.*active"; then
            storage_options+=("$storage")
            info "✓ Found active storage: $storage"
        fi
    done
    
    # Fallback to any available storage
    if [ ${#storage_options[@]} -eq 0 ]; then
        readarray -t storage_options < <(pvesm status | awk 'NR>1 && $3=="active" && $1!="local" {print $1}')
    fi
    
    if [ ${#storage_options[@]} -eq 0 ]; then
        error "No suitable container storage found"
        echo "Available storage pools:"
        pvesm status
        exit 1
    fi
    
    AVAILABLE_STORAGE="${storage_options[0]}"
    
    # Network bridge detection
    info "Detecting network configuration..."
    NETWORK_BRIDGE=$(ip link show type bridge | grep -o "vmbr[0-9]*" | head -1)
    [[ -z "$NETWORK_BRIDGE" ]] && NETWORK_BRIDGE="vmbr0"
    
    # Check if bridge exists and is active
    if ! ip link show "$NETWORK_BRIDGE" &>/dev/null; then
        warning "Bridge $NETWORK_BRIDGE not found, using vmbr0"
        NETWORK_BRIDGE="vmbr0"
    fi
    
    # Find optimal container ID
    info "Finding available container ID..."
    CONTAINER_ID=200
    while pct status $CONTAINER_ID >/dev/null 2>&1; do
        ((CONTAINER_ID++))
        if [ $CONTAINER_ID -gt 999 ]; then
            error "No available container IDs (200-999)"
            exit 1
        fi
    done
    
    # Intelligent resource allocation
    info "Calculating optimal resource allocation..."
    local total_mem=$(free -m | awk 'NR==2{print $2}')
    local total_cores=$(nproc)
    
    # Memory calculation (25-50% of total, min 3GB, max 8GB)
    CONTAINER_MEMORY=$(( total_mem / 4 ))
    [[ $CONTAINER_MEMORY -lt 3072 ]] && CONTAINER_MEMORY=3072
    [[ $CONTAINER_MEMORY -gt 8192 ]] && CONTAINER_MEMORY=8192
    
    # CPU calculation (25-50% of total, min 2, max 6)
    CONTAINER_CORES=$(( total_cores / 3 ))
    [[ $CONTAINER_CORES -lt 2 ]] && CONTAINER_CORES=2
    [[ $CONTAINER_CORES -gt 6 ]] && CONTAINER_CORES=6
    
    # Swap calculation (1/3 of memory)
    CONTAINER_SWAP=$(( CONTAINER_MEMORY / 3 ))
    
    # Disk space calculation
    local storage_info=$(pvesm status | grep "^$AVAILABLE_STORAGE")
    local total_space=$(echo "$storage_info" | awk '{print $4}')
    local used_space=$(echo "$storage_info" | awk '{print $3}')
    local available_space=$(( total_space - used_space ))
    
    CONTAINER_DISK=32  # Default 32GB
    if [ $available_space -lt 34359738368 ]; then  # Less than 32GB available
        CONTAINER_DISK=16
        warning "Limited storage space, reducing container disk to 16GB"
    fi
    
    success "Environment optimally configured:"
    echo -e "  ${CYAN}Storage:${NC} $AVAILABLE_STORAGE"
    echo -e "  ${CYAN}Network:${NC} $NETWORK_BRIDGE"
    echo -e "  ${CYAN}Container ID:${NC} $CONTAINER_ID"
    echo -e "  ${CYAN}Memory:${NC} ${CONTAINER_MEMORY}MB"
    echo -e "  ${CYAN}CPU Cores:${NC} $CONTAINER_CORES"
    echo -e "  ${CYAN}Swap:${NC} ${CONTAINER_SWAP}MB"
    echo -e "  ${CYAN}Disk:${NC} ${CONTAINER_DISK}GB"
}

# Enhanced template management
ensure_template() {
    log "Ensuring Ubuntu 22.04 LTS template..."
    
    local template_file="/var/lib/vz/template/cache/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
    local template_name="ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
    
    if [[ ! -f "$template_file" ]]; then
        log "Ubuntu template not found, downloading..."
        
        # Update template database
        if ! pveam update; then
            error "Failed to update template database"
            return 1
        fi
        
        # Download template with progress
        if ! pveam download local "$template_name"; then
            error "Failed to download Ubuntu template"
            return 1
        fi
        
        success "Ubuntu template downloaded successfully"
    else
        success "Ubuntu template already available"
    fi
    
    return 0
}

# Create container
create_container() {
    log "Creating container $CONTAINER_ID with optimized settings..."
    
    # Create container with comprehensive configuration
    if ! pct create $CONTAINER_ID \
        "/var/lib/vz/template/cache/ubuntu-22.04-standard_22.04-1_amd64.tar.zst" \
        --hostname "moxnas-$(date +%Y%m%d)" \
        --memory $CONTAINER_MEMORY \
        --swap $CONTAINER_SWAP \
        --cores $CONTAINER_CORES \
        --rootfs "$AVAILABLE_STORAGE:$CONTAINER_DISK" \
        --net0 "name=eth0,bridge=$NETWORK_BRIDGE,ip=dhcp,firewall=1" \
        --features "nesting=1,keyctl=1,mount=nfs;cifs" \
        --unprivileged 1 \
        --protection 0 \
        --startup "order=2,up=30" \
        --description "MoxNas v$MOXNAS_VERSION - Professional NAS Management System"; then
        error "Failed to create container"
        return 1
    fi
    
    success "Container $CONTAINER_ID created successfully"
    
    # Start container
    log "Starting container..."
    if ! pct start $CONTAINER_ID; then
        error "Failed to start container"
        return 1
    fi
    
    success "Container started successfully"
    
    # Wait for network initialization with timeout
    log "Waiting for network configuration..."
    local timeout=60
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        if pct exec $CONTAINER_ID -- ip route | grep -q default; then
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    if [ $elapsed -ge $timeout ]; then
        error "Network configuration timeout"
        return 1
    fi
    
    # Get container IP with retry logic
    log "Obtaining container IP address..."
    local ip_timeout=90
    local ip_elapsed=0
    
    while [ $ip_elapsed -lt $ip_timeout ]; do
        CONTAINER_IP=$(pct exec $CONTAINER_ID -- hostname -I 2>/dev/null | awk '{print $1}' | tr -d '\n' || true)
        
        if [[ $CONTAINER_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            success "Container IP obtained: $CONTAINER_IP"
            return 0
        fi
        
        sleep 3
        ip_elapsed=$((ip_elapsed + 3))
    done
    
    error "Failed to obtain container IP address"
    return 1
}

# Enhanced dependency installation
install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package database
    info "Updating package database..."
    if ! pct exec $CONTAINER_ID -- apt-get update -qq; then
        error "Failed to update package database"
        return 1
    fi
    
    # Upgrade system packages
    info "Upgrading system packages..."
    if ! pct exec $CONTAINER_ID -- apt-get upgrade -y -qq; then
        warning "Some packages failed to upgrade (non-critical)"
    fi
    
    # Install essential packages
    info "Installing essential packages..."
    local packages=(
        "curl" "wget" "git" "unzip" "software-properties-common"
        "python3" "python3-pip" "python3-venv" "python3-dev"
        "nodejs" "npm" "nginx" 
        "postgresql" "postgresql-contrib" "postgresql-client"
        "redis-server"
        "openssh-server" "vsftpd" "samba" "nfs-kernel-server"
        "systemd" "supervisor" "htop" "nano" "net-tools"
        "build-essential" "libpq-dev" "libffi-dev" "libssl-dev"
    )
    
    if ! pct exec $CONTAINER_ID -- apt-get install -y "${packages[@]}"; then
        error "Failed to install required packages"
        return 1
    fi
    
    # Install Node.js LTS if needed
    info "Verifying Node.js version..."
    local node_version=$(pct exec $CONTAINER_ID -- node --version 2>/dev/null | cut -d'v' -f2 || echo "0")
    if [[ $(echo "$node_version" | cut -d'.' -f1) -lt 18 ]]; then
        log "Installing Node.js 18 LTS..."
        pct exec $CONTAINER_ID -- curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        pct exec $CONTAINER_ID -- apt-get install -y nodejs
    fi
    
    success "System dependencies installed successfully"
    return 0
}

# Enhanced application setup
setup_application() {
    log "Setting up MoxNas application..."
    
    # Clone repository
    info "Cloning MoxNas repository..."
    if ! pct exec $CONTAINER_ID -- git clone "https://github.com/${GITHUB_REPO}.git" /opt/moxnas; then
        error "Failed to clone MoxNas repository"
        return 1
    fi
    
    # Set proper permissions
    pct exec $CONTAINER_ID -- chown -R root:root /opt/moxnas
    pct exec $CONTAINER_ID -- chmod +x /opt/moxnas/scripts/*.sh
    
    # Python virtual environment setup
    info "Setting up Python virtual environment..."
    if ! pct exec $CONTAINER_ID -- python3 -m venv /opt/moxnas/venv; then
        error "Failed to create Python virtual environment"
        return 1
    fi
    
    # Install Python dependencies
    info "Installing Python dependencies..."
    if ! pct exec $CONTAINER_ID -- /opt/moxnas/venv/bin/pip install --upgrade pip setuptools wheel; then
        error "Failed to upgrade pip"
        return 1
    fi
    
    if ! pct exec $CONTAINER_ID -- /opt/moxnas/venv/bin/pip install -r /opt/moxnas/requirements.txt; then
        error "Failed to install Python dependencies"
        return 1
    fi
    
    # Frontend setup
    info "Setting up frontend application..."
    if ! pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/frontend && npm ci --silent"; then
        error "Failed to install frontend dependencies"
        return 1
    fi
    
    # Build frontend with error handling
    info "Building frontend application (this may take a few minutes)..."
    if ! pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/frontend && NODE_OPTIONS='--max-old-space-size=2048' npm run build:prod"; then
        warning "Production build failed, trying standard build..."
        if ! pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/frontend && NODE_OPTIONS='--max-old-space-size=1536' npm run build"; then
            error "Frontend build failed"
            return 1
        fi
    fi
    
    # Database setup
    info "Configuring PostgreSQL database..."
    
    # Start PostgreSQL
    pct exec $CONTAINER_ID -- systemctl start postgresql
    pct exec $CONTAINER_ID -- systemctl enable postgresql
    
    # Create database and user
    if ! pct exec $CONTAINER_ID -- sudo -u postgres createdb moxnas_db 2>/dev/null; then
        warning "Database might already exist"
    fi
    
    if ! pct exec $CONTAINER_ID -- sudo -u postgres psql -c "CREATE USER moxnas_user WITH PASSWORD 'moxnas_pass_$(date +%s)';" 2>/dev/null; then
        warning "Database user might already exist"
    fi
    
    pct exec $CONTAINER_ID -- sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE moxnas_db TO moxnas_user;"
    
    # Generate secure environment configuration
    info "Generating secure configuration..."
    local secret_key=$(pct exec $CONTAINER_ID -- python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    local db_password="moxnas_pass_$(date +%s)"
    
    cat > /tmp/moxnas_env << EOF
# MoxNas Configuration - Generated $(date)
SECRET_KEY=$secret_key
DEBUG=False
ALLOWED_HOSTS=$CONTAINER_IP,localhost,127.0.0.1,moxnas

# Database Configuration
DATABASE_URL=postgresql://moxnas_user:$db_password@localhost/moxnas_db

# Proxmox Configuration (Update these settings via web interface)
PROXMOX_HOST=192.168.1.100
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your_proxmox_password
PROXMOX_NODE=pve
PROXMOX_PORT=8006
PROXMOX_VERIFY_SSL=False

# Container Configuration
CONTAINER_TEMPLATE=ubuntu-22.04-standard_22.04-1_amd64.tar.zst
CONTAINER_STORAGE=$AVAILABLE_STORAGE
CONTAINER_MEMORY=$CONTAINER_MEMORY
CONTAINER_CORES=$CONTAINER_CORES

# Security Settings
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_AGE=3600
CSRF_COOKIE_SECURE=False
SESSION_COOKIE_SECURE=False
EOF
    
    pct push $CONTAINER_ID /tmp/moxnas_env /opt/moxnas/.env
    rm /tmp/moxnas_env
    
    # Django setup
    info "Initializing Django application..."
    
    # Generate and apply migrations
    if ! pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/backend && /opt/moxnas/venv/bin/python manage.py makemigrations"; then
        error "Failed to generate database migrations"
        return 1
    fi
    
    if ! pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/backend && /opt/moxnas/venv/bin/python manage.py migrate"; then
        error "Failed to apply database migrations"
        return 1
    fi
    
    # Create superuser
    if ! pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/backend && echo \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@moxnas.local', 'admin123')\" | /opt/moxnas/venv/bin/python manage.py shell"; then
        error "Failed to create admin user"
        return 1
    fi
    
    # Collect static files
    if ! pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/backend && /opt/moxnas/venv/bin/python manage.py collectstatic --noinput"; then
        warning "Static files collection failed (non-critical)"
    fi
    
    success "MoxNas application configured successfully"
    return 0
}

# Configure services
configure_services() {
    log "Configuring services..."
    
    # Systemd service
    cat > /tmp/moxnas.service << 'EOF'
[Unit]
Description=MoxNas NAS Management System
After=network.target postgresql.service

[Service]
Type=forking
User=root
WorkingDirectory=/opt/moxnas/backend
Environment=PATH=/opt/moxnas/venv/bin
ExecStart=/opt/moxnas/venv/bin/gunicorn --daemon --bind 0.0.0.0:8000 --workers 3 --timeout 120 --max-requests 1000 --pid /var/run/moxnas.pid moxnas.wsgi:application
PIDFile=/var/run/moxnas.pid
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    pct push $CONTAINER_ID /tmp/moxnas.service /etc/systemd/system/moxnas.service
    rm /tmp/moxnas.service
    
    # Enable services
    pct exec $CONTAINER_ID -- systemctl daemon-reload
    pct exec $CONTAINER_ID -- systemctl enable moxnas postgresql ssh
    
    # Start MoxNas
    pct exec $CONTAINER_ID -- systemctl start postgresql
    pct exec $CONTAINER_ID -- systemctl start moxnas
    
    success "Services started"
}

# Test installation
test_installation() {
    log "Testing installation..."
    
    # Wait for service
    for i in {1..30}; do
        if curl -s --connect-timeout 5 http://$CONTAINER_IP:8000 >/dev/null; then
            success "✓ Web interface accessible"
            return 0
        fi
        sleep 3
    done
    
    warning "Web interface test failed"
    return 1
}

# Main function with enhanced workflow
main() {
    # Parse arguments
    for arg in "$@"; do
        case $arg in
            --test-mode)
                TEST_MODE="true"
                warning "Running in TEST MODE - Proxmox checks will be bypassed"
                ;;
            --auto)
                AUTO_MODE="true"
                ;;
        esac
    done
    
    # Initialize logging
    echo "MoxNas Installation Log - $(date)" > "$INSTALL_LOG"
    
    print_banner
    
    # Pre-flight checks
    check_system_requirements
    check_proxmox
    detect_environment
    echo
    
    # User confirmation
    echo -e "${BOLD}${YELLOW}Installation Summary:${NC}"
    echo -e "Container will be created with ID: ${BOLD}$CONTAINER_ID${NC}"
    echo -e "Memory allocation: ${BOLD}${CONTAINER_MEMORY}MB${NC}"
    echo -e "CPU cores: ${BOLD}$CONTAINER_CORES${NC}"
    echo -e "Storage: ${BOLD}$AVAILABLE_STORAGE${NC}"
    echo
    
    if [[ "$AUTO_MODE" != "true" ]]; then
        read -p "Continue with installation? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Installation cancelled by user"
            exit 0
        fi
    fi
    
    echo -e "${BOLD}${GREEN}🚀 Starting MoxNas deployment...${NC}\n"
    
    # Installation steps with progress tracking
    local steps=("ensure_template" "create_container" "install_dependencies" "setup_application" "configure_services" "test_installation")
    local step_names=("Template" "Container" "Dependencies" "Application" "Services" "Testing")
    local total_steps=${#steps[@]}
    
    for i in "${!steps[@]}"; do
        local step_num=$((i + 1))
        echo -e "\n${BOLD}${BLUE}[$step_num/$total_steps] ${step_names[i]} Setup${NC}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if "${steps[i]}"; then
            success "✓ ${step_names[i]} completed successfully"
        else
            error "✗ ${step_names[i]} failed"
            exit 1
        fi
    done
    
    # Final success message
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    success "🎉 MoxNas installation completed successfully!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo -e "${BOLD}${GREEN}📊 Installation Details:${NC}"
    echo -e "  ${CYAN}Container ID:${NC} $CONTAINER_ID"
    echo -e "  ${CYAN}Container IP:${NC} $CONTAINER_IP"
    echo -e "  ${CYAN}Web Interface:${NC} ${BOLD}${GREEN}http://$CONTAINER_IP:8000${NC}"
    echo -e "  ${CYAN}Default Login:${NC} ${BOLD}admin${NC} / ${BOLD}admin123${NC}"
    echo
    echo -e "${BOLD}${YELLOW}📚 Next Steps:${NC}"
    echo "1. Access the web interface using the URL above"
    echo "2. Change the default admin password"
    echo "3. Configure Proxmox connection settings"
    echo "4. Create your first NAS shares"
    echo
    echo -e "${BOLD}${BLUE}📖 Documentation:${NC} https://github.com/${GITHUB_REPO}"
    echo -e "${BOLD}${BLUE}💬 Support:${NC} https://github.com/${GITHUB_REPO}/issues"
    echo -e "${BOLD}${BLUE}📋 Installation Log:${NC} $INSTALL_LOG"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Execute main function with all arguments
main "$@"