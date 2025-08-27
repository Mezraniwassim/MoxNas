# MoxNAS - Proxmox Community Script Installation

MoxNAS is a professional Network Attached Storage (NAS) solution designed specifically for Proxmox VE environments. This guide covers installation using the Proxmox VE Helper-Scripts community project.

## One-Line Installation

For the easiest installation experience, use the community script:

```bash
bash -c "$(wget -qLO - https://github.com/community-scripts/ProxmoxVE/raw/main/ct/moxnas.sh)"
```

This will create a new LXC container with MoxNAS pre-configured and ready to use.

## What's Included

The automated installation includes:

### 🚀 **Complete NAS Stack**
- **Web Interface**: Secure HTTPS web management portal
- **Database**: PostgreSQL for data storage
- **Cache**: Redis for sessions and background tasks
- **File Sharing**: SMB/CIFS, NFS, and FTP protocols
- **Storage Management**: RAID support with mdadm
- **Monitoring**: Real-time system health and performance monitoring

### 🔧 **Pre-Configured Services**
- **Nginx**: Reverse proxy with SSL termination
- **Supervisor**: Process management for MoxNAS services
- **Systemd**: Service management and health monitoring
- **Firewall**: UFW configured with appropriate ports
- **SSL**: Self-signed certificates (replace with Let's Encrypt for production)

### 📁 **Default Storage Layout**
- **Application**: `/opt/moxnas/`
- **Storage Pool**: `/mnt/storage/` (ready for mounting drives)
- **Backups**: `/mnt/backups/` (backup destination)
- **FTP Root**: `/srv/ftp/` (FTP access point)

## Container Specifications

### Default Configuration
- **OS**: Ubuntu 24.04 LTS
- **CPU**: 4 cores
- **RAM**: 4096 MB (4 GB)
- **Disk**: 20 GB
- **Container Type**: Unprivileged (recommended)
- **Network**: Bridge mode with DHCP

### Recommended Hardware
For optimal performance:

- **CPU**: 4+ cores (Intel/AMD x64)
- **RAM**: 8+ GB for larger deployments
- **Storage**: 20 GB for OS + additional drives for data
- **Network**: Gigabit Ethernet recommended

## Post-Installation Setup

### 1. **Access the Web Interface**
After installation completes, access MoxNAS via:
```
https://YOUR_CONTAINER_IP
```

**Default Credentials:**
- **Username**: `admin`
- **Password**: (displayed at end of installation)

### 2. **Initial Configuration**
1. **Change Admin Password**: Go to Settings → User Management
2. **Configure Storage**: Add your storage drives in Storage Management
3. **Create Shares**: Set up SMB/NFS shares in Network Shares
4. **Configure Backups**: Set up backup jobs in Backup Management

### 3. **Security Hardening**
1. **SSL Certificate**: Replace self-signed cert with Let's Encrypt
2. **Firewall Rules**: Adjust UFW rules for your network
3. **User Accounts**: Create additional users as needed
4. **2FA**: Enable two-factor authentication for admin accounts

## Advanced Installation Options

### Custom Container Configuration

If you need to customize the container settings, you can modify the variables before running the script:

```bash
# Download the script
wget https://github.com/community-scripts/ProxmoxVE/raw/main/ct/moxnas.sh

# Edit the configuration variables at the top
nano moxnas.sh

# Run the modified script
bash moxnas.sh
```

### Manual LXC Creation

For advanced users who prefer manual container creation:

```bash
# Create container with specific settings
pct create 100 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.xz \
  --hostname moxnas \
  --memory 4096 \
  --cores 4 \
  --rootfs local-lvm:20 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1

# Start the container
pct start 100

# Enter the container and run the installation script
pct enter 100
# ... then run MoxNAS installation manually
```

## Storage Configuration

### Adding Physical Drives

To add physical drives to your MoxNAS container:

1. **Attach drives to Proxmox host**
2. **Pass through to container**:
   ```bash
   # Find the drive
   lsblk
   
   # Add to container (replace 100 with your container ID)
   pct set 100 -mp0 /dev/sdb,mp=/mnt/data
   ```

3. **Configure in MoxNAS web interface**:
   - Go to Storage Management
   - Scan for new devices
   - Create storage pools
   - Set up RAID arrays as needed

### Network Storage

MoxNAS also supports network-attached storage:
- **iSCSI**: Connect to SAN storage
- **NFS**: Mount existing NFS shares
- **SMB**: Connect to Windows shares

## Networking

### Default Port Configuration

The installation configures these ports:

| Service | Port | Protocol | Description |
|---------|------|----------|-------------|
| Web Interface | 80/443 | HTTP/HTTPS | Management portal |
| SMB/CIFS | 139/445 | TCP | Windows file sharing |
| NFS | 2049 | TCP | Unix/Linux file sharing |
| FTP | 21 | TCP | File transfer |
| FTP Data | 10000-10100 | TCP | FTP passive mode |

### Firewall Configuration

The UFW firewall is pre-configured but you may need to adjust rules:

```bash
# Allow additional IP range for SMB
ufw allow from 192.168.1.0/24 to any port 445

# Allow specific host for NFS
ufw allow from 192.168.1.100 to any port 2049
```

## Maintenance & Updates

### Updating MoxNAS

The installation includes an update function:

```bash
# Run from within the container
bash -c "$(wget -qLO - https://github.com/community-scripts/ProxmoxVE/raw/main/ct/moxnas.sh)" -s update
```

### Manual Updates

For manual updates:

```bash
# Enter container
pct enter CONTAINER_ID

# Stop services
supervisorctl stop all

# Update application
cd /opt/moxnas
git pull origin main

# Update dependencies
sudo -u moxnas bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Run migrations
sudo -u moxnas bash -c "source venv/bin/activate && python migrate.py upgrade"

# Start services
supervisorctl start all
```

### Health Monitoring

MoxNAS includes comprehensive health monitoring:

```bash
# Check overall system health
systemctl status moxnas-health

# View health monitor logs
journalctl -u moxnas-health -f

# Manual health check
/usr/local/bin/moxnas-health-monitor --check
```

### Backup & Restore

#### Container Backup (Proxmox)

```bash
# Create container backup
vzdump CONTAINER_ID --storage local --mode snapshot

# Restore container backup
pct restore CONTAINER_ID /var/lib/vz/dump/vzdump-lxc-CONTAINER_ID-*.tar.lzo --storage local
```

#### MoxNAS Data Backup

```bash
# Backup MoxNAS configuration and data
/usr/local/bin/moxnas-maintenance

# Manual database backup
sudo -u moxnas bash -c "cd /opt/moxnas && source venv/bin/activate && python migrate.py backup --backup-file /mnt/backups/moxnas_db_backup.sql"
```

## Troubleshooting

### Common Issues

**1. Web interface not accessible**
```bash
# Check services
supervisorctl status
systemctl status nginx

# Check ports
netstat -tlnp | grep -E ':(80|443|5000)'
```

**2. Database connection errors**
```bash
# Check PostgreSQL
systemctl status postgresql
sudo -u postgres psql -c "SELECT 1"

# Reset database password if needed
sudo -u postgres psql -c "ALTER USER moxnas PASSWORD 'newpassword';"
```

**3. Storage devices not detected**
```bash
# Check if drives are visible
lsblk
fdisk -l

# Scan for new devices
echo 1 > /sys/class/scsi_host/host0/scan
```

**4. File sharing not working**
```bash
# Check SMB
systemctl status smbd nmbd
testparm -s

# Check NFS
systemctl status nfs-kernel-server
showmount -e localhost
```

### Log Files

Important log locations:

| Component | Log Location |
|-----------|--------------|
| MoxNAS Web | `/var/log/supervisor/moxnas-web.log` |
| Background Tasks | `/var/log/supervisor/moxnas-worker.log` |
| Scheduler | `/var/log/supervisor/moxnas-beat.log` |
| Health Monitor | `journalctl -u moxnas-health` |
| Nginx | `/var/log/nginx/error.log` |
| Database | `/var/log/postgresql/postgresql-*-main.log` |

### Getting Help

1. **Documentation**: Check `/opt/moxnas/INSTALLATION_INFO.txt`
2. **Logs**: Review log files for error messages
3. **Community**: Visit the MoxNAS community forums
4. **Issues**: Report bugs on the GitHub repository

## Security Considerations

### Production Deployment

Before using in production:

1. **SSL Certificates**: Replace self-signed certificates
   ```bash
   # Install certbot
   apt install certbot python3-certbot-nginx
   
   # Get Let's Encrypt certificate
   certbot --nginx -d your-domain.com
   ```

2. **Firewall**: Restrict access to necessary networks only
3. **Updates**: Set up automatic security updates
4. **Monitoring**: Configure external monitoring
5. **Backups**: Implement regular backup schedules

### Network Security

- Use VPN for remote access
- Enable 2FA for all admin accounts
- Regular password rotation
- Monitor access logs
- Implement network segmentation

## Performance Optimization

### Container Tuning

```bash
# Increase container limits if needed
pct set CONTAINER_ID --memory 8192 --cores 8

# Enable advanced features
pct set CONTAINER_ID --features keyctl=1,nesting=1
```

### Storage Performance

- Use separate drives for OS and data
- Configure appropriate RAID levels for your needs
- Enable write caching for better performance
- Monitor disk I/O with `iotop`

### Network Performance

- Use bridge mode for best network performance  
- Consider multiple network interfaces for storage traffic
- Enable jumbo frames if supported by your network

---

This installation method provides a complete, production-ready MoxNAS deployment with minimal effort. The automated script handles all the complex configuration details, allowing you to focus on using your new NAS system.