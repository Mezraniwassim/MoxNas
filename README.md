# MoxNAS - Containerized NAS Solution

MoxNAS is a lightweight, containerized Network Attached Storage (NAS) solution designed to run in LXC containers on Proxmox. It provides a TrueNAS-like experience without requiring ZFS, virtualization features, or application support.

## 🚀 Quick Start

**One-line installation:**

```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install_moxnas.sh | bash
```

## Features

- **Containerized Architecture**: Runs entirely within LXC containers
- **Multiple Protocols**: SMB/CIFS, NFS, FTP, iSCSI, SSH, SNMP support
- **Modern Web Interface**: Django REST API backend with React frontend
- **Storage Management**: Mount point-based storage (no ZFS required)
- **User Management**: Built-in user and group management
- **Network Configuration**: Container-friendly network setup
- **System Monitoring**: Real-time system performance monitoring

## Quick Installation

### One-Line Installation (On Proxmox Host)

```bash
# Install with default container ID (200)
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install_moxnas.sh | bash

# Install with custom container ID
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install_moxnas.sh | bash -s 201

# If installation fails, run the diagnostic helper
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/manual_install_helper.sh | bash

# Debug storage configuration
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/debug_proxmox_storage.sh | bash
```

### Installation Process

The installation script will:

1. **Create LXC Container**: Ubuntu 22.04 with 2GB RAM, 8GB disk
2. **Install Dependencies**: Python, Node.js, and all NAS services
3. **Download MoxNAS**: Clone repository and setup environment
4. **Configure Services**: SMB, NFS, FTP, SSH, SNMP, iSCSI
5. **Start MoxNAS**: Web interface and all services

