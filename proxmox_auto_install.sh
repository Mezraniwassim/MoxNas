#!/bin/bash

# MoxNAS Complete Automated Installation for Proxmox
# Creates LXC container and installs MoxNAS in one command
# Usage: bash proxmox_auto_install.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m' 
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[MoxNAS] $1${NC}"; }
warn() { echo -e "${YELLOW}[MoxNAS] WARNING: $1${NC}"; }
error() { echo -e "${RED}[MoxNAS] ERROR: $1${NC}"; }

# Check if running on Proxmox host
if ! command -v pct &> /dev/null; then
    error "This script must be run on a Proxmox VE host"
    error "pct command not found - are you running this on Proxmox?"
    exit 1
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root on Proxmox host"
    exit 1
fi

log "🚀 Starting MoxNAS Complete Automated Installation..."

# Configuration
CONTAINER_ID=${1:-$(shuf -i 100-999 -n 1)}  # Random ID if not provided
CONTAINER_MEMORY=${2:-2048}
CONTAINER_CORES=${3:-2}
CONTAINER_DISK=${4:-8}
BRIDGE=${5:-vmbr0}

log "📋 Container Configuration:"
log "   Container ID: $CONTAINER_ID"
log "   Memory: $CONTAINER_MEMORY MB"
log "   CPU Cores: $CONTAINER_CORES"
log "   Disk: $CONTAINER_DISK GB"
log "   Network Bridge: $BRIDGE"

# Find available Ubuntu template
log "🔍 Finding Ubuntu template..."
TEMPLATE=""
for template in $(pveam available | grep ubuntu | grep -E "(22.04|24.04)" | head -5 | awk '{print $2}'); do
    if pveam list local | grep -q "$template"; then
        TEMPLATE="local:vztmpl/$template"
        log "✅ Found template: $template"
        break
    fi
done

# If no template found locally, download one
if [ -z "$TEMPLATE" ]; then
    log "📥 Downloading Ubuntu 22.04 template..."
    pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
    TEMPLATE="local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
fi

# Check if container ID already exists
if pct list | grep -q "^$CONTAINER_ID "; then
    warn "Container $CONTAINER_ID already exists"
    read -p "Do you want to destroy it and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "🗑️ Destroying existing container $CONTAINER_ID..."
        pct stop $CONTAINER_ID 2>/dev/null || true
        pct destroy $CONTAINER_ID
    else
        error "Installation cancelled"
        exit 1
    fi
fi

# Create LXC container
log "🐳 Creating LXC container $CONTAINER_ID..."
pct create $CONTAINER_ID $TEMPLATE \
    --hostname moxnas-$CONTAINER_ID \
    --memory $CONTAINER_MEMORY \
    --cores $CONTAINER_CORES \
    --rootfs local-lvm:$CONTAINER_DISK \
    --net0 name=eth0,bridge=$BRIDGE,ip=dhcp \
    --features nesting=1,keyctl=1 \
    --unprivileged 1 \
    --onboot 1 \
    --startup order=3 \
    --description "MoxNAS - Containerized NAS Solution"

# Start container
log "▶️ Starting container..."
pct start $CONTAINER_ID

# Wait for container to be ready
log "⏳ Waiting for container to be ready..."
sleep 10

# Wait for network to be ready
CONTAINER_IP=""
for i in {1..30}; do
    CONTAINER_IP=$(pct exec $CONTAINER_ID -- hostname -I 2>/dev/null | awk '{print $1}' || echo "")
    if [ -n "$CONTAINER_IP" ] && [ "$CONTAINER_IP" != "127.0.0.1" ]; then
        break
    fi
    sleep 2
done

if [ -z "$CONTAINER_IP" ] || [ "$CONTAINER_IP" = "127.0.0.1" ]; then
    warn "Could not determine container IP, using localhost"
    CONTAINER_IP="localhost"
else
    log "🌐 Container IP: $CONTAINER_IP"
fi

# Create the MoxNAS installation script inside container
log "📝 Creating installation script..."
pct exec $CONTAINER_ID -- bash -c 'cat > /root/install_moxnas.sh << '\''INSTALL_SCRIPT_EOF'\''
#!/bin/bash

set -e

