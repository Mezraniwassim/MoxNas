# MoxNas One-Click Installation for Alex

## Quick Start (One Command)

Run this single command on your Proxmox host as root:

```bash
curl -sSL https://raw.githubusercontent.com/your-repo/MoxNas/main/install_for_alex.sh | bash
```

Or download and run locally:

```bash
wget https://raw.githubusercontent.com/your-repo/MoxNas/main/install_for_alex.sh
chmod +x install_for_alex.sh
./install_for_alex.sh
```

## What This Script Does

The installation script **automatically**:

1. **Detects your Proxmox environment:**
   - Available storage (local-lvm, etc.)
   - Network bridges (vmbr0, etc.)
   - Available memory and CPU cores
   - Next available container ID

2. **Creates optimized container:**
   - Ubuntu 22.04 LXC container
   - 3GB+ RAM (prevents build failures)
   - Proper CPU allocation
   - Nested virtualization enabled

3. **Installs complete MoxNas system:**
   - Django backend with Proxmox API
   - React frontend dashboard
   - PostgreSQL database
   - NAS services (SSH, FTP, SMB, NFS)
   - Nginx web server

4. **Configures everything:**
   - Database setup with admin user
   - System services and startup scripts
   - Network accessibility
   - Service monitoring

5. **Tests installation:**
   - Web interface accessibility
   - API endpoint responses
   - Service status checks
   - Database connectivity

## After Installation

The script will display:
- Container ID and IP address
- Web interface URL: `http://[CONTAINER_IP]:8000`
- Admin login: `admin / admin123`

## Addresses Alex's Issues

This installation specifically fixes:
- ✅ **Memory build failures:** 3GB+ RAM allocation
- ✅ **Service startup issues:** Enhanced systemd configuration
- ✅ **Missing functionality:** Complete ACLs, datasets, shares
- ✅ **Network problems:** Auto-detected bridge configuration
- ✅ **Installation complexity:** Single command deployment

## Troubleshooting

If you encounter issues:

```bash
# Check container status
pct status [CONTAINER_ID]

# Check MoxNas service
pct exec [CONTAINER_ID] -- systemctl status moxnas

# View logs
pct exec [CONTAINER_ID] -- journalctl -u moxnas -f

# Restart service
pct exec [CONTAINER_ID] -- /opt/moxnas/start_service.sh
```

## Manual Configuration

After installation, access the web interface and:
1. Go to Settings → Proxmox
2. Enter your Proxmox credentials
3. Configure storage and network settings
4. Create NAS users and shares

The system is ready to use immediately!