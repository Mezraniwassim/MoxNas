# MoxNAS LXC Container Deployment Guide

## 🚀 Quick Deployment

### One-Line Installation on Proxmox VE

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/Mezraniwassim/MoxNAS/master/install-moxnas-lxc.sh)"
```

### Manual Installation

```bash
# Download the script
wget https://raw.githubusercontent.com/Mezraniwassim/MoxNAS/master/install-moxnas-lxc.sh

# Make executable
chmod +x install-moxnas-lxc.sh

# Run installation
./install-moxnas-lxc.sh
```

## 📋 System Requirements

### Proxmox VE Host Requirements
- Proxmox VE 7.0 or later
- Minimum 8GB RAM (for host + container)
- Minimum 50GB free storage
- Internet connection for downloading packages

### Container Specifications
- **CPU**: 4 cores (configurable)
- **RAM**: 4GB (configurable) 
- **Storage**: 20GB (configurable)
- **Network**: Bridge interface (vmbr0)

## 🛠️ Advanced Configuration

### Custom Installation Options

You can customize the installation by setting environment variables:

```bash
# Custom container configuration
export CTID=200                    # Container ID
export CT_HOSTNAME="my-moxnas"     # Container hostname
export CORES=6                     # CPU cores
export MEMORY=8192                 # RAM in MB
export DISK_SIZE=50                # Disk size in GB
export NETWORK="vmbr1"             # Network bridge

# Network configuration
export IP_CONFIG="192.168.1.100/24,gw=192.168.1.1"  # Static IP

# Run installation
./install-moxnas-lxc.sh
```

### Manual Storage Setup

For production use, you may want to add additional storage:

```bash
# Add storage mount point to container
pct set <CTID> -mp0 /mnt/data,mp=/mnt/storage

# Or add additional disk
pct set <CTID> -scsi1 local-lvm:50
```

## 🔧 Post-Installation Configuration

### 1. First Login

After installation completes:

1. **Find your container IP**: `pct list | grep moxnas`
2. **Access web interface**: `https://<container-ip>`
3. **Get admin credentials**: 
   ```bash
   pct exec <CTID> -- cat /opt/moxnas/.admin_credentials
   ```

### 2. Security Configuration

#### Change Default Passwords
```bash
# Access container
pct enter <CTID>

# Change admin password via web interface or CLI
cd /opt/moxnas
sudo -u moxnas bash -c "source venv/bin/activate && python -c '
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash
app = create_app(\"production\")
with app.app_context():
    admin = User.query.filter_by(username=\"admin\").first()
    admin.password_hash = generate_password_hash(\"your-new-secure-password\")
    db.session.commit()
    print(\"Password updated\")
'"
```

#### SSL Certificate Configuration
Replace self-signed certificate with proper SSL:

```bash
# Copy your SSL certificate files
pct push <CTID> /path/to/your.crt /etc/ssl/certs/moxnas.crt
pct push <CTID> /path/to/your.key /etc/ssl/private/moxnas.key

# Update nginx configuration
pct exec <CTID> -- sed -i 's/moxnas-selfsigned.crt/moxnas.crt/g' /etc/nginx/sites-available/moxnas
pct exec <CTID> -- sed -i 's/moxnas-selfsigned.key/moxnas.key/g' /etc/nginx/sites-available/moxnas

# Restart nginx
pct exec <CTID> -- systemctl restart nginx
```

### 3. Storage Configuration

#### Add Storage Devices
For real storage devices, you need to pass them through to the container:

```bash
# Example: Pass through physical disks
pct set <CTID> -dev0 /dev/disk/by-id/ata-YOUR-DISK-ID
```

#### Configure NFS Shares
```bash
# Enable NFS server
pct exec <CTID> -- systemctl enable nfs-kernel-server
pct exec <CTID> -- systemctl start nfs-kernel-server
```

#### Configure SMB Shares
```bash
# Configure Samba
pct exec <CTID> -- systemctl enable smbd nmbd
pct exec <CTID> -- systemctl start smbd nmbd
```

## 📊 Monitoring and Maintenance

### Service Status
```bash
# Check all MoxNAS services
pct exec <CTID> -- systemctl status moxnas moxnas-worker nginx postgresql redis-server

# View logs
pct exec <CTID> -- journalctl -u moxnas --lines=50
```

### Database Maintenance
```bash
# Access container
pct enter <CTID>

# Create database backup
sudo -u postgres pg_dump moxnas > /opt/moxnas/backup_$(date +%Y%m%d).sql

# Monitor database size
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('moxnas'));"
```

### Performance Tuning

#### Container Resource Limits
```bash
# Adjust CPU and memory
pct set <CTID> -cores 6 -memory 8192

# Set CPU limit
pct set <CTID> -cpulimit 4
```

#### PostgreSQL Optimization
```bash
# Access container
pct enter <CTID>

# Edit PostgreSQL configuration
nano /etc/postgresql/15/main/postgresql.conf

# Add performance optimizations:
# shared_buffers = 512MB
# effective_cache_size = 2GB
# maintenance_work_mem = 128MB
# checkpoint_completion_target = 0.9
```

## 🔒 Security Recommendations

### 1. Network Security
- Use firewall rules to restrict access
- Consider VPN access for remote management
- Enable fail2ban for brute-force protection

### 2. Container Security
```bash
# Update container regularly
pct exec <CTID> -- apt update && apt upgrade -y

# Monitor security logs
pct exec <CTID> -- tail -f /var/log/auth.log
```

### 3. Backup Strategy
```bash
# Create container backup
vzdump <CTID> --storage local --mode snapshot

# Schedule regular backups
cat > /etc/cron.d/moxnas-backup << EOF
0 2 * * * root vzdump <CTID> --storage backup-storage --mode snapshot --compress lzo
EOF
```

## 🆘 Troubleshooting

### Common Issues

#### Web Interface Not Accessible
```bash
# Check service status
pct exec <CTID> -- systemctl status nginx moxnas

# Check ports
pct exec <CTID> -- netstat -tlnp | grep :443

# Check firewall
pct exec <CTID> -- ufw status
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
pct exec <CTID> -- systemctl status postgresql

# Test database connection
pct exec <CTID> -- sudo -u moxnas bash -c "cd /opt/moxnas && source venv/bin/activate && python -c 'from app import create_app, db; app = create_app(\"production\"); app.app_context().push(); print(db.engine.url)'"
```

#### Storage Issues
```bash
# Check disk usage
pct exec <CTID> -- df -h

# Check mounted filesystems
pct exec <CTID> -- mount | grep moxnas

# Scan for storage devices
pct exec <CTID> -- lsblk
```

### Log Locations
- **MoxNAS Application**: `journalctl -u moxnas`
- **Nginx**: `/var/log/nginx/`
- **PostgreSQL**: `/var/log/postgresql/`
- **System**: `journalctl -xe`

## 📚 Additional Resources

- **GitHub Repository**: https://github.com/Mezraniwassim/MoxNAS
- **Documentation**: https://github.com/Mezraniwassim/MoxNAS/wiki
- **Issue Tracker**: https://github.com/Mezraniwassim/MoxNAS/issues

## 🤝 Support

For support and questions:
1. Check the troubleshooting section above
2. Search existing GitHub issues
3. Create a new issue with detailed information
4. Include relevant log files and system information

---

**MoxNAS** - Professional Network Attached Storage Solution