#!/bin/bash

# MoxNas One-Click Installation for Alex
# Auto-detects Proxmox environment and creates container automatically
# Usage: curl -sSL https://raw.githubusercontent.com/your-repo/MoxNas/main/install_for_alex.sh | bash

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[MOXNAS]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running on Proxmox
check_proxmox() {
    log "Checking Proxmox environment..."
    
    if ! command -v pct >/dev/null 2>&1; then
        error "This script must be run on a Proxmox VE host"
        exit 1
    fi
    
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        exit 1
    fi
    
    success "Proxmox VE detected"
}

# Auto-detect available resources
detect_environment() {
    log "Auto-detecting Proxmox environment..."
    
    # Detect available storage
    AVAILABLE_STORAGE=$(pvesm status | grep -v "^Name" | head -1 | awk '{print $1}')
    if [[ -z "$AVAILABLE_STORAGE" ]]; then
        AVAILABLE_STORAGE="local-lvm"
    fi
    
    # Detect network bridge
    NETWORK_BRIDGE=$(ip link show type bridge | grep -o "vmbr[0-9]*" | head -1)
    if [[ -z "$NETWORK_BRIDGE" ]]; then
        NETWORK_BRIDGE="vmbr0"
    fi
    
    # Find next available container ID
    CONTAINER_ID=200
    while pct status $CONTAINER_ID >/dev/null 2>&1; do
        ((CONTAINER_ID++))
    done
    
    # Detect memory and CPU
    TOTAL_MEM=$(free -m | awk 'NR==2{print $2}')
    TOTAL_CPU=$(nproc)
    
    # Allocate resources conservatively
    CONTAINER_MEMORY=$((TOTAL_MEM / 4))  # 25% of total memory
    if [[ $CONTAINER_MEMORY -lt 3072 ]]; then
        CONTAINER_MEMORY=3072  # Minimum for frontend builds
    fi
    if [[ $CONTAINER_MEMORY -gt 8192 ]]; then
        CONTAINER_MEMORY=8192  # Maximum reasonable allocation
    fi
    
    CONTAINER_CORES=$((TOTAL_CPU / 2))
    if [[ $CONTAINER_CORES -lt 2 ]]; then
        CONTAINER_CORES=2
    fi
    if [[ $CONTAINER_CORES -gt 4 ]]; then
        CONTAINER_CORES=4
    fi
    
    CONTAINER_SWAP=$((CONTAINER_MEMORY / 3))
    
    success "Environment detected:"
    echo "  Storage: $AVAILABLE_STORAGE"
    echo "  Network: $NETWORK_BRIDGE"
    echo "  Container ID: $CONTAINER_ID"
    echo "  Memory: ${CONTAINER_MEMORY}MB"
    echo "  CPU Cores: $CONTAINER_CORES"
    echo "  Swap: ${CONTAINER_SWAP}MB"
}

# Download Ubuntu template if needed
ensure_template() {
    log "Checking Ubuntu template..."
    
    local template_name="ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
    local template_path="/var/lib/vz/template/cache/$template_name"
    
    if [[ ! -f "$template_path" ]]; then
        log "Downloading Ubuntu 22.04 template..."
        pveam update
        pveam download local $template_name
    fi
    
    success "Ubuntu template ready"
}

