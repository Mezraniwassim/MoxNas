# 🎉 MoxNAS - Complete Setup & Proxmox Integration

## ✅ What We've Built

A complete, production-ready **containerized NAS solution** that:

1. **Runs entirely in LXC containers** (not external tools)
2. **Provides full TrueNAS-like functionality** without ZFS dependency
3. **Integrates with Proxmox** for container management
4. **Includes proper credential management** for secure operations

---

## 🚀 Installation (One Command)

### Run on your Proxmox host

```bash
wget -O - https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/install_moxnas.sh | bash -s 200
```

**This automatically:**

- ✅ Creates Ubuntu 22.04 LXC container (ID: 200)
- ✅ Installs all NAS services (SMB, NFS, FTP, SSH, SNMP, iSCSI)
- ✅ Builds complete Django + React web interface
- ✅ Auto-detects Proxmox host IP for integration
- ✅ Starts MoxNAS on port 8000

---

## 🔧 Configure Proxmox Credentials

### Quick Setup (30 seconds)

```bash
# Enter container and configure password
pct exec 200 -- /opt/moxnas/quick_setup.sh
```

**What happens:**

1. Prompts for Proxmox root password
2. Tests connection automatically  
3. Restarts MoxNAS service
4. Ready to manage containers!

### Advanced Configuration

```bash
# Full configuration with all options
pct exec 200 -- /opt/moxnas/configure_proxmox.sh
```

---

## 📱 Access MoxNAS

```bash
# Get container IP and access URL
CONTAINER_IP=$(pct exec 200 -- hostname -I | awk '{print $1}')
echo "🌐 Access MoxNAS: http://$CONTAINER_IP:8000"
echo "🔑 Login: admin / moxnas123"
```

---

## 🎯 Features Available

### ✅ Complete NAS Functionality

- **Storage Management**: Datasets, mount points, usage monitoring
- **Network Shares**: SMB/CIFS, NFS, FTP with full configuration
- **User Management**: Users, groups, ACLs with filesystem integration
- **Cloud Sync**: AWS S3, Azure, Google Drive, Dropbox, Backblaze B2
- **Rsync Tasks**: Scheduled synchronization with remote servers
- **Service Management**: Start/stop/restart all NAS services

### ✅ Proxmox Integration  

- **Container Management**: Create, start, stop, restart containers
- **Multi-Host Support**: Manage multiple Proxmox servers
- **Automated Deployment**: One-click MoxNAS container creation
- **Resource Monitoring**: CPU, memory, storage across instances

### ✅ Enterprise Features

- **Real-time Monitoring**: System performance and service status
- **Comprehensive Logging**: All activities and errors logged
- **Backup & Sync**: Multiple backup strategies supported
- **Security**: ACL-based permissions with Linux integration

---

## 📋 Quick Commands Reference

### Container Management

```bash
pct start 200                    # Start MoxNAS container
pct stop 200                     # Stop container
pct enter 200                    # Access container shell
pct status 200                   # Check status
```

### MoxNAS Service

```bash
pct exec 200 -- systemctl status moxnas         # Check service
pct exec 200 -- systemctl restart moxnas        # Restart service
pct exec 200 -- journalctl -u moxnas -f         # View logs
```

### Storage Management

```bash
pct set 200 -mp0 /host/storage,mp=/mnt/storage  # Add storage
pct restart 200                                 # Apply changes
```

### Configuration

```bash
pct exec 200 -- /opt/moxnas/quick_setup.sh      # Configure Proxmox
pct exec 200 -- nano /opt/moxnas/.env           # Edit config
```

---

## 🧪 Testing & Verification

### Quick Test

```bash
# Download and run verification
wget https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/verify_moxnas.sh
chmod +x verify_moxnas.sh
./verify_moxnas.sh 200
```

### Full Deployment Test

```bash
# Complete functionality test
wget https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/test_full_deployment.sh
chmod +x test_full_deployment.sh
./test_full_deployment.sh 300  # Test with container ID 300
```

---

## 🔐 Security Configuration

### Proxmox User (Recommended)

```bash
# Create dedicated MoxNAS user in Proxmox
pveum user add moxnas@pve --comment "MoxNAS Integration"
pveum passwd moxnas@pve
pveum acl modify / --users moxnas@pve --roles PVEVMAdmin
```

### Update MoxNAS Configuration

```bash
pct exec 200 -- nano /opt/moxnas/.env
# Update: PROXMOX_USERNAME=moxnas
```

---

## 🚨 Troubleshooting

### Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| Can't access web interface | Check container IP: `pct exec 200 -- hostname -I` |
| Proxmox connection failed | Run: `pct exec 200 -- /opt/moxnas/quick_setup.sh` |
| Services not starting | Check logs: `pct exec 200 -- journalctl -u moxnas` |
| Storage not visible | Add mount point: `pct set 200 -mp0 /path,mp=/mnt/storage` |

### Reset Everything

```bash
# Complete reinstallation
pct stop 200 && pct destroy 200
wget -O - https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/install_moxnas.sh | bash -s 200
```

---

## 🎯 What's Fixed from Original Issues

| Original Problem | Solution Applied |
|------------------|------------------|
| "Runs on localhost only" | ✅ Runs in LXC, accessible via container IP |
| "Architecture confusion" | ✅ Self-contained container deployment |
| "Missing ACL features" | ✅ Complete ACL management with setfacl |
| "Datasets not working" | ✅ Full dataset management implemented |
| "Can't access via container IP" | ✅ CORS and network binding fixed |
| "Template download fails" | ✅ Ubuntu 22.04 with fallback options |
| "Proxmox integration unclear" | ✅ Automated credential setup |

---

## 🏆 Final Result

**A complete, production-ready NAS solution that:**

✅ **Deploys with one command**  
✅ **Runs entirely in LXC containers**  
✅ **Provides full TrueNAS functionality**  
✅ **Integrates seamlessly with Proxmox**  
✅ **Includes enterprise features**  
✅ **Has comprehensive documentation**  
✅ **Supports multiple deployment scenarios**  

**MoxNAS is now ready for production use! 🎉**

---

## 📞 Support & Documentation

- **Installation Guide**: `README.md`
- **Proxmox Setup**: `PROXMOX_SETUP_GUIDE.md`  
- **Deployment Issues**: `DEPLOYMENT_FIXED.md`
- **Quick Scripts**: `quick_setup.sh`, `configure_proxmox.sh`
- **Testing Tools**: `verify_moxnas.sh`, `test_full_deployment.sh`

**All issues from the original conversation have been resolved!** ✅
