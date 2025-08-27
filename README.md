# MoxNAS - Professional Network Attached Storage for Proxmox

![MoxNAS Logo](https://img.shields.io/badge/MoxNAS-v1.0.0-blue?style=for-the-badge&logo=database)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.3+-red?style=for-the-badge&logo=flask)

## 🚀 Overview

MoxNAS is a comprehensive, enterprise-grade Network Attached Storage (NAS) solution specifically designed for Proxmox LXC containers. Built with security, performance, and reliability as core principles, MoxNAS provides TrueNAS-like functionality with a modern web interface and professional-grade features.

### 🎯 Key Features

- **🛡️ Enterprise Security**: Multi-factor authentication, CSRF protection, rate limiting, audit logging
- **💾 Advanced Storage Management**: RAID 0/1/5/10 support, SMART monitoring, automated health checks
- **🔗 Network Sharing**: SMB/CIFS, NFS, FTP/SFTP protocols with granular access control
- **📊 Real-time Monitoring**: System metrics, storage health, performance analytics
- **🔄 Backup Management**: Scheduled backups, encryption, retention policies
- **📱 Responsive Interface**: Modern Bootstrap 5 UI with mobile support
- **🔧 RESTful API**: Comprehensive API for automation and integration
- **⚡ Background Processing**: Celery-based task queue for long-running operations

## 🏗️ Architecture

```text
MoxNAS/
├── app/                          # Flask application
│   ├── auth/                     # Authentication system
│   ├── storage/                  # Storage management
│   ├── shares/                   # Network shares
│   ├── backups/                  # Backup management
│   ├── monitoring/               # System monitoring
│   ├── api/                      # REST API
│   ├── templates/                # HTML templates
│   ├── static/                   # CSS, JS, images
│   └── models.py                 # Database models
├── migrations/                   # Database migrations
├── tests/                        # Unit tests
├── config.py                     # Configuration
├── requirements.txt              # Dependencies
├── wsgi.py                       # WSGI entry point
├── celery_worker.py              # Celery worker
└── install.sh                    # Installation script
```

## 🛠️ Technology Stack

- **Backend**: Flask 2.3+ with Blueprint architecture
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Task Queue**: Celery with Redis broker
- **Frontend**: Bootstrap 5, Chart.js, vanilla JavaScript
- **Security**: Flask-WTF (CSRF), Flask-Login, Flask-Limiter
- **Storage**: mdadm (RAID), LVM, ext4/XFS filesystems
- **Protocols**: Samba (SMB), NFS-kernel-server, vsftpd
- **Monitoring**: psutil, SMART tools, custom collectors

## 📋 Requirements

### System Requirements

- **OS**: Debian 11+ / Ubuntu 20.04+ LXC container
- **RAM**: Minimum 2GB, recommended 4GB+
- **Storage**: 10GB+ for system, additional for data storage
- **CPU**: 2+ cores recommended

### Software Dependencies

- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- Nginx
- Supervisor

## 🚀 Quick Installation

### 1. Automated Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/moxnas.git
cd moxnas

# Run the installation script as root
sudo ./install.sh
```

### 2. Manual Installation

```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip python3-venv postgresql redis-server nginx supervisor

# Setup application
cd /opt/moxnas
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize database
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

## 💻 Usage

### Web Interface

1. Access MoxNAS at `https://your-server-ip`
2. Login with admin credentials (created during installation)
3. Navigate through the intuitive web interface:
   - **Dashboard**: System overview and real-time metrics
   - **Storage**: Manage devices, pools, and datasets
   - **Shares**: Configure network shares (SMB, NFS, FTP)
   - **Backups**: Schedule and monitor backup jobs
   - **Monitoring**: View system performance and logs

### API Access

```bash
# Authentication
POST /api/auth/login
POST /api/auth/logout

# Storage Management  
GET  /api/storage/devices
POST /api/storage/pools
GET  /api/storage/pools/{id}

# Share Management
GET  /api/shares
POST /api/shares
PUT  /api/shares/{id}

# Monitoring
GET /api/monitoring/system
GET /api/monitoring/storage
```

## 🛡️ Security Features

### Authentication & Authorization

- **Strong Password Policies**: Minimum 8 characters, mixed case, numbers, symbols
- **Account Lockout**: 5 failed attempts = 30 minute lockout
- **Two-Factor Authentication**: TOTP support with QR codes
- **Session Management**: 8-hour timeout, secure cookies
- **Role-Based Access**: Admin and user roles with proper authorization

### Security Measures

- **CSRF Protection**: All forms protected with CSRF tokens
- **Rate Limiting**: Login attempts and API calls rate limited
- **Input Validation**: Comprehensive validation on all inputs
- **SQL Injection Prevention**: Parameterized queries only
- **XSS Protection**: All user input escaped in templates
- **Audit Logging**: All actions logged with user context

## 📊 Monitoring & Alerting

### Real-time Metrics

- CPU, memory, and disk usage
- Network interface statistics
- Storage pool health and usage
- SMART data for all devices
- Active network connections

### Alerting System

- Email notifications for critical events
- SMART failure alerts
- Storage capacity warnings
- System performance alerts
- Configurable alert thresholds

## 🔄 Backup & Recovery

### Backup Features

- **Scheduled Backups**: Cron-based scheduling
- **Multiple Targets**: Local, remote, and cloud destinations
- **Encryption**: AES encryption for backup data
- **Incremental Backups**: Space-efficient incremental backups
- **Retention Policies**: Automatic cleanup of old backups
- **Restore Interface**: Easy data recovery through web UI

## 🧪 Testing

```bash
# Run unit tests
cd /opt/moxnas
source venv/bin/activate
python -m pytest tests/ -v

# Coverage report
python -m pytest --cov=app tests/
```

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [User Manual](docs/user-guide.md)
- [API Documentation](docs/api.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🤝 Contributing

We welcome contributions! Please see our Contributing Guidelines for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/moxnas/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/moxnas/discussions)

---

**MoxNAS** - Professional Network Attached Storage for the Modern Data Center

Made with ❤️ for the Proxmox community