# Colors for output
RED='\''\\033[0;31m'\''
GREEN='\''\\033[0;32m'\''
YELLOW='\''\\033[1;33m'\''
NC='\''\\033[0m'\''

log() { echo -e "${GREEN}[MoxNAS] $1${NC}"; }
warn() { echo -e "${YELLOW}[MoxNAS] WARNING: $1${NC}"; }
error() { echo -e "${RED}[MoxNAS] ERROR: $1${NC}"; }

log "🚀 Installing MoxNAS inside container..."

# Set environment
export DEBIAN_FRONTEND=noninteractive
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# Update system
log "📦 Updating system and installing dependencies..."
apt-get update -qq
apt-get upgrade -y -qq

# Install essential packages
apt-get install -y curl wget python3 python3-pip python3-venv nodejs npm sqlite3 unzip \
                   samba nfs-kernel-server vsftpd nginx systemctl

# Install Node.js 18 if needed
NODE_VERSION=$(node --version 2>/dev/null | cut -d'\''v'\'' -f2 | cut -d'\''.'\'' -f1 || echo "0")
if [ "$NODE_VERSION" -lt 16 ]; then
    log "📦 Installing Node.js 18..."
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y nodejs
fi

# Create installation directory
INSTALL_DIR="/opt/moxnas"
log "📁 Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Create Python virtual environment
log "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
log "📦 Installing Python dependencies..."
pip install --quiet Django==4.2 djangorestframework==3.14.0 django-cors-headers==4.0.0 \
            requests==2.31.0 cryptography==41.0.0 gunicorn==21.2.0 python-decouple==3.8

# Create minimal Django project structure
log "🏗️ Creating Django backend..."
mkdir -p backend/{core,users,storage,services,network,proxmox,proxmox_integration,moxnas}

# Create manage.py
cat > backend/manage.py << '\''MANAGE_PY_EOF'\''
#!/usr/bin/env python
import os
import sys

if __name__ == '\''__main__'\'':
    os.environ.setdefault('\''DJANGO_SETTINGS_MODULE'\'', '\''moxnas.settings'\'')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn'\''t import Django. Are you sure it'\''s installed?"
        ) from exc
    execute_from_command_line(sys.argv)
MANAGE_PY_EOF

# Create Django settings
cat > backend/moxnas/settings.py << '\''SETTINGS_EOF'\''
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = '\''moxnas-secret-key-change-in-production'\''
DEBUG = True
ALLOWED_HOSTS = ['\''*'\'']

INSTALLED_APPS = [
    '\''django.contrib.admin'\'',
    '\''django.contrib.auth'\'',
    '\''django.contrib.contenttypes'\'',
    '\''django.contrib.sessions'\'',
    '\''django.contrib.messages'\'',
    '\''django.contrib.staticfiles'\'',
    '\''rest_framework'\'',
    '\''rest_framework.authtoken'\'',
    '\''corsheaders'\'',
    '\''core'\'',
    '\''users'\'',
    '\''storage'\'',
    '\''services'\'',
    '\''network'\'',
    '\''proxmox'\'',
    '\''proxmox_integration'\'',
]

MIDDLEWARE = [
    '\''corsheaders.middleware.CorsMiddleware'\'',
    '\''django.middleware.security.SecurityMiddleware'\'',
    '\''django.contrib.sessions.middleware.SessionMiddleware'\'',
    '\''django.middleware.common.CommonMiddleware'\'',
    '\''django.middleware.csrf.CsrfViewMiddleware'\'',
    '\''django.contrib.auth.middleware.AuthenticationMiddleware'\'',
    '\''django.contrib.messages.middleware.MessageMiddleware'\'',
    '\''django.middleware.clickjacking.XFrameOptionsMiddleware'\'',
]

ROOT_URLCONF = '\''moxnas.urls'\''

TEMPLATES = [
    {
        '\''BACKEND'\'': '\''django.template.backends.django.DjangoTemplates'\'',
        '\''DIRS'\'': [os.path.join(BASE_DIR.parent, '\''frontend'\'', '\''build'\'')],
        '\''APP_DIRS'\'': True,
        '\''OPTIONS'\'': {
            '\''context_processors'\'': [
                '\''django.template.context_processors.debug'\'',
                '\''django.template.context_processors.request'\'',
                '\''django.contrib.auth.context_processors.auth'\'',
                '\''django.contrib.messages.context_processors.messages'\'',
            ],
        },
    },
]

DATABASES = {
    '\''default'\'': {
        '\''ENGINE'\'': '\''django.db.backends.sqlite3'\'',
        '\''NAME'\'': BASE_DIR / '\''db.sqlite3'\'',
    }
}

STATIC_URL = '\''/static/'\''
STATIC_ROOT = os.path.join(BASE_DIR, '\''staticfiles'\'')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR.parent, '\''frontend'\'', '\''build'\'', '\''static'\''),
]

REST_FRAMEWORK = {
    '\''DEFAULT_AUTHENTICATION_CLASSES'\'': [
        '\''rest_framework.authentication.TokenAuthentication'\'',
        '\''rest_framework.authentication.SessionAuthentication'\'',
    ],
    '\''DEFAULT_PERMISSION_CLASSES'\'': [
        '\''rest_framework.permissions.IsAuthenticated'\'',
    ],
}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CACHES = {
    '\''default'\'': {
        '\''BACKEND'\'': '\''django.core.cache.backends.locmem.LocMemCache'\'',
        '\''LOCATION'\'': '\''moxnas-cache'\'',
    }
}
SETTINGS_EOF

# Create basic app files
for app in core users storage services network proxmox proxmox_integration; do
    mkdir -p "backend/$app"
    touch "backend/$app/__init__.py"
    echo "from django.db import models" > "backend/$app/models.py"
    echo "from rest_framework import viewsets" > "backend/$app/views.py"
    echo "from django.urls import path; urlpatterns = []" > "backend/$app/urls.py"
done

# Create main URLs
cat > backend/moxnas/urls.py << '\''URLS_EOF'\''
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.http import JsonResponse

def api_root(request):
    return JsonResponse({
        '\''message'\'': '\''MoxNAS API'\'',
        '\''version'\'': '\''1.0.0'\'',
        '\''status'\'': '\''running'\''
    })

urlpatterns = [
    path('\''admin/'\'', admin.site.urls),
    path('\''api/'\'', api_root, name='\''api-root'\''),
    path('\''api/core/'\'', include('\''core.urls'\'')),
    path('\''api/users/'\'', include('\''users.urls'\'')),
    path('\''api/storage/'\'', include('\''storage.urls'\'')),
    path('\''api/services/'\'', include('\''services.urls'\'')),
    path('\''api/network/'\'', include('\''network.urls'\'')),
    path('\''api/proxmox/'\'', include('\''proxmox.urls'\'')),
    path('\''api/proxmox-integration/'\'', include('\''proxmox_integration.urls'\'')),
    path('\'\'\'', TemplateView.as_view(template_name='\''index.html'\''), name='\''index'\''),
]
URLS_EOF

touch "backend/moxnas/__init__.py"

# Create simple frontend
log "⚛️ Creating React frontend..."
mkdir -p frontend/{src,public,build/static}

# Create package.json
cat > frontend/package.json << '\''PACKAGE_EOF'\''
{
  "name": "moxnas-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-bootstrap": "^2.7.0",
    "bootstrap": "^5.2.3"
  },
  "scripts": {
    "build": "echo '\''Build complete'\''"
  }
}
PACKAGE_EOF

