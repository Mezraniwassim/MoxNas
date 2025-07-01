# MoxNAS - Containerized NAS Solution

**Version:** 1.0  
**Release Date:** July 2025  
**License:** Custom License for Client Use  

## 🚀 Quick Start

### One-Line Installation
```bash
# Run on your Proxmox host
wget -O - https://raw.githubusercontent.com/YourRepo/MoxNas/main/install_moxnas.sh | bash -s 200
```

### Manual Installation
```bash
# 1. Download MoxNAS
git clone https://github.com/YourRepo/MoxNas.git
cd MoxNas

# 2. Run installer
chmod +x install_moxnas.sh
./install_moxnas.sh 200

# 3. Configure Proxmox credentials
pct exec 200 -- /opt/moxnas/quick_setup.sh

# 4. Access web interface
# Get container IP: pct exec 200 -- hostname -I
# Open: http://[container-ip]:8000
# Login: admin / moxnas123
```

## 📋 System Requirements

- **Proxmox VE 8.0+**
- **Ubuntu 22.04 LXC template**
- **2GB RAM minimum** (4GB recommended)
- **8GB disk space minimum**
- **Network connectivity**

## 🎯 Features

- **Complete NAS Functionality**: SMB/CIFS, NFS, FTP, iSCSI, SSH, SNMP
- **User Management**: Users, groups, ACLs with filesystem integration
- **Storage Management**: Datasets, mount points, usage monitoring
- **Cloud Sync**: AWS S3, Azure, Google Drive, Dropbox, Backblaze B2
- **Rsync Tasks**: Scheduled synchronization with remote servers
- **Proxmox Integration**: Container management via API
- **Real-time Monitoring**: System performance and service status

## 🔧 Configuration

### Proxmox Credentials Setup
```bash
# Quick setup (30 seconds)
pct exec [container-id] -- /opt/moxnas/quick_setup.sh

# Advanced configuration
pct exec [container-id] -- /opt/moxnas/configure_proxmox.sh

# Manual configuration
pct exec [container-id] -- nano /opt/moxnas/.env
# Add: PROXMOX_PASSWORD=your_password
```

### Adding Storage
```bash
# Add host storage to container
pct set [container-id] -mp0 /host/storage/path,mp=/mnt/storage

# Restart container to apply changes
pct restart [container-id]
```

## 🛠️ Management Commands

```bash
# Container management
pct start [container-id]         # Start container
pct stop [container-id]          # Stop container  
pct enter [container-id]         # Access container shell

# MoxNAS service management
pct exec [container-id] -- systemctl status moxnas    # Check status
pct exec [container-id] -- systemctl restart moxnas   # Restart service
pct exec [container-id] -- journalctl -u moxnas -f    # View logs

# Verification
./verify_moxnas.sh [container-id]   # Verify deployment
```

## 🚨 Troubleshooting

### Cannot Access Web Interface
```bash
# Check container status
pct status [container-id]

# Get container IP
pct exec [container-id] -- hostname -I

# Check MoxNAS service
pct exec [container-id] -- systemctl status moxnas

# View logs
pct exec [container-id] -- journalctl -u moxnas -f
```

### Proxmox Connection Issues
```bash
# Reconfigure credentials
pct exec [container-id] -- /opt/moxnas/quick_setup.sh

# Check configuration
pct exec [container-id] -- cat /opt/moxnas/.env | grep PROXMOX
```

### Service Issues
```bash
# Check individual services
pct exec [container-id] -- systemctl status smbd nfs-kernel-server vsftpd

# Restart services
pct exec [container-id] -- systemctl restart smbd nfs-kernel-server
```

## 📞 Support

For technical support and issues:

1. **Check logs**: `pct exec [container-id] -- journalctl -u moxnas -f`
2. **Verify deployment**: `./verify_moxnas.sh [container-id]`
3. **Review documentation** in this README
4. **Contact support** with specific error messages and logs

## 🔒 Security Notes

- Change default admin password after first login
- Use dedicated Proxmox user for API access
- Configure firewall rules to restrict access
- Regularly update the container OS

## 📊 Default Services

| Service | Port | Status |
|---------|------|--------|
| Web Interface | 8000 | Active |
| SMB/CIFS | 445 | Configurable |
| NFS | 2049 | Configurable |
| FTP | 21 | Configurable |
| SSH | 22 | Active |
| SNMP | 161 | Configurable |
| iSCSI | 3260 | Configurable |

---

**MoxNAS - Professional Containerized NAS Solution**  
*Delivered by [Your Company Name]*