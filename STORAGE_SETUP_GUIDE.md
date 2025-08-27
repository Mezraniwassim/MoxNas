# MoxNAS Storage Setup Guide

## Overview
MoxNAS automatically detects and configures storage disks passed through to the LXC container. This guide explains how to set up storage for your NAS.

## Automatic Disk Detection

### Default Behavior
The installation script automatically:
1. **Detects available storage disks** (sdb, sdc, nvme1n1, etc.)
2. **Passes them through to the LXC container**
3. **Initializes storage** using optimal configuration
4. **Mounts storage** at `/mnt/storage`

### Disk Configuration Options

#### Single Disk
- Creates GPT partition table
- Single ext4 partition using full disk
- Direct mount to `/mnt/storage`

#### Multiple Disks
- Creates LVM volume group `moxnas-vg`
- Uses 90% of available space
- Single logical volume with ext4 filesystem
- Provides expandability for future disks

## Manual Configuration

### Specify Disks Manually
```bash
# Pass specific disks to the installation
STORAGE_DISKS="/dev/sdb,/dev/sdc" ./install-moxnas-lxc.sh
```

### Disable Auto-Detection
```bash
# Disable automatic disk detection
AUTO_DETECT_DISKS="false" ./install-moxnas-lxc.sh
```

### Skip Storage Pool Creation
```bash
# Create container but don't initialize storage
CREATE_STORAGE_POOL="false" ./install-moxnas-lxc.sh
```

## Advanced Storage Management

### Re-run Storage Initialization
```bash
# Enter the container
pct enter <container-id>

# Re-initialize storage
/opt/moxnas/initialize_storage.py
```

### Add Additional Disks

#### 1. Add Disk to Proxmox Host
```bash
# Identify new disk
lsblk

# Add disk to container configuration
echo "lxc.cgroup2.devices.allow: b MAJOR:MINOR rwm" >> /etc/pve/lxc/<ctid>.conf
echo "lxc.mount.entry: /dev/sdX /dev/sdX none bind,optional,create=file" >> /etc/pve/lxc/<ctid>.conf

# Restart container
pct restart <container-id>
```

#### 2. Extend Existing Storage
```bash
# Enter container
pct enter <container-id>

# For LVM setup - add new disk to volume group
pvcreate /dev/sdX
vgextend moxnas-vg /dev/sdX
lvextend -l +100%FREE /dev/moxnas-vg/storage
resize2fs /dev/moxnas-vg/storage
```

## Storage Locations

### Primary Storage
- **Mount Point**: `/mnt/storage`
- **Used for**: Main NAS storage, shares
- **Protocols**: SMB, NFS, FTP access

### Backup Storage  
- **Mount Point**: `/mnt/backups`
- **Used for**: Backup jobs, snapshots
- **Configuration**: Can be separate disk or subdirectory

### Container Storage
- **Mount Point**: `/` (root filesystem)
- **Used for**: OS, applications, temporary files
- **Size**: Defined by `DISK_SIZE` parameter (default 20GB)

## Web Interface Management

### Storage Pools
1. **Access**: Storage > Pools in web interface
2. **Create RAID**: Configure RAID 0, 1, 5, 10 arrays
3. **Monitor**: View disk health, SMART data
4. **Manage**: Create/delete pools, add/remove disks

### Disk Health
1. **SMART Monitoring**: Automatic health checks
2. **Alerts**: Email notifications for failures
3. **Reports**: Detailed disk statistics and predictions

## Troubleshooting

### No Disks Detected
```bash
# Check if disks are available on host
lsblk

# Verify container can see disks
pct enter <container-id>
lsblk

# Check container configuration
cat /etc/pve/lxc/<ctid>.conf | grep lxc.mount.entry
```

### Storage Not Mounted
```bash
# Check mount status
mount | grep storage

# Check fstab entries
cat /etc/fstab

# Manual mount
mount -a

# Re-run initialization
/opt/moxnas/initialize_storage.py
```

### Disk Permissions
```bash
# Fix ownership
chown -R moxnas:moxnas /mnt/storage

# Fix permissions  
chmod 755 /mnt/storage
```

## Performance Optimization

### For SSDs
- Enable TRIM support
- Consider different filesystem (XFS)
- Optimize mount options

### For HDDs
- Use appropriate scheduler
- Consider RAID configuration
- Enable write barriers

### For Mixed Environments
- Use SSD for cache/logs
- Use HDDs for bulk storage
- Consider tiered storage

## Backup Recommendations

### Container Backup
```bash
# Create container backup
vzdump <container-id> --storage <backup-storage>
```

### Data Backup
- Use MoxNAS built-in backup jobs
- Configure external backup targets
- Regular RAID health monitoring
- Test restore procedures

## Security Considerations

### Disk Encryption
- Consider LUKS encryption for sensitive data
- Performance impact on older hardware
- Key management and recovery procedures

### Access Control
- Proper user permissions
- Share-level access control
- Network access restrictions

---

For more information, see the main MoxNAS documentation or access the web interface at `https://container-ip`.