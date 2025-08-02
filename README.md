# MoxNAS - Containerized NAS Solution

MoxNAS is a lightweight, containerized Network Attached Storage (NAS) solution designed to run in LXC containers on Proxmox. It provides a TrueNAS-like experience without requiring ZFS, virtualization features, or application support.

## 🚀 Quick Start

**One-line installation:**

```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/quick_install.sh | sudo bash
```

**That's it!** MoxNAS will be automatically installed and running at `http://CONTAINER_IP:8000`

## Features

- **Containerized Architecture**: Runs entirely within LXC containers
- **Multiple Protocols**: SMB/CIFS, NFS, FTP, iSCSI, SSH, SNMP support
- **Modern Web Interface**: Django REST API backend with React frontend
- **Storage Management**: Mount point-based storage (no ZFS required)
- **User Management**: Built-in user and group management
- **Network Configuration**: Container-friendly network setup
- **System Monitoring**: Real-time system performance monitoring

## Installation Methods

### Universal Installation (Works on Any Proxmox)

**For any existing LXC container or Ubuntu system:**

```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/quick_install.sh | sudo bash
```

**That's it!** Works with:
- ✅ Any Proxmox version (7.x, 8.x+)
- ✅ Any container ID (100, 200, 999, etc.)
- ✅ Any Ubuntu LXC container (20.04, 22.04, 24.04)
- ✅ Any storage configuration (local, NFS, Ceph, ZFS)
- ✅ Any network setup (DHCP, static IP, VLAN)

### Need to Create a Container?

**Option 1 - Use Proxmox Web Interface:**
1. Go to Proxmox web interface
2. Create new LXC container with Ubuntu template
3. Allocate 2GB+ RAM, 8GB+ disk
4. Start container and enter it
5. Run the installation command above

**Option 2 - Command Line (Example):**
```bash
# Example - adjust ID, storage, network for your environment
CTID=200  # Change to available container ID
pct create $CTID local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.xz \
  --hostname moxnas \
  --memory 2048 \
  --cores 2 \
  --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1

# Start and install
pct start $CTID
pct enter $CTID
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/quick_install.sh | sudo bash
```

### What the Installation Does:

1. **System Setup**: Install Python, Node.js, and system dependencies
2. **NAS Services**: Install and configure Samba, NFS, FTP, SSH
3. **MoxNAS App**: Download, build, and configure the web interface
4. **Service Config**: Optimize all services for container environment
5. **Auto-Start**: Launch MoxNAS web interface on port 8000

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
- Password: Generated during installation (check `/opt/moxnas/admin_password.txt` in container)

To view the password:

```bash
pct exec [container-id] -- cat /opt/moxnas/admin_password.txt
```

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
