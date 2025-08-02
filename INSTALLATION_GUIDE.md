# MoxNAS Installation Guide

MoxNAS is a containerized NAS solution designed specifically for LXC containers in Proxmox environments.

## Quick Installation

### Method 1: Automatic Installation (Recommended)

1. **Download and run the installation script:**
   ```bash
   wget https://raw.githubusercontent.com/your-repo/MoxNas/main/install_moxnas.sh
   chmod +x install_moxnas.sh
   sudo ./install_moxnas.sh
   ```

2. **Access MoxNAS:**
   - Web Interface: `http://CONTAINER_IP:8000`
   - Admin Panel: `http://CONTAINER_IP:8000/admin`

### Method 2: Manual Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo/MoxNas.git
   cd MoxNas
   ```

2. **Run installation script:**
   ```bash
   sudo ./install_moxnas.sh
   ```

## Installation Features

### ✅ Fixed Issues
- **Network Connectivity**: Improved network checks that work with firewalls blocking ICMP
- **Container Compatibility**: Optimized for LXC containers with proper service management
- **Path Validation**: Robust directory creation and permission handling
- **Service Management**: Fallback methods for starting services in containers
- **Locale Issues**: Automatic locale configuration to prevent warnings

### 🔧 Installation Process
The installation script will:

1. **System Checks**: Detect container environment and validate network connectivity
2. **Dependencies**: Install Python, Node.js, and required system packages
3. **NAS Services**: Install and configure Samba, NFS, FTP, SSH services
4. **MoxNAS App**: Set up Django backend and React frontend
5. **Service Configuration**: Configure services for container environment
6. **Auto-Start**: Start MoxNAS web interface automatically

## Container Management

### Starting MoxNAS Services
```bash
# Start all services
sudo /opt/moxnas/start_container.sh start

# Check status
sudo /opt/moxnas/start_container.sh status

# Restart services
sudo /opt/moxnas/start_container.sh restart

# Stop services
sudo /opt/moxnas/start_container.sh stop
```

### Manual Service Management
```bash
# Start individual services
systemctl start smbd nmbd vsftpd nfs-kernel-server ssh

# Check service status
systemctl status smbd

# View logs
tail -f /var/log/moxnas/error.log
tail -f /var/log/moxnas/access.log
```

## Proxmox LXC Configuration

### Creating LXC Container
```bash
# Create Ubuntu container
pct create 200 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.xz \
  --hostname moxnas \
  --memory 2048 \
  --cores 2 \
  --rootfs local-lvm:8 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1

# Add storage mount point
pct set 200 -mp0 /path/to/host/storage,mp=/mnt/storage

# Start container
pct start 200
```

### Container Configuration Requirements
- **Memory**: Minimum 2GB RAM
- **Storage**: Minimum 8GB for system, separate mount for data
- **Features**: `nesting=1` (required for some services)
- **Network**: Bridge network with internet access

## Troubleshooting

### Common Issues

#### 1. Web Interface Not Accessible
```bash
# Check if gunicorn is running
ps aux | grep gunicorn

# Check port 8000
netstat -tlnp | grep 8000

# Check logs
tail -f /var/log/moxnas/error.log

# Restart web interface
/opt/moxnas/start_container.sh restart
```

#### 2. Service Management Errors
```bash
# Check service status
systemctl status smbd
systemctl status vsftpd
systemctl status nfs-kernel-server

# Try alternative start methods (for containers)
/usr/sbin/smbd -D
/usr/sbin/vsftpd
service nfs-kernel-server start
```

#### 3. Permission Errors
```bash
# Fix storage permissions
sudo chown -R root:root /mnt/storage
sudo chmod -R 755 /mnt/storage

# Fix MoxNAS permissions
sudo chown -R root:root /opt/moxnas
sudo chmod +x /opt/moxnas/backend/start_moxnas.py
```

#### 4. Network Connectivity Issues
```bash
# Test connectivity
wget --spider --timeout=10 http://archive.ubuntu.com
curl -I --max-time 10 http://google.com

# Check DNS
nslookup google.com

# Check container network
ip addr show
route -n
```

### Log Files
- **Application Logs**: `/var/log/moxnas/`
- **Django Logs**: `/var/log/moxnas/error.log`
- **Access Logs**: `/var/log/moxnas/access.log`
- **System Logs**: `/var/log/syslog`

## Configuration

### Environment Variables
Create `/opt/moxnas/.env` file:
```bash
# Database
DATABASE_URL=sqlite:///opt/moxnas/backend/db.sqlite3

# Security
SECRET_KEY=your-secret-key-here
DEBUG=False

# Network
ALLOWED_HOSTS=*
CORS_ALLOW_ALL_ORIGINS=True

# Storage
MOXNAS_STORAGE_PATH=/mnt/storage
MOXNAS_LOG_PATH=/var/log/moxnas

# Proxmox (optional)
PROXMOX_HOST=your-proxmox-ip
PROXMOX_USERNAME=root
PROXMOX_PASSWORD=your-password
```

### Service Configuration
- **Samba**: `/etc/samba/smb.conf`
- **NFS**: `/etc/exports`
- **FTP**: `/etc/vsftpd.conf`
- **SSH**: `/etc/ssh/sshd_config`

## Features

### Core NAS Services
- **SMB/CIFS** (Port 445): Windows file sharing
- **NFS** (Port 2049): Unix/Linux file sharing  
- **FTP** (Port 21): File transfer protocol
- **SSH** (Port 22): Secure shell access

### Management Features
- **Web Interface**: Modern React-based UI
- **REST API**: Full API for automation
- **User Management**: Access control and permissions
- **Storage Management**: Share creation and management
- **System Monitoring**: Resource usage and logs

### Advanced Features
- **Cloud Sync**: Integration with AWS S3, Azure, Google Drive
- **Rsync Tasks**: Scheduled synchronization
- **Proxmox Integration**: Container management from MoxNAS
- **Task Logging**: Comprehensive operation tracking

## Security

### Built-in Security Features
- **Rate Limiting**: API and web interface protection
- **Input Validation**: Path and command sanitization
- **CSRF Protection**: Cross-site request forgery prevention
- **Secure Headers**: XSS and clickjacking protection
- **Session Management**: Secure cookie handling

### Recommended Security Practices
1. Change default passwords
2. Use HTTPS in production
3. Limit network access
4. Regular security updates
5. Monitor access logs

## Support

### Getting Help
1. Check the logs first: `/var/log/moxnas/`
2. Verify network connectivity
3. Check service status
4. Review container configuration

### Reporting Issues
When reporting issues, please include:
- Container configuration
- Error logs from `/var/log/moxnas/`
- Network configuration
- Steps to reproduce

## Development

### Development Setup
```bash
# Clone repository
git clone https://github.com/your-repo/MoxNas.git
cd MoxNas

# Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend setup (separate terminal)
cd frontend
npm install
npm start
```

### Project Structure
```
MoxNas/
├── backend/           # Django application
│   ├── moxnas/       # Main Django project
│   ├── core/         # Core functionality
│   ├── services/     # NAS service management
│   ├── storage/      # Storage management
│   ├── users/        # User management
│   └── proxmox/      # Proxmox integration
├── frontend/         # React application
├── install_moxnas.sh # Installation script
└── start_container.sh # Container startup script
```

This installation guide provides comprehensive instructions for deploying MoxNAS in LXC containers with improved reliability and error handling.