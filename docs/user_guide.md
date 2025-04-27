# MoxNAS User Guide

## Overview

MoxNAS is a streamlined NAS solution designed to run as an LXC container in Proxmox VE 8.4. It provides core NAS functionality including SMB, NFS, FTP, and iSCSI services while using efficient mount point-based storage.

### System Architecture

```ascii
┌─────────────────────────────────────────────────┐
│                 Proxmox VE 8.4                  │
│                                                 │
│  ┌─────────────────────────────────────────┐    │
│  │           MoxNAS LXC Container          │    │
│  │                                         │    │
│  │  ┌─────────┐  ┌──────┐  ┌──────────┐   │    │
│  │  │ Storage │  │ Core │  │ Network  │   │    │
│  │  │ Manager │  │ Svcs │  │ Services │   │    │
│  │  └────┬────┘  └──┬───┘  └────┬─────┘   │    │
│  │       │          │           │         │    │
│  │  ┌────┴──────────┴───────────┴─────┐   │    │
│  │  │        Mount Points            │   │    │
│  │  │   ┌─────────┐  ┌─────────┐     │   │    │
│  │  │   │ pool0   │  │  tank   │     │   │    │
│  │  │   └─────────┘  └─────────┘     │   │    │
│  │  └────────────────────────────────┘   │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

## System Requirements

- Proxmox VE 8.4
- Container Resources:
  - Memory: 4GB minimum
  - CPU: 2 cores minimum
  - Storage: 32GB minimum for root filesystem
  - Network: One network interface

## Quick Start Guide

### 1. Accessing MoxNAS

Network Architecture:

```ascii
┌──────────────┐     ┌───────────────┐     ┌─────────────┐
│   Windows    │     │    MoxNAS     │     │   Linux     │
│   Client     │─────│  172.16.135.130│─────│   Client    │
└──────────────┘     └───────────────┘     └─────────────┘
       │                     │                    │
       ├─────── SMB/CIFS ───►│                    │
       │                     │◄──── NFS ─────────┤
       │                     │                    │
       └────── FTP/SFTP ────►│◄───── iSCSI ─────┘
```

### 2. Storage Management

Storage Layout:

```ascii
┌─────────────────────────────────────┐
│            Mount Points             │
│                                     │
│  /mnt/pool0           /mnt/tank    │
│  ├── share1           ├── data     │
│  ├── nfs_share        ├── backup   │
│  └── iscsi_store      └── media    │
└─────────────────────────────────────┘
```

To check storage status:

```bash
df -h /mnt/pool0 /mnt/tank
```

### 3. File Sharing Services

Service Architecture:

```ascii
┌────────────────────────────────────────────────┐
│                  MoxNAS Services               │
│                                                │
│  ┌─────────┐   ┌─────────┐   ┌─────────────┐  │
│  │   SMB   │   │   NFS   │   │    FTP      │  │
│  │ Port 445│   │Port 2049│   │   Port 21   │  │
│  └────┬────┘   └────┬────┘   └─────┬───────┘  │
│       │             │              │          │
│  ┌────┴─────────────┴──────────────┴────┐     │
│  │           Storage Backend            │     │
│  │         (Mount Point Based)          │     │
│  └─────────────────────────────────────┘     │
└────────────────────────────────────────────────┘
```

### 4. Service Management

Check service status:

```bash
systemctl status smbd       # SMB service
systemctl status nfs-server # NFS service
systemctl status vsftpd     # FTP service
systemctl status tgt        # iSCSI service
```

Restart services if needed:

```bash
systemctl restart smbd       # Restart SMB
systemctl restart nfs-server # Restart NFS
systemctl restart vsftpd     # Restart FTP
systemctl restart tgt        # Restart iSCSI
```

### 5. Mount Point Monitoring

Monitoring Architecture:

```ascii
┌────────────────────────────────────────┐
│        Mount Point Monitoring          │
│                                        │
│  ┌──────────────┐    ┌──────────────┐  │
│  │ SMB Monitor  │    │ NFS Monitor  │  │
│  └───────┬──────┘    └──────┬───────┘  │
│          │                   │         │
│  ┌───────┴───────────────────┴───────┐  │
│  │        Systemd Services           │  │
│  └───────────────┬─────────────────┘  │
│                  │                    │
│  ┌───────────────┴─────────────────┐  │
│  │         Auto Recovery           │  │
│  └────────────────────────────────┘  │
└────────────────────────────────────────┘
```

View monitoring status:

```bash
systemctl status moxnas-mount-*
```

Check mount point status:

```bash
systemctl status moxnas-mount-smb
systemctl status moxnas-mount-nfs
```

### 6. Best Practices

1. Storage Management
   - Regularly monitor storage usage
   - Keep at least 10% free space
   - Check mount points status regularly

2. Security
   - Change default passwords
   - Use strong authentication
   - Limit NFS exports to specific subnets
   - Configure firewall rules in Proxmox

3. Maintenance
   - Regular service status checks
   - Monitor system logs
   - Keep backups of important data

### 7. Troubleshooting

Common Issues and Solutions:

1. Share Access Issues

   ```bash
   # Check SMB configuration
   testparm
   
   # Check NFS exports
   exportfs -v
   ```

2. Mount Point Problems

   ```bash
   # Verify mounts
   df -h
   mount | grep mnt
   
   # Check mount monitoring
   journalctl -u moxnas-mount-*
   ```

3. Service Failures

   ```bash
   # Check service logs
   journalctl -u smbd
   journalctl -u nfs-server
   journalctl -u vsftpd
   journalctl -u tgt
   ```

## Troubleshooting Decision Tree

```ascii
                    ┌─────────────────┐
                    │  Issue Report   │
                    └────────┬────────┘
                            │
              ┌────────────┴───────────┐
              │   Service Available?    │
              └────────────┬───────────┘
         No               │              Yes
    ┌─────────┐          │          ┌──────────┐
    │         │          │          │          │
    ▼         │          ▼          │          ▼
┌─────────┐   │   ┌───────────┐     │    ┌──────────┐
│ Network │   │   │  Storage  │     │    │ Access   │
│ Issue?  │   │   │  Issue?   │     │    │ Issue?   │
└────┬────┘   │   └─────┬─────┘     │    └────┬─────┘
     │        │         │           │         │
   Check:     │       Check:        │       Check:
┌────┴────┐   │   ┌─────┴─────┐    │    ┌────┴────┐
│• Network│   │   │• Mount     │    │    │• User    │
│  Status │   │   │  Status   │    │    │  Auth    │
│• IP     │   │   │• Disk     │    │    │• Share   │
│  Config │   │   │  Space    │    │    │  Perms   │
│• DNS    │   │   │• IO       │    │    │• Firewall│
└────┬────┘   │   └─────┬─────┘    │    └────┬────┘
     │        │         │          │         │
     └────────┴─────────┴──────────┴─────────┘
                        │
                        ▼
               ┌─────────────────┐
               │ Apply Solution  │
               │ from Relevant  │
               │ Section Above  │
               └─────────────────┘
```

### 8. Support and Updates

For support or updates:

- Check system logs: `journalctl -xe`
- Monitor service status: `systemctl status service_name`
- Contact system administrator for assistance

## Appendix: Quick Reference

### Important Paths

- SMB Shares: `/mnt/pool0/share1`
- NFS Exports: `/mnt/nfs_share`
- Configuration: `/etc/samba/smb.conf`, `/etc/exports`

### Common Commands

```bash
# Check service status
systemctl status service_name

# View logs
journalctl -u service_name

# Check mounts
df -h
mount

# Monitor system
top
htop (if installed)
```

### Default Ports

- SMB: 445
- NFS: 2049
- FTP: 21
- iSCSI: 3260
- SSH: 22

## Detailed Component Diagrams

### Storage Component Architecture

```ascii
┌─────────────────────────────────────────────────────┐
│                Storage Management                   │
│                                                     │
│  ┌─────────────┐         ┌─────────────────────┐   │
│  │ Mount Points│◄────────│ Storage Manager     │   │
│  │ Management  │         │ - Mount operations   │   │
│  └─────────────┘         │ - Status monitoring  │   │
│         ▲               │ - Auto recovery      │   │
│         │               └─────────────────────┘   │
│         │                        ▲                │
│  ┌──────┴────────┐      ┌──────┴─────────┐      │
│  │ Pool0         │      │ Tank           │      │
│  │ (/mnt/pool0)  │      │ (/mnt/tank)    │      │
│  └──────┬────────┘      └──────┬─────────┘      │
│         │                       │                │
│    ┌────┴───────────────────────┴────┐          │
│    │        Physical Storage         │          │
│    └──────────────────────────────────┘          │
└─────────────────────────────────────────────────────┘
```

### Network Services Architecture

```ascii
┌────────────────────────────────────────────────────┐
│              Network Services Layer                │
│                                                    │
│  ┌──────────────┐    ┌─────────────┐   ┌───────┐  │
│  │ SMB Manager  │    │ NFS Manager │   │ FTP   │  │
│  │ - Auth       │    │ - Exports   │   │Service│  │
│  │ - Shares     │    │ - Mounts    │   │       │  │
│  └───────┬──────┘    └──────┬──────┘   └───┬───┘  │
│          │                   │              │      │
│  ┌───────┴───────────────────┴──────────────┴───┐  │
│  │            Access Control Layer             │  │
│  │     (Permissions, Users, Groups)            │  │
│  └───────────────────────┬───────────────────┘  │
│                          │                       │
│  ┌────────────────────────────────────────────┐  │
│  │            Network Interface               │  │
│  │          eth0 (172.16.135.130)            │  │
│  └────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

## Common Tasks Quick Reference

### 1. User Management Tasks

```ascii
┌────────────────────┐
│ Add New User       │
├────────────────────┤
│ 1. Create User     │
│ 2. Set Password    │
│ 3. Add to Groups   │
│ 4. Set Permissions │
└────────────────────┘
```

### 2. Share Management Tasks

```ascii
┌────────────────────┐
│ Create New Share   │
├────────────────────┤
│ 1. Create Dir      │
│ 2. Set Ownership   │
│ 3. Configure Share │
│ 4. Set Permissions │
└────────────────────┘
```

### 3. Maintenance Tasks

```ascii
┌────────────────────┐
│ System Maintenance │
├────────────────────┤
│ 1. Check Logs      │
│ 2. Update System   │
│ 3. Verify Services │
│ 4. Check Storage   │
└────────────────────┘
```