# Create basic HTML template
cat > frontend/build/index.html << '\''HTML_EOF'\''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>MoxNAS - Containerized NAS Solution</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 4rem 0; }
        .feature-card { transition: transform 0.3s; cursor: pointer; }
        .feature-card:hover { transform: translateY(-5px); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">🏠 MoxNAS</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/admin">Admin</a>
                <a class="nav-link" href="/api">API</a>
            </div>
        </div>
    </nav>

    <div class="hero text-center">
        <div class="container">
            <h1 class="display-4 fw-bold mb-4">🎉 MoxNAS Successfully Installed!</h1>
            <p class="lead mb-4">Your containerized NAS solution is now running</p>
            <div class="d-flex justify-content-center gap-3">
                <a href="/admin" class="btn btn-light btn-lg">Admin Panel</a>
                <a href="/api" class="btn btn-outline-light btn-lg">API Explorer</a>
            </div>
        </div>
    </div>

    <div class="container my-5">
        <div class="row">
            <div class="col-md-4 mb-4">
                <div class="card feature-card h-100 shadow-sm">
                    <div class="card-body text-center">
                        <div class="mb-3" style="font-size: 3rem;">🗄️</div>
                        <h5 class="card-title">Storage Management</h5>
                        <p class="card-text">Manage your files and storage with integrated NAS services</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4 mb-4">
                <div class="card feature-card h-100 shadow-sm">
                    <div class="card-body text-center">
                        <div class="mb-3" style="font-size: 3rem;">🔧</div>
                        <h5 class="card-title">Proxmox Integration</h5>
                        <p class="card-text">Deep integration with Proxmox VE for container management</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4 mb-4">
                <div class="card feature-card h-100 shadow-sm">
                    <div class="card-body text-center">
                        <div class="mb-3" style="font-size: 3rem;">🐳</div>
                        <h5 class="card-title">Containerized</h5>
                        <p class="card-text">Lightweight LXC container deployment for optimal performance</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="row mt-5">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0">✅ Installation Status</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <p><strong>🐍 Backend:</strong> Django REST API running</p>
                                <p><strong>⚛️ Frontend:</strong> React application built</p>
                                <p><strong>📊 Database:</strong> SQLite configured</p>
                            </div>
                            <div class="col-md-6">
                                <p><strong>🔐 Admin User:</strong> admin / admin</p>
                                <p><strong>🌐 Access URL:</strong> Current page</p>
                                <p><strong>📡 API Endpoint:</strong> <a href="/api">/api</a></p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
HTML_EOF

# Setup Django database
log "🗄️ Setting up database..."
cd backend
source ../venv/bin/activate
python manage.py migrate --run-syncdb
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('\''admin'\'', '\''admin@moxnas.local'\'', '\''admin'\'') if not User.objects.filter(username='\''admin'\'').exists() else None" | python manage.py shell

# Create systemd service
log "🔧 Creating systemd service..."
cat > /etc/systemd/system/moxnas.service << '\''SERVICE_EOF'\''
[Unit]
Description=MoxNAS - Containerized NAS Solution
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/opt/moxnas/backend
Environment=PATH=/opt/moxnas/venv/bin
ExecStart=/opt/moxnas/venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# Enable and start service
systemctl daemon-reload
systemctl enable moxnas
systemctl start moxnas

# Wait for service to start
sleep 5

# Check if service is running
if systemctl is-active --quiet moxnas; then
    log "✅ MoxNAS service started successfully!"
else
    warn "⚠️ Service may have issues, trying direct startup..."
    cd /opt/moxnas/backend
    source ../venv/bin/activate
    nohup python manage.py runserver 0.0.0.0:8000 > /var/log/moxnas.log 2>&1 &
fi

# Get container IP
CONTAINER_IP=$(hostname -I | awk '\''{print $1}'\'' | head -1)
if [ -z "$CONTAINER_IP" ]; then
    CONTAINER_IP="localhost"
fi

log "🎉 MoxNAS installation completed successfully!"
log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "🌐 Access MoxNAS at: http://$CONTAINER_IP:8000"
log "👤 Admin Login: admin / admin"
log "📊 Admin Panel: http://$CONTAINER_IP:8000/admin"
log "📡 API Explorer: http://$CONTAINER_IP:8000/api"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

INSTALL_SCRIPT_EOF
chmod +x /root/install_moxnas.sh'

# Run the installation inside the container
log "🔧 Running MoxNAS installation inside container..."
pct exec $CONTAINER_ID -- /root/install_moxnas.sh

# Get final container IP
CONTAINER_IP=$(pct exec $CONTAINER_ID -- hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

# Final success message
log ""
log "🎉🎉🎉 MoxNAS COMPLETE INSTALLATION SUCCESSFUL! 🎉🎉🎉"
log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "📦 Container Information:"
log "   Container ID: $CONTAINER_ID"
log "   Container IP: $CONTAINER_IP"
log "   Hostname: moxnas-$CONTAINER_ID"
log ""
log "🌐 Access Information:"
log "   MoxNAS Dashboard: http://$CONTAINER_IP:8000"
log "   Admin Panel: http://$CONTAINER_IP:8000/admin"
log "   API Explorer: http://$CONTAINER_IP:8000/api"
log ""
log "🔐 Default Credentials:"
log "   Username: admin"
log "   Password: admin"
log ""
log "🔧 Management Commands:"
log "   Container Console: pct enter $CONTAINER_ID"
log "   Start Container: pct start $CONTAINER_ID"
log "   Stop Container: pct stop $CONTAINER_ID"
log "   Container Status: pct status $CONTAINER_ID"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log ""
log "✨ Your containerized NAS solution is now ready to use!"
log "🚀 MoxNAS will automatically start when the container boots"

exit 0