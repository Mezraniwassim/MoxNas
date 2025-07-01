#!/bin/bash
#
# MoxNAS One-Line Installer for Proxmox LXC
# Usage: curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/install_moxnas.sh | bash
# Or with custom container ID: curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/install_moxnas.sh | bash -s 201
#

set -e

# Configuration
CONTAINER_ID=${1:-200}
CONTAINER_HOSTNAME="moxnas"
CONTAINER_PASSWORD="moxnas123"
TEMPLATE="ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
TEMPLATE_SIMPLE="ubuntu-22.04-standard"
DISK_SIZE="8G"
MEMORY="2048"
CORES="2"
REPO_URL="https://github.com/Mezraniwassim/MoxNas.git"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running on Proxmox
check_proxmox() {
    if ! command -v pct &> /dev/null; then
        log_error "This script must be run on a Proxmox VE host"
        exit 1
    fi
    log_success "Running on Proxmox VE"
}

# Check if container ID already exists
check_container() {
    if pct status "$CONTAINER_ID" &> /dev/null; then
        log_warning "Container $CONTAINER_ID already exists. Stopping and removing..."
        pct stop "$CONTAINER_ID" 2>/dev/null || true
        pct destroy "$CONTAINER_ID" 2>/dev/null || true
    fi
}

# Detect available storage and check configuration
detect_storage() {
    log_info "Detecting Proxmox storage configuration..."
    
    # Show current storage status for debugging
    log_info "Available storage:"
    pvesm status
    
    # Find storage that supports containers/VMs
    STORAGE_NAME=""
    
    # Check each storage and verify it supports containers
    while IFS= read -r line; do
        storage_name=$(echo "$line" | awk '{print $1}')
        storage_type=$(echo "$line" | awk '{print $2}')
        storage_status=$(echo "$line" | awk '{print $3}')
        
        # Skip header and inactive storage
        if [[ "$storage_name" == "Name" ]] || [[ "$storage_status" != "active" ]]; then
            continue
        fi
        
        # Check if this storage supports containers
        if pvesm status -storage "$storage_name" 2>/dev/null | grep -q "content.*vztmpl\|content.*rootdir\|content.*images"; then
            STORAGE_NAME="$storage_name"
            log_info "Found suitable storage: $storage_name (type: $storage_type)"
            break
        fi
    done < <(pvesm status)
    
    # If no suitable storage found, try common names
    if [ -z "$STORAGE_NAME" ]; then
        for storage in local-lvm local local-zfs pve-local; do
            if pvesm status | grep -q "^$storage.*active"; then
                STORAGE_NAME="$storage"
                log_info "Using fallback storage: $storage"
                break
            fi
        done
    fi
    
    # Last resort: use first active storage
    if [ -z "$STORAGE_NAME" ]; then
        STORAGE_NAME=$(pvesm status | awk 'NR>1 && $3=="active" {print $1}' | head -1)
        if [ -n "$STORAGE_NAME" ]; then
            log_warning "Using first available storage: $STORAGE_NAME"
        fi
    fi
    
    if [ -z "$STORAGE_NAME" ]; then
        log_error "No active storage found"
        log_error "Please check your Proxmox storage configuration"
        exit 1
    fi
    
    log_success "Selected storage: $STORAGE_NAME"
    
    # Verify storage can be used for containers
    log_info "Verifying storage supports containers..."
    if ! pvesm status -storage "$STORAGE_NAME" >/dev/null 2>&1; then
        log_error "Storage $STORAGE_NAME is not accessible"
        exit 1
    fi
    
    log_success "Storage verification complete"
}

# Download Ubuntu template if not exists
download_template() {
    log_info "Checking Ubuntu template..."
    
    # Check if template exists (try both full name and simple name)
    if ! pveam list local | grep -q "$TEMPLATE_SIMPLE"; then
        log_info "Downloading Ubuntu 22.04 template..."
        if ! pveam download local "$TEMPLATE"; then
            # Try alternative template names
            log_info "Trying alternative template..."
            pveam update
            pveam available | grep ubuntu-22.04 | head -1 | awk '{print $2}' | xargs pveam download local
        fi
    fi
    
    # Update the template name to what's actually available (filename only, not full path)
    TEMPLATE_FULL=$(pveam list local | grep ubuntu-22.04 | head -1 | awk '{print $1}')
    TEMPLATE=$(echo "$TEMPLATE_FULL" | sed 's/.*://')
    
    if [ -z "$TEMPLATE" ]; then
        log_error "Could not find Ubuntu 22.04 template"
        exit 1
    fi
    
    log_success "Ubuntu template available: $TEMPLATE"
}

