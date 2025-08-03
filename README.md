# MoxNas - NAS Management for Proxmox

Complete NAS solution running in LXC containers on Proxmox VE.

## One-Command Installation

Run this single command on your Proxmox host as root:

```bash
curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/quick-install.sh | bash
```

Or download and run locally:

```bash
wget https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/quick-install.sh
chmod +x quick-install.sh
./quick-install.sh
```

## What It Does

The installation script automatically:

✅ **Detects your environment** - storage, network, resources  
✅ **Creates optimized container** - 3GB+ RAM, proper CPU allocation  
✅ **Installs complete system** - Django backend, React frontend, NAS services  
✅ **Configures everything** - database, services, network  
✅ **Tests installation** - ensures everything works  

## After Installation

Access your MoxNas at: `http://[CONTAINER_IP]:8000`  
Login: `admin / admin123`

## Features

- **Web Dashboard** - Modern React interface
- **Proxmox Integration** - Manage containers directly
- **NAS Services** - SSH, FTP, SMB, NFS
- **Storage Management** - Datasets, shares, ACLs
- **User Management** - Accounts and permissions
- **Real-time Monitoring** - Resource usage and status

## Alternative Installation Methods

### Manual Installation

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