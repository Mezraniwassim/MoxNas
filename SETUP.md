# MoxNas Setup Guide

## Overview

MoxNas is a Network Attached Storage (NAS) solution designed to run in LXC containers on Proxmox. It provides a web-based dashboard for managing containers, NAS services, and storage.

## Architecture

- **Backend**: Django REST API with Proxmox integration
- **Frontend**: React-based web dashboard
- **Deployment**: LXC containers on Proxmox
- **Services**: FTP, NFS, SSH, SMB/CIFS services

## Installation Methods

### Method 1: Automated Installation (Recommended)

Run this script from your Proxmox host:

```bash
# Clone the repository
git clone https://github.com/Mezraniwassim/MoxNas.git
cd MoxNas

# Run the automated installation script
./scripts/install_moxnas.sh [container_id]
```

The script will:
1. Create an LXC container
2. Install all dependencies
3. Set up MoxNas application
4. Configure services
5. Start the web interface

### Method 2: Manual Installation

1. **Create LXC Container manually in Proxmox**
2. **Enter the container**: `pct enter [container_id]`
3. **Clone repository**:
   ```bash
   git clone https://github.com/Mezraniwassim/MoxNas.git /opt/moxnas
   cd /opt/moxnas
   ```
4. **Run container setup script**:
   ```bash
   chmod +x scripts/start_container.sh
   ./scripts/start_container.sh
   ```

### Method 3: Development Setup

For development on your local machine:

```bash
# Clone repository
git clone https://github.com/Mezraniwassim/MoxNas.git
cd MoxNas

# Copy environment template
cp .env.example .env

# Edit .env with your Proxmox credentials
nano .env

# Run development server
python3 start_moxnas.py
```

## Configuration

### Proxmox Credentials

Create a `.env` file with your Proxmox credentials:

```bash
PROXMOX_HOST=192.168.1.100
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your_password
PROXMOX_PORT=8006
PROXMOX_NODE=pve
```

### Network Configuration

The container will get an IP address via DHCP. If ICMP (ping) is blocked by your firewall, the installation script will continue anyway as it tests HTTP connectivity as a fallback.

## Accessing MoxNas

After installation:

1. **Find container IP**: `pct exec [container_id] -- hostname -I`
2. **Web Interface**: `http://[container_ip]:8000`
3. **Admin Panel**: `http://[container_ip]:8000/admin`
4. **Default Credentials**: 
   - **Web Admin**: Username: `admin`, Password: `admin123`
   - **Container Root**: Password: `moxnas123`

## Services Management

### Starting/Stopping Services

```bash
# From Proxmox host
pct exec [container_id] -- systemctl start moxnas
pct exec [container_id] -- systemctl stop moxnas
pct exec [container_id] -- systemctl status moxnas

# Inside container
./scripts/start_container.sh start
./scripts/start_container.sh stop
./scripts/start_container.sh restart
./scripts/start_container.sh status
```

### Available NAS Services

- **SSH Server**: Port 22 (usually enabled by default)
- **FTP Server**: Port 21 (configure via web interface)
- **NFS Server**: Port 2049 (configure via web interface)
- **SMB/CIFS**: Port 445 (configure via web interface)

## Troubleshooting

### Critical Issues and Solutions

#### 1. **Container Network Issues (ICMP Blocked)**
**Symptom**: Installation fails with "Container network not ready" or ping timeouts
**Solution**: 
- The script now handles ICMP blocking gracefully
- Uses HTTP connectivity tests as fallback
- Installation continues even if ping fails

#### 2. **Frontend Build Failures (Memory Issues)**
**Symptom**: "The build failed because the process exited too early" or out of memory errors
**Solutions**: 
- **Increased default memory**: Container now uses 3GB RAM by default
- **Optimized build process**: Uses `NODE_OPTIONS=--max-old-space-size=1536`
- **Disabled source maps**: `GENERATE_SOURCEMAP=false` for production builds

#### 3. **Web Interface Not Accessible**
**Symptom**: Timeout when accessing `http://[container_ip]:8000`
**Solutions**:
```bash  
# Check if MoxNas is running
pct exec [container_id] -- systemctl status moxnas

# If not running, start manually
pct exec [container_id] -- bash -c 'cd /opt/moxnas && source venv/bin/activate && gunicorn --bind 0.0.0.0:8000 --workers 3 --chdir backend --daemon moxnas.wsgi:application'

# Verify it's listening
pct exec [container_id] -- netstat -tlnp | grep 8000

# Check processes
pct exec [container_id] -- ps aux | grep gunicorn
```

#### 4. **Service Startup Failures**
**Symptom**: Gunicorn doesn't start automatically after installation
**Solutions**:
- **Improved systemd service**: More reliable startup script
- **Startup script**: `/opt/moxnas/start_service.sh` handles migrations and static files
- **Manual restart**: `pct exec [container_id] -- systemctl restart moxnas`

#### 5. **ACLs, Datasets, and Shares Not Working**
**Symptom**: Error messages when trying to create shares or datasets
**Solutions**:
- **Enhanced models**: Full ACL, dataset, and share management
- **Service integration**: Actual NFS, SMB, FTP configuration
- **Path validation**: Proper directory creation and permissions
- **Working API endpoints**: Complete CRUD operations

#### 6. **Missing Credentials Tab**
**Solution**: Added comprehensive "Credentials" tab in Settings with:
- NAS user management
- Service authentication settings
- Admin password changes

### Quick Diagnostic Commands

```bash
# 1. Check container status
pct status [container_id]

# 2. Check MoxNas service
pct exec [container_id] -- systemctl status moxnas

# 3. Check if web interface responds
pct exec [container_id] -- curl -s http://localhost:8000 | head -10

# 4. Check container IP
pct exec [container_id] -- hostname -I

# 5. Check all services
pct exec [container_id] -- systemctl status moxnas ssh vsftpd smbd nfs-kernel-server

# 6. View recent logs
pct exec [container_id] -- journalctl -u moxnas -n 50

# 7. Check disk space
pct exec [container_id] -- df -h

# 8. Manual service restart
pct exec [container_id] -- /opt/moxnas/start_service.sh
```

### Installation Recovery

If installation partially fails:

```bash
# 1. Enter the container
pct enter [container_id]

# 2. Navigate to MoxNas directory
cd /opt/moxnas

# 3. Activate virtual environment
source venv/bin/activate

# 4. Install missing dependencies
pip install -r requirements.txt

# 5. Run migrations
cd backend && python manage.py migrate

# 6. Collect static files
python manage.py collectstatic --noinput

# 7. Build frontend (if needed)
cd ../frontend && npm install && npm run build:prod

# 8. Start service
cd .. && /opt/moxnas/start_service.sh
```

### Memory Optimization

For containers with limited memory:

```bash
# Reduce worker processes
pct exec [container_id] -- bash -c 'cd /opt/moxnas && source venv/bin/activate && gunicorn --bind 0.0.0.0:8000 --workers 1 --chdir backend --daemon moxnas.wsgi:application'

# Or increase container memory
pct set [container_id] --memory 4096
pct reboot [container_id]
```

### Network Troubleshooting

```bash
# Check if ports are open
pct exec [container_id] -- netstat -tlnp

# Check firewall (if applicable)
pct exec [container_id] -- ufw status

# Test internal connectivity
pct exec [container_id] -- curl -v http://localhost:8000

# Check from Proxmox host
curl -v http://[container_ip]:8000
```

## Development

### Backend Development

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
python manage.py runserver
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

### Running Both (Development)

```bash
python3 start_moxnas.py
```

## API Endpoints

- **Dashboard**: `/api/proxmox/dashboard/`
- **Containers**: `/api/containers/`
- **Services**: `/api/services/`
- **Storage**: `/api/storage/`

## Security Notes

1. **Change default passwords** after installation
2. **Configure firewall** to restrict access to management ports
3. **Use HTTPS** in production (configure reverse proxy)
4. **Regular updates** of the system and MoxNas

## Container Management Commands

```bash
# Start container
pct start [container_id]

# Stop container
pct stop [container_id]

# Enter container
pct enter [container_id]

# View container status
pct status [container_id]

# Delete container (WARNING: This will destroy all data)
pct destroy [container_id]
```

## Backup and Recovery

### Container Backup

```bash
# Create backup
vzdump [container_id] --storage [storage_name]

# Restore backup
pct restore [container_id] [backup_file] --storage [storage_name]
```

### Data Backup

Important directories to backup:
- `/opt/moxnas/` - Application files
- `/opt/moxnas/backend/db.sqlite3` - Database
- User data directories (as configured)

## Support

For issues and feature requests:
1. Check the troubleshooting section above
2. Review the logs for error messages
3. Create an issue on the GitHub repository

## Version Information

- **Current Version**: 1.0.0
- **Django Version**: 4.2.7
- **React Version**: 18.2.0
- **Python Version**: 3.8+
- **Node.js Version**: 16+