# Create LXC container
create_container() {
    log_info "Creating LXC container $CONTAINER_ID..."
    
    # Show the command that will be executed
    log_info "Executing: pct create $CONTAINER_ID local:vztmpl/$TEMPLATE --rootfs $STORAGE_NAME:$DISK_SIZE"
    
    # Create container with error handling
    if ! pct create "$CONTAINER_ID" \
        local:vztmpl/"$TEMPLATE" \
        --hostname "$CONTAINER_HOSTNAME" \
        --password "$CONTAINER_PASSWORD" \
        --cores "$CORES" \
        --memory "$MEMORY" \
        --rootfs "$STORAGE_NAME":"$DISK_SIZE" \
        --net0 name=eth0,bridge=vmbr0,ip=dhcp \
        --features nesting=1 \
        --unprivileged 0 \
        --onboot 1 \
        --start 1; then
        
        log_error "Container creation failed. Debugging information:"
        log_error "Storage: $STORAGE_NAME"
        log_error "Template: $TEMPLATE" 
        log_error "Disk size: $DISK_SIZE"
        
        log_info "Manual creation command:"
        log_info "pct create $CONTAINER_ID local:vztmpl/$TEMPLATE \\"
        log_info "  --hostname $CONTAINER_HOSTNAME \\"
        log_info "  --password $CONTAINER_PASSWORD \\"
        log_info "  --cores $CORES \\"
        log_info "  --memory $MEMORY \\"
        log_info "  --rootfs $STORAGE_NAME:$DISK_SIZE \\"
        log_info "  --net0 name=eth0,bridge=vmbr0,ip=dhcp \\"
        log_info "  --features nesting=1 \\"
        log_info "  --unprivileged 0 \\"
        log_info "  --start 1"
        
        log_error "Please check your Proxmox storage configuration:"
        log_error "1. Run: pvesm status"
        log_error "2. Verify storage supports containers"
        log_error "3. Check available space"
        
        exit 1
    fi
        
    log_success "Container $CONTAINER_ID created and started"
}

# Wait for container to be ready
wait_container() {
    log_info "Waiting for container to be ready..."
    sleep 15
    
    # Wait for network
    timeout=60
    while [ $timeout -gt 0 ]; do
        if pct exec "$CONTAINER_ID" -- ping -c 1 8.8.8.8 &> /dev/null; then
            break
        fi
        sleep 2
        ((timeout--))
    done
    
    if [ $timeout -eq 0 ]; then
        log_error "Container network not ready"
        exit 1
    fi
    
    log_success "Container is ready"
}

# Install MoxNAS in container
install_moxnas() {
    log_info "Installing MoxNAS in container..."
    
    # Update system and install dependencies
    pct exec "$CONTAINER_ID" -- bash -c "
        export DEBIAN_FRONTEND=noninteractive
        apt-get update
        apt-get upgrade -y
        
        # Install system dependencies
        apt-get install -y \
            python3 \
            python3-pip \
            python3-venv \
            git \
            curl \
            wget \
            nodejs \
            npm \
            systemd \
            sudo \
            build-essential
    "
    
    # Install NAS services
    pct exec "$CONTAINER_ID" -- bash -c "
        export DEBIAN_FRONTEND=noninteractive
        apt-get install -y \
            samba \
            nfs-kernel-server \
            vsftpd \
            openssh-server \
            snmpd \
            tgt \
            open-iscsi
    "
    
    # Clone and setup MoxNAS
    pct exec "$CONTAINER_ID" -- bash -c "
        cd /opt
        git clone $REPO_URL moxnas
        cd moxnas
        
        # Create Python virtual environment
        python3 -m venv venv
        source venv/bin/activate
        
        # Install Python dependencies
        pip install --upgrade pip
        pip install -r requirements.txt
        pip install gunicorn
        
        # Install Node.js dependencies and build frontend
        cd frontend
        npm install
        npm run build
        cd ..
        
        # Create .env file
        cat > .env << 'EOF'
SECRET_KEY=moxnas-secret-key-\$(openssl rand -hex 32)
DEBUG=False
ALLOWED_HOSTS=*
MOXNAS_STORAGE_PATH=/mnt/storage
MOXNAS_CONFIG_PATH=/etc/moxnas
MOXNAS_LOG_PATH=/var/log/moxnas
EOF
        
        # Create directories
        mkdir -p /mnt/storage /etc/moxnas /var/log/moxnas
        chown -R root:root /opt/moxnas
        chmod +x start_moxnas.py
        
        # Run initial Django setup
        source venv/bin/activate
        cd backend
        python manage.py migrate
        python manage.py collectstatic --noinput
        cd ..
    "
    
    log_success "MoxNAS application installed"
}

