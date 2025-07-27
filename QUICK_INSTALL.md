# MoxNAS Quick Installation Guide

## 🚀 One-Line Installation

### Default Installation (Container ID 200)

```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install_moxnas.sh | bash
```

### Custom Container ID

```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install_moxnas.sh | bash -s 201
```

## 🔧 Troubleshooting

### If Installation Fails

Run the diagnostic helper to analyze your Proxmox configuration:

```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/manual_install_helper.sh | bash
```

### Debug Storage Issues

If you get "no such logical volume" errors:

```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/debug_proxmox_storage.sh | bash
```

## 📋 What the Installation Does

1. **Detects your Proxmox storage configuration**
2. **Downloads Ubuntu 22.04 LXC template**
3. **Creates LXC container with optimal settings**
4. **Installs all NAS services (SMB, NFS, FTP, SSH, SNMP, iSCSI)**
5. **Sets up MoxNAS web interface**
6. **Configures systemd service for auto-start**

## 🌐 Access After Installation

1. **Get container IP:**
   ```bash
   CONTAINER_IP=$(pct exec 200 -- hostname -I | awk '{print $1}')
   echo "Access MoxNAS: http://$CONTAINER_IP:8000"
   ```

2. **Default Login:**
   - Username: `admin`
   - Password: `moxnas123`

## ⚙️ Post-Installation Configuration

### Add Storage to Container

```bash
# Add host storage to container
pct set 200 -mp0 /host/storage/path,mp=/mnt/storage

# Restart container to apply changes
pct restart 200
```

### Configure Proxmox Integration

```bash
# Run quick setup for Proxmox credentials
pct exec 200 -- /opt/moxnas/quick_setup.sh
```

## 🔍 Manual Installation (If Automated Fails)

If the automated installation fails, use the manual helper:

```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/manual_install_helper.sh | bash
```

This will show you the exact commands to run manually based on your Proxmox configuration.

## 📊 Container Management

```bash
# Start container
pct start 200

# Stop container  
pct stop 200

# Access container shell
pct enter 200

# Check MoxNAS service status
pct exec 200 -- systemctl status moxnas

# View MoxNAS logs
pct exec 200 -- journalctl -u moxnas -f
```

## ✅ Verification

After installation, verify MoxNAS is working:

1. **Check container status:** `pct status 200`
2. **Check MoxNAS service:** `pct exec 200 -- systemctl status moxnas`
3. **Access web interface:** `http://[container-ip]:8000`
4. **Test NAS services:** SMB, NFS, FTP connections

---

**Need help?** The diagnostic scripts will provide detailed information about your Proxmox configuration and recommend the best installation approach.