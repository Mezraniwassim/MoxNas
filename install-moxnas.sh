#!/bin/bash

# MoxNas One-Command Installation 
# Usage: curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas.sh | bash

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[MOXNAS]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Check Proxmox
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

# Auto-detect environment
detect_environment() {
    log "Auto-detecting Proxmox environment..."
    
    # Force use local-lvm for containers (most common)
    AVAILABLE_STORAGE="local-lvm"
    
    # Verify it exists and is active
    if ! pvesm status | grep -q "^local-lvm.*active"; then
        # Fallback to any non-local storage
        AVAILABLE_STORAGE=$(pvesm status | awk 'NR>1 && $3=="active" && $1!="local" {print $1}' | head -1)
        if [[ -z "$AVAILABLE_STORAGE" ]]; then
            error "No suitable storage found. Available storage:"
            pvesm status
            exit 1
        fi
    fi
    
    NETWORK_BRIDGE=$(ip link show type bridge | grep -o "vmbr[0-9]*" | head -1)
    [[ -z "$NETWORK_BRIDGE" ]] && NETWORK_BRIDGE="vmbr0"
    
    # Find next available container ID
    CONTAINER_ID=200
    while pct status $CONTAINER_ID >/dev/null 2>&1; do
        ((CONTAINER_ID++))
    done
    
    # Resource allocation
    TOTAL_MEM=$(free -m | awk 'NR==2{print $2}')
    CONTAINER_MEMORY=$((TOTAL_MEM / 4))
    [[ $CONTAINER_MEMORY -lt 3072 ]] && CONTAINER_MEMORY=3072
    [[ $CONTAINER_MEMORY -gt 8192 ]] && CONTAINER_MEMORY=8192
    
    CONTAINER_CORES=$(($(nproc) / 2))
    [[ $CONTAINER_CORES -lt 2 ]] && CONTAINER_CORES=2
    [[ $CONTAINER_CORES -gt 4 ]] && CONTAINER_CORES=4
    
    CONTAINER_SWAP=$((CONTAINER_MEMORY / 3))
    
    success "Environment configured:"
    echo "  Storage: $AVAILABLE_STORAGE"
    echo "  Network: $NETWORK_BRIDGE"
    echo "  Container ID: $CONTAINER_ID"
    echo "  Memory: ${CONTAINER_MEMORY}MB"
    echo "  CPU Cores: $CONTAINER_CORES"
}

# Ensure Ubuntu template
ensure_template() {
    log "Ensuring Ubuntu template..."
    if [[ ! -f "/var/lib/vz/template/cache/ubuntu-22.04-standard_22.04-1_amd64.tar.zst" ]]; then
        log "Downloading Ubuntu template..."
        pveam update
        pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
    fi
    success "Ubuntu template ready"
}

# Create container
create_container() {
    log "Creating container $CONTAINER_ID..."
    
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
    
    success "Container created and started"
    
    # Wait and get IP
    log "Waiting for network..."
    sleep 15
    
    for i in {1..30}; do
        CONTAINER_IP=$(pct exec $CONTAINER_ID -- hostname -I 2>/dev/null | awk '{print $1}' | tr -d '\n' || true)
        [[ $CONTAINER_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && break
        sleep 3
    done
    
    [[ ! $CONTAINER_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && { error "No IP address"; exit 1; }
    success "Container IP: $CONTAINER_IP"
}

# Install MoxNas
install_moxnas() {
    log "Installing MoxNas..."
    
    # Update system
    pct exec $CONTAINER_ID -- apt-get update
    pct exec $CONTAINER_ID -- apt-get upgrade -y
    
    # Install packages
    pct exec $CONTAINER_ID -- apt-get install -y \
        curl wget git python3 python3-pip python3-venv \
        nodejs npm nginx postgresql postgresql-contrib \
        vsftpd samba nfs-kernel-server openssh-server \
        systemd supervisor
    
    # Clone repo
    pct exec $CONTAINER_ID -- git clone https://github.com/Mezraniwassim/MoxNas.git /opt/moxnas
    
    # Python setup
    pct exec $CONTAINER_ID -- python3 -m venv /opt/moxnas/venv
    pct exec $CONTAINER_ID -- /opt/moxnas/venv/bin/pip install --upgrade pip
    pct exec $CONTAINER_ID -- /opt/moxnas/venv/bin/pip install -r /opt/moxnas/backend/requirements.txt
    
    # Build frontend
    log "Building frontend..."
    pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/frontend && npm ci"
    pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/frontend && NODE_OPTIONS='--max-old-space-size=2048' npm run build"
    
    # Database setup
    pct exec $CONTAINER_ID -- sudo -u postgres createdb moxnas_db
    pct exec $CONTAINER_ID -- sudo -u postgres psql -c "CREATE USER moxnas_user WITH PASSWORD 'moxnas_pass';"
    pct exec $CONTAINER_ID -- sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE moxnas_db TO moxnas_user;"
    
    # Django setup
    pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/backend && /opt/moxnas/venv/bin/python manage.py migrate"
    pct exec $CONTAINER_ID -- bash -c "cd /opt/moxnas/backend && echo \"from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@moxnas.local', 'admin123')\" | /opt/moxnas/venv/bin/python manage.py shell"
    
    # Environment file
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
    
    success "MoxNas installed"
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

# Main function
main() {
    echo "=================================="
    echo "🚀 MoxNas Installation"
    echo "=================================="
    echo
    
    check_proxmox
    detect_environment
    echo
    
    log "Starting installation..."
    ensure_template
    create_container
    install_moxnas
    configure_services
    test_installation
    
    echo
    echo "=================================="
    success "🎉 Installation Complete!"
    echo "=================================="
    echo -e "${BLUE}Container ID:${NC} $CONTAINER_ID"
    echo -e "${BLUE}Web Interface:${NC} http://$CONTAINER_IP:8000"
    echo -e "${BLUE}Login:${NC} admin / admin123"
    echo "=================================="
}

main "$@"