# MoxNAS Proxmox LXC Deployment Guide

## 🚀 Quick Start with Proxmox Community Scripts

### Option 1: Using the Community Script (Recommended)

1. **Access your Proxmox VE host via SSH**

2. **Run the MoxNAS community script**:
   ```bash
   bash -c "$(wget -qLO - https://github.com/community-scripts/ProxmoxVE/raw/main/ct/moxnas.sh)"
   ```

3. **Follow the interactive prompts** to configure:
   - Container ID
   - Hostname
   - Resources (CPU, RAM, Disk)
   - Network settings
   - Root password

4. **Wait for installation** (10-15 minutes)

5. **Access MoxNAS**:
   - Web Interface: `https://container-ip`
   - Username: `admin`
   - Password: `moxnas1234`

### Option 2: Manual Container + Deployment Script

If you prefer to create the container manually:

#### Step 1: Create LXC Container
```bash
# On Proxmox host
pct create 200 local:vztmpl/debian-12-standard_12.2-1_amd64.tar.xz \
  --hostname moxnas \
  --memory 4096 \
  --cores 4 \
  --rootfs local-lvm:20 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --features nesting=1 \
  --unprivileged 1 \
  --onboot 1

# Start container
pct start 200
```

#### Step 2: Deploy MoxNAS Inside Container
```bash
# Enter container
pct enter 200

# Download and run deployment script
wget -O- https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/deploy-lxc.sh | bash
```

## 📋 Container Requirements

### Minimum Requirements
- **OS**: Debian 12 or Ubuntu 22.04/24.04
- **CPU**: 2 cores
- **RAM**: 2GB
- **Disk**: 10GB
- **Features**: `nesting=1` (required for Docker-like functionality)

### Recommended Configuration
- **CPU**: 4 cores
- **RAM**: 4GB
- **Disk**: 20GB
- **Network**: Bridge mode with dedicated IP
- **Storage**: Additional mount points for data

### Advanced Configuration
```bash
# Create container with advanced features
pct create 200 local:vztmpl/debian-12-standard_12.2-1_amd64.tar.xz \
  --hostname moxnas \
  --memory 4096 \
  --cores 4 \
  --rootfs local-lvm:20 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.100/24,gw=192.168.1.1 \
  --nameserver 8.8.8.8 \
  --features nesting=1,keyctl=1 \
  --unprivileged 1 \
  --onboot 1 \
  --protection 0 \
  --swap 2048 \
  --mp0 /mnt/pve-storage,mp=/mnt/storage \
  --mp1 /mnt/pve-backups,mp=/mnt/backups
```

## 🔧 Post-Installation Configuration

### 1. Initial Setup
1. Access web interface: `https://your-container-ip`
2. Login with: `admin` / `moxnas1234`
3. **Change default password immediately**
4. Configure admin email and contact information

### 2. Storage Configuration
1. Go to **Storage Management**
2. Scan for available devices
3. Create storage pools (RAID 0/1/5/10)
4. Create datasets and mount points

### 3. Network Shares Setup
1. Navigate to **Network Shares**
2. Create SMB/CIFS shares for Windows clients
3. Configure NFS exports for Linux/Unix systems
4. Set up FTP access if needed
5. Configure user permissions and access controls

### 4. User Management
1. Go to **User Management**
2. Create additional user accounts
3. Configure role-based permissions
4. Enable 2FA for security

### 5. Backup Configuration
1. Access **Backup Management**
2. Configure backup destinations
3. Create automated backup jobs
4. Set retention policies
5. Test restore procedures

## 🛠️ Storage Integration

### Adding Physical Drives to Container

#### Method 1: Device Passthrough (Privileged Container)
```bash
# Make container privileged (on Proxmox host)
pct set 200 --unprivileged 0

# Pass through disk device
pct set 200 --mp0 /dev/disk/by-id/your-disk-id,mp=/mnt/disk1

# Restart container
pct restart 200
```

#### Method 2: Directory Bind Mount (Recommended)
```bash
# Create mount point on Proxmox host
mkdir -p /mnt/pve-storage

# Mount your drives on Proxmox host
mount /dev/sdb1 /mnt/pve-storage

# Add bind mount to container
pct set 200 --mp0 /mnt/pve-storage,mp=/mnt/storage

# Make permanent in /etc/fstab on Proxmox host
echo "/dev/sdb1 /mnt/pve-storage ext4 defaults 0 0" >> /etc/fstab
```

### ZFS Integration
```bash
# Create ZFS pool on Proxmox host
zpool create storage mirror /dev/sdb /dev/sdc

# Create dataset
zfs create storage/moxnas

# Bind mount to container
pct set 200 --mp0 /storage/moxnas,mp=/mnt/storage
```

## 🌐 Network Configuration

### Port Configuration
| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Web Interface | 80/443 | HTTP/HTTPS | Management |
| SMB/CIFS | 139/445 | TCP | Windows Shares |
| NFS | 2049 | TCP | Unix/Linux Shares |
| FTP | 21 | TCP | File Transfer |
| FTP Data | 10000-10100 | TCP | Passive FTP |

### Firewall Configuration
```bash
# On Proxmox host, allow ports through firewall
# Edit /etc/pve/firewall/cluster.fw

[group management]
IN ACCEPT -p tcp --dport 80
IN ACCEPT -p tcp --dport 443

[group filesharing]  
IN ACCEPT -p tcp --dport 139
IN ACCEPT -p tcp --dport 445
IN ACCEPT -p tcp --dport 2049
IN ACCEPT -p tcp --dport 21
IN ACCEPT -p tcp --dport 10000:10100

# Apply to container
# Edit /etc/pve/firewall/200.fw
[OPTIONS]
enable: 1

[IN]
GROUP management
GROUP filesharing -source 192.168.1.0/24
```

## 🔒 Security Best Practices

### 1. SSL Certificate
```bash
# Inside container, replace self-signed certificate
apt-get install certbot python3-certbot-nginx

# Get Let's Encrypt certificate
certbot --nginx -d your-domain.com

# Auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
```

### 2. Access Control
- Use strong passwords (minimum 12 characters)
- Enable 2FA for all admin accounts
- Restrict SMB/NFS access to specific networks
- Regular security updates

### 3. Network Isolation
```bash
# Create separate VLAN for NAS traffic
# On Proxmox host
ip link add link vmbr0 name vmbr0.100 type vlan id 100
ip addr add 192.168.100.1/24 dev vmbr0.100
ip link set dev vmbr0.100 up

# Assign container to VLAN
pct set 200 --net0 name=eth0,bridge=vmbr0.100,ip=192.168.100.10/24,gw=192.168.100.1
```

## 📊 Monitoring and Maintenance

### Health Monitoring
```bash
# Check service status
systemctl status moxnas moxnas-worker moxnas-beat

# View logs
journalctl -u moxnas -f

# Monitor resources
htop
iotop
```

### Backup Container
```bash
# Create container backup (on Proxmox host)
vzdump 200 --storage local --mode snapshot --compress gzip

# Schedule automatic backups
# Add to /etc/cron.d/vzdump
# 0 2 * * 1 root vzdump 200 --storage local --mode snapshot
```

### Updates
```bash
# Update system packages
apt update && apt upgrade -y

# Update MoxNAS (inside container)
cd /opt/moxnas
systemctl stop moxnas moxnas-worker
git pull origin master
source venv/bin/activate
pip install -r requirements.txt --upgrade
python migrate.py upgrade
systemctl start moxnas moxnas-worker
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Web Interface Not Accessible
```bash
# Check services
systemctl status nginx moxnas

# Check ports
netstat -tlnp | grep -E ':(80|443|5000)'

# Check logs
journalctl -u nginx -f
journalctl -u moxnas -f
```

#### 2. Database Connection Issues
```bash
# Check PostgreSQL
systemctl status postgresql
sudo -u postgres psql -c "SELECT 1"

# Reset database if needed
sudo -u postgres psql
DROP DATABASE moxnas_db;
CREATE DATABASE moxnas_db OWNER moxnas;
```

#### 3. File Shares Not Working
```bash
# SMB troubleshooting
systemctl status smbd nmbd
testparm -s
smbclient -L localhost -U root

# NFS troubleshooting
systemctl status nfs-kernel-server
showmount -e localhost
exportfs -ra
```

#### 4. Storage Issues
```bash
# Check disk space
df -h
lsblk

# Check mount points
mount | grep mnt

# SMART diagnostics
smartctl -a /dev/sdb
```

### Log Locations
- **MoxNAS Application**: `journalctl -u moxnas`
- **Worker Process**: `journalctl -u moxnas-worker`
- **Nginx**: `/var/log/nginx/error.log`
- **PostgreSQL**: `/var/log/postgresql/`
- **Samba**: `/var/log/samba/`

## 🎯 Performance Optimization

### Container Resources
```bash
# Increase container resources if needed
pct set 200 --memory 8192 --cores 8

# Enable advanced features
pct set 200 --features keyctl=1,nesting=1
```

### Storage Performance
- Use separate storage for OS and data
- Consider ZFS for data integrity
- Enable write caching where appropriate
- Monitor I/O with `iotop` and `iostat`

### Network Performance
- Use dedicated network interface for storage traffic
- Enable jumbo frames if supported
- Consider 10GbE for high-throughput environments

## 📞 Support and Community

- **Documentation**: Check `/opt/moxnas/README.md` inside container
- **Logs**: Review system logs for error messages
- **Community**: Visit MoxNAS community forums
- **Issues**: Report bugs on GitHub repository

---

This guide provides comprehensive instructions for deploying MoxNAS in Proxmox LXC containers using the community scripts infrastructure. The automated deployment handles all configuration details, making it easy to get a professional NAS solution running quickly.
