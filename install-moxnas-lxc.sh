#!/usr/bin/env bash

# MoxNAS LXC Container Creation and Installation Script
# One-line deployment for Proxmox VE
# Usage: bash -c "$(wget -qLO - https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas-lxc.sh)"

set -euo pipefail

# Colors for output
RD="\033[01;31m"
YW="\033[33m"
GN="\033[1;92m"
CL="\033[m"
BFR="\\r\\033[K"
HOLD="-"

# Display functions
function msg_info() {
    local msg="$1"
    echo -ne " ${HOLD} ${YW}${msg}..."
    echo -e "${CL}"
}

function msg_ok() {
    local msg="$1"
    echo -e "${BFR} ✓ ${GN}${msg}${CL}"
}

function msg_error() {
    local msg="$1"
    echo -e "${BFR} ✗ ${RD}${msg}${CL}"
}

# Check if running on Proxmox
if ! command -v pct &> /dev/null; then
    msg_error "This script must be run on a Proxmox VE host"
    exit 1
fi

# Function to detect available storage disks
detect_storage_disks() {
    local disks=()
    msg_info "Detecting available storage disks"
    
    # Get all block devices that are not mounted and not used by the system
    while IFS= read -r disk; do
        # Skip if disk is mounted or is a system disk
        if ! grep -q "^${disk}" /proc/mounts && ! pvdisplay "${disk}" &>/dev/null && ! grep -q "^${disk}" /proc/swaps; then
            # Check if disk has a size > 1GB
            local size=$(lsblk -b -n -o SIZE "${disk}" 2>/dev/null)
            if [[ -n "$size" ]] && [[ $size -gt 1073741824 ]]; then
                disks+=("$disk")
            fi
        fi
    done < <(lsblk -d -n -o NAME | grep -E '^sd[b-z]$|^nvme[0-9]+n[1-9]$|^vd[b-z]$' | sed 's|^|/dev/|')
    
    if [[ ${#disks[@]} -gt 0 ]]; then
        msg_ok "Found ${#disks[@]} available storage disk(s): ${disks[*]}"
        printf '%s\n' "${disks[@]}"
    else
        msg_info "No additional storage disks detected"
    fi
}

# Function to configure disk passthrough
configure_disk_passthrough() {
    local ctid=$1
    shift
    local disks=("$@")
    
    if [[ ${#disks[@]} -eq 0 ]]; then
        msg_info "No disks to configure for passthrough"
        return
    fi
    
    msg_info "Configuring disk passthrough for container $ctid"
    
    for disk in "${disks[@]}"; do
        if [[ -b "$disk" ]]; then
            msg_info "Adding disk $disk to container"
            
            # Get major and minor device numbers
            local major=$(stat -c "%t" "$disk")
            local minor=$(stat -c "%T" "$disk")
            major=$((0x$major))
            minor=$((0x$minor))
            
            # Add device to container configuration
            cat >> /etc/pve/lxc/${ctid}.conf << EOF

# Storage disk: $disk
lxc.cgroup2.devices.allow: b $major:$minor rwm
lxc.mount.entry: $disk $disk none bind,optional,create=file
EOF
            msg_ok "Added $disk to container configuration"
        else
            msg_error "Disk $disk is not a valid block device"
        fi
    done
}

# Configuration variables with defaults
CTID=${CTID:-$(pvesh get /cluster/nextid)}
CT_HOSTNAME=${CT_HOSTNAME:-"moxnas"}
STORAGE=${STORAGE:-"local-lvm"}
TEMPLATE=${TEMPLATE:-"local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"}
PASSWORD=${PASSWORD:-"moxnas1234"}
CORES=${CORES:-4}
MEMORY=${MEMORY:-4096}
DISK_SIZE=${DISK_SIZE:-20}
NETWORK=${NETWORK:-"vmbr0"}
IP_CONFIG=${IP_CONFIG:-"dhcp"}
GITHUB_REPO=${GITHUB_REPO:-"https://github.com/Mezraniwassim/MoxNAS.git"}
BRANCH=${BRANCH:-"master"}

# Storage configuration
STORAGE_DISKS=${STORAGE_DISKS:-""}  # Comma-separated list of disks to pass through (e.g., "/dev/sdb,/dev/sdc")
AUTO_DETECT_DISKS=${AUTO_DETECT_DISKS:-"true"}  # Auto-detect available disks
CREATE_STORAGE_POOL=${CREATE_STORAGE_POOL:-"true"}  # Automatically create storage pool

# Check if template exists
msg_info "Checking Debian template"
TEMPLATE="local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst"
if ! pveam list local 2>/dev/null | grep -q "debian-12-standard_12.7-1_amd64.tar.zst"; then
    msg_info "Downloading Debian 12 template"
    pveam update >/dev/null 2>&1
    pveam download local debian-12-standard_12.7-1_amd64.tar.zst >/dev/null 2>&1
fi
msg_ok "Template ready"

# Handle storage disk configuration
AVAILABLE_DISKS=()
if [[ "$AUTO_DETECT_DISKS" == "true" ]]; then
    mapfile -t AVAILABLE_DISKS < <(detect_storage_disks)
fi

# Parse manually specified disks
if [[ -n "$STORAGE_DISKS" ]]; then
    IFS=',' read -ra MANUAL_DISKS <<< "$STORAGE_DISKS"
    for disk in "${MANUAL_DISKS[@]}"; do
        disk=$(echo "$disk" | xargs)  # Trim whitespace
        if [[ -b "$disk" ]]; then
            AVAILABLE_DISKS+=("$disk")
        else
            msg_error "Specified disk $disk is not a valid block device"
        fi
    done
fi

# Display configuration
echo -e "\n${GN}MoxNAS LXC Container Configuration:${CL}"
echo -e "CT ID: ${YW}${CTID}${CL}"
echo -e "Hostname: ${YW}${CT_HOSTNAME}${CL}"
echo -e "Password: ${YW}${PASSWORD}${CL}"
echo -e "Cores: ${YW}${CORES}${CL}"
echo -e "Memory: ${YW}${MEMORY}MB${CL}"
echo -e "Disk: ${YW}${DISK_SIZE}GB${CL}"
echo -e "Network: ${YW}${IP_CONFIG}${CL}"
if [[ ${#AVAILABLE_DISKS[@]} -gt 0 ]]; then
    echo -e "Storage Disks: ${YW}${AVAILABLE_DISKS[*]}${CL}"
else
    echo -e "Storage Disks: ${YW}None (using container filesystem)${CL}"
fi
echo ""

# Create container
msg_info "Creating LXC container"
pct create ${CTID} ${TEMPLATE} \
    --arch amd64 \
    --cores ${CORES} \
    --hostname ${CT_HOSTNAME} \
    --memory ${MEMORY} \
    --net0 name=eth0,bridge=${NETWORK},ip=${IP_CONFIG} \
    --ostype debian \
    --password ${PASSWORD} \
    --rootfs ${STORAGE}:${DISK_SIZE} \
    --swap 512 \
    --unprivileged 1 \
    --features nesting=1 \
    --startup order=1 \
    --onboot 1

msg_ok "Container created (ID: ${CTID})"

# Configure container for NAS functionality
msg_info "Configuring container for NAS functionality"
cat >> /etc/pve/lxc/${CTID}.conf << EOF

# MoxNAS specific configuration
lxc.apparmor.profile: unconfined
lxc.cap.drop: 
lxc.cgroup.devices.allow: a
lxc.mount.auto: "proc:rw sys:rw"
EOF

# Configure disk passthrough if disks are available
if [[ ${#AVAILABLE_DISKS[@]} -gt 0 ]]; then
    configure_disk_passthrough "${CTID}" "${AVAILABLE_DISKS[@]}"
fi

msg_ok "Container configured"

# Start container
msg_info "Starting container"
pct start ${CTID}

# Wait for container to be ready
sleep 10

# Install MoxNAS inside the container
msg_info "Installing MoxNAS application"
pct exec ${CTID} -- bash -c "$(cat << 'INSTALL_SCRIPT'
#!/bin/bash
set -euo pipefail

# Standard output suppression function
silent() {
    "$@" >/dev/null 2>&1
}

# Color functions for container
function msg_info() { echo -e " ⏳ \e[33m$1...\e[0m"; }
function msg_ok() { echo -e " ✅ \e[32m$1\e[0m"; }

msg_info "Updating system"
silent apt-get update
silent apt-get upgrade -y

msg_info "Configuring locale"
export DEBIAN_FRONTEND=noninteractive
silent apt-get install -y locales
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
silent locale-gen
silent update-locale LANG=en_US.UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

msg_info "Installing dependencies"
silent apt-get install -y \
    curl wget git sudo mc \
    python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib \
    redis-server nginx supervisor \
    mdadm smartmontools \
    nfs-kernel-server samba vsftpd \
    htop iotop build-essential \
    libpq-dev libffi-dev libssl-dev openssl ufw \
    lvm2 parted gdisk dosfstools

msg_info "Setting up PostgreSQL"
systemctl start postgresql
systemctl enable postgresql
POSTGRES_PASSWORD=$(openssl rand -base64 32)
sudo -u postgres LANG=C.UTF-8 LC_ALL=C.UTF-8 psql -c "CREATE DATABASE moxnas;"
sudo -u postgres LANG=C.UTF-8 LC_ALL=C.UTF-8 psql -c "CREATE USER moxnas WITH PASSWORD '$POSTGRES_PASSWORD';"
sudo -u postgres LANG=C.UTF-8 LC_ALL=C.UTF-8 psql -c "GRANT ALL PRIVILEGES ON DATABASE moxnas TO moxnas;"
sudo -u postgres LANG=C.UTF-8 LC_ALL=C.UTF-8 psql -c "ALTER USER moxnas CREATEDB;"

msg_info "Setting up Redis"
REDIS_PASSWORD=$(openssl rand -base64 32)
# Escape special characters for sed
REDIS_PASSWORD_ESCAPED=$(printf '%s\n' "$REDIS_PASSWORD" | sed 's/[[\.*^$()+?{|]/\\&/g')
sed -i "s|# requirepass foobared|requirepass $REDIS_PASSWORD_ESCAPED|" /etc/redis/redis.conf
systemctl restart redis-server
systemctl enable redis-server

msg_info "Setting up MoxNAS directory"
mkdir -p /opt/moxnas

msg_info "Installing MoxNAS application"
cd /opt/moxnas

# Download MoxNAS from GitHub
wget -O moxnas.tar.gz https://github.com/Mezraniwassim/MoxNas/archive/refs/heads/master.tar.gz
tar -xzf moxnas.tar.gz --strip-components=1
rm moxnas.tar.gz

# Create Python virtual environment (as root)
python3 -m venv venv
source venv/bin/activate && pip install --upgrade pip
source venv/bin/activate && pip install gunicorn
source venv/bin/activate && pip install -r requirements.txt

# Create configuration file
cat > /opt/moxnas/.env << EOF
FLASK_ENV=production
SECRET_KEY=$(openssl rand -base64 64)
DATABASE_URL=postgresql://moxnas:$POSTGRES_PASSWORD@localhost/moxnas
REDIS_URL=redis://:$REDIS_PASSWORD@localhost:6379/0
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@localhost:6379/0
MOXNAS_ADMIN_EMAIL=admin@moxnas.local
SESSION_COOKIE_SECURE=true
EOF

chmod 600 /opt/moxnas/.env

msg_info "Setting up storage directories"
mkdir -p /mnt/storage /mnt/backups /var/log/moxnas

# Initialize passed-through storage disks
if ls /dev/sd[b-z] /dev/nvme[0-9]*n[1-9] /dev/vd[b-z] 2>/dev/null | head -1 >/dev/null; then
    msg_info "Initializing storage disks for MoxNAS"
    
    # Create a simple storage detection script
    cat > /opt/moxnas/initialize_storage.py << 'EOF'
#!/usr/bin/env python3
"""Initialize MoxNAS storage disks"""
import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, check=True):
    """Run command safely"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"Error running '{cmd}': {result.stderr}", file=sys.stderr)
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"Exception running '{cmd}': {e}", file=sys.stderr)
        return None

def detect_storage_disks():
    """Detect available storage disks"""
    disks = []
    
    # Check for common disk patterns
    for pattern in ['/dev/sd[b-z]', '/dev/nvme[0-9]*n[1-9]', '/dev/vd[b-z]']:
        output = run_command(f'ls {pattern} 2>/dev/null || true')
        if output:
            disks.extend(output.split('\n'))
    
    # Filter out mounted disks
    available_disks = []
    for disk in disks:
        if disk and Path(disk).exists():
            # Check if disk is mounted
            mount_check = run_command(f'mount | grep "^{disk}"')
            if not mount_check:
                # Get disk size
                size_output = run_command(f'lsblk -b -n -o SIZE {disk}')
                if size_output and int(size_output) > 1073741824:  # > 1GB
                    available_disks.append(disk)
    
    return available_disks

def setup_storage_pool(disks):
    """Set up basic storage configuration"""
    if not disks:
        print("No storage disks available")
        return False
    
    print(f"Setting up storage with disks: {', '.join(disks)}")
    
    # Create a simple LVM setup for multiple disks or direct mount for single disk
    if len(disks) == 1:
        disk = disks[0]
        print(f"Setting up single disk: {disk}")
        
        # Create partition table and partition
        run_command(f'parted -s {disk} mklabel gpt')
        run_command(f'parted -s {disk} mkpart primary 0% 100%')
        
        # Create filesystem
        partition = f"{disk}1"
        run_command(f'mkfs.ext4 -F {partition}')
        
        # Create mount point and mount
        run_command('mkdir -p /mnt/moxnas-storage')
        
        # Add to fstab
        uuid_output = run_command(f'blkid -s UUID -o value {partition}')
        if uuid_output:
            fstab_entry = f"UUID={uuid_output} /mnt/moxnas-storage ext4 defaults 0 2\n"
            with open('/etc/fstab', 'a') as f:
                f.write(fstab_entry)
        
        # Mount the filesystem
        run_command('mount /mnt/moxnas-storage')
        
        # Update storage directory  
        run_command('rm -rf /mnt/storage 2>/dev/null || true')
        run_command('ln -sf /mnt/moxnas-storage /mnt/storage')
        
        print(f"Single disk storage configured: {partition} -> /mnt/storage")
        
    else:
        print(f"Setting up LVM with {len(disks)} disks")
        
        # Create physical volumes
        for disk in disks:
            run_command(f'pvcreate -f {disk}')
        
        # Create volume group
        run_command(f"vgcreate moxnas-vg {' '.join(disks)}")
        
        # Create logical volume (use 90% of space)
        run_command('lvcreate -l 90%FREE -n storage moxnas-vg')
        
        # Create filesystem
        run_command('mkfs.ext4 -F /dev/moxnas-vg/storage')
        
        # Create mount point and mount
        run_command('mkdir -p /mnt/moxnas-storage')
        
        # Add to fstab
        fstab_entry = "/dev/moxnas-vg/storage /mnt/moxnas-storage ext4 defaults 0 2\n"
        with open('/etc/fstab', 'a') as f:
            f.write(fstab_entry)
        
        # Mount the filesystem
        run_command('mount /mnt/moxnas-storage')
        
        # Update storage directory  
        run_command('rm -rf /mnt/storage 2>/dev/null || true')
        run_command('ln -sf /mnt/moxnas-storage /mnt/storage')
        
        print(f"LVM storage configured: /dev/moxnas-vg/storage -> /mnt/storage")
    
    # Set permissions
    run_command('chmod 755 /mnt/storage')
    
    return True

if __name__ == '__main__':
    print("MoxNAS Storage Initialization")
    print("=" * 40)
    
    # Detect available disks
    disks = detect_storage_disks()
    
    if not disks:
        print("No additional storage disks detected.")
        print("MoxNAS will use container filesystem for storage.")
    else:
        print(f"Found {len(disks)} storage disk(s): {', '.join(disks)}")
        
        # Set up storage
        if setup_storage_pool(disks):
            print("Storage initialization completed successfully!")
        else:
            print("Storage initialization failed!")
            sys.exit(1)
EOF
    
    chmod +x /opt/moxnas/initialize_storage.py
    
    # Run storage initialization
    python3 /opt/moxnas/initialize_storage.py
    
    # Update MoxNAS database with detected storage
    bash -c "cd /opt/moxnas && source venv/bin/activate && python -c '
from app import create_app, db
from app.storage.manager import storage_manager
app = create_app(\"production\")
with app.app_context():
    try:
        storage_manager.update_device_database()
        print(\"Storage database updated successfully\")
    except Exception as e:
        print(f\"Warning: Could not update storage database: {e}\")
'"
    
    msg_ok "Storage disks initialized and database updated"
else
    msg_info "No additional storage disks found, using container filesystem"
fi

chmod 755 /mnt/storage /mnt/backups /var/log/moxnas

msg_info "Initializing database"
cd /opt/moxnas
bash -c "source venv/bin/activate && python -c 'from app import create_app, db; app = create_app(\"production\"); app.app_context().push(); db.create_all()'"

# Also run initial storage scan to populate the database
msg_info "Running initial storage device scan"
bash -c "cd /opt/moxnas && source venv/bin/activate && python -c '
from app import create_app, db
from app.storage.manager import storage_manager
app = create_app(\"production\")
with app.app_context():
    try:
        storage_manager.update_device_database()
        print(\"Initial storage device scan completed\")
    except Exception as e:
        print(f\"Note: Initial storage scan will run after first login: {e}\")
'"

# Create admin user with fixed password
ADMIN_PASSWORD="moxnas1234"
bash -c "cd /opt/moxnas && source venv/bin/activate && python -c '
from app import create_app, db
from app.models import User, UserRole
from werkzeug.security import generate_password_hash
import os
app = create_app(\"production\")
with app.app_context():
    admin = User(
        username=\"admin\",
        email=\"admin@moxnas.local\",
        role=UserRole.ADMIN,
        is_active=True,
        password_hash=generate_password_hash(\"'$ADMIN_PASSWORD'\")
    )
    db.session.add(admin)
    db.session.commit()
    print(\"Admin user created successfully\")
'"

# Save admin credentials
echo "Admin Username: admin" > /opt/moxnas/.admin_credentials
echo "Admin Password: $ADMIN_PASSWORD" >> /opt/moxnas/.admin_credentials
chmod 600 /opt/moxnas/.admin_credentials

msg_info "Configuring Nginx"
# Generate self-signed SSL certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/moxnas-selfsigned.key \
    -out /etc/ssl/certs/moxnas-selfsigned.crt \
    -subj "/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas.local"

cat > /etc/nginx/sites-available/moxnas << 'EOF'
server {
    listen 80;
    server_name _;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;
    
    ssl_certificate /etc/ssl/certs/moxnas-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/moxnas-selfsigned.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    client_max_body_size 10G;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_buffering off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /static {
        alias /opt/moxnas/app/static;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
}
EOF

ln -sf /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

msg_info "Configuring systemd services"
# Create MoxNAS systemd service
cat > /etc/systemd/system/moxnas.service << 'EOF'
[Unit]
Description=MoxNAS Web Application
Documentation=https://github.com/Mezraniwassim/MoxNAS
After=network-online.target postgresql.service redis-server.service
Wants=network-online.target
Requires=postgresql.service redis-server.service

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/moxnas
Environment="PATH=/opt/moxnas/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/moxnas"
EnvironmentFile=/opt/moxnas/.env

ExecStart=/opt/moxnas/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 wsgi:app
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID

Restart=always
RestartSec=10
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Security settings for LXC (relaxed for root access)
NoNewPrivileges=no
ProtectSystem=no
ProtectHome=no
ReadWritePaths=/
PrivateTmp=no
PrivateDevices=no
ProtectKernelTunables=no
ProtectKernelModules=no
ProtectControlGroups=no
RestrictRealtime=no
LockPersonality=no

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096
MemoryMax=1G
CPUQuota=100%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=moxnas

[Install]
WantedBy=multi-user.target
EOF

# Create MoxNAS worker service
cat > /etc/systemd/system/moxnas-worker.service << 'EOF'
[Unit]
Description=MoxNAS Background Worker
After=network-online.target postgresql.service redis-server.service moxnas.service
Wants=network-online.target
Requires=postgresql.service redis-server.service

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/moxnas
Environment="PATH=/opt/moxnas/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=/opt/moxnas"
EnvironmentFile=/opt/moxnas/.env

ExecStart=/opt/moxnas/venv/bin/celery -A celery_worker.celery worker --loglevel=info --concurrency=2
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID

Restart=always
RestartSec=10
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

# Security settings (relaxed for root access)
NoNewPrivileges=no
ProtectSystem=no
ProtectHome=no
ReadWritePaths=/
PrivateTmp=no
PrivateDevices=no
ProtectKernelTunables=no
ProtectKernelModules=no

# Resource limits
LimitNOFILE=65536
LimitNPROC=2048
MemoryMax=512M
CPUQuota=50%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=moxnas-worker

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start services
systemctl daemon-reload
systemctl enable moxnas moxnas-worker
systemctl start moxnas moxnas-worker

msg_info "Setting up storage and shares"
mkdir -p /mnt/storage /mnt/backups /srv/ftp
chmod 755 /mnt/storage /mnt/backups /srv/ftp

# NFS configuration
echo "/mnt/storage *(rw,sync,no_subtree_check,no_root_squash)" >> /etc/exports
systemctl enable nfs-kernel-server
systemctl start nfs-kernel-server

# Samba configuration
cp /etc/samba/smb.conf /etc/samba/smb.conf.backup
cat >> /etc/samba/smb.conf << 'EOF'

[moxnas-storage]
    path = /mnt/storage
    browseable = yes
    writable = yes
    guest ok = no
    valid users = root
    create mask = 0755
    directory mask = 0755
    force user = root
    force group = root
EOF

echo -e "$ADMIN_PASSWORD\n$ADMIN_PASSWORD" | smbpasswd -a root
systemctl enable smbd nmbd
systemctl start smbd nmbd

# FTP configuration
cat > /etc/vsftpd.conf << 'EOF'
listen=NO
listen_ipv6=YES
anonymous_enable=NO
local_enable=YES
write_enable=YES
local_umask=022
dirmessage_enable=YES
use_localtime=YES
xferlog_enable=YES
connect_from_port_20=YES
chroot_local_user=YES
allow_writeable_chroot=YES
secure_chroot_dir=/var/run/vsftpd/empty
pam_service_name=vsftpd
rsa_cert_file=/etc/ssl/certs/ssl-cert-snakeoil.pem
rsa_private_key_file=/etc/ssl/private/ssl-cert-snakeoil.key
ssl_enable=YES
pasv_enable=Yes
pasv_min_port=10000
pasv_max_port=10100
user_sub_token=$USER
local_root=/srv/ftp
userlist_enable=YES
userlist_file=/etc/vsftpd.userlist
userlist_deny=NO
EOF

echo "root" > /etc/vsftpd.userlist
systemctl enable vsftpd
systemctl start vsftpd

msg_info "Configuring firewall"
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw allow 139,445/tcp
ufw allow 2049/tcp
ufw allow 21/tcp
ufw allow 10000:10100/tcp

msg_info "Setting up automatic share mounting"
# Get container IP address
SERVER_IP=$(hostname -I | awk '{print $1}')

# Create mount points for testing shares
mkdir -p /mnt/test-smb /mnt/test-nfs /mnt/test-ftp

# Install CIFS utilities for SMB mounting
apt-get install -y cifs-utils

# Create SMB credentials file
cat > /etc/cifs-credentials << EOF
username=root
password=$ADMIN_PASSWORD
domain=
EOF
chmod 600 /etc/cifs-credentials

# Add entries to fstab for automatic mounting
cat >> /etc/fstab << EOF

# MoxNAS Share Mounts (for testing and access)
//$SERVER_IP/moxnas-storage /mnt/test-smb cifs credentials=/etc/cifs-credentials,uid=0,gid=0,iocharset=utf8,file_mode=0755,dir_mode=0755,nofail 0 0
$SERVER_IP:/mnt/storage /mnt/test-nfs nfs defaults,nofail 0 0
EOF

# Wait for services to be fully ready
sleep 5

# Mount the shares
msg_info "Mounting network shares for testing"
mount /mnt/test-smb 2>/dev/null || echo "SMB mount will be available after reboot"
mount /mnt/test-nfs 2>/dev/null || echo "NFS mount will be available after reboot"

# Create test files to verify shares work
if mountpoint -q /mnt/test-smb; then
    echo "SMB share mounted successfully" > /mnt/test-smb/smb-test.txt
    msg_ok "SMB share mounted and tested"
else
    msg_info "SMB share will be mounted on next boot"
fi

if mountpoint -q /mnt/test-nfs; then
    echo "NFS share mounted successfully" > /mnt/test-nfs/nfs-test.txt
    msg_ok "NFS share mounted and tested"
else
    msg_info "NFS share will be mounted on next boot"
fi

# Create a script for manual mounting and testing
cat > /opt/moxnas/mount-shares.sh << 'EOF'
#!/bin/bash
# MoxNAS Share Mounting Script

echo "🔧 MoxNAS Share Mount Manager"
echo "=========================="

# Get current IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "Container IP: $SERVER_IP"
echo ""

# Function to test mount
test_mount() {
    local mount_point=$1
    local share_type=$2
    
    if mountpoint -q "$mount_point"; then
        echo "✅ $share_type mounted at $mount_point"
        if [ -w "$mount_point" ]; then
            echo "   Write test: OK"
        else
            echo "   Write test: FAILED (read-only)"
        fi
    else
        echo "❌ $share_type not mounted at $mount_point"
    fi
}

# Check current mounts
echo "📂 Current Share Status:"
test_mount "/mnt/test-smb" "SMB"
test_mount "/mnt/test-nfs" "NFS" 
echo ""

# Show usage
echo "🚀 Manual Commands:"
echo "Mount SMB:  mount /mnt/test-smb"
echo "Mount NFS:  mount /mnt/test-nfs"
echo "Unmount:    umount /mnt/test-smb /mnt/test-nfs"
echo "List:       df -h | grep test"
echo ""

# Offer to remount
if [ "$1" = "mount" ]; then
    echo "🔄 Attempting to mount shares..."
    mount /mnt/test-smb 2>/dev/null && echo "✅ SMB mounted" || echo "❌ SMB mount failed"
    mount /mnt/test-nfs 2>/dev/null && echo "✅ NFS mounted" || echo "❌ NFS mount failed"
fi

if [ "$1" = "test" ]; then
    echo "🧪 Testing write access..."
    echo "Test from $(date)" > /mnt/test-smb/mount-test.txt 2>/dev/null && echo "✅ SMB write OK" || echo "❌ SMB write failed"
    echo "Test from $(date)" > /mnt/test-nfs/mount-test.txt 2>/dev/null && echo "✅ NFS write OK" || echo "❌ NFS write failed"
fi
EOF

chmod +x /opt/moxnas/mount-shares.sh

# Create installation summary
SERVER_IP=$(hostname -I | awk '{print $1}')

# Get storage information
STORAGE_INFO="Container filesystem only"
if [[ -L /mnt/storage ]] && [[ -e /mnt/storage ]]; then
    REAL_PATH=$(readlink -f /mnt/storage)
    if [[ "$REAL_PATH" != "/mnt/storage" ]]; then
        # Get storage size
        STORAGE_SIZE=$(df -h /mnt/storage 2>/dev/null | awk 'NR==2{print $2}' || echo "Unknown")
        if [[ -n "$STORAGE_SIZE" ]]; then
            STORAGE_INFO="Dedicated storage: $STORAGE_SIZE ($REAL_PATH)"
        else
            STORAGE_INFO="Dedicated storage: $REAL_PATH"
        fi
    fi
fi

cat > /opt/moxnas/INSTALLATION_INFO.txt << EOF
MoxNAS Installation Complete!
=============================

Web Interface: https://$SERVER_IP
Admin Username: admin
Admin Password: $ADMIN_PASSWORD

Database Password: $POSTGRES_PASSWORD
Redis Password: $REDIS_PASSWORD

Storage Configuration:
$STORAGE_INFO

Network Shares:
- SMB: //$SERVER_IP/moxnas-storage (user: root, pass: $ADMIN_PASSWORD)
- NFS: $SERVER_IP:/mnt/storage
- FTP: ftp://$SERVER_IP (user: root, pass: $ADMIN_PASSWORD)

Storage Management:
- Web Interface: Storage > Pools (create RAID arrays, manage disks)
- CLI: /opt/moxnas/initialize_storage.py (re-run storage setup)
- Direct access: /mnt/storage (primary storage location)

Mounted Shares (inside container):
- SMB Test Mount: /mnt/test-smb (auto-mounted via fstab)
- NFS Test Mount: /mnt/test-nfs (auto-mounted via fstab)
- Credentials: /etc/cifs-credentials (for SMB access)

Installation Date: $(date)
EOF

chmod 600 /opt/moxnas/INSTALLATION_INFO.txt

# Create welcome motd
cat > /etc/motd << EOF

    __  __            _   _          ____  
   |  \/  | _____  __| \ | |   /\   / ___| 
   | |\/| |/ _ \ \/ /|  \| |  /  \  \___ \ 
   | |  | | (_) >  < | |\  | / /\ \  ___) |
   |_|  |_|\___/_/\_\|_| \_|/_/  \_\|____/ 

   Professional Network Attached Storage
   
   🌐 Web Interface: https://$SERVER_IP
   👤 Username: admin
   🔑 Password: $ADMIN_PASSWORD
   🗝️  Container Root: $PASSWORD
   
   📁 Installation Info: /opt/moxnas/INSTALLATION_INFO.txt
   🔧 Share Mount Manager: /opt/moxnas/mount-shares.sh

   📂 Test Mount Points:
   • SMB: /mnt/test-smb
   • NFS: /mnt/test-nfs
   
   Quick Commands:
   • Check shares: /opt/moxnas/mount-shares.sh
   • Mount shares: /opt/moxnas/mount-shares.sh mount
   • Test shares: /opt/moxnas/mount-shares.sh test

EOF

msg_info "Finalizing installation"
systemctl daemon-reload
systemctl restart supervisor
sleep 3

msg_ok "MoxNAS installation completed successfully!"
echo ""
echo "🎉 Installation Summary:"
echo "📱 Web Interface: https://$SERVER_IP"
echo "👤 Username: admin"
echo "🔑 Password: $ADMIN_PASSWORD"
echo ""
echo "📋 View full details: cat /opt/moxnas/INSTALLATION_INFO.txt"

INSTALL_SCRIPT
)"

msg_ok "MoxNAS installed successfully"

# Get container IP
CONTAINER_IP=$(pct exec ${CTID} -- hostname -I | awk '{print $1}')
INSTALL_INFO=$(pct exec ${CTID} -- cat /opt/moxnas/INSTALLATION_INFO.txt)

echo ""
echo -e "${GN}🎉 MoxNAS Deployment Complete! 🎉${CL}"
echo ""
echo -e "${YW}Container Details:${CL}"
echo -e "CT ID: ${GN}${CTID}${CL}"
echo -e "Hostname: ${GN}${CT_HOSTNAME}${CL}"
echo -e "IP Address: ${GN}${CONTAINER_IP}${CL}"
echo ""
echo -e "${YW}Access Information:${CL}"
echo -e "🌐 Web Interface: ${GN}https://${CONTAINER_IP}${CL}"
echo -e "👤 Username: ${GN}admin${CL}"
echo -e "🔑 Root Password: ${GN}${PASSWORD}${CL}"
echo ""
echo -e "${YW}Management Commands:${CL}"
echo -e "Enter Container: ${GN}pct enter ${CTID}${CL}"
echo -e "View Logs: ${GN}pct exec ${CTID} -- supervisorctl tail -f moxnas-web${CL}"
echo -e "Restart Services: ${GN}pct exec ${CTID} -- supervisorctl restart all${CL}"
echo ""
echo -e "${YW}Installation Details:${CL}"
echo -e "${GN}pct exec ${CTID} -- cat /opt/moxnas/INSTALLATION_INFO.txt${CL}"
echo ""
echo -e "🚀 ${GN}Ready to manage your storage!${CL}"