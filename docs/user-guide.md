# MoxNAS User Guide

Complete user guide for MoxNAS - the TrueNAS-inspired NAS solution for Proxmox LXC containers.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Storage Management](#storage-management)
4. [Share Management](#share-management)
5. [Network Configuration](#network-configuration)
6. [System Administration](#system-administration)
7. [User Management](#user-management)
8. [Monitoring and Logs](#monitoring-and-logs)
9. [Advanced Features](#advanced-features)
10. [Best Practices](#best-practices)

## Getting Started

### First Login

1. Open your web browser and navigate to `http://YOUR_SERVER_IP:8000`
2. Log in with default credentials:
   - **Username**: `admin`
   - **Password**: `admin`
3. **Important**: Change the default password immediately

### Interface Overview

MoxNAS features a TrueNAS-inspired interface with:
- **Sidebar Navigation**: Access all major sections
- **Dashboard**: System overview and quick actions
- **Real-time Updates**: Live system statistics
- **Responsive Design**: Works on desktop and mobile

## Dashboard Overview

The dashboard provides a comprehensive view of your NAS system.

### System Statistics Cards

- **CPU Usage**: Real-time CPU utilization with progress bar
- **Memory**: RAM usage and availability
- **Storage**: Disk space usage across all drives
- **Network**: Connection status and traffic statistics

### Quick Actions

- **Create Share**: Set up new SMB, NFS, or FTP shares
- **Add User**: Create new system users
- **System Settings**: Access configuration options
- **View Logs**: Check system and service logs

### Service Status

Monitor the status of core NAS services:
- **Web Server** (nginx): Handles web interface
- **SMB/CIFS** (smbd): Windows file sharing
- **NFS Server**: Unix/Linux file sharing  
- **FTP Server** (vsftpd): File transfer protocol

Each service shows:
- Current status (Running/Stopped)
- Restart button for quick service management

## Storage Management

### Storage Overview

The Storage section provides detailed information about:
- Physical drives and partitions
- Mount points and file systems
- Storage usage and availability
- Disk health status

### Disk Management

#### Viewing Disk Information

1. Navigate to **Storage** → **Disks**
2. View disk details:
   - Device name and size
   - File system type
   - Mount point
   - Usage statistics
   - Health status

#### Mount Points

1. Go to **Storage** → **Mount Points**
2. View current mounts:
   - Device path
   - Mount point
   - File system type
   - Mount options

### Storage Monitoring

- **Real-time Usage**: Live updates of disk usage
- **Historical Data**: Usage trends over time
- **Alerts**: Warnings for low disk space
- **SMART Data**: Disk health monitoring (if available)

## Share Management

Share management is the core functionality of MoxNAS, supporting multiple protocols.

### Creating Shares

#### SMB/CIFS Shares (Windows Compatible)

1. Navigate to **Shares**
2. Click **"Add Share"**
3. Configure share settings:
   - **Name**: Share identifier (no spaces)
   - **Type**: Select "SMB"
   - **Path**: Directory path (auto-created if needed)
   - **Guest Access**: Allow anonymous access
   - **Browseable**: Show in network browser
   - **Read Only**: Set write permissions

4. Click **"Create Share"**

**Access SMB Shares**:
- Windows: `\\SERVER_IP\sharename`
- macOS: `smb://SERVER_IP/sharename`
- Linux: `smb://SERVER_IP/sharename`

#### NFS Shares (Unix/Linux)

1. Create new share with type "NFS"
2. Configure NFS-specific options:
   - **Clients**: IP addresses or subnets allowed
   - **Options**: Mount options (rw, ro, sync, etc.)
   - **Root Squash**: Security setting for root access

**Access NFS Shares**:
```bash
sudo mount -t nfs SERVER_IP:/mnt/shares/sharename /mnt/local
```

#### FTP Shares

1. Create new share with type "FTP"
2. Configure FTP settings:
   - **Anonymous Access**: Allow anonymous login
   - **Upload Permissions**: Allow file uploads
   - **Directory Permissions**: Control folder creation

**Access FTP**:
- Browser: `ftp://SERVER_IP`
- Command line: `ftp SERVER_IP`
- FTP clients: FileZilla, WinSCP, etc.

### Managing Existing Shares

#### Share List View

The shares table shows:
- **Name**: Share identifier
- **Type**: Protocol (SMB, NFS, FTP)
- **Path**: File system location
- **Status**: Active/Inactive
- **Actions**: Edit, Delete buttons

#### Editing Shares

1. Click the edit button (pencil icon)
2. Modify share settings
3. Save changes
4. Services automatically reload

#### Deleting Shares

1. Click the delete button (trash icon)
2. Confirm deletion
3. Choose whether to remove directory
4. Share is removed from configuration

### Share Permissions

#### SMB/CIFS Permissions

- **Guest Access**: Anonymous users can access
- **Valid Users**: Specific users allowed
- **Read Only**: Prevent file modifications
- **Create Mask**: Default file permissions
- **Directory Mask**: Default folder permissions

#### NFS Permissions

- **Root Squash**: Map root user to anonymous
- **All Squash**: Map all users to anonymous
- **Anonymous UID/GID**: User/group for anonymous access
- **Sync/Async**: Write synchronization

#### File System Permissions

Standard Unix permissions apply:
- **Owner**: User who created the share
- **Group**: Group ownership
- **Others**: Everyone else
- **Permissions**: Read (r), Write (w), Execute (x)

## Network Configuration

### Network Interfaces

#### Viewing Interface Information

1. Navigate to **Network**
2. View interface details:
   - Interface name (eth0, eth1, etc.)
   - IP address and netmask
   - MAC address
   - Link status
   - Traffic statistics

#### Interface Configuration

Network configuration is typically handled at the container level, but you can:
- Monitor interface status
- View traffic statistics
- Check connectivity
- Diagnose network issues

### Network Services

#### Service Ports

Default ports used by MoxNAS:
- **8000**: Web interface (HTTP)
- **445**: SMB/CIFS
- **2049**: NFS
- **21**: FTP control
- **20**: FTP data
- **30000-31000**: FTP passive ports

#### Firewall Considerations

Ensure these ports are open in your firewall:
```bash
# Web interface
sudo ufw allow 8000/tcp

# SMB
sudo ufw allow 445/tcp

# NFS  
sudo ufw allow 2049/tcp

# FTP
sudo ufw allow 21/tcp
sudo ufw allow 30000:31000/tcp
```

### Network Diagnostics

#### Connection Testing

Use the built-in tools to test:
- **Ping**: Basic connectivity
- **Port Check**: Service availability
- **Bandwidth Test**: Network speed
- **DNS Resolution**: Name lookup

#### Troubleshooting Network Issues

Common solutions:
1. **Check Interface Status**: Ensure interfaces are up
2. **Verify IP Configuration**: Correct IP and netmask
3. **Test Connectivity**: Ping gateway and external hosts
4. **Check Service Ports**: Verify services are listening
5. **Firewall Rules**: Ensure ports are open

## System Administration

### System Information

#### Hardware Details

View system specifications:
- **CPU**: Model, cores, frequency
- **Memory**: Total, used, available
- **Storage**: Drives, partitions, usage
- **Network**: Interfaces, addresses

#### Software Information

Check installed components:
- **Operating System**: Version and build
- **MoxNAS Version**: Current version
- **Service Versions**: Individual service versions
- **Uptime**: System runtime

### Service Management

#### Service Control

From the dashboard or System section:
- **Start**: Begin service operation
- **Stop**: Halt service
- **Restart**: Stop and start service
- **Reload**: Refresh configuration without restart
- **Status**: Check current state

#### Service Configuration

Each service has configuration files:
- **Samba**: `/etc/samba/smb.conf`
- **NFS**: `/etc/exports`
- **FTP**: `/etc/vsftpd.conf`
- **Nginx**: `/etc/nginx/sites-available/moxnas.conf`

### System Settings

#### General Settings

Configure system-wide options:
- **Hostname**: System identifier
- **Timezone**: Local time zone
- **Language**: Interface language
- **Theme**: Interface appearance

#### Security Settings

Important security configurations:
- **Password Policy**: Minimum requirements
- **Session Timeout**: Auto-logout time
- **SSL/TLS**: Enable encryption
- **Access Control**: IP restrictions

### Maintenance

#### System Updates

Keep MoxNAS updated:
1. **Check for Updates**: System will notify of available updates
2. **Download Updates**: Retrieve update packages
3. **Install Updates**: Apply updates with restart if needed
4. **Verify Update**: Confirm successful installation

#### Backup and Restore

#### Configuration Backup

Export system configuration:
1. Navigate to **System** → **Backup**
2. Select components to backup
3. Download backup file
4. Store securely off-site

#### Configuration Restore

Import previous configuration:
1. Navigate to **System** → **Restore**
2. Upload backup file
3. Select components to restore
4. Apply configuration
5. Restart services if needed

## User Management

### User Accounts

#### Creating Users

1. Navigate to **System** → **Users**
2. Click **"Add User"**
3. Configure user details:
   - **Username**: Login identifier
   - **Password**: Secure password
   - **Full Name**: Display name
   - **Email**: Contact information
   - **Role**: Administrator or User
   - **Home Directory**: User's personal space

#### User Roles

**Administrator**:
- Full system access
- Can create/modify users
- Service management
- System configuration

**User**:
- Limited access
- Can access assigned shares
- Cannot modify system settings
- Read-only dashboard access

#### User Management

- **Edit User**: Modify user properties
- **Change Password**: Update authentication
- **Delete User**: Remove user account
- **Disable User**: Temporarily disable access

### Authentication

#### Local Authentication

Default authentication using local user database:
- Users stored in `/etc/moxnas/users.json`
- Passwords hashed and secured
- Session management

#### External Authentication

Future support planned for:
- **LDAP/Active Directory**: Enterprise authentication
- **OAuth2**: Third-party authentication
- **SAML**: Single sign-on

### Access Control

#### Share Permissions

Control user access to shares:
- **User-specific Access**: Assign shares to users
- **Group-based Access**: Organize users into groups
- **Role-based Access**: Permissions based on roles

#### System Permissions

Control system access:
- **Dashboard Access**: View system information
- **Configuration Access**: Modify settings
- **Service Control**: Start/stop services
- **User Management**: Create/modify users

## Monitoring and Logs

### System Monitoring

#### Real-time Metrics

Dashboard displays live metrics:
- **CPU Usage**: Current utilization percentage
- **Memory Usage**: RAM consumption
- **Disk I/O**: Read/write operations
- **Network Traffic**: Bytes sent/received

#### Historical Data

Track trends over time:
- **Performance Graphs**: Visual representations
- **Usage Reports**: Detailed statistics
- **Alert History**: Previous warnings
- **Service Uptime**: Availability metrics

### Log Management

#### System Logs

View comprehensive logging:
- **Application Logs**: MoxNAS-specific events
- **Service Logs**: Individual service messages
- **System Logs**: Operating system events
- **Security Logs**: Authentication and access

#### Log Viewing

Access logs through:
1. **Web Interface**: Logs section in dashboard
2. **Command Line**: Direct log file access
3. **Syslog**: System-wide log aggregation
4. **External Tools**: Log management systems

#### Log Levels

Different log levels available:
- **Error**: System errors and failures
- **Warning**: Potential issues
- **Info**: General information
- **Debug**: Detailed debugging information

### Alerts and Notifications

#### Alert Types

System monitors for:
- **High Resource Usage**: CPU, memory, disk
- **Service Failures**: Service stops or crashes
- **Storage Issues**: Low disk space, errors
- **Network Problems**: Connectivity issues
- **Security Events**: Failed logins, unauthorized access

#### Notification Methods

Alerts can be sent via:
- **Web Interface**: In-dashboard notifications
- **Email**: SMTP notifications
- **SNMP**: Network monitoring systems
- **Webhooks**: Custom integrations

## Advanced Features

### Command Line Management

#### Service Management Scripts

MoxNAS includes powerful command-line tools:

**Samba Management**:
```bash
# Create SMB share
/opt/moxnas/scripts/samba/manage.sh create myshare /mnt/shares/myshare

# List shares
/opt/moxnas/scripts/samba/manage.sh list

# Delete share
/opt/moxnas/scripts/samba/manage.sh delete myshare
```

**NFS Management**:
```bash
# Create NFS export
/opt/moxnas/scripts/nfs/manage.sh create /mnt/shares/nfsshare

# Show active exports
/opt/moxnas/scripts/nfs/manage.sh active

# Reload exports
/opt/moxnas/scripts/nfs/manage.sh reload
```

**FTP Management**:
```bash
# Setup anonymous FTP
/opt/moxnas/scripts/ftp/manage.sh setup-anonymous

# Create FTP user
/opt/moxnas/scripts/ftp/manage.sh create-user ftpuser

# Check FTP status
/opt/moxnas/scripts/ftp/manage.sh status
```

### API Integration

#### REST API

MoxNAS provides a comprehensive REST API:

**System Statistics**:
```bash
curl http://localhost:8001/api/system-stats
```

**Service Status**:
```bash
curl http://localhost:8001/api/services
```

**Share Management**:
```bash
# List shares
curl http://localhost:8001/api/shares

# Create share
curl -X POST -H "Content-Type: application/json" \
  -d '{"name": "api-share", "type": "smb", "path": "/mnt/shares/api-share"}' \
  http://localhost:8001/api/shares

# Delete share
curl -X DELETE http://localhost:8001/api/shares/api-share
```

#### Integration Examples

**Monitoring Integration**:
```python
import requests
import json

def get_system_stats():
    response = requests.get('http://nas-server:8001/api/system-stats')
    return response.json()

stats = get_system_stats()
print(f"CPU Usage: {stats['cpu']['percent']}%")
```

### Automation

#### Scheduled Tasks

Set up automated maintenance:
- **Backup Scripts**: Regular configuration backups
- **Log Rotation**: Prevent log files from growing
- **Health Checks**: Automated system validation
- **Update Checks**: Check for new versions

#### Custom Scripts

Create custom automation:
```bash
#!/bin/bash
# Custom backup script
DATE=$(date +%Y%m%d)
tar -czf "/backup/moxnas-config-$DATE.tar.gz" /etc/moxnas/
```

## Best Practices

### Security

1. **Change Default Passwords**: Never use defaults in production
2. **Regular Updates**: Keep system patched
3. **Access Control**: Limit user permissions
4. **Network Security**: Use VLANs and firewalls
5. **Backup Strategy**: Regular configuration backups
6. **Monitoring**: Watch for security events

### Performance

1. **Resource Monitoring**: Track CPU, memory, disk usage
2. **Service Optimization**: Configure services for your workload
3. **Network Tuning**: Optimize for your network environment
4. **Storage Management**: Monitor disk space and health
5. **Regular Maintenance**: Keep system clean and optimized

### Reliability

1. **Service Monitoring**: Ensure services stay running
2. **Health Checks**: Regular system validation
3. **Redundancy**: Consider backup systems
4. **Documentation**: Keep configuration documented
5. **Testing**: Regular restore testing

### Maintenance Schedule

#### Daily
- Check service status
- Monitor resource usage
- Review error logs

#### Weekly
- System updates
- Log cleanup
- Performance review

#### Monthly
- Configuration backup
- Security review
- Documentation update

#### Quarterly
- Full system audit
- Disaster recovery testing
- Capacity planning

This completes the comprehensive user guide for MoxNAS. For installation instructions, see the [Installation Guide](installation-guide.md). For troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).