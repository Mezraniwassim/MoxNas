# MoxNAS User Guide

This guide covers the daily operation and management of your MoxNAS system.

## Getting Started

### First Login

1. Access your MoxNAS web interface at `http://YOUR-CONTAINER-IP:8000`
2. Log in with the credentials created during installation
3. Complete the initial setup wizard if prompted

### Dashboard Overview

The dashboard provides a quick overview of your system:

- **Storage Usage**: Current storage capacity and utilization
- **System Status**: CPU, memory, and service status
- **Recent Activity**: Latest snapshots, alerts, and operations
- **Quick Actions**: Common tasks and shortcuts

## Storage Management

### Creating Storage Pools

1. Navigate to **Storage** → **Pools**
2. Click **Create Pool**
3. Select your pool type:
   - **Single**: Single disk (no redundancy)
   - **Mirror**: RAID 1 (requires 2+ disks)
   - **RAID-Z**: RAID 5 equivalent (requires 3+ disks)
   - **RAID-Z2**: RAID 6 equivalent (requires 4+ disks)
4. Select disks to include
5. Configure pool settings and create

### Managing Datasets

Datasets are filesystem containers within pools:

1. Go to **Storage** → **Datasets**
2. Click **Create Dataset**
3. Configure:
   - **Name**: Dataset identifier
   - **Mount Point**: Where it appears in the filesystem
   - **Quota**: Maximum size (optional)
   - **Compression**: Data compression method
   - **Deduplication**: Remove duplicate data blocks

### Snapshots

Snapshots are point-in-time copies of your data:

#### Creating Snapshots
1. Select a dataset
2. Click **Create Snapshot**
3. Enter a descriptive name
4. Click **Create**

#### Managing Snapshots
- **Rollback**: Restore dataset to snapshot state
- **Clone**: Create new dataset from snapshot
- **Delete**: Remove snapshot to free space

#### Automatic Snapshots
Configure automatic snapshots in **Settings** → **Snapshots**:
- **Hourly**: Keep last 24 hours
- **Daily**: Keep last 7 days
- **Weekly**: Keep last 4 weeks
- **Monthly**: Keep last 12 months

## File Sharing

### SMB/CIFS Shares (Windows)

1. Navigate to **Shares** → **SMB**
2. Click **Add Share**
3. Configure:
   - **Name**: Share name as seen by clients
   - **Path**: Dataset or directory to share
   - **Description**: Optional description
   - **Access Control**: Read-only or read-write
   - **Guest Access**: Allow anonymous access
   - **Valid Users**: Specific users or groups

### NFS Shares (Unix/Linux)

1. Go to **Shares** → **NFS**
2. Click **Add Export**
3. Configure:
   - **Path**: Directory to export
   - **Networks**: Allowed client networks (e.g., 192.168.1.0/24)
   - **Options**: 
     - `rw` (read-write) or `ro` (read-only)
     - `sync` (synchronous writes)
     - `no_subtree_check` (performance optimization)

### FTP Shares

1. Navigate to **Shares** → **FTP**
2. Click **Add FTP User**
3. Configure:
   - **Username**: FTP login name
   - **Password**: FTP password
   - **Home Directory**: User's accessible directory
   - **Permissions**: Upload, download, delete

## User Management

### Adding Users

1. Go to **Users** → **Local Users**
2. Click **Add User**
3. Fill in user details:
   - **Username**: Login name
   - **Full Name**: Display name
   - **Email**: Contact email
   - **Password**: Login password
   - **Groups**: Assign to groups

### User Groups

Groups simplify permission management:

1. Navigate to **Users** → **Groups**
2. Click **Add Group**
3. Configure group settings and add members

### Permission Management

Set permissions at the dataset level:
- **Owner**: Full control
- **Group**: Group permissions
- **Other**: Everyone else permissions

## Network Configuration

### Interface Management

1. Go to **Network** → **Interfaces**
2. View and configure network interfaces
3. Set static IP addresses or DHCP
4. Configure VLANs if needed

### DNS Configuration

1. Navigate to **Network** → **DNS**
2. Configure DNS servers
3. Set search domains
4. Manage local hostname resolution

## Service Management

### Controlling Services