# Setup systemd service
setup_service() {
    log_info "Setting up MoxNAS systemd service..."
    
    pct exec "$CONTAINER_ID" -- bash -c "
        cat > /etc/systemd/system/moxnas.service << 'EOF'
[Unit]
Description=MoxNAS Web Interface
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/moxnas
Environment=PATH=/opt/moxnas/venv/bin
ExecStart=/opt/moxnas/venv/bin/python /opt/moxnas/start_moxnas.py --production
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        systemctl daemon-reload
        systemctl enable moxnas
    "
    
    log_success "MoxNAS service configured"
}

# Configure NAS services
configure_services() {
    log_info "Configuring NAS services..."
    
    # Configure Samba
    pct exec "$CONTAINER_ID" -- bash -c "
        cp /etc/samba/smb.conf /etc/samba/smb.conf.backup
        cat > /etc/samba/smb.conf << 'EOF'
[global]
    workgroup = WORKGROUP
    server string = MoxNAS
    security = user
    map to guest = Bad User
    dns proxy = no
    
[moxnas-share]
    path = /mnt/storage
    browseable = yes
    writable = yes
    guest ok = yes
    read only = no
    create mask = 0755
EOF
        systemctl enable smbd nmbd
    "
    
    # Configure NFS
    pct exec "$CONTAINER_ID" -- bash -c "
        echo '/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)' > /etc/exports
        systemctl enable nfs-kernel-server
    "
    
    # Configure FTP
    pct exec "$CONTAINER_ID" -- bash -c "
        cp /etc/vsftpd.conf /etc/vsftpd.conf.backup
        cat >> /etc/vsftpd.conf << 'EOF'

# MoxNAS FTP Configuration
anonymous_enable=YES
local_enable=YES
write_enable=YES
anon_upload_enable=YES
anon_mkdir_write_enable=YES
anon_root=/mnt/storage
pasv_enable=YES
pasv_min_port=40000
pasv_max_port=50000
EOF
        systemctl enable vsftpd
    "
    
    # Configure SSH
    pct exec "$CONTAINER_ID" -- bash -c "
        sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
        systemctl enable ssh
    "
    
    # Configure SNMP
    pct exec "$CONTAINER_ID" -- bash -c "
        systemctl enable snmpd
    "
    
    # Configure iSCSI
    pct exec "$CONTAINER_ID" -- bash -c "
        systemctl enable tgt
    "
    
    log_success "NAS services configured"
}

# Start all services
start_services() {
    log_info "Starting all services..."
    
    pct exec "$CONTAINER_ID" -- bash -c "
        # Start NAS services
        systemctl start ssh
        systemctl start smbd
        systemctl start nmbd
        systemctl start nfs-kernel-server
        systemctl start vsftpd
        systemctl start snmpd
        systemctl start tgt
        
        # Start MoxNAS
        systemctl start moxnas
    "
    
    log_success "All services started"
}

# Get container information
show_info() {
    log_info "Getting container information..."
    
    CONTAINER_IP=$(pct exec "$CONTAINER_ID" -- hostname -I | awk '{print $1}')
    
    echo ""
    echo "=========================================="
    echo "       MoxNAS Installation Complete!      "
    echo "=========================================="
    echo ""
    echo "Container Details:"
    echo "  ID: \$CONTAINER_ID"
    echo "  Hostname: \$CONTAINER_HOSTNAME"
    echo "  IP Address: \$CONTAINER_IP"
    echo "  Root Password: \$CONTAINER_PASSWORD"
    echo ""
    echo "Access MoxNAS:"
    echo "  Web Interface: http://\$CONTAINER_IP:8000"
    echo "  Admin User: admin"
    echo "  Admin Password: moxnas123"
    echo ""
    echo "NAS Services:"
    echo "  SMB/CIFS: //\$CONTAINER_IP/moxnas-share"
    echo "  NFS: \$CONTAINER_IP:/mnt/storage"
    echo "  FTP: ftp://\$CONTAINER_IP"
    echo "  SSH: ssh root@\$CONTAINER_IP"
    echo ""
    echo "Container Management:"
    echo "  Start: pct start \$CONTAINER_ID"
    echo "  Stop: pct stop \$CONTAINER_ID"
    echo "  Shell: pct enter \$CONTAINER_ID"
    echo "  Logs: pct exec \$CONTAINER_ID -- journalctl -u moxnas -f"
    echo ""
    echo "Storage:"
    echo "  Add storage: pct set \$CONTAINER_ID -mp0 /host/path,mp=/mnt/storage"
    echo "  Then restart: pct restart \$CONTAINER_ID"
    echo ""
    log_success "Installation completed successfully!"
}

# Main installation function
main() {
    echo "=========================================="
    echo "       MoxNAS LXC Container Installer     "     
    echo "=========================================="
    echo ""
    
    check_proxmox
    check_container
    detect_storage
    download_template
    create_container
    wait_container
    install_moxnas
    setup_service
    configure_services
    start_services
    show_info
}

# Run main function
main "\$@"