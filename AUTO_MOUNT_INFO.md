# MoxNAS Automatic Share Mounting

## Overview
MoxNAS installation now automatically mounts its own network shares **inside the container** for testing and local access purposes.

## Auto-Created Mount Points

### Inside the Container
- **SMB Test Mount**: `/mnt/test-smb` 
- **NFS Test Mount**: `/mnt/test-nfs`
- **Credentials File**: `/etc/cifs-credentials`

### Automatic Configuration
The installation script automatically:
1. Gets the container's IP address
2. Creates mount points for testing
3. Installs CIFS utilities for SMB mounting
4. Creates secure credentials file for SMB access
5. Adds entries to `/etc/fstab` for persistent mounting
6. Attempts to mount shares immediately
7. Creates test files to verify functionality

## fstab Entries Added
```bash
# MoxNAS Share Mounts (for testing and access)
//container-ip/moxnas-storage /mnt/test-smb cifs credentials=/etc/cifs-credentials,uid=0,gid=0,iocharset=utf8,file_mode=0755,dir_mode=0755,nofail 0 0
container-ip:/mnt/storage /mnt/test-nfs nfs defaults,nofail 0 0
```

## Mount Manager Script

### Location
`/opt/moxnas/mount-shares.sh`

### Usage
```bash
# Check current mount status
/opt/moxnas/mount-shares.sh

# Mount shares manually
/opt/moxnas/mount-shares.sh mount

# Test write access
/opt/moxnas/mount-shares.sh test
```

### Features
- Shows current mount status with ✅/❌ indicators
- Tests write access to mounted shares
- Provides manual mount commands
- Shows container IP address
- Creates test files to verify functionality

## Manual Commands

### Mount Operations
```bash
# Mount SMB share
mount /mnt/test-smb

# Mount NFS share  
mount /mnt/test-nfs

# Unmount all test shares
umount /mnt/test-smb /mnt/test-nfs

# List mounted shares
df -h | grep test
```

### Check Mount Status
```bash
# Check if mount points are active
mountpoint /mnt/test-smb
mountpoint /mnt/test-nfs

# View mount details
mount | grep test
```

## Purpose and Benefits

### Why Auto-Mount?
1. **Immediate Testing**: Verify shares work right after installation
2. **Local Access**: Easy access to NAS storage from within container
3. **Development**: Convenient for development and debugging
4. **Validation**: Proves SMB and NFS services are working correctly

### Use Cases
- **File Operations**: Direct file access via mounted shares
- **Backup Scripts**: Local backup operations
- **Data Migration**: Easy data transfer between storage types
- **Service Verification**: Confirm all protocols are functional

## Security

### Credentials
- SMB credentials stored in `/etc/cifs-credentials`
- File permissions set to `600` (root only)
- Contains username=root, password=moxnas1234

### Safety Features
- `nofail` option prevents boot failures if mounts fail
- Local loopback mounting (container mounting its own shares)
- No external network access required

## Troubleshooting

### Mounts Not Working
```bash
# Check if services are running
systemctl status smbd nmbd nfs-kernel-server

# View mount errors
dmesg | grep -i cifs
dmesg | grep -i nfs

# Manual mount with verbose output
mount -v /mnt/test-smb
mount -v /mnt/test-nfs
```

### Service Issues
```bash
# Restart services
systemctl restart smbd nmbd
systemctl restart nfs-kernel-server

# Check network connectivity  
netstat -tlnp | grep -E '445|2049'
```

### Permission Problems
```bash
# Check storage permissions
ls -la /mnt/storage

# Verify SMB user
smbpasswd -a root

# Test NFS exports
exportfs -v
```

## Integration with Web Interface

The auto-mounted shares integrate seamlessly with the MoxNAS web interface:
- File browser shows content from `/mnt/storage`
- Storage management affects both direct and mounted access
- Share configuration changes reflect in mounted paths
- Backup operations can use mounted shares as sources/destinations

---

This feature provides immediate validation that your MoxNAS installation is working correctly and all network protocols are functional!