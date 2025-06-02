# MoxNAS - Streamlined NAS for LXC Containers

MoxNAS is a lightweight Network Attached Storage solution based on TrueNAS Scale, specifically designed to run in LXC containers on Proxmox.

## Features

- **Core NAS Services**: SMB, NFS, FTP, iSCSI
- **Management Services**: SSH, SNMP, UPS support
- **Web Interface**: Modern web UI for configuration and monitoring
- **Storage**: Mount-point based (no ZFS dependency)
- **Containerized**: Optimized for LXC deployment

## Project Structure

```
MoxNAS/
├── backend/           # Python backend services
├── frontend/          # Web UI
├── services/          # Core NAS services configuration
├── deployment/        # LXC and Proxmox deployment scripts
├── tests/            # Test suites
└── docs/             # Documentation
```

## Quick Start

1. Clone the repository
2. Run the deployment script for Proxmox
3. Configure services through the web interface

## Requirements

- Proxmox VE 8.4+
- LXC container support
- Mount points for storage

## License

Open Source - Based on TrueNAS Scale
