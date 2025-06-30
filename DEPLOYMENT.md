# MoxNAS Self-Contained LXC Deployment Guide

MoxNAS is a complete containerized NAS solution that runs entirely within LXC containers on Proxmox. This guide provides comprehensive deployment and management instructions.

## Overview

MoxNAS provides TrueNAS-like functionality in a lightweight LXC container:
- **Complete NAS Services**: SMB, NFS, FTP, SSH, SNMP, iSCSI
- **Modern Web Interface**: Django REST API + React frontend  
- **Cloud Sync & Rsync**: Automated backup and synchronization
- **User Management**: ACLs, groups, and service access control
- **Self-Contained**: No external dependencies or development environment needed

## Quick Installation

### Option 1: One-Line Installation (Recommended)

Run this on your Proxmox host to automatically create and configure a MoxNAS container:

```bash
# Install with default container ID (200)
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/install_moxnas.sh | bash

# Or with custom container ID
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/install_moxnas.sh | bash -s 201
```

### Option 2: Manual Container Creation

1. **Create LXC container:**
   ```bash
   pct create 200 ubuntu-22.04-standard \
     --hostname moxnas \
     --memory 2048 \
     --cores 2 \
     --rootfs local-lvm:8 \
     --net0 name=eth0,bridge=vmbr0,ip=dhcp \
     --features nesting=1,keyctl=1 \
     --unprivileged 0 \
     --onboot 1
   ```

2. **Start container:**
   ```bash
   pct start 200
   ```

3. **Install MoxNAS:**
   ```bash
   pct exec 200 -- bash -c "
   apt update && apt install -y curl git
   cd /opt
   git clone https://github.com/Mezraniwassim/MoxNas.git moxnas
   cd moxnas
   chmod +x start_container.sh
   ./start_container.sh
   "
   ```

## What Gets Installed

### Core Components
- **Django Web Interface**: Complete management UI on port 8080
- **React Frontend**: Built and served by Django (no separate Node.js server)
- **SQLite Database**: Stores configuration and metadata
- **Real-time Monitoring**: CPU, memory, disk, and network stats

### NAS Services
- **SMB/CIFS (Samba)**: Windows file sharing - Port 445
- **NFS**: Network File System - Port 2049  
- **FTP (vsftpd)**: File Transfer Protocol - Port 21
- **SSH**: Secure Shell access - Port 22
- **SNMP**: Network monitoring - Port 161
- **iSCSI (tgt)**: Block-level storage - Port 3260

### Features
- **Storage Management**: Datasets and mount points
- **Share Configuration**: SMB, NFS, and FTP shares with web interface
- **User Management**: Custom user model with NAS-specific permissions
- **Access Control**: ACLs and permission management
- **Service Control**: Start/stop/restart services from web interface
- **System Monitoring**: Real-time system statistics

## Access and Usage

### Web Interface
- **URL**: `http://[container-ip]:8080`
- **Default Login**: `admin` / `moxnas123`
- **Find Container IP**: `pct exec [container-id] -- hostname -I`

### Container Management
```bash
# Start container
pct start 200

# Stop container  
pct stop 200

# Access shell
pct enter 200

# View MoxNAS logs
pct exec 200 -- journalctl -u moxnas -f

# Restart MoxNAS service
pct exec 200 -- systemctl restart moxnas
```

### Adding Storage

To add storage from Proxmox host to the container:

```bash
# Method 1: Add mount point
pct set 200 -mp0 /host/path/to/storage,mp=/mnt/storage

# Method 2: Edit container config
nano /etc/pve/lxc/200.conf
# Add: mp0: /host/path/to/storage,mp=/mnt/storage

# Restart container
pct restart 200
```

## Architecture

```
┌─────────────────────────────────────┐
│           Proxmox Host              │
│  ┌─────────────────────────────────┐│
│  │        LXC Container            ││
│  │  ┌─────────────────────────────┐││
│  │  │       MoxNAS Web UI         │││  ← http://container-ip:8080
│  │  │  Django + React (Built)     │││
│  │  │  SQLite Database            │││
│  │  └─────────────────────────────┘││
│  │  ┌─────────────────────────────┐││
│  │  │       NAS Services          │││
│  │  │  ✓ Samba (SMB/CIFS)        │││  ← Port 445
│  │  │  ✓ NFS Server               │││  ← Port 2049
│  │  │  ✓ FTP Server (vsftpd)      │││  ← Port 21
│  │  │  ✓ SSH Server               │││  ← Port 22
│  │  │  ✓ SNMP Agent               │││  ← Port 161
│  │  │  ✓ iSCSI Target (tgt)       │││  ← Port 3260
│  │  └─────────────────────────────┘││
│  └─────────────────────────────────┘│
│  Storage: /host/storage → /mnt/storage │
└─────────────────────────────────────┘
```

