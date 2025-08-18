# MoxNAS Installation Guide

This guide covers the installation of MoxNAS on Proxmox VE using LXC containers.

## Prerequisites

### Proxmox VE Requirements
- Proxmox VE 7.0 or higher
- At least 2GB RAM available for the LXC container
- At least 8GB storage for the container
- Network connectivity to download packages

### Container Requirements
- Debian 12 (Bookworm) LXC container
- Root access within the container
- Internet connectivity for package downloads

## Quick Installation

The easiest way to install MoxNAS is using the Proxmox Helper Scripts framework:

```bash
bash -c "$(wget -qLO - https://github.com/tteck/Proxmox/raw/main/ct/moxnas.sh)"
```

This will:
1. Create a new LXC container with optimal settings
2. Install all required dependencies
3. Set up the MoxNAS application
4. Configure services and start the web interface

## Manual Installation

If you prefer to install manually or on an existing container:

### Step 1: Prepare the Container

1. Create or access a Debian 12 LXC container
2. Update the system:
   ```bash
   apt update && apt upgrade -y
   ```

### Step 2: Run the Installation Script

Download and run the installation script:

```bash
wget -O moxnas-install.sh https://raw.githubusercontent.com/moxnas/moxnas/main/proxmox/install/moxnas-install.sh
chmod +x moxnas-install.sh
./moxnas-install.sh
```

### Step 3: Access the Web Interface

After installation completes, access MoxNAS at:
```
http://CONTAINER-IP:8000
```

Replace `CONTAINER-IP` with the actual IP address of your container.

## Manual Setup (Advanced Users)

For advanced users who want full control over the installation:

### 1. Install Dependencies

```bash
# System packages
apt install -y python3 python3-pip python3-venv nodejs npm nginx sqlite3 git curl wget unzip

# NAS services
apt install -y samba nfs-kernel-server vsftpd

# ZFS tools (if using ZFS)
apt install -y zfsutils-linux
```

### 2. Create Application User

```bash
useradd -r -s /bin/bash -d /opt/moxnas -m moxnas
usermod -aG sudo moxnas
```

### 3. Download MoxNAS

```bash
cd /opt/moxnas
git clone https://github.com/moxnas/moxnas.git .
chown -R moxnas:moxnas /opt/moxnas
```

### 4. Set Up Python Environment

```bash
sudo -u moxnas python3 -m venv venv
sudo -u moxnas /opt/moxnas/venv/bin/pip install -r backend/requirements.txt
```

### 5. Set Up Frontend

```bash
cd frontend
sudo -u moxnas npm install
sudo -u moxnas npm run build
```

### 6. Configure Database

```bash
cd backend
sudo -u moxnas /opt/moxnas/venv/bin/python manage.py migrate
sudo -u moxnas /opt/moxnas/venv/bin/python manage.py collectstatic --noinput
```

### 7. Install Systemd Services

```bash
cp config/systemd/*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable moxnas moxnas-monitor
```

### 8. Configure Nginx

```bash
cp config/nginx/moxnas-nginx.conf /etc/nginx/sites-available/moxnas
ln -s /etc/nginx/sites-available/moxnas /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx
```

### 9. Start Services

```bash
systemctl start moxnas
systemctl start moxnas-monitor
```

## Post-Installation

### 1. Initial Configuration

1. Access the web interface at `http://CONTAINER-IP:8000`
2. Complete the initial setup wizard
3. Create an admin user account
4. Configure storage pools and shares

### 2. Security Considerations

1. Change default passwords
2. Configure firewall rules if needed
3. Set up SSL/TLS certificates for HTTPS
4. Review and adjust service configurations

### 3. Network Configuration

Configure your network settings based on your requirements:

- **SMB/CIFS**: Port 445 (Windows file sharing)
- **NFS**: Port 2049 (Unix/Linux file sharing)
- **FTP**: Port 21 (File transfer)
- **Web Interface**: Port 8000 (Management interface)

## Troubleshooting

### Installation Issues

1. **Container creation fails**: Check Proxmox storage and resources
2. **Package installation fails**: Verify internet connectivity
3. **Service startup fails**: Check logs with `journalctl -u moxnas`

### Common Problems

1. **Web interface not accessible**:
   ```bash
   systemctl status moxnas
   systemctl status nginx
   ss -tlnp | grep :8000
   ```

2. **Database issues**:
   ```bash
   cd /opt/moxnas/backend
   sudo -u moxnas /opt/moxnas/venv/bin/python manage.py check
   ```

3. **Permission problems**:
   ```bash
   chown -R moxnas:moxnas /opt/moxnas
   chmod +x /opt/moxnas/scripts/*.py
   ```

### Log Files

Check these log files for troubleshooting:

- Application logs: `/var/log/moxnas/`
- Nginx logs: `/var/log/nginx/moxnas-*.log`
- System logs: `journalctl -u moxnas`

## Validation

Use the installation validator to check your setup:

```bash
cd /opt/moxnas/scripts
python3 install-validator.py report
```

This will generate a comprehensive report of your installation status.

## Next Steps

After successful installation:

1. Read the [User Guide](user-guide.md) for daily operations
2. Review [API Documentation](api-documentation.md) for automation
3. Check [Troubleshooting](troubleshooting.md) for common issues
4. Join the community for support and updates