### Manual Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Mezraniwassim/MoxNas.git
   cd MoxNas
   ```

2. **Run the installation script:**

   ```bash
   chmod +x install_moxnas.sh
   ./install_moxnas.sh [container_id]
   ```

## Usage

### Accessing MoxNAS

After installation, access the web interface at:

```
http://[container-ip]
```

Find your container IP:

```bash
CONTAINER_IP=$(pct exec [container-id] -- hostname -I | awk '{print $1}')
echo "Access MoxNAS at: http://$CONTAINER_IP"
```

**Default Login Credentials:**

- Username: `admin`
- Password: `moxnas123`

### Container Management

- **Start container:** `pct start [container-id]`
- **Stop container:** `pct stop [container-id]`
- **Access shell:** `pct enter [container-id]`
- **View logs:** `pct exec [container-id] -- journalctl -u moxnas`

### Adding Storage

To add storage from the Proxmox host:

1. **Add mount point to container:**

   ```bash
   pct set [container-id] -mp0 /host/path/to/storage,mp=/mnt/storage
   ```

2. **Or edit container configuration:**

   ```bash
   nano /etc/pve/lxc/[container-id].conf
   ```

   Add line:

   ```
   mp0: /host/path/to/storage,mp=/mnt/storage
   ```

3. **Restart container:**

   ```bash
   pct restart [container-id]
   ```

## Web Interface

The MoxNAS web interface provides the following sections:

### Dashboard

- System overview with CPU, memory, and disk usage
- Service status monitoring
- Network interface information
- Active shares summary

### Storage

- Mount point management
- Dataset organization
- Disk usage monitoring
- Storage configuration

### Shares

- SMB/CIFS share management
- NFS export configuration
- FTP directory setup
- Access control settings

### Network

- Network interface status
- Service port configuration
- Network settings overview

### Shares & Sync ⭐ **NEW**

- **Network Shares**: SMB/CIFS, NFS, FTP share management
- **Cloud Sync**: Sync with AWS S3, Azure Blob, Google Drive, Dropbox, Backblaze B2
- **Rsync Tasks**: Scheduled rsync synchronization with remote servers
- **Real-time sync monitoring** and task logs

### Credentials

- User account management with service access control
- Group administration and permissions
- Access control lists (ACLs) for fine-grained permissions
- Password management and authentication

### Proxmox ⭐ **ENHANCED**

- Container management and deployment
- Multiple Proxmox node support
- Remote container control (start/stop)
- Connection testing and synchronization

### System

- System information
- Configuration settings
- Service management
- System actions (restart, reboot)

### Reporting

- Performance monitoring
- Resource usage charts
- System logs
- Network activity

## Supported Services

| Service | Port | Protocol | Status |
|---------|------|----------|--------|
| Web Interface | 80 | HTTP | ✅ Active |
| SMB/CIFS | 445 | TCP | ⚙️ Configurable |
| NFS | 2049 | TCP/UDP | ⚙️ Configurable |
| FTP | 21 | TCP | ⚙️ Configurable |
| SSH | 22 | TCP | ✅ Active |
| SNMP | 161 | UDP | ⚙️ Configurable |
| iSCSI | 3260 | TCP | ⚙️ Configurable |

## Architecture

MoxNAS is designed with a containerized architecture:

```
┌─────────────────────────────────────┐
│           Proxmox Host              │
│  ┌─────────────────────────────────┐│
│  │        LXC Container            ││
│  │  ┌─────────────────────────────┐││
│  │  │       MoxNAS Application    │││
│  │  │  - Django REST API          │││
│  │  │  - React Frontend           │││
│  │  │  - Service Management       │││
│  │  │  - Storage Management       │││
│  │  └─────────────────────────────┘││
│  │  ┌─────────────────────────────┐││
│  │  │       NAS Services          │││
│  │  │  - Samba (SMB/CIFS)        │││
│  │  │  - NFS Server               │││
│  │  │  - FTP Server               │││
│  │  │  - SSH Server               │││
│  │  │  - SNMP Agent               │││
│  │  │  - iSCSI Target             │││
│  │  └─────────────────────────────┘││
│  └─────────────────────────────────┘│
│  Storage: /host/storage → /mnt/storage │
└─────────────────────────────────────┘
```

## Requirements

### Proxmox Host

- Proxmox VE 8.0 or later
- Available container ID
- Sufficient storage space
- Network connectivity

### LXC Container

- Ubuntu 22.04 base template
- 2GB RAM minimum (4GB recommended)
- 8GB disk space minimum
- Privileged container for some features

## Configuration

### Environment Variables

MoxNAS can be configured using environment variables:

- `MOXNAS_PORT`: Web interface port (default: 80)
- `MOXNAS_STORAGE`: Storage path (default: /mnt/storage)
- `MOXNAS_LOG_LEVEL`: Logging level (default: INFO)

### Configuration Files

- `/etc/moxnas/config.json`: Main configuration
- `/etc/samba/smb.conf`: Samba configuration
- `/etc/exports`: NFS exports
- `/etc/vsftpd.conf`: FTP configuration

## Troubleshooting

### Common Issues

1. **Cannot access web interface:**
   - Check container is running: `pct status [container-id]`
   - Verify container IP: `pct exec [container-id] -- hostname -I`
   - Check MoxNAS service: `pct exec [container-id] -- systemctl status moxnas`

2. **Storage not visible:**
   - Verify mount point: `pct exec [container-id] -- df -h`
   - Check permissions: `pct exec [container-id] -- ls -la /mnt/storage`

3. **Services not starting:**
   - Check service status: `pct exec [container-id] -- systemctl status [service]`
   - View logs: `pct exec [container-id] -- journalctl -u [service]`

### Log Files

- MoxNAS logs: `/var/log/moxnas/`
- Service logs: `journalctl -u [service-name]`
- Web interface: `journalctl -u moxnas`

## Development

### Running in Development Mode

1. **Clone and setup:**

   ```bash
   git clone https://github.com/Mezraniwassim/MoxNas.git
   cd MoxNas
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install frontend dependencies:**

   ```bash
   cd frontend
   npm install
   cd ..
   ```

3. **Run application:**

   ```bash
   python3 start_moxnas.py
   ```

4. **Access at:**
   - Backend API: `http://localhost:8000`
   - Frontend: `http://localhost:3000`

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and issues:

- Create an issue on GitHub
- Check the troubleshooting section
- Review the documentation

## Acknowledgments

- Inspired by TrueNAS Scale
- Built for Proxmox LXC containers
- Designed for simplicity and reliability
