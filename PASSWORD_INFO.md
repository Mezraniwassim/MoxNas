# MoxNAS Default Passwords

## Overview
For easier deployment and testing, MoxNAS now uses fixed default passwords instead of randomly generated ones.

## Default Credentials

### Web Interface
- **URL**: `https://container-ip`
- **Username**: `admin`
- **Password**: `moxnas1234`

### LXC Container Root Access
- **Username**: `root` 
- **Password**: `moxnas1234`

### Network Shares

#### SMB/CIFS
- **Share**: `//container-ip/moxnas-storage`
- **Username**: `root`
- **Password**: `moxnas1234`

#### FTP
- **URL**: `ftp://container-ip`
- **Username**: `root`
- **Password**: `moxnas1234`

#### NFS
- **Mount**: `container-ip:/mnt/storage`
- **Authentication**: None (host-based access control)

## Security Considerations

### Change Default Passwords
**Important**: Change these default passwords in production environments:

1. **Web Interface**: Login → Settings → Change Password
2. **Root Access**: `passwd` command in container
3. **SMB Password**: `smbpasswd -a root` in container
4. **FTP Access**: Managed through PAM/system password

### Custom Password Installation
To use custom passwords during installation:

```bash
# Set custom passwords
PASSWORD="your-root-password" \
bash -c "$(wget -qLO - https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas-lxc.sh)"
```

## Root Access Rationale

### Why Root User?
MoxNAS now runs as root for several important reasons:

1. **NFS Server Requirements**: NFS kernel server requires root privileges for proper operation
2. **Storage Management**: Direct disk access and RAID operations need root permissions  
3. **Network Services**: Binding to privileged ports (< 1024) requires root
4. **System Integration**: Full hardware access for SMART monitoring and device management

### LXC Container Security
Running as root in LXC containers is safer than traditional systems because:
- **Container Isolation**: Root inside container ≠ root on host
- **Capability Dropping**: LXC drops dangerous capabilities by default
- **Namespace Isolation**: Process, network, and filesystem isolation
- **Resource Limits**: CPU, memory, and I/O constraints applied

### Security Measures
Even with root access, security is maintained through:
- **Strong Web Authentication**: Session management and CSRF protection
- **Input Validation**: All user inputs validated and sanitized
- **Audit Logging**: All administrative actions logged
- **Network Isolation**: Container network is isolated from host
- **Regular Updates**: Keep container and packages updated

## Best Practices

### Production Deployment
1. **Change Passwords**: Immediately after deployment
2. **Enable Firewall**: Restrict access to necessary ports only
3. **SSL Certificates**: Replace self-signed certificates with proper ones
4. **Backup Strategy**: Regular container and data backups
5. **Monitor Logs**: Watch for suspicious activities

### Development/Testing
The default passwords are acceptable for:
- Development environments
- Testing and evaluation
- Internal networks with proper isolation
- Proof-of-concept deployments

---

For more information, see the main MoxNAS documentation or contact support.