# MoxNAS Proxmox Integration Setup Guide

## 🚀 Complete Setup Process

### Step 1: Install MoxNAS

```bash
# Run on your Proxmox host
wget -O - https://raw.githubusercontent.com/Mezraniwassim/MoxNas/main/install_moxnas.sh | bash -s 200
```

### Step 2: Configure Proxmox Credentials

#### Option A: Quick Setup (Recommended)

```bash
# Enter the container and run quick setup
pct exec 200 -- /opt/moxnas/quick_setup.sh
```

**What it does:**

- Prompts for your Proxmox root password
- Tests the connection
- Restarts MoxNAS service
- Ready to use!

#### Option B: Detailed Configuration

```bash
# For advanced configuration options
pct exec 200 -- /opt/moxnas/configure_proxmox.sh
```

**What it configures:**

- Proxmox host IP address
- Custom username (if not root)
- Custom realm (if not PAM)
- SSL certificate settings
- Connection testing

#### Option C: Manual Configuration

```bash
# Edit configuration directly
pct exec 200 -- nano /opt/moxnas/.env

# Add/update these lines:
PROXMOX_HOST=192.168.1.100
PROXMOX_PORT=8006
PROXMOX_USERNAME=root
PROXMOX_PASSWORD=your_password
PROXMOX_REALM=pam
PROXMOX_SSL_VERIFY=False

# Restart MoxNAS
pct exec 200 -- systemctl restart moxnas
```

### Step 3: Access MoxNAS

```bash
# Get container IP
CONTAINER_IP=$(pct exec 200 -- hostname -I | awk '{print $1}')
echo "Access: http://$CONTAINER_IP:8000"

# Default login: admin / moxnas123
```

## 🏢 Enterprise Setup (Multiple Proxmox Hosts)

For managing multiple Proxmox hosts, you can configure additional connections:

### Configuration File Format

```bash
# Edit: /opt/moxnas/config/proxmox.conf
[proxmox_primary]
host = 192.168.1.100
port = 8006
username = root
realm = pam
ssl_verify = False

[proxmox_secondary]  
host = 192.168.1.101
port = 8006
username = admin
realm = pve
ssl_verify = True
```

## 🔧 Configuration Parameters

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `PROXMOX_HOST` | Proxmox server IP | Auto-detected | `192.168.1.100` |
| `PROXMOX_PORT` | Web interface port | `8006` | `8006` |
| `PROXMOX_USERNAME` | Username | `root` | `root` or `admin` |
| `PROXMOX_PASSWORD` | Password | (empty) | `your_password` |
| `PROXMOX_REALM` | Authentication realm | `pam` | `pam` or `pve` |
| `PROXMOX_SSL_VERIFY` | Verify SSL certificates | `False` | `True`/`False` |

## 🧪 Testing Your Configuration

### Test Connection

```bash
# Quick connection test
pct exec 200 -- curl -k -d "username=root@pam&password=your_password" \
  "https://192.168.1.100:8006/api2/json/access/ticket"
```

### Test in MoxNAS Web Interface

1. Open `http://[container-ip]:8000`
2. Login with `admin` / `moxnas123`
3. Go to **Proxmox** tab
4. Click **Test Connection**
5. Should show green "Connected" status

### View Logs

```bash
# Check MoxNAS logs
pct exec 200 -- journalctl -u moxnas -f

# Check for connection errors
pct exec 200 -- grep -i proxmox /var/log/moxnas/moxnas.log
```

## 🔒 Security Best Practices

### 1. Use Dedicated User

```bash
# Create dedicated user in Proxmox for MoxNAS
pveum user add moxnas@pve --comment "MoxNAS Integration User"
pveum passwd moxnas@pve

# Grant necessary permissions
pveum acl modify / --users moxnas@pve --roles PVEVMAdmin
```

### 2. Enable SSL Verification

```bash
# If you have proper SSL certificates
PROXMOX_SSL_VERIFY=True
```

### 3. Restrict Network Access

```bash
# Use firewall rules to limit access
# Only allow MoxNAS container to access Proxmox API
```

## 🚨 Troubleshooting

### Common Issues

#### "Connection refused"

```bash
# Check if Proxmox is accessible
ping 192.168.1.100

# Check if port 8006 is open
telnet 192.168.1.100 8006
```

#### "Authentication failed"

```bash
# Verify credentials
pct exec 200 -- cat /opt/moxnas/.env | grep PROXMOX

# Test manually
curl -k -d "username=root@pam&password=wrong" \
  "https://192.168.1.100:8006/api2/json/access/ticket"
```

#### "SSL certificate verify failed"

```bash
# Disable SSL verification
PROXMOX_SSL_VERIFY=False

# Or install proper certificates
```

### Reset Configuration

```bash
# Remove all Proxmox settings
pct exec 200 -- sed -i '/^PROXMOX_/d' /opt/moxnas/.env

# Run setup again
pct exec 200 -- /opt/moxnas/quick_setup.sh
```

## 📱 Using MoxNAS Proxmox Features

Once configured, you can:

### Container Management

- **View all containers** on your Proxmox host
- **Create new MoxNAS containers** with one click
- **Start/stop/restart** containers remotely
- **Monitor resource usage** across containers

### Automated Deployment

- **Clone MoxNAS setup** to new containers
- **Bulk management** of multiple NAS instances
- **Resource scaling** based on demand

### Integration Features

- **Centralized monitoring** of all NAS instances
- **Unified user management** across containers
- **Backup and sync** between instances

## 🎯 Next Steps

1. ✅ **Install MoxNAS**: `wget -O - ... | bash`
2. ✅ **Configure Proxmox**: `/opt/moxnas/quick_setup.sh`
3. ✅ **Test Connection**: Web interface → Proxmox tab
4. 🚀 **Create Containers**: Use MoxNAS to deploy new instances
5. 📊 **Monitor & Manage**: Full container lifecycle management

Your MoxNAS is now ready for enterprise-grade Proxmox integration! 🎉