# Create and configure container
create_container() {
    log "Creating MoxNas container..."
    
    # Create container
    pct create $CONTAINER_ID \
        /var/lib/vz/template/cache/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
        --hostname moxnas \
        --memory $CONTAINER_MEMORY \
        --swap $CONTAINER_SWAP \
        --cores $CONTAINER_CORES \
        --rootfs $AVAILABLE_STORAGE:32 \
        --net0 name=eth0,bridge=$NETWORK_BRIDGE,ip=dhcp \
        --features nesting=1,keyctl=1 \
        --unprivileged 1 \
        --start 1
    
    success "Container $CONTAINER_ID created"
    
    # Wait for container to be ready
    log "Waiting for container to be ready..."
    sleep 10
    
    # Get container IP
    local container_ip=""
    for i in {1..30}; do
        container_ip=$(pct exec $CONTAINER_ID -- hostname -I 2>/dev/null | awk '{print $1}' | tr -d '\n' || true)
        if [[ $container_ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            break
        fi
        sleep 2
    done
    
    if [[ ! $container_ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        error "Could not get container IP address"
        exit 1
    fi
    
    CONTAINER_IP=$container_ip
    success "Container IP: $CONTAINER_IP"
}

# Install MoxNas in container
install_moxnas() {
    log "Installing MoxNas in container..."
    
    # Update system
    pct exec $CONTAINER_ID -- apt-get update
    pct exec $CONTAINER_ID -- apt-get upgrade -y
    
    # Install required packages
    pct exec $CONTAINER_ID -- apt-get install -y \
        curl wget git python3 python3-pip python3-venv \
        nodejs npm nginx postgresql postgresql-contrib \
        vsftpd samba nfs-kernel-server openssh-server \
        systemd supervisor htop nano
    
    # Clone MoxNas repository
    pct exec $CONTAINER_ID -- git clone https://github.com/your-repo/MoxNas.git /opt/moxnas
    
    # Set up Python virtual environment
    pct exec $CONTAINER_ID -- python3 -m venv /opt/moxnas/venv
    pct exec $CONTAINER_ID -- /opt/moxnas/venv/bin/pip install --upgrade pip
    pct exec $CONTAINER_ID -- /opt/moxnas/venv/bin/pip install -r /opt/moxnas/backend/requirements.txt
    
    # Build frontend with memory optimization
    pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/frontend && npm ci --production=false"
    pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/frontend && NODE_OPTIONS='--max-old-space-size=2048' npm run build"
    
    # Set up database
    pct exec $CONTAINER_ID -- sudo -u postgres createdb moxnas_db
    pct exec $CONTAINER_ID -- sudo -u postgres psql -c "CREATE USER moxnas_user WITH PASSWORD 'moxnas_pass';"
    pct exec $CONTAINER_ID -- sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE moxnas_db TO moxnas_user;"
    
    # Configure Django
    pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/backend && /opt/moxnas/venv/bin/python manage.py migrate"
    pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/backend && echo \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@moxnas.local', 'admin123')\" | /opt/moxnas/venv/bin/python manage.py shell"
    
    # Create environment file
    cat > /tmp/moxnas_env << EOF
PROXMOX_HOST=127.0.0.1
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your_password
PROXMOX_PORT=8006
DATABASE_URL=postgresql://moxnas_user:moxnas_pass@localhost/moxnas_db
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=$CONTAINER_IP,localhost,127.0.0.1
EOF
    
    pct push $CONTAINER_ID /tmp/moxnas_env /opt/moxnas/.env
    rm /tmp/moxnas_env
    
    success "MoxNas installed successfully"
}

# Configure services
configure_services() {
    log "Configuring system services..."
    
    # Create systemd service
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
ExecReload=/bin/kill -HUP $MAINPID
PIDFile=/var/run/moxnas.pid
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    pct push $CONTAINER_ID /tmp/moxnas.service /etc/systemd/system/moxnas.service
    rm /tmp/moxnas.service
    
    # Create startup script
    cat > /tmp/start_service.sh << 'EOF'
#!/bin/bash
cd /opt/moxnas/backend
source /opt/moxnas/.env
/opt/moxnas/venv/bin/python manage.py migrate --noinput
/opt/moxnas/venv/bin/python manage.py collectstatic --noinput
systemctl start moxnas
EOF
    
    pct push $CONTAINER_ID /tmp/start_service.sh /opt/moxnas/start_service.sh
    rm /tmp/start_service.sh
    pct exec $CONTAINER_ID -- chmod +x /opt/moxnas/start_service.sh
    
    # Enable and start services
    pct exec $CONTAINER_ID -- systemctl daemon-reload
    pct exec $CONTAINER_ID -- systemctl enable moxnas
    pct exec $CONTAINER_ID -- systemctl enable postgresql
    pct exec $CONTAINER_ID -- systemctl enable ssh
    pct exec $CONTAINER_ID -- systemctl enable vsftpd
    pct exec $CONTAINER_ID -- systemctl enable smbd
    pct exec $CONTAINER_ID -- systemctl enable nfs-kernel-server
    
    # Start MoxNas
    pct exec $CONTAINER_ID -- /opt/moxnas/start_service.sh
    
    success "Services configured and started"
    
    # Wait for service to be ready
    log "Waiting for MoxNas to be ready..."
    for i in {1..30}; do
        if curl -s --connect-timeout 5 http://$CONTAINER_IP:8000 >/dev/null; then
            break
        fi
        sleep 2
    done
}

# Run final tests
run_tests() {
    log "Running final tests..."
    
    local tests_passed=0
    local total_tests=5
    
    # Test web interface
    if curl -s --connect-timeout 10 http://$CONTAINER_IP:8000 >/dev/null; then
        success "✓ Web interface accessible"
        ((tests_passed++))
    else
        error "✗ Web interface not accessible"
    fi
    
    # Test API endpoints
    if curl -s --connect-timeout 5 http://$CONTAINER_IP:8000/api/proxmox/dashboard/ | grep -q "containers\|error"; then
        success "✓ API endpoints responding"
        ((tests_passed++))
    else
        error "✗ API endpoints not responding"
    fi
    
    # Test MoxNas service
    if pct exec $CONTAINER_ID -- systemctl is-active moxnas >/dev/null 2>&1; then
        success "✓ MoxNas service running"
        ((tests_passed++))
    else
        error "✗ MoxNas service not running"
    fi
    
    # Test database
    if pct exec $CONTAINER_ID -- sudo -u postgres psql -d moxnas_db -c "SELECT 1;" >/dev/null 2>&1; then
        success "✓ Database accessible"
        ((tests_passed++))
    else
        error "✗ Database not accessible"
    fi
    
    # Test NAS services
    local nas_services=0
    if pct exec $CONTAINER_ID -- systemctl is-enabled ssh >/dev/null 2>&1; then ((nas_services++)); fi
    if pct exec $CONTAINER_ID -- systemctl is-enabled vsftpd >/dev/null 2>&1; then ((nas_services++)); fi
    if pct exec $CONTAINER_ID -- systemctl is-enabled smbd >/dev/null 2>&1; then ((nas_services++)); fi
    if pct exec $CONTAINER_ID -- systemctl is-enabled nfs-kernel-server >/dev/null 2>&1; then ((nas_services++)); fi
    
    if [[ $nas_services -ge 3 ]]; then
        success "✓ NAS services configured ($nas_services/4)"
        ((tests_passed++))
    else
        error "✗ NAS services not properly configured ($nas_services/4)"
    fi
    
    echo
    echo "=================================="
    if [[ $tests_passed -eq $total_tests ]]; then
        success "All tests passed! ($tests_passed/$total_tests)"
        echo -e "${GREEN}MoxNas is ready to use!${NC}"
    else
        warning "Some tests failed ($tests_passed/$total_tests)"
        echo -e "${YELLOW}MoxNas may need additional configuration${NC}"
    fi
}

# Main installation process
main() {
    echo "=================================="
    echo "MoxNas One-Click Installation"
    echo "Auto-detecting Alex's Environment"
    echo "=================================="
    echo
    
    # Check prerequisites
    check_proxmox
    
    # Auto-detect environment
    detect_environment
    
    echo
    read -p "Continue with installation? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log "Installation cancelled"
        exit 0
    fi
    
    # Installation steps
    ensure_template
    create_container
    install_moxnas
    configure_services
    run_tests
    
    echo
    echo "=================================="
    success "MoxNas Installation Complete!"
    echo "=================================="
    echo -e "${BLUE}Container ID:${NC} $CONTAINER_ID"
    echo -e "${BLUE}Container IP:${NC} $CONTAINER_IP"
    echo -e "${BLUE}Web Interface:${NC} http://$CONTAINER_IP:8000"
    echo -e "${BLUE}Admin Panel:${NC} http://$CONTAINER_IP:8000/admin"
    echo -e "${BLUE}Login:${NC} admin / admin123"
    echo
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Access the web interface at http://$CONTAINER_IP:8000"
    echo "2. Configure Proxmox credentials in Settings"
    echo "3. Set up your NAS shares and users"
    echo
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo "  pct exec $CONTAINER_ID -- systemctl status moxnas"
    echo "  pct exec $CONTAINER_ID -- journalctl -u moxnas -f"
    echo "  pct exec $CONTAINER_ID -- /opt/moxnas/start_service.sh"
    echo "=================================="
}

# Run main function
main "$@"