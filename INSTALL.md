# 🚀 MoxNas One-Command Installation Guide

## Quick Start

### **Option 1: Ultra-Quick Install (Recommended)**
```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/quick-install.sh | bash
```

### **Option 2: Full Installer**
```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas.sh | bash
```

### **Option 3: Manual Download & Run**
```bash
# Download installer
wget https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas.sh

# Make executable
chmod +x install-moxnas.sh

# Run installer
./install-moxnas.sh
```

## 📋 Prerequisites

- **Proxmox VE 8.0+** (running as root)
- **4GB+ RAM** (minimum 2GB)
- **10GB+ free disk space**
- **Internet connection** for downloading packages
- **Available LXC container ID** (script auto-detects)

## 🎯 What the Installer Does

### **Environment Detection**
- ✅ Validates Proxmox VE environment
- ✅ Detects optimal storage pool (local-lvm, local-zfs, etc.)
- ✅ Finds available network bridge (vmbr0, vmbr1, etc.)
- ✅ Calculates optimal resource allocation
- ✅ Selects next available container ID (200+)

### **Container Creation**
- ✅ Downloads Ubuntu 22.04 LTS template
- ✅ Creates LXC container with optimized settings
- ✅ Configures networking (DHCP by default)
- ✅ Enables container features (nesting, keyctl, mount)

### **Software Installation**
- ✅ System packages (Python, Node.js, PostgreSQL, Nginx, etc.)
- ✅ MoxNas application from GitHub
- ✅ Frontend build process
- ✅ Database initialization
- ✅ Service configuration

### **Service Setup**
- ✅ Systemd services for MoxNas
- ✅ Nginx reverse proxy
- ✅ PostgreSQL database
- ✅ Redis caching (optional)
- ✅ NAS services (SSH, FTP, SMB, NFS)

### **Security Configuration**
- ✅ Secure service configurations
- ✅ Firewall-friendly setup
- ✅ Process isolation
- ✅ Log rotation

## 📊 Installation Options

### **Interactive Mode (Default)**
```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas.sh | bash
```
- Shows installation summary
- Asks for confirmation before proceeding
- Provides detailed progress information

### **Automated Mode**
```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas.sh | bash -s -- --auto
```
- No user interaction required
- Ideal for scripted deployments
- Uses optimal detected settings

## 🎨 Installation Output

The installer provides:
- 🎨 **Colorful progress indicators**
- 📊 **Real-time status updates**
- ⏱️ **Progress bars for long operations**
- 📝 **Detailed logging** (saved to `/tmp/moxnas-install.log`)
- ✅ **Success confirmations**
- ⚠️ **Warning notifications**
- 🚨 **Clear error messages**

## 📋 Post-Installation

After successful installation:

### **Access Information**
- **Web Interface:** `http://[CONTAINER_IP]:80`
- **Default Login:** `admin` / `admin123`
- **Container ID:** Auto-assigned (200+)

### **First Steps**
1. **Change default password** (important!)
2. **Configure Proxmox connection** in Settings
3. **Set up storage pools** and datasets
4. **Create user accounts** and permissions
5. **Configure NAS services** (SMB, NFS, etc.)

### **Container Management**
```bash
# Check container status
pct status [CONTAINER_ID]

# Start/stop container
pct start [CONTAINER_ID]
pct stop [CONTAINER_ID]

# Access container console
pct enter [CONTAINER_ID]

# Check MoxNas service status
pct exec [CONTAINER_ID] -- systemctl status moxnas
```

## 🔧 Troubleshooting

### **Common Issues**

#### **Installation Fails**
```bash
# Check installation log
cat /tmp/moxnas-install.log

# Verify Proxmox version
pveversion

# Check available storage
pvesm status

# Verify internet connectivity
ping 8.8.8.8
```

#### **Web Interface Not Accessible**
```bash
# Check container IP
pct exec [CONTAINER_ID] -- hostname -I

# Check service status
pct exec [CONTAINER_ID] -- systemctl status moxnas nginx

# Check firewall
pct exec [CONTAINER_ID] -- netstat -tlpn | grep 80
```

#### **Service Issues**
```bash
# Check MoxNas logs
pct exec [CONTAINER_ID] -- journalctl -u moxnas -f

# Check Nginx logs
pct exec [CONTAINER_ID] -- tail -f /var/log/nginx/error.log

# Restart services
pct exec [CONTAINER_ID] -- systemctl restart moxnas nginx
```

### **Recovery Options**

#### **Reinstall MoxNas in Existing Container**
```bash
# Download repair script
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/scripts/repair-install.sh | bash -s [CONTAINER_ID]
```

#### **Complete Removal**
```bash
# Stop and remove container
pct stop [CONTAINER_ID]
pct destroy [CONTAINER_ID]

# Run installer again
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas.sh | bash
```

## 📚 Advanced Configuration

### **Custom Installation Parameters**

Create a configuration file before installation:
```bash
# Create custom config
cat > /tmp/moxnas-config << EOF
CONTAINER_MEMORY=4096
CONTAINER_CORES=4
CONTAINER_STORAGE=local-zfs
NETWORK_BRIDGE=vmbr1
ADMIN_PASSWORD=your_secure_password
EOF

# Run installer with custom config
MOXNAS_CONFIG=/tmp/moxnas-config ./install-moxnas.sh
```

### **Production Deployment**

For production environments:
```bash
# Use production installer
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-production.sh | bash
```

This includes:
- SSL/TLS certificate setup
- Enhanced security configurations
- Monitoring and alerting
- Backup automation
- Performance optimization

## 🆘 Support

- **📚 Documentation:** [GitHub Wiki](https://github.com/Mezraniwassim/MoxNas/wiki)
- **🐛 Bug Reports:** [GitHub Issues](https://github.com/Mezraniwassim/MoxNas/issues)
- **💬 Discussions:** [GitHub Discussions](https://github.com/Mezraniwassim/MoxNas/discussions)
- **📧 Security Issues:** security@moxnas.local

## 🏷️ License

MIT License - see [LICENSE](LICENSE) file for details.

---

**MoxNas** - Professional NAS Management for Proxmox VE
