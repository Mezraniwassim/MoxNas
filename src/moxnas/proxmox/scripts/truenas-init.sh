#!/bin/bash
# TrueNAS Scale initialization script for Debian container

set -e

# Container environment variables
CONTAINER_ROOTFS="${LXC_ROOTFS_PATH:-$1}"
DEBUG=1

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${CONTAINER_ROOTFS}/var/log/truenas-init.log"
}

# Execute command inside container
exec_in_container() {
    chroot "$CONTAINER_ROOTFS" /bin/bash -c "$1"
}

setup_repositories() {
    log "Setting up required repositories"
    # Add required repos
    cat > "${CONTAINER_ROOTFS}/etc/apt/sources.list.d/truenas.list" << EOF
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security bookworm-security main contrib non-free non-free-firmware
EOF
    
    # Create lock directory if it doesn't exist
    mkdir -p "${CONTAINER_ROOTFS}/var/lock"
    
    # Update package lists
    exec_in_container "apt-get update"
}

install_base_packages() {
    log "Installing base packages"
    exec_in_container "DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3 python3-pip \
        samba nfs-kernel-server proftpd-basic \
        lvm2 mdadm \
        nginx \
        openssh-server \
        sudo \
        systemd systemd-sysv"
}

configure_services() {
    log "Configuring base services"
    
    # Enable required services
    exec_in_container "systemctl enable ssh"
    exec_in_container "systemctl enable smbd"
    exec_in_container "systemctl enable nfs-server"
    exec_in_container "systemctl enable proftpd"
    
    # Create necessary directories
    exec_in_container "mkdir -p /mnt/pool0"
    exec_in_container "mkdir -p /var/lib/truenas"
    exec_in_container "mkdir -p /var/log/truenas"
    
    # Set proper permissions
    exec_in_container "chown -R root:root /mnt/pool0"
    exec_in_container "chmod 755 /mnt/pool0"
}

setup_python_environment() {
    log "Setting up Python environment"
    exec_in_container "pip3 install \
        aiohttp \
        psutil \
        pyyaml \
        netifaces \
        proxmoxer"
}

setup_network() {
    log "Configuring network"
    
    # Configure systemd-networkd for DHCP
    cat > "${CONTAINER_ROOTFS}/etc/systemd/network/eth0.network" << EOF
[Match]
Name=eth0

[Network]
DHCP=yes
IPv6AcceptRA=yes
EOF

    # Enable networkd
    exec_in_container "systemctl enable systemd-networkd"
    exec_in_container "systemctl enable systemd-resolved"
    
    # Configure DNS resolution
    exec_in_container "ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf"
}

main() {
    # Check if we're running as a hook
    if [ -z "$CONTAINER_ROOTFS" ]; then
        echo "Error: No container rootfs specified"
        exit 1
    }

    # Create state file path
    INIT_DONE="${CONTAINER_ROOTFS}/var/lib/truenas/.init-done"
    
    # Only run initialization once
    if [ ! -f "$INIT_DONE" ]; then
        log "Starting TrueNAS Scale initialization"
        
        setup_repositories
        install_base_packages
        setup_network
        configure_services
        setup_python_environment
        
        touch "$INIT_DONE"
        log "TrueNAS Scale initialization completed"
    else
        log "TrueNAS Scale already initialized, skipping"
    fi
}

main