## Key Differences from Previous Version

### Before (Hybrid Architecture)
- Web interface ran on development machine
- Required local Node.js and npm
- Services ran in separate containers
- Complex setup and configuration

### Now (Self-Contained)
- Everything runs inside LXC container
- React frontend is built and served by Django
- Single container with all services
- Simple installation and management
- True TrueNAS-like experience in containers

## Proxmox Integration Setup (Optional)

If you want to use MoxNAS to manage other LXC containers:

1. **Configure environment variables in MoxNAS container:**
   ```bash
   pct exec 200 -- bash -c "
   cat > /opt/moxnas/.env << 'EOF'
   PROXMOX_HOST=your-proxmox-ip
   PROXMOX_PORT=8006
   PROXMOX_USERNAME=root
   PROXMOX_PASSWORD=your-proxmox-password
   PROXMOX_REALM=pam
   PROXMOX_SSL_VERIFY=False
   EOF
   "
   ```

2. **Restart MoxNAS service:**
   ```bash
   pct exec 200 -- systemctl restart moxnas
   ```

3. **Access Proxmox tab in web interface** and add your Proxmox nodes

### Proxmox API User (Recommended)

For security, create a dedicated API user instead of using root:

1. **In Proxmox web interface, go to:** Datacenter → Permissions → Users
2. **Create new user:** `moxnas@pve`
3. **Create API token** for the user
4. **Grant permissions:** PVEAdmin role on `/`
5. **Use token in MoxNAS** instead of password

## Container Management

- **Start:** `pct start 200`
- **Stop:** `pct stop 200`
- **Shell:** `pct enter 200`
- **Logs:** `pct exec 200 -- journalctl -u moxnas -f`

## Features

MoxNAS provides all the NAS functionality the client requested:

### ✅ Core Services
- SMB/CIFS file sharing
- NFS exports  
- FTP server
- SSH access
- SNMP monitoring
- iSCSI targets

### ✅ Web Interface
- **Dashboard:** System overview, service status, network info
- **Storage:** Mount points, datasets, disk usage
- **Shares:** SMB/NFS/FTP share management
- **Network:** Service ports and network configuration
- **Credentials:** User/group management, ACLs
- **Proxmox:** Container management and deployment ⭐ **NEW**
- **System:** Service control, system actions
- **Reporting:** System monitoring and logs

### ✅ Advanced Features
- Access Control Lists (ACLs)
- Dataset management
- User and group management
- Service start/stop/restart
- Real-time system monitoring
- **Proxmox Integration:** Create and manage LXC containers ⭐ **NEW**

### ✅ Proxmox Management Features
- **Node Management:** Add multiple Proxmox hosts
- **Container Creation:** Deploy new MoxNAS containers via web interface
- **Container Control:** Start/stop containers remotely
- **Connection Testing:** Verify Proxmox API connectivity
- **Container Sync:** Import existing containers from Proxmox

## Troubleshooting

1. **Web interface not accessible:**
   ```bash
   pct exec 200 -- systemctl status moxnas
   pct exec 200 -- journalctl -u moxnas
   ```

2. **Services not starting:**
   ```bash
   pct exec 200 -- systemctl status smbd
   pct exec 200 -- systemctl status nfs-kernel-server
   ```

3. **Storage not mounted:**
   ```bash
   pct exec 200 -- df -h
   pct exec 200 -- ls -la /mnt/storage
   ```

## Key Differences from Original TrueNAS

- **No ZFS:** Uses standard filesystems and mount points
- **No VM support:** Focused on NAS services only  
- **No App marketplace:** Core NAS functionality only
- **Container optimized:** Runs efficiently in LXC
- **Lightweight:** Minimal resource requirements

This deployment provides the exact functionality requested by the client: a TrueNAS-like experience running inside LXC containers with all core NAS services and web interface features preserved.