#!/bin/bash
#
# MoxNAS One-Line Installer for Proxmox LXC
# 
# INSTALLATION COMMANDS:
# Default installation:  curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install_moxnas.sh | bash
# Custom container ID:   curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install_moxnas.sh | bash -s 201
# Skip network check:    curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install_moxnas.sh | bash -s 200 skip
# Troubleshooting:       curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/manual_install_helper.sh | bash
# Storage debugging:     curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/debug_proxmox_storage.sh | bash
#

set -e

# Configuration
CONTAINER_ID=${1:-200}
SKIP_NETWORK_CHECK=${2:-false}
CONTAINER_HOSTNAME="moxnas"
CONTAINER_PASSWORD="moxnas123"
TEMPLATE="ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
TEMPLATE_SIMPLE="ubuntu-22.04-standard"
DISK_SIZE="8"
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

# Check Node.js version and install if needed
check_nodejs_version() {
    pct exec "$CONTAINER_ID" -- bash -c "
        # Check if Node.js is installed and get version
        if command -v node >/dev/null 2>&1; then
            NODE_VERSION=\$(node --version | cut -d'v' -f2)
            MAJOR_VERSION=\$(echo \$NODE_VERSION | cut -d'.' -f1)
            
            if [ \"\$MAJOR_VERSION\" -lt 14 ]; then
                echo 'Node.js version is too old (\$NODE_VERSION). Installing Node.js 18...'
                
                # Remove conflicting packages first
                apt-get remove -y nodejs nodejs-doc libnode-dev npm || true
                apt-get autoremove -y || true
                
                # Add NodeSource repository and install Node.js 18
                curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
                apt-get install -y nodejs
                
                # Install npm separately if not included
                if ! command -v npm >/dev/null 2>&1; then
                    apt-get install -y npm || curl -L https://www.npmjs.com/install.sh | sh
                fi
            else
                echo 'Node.js version \$NODE_VERSION is compatible'
            fi
        else
            echo 'Node.js not found. Installing Node.js 18...'
            
            # Remove any existing Node.js packages
            apt-get remove -y nodejs nodejs-doc libnode-dev npm || true
            apt-get autoremove -y || true
            
            # Install Node.js 18
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
            apt-get install -y nodejs
            
            # Install npm if not included
            if ! command -v npm >/dev/null 2>&1; then
                apt-get install -y npm || curl -L https://www.npmjs.com/install.sh | sh
            fi
        fi
        
        # Verify installation
        echo 'Final Node.js and npm versions:'
        node --version || echo 'Node.js not available'
        npm --version || echo 'npm not available'
    "
}

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
    
    # Also show LVM information for debugging
    log_info "LVM Volume Groups:"
    vgs 2>/dev/null || log_warning "LVM not available or no volume groups found"
    
    log_info "LVM Logical Volumes:"
    lvs 2>/dev/null || log_warning "LVM not available or no logical volumes found"
    
    # Find storage that supports containers and has enough space
    STORAGE_NAME=""
    
    # Check each storage and verify it supports containers
    while IFS= read -r line; do
        storage_name=$(echo "$line" | awk '{print $1}')
        storage_type=$(echo "$line" | awk '{print $2}')
        storage_status=$(echo "$line" | awk '{print $3}')
        storage_avail=$(echo "$line" | awk '{print $5}')
        
        # Skip header and inactive storage
        if [[ "$storage_name" == "Name" ]] || [[ "$storage_status" != "active" ]]; then
            continue
        fi
        
        # Check available space (need at least 8GB = 8388608 KB)
        # Note: We'll be more lenient with space check since LVM thin provisioning may show lower available space
        if [[ "$storage_avail" =~ ^[0-9]+$ ]] && [ "$storage_avail" -lt 1048576 ]; then
            log_warning "Storage $storage_name has very low space: ${storage_avail}KB available"
            # Don't skip, just warn - LVM thin pools can expand
        fi
        
        # Prefer LVM-thin first, then other types that support containers
        # Note: 'local' dir storage doesn't support container rootfs, only templates
        if [[ "$storage_type" == "lvmthin" ]]; then
            STORAGE_NAME="$storage_name"
            log_info "Found suitable storage: $storage_name (type: $storage_type, available: ${storage_avail}KB)"
            break
        elif [[ "$storage_type" == "lvm" ]] || [[ "$storage_type" == "zfspool" ]]; then
            # These also support containers, use as backup if no lvmthin found
            if [ -z "$STORAGE_NAME" ]; then
                STORAGE_NAME="$storage_name"
                log_info "Found suitable storage: $storage_name (type: $storage_type, available: ${storage_avail}KB)"
            fi
        fi
    done < <(pvesm status)
    
    # If no LVM-thin or dir found, try any storage that supports containers
    if [ -z "$STORAGE_NAME" ]; then
        while IFS= read -r line; do
            storage_name=$(echo "$line" | awk '{print $1}')
            storage_type=$(echo "$line" | awk '{print $2}')
            storage_status=$(echo "$line" | awk '{print $3}')
            
            # Skip header and inactive storage
            if [[ "$storage_name" == "Name" ]] || [[ "$storage_status" != "active" ]]; then
                continue
            fi
            
            # Check if this storage supports containers by checking content types
            storage_content=$(pvesm status -storage "$storage_name" 2>/dev/null | grep -o "content.*" | head -1)
            if echo "$storage_content" | grep -q "vztmpl\|rootdir\|images"; then
                STORAGE_NAME="$storage_name"
                log_info "Found storage with container support: $storage_name (type: $storage_type)"
                break
            fi
        done < <(pvesm status)
    fi
    
    # If still no suitable storage found, try common names
    if [ -z "$STORAGE_NAME" ]; then
        for storage in local-lvm local local-zfs pve-local; do
            if pvesm status | grep -q "^$storage.*active"; then
                STORAGE_NAME="$storage"
                log_warning "Using fallback storage: $storage"
                break
            fi
        done
    fi
    
    if [ -z "$STORAGE_NAME" ]; then
        log_error "No suitable storage found for containers"
        log_error "Available storage:"
        pvesm status
        log_error ""
        log_error "Please ensure you have storage configured that supports containers."
        log_error "Storage must have 'images' or 'rootdir' content type enabled."
        exit 1
    fi
    
    log_success "Selected storage: $STORAGE_NAME"
    
    # Show storage details for verification
    log_info "Storage details:"
    pvesm status -storage "$STORAGE_NAME" 2>/dev/null || log_warning "Could not get detailed storage info"
    
    log_success "Storage verification complete"
}

