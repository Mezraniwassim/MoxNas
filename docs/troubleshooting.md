# MoxNAS Troubleshooting Guide

This guide helps resolve common issues with MoxNAS installation and operation.

## Installation Issues

### Container Creation Problems

**Problem**: Proxmox Helper Script fails to create container

**Symptoms**:
- Script exits with error
- Container creation timeout
- Insufficient resources error

**Solutions**:
1. Check available storage:
   ```bash
   pvesh get /nodes/NODENAME/storage
   ```

2. Verify memory availability:
   ```bash
   free -h
   ```

3. Check Proxmox logs:
   ```bash
   journalctl -u pveproxy -f
   ```

### Package Installation Failures

**Problem**: Package installation fails during setup

**Symptoms**:
- Network connectivity errors
- Package not found errors
- GPG key errors

**Solutions**:
1. Update package lists:
   ```bash
   apt update
   ```

2. Check internet connectivity:
   ```bash
   ping -c 4 8.8.8.8
   curl -I https://debian.org
   ```

3. Fix broken packages:
   ```bash
   apt --fix-broken install
   dpkg --configure -a
   ```

### Service Startup Issues

**Problem**: MoxNAS services fail to start

**Symptoms**:
- Service inactive/failed status
- Web interface inaccessible
- Database connection errors

**Solutions**:
1. Check service status:
   ```bash
   systemctl status moxnas
   systemctl status nginx
   ```

2. View service logs:
   ```bash
   journalctl -u moxnas -f
   journalctl -u nginx -f
   ```

3. Restart services:
   ```bash
   systemctl restart moxnas
   systemctl restart nginx
   ```

## Web Interface Issues

### Cannot Access Web Interface

**Problem**: Web interface returns connection refused or timeout

**Diagnostic Steps**:
1. Check if services are running:
   ```bash
   systemctl is-active moxnas nginx
   ```

2. Verify port binding:
   ```bash
   ss -tlnp | grep :8000
   ```

3. Check firewall:
   ```bash
   iptables -L INPUT -n
   ufw status
   ```

4. Test local connectivity:
   ```bash
   curl -I http://localhost:8000
   ```

**Solutions**:
1. Restart services:
   ```bash
   systemctl restart moxnas nginx
   ```

2. Check configuration:
   ```bash
   nginx -t
   ```

3. Disable firewall temporarily:
   ```bash
   ufw disable  # Test only
   ```

### Web Interface Loads but Shows Errors

**Problem**: Interface loads but displays error messages

**Common Errors**:

#### "API Connection Failed"
1. Check backend service:
   ```bash
   systemctl status moxnas
   curl http://localhost:8001/api/
   ```

2. Review Django logs:
   ```bash
   tail -f /var/log/moxnas/django.log
   ```

#### "Database Error"
1. Check database file:
   ```bash
   ls -la /opt/moxnas/backend/db.sqlite3
   sudo -u moxnas python manage.py check
   ```

2. Run migrations:
   ```bash
   cd /opt/moxnas/backend
   sudo -u moxnas /opt/moxnas/venv/bin/python manage.py migrate
   ```

### Slow Web Interface

**Problem**: Interface loads slowly or times out

**Diagnostic Steps**:
1. Check system resources:
   ```bash
   top
   free -h
   iostat 1 5
   ```

2. Monitor network:
   ```bash
   netstat -i
   iftop  # if installed
   ```

**Solutions**:
1. Increase worker processes:
   ```bash
   # Edit /etc/systemd/system/moxnas.service
   ExecStart=... --workers 4
   systemctl daemon-reload
   systemctl restart moxnas
   ```

2. Optimize database:
   ```bash
   cd /opt/moxnas/backend
   sudo -u moxnas /opt/moxnas/venv/bin/python manage.py optimizedb
   ```

## Storage Issues

### Pool Creation Failures

**Problem**: Cannot create ZFS pools

**Symptoms**:
- "No such device" errors
- Permission denied errors
- Pool already exists errors

