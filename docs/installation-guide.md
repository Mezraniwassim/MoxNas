# MoxNAS Installation Guide

This guide covers the complete installation process for MoxNAS, a TrueNAS-inspired network attached storage solution designed for Proxmox LXC containers.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Installation](#quick-installation)
3. [Manual Installation](#manual-installation)
4. [Post-Installation Setup](#post-installation-setup)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **Operating System**: Ubuntu 22.04 LTS or Debian 11+
- **Memory**: 1GB RAM (2GB recommended)
- **Storage**: 4GB available disk space
- **CPU**: 2 cores recommended
- **Network**: Ethernet connection

### Software Dependencies
- Python 3.8+
- Nginx
- Hugo (installed automatically)
- Samba
- NFS kernel server
- vsftpd

## Quick Installation

### Option 1: Proxmox Helper Scripts (Recommended)

For Proxmox VE users, use the community-scripts compliant helper script:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/MoxNAS/main/proxmox/ct/moxnas.sh)"
```

This will:
- Create an LXC container
- Install Ubuntu 22.04
- Configure all dependencies
- Set up MoxNAS automatically
- Start all services

### Option 2: One-Line Local Installation

For existing Ubuntu/Debian systems:

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/MoxNAS/main/install.sh | sudo bash
```

## Manual Installation

### Step 1: Download MoxNAS

```bash
git clone https://github.com/YOUR_USERNAME/MoxNAS.git
cd MoxNAS
```

### Step 2: Run Installation Script

```bash
sudo ./install.sh
```

The installation script will:
1. Check system requirements
2. Install all dependencies
3. Set up directory structure
4. Configure services
5. Build and deploy the web interface
6. Start all services

### Step 3: Verify Installation

```bash
sudo ./test-moxnas.sh
```

## Post-Installation Setup

### 1. Access the Web Interface

Open your web browser and navigate to:
```
http://YOUR_SERVER_IP:8000
```

Default credentials:
- **Username**: `admin`
- **Password**: `admin`

### 2. Change Default Password

**Important**: Change the default password immediately after first login.

1. Navigate to System → Users
2. Click on the admin user
3. Set a new strong password
4. Save changes

### 3. Configure Network Settings

1. Go to Network section
2. Verify network interfaces
3. Configure static IP if needed
4. Set up firewall rules

### 4. Create Your First Share

1. Navigate to Shares section
2. Click "Add Share"
3. Configure share settings:
   - **Name**: Choose a descriptive name
   - **Type**: SMB, NFS, or FTP
   - **Path**: Default is `/mnt/shares/[name]`
   - **Access**: Configure permissions

## Service Configuration

### SMB/CIFS Shares

Access via Windows/macOS:
```
\\YOUR_SERVER_IP\sharename
```

Access via Linux:
```bash
sudo mount -t cifs //YOUR_SERVER_IP/sharename /mnt/point -o guest
```

### NFS Shares

Mount NFS share:
```bash
sudo mount -t nfs YOUR_SERVER_IP:/mnt/shares/sharename /mnt/point
```

Add to `/etc/fstab` for permanent mounting:
```
YOUR_SERVER_IP:/mnt/shares/sharename /mnt/point nfs defaults 0 0
```

### FTP Access

Connect via FTP client:
```
ftp://YOUR_SERVER_IP
```

Anonymous access is enabled by default.

## Verification

### Check Service Status

```bash
# Check all services
sudo systemctl status moxnas-api nginx smbd nfs-kernel-server vsftpd

# Check specific service
sudo systemctl status moxnas-api
```

### Run Comprehensive Tests

```bash
sudo ./test-moxnas.sh
```

### Check Logs

```bash
# API server logs
sudo journalctl -u moxnas-api -f

# Nginx logs
sudo tail -f /var/log/nginx/moxnas_error.log

# Samba logs
sudo tail -f /var/log/samba/smbd.log
```

## Firewall Configuration

### Ubuntu/Debian (ufw)

```bash
# Allow web interface
sudo ufw allow 8000/tcp

# Allow SMB/CIFS
sudo ufw allow 445/tcp
sudo ufw allow 139/tcp

# Allow NFS
sudo ufw allow 2049/tcp
sudo ufw allow 111/tcp

# Allow FTP
sudo ufw allow 21/tcp
sudo ufw allow 20/tcp
sudo ufw allow 30000:31000/tcp

# Enable firewall
sudo ufw enable
```

### Proxmox VE

Add firewall rules in Proxmox web interface:
- Port 8000 (Web Interface)
- Port 445 (SMB)
- Port 2049 (NFS)
- Port 21 (FTP)
- Ports 30000-31000 (FTP Passive)

## Troubleshooting

### Common Issues

#### 1. Web Interface Not Accessible

**Symptoms**: Cannot access http://IP:8000

**Solutions**:
```bash
# Check if nginx is running
sudo systemctl status nginx

# Check if port 8000 is listening
sudo netstat -tlnp | grep :8000

# Restart nginx
sudo systemctl restart nginx

# Check nginx error logs
sudo tail -f /var/log/nginx/moxnas_error.log
```

#### 2. API Server Not Running

**Symptoms**: 502 Bad Gateway or API errors

**Solutions**:
```bash
# Check API server status
sudo systemctl status moxnas-api

# View API server logs
sudo journalctl -u moxnas-api -f

# Restart API server
sudo systemctl restart moxnas-api

# Check Python dependencies
python3 -c "import aiohttp, psutil, aiofiles"
```

#### 3. SMB Shares Not Accessible

**Symptoms**: Cannot connect to SMB shares

**Solutions**:
```bash
# Check Samba service
sudo systemctl status smbd

# Test Samba configuration
sudo testparm

# Check Samba logs
sudo tail -f /var/log/samba/smbd.log

# List active shares
sudo smbstatus --shares
```

#### 4. NFS Shares Not Working

**Symptoms**: Cannot mount NFS shares

**Solutions**:
```bash
# Check NFS server
sudo systemctl status nfs-kernel-server

# Check exports
sudo exportfs -v

# Reload exports
sudo exportfs -ra

# Check NFS logs
sudo journalctl -u nfs-kernel-server -f
```

#### 5. FTP Not Working

**Symptoms**: Cannot connect via FTP

**Solutions**:
```bash
# Check vsftpd service
sudo systemctl status vsftpd

# Test FTP configuration
sudo vsftpd /etc/vsftpd.conf

# Check FTP logs
sudo tail -f /var/log/vsftpd.log
```

### Performance Optimization

#### For Low-Memory Systems

Edit `/etc/systemd/system/moxnas-api.service`:
```ini
[Service]
MemoryMax=256M
```

Then restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart moxnas-api
```

#### For High-Load Systems

Increase worker processes in nginx configuration.

### Getting Help

1. **Check Documentation**: Review all documentation in the `docs/` directory
2. **Run Diagnostics**: Use `./test-moxnas.sh` for comprehensive testing
3. **Check Logs**: Review service logs for error messages
4. **Community Support**: Open an issue on GitHub
5. **Discord/Forums**: Join the community discussions

### Maintenance

#### Regular Tasks

1. **Update System**:
   ```bash
   sudo apt update && sudo apt upgrade
   ```

2. **Backup Configuration**:
   ```bash
   sudo tar -czf moxnas-backup-$(date +%Y%m%d).tar.gz \
       /etc/moxnas /etc/samba/smb.conf /etc/exports /etc/vsftpd.conf
   ```

3. **Monitor Logs**:
   ```bash
   sudo journalctl -u moxnas-api --since "1 hour ago"
   ```

4. **Check Storage**:
   ```bash
   df -h /mnt/shares
   ```

## Security Considerations

### Essential Security Steps

1. **Change Default Passwords**: Never use default credentials in production
2. **Enable Firewall**: Configure appropriate firewall rules
3. **Regular Updates**: Keep system and packages updated
4. **Access Control**: Configure proper user permissions
5. **Network Isolation**: Consider VLANs for storage networks
6. **Backup Strategy**: Implement regular configuration backups

### SSL/TLS Configuration

To enable HTTPS (optional):

1. Generate SSL certificate
2. Configure nginx with SSL
3. Update firewall rules for port 443
4. Test SSL configuration

This completes the installation guide. For additional configuration options and advanced features, see the [User Guide](user-guide.md).