# Download Ubuntu template if not exists
download_template() {
    log_info "Checking Ubuntu template..."
    
    # First check what templates are available
    log_info "Available templates:"
    pveam list local | grep ubuntu || true
    
    # Check if any Ubuntu 22.04 template exists
    if ! pveam list local | grep -q "ubuntu-22.04"; then
        log_info "Downloading Ubuntu 22.04 template..."
        pveam update
        
        # Try to download the specific template
        if ! pveam download local "$TEMPLATE"; then
            # Try to find and download any Ubuntu 22.04 template
            log_info "Trying to find available Ubuntu 22.04 templates..."
            AVAILABLE_TEMPLATE=$(pveam available | grep ubuntu-22.04 | head -1 | awk '{print $2}')
            if [ -n "$AVAILABLE_TEMPLATE" ]; then
                log_info "Downloading: $AVAILABLE_TEMPLATE"
                pveam download local "$AVAILABLE_TEMPLATE"
            else
                log_error "No Ubuntu 22.04 template found"
                exit 1
            fi
        fi
    fi
    
    # Get the actual template filename (just the filename, without local:vztmpl/ prefix)
    TEMPLATE_FULL=$(pveam list local | grep ubuntu-22.04 | head -1 | awk '{print $1}')
    TEMPLATE=$(echo "$TEMPLATE_FULL" | sed 's/local:vztmpl\///')
    
    if [ -z "$TEMPLATE" ]; then
        log_error "Could not find Ubuntu 22.04 template after download"
        exit 1
    fi
    
    log_success "Using Ubuntu template: $TEMPLATE"
}

# Create LXC container
create_container() {
    log_info "Creating LXC container $CONTAINER_ID..."
    
    # Show the command that will be executed
    log_info "Template file: $TEMPLATE"
    log_info "Storage: $STORAGE_NAME"
    log_info "Full command: pct create $CONTAINER_ID local:vztmpl/$TEMPLATE --rootfs $STORAGE_NAME:$DISK_SIZE"
    log_info "Note: Using Proxmox syntax $STORAGE_NAME:$DISK_SIZE (means ${DISK_SIZE}GB on $STORAGE_NAME storage)"
    
    # Create container with error handling
    if ! pct create "$CONTAINER_ID" \
        "local:vztmpl/$TEMPLATE" \
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
    
    # Skip network check if requested
    if [ "$SKIP_NETWORK_CHECK" = "true" ] || [ "$SKIP_NETWORK_CHECK" = "skip" ]; then
        log_warning "Skipping network connectivity check as requested"
        log_success "Container startup completed (network check bypassed)"
        return 0
    fi
    
    # Wait for network - Check both IP assignment and basic connectivity
    timeout=60
    network_ready=false
    
    while [ $timeout -gt 0 ]; do
        # Check if container has a valid IP address assigned
        if pct exec "$CONTAINER_ID" -- ip addr show eth0 | grep -q "inet.*scope global" &> /dev/null; then
            # Additional check - try to reach gateway or DNS
            if pct exec "$CONTAINER_ID" -- timeout 5 nslookup google.com &> /dev/null ||
               pct exec "$CONTAINER_ID" -- timeout 5 wget -q --spider http://google.com &> /dev/null ||
               pct exec "$CONTAINER_ID" -- timeout 3 curl -s http://google.com &> /dev/null; then
                network_ready=true
                break
            else
                log_warning "IP assigned but no internet connectivity - continuing anyway"
                # Even without internet, we can continue if IP is assigned
                network_ready=true
                break
            fi
        fi
        sleep 2
        ((timeout--))
    done
    
    if [ "$network_ready" = "false" ]; then
        log_warning "Container network not fully ready - continuing anyway"
        log_warning "Network issues may affect package downloads during installation"
        log_warning "You may need to configure network manually: pct enter $CONTAINER_ID"
    else
        log_success "Container network is ready"
    fi
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
    
    # Check and upgrade Node.js version if needed
    log_info "Checking Node.js version compatibility..."
    check_nodejs_version
    
    # Configure locale to prevent warnings
    log_info "Configuring system locale..."
    pct exec "$CONTAINER_ID" -- bash -c "
        export DEBIAN_FRONTEND=noninteractive
        
        # Install locales package if not present
        apt-get install -y locales
        
        # Generate en_US.UTF-8 locale
        locale-gen en_US.UTF-8
        
        # Set system locale
        update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8
        
        # Export locale for current session
        export LANG=en_US.UTF-8
        export LC_ALL=en_US.UTF-8
    "
    
    # Fix common permission issues
    log_info "Setting up proper permissions and directories..."
    pct exec "$CONTAINER_ID" -- bash -c "
        # Create necessary directories with proper permissions
        mkdir -p /var/lib/snmp /var/log/moxnas /etc/moxnas /mnt/storage
        
        # Fix directory permissions
        chmod 755 /var/lib/snmp /var/log/moxnas /etc/moxnas /mnt/storage
        
        # Ensure proper ownership for service directories
        if id snmp >/dev/null 2>&1; then
            chown snmp:snmp /var/lib/snmp
        fi
        
        # Set proper locale environment for all sessions
        echo 'export LANG=en_US.UTF-8' >> /etc/environment
        echo 'export LC_ALL=en_US.UTF-8' >> /etc/environment
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
        pip install gunicorn psutil



        # Install Node.js dependencies and build frontend - BOTH FRONTEND AND BACKEND MUST WORK
        cd frontend
        
        # Ensure Node.js is properly installed before building
        if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
            echo \"Node.js or npm not found, installing Node.js 18...\"
            cd /opt/moxnas
            
            # Remove conflicting packages
            apt-get remove -y nodejs nodejs-doc libnode-dev npm || true
            apt-get autoremove -y || true
            
            # Install Node.js 18
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
            apt-get install -y nodejs
            
            cd frontend
        fi
        
        # Check Node.js version and upgrade if too old
        NODE_VERSION=\$(node --version | cut -d'v' -f2)
        MAJOR_VERSION=\$(echo \$NODE_VERSION | cut -d'.' -f1)
        
        if [ \"\$MAJOR_VERSION\" -lt 14 ]; then
            echo \"Node.js version \$NODE_VERSION is too old, upgrading to Node.js 18...\"
            cd /opt/moxnas
            
            # Remove old Node.js
            apt-get remove -y nodejs nodejs-doc libnode-dev npm || true
            apt-get autoremove -y || true
            
            # Install Node.js 18
            curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
            apt-get install -y nodejs
            
            cd frontend
            
            # Verify new version
            NODE_VERSION=\$(node --version | cut -d'v' -f2)
            MAJOR_VERSION=\$(echo \$NODE_VERSION | cut -d'.' -f1)
            echo \"Updated to Node.js version \$NODE_VERSION\"
        fi
        
        echo \"Using Node.js version \$NODE_VERSION\"
        
        # Install npm packages with proper error handling
        echo \"Installing npm packages...\"
        npm install --prefer-offline --no-audit --progress=false --legacy-peer-deps || {
            echo \"npm install failed, trying with cache clean...\"
            npm cache clean --force
            npm install --prefer-offline --no-audit --progress=false --legacy-peer-deps || {
                echo \"npm install still failing, trying basic install...\"
                npm install --no-audit --progress=false || {
                    echo \"CRITICAL: npm install failed completely - frontend will not work\"
                    echo \"Manual fix required: pct exec \$CONTAINER_ID -- bash -c 'cd /opt/moxnas/frontend && npm install'\"
                    exit 1
                }
            }
        }
        
        # Set Node.js memory options for limited environments
        export NODE_OPTIONS=\"--max-old-space-size=1024\"
        
        # Build frontend with fallback options
        echo \"Building frontend...\"
        npm run build || {
            echo \"Frontend build failed, trying with reduced memory...\"
            export NODE_OPTIONS=\"--max-old-space-size=512\"
            npm run build || {
                echo \"Frontend build failed again, trying development build...\"
                npm run build:dev || {
                    echo \"CRITICAL: Frontend build failed completely\"
                    echo \"Manual fix required: pct exec \$CONTAINER_ID -- bash -c 'cd /opt/moxnas/frontend && npm run build'\"
                    exit 1
                }
            }
        }
        
        echo \"Frontend build completed successfully\"
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
        
        # Run initial Django setup with virtual environment
        cd backend
        ../venv/bin/python manage.py migrate
        ../venv/bin/python manage.py collectstatic --noinput
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
        
        # Set proper permissions for systemd service file
        chmod 644 /etc/systemd/system/moxnas.service
        chown root:root /etc/systemd/system/moxnas.service
        
        # Reload systemd and enable service
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
        # Fix SNMP directory permissions
        if [ -d /var/lib/snmp ]; then
            chown snmp:snmp /var/lib/snmp
            chmod 755 /var/lib/snmp
        else
            mkdir -p /var/lib/snmp
            chown snmp:snmp /var/lib/snmp
            chmod 755 /var/lib/snmp
        fi
        systemctl enable snmpd
    "
    
    # Configure iSCSI
    pct exec "$CONTAINER_ID" -- bash -c "
        systemctl enable tgt
    "
    
    log_success "NAS services configured"
}

# Fix service configurations and permissions
fix_service_configurations() {
    log_info "Fixing service configurations and permissions..."
    
    pct exec "$CONTAINER_ID" -- bash -c "
        # Fix NFS exports - remove duplicate entries
        if [ -f /etc/exports ]; then
            # Remove duplicate entries for /mnt/storage
            grep -v '^/mnt/storage' /etc/exports > /tmp/exports.tmp || true
            echo '/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)' >> /tmp/exports.tmp
            mv /tmp/exports.tmp /etc/exports
        else
            echo '/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)' > /etc/exports
        fi
        
        # Fix Samba configuration - remove duplicate www share
        if [ -f /etc/samba/smb.conf ]; then
            # Remove the www share section that was causing issues
            sed -i '/\[www\]/,/^$/d' /etc/samba/smb.conf
        fi
        
        # Ensure storage directories have proper permissions
        mkdir -p /mnt/storage
        chmod 755 /mnt/storage
        chown root:root /mnt/storage
        
        # Create MoxNAS config and log directories
        mkdir -p /etc/moxnas /var/log/moxnas
        chmod 755 /etc/moxnas /var/log/moxnas
        
        # Create additional service directories
        mkdir -p /mnt/storage/shares /mnt/storage/ftp_users /var/lib/moxnas
        chmod 755 /mnt/storage/shares /mnt/storage/ftp_users /var/lib/moxnas
        
        # Ensure proper exports file exists
        touch /etc/exports
        chmod 644 /etc/exports
        
        # Fix Django database permissions
        cd /opt/moxnas/backend
        chmod 664 db.sqlite3 2>/dev/null || true
        
        # Install missing Python package
        cd /opt/moxnas
        source venv/bin/activate
        pip install psutil 2>/dev/null || true
        
        # Run Django migrations to ensure database is up to date
        cd backend
        python manage.py migrate --run-syncdb 2>/dev/null || true
        
        # Initialize services using management command
        python manage.py initialize_services 2>/dev/null || true
        
        # Reload NFS exports
        exportfs -ra 2>/dev/null || true
        
        # Restart services to apply new configurations
        systemctl restart smbd nmbd 2>/dev/null || true
        systemctl restart nfs-kernel-server 2>/dev/null || true
    "
    
    log_success "Service configurations fixed"
}

# Verify and fix MoxNAS startup
verify_moxnas_startup() {
    log_info "Verifying MoxNAS startup..."
    
    # Wait a moment for services to start
    sleep 10
    
    # Check if MoxNAS systemd service is running
    if pct exec "$CONTAINER_ID" -- systemctl is-active moxnas &> /dev/null; then
        log_success "MoxNAS systemd service is running"
        return 0
    fi
    
    log_warning "MoxNAS systemd service failed, attempting manual start..."
    
    # Try manual start with gunicorn
    pct exec "$CONTAINER_ID" -- bash -c "
        cd /opt/moxnas
        source venv/bin/activate
        
        # Ensure gunicorn is installed
        pip install gunicorn &> /dev/null || log_warning 'Failed to install gunicorn'
        
        # Run Django migrations and collectstatic with better error handling
        cd backend
        python manage.py migrate || {
            log_warning 'Initial migrations failed, running syncdb...'
            python manage.py migrate --run-syncdb || log_warning 'Migration issues - continuing anyway'
        }
        
        python manage.py collectstatic --noinput || {
            log_warning 'Collectstatic failed, creating minimal static setup...'
            mkdir -p staticfiles
        }
        
        python manage.py initialize_services || {
            log_warning 'Service initialization failed, creating default services...'
            python manage.py shell << 'PYTHON_EOF'
from core.models import ServiceStatus
services = [
    ('smb', 445), ('nfs', 2049), ('ftp', 21), 
    ('ssh', 22), ('snmp', 161), ('iscsi', 3260)
]
for name, port in services:
    ServiceStatus.objects.get_or_create(
        name=name, 
        defaults={'port': port, 'status': 'stopped'}
    )
print('Services initialized')
PYTHON_EOF
        }
        
        # Kill any existing gunicorn processes
        pkill -f gunicorn || true
        sleep 2
        
        # Start gunicorn with better error handling and logging
        gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 60 \
                 --access-logfile /var/log/moxnas/access.log \
                 --error-logfile /var/log/moxnas/error.log \
                 --daemon --preload moxnas.wsgi:application || {
            log_warning 'Gunicorn daemon start failed, trying with simpler config...'
            gunicorn --bind 0.0.0.0:8000 --workers 1 --daemon moxnas.wsgi:application || {
                log_error 'Gunicorn failed to start. Manual start may be needed.'
                return 1
            }
        }
    "
    
    # Wait and check if gunicorn started
    sleep 5
    if pct exec "$CONTAINER_ID" -- ps aux | grep -q "gunicorn.*8000"; then
        log_success "MoxNAS started manually with gunicorn"
        
        # Create a simple startup script for future reboots
        pct exec "$CONTAINER_ID" -- bash -c "
            cat > /usr/local/bin/start-moxnas.sh << 'EOF'
#!/bin/bash
cd /opt/moxnas
source venv/bin/activate
cd backend
gunicorn --bind 0.0.0.0:8000 --workers 3 moxnas.wsgi:application --daemon
EOF
            chmod +x /usr/local/bin/start-moxnas.sh
            
            # Add to rc.local for auto-start
            if ! grep -q 'start-moxnas.sh' /etc/rc.local; then
                sed -i '/^exit 0/i /usr/local/bin/start-moxnas.sh' /etc/rc.local
            fi
        "
        log_info "Created startup script for future container restarts"
        return 0
    fi
    
    log_error "Failed to start MoxNAS manually. Please check logs:"
    log_error "  pct exec $CONTAINER_ID -- journalctl -u moxnas"
    log_error "  pct exec $CONTAINER_ID -- cd /opt/moxnas && source venv/bin/activate && python backend/manage.py runserver 0.0.0.0:8000"
    return 1
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
    echo "Troubleshooting:"
    echo "  Manual start: pct exec \$CONTAINER_ID -- /usr/local/bin/start-moxnas.sh"
    echo "  Check logs: pct exec \$CONTAINER_ID -- journalctl -u moxnas -f"
    echo "  Web test: curl -I http://\$CONTAINER_IP:8000"
    echo ""
    
    # Final verification test
    log_info "Performing final web interface test..."
    if curl -I "http://\$CONTAINER_IP:8000" &> /dev/null; then
        log_success "✅ MoxNAS web interface is accessible!"
        log_success "🌐 Open: http://\$CONTAINER_IP:8000"
        log_success "👤 Login: admin / moxnas123"
    else
        log_warning "⚠️  Web interface test failed. Try manual commands above."
    fi
    
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
    fix_service_configurations
    start_services
    verify_moxnas_startup
    show_info
}

# Run main function
main "\$@"