**Solutions**:
1. Check disk availability:
   ```bash
   lsblk
   fdisk -l
   ```

2. Verify ZFS installation:
   ```bash
   which zpool
   modprobe zfs
   ```

3. Check disk usage:
   ```bash
   zpool status
   zpool import
   ```

4. Clear existing labels:
   ```bash
   wipefs -a /dev/sdX  # BE CAREFUL!
   ```

### Pool Degraded Status

**Problem**: Storage pool shows as degraded

**Diagnostic Steps**:
1. Check pool status:
   ```bash
   zpool status -v
   ```

2. Check disk health:
   ```bash
   smartctl -a /dev/sdX
   ```

3. Review system logs:
   ```bash
   dmesg | grep -i error
   journalctl -k | grep -i zfs
   ```

**Solutions**:
1. Replace failed disk:
   ```bash
   zpool replace poolname /dev/old_disk /dev/new_disk
   ```

2. Clear errors (if disk is healthy):
   ```bash
   zpool clear poolname
   ```

3. Scrub pool:
   ```bash
   zpool scrub poolname
   ```

### Disk Detection Issues

**Problem**: Disks not appearing in MoxNAS interface

**Solutions**:
1. Rescan SCSI bus:
   ```bash
   echo "- - -" > /sys/class/scsi_host/host0/scan
   ```

2. Check disk permissions:
   ```bash
   ls -la /dev/sd*
   ```

3. Verify udev rules:
   ```bash
   udevadm trigger
   udevadm settle
   ```

## Share Access Issues

### SMB/CIFS Share Problems

**Problem**: Cannot access SMB shares

**Diagnostic Steps**:
1. Check Samba status:
   ```bash
   systemctl status smbd nmbd
   ```

2. Test Samba configuration:
   ```bash
   testparm -s
   ```

3. Check share permissions:
   ```bash
   ls -la /path/to/share
   ```

**Solutions**:
1. Restart Samba:
   ```bash
   systemctl restart smbd nmbd
   ```

2. Add user to Samba:
   ```bash
   smbpasswd -a username
   ```

3. Fix permissions:
   ```bash
   chown -R moxnas:moxnas /path/to/share
   chmod -R 755 /path/to/share
   ```

### NFS Share Problems

**Problem**: Cannot mount NFS shares

**Diagnostic Steps**:
1. Check NFS status:
   ```bash
   systemctl status nfs-kernel-server
   ```

2. Verify exports:
   ```bash
   exportfs -v
   showmount -e localhost
   ```

3. Test mount locally:
   ```bash
   mount -t nfs localhost:/path/to/export /mnt/test
   ```

**Solutions**:
1. Restart NFS:
   ```bash
   systemctl restart nfs-kernel-server
   ```

2. Re-export shares:
   ```bash
   exportfs -ra
   ```

3. Check firewall:
   ```bash
   ufw allow 2049
   ```

## Network Issues

### Network Configuration Problems

**Problem**: Network interface not working correctly

**Diagnostic Steps**:
1. Check interface status:
   ```bash
   ip addr show
   ip route show
   ```

2. Test connectivity:
   ```bash
   ping gateway_ip
   ping 8.8.8.8
   ```

3. Check DNS:
   ```bash
   nslookup google.com
   cat /etc/resolv.conf
   ```

**Solutions**:
1. Restart networking:
   ```bash
   systemctl restart networking
   ```

2. Reset interface:
   ```bash
   ip link set eth0 down
   ip link set eth0 up
   ```

3. Check cable and switch:
   ```bash
   ethtool eth0
   ```

### DNS Resolution Issues

**Problem**: Cannot resolve hostnames

**Solutions**:
1. Update DNS servers:
   ```bash
   echo "nameserver 8.8.8.8" >> /etc/resolv.conf
   ```

2. Restart systemd-resolved:
   ```bash
   systemctl restart systemd-resolved
   ```

## Performance Issues

### High CPU Usage

**Problem**: System CPU usage is consistently high

**Diagnostic Steps**:
1. Identify high CPU processes:
   ```bash
   top
   htop
   ps aux --sort=-%cpu | head
   ```

2. Check I/O wait:
   ```bash
   iostat 1 5
   ```

**Solutions**:
1. Adjust worker processes:
   ```bash
   # Reduce Gunicorn workers
   systemctl edit moxnas
   ```

2. Optimize database queries:
   ```bash
   # Check slow queries in Django logs
   ```

### High Memory Usage

**Problem**: System running out of memory

**Diagnostic Steps**:
1. Check memory usage:
   ```bash
   free -h
   ps aux --sort=-%mem | head
   ```

2. Check for memory leaks:
   ```bash
   watch -n 1 'cat /proc/meminfo'
   ```

**Solutions**:
1. Restart services:
   ```bash
   systemctl restart moxnas
   ```

2. Increase swap:
   ```bash
   fallocate -l 2G /swapfile
   chmod 600 /swapfile
   mkswap /swapfile
   swapon /swapfile
   ```

### Slow File Transfers

**Problem**: File transfer speeds are slower than expected

**Diagnostic Steps**:
1. Test disk performance:
   ```bash
   hdparm -t /dev/sdX
   dd if=/dev/zero of=/tmp/testfile bs=1M count=1000
   ```

2. Check network performance:
   ```bash
   iperf3 -s  # On server
   iperf3 -c server_ip  # On client
   ```

**Solutions**:
1. Enable jumbo frames:
   ```bash
   ip link set eth0 mtu 9000
   ```

2. Tune network settings:
   ```bash
   echo 'net.core.rmem_max = 67108864' >> /etc/sysctl.conf
   sysctl -p
   ```

## Security Issues

### Authentication Problems

**Problem**: Cannot log in to web interface

**Solutions**:
1. Reset admin password:
   ```bash
   cd /opt/moxnas/backend
   sudo -u moxnas /opt/moxnas/venv/bin/python manage.py changepassword admin
   ```

2. Create new superuser:
   ```bash
   sudo -u moxnas /opt/moxnas/venv/bin/python manage.py createsuperuser
   ```

### Permission Denied Errors

**Problem**: Various permission denied errors

**Solutions**:
1. Fix ownership:
   ```bash
   chown -R moxnas:moxnas /opt/moxnas
   ```

2. Fix permissions:
   ```bash
   chmod +x /opt/moxnas/scripts/*.py
   chmod 644 /etc/systemd/system/moxnas.service
   ```

## Log Analysis

### Important Log Locations

- **MoxNAS Application**: `/var/log/moxnas/`
- **Django**: `/var/log/moxnas/django.log`
- **Nginx**: `/var/log/nginx/moxnas-*.log`
- **System**: `journalctl -u moxnas`
- **Samba**: `/var/log/samba/`
- **System Messages**: `/var/log/syslog`

### Log Analysis Commands

```bash
# Real-time log monitoring
tail -f /var/log/moxnas/django.log

# Search for errors
grep -i error /var/log/moxnas/django.log

# View service logs
journalctl -u moxnas --since "1 hour ago"

# System messages
dmesg | tail -20
```

## Getting Help

### Information to Collect

When seeking help, collect this information:

1. **System Information**:
   ```bash
   uname -a
   cat /etc/os-release
   df -h
   free -h
   ```

2. **MoxNAS Version**:
   ```bash
   cat /opt/moxnas/VERSION
   ```

3. **Service Status**:
   ```bash
   systemctl status moxnas nginx
   ```

4. **Recent Logs**:
   ```bash
   journalctl -u moxnas --since "1 hour ago"
   ```

### Support Channels

1. **Documentation**: Check this guide and other docs
2. **GitHub Issues**: Report bugs and feature requests
3. **Community Forums**: Ask questions and share solutions
4. **Professional Support**: Available for enterprise users

### Diagnostic Script

Run the built-in diagnostic script:

```bash
cd /opt/moxnas/scripts
python3 install-validator.py report
```

This generates a comprehensive system report for troubleshooting.

Remember to always backup your data before making significant changes to the system!