1. Go to **Services**
2. View all managed services:
   - **Samba**: SMB/CIFS file sharing
   - **NFS**: Network File System
   - **FTP**: File Transfer Protocol
   - **SSH**: Secure Shell access

For each service:
- **Start/Stop**: Control service state
- **Enable/Disable**: Auto-start on boot
- **Configure**: Service-specific settings
- **Logs**: View service logs

### Service Configuration

#### Samba Configuration
- **Workgroup**: Windows workgroup name
- **Description**: Server description
- **Log Level**: Debugging verbosity
- **Guest Account**: Anonymous access user

#### NFS Configuration
- **Version**: NFS protocol version
- **Port Settings**: Custom port configuration
- **Security**: Kerberos and other security options

## System Monitoring

### Performance Monitoring

The system continuously monitors:
- **CPU Usage**: Per-core and average utilization
- **Memory Usage**: RAM and swap utilization
- **Disk I/O**: Read/write operations and throughput
- **Network I/O**: Interface traffic and errors
- **Temperature**: Hardware temperature sensors

### Alerts and Notifications

Configure alerts in **Settings** → **Alerts**:
- **CPU**: Alert when usage exceeds threshold
- **Memory**: Alert on memory exhaustion
- **Disk Space**: Alert when storage fills up
- **Temperature**: Alert on overheating
- **Service**: Alert when services fail

### Log Management

Access logs through **System** → **Logs**:
- **System Logs**: General system events
- **Application Logs**: MoxNAS-specific logs
- **Service Logs**: Individual service logs
- **Security Logs**: Authentication and access logs

## Backup and Recovery

### Dataset Replication

Replicate datasets to remote systems:

1. Go to **Backup** → **Replication**
2. Click **Add Replication Task**
3. Configure:
   - **Source Dataset**: Local dataset to replicate
   - **Target**: Remote system and dataset
   - **Schedule**: How often to replicate
   - **Retention**: How long to keep replicas

### Export/Import

Export pools for migration:

```bash
# Export pool
zpool export tank

# Import on new system
zpool import tank
```

### Disaster Recovery

1. **Regular Snapshots**: Automated point-in-time recovery
2. **Off-site Replication**: Protect against site disasters
3. **Configuration Backup**: Export system configuration
4. **Documentation**: Keep recovery procedures updated

## Maintenance

### Regular Tasks

#### Weekly
- Review system logs for errors
- Check storage pool health
- Verify backup completion
- Update package lists

#### Monthly
- Update system packages
- Review user access logs
- Clean old snapshots
- Check disk health (SMART)

#### Quarterly
- Update MoxNAS to latest version
- Review and update documentation
- Test backup/recovery procedures
- Security audit and updates

### System Updates

1. Go to **Settings** → **Updates**
2. Check for available updates
3. Review update notes
4. Apply updates during maintenance window

### Performance Tuning

#### Storage Optimization
- **Compression**: Enable for better storage efficiency
- **Deduplication**: Remove duplicate blocks
- **Record Size**: Optimize for your workload
- **ARC Cache**: Tune memory cache settings

#### Network Optimization
- **Jumbo Frames**: Enable for high-throughput networks
- **TCP Tuning**: Optimize for your network conditions
- **Interface Bonding**: Combine interfaces for redundancy

## Troubleshooting

### Common Issues

#### Storage Issues
- **Pool Degraded**: Replace failed disks immediately
- **High Fragmentation**: Consider pool recreation
- **Slow Performance**: Check network and disk I/O

#### Network Issues
- **Can't Access Shares**: Check user permissions and network connectivity
- **Slow Transfer**: Verify network configuration and cables
- **Connection Refused**: Check service status and firewall

#### Service Issues
- **Service Won't Start**: Check configuration files and dependencies
- **Authentication Failed**: Verify user credentials and permissions
- **Performance Problems**: Review resource usage and limits

### Getting Help

1. **Built-in Documentation**: Help system within the interface
2. **Log Analysis**: Check system and service logs
3. **Community Forums**: Join the MoxNAS community
4. **Professional Support**: Available for enterprise deployments

For immediate help:
- Check the [Troubleshooting Guide](troubleshooting.md)
- Review [API Documentation](api-documentation.md)
- Visit the community forums
- Submit issues on GitHub