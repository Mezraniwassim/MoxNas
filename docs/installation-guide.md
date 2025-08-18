# MoxNAS Installation Guide

## Overview

This guide provides step-by-step instructions for installing MoxNAS in various environments, from development setups to production deployments in Proxmox LXC containers.

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores (x86_64)
- **RAM**: 4GB
- **Storage**: 20GB system disk + storage for data
- **Network**: 1Gbps Ethernet recommended
- **OS**: Ubuntu 20.04+ or Debian 11+

### Recommended Requirements
- **CPU**: 4+ cores (x86_64)
- **RAM**: 8GB+
- **Storage**: 50GB system disk + dedicated storage drives
- **Network**: 10Gbps Ethernet for high-performance workloads
- **OS**: Ubuntu 22.04 LTS or Debian 12

### Supported Platforms
- ✅ Proxmox LXC containers (primary target)
- ✅ Docker containers
- ✅ Virtual machines (VMware, VirtualBox, KVM)
- ✅ Bare metal servers
- ✅ Cloud instances (AWS, GCP, Azure)

## Quick Installation

### Option 1: Automated Deployment Script (Recommended)

```bash
# Download and run the automated installer
curl -fsSL https://raw.githubusercontent.com/your-org/moxnas/main/scripts/deployment/deploy-moxnas.sh | bash

# Or download and review first
wget https://raw.githubusercontent.com/your-org/moxnas/main/scripts/deployment/deploy-moxnas.sh
chmod +x deploy-moxnas.sh
./deploy-moxnas.sh
```

### Option 2: Docker Installation

```bash
# Clone the repository
git clone https://github.com/your-org/moxnas.git
cd moxnas

# Create environment file
cp config/production/.env.example .env
# Edit .env with your settings

# Start with Docker Compose
docker-compose -f docker-compose.production.yml up -d
```

## Proxmox LXC Installation

### Step 1: Create LXC Container

1. **Download Ubuntu Template** (if not already available):
   ```bash
   # On Proxmox host
   pveam update
   pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
   ```

2. **Create Container**:
   ```bash
   pct create 200 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
     --hostname moxnas \
     --memory 4096 \
     --cores 4 \
     --rootfs local-lvm:20 \
     --net0 name=eth0,bridge=vmbr0,ip=dhcp \
     --unprivileged 1 \
     --features nesting=1
   ```

3. **Start Container**:
   ```bash
   pct start 200
   ```

### Step 2: Configure Container

1. **Enter Container**:
   ```bash
   pct enter 200
   ```

2. **Update System**:
   ```bash
   apt update && apt upgrade -y
   apt install -y curl wget git
   ```

3. **Run Installation Script**:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/your-org/moxnas/main/scripts/deployment/deploy-moxnas.sh | bash
   ```

### Step 3: Add Storage

1. **Stop Container**:
   ```bash
   pct stop 200
   ```

2. **Add Storage Disk**:
   ```bash
   # Add a 500GB disk for data storage
   pct set 200 -mp0 /mnt/data,mp=/mnt/data,size=500G
   ```

3. **Start Container**:
   ```bash
   pct start 200
   ```

## Manual Installation

### Step 1: System Preparation

1. **Update System**:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Dependencies**:
   ```bash
   sudo apt install -y \
     python3 python3-pip python3-venv \
     nodejs npm \
     nginx \
     postgresql postgresql-contrib \
     redis-server \
     git curl wget \
     samba nfs-kernel-server vsftpd \
     zfsutils-linux \
     systemd
   ```

3. **Create System User**:
   ```bash
   sudo useradd --system --home /opt/moxnas --shell /bin/bash moxnas
   sudo mkdir -p /opt/moxnas
   sudo chown moxnas:moxnas /opt/moxnas
   ```

### Step 2: Download and Setup MoxNAS

1. **Clone Repository**:
   ```bash
   sudo -u moxnas git clone https://github.com/your-org/moxnas.git /opt/moxnas
   cd /opt/moxnas
   ```

2. **Create Python Virtual Environment**:
   ```bash
   sudo -u moxnas python3 -m venv /opt/moxnas/venv
   sudo -u moxnas /opt/moxnas/venv/bin/pip install --upgrade pip
   sudo -u moxnas /opt/moxnas/venv/bin/pip install -r requirements.txt
   ```

3. **Install Frontend Dependencies**:
   ```bash
   cd /opt/moxnas/frontend
   sudo -u moxnas npm install
   sudo -u moxnas npm run build
   ```

### Step 3: Database Setup

1. **Create Database**:
   ```bash
   sudo -u postgres createuser moxnas
   sudo -u postgres createdb moxnas -O moxnas
   sudo -u postgres psql -c "ALTER USER moxnas PASSWORD 'secure-password';"
   ```

2. **Configure Database Connection**:
   ```bash
   cd /opt/moxnas
   sudo -u moxnas cp config/production/.env.example .env
   ```

   Edit `.env`:
   ```bash
   DATABASE_URL=postgresql://moxnas:secure-password@localhost/moxnas
   SECRET_KEY=your-very-long-random-secret-key-here
   DEBUG=False
   ALLOWED_HOSTS=localhost,127.0.0.1,your-server-ip
   ```

3. **Run Database Migrations**:
   ```bash
   cd /opt/moxnas/backend
   sudo -u moxnas ../venv/bin/python manage.py migrate
   sudo -u moxnas ../venv/bin/python manage.py collectstatic --noinput
   sudo -u moxnas ../venv/bin/python manage.py createsuperuser
   ```

### Step 4: Service Configuration

1. **Create Systemd Service**:
   ```bash
   sudo cp /opt/moxnas/services/moxnas.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable moxnas
   ```

2. **Configure Nginx**:
   ```bash
   sudo cp /opt/moxnas/config/nginx/moxnas.conf /etc/nginx/sites-available/
   sudo ln -s /etc/nginx/sites-available/moxnas.conf /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

3. **Start Services**:
   ```bash
   sudo systemctl start moxnas
   sudo systemctl start nginx
   ```

### Step 5: Initial Configuration

1. **Access Web Interface**:
   - Open browser to `http://your-server-ip`
   - Login with superuser credentials

2. **Run Initial Setup**:
   ```bash
   cd /opt/moxnas/backend
   sudo -u moxnas ../venv/bin/python manage.py validate_database --migrate --create-superuser
   ```

## Docker Installation

### Step 1: Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Step 2: Setup MoxNAS

1. **Clone Repository**:
   ```bash
   git clone https://github.com/your-org/moxnas.git
   cd moxnas
   ```

2. **Configure Environment**:
   ```bash
   cp config/production/.env.example .env
   # Edit .env file with your settings
   ```

3. **Build and Start**:
   ```bash
   docker-compose -f docker-compose.production.yml up -d
   ```

4. **Initialize Database**:
   ```bash
   docker-compose exec app python manage.py migrate
   docker-compose exec app python manage.py createsuperuser
   ```

### Step 3: Verify Installation

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Test health check
curl http://localhost:8000/api/system/health/
```

## Development Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/moxnas.git
cd moxnas
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database (SQLite for development)
python manage.py migrate
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### Step 3: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

### Step 4: Development Tools

```bash
# Run tests
./scripts/run_tests.sh

# Code formatting
black backend/
isort backend/

# Frontend linting
npm run lint
```

## Configuration

### Environment Variables

**Required Settings**:
```bash
# Security
SECRET_KEY=your-very-long-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Database
DATABASE_URL=postgresql://user:password@localhost/moxnas

# Cache
REDIS_URL=redis://localhost:6379/0

# Services
SAMBA_CONFIG_PATH=/etc/samba/smb.conf
NFS_EXPORTS_PATH=/etc/exports
FTP_CONFIG_PATH=/etc/vsftpd/vsftpd.conf
```

**Optional Settings**:
```bash
# Email notifications
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# Monitoring
PROMETHEUS_ENABLED=True
METRICS_RETENTION_DAYS=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/moxnas/moxnas.log

# Storage
DEFAULT_STORAGE_PATH=/mnt/storage
BACKUP_PATH=/mnt/backup
```

### SSL/TLS Configuration

1. **Generate SSL Certificate** (self-signed for testing):
   ```bash
   sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout /etc/ssl/private/moxnas.key \
     -out /etc/ssl/certs/moxnas.crt
   ```

2. **Configure Nginx for HTTPS**:
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;
       
       ssl_certificate /etc/ssl/certs/moxnas.crt;
       ssl_certificate_key /etc/ssl/private/moxnas.key;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-Proto https;
       }
   }
   ```

### Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 139/tcp     # Samba
sudo ufw allow 445/tcp     # Samba
sudo ufw allow 2049/tcp    # NFS
sudo ufw allow 21/tcp      # FTP
sudo ufw enable

# iptables (alternative)
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 139 -j ACCEPT
iptables -A INPUT -p tcp --dport 445 -j ACCEPT
iptables -A INPUT -p tcp --dport 2049 -j ACCEPT
```

## Post-Installation

### Step 1: Verify Installation

```bash
# Check service status
sudo systemctl status moxnas
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis

# Test web interface
curl http://localhost/api/system/health/

# Check logs
sudo journalctl -u moxnas -f
```

### Step 2: Create Storage Pool

1. Access web interface at `http://your-server-ip`
2. Login with admin credentials
3. Navigate to **Storage** → **Pools**
4. Click **Create Pool** and configure your storage

### Step 3: Configure Services

1. Navigate to **Services**
2. Configure Samba, NFS, and FTP services as needed
3. Create shares in **Shares** section

### Step 4: Setup Monitoring

1. Configure Prometheus (optional):
   ```bash
   # Install Prometheus
   wget https://github.com/prometheus/prometheus/releases/latest/download/prometheus-*.linux-amd64.tar.gz
   tar xzf prometheus-*.linux-amd64.tar.gz
   sudo mv prometheus-*/prometheus /usr/local/bin/
   
   # Configure and start
   sudo cp config/prometheus/prometheus.yml /etc/prometheus/
   sudo systemctl start prometheus
   ```

2. Setup Grafana (optional):
   ```bash
   sudo apt install -y software-properties-common
   sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
   sudo apt update && sudo apt install grafana
   sudo systemctl enable grafana-server
   sudo systemctl start grafana-server
   ```

## Backup and Recovery

### System Backup

```bash
# Backup configuration
sudo tar -czf moxnas-config-$(date +%Y%m%d).tar.gz \
  /opt/moxnas/.env \
  /etc/nginx/sites-available/moxnas.conf \
  /etc/systemd/system/moxnas.service

# Backup database
sudo -u postgres pg_dump moxnas > moxnas-db-$(date +%Y%m%d).sql
```

### Data Backup

```bash
# ZFS snapshots (if using ZFS)
zfs snapshot tank@backup-$(date +%Y%m%d)
zfs send tank@backup-$(date +%Y%m%d) | gzip > backup.gz

# rsync backup
rsync -av /mnt/storage/ /mnt/backup/
```

## Troubleshooting

### Common Issues

**Service Won't Start**:
```bash
# Check logs
sudo journalctl -u moxnas -n 50

# Check configuration
sudo -u moxnas /opt/moxnas/venv/bin/python /opt/moxnas/backend/manage.py check
```

**Database Connection Error**:
```bash
# Test database connection
sudo -u postgres psql -d moxnas -c "SELECT version();"

# Check credentials in .env file
cat /opt/moxnas/.env | grep DATABASE_URL
```

**Web Interface Not Accessible**:
```bash
# Check Nginx status
sudo systemctl status nginx
sudo nginx -t

# Check firewall
sudo ufw status
```

### Log Locations

- **Application logs**: `/var/log/moxnas/moxnas.log`
- **Nginx logs**: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- **System logs**: `sudo journalctl -u moxnas`
- **Database logs**: `/var/log/postgresql/`

### Performance Tuning

**Database Optimization**:
```sql
-- PostgreSQL settings in /etc/postgresql/*/main/postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
max_connections = 100
```

**Nginx Optimization**:
```nginx
# In /etc/nginx/nginx.conf
worker_processes auto;
worker_connections 1024;

# Enable compression
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

## Security Hardening

### System Security

```bash
# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Install fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban

# Setup automatic updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades
```

### Application Security

1. **Change default passwords**
2. **Enable two-factor authentication**
3. **Regular security updates**
4. **Monitor access logs**
5. **Use strong SSL/TLS configuration**

## Getting Help

- **Documentation**: Check the [User Guide](user-guide.md) and [Technical Documentation](technical-documentation.md)
- **Health Checks**: Use `/api/system/health/detailed/` endpoint
- **Logs**: Check application and system logs
- **Community**: Join the community forums
- **Support**: Contact support for enterprise deployments

For additional help, run the validation script:
```bash
python /opt/moxnas/final_validation.py
```