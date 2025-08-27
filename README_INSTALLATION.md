# MoxNAS One-Line Installation Guide

**MoxNAS** is a professional Network Attached Storage solution designed for Debian/Ubuntu systems, optimized for Proxmox LXC containers but works on any Debian-based system.

## 🚀 Quick Installation

### One-Line Command

```bash
bash <(curl -s https://raw.githubusercontent.com/moxnas/moxnas/main/install-moxnas.sh)
```

That's it! The script will automatically:
- ✅ Install all required dependencies
- ✅ Configure PostgreSQL database
- ✅ Set up Redis cache server
- ✅ Install and configure MoxNAS application
- ✅ Configure Nginx with SSL
- ✅ Set up file sharing (SMB, NFS, FTP)
- ✅ Configure firewall and security
- ✅ Start all services automatically

## 📋 System Requirements

### Minimum Requirements
- **OS**: Debian 11+ or Ubuntu 20.04+ LTS
- **CPU**: 2 cores (4+ recommended)
- **RAM**: 2GB (4GB+ recommended)
- **Disk**: 10GB (20GB+ recommended)
- **Network**: Internet connection for installation

### Recommended for Production
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 50GB+ for OS, additional drives for storage
- **Network**: Gigabit Ethernet

## 🔧 What Gets Installed

### Core Components
- **PostgreSQL 14+**: Primary database
- **Redis 6+**: Cache and session store
- **Python 3.9+**: Application runtime
- **Nginx**: Web server with SSL
- **Supervisor**: Process manager

### File Sharing Services
- **Samba**: SMB/CIFS (Windows file sharing)
- **NFS**: Network File System (Unix/Linux)
- **vsftpd**: FTP server with SSL support

### Storage & Monitoring
- **mdadm**: RAID array management
- **smartmontools**: Drive health monitoring
- **Health Monitor**: System health daemon
- **Log Rotation**: Automatic log management

### Security Features
- **UFW Firewall**: Pre-configured rules
- **fail2ban**: Intrusion prevention
- **SSL/TLS**: HTTPS encryption
- **Security Headers**: Web security hardening

## 📱 Post-Installation Access

After successful installation, you'll see:

```
╔══════════════════════════════════════════════════════════════╗
║                 MoxNAS Installation Complete!               ║
╠══════════════════════════════════════════════════════════════╣
║ Web Interface: https://YOUR_IP_ADDRESS                      ║
║ Username: admin                                              ║
║ Password: [randomly generated]                              ║
║                                                              ║
║ Please save these credentials and change them after login!  ║
╚══════════════════════════════════════════════════════════════╝
```

## 🌐 Network Shares Access

### SMB/CIFS (Windows)
```
\\YOUR_IP_ADDRESS\storage
Username: moxnas
Password: [admin password]
```

### NFS (Linux/macOS)
```bash
sudo mount -t nfs YOUR_IP_ADDRESS:/mnt/storage /local/mount/point
```

### FTP
```
ftp://YOUR_IP_ADDRESS
Username: moxnas
Password: [admin password]
```

## 🛠️ Manual Installation (Advanced)

If you prefer manual control or need to customize the installation:

```bash
# Download the script
wget https://raw.githubusercontent.com/moxnas/moxnas/main/install-moxnas.sh

# Make it executable
chmod +x install-moxnas.sh

# Review the script (recommended)
less install-moxnas.sh

# Run the installation
sudo ./install-moxnas.sh
```

## 📊 Service Management

### Check Service Status
```bash
# All MoxNAS services
supervisorctl status

# Individual system services
systemctl status moxnas-health
systemctl status postgresql
systemctl status redis-server
systemctl status nginx
```

### View Service Logs
```bash
# MoxNAS application logs
supervisorctl tail -f moxnas-web

# System health monitor
journalctl -u moxnas-health -f

# All MoxNAS logs
tail -f /opt/moxnas/logs/*.log
```

### Restart Services
```bash
# Restart all MoxNAS services
supervisorctl restart all

# Restart individual services
systemctl restart nginx
systemctl restart postgresql
```

## 🔒 Security Hardening

The installation includes basic security, but for production use:

### 1. Change Default Passwords
```bash
# Access web interface and change admin password
# Or use command line:
cd /opt/moxnas
sudo -u moxnas bash -c "source venv/bin/activate && python -c '
from app import create_app, db
from app.models import User
app = create_app()
app.app_context().push()
admin = User.query.filter_by(username=\"admin\").first()
admin.set_password(\"your_new_secure_password\")
db.session.commit()
print(\"Password updated\")
'"
```

### 2. SSL Certificate (Let's Encrypt)
```bash
# Install certbot
apt install certbot python3-certbot-nginx

# Get SSL certificate (replace your-domain.com)
certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

### 3. Firewall Customization
```bash
# Allow specific IP range for SMB
ufw allow from 192.168.1.0/24 to any port 445

# Block FTP if not needed
ufw delete allow 21/tcp
```

### 4. Enable 2FA
- Log into web interface
- Go to Settings → Security
- Enable Two-Factor Authentication

## 📈 Performance Optimization

### For Larger Deployments

1. **Increase Database Performance**:
```bash
# Edit PostgreSQL config
nano /etc/postgresql/*/main/postgresql.conf

# Increase shared_buffers, effective_cache_size
# Restart PostgreSQL
systemctl restart postgresql
```

2. **Optimize Nginx**:
```bash
# Edit Nginx config
nano /etc/nginx/sites-available/moxnas

# Increase worker_connections
# Enable additional caching
systemctl restart nginx
```

3. **Scale Workers**:
```bash
# Edit supervisor config
nano /etc/supervisor/conf.d/moxnas.conf

# Increase Gunicorn workers and Celery concurrency
supervisorctl restart all
```

## 🗂️ Storage Configuration

### Adding Physical Drives

1. **Attach drives to your system**
2. **Detect drives in MoxNAS**:
   - Web Interface → Storage Management → Scan Devices
3. **Create storage pools**:
   - Storage Management → Create Pool
   - Choose RAID level (0, 1, 5, 10)
4. **Create network shares**:
   - Network Shares → Create Share
   - Choose protocol (SMB, NFS, FTP)

### RAID Configuration
MoxNAS supports multiple RAID levels:
- **RAID 0**: Performance (no redundancy)
- **RAID 1**: Mirroring (100% redundancy)
- **RAID 5**: Parity (single drive failure tolerance)
- **RAID 10**: Mirroring + Striping (best of both)

## 🔧 Troubleshooting

### Common Issues

**1. Web interface not accessible**
```bash
# Check services
supervisorctl status
systemctl status nginx

# Check firewall
ufw status
```

**2. Database connection errors**
```bash
# Check PostgreSQL
systemctl status postgresql
sudo -u postgres psql -c "SELECT version();"
```

**3. File shares not working**
```bash
# Check SMB
systemctl status smbd nmbd
testparm -s

# Check NFS
systemctl status nfs-kernel-server
showmount -e localhost
```

**4. Permission issues**
```bash
# Fix ownership
chown -R moxnas:moxnas /opt/moxnas
chown -R moxnas:moxnas /mnt/storage
```

### Log Locations

| Component | Log Path |
|-----------|----------|
| Installation | `/var/log/moxnas-install.log` |
| Web Application | `/opt/moxnas/logs/web.log` |
| Background Tasks | `/opt/moxnas/logs/worker.log` |
| Scheduler | `/opt/moxnas/logs/scheduler.log` |
| Health Monitor | `journalctl -u moxnas-health` |
| Nginx | `/var/log/nginx/error.log` |
| Database | `/var/log/postgresql/postgresql-*-main.log` |

### Getting Help

1. **Check installation info**: `cat /opt/moxnas/INSTALLATION_INFO.txt`
2. **Run health check**: `/usr/local/bin/moxnas-health-monitor --check`
3. **View system status**: Check the MOTD when logging in via SSH
4. **Community Support**: GitHub Issues and Discussions

## 🔄 Updates & Maintenance

### Updating MoxNAS
```bash
# Automated update (when available)
cd /opt/moxnas
sudo -u moxnas bash -c "source venv/bin/activate && python update.py"

# Manual update
cd /opt/moxnas
git pull origin main
sudo -u moxnas bash -c "source venv/bin/activate && pip install -r requirements.txt"
sudo -u moxnas bash -c "source venv/bin/activate && python migrate.py upgrade"
supervisorctl restart all
```

### System Maintenance
```bash
# Run maintenance script
/usr/local/bin/moxnas-maintenance

# Update system packages
apt update && apt upgrade

# Clean up logs
logrotate -f /etc/logrotate.d/moxnas
```

### Backup & Restore
```bash
# Backup configuration and database
cd /opt/moxnas
sudo -u moxnas bash -c "source venv/bin/activate && python migrate.py backup --backup-file /mnt/backups/moxnas-backup-$(date +%Y%m%d).sql"

# Backup entire application directory
tar -czf /mnt/backups/moxnas-full-backup-$(date +%Y%m%d).tar.gz /opt/moxnas
```

## 🏢 Production Deployment Checklist

- [ ] Change all default passwords
- [ ] Install proper SSL certificates
- [ ] Configure firewall for your network
- [ ] Set up monitoring and alerting
- [ ] Configure automated backups
- [ ] Test disaster recovery procedures
- [ ] Document your specific configuration
- [ ] Set up log aggregation
- [ ] Configure network time synchronization
- [ ] Plan for capacity expansion

---

## 📞 Support & Community

- **Documentation**: [GitHub Wiki](https://github.com/moxnas/moxnas/wiki)
- **Issues**: [GitHub Issues](https://github.com/moxnas/moxnas/issues)
- **Discussions**: [GitHub Discussions](https://github.com/moxnas/moxnas/discussions)
- **License**: MIT License

MoxNAS is open-source software, contributions are welcome!