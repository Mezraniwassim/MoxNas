# MoxNas - Professional NAS Management for Proxmox

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Proxmox](https://img.shields.io/badge/Proxmox-VE%208.0+-red.svg)](https://www.proxmox.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-blue.svg)](https://reactjs.org)

**Enterprise-grade Network Attached Storage solution designed specifically for Proxmox Virtual Environment**

🚀 Deploy complete NAS functionality in LXC containers with modern web management interface

# 🚀 One-Command Installation

## Quick Install (Recommended)

Copy and paste this single command on your Proxmox host as root:

```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas.sh | bash
```

## Alternative Installation Methods

### Auto-install (No prompts)
```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas.sh | bash -s -- --auto
```

### Download and inspect first
```bash
wget https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install-moxnas.sh
chmod +x install-moxnas.sh
./install-moxnas.sh
```

## What It Does

✅ **Auto-detects** your Proxmox environment  
✅ **Creates** optimized LXC container  
✅ **Installs** complete MoxNas system  
✅ **Configures** all services automatically  
✅ **Tests** installation  

## After Installation

- **Web Interface**: `http://[CONTAINER_IP]:8000`
- **Login**: `admin` / `admin123`
- **Change password immediately!`

## Requirements

- Proxmox VE 8.0+
- 4GB+ RAM recommended
- 10GB+ storage space
- Internet connection

## Features

- **Web Dashboard** - Modern React interface
- **Proxmox Integration** - Manage containers directly
- **NAS Services** - SSH, FTP, SMB, NFS
- **Storage Management** - Datasets, shares, ACLs
- **User Management** - Accounts and permissions
- **Real-time Monitoring** - Resource usage and status

## Manual Installation

```bash
# Clone the repository
git clone https://github.com/Mezraniwassim/MoxNas.git
cd MoxNas

# Run the installation script from Proxmox host
./scripts/install_moxnas.sh [container_id]
```

## Configuration

Copy `.env.example` to `.env` and configure your Proxmox credentials:

```bash
PROXMOX_HOST=your-proxmox-host
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your-password
PROXMOX_PORT=8006
```

## Manual Testing

```bash
# Run comprehensive tests
./scripts/test_moxnas.sh [CONTAINER_ID]

# Check service status
pct exec [CONTAINER_ID] -- systemctl status moxnas

# View logs
pct exec [CONTAINER_ID] -- journalctl -u moxnas -f
```

## Troubleshooting

If issues occur:

```bash
# Restart services
pct exec [CONTAINER_ID] -- /opt/moxnas/start_service.sh

# Check container resources
pct config [CONTAINER_ID]

# Monitor memory usage
pct exec [CONTAINER_ID] -- free -h
```

## Development

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## Services

- **Dashboard**: Container and service management
- **Storage**: Dataset and share management
- **Services**: FTP, NFS, SSH, SMB configuration
- **Access Control**: User and permission management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License