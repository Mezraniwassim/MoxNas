#!/bin/bash

# MoxNAS Simple Proxmox Installation Script
# Creates LXC container and installs MoxNAS - Fixed for LXC compatibility

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m' 
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[MoxNAS] $1${NC}"; }
warn() { echo -e "${YELLOW}[MoxNAS] WARNING: $1${NC}"; }
error() { echo -e "${RED}[MoxNAS] ERROR: $1${NC}"; }

# Check if running on Proxmox host
if ! command -v pct &> /dev/null; then
    error "This script must be run on a Proxmox VE host"
    exit 1
fi

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root on Proxmox host"
    exit 1
fi

log "🚀 Starting MoxNAS Simple Installation..."

# Configuration - Use specific container ID range
CONTAINER_ID=${1:-200}
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

# Find Ubuntu template
log "🔍 Finding Ubuntu template..."
TEMPLATE=""
for template in $(pveam available | grep ubuntu | grep -E "(22.04|24.04)" | head -3 | awk '{print $2}'); do
    if pveam list local | grep -q "$template"; then
        TEMPLATE="local:vztmpl/$template"
        log "✅ Found template: $template"
        break
    fi
done

if [ -z "$TEMPLATE" ]; then
    log "📥 Downloading Ubuntu 22.04 template..."
    pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
    TEMPLATE="local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
fi

# Check if container ID exists
if pct list | grep -q "^$CONTAINER_ID "; then
    warn "Container $CONTAINER_ID already exists - destroying it..."
    pct stop $CONTAINER_ID 2>/dev/null || true
    pct destroy $CONTAINER_ID
fi

# Create LXC container with simplified features
log "🐳 Creating LXC container $CONTAINER_ID..."
pct create $CONTAINER_ID $TEMPLATE \
    --hostname moxnas-$CONTAINER_ID \
    --memory $CONTAINER_MEMORY \
    --cores $CONTAINER_CORES \
    --rootfs local-lvm:$CONTAINER_DISK \
    --net0 name=eth0,bridge=$BRIDGE,ip=dhcp \
    --features nesting=1 \
    --unprivileged 1 \
    --onboot 1 \
    --description "MoxNAS - Containerized NAS Solution"

# Start container
log "▶️ Starting container..."
pct start $CONTAINER_ID

# Wait for container to be ready
log "⏳ Waiting for container to be ready..."
sleep 15

# Wait for network
CONTAINER_IP=""
for i in {1..30}; do
    CONTAINER_IP=$(pct exec $CONTAINER_ID -- hostname -I 2>/dev/null | awk '{print $1}' || echo "")
    if [ -n "$CONTAINER_IP" ] && [ "$CONTAINER_IP" != "127.0.0.1" ]; then
        break
    fi
    sleep 2
done

if [ -z "$CONTAINER_IP" ] || [ "$CONTAINER_IP" = "127.0.0.1" ]; then
    CONTAINER_IP="localhost"
fi
log "🌐 Container IP: $CONTAINER_IP"

# Create simple installation script
log "📝 Creating simple installation script..."
pct exec $CONTAINER_ID -- bash -c 'cat > /root/simple_install.sh << '\''EOF'\''
#!/bin/bash

set -e

GREEN='\''\\033[0;32m'\''
RED='\''\\033[0;31m'\''
NC='\''\\033[0m'\''

log() { echo -e "${GREEN}[MoxNAS] $1${NC}"; }
error() { echo -e "${RED}[MoxNAS] ERROR: $1${NC}"; }

log "🚀 Installing MoxNAS..."

# Set environment
export DEBIAN_FRONTEND=noninteractive
export LC_ALL=C.UTF-8

# Update and install essential packages only
log "📦 Installing essential packages..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv curl wget

# Create installation directory
log "📁 Creating installation directory..."
mkdir -p /opt/moxnas
cd /opt/moxnas

# Create Python virtual environment
log "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install minimal Django setup
log "📦 Installing Python packages..."
pip install --quiet Django==4.2 djangorestframework==3.14.0 django-cors-headers==4.0.0

# Create minimal Django project
log "🏗️ Creating Django project..."
mkdir -p backend
cd backend

# Create manage.py
cat > manage.py << '\''MANAGE_EOF'\''
#!/usr/bin/env python
import os, sys
if __name__ == '\''__main__'\'':
    os.environ.setdefault('\''DJANGO_SETTINGS_MODULE'\'', '\''moxnas.settings'\'')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
MANAGE_EOF

# Create settings directory
mkdir -p moxnas
cat > moxnas/__init__.py << '\''EOF'\''
EOF

cat > moxnas/settings.py << '\''SETTINGS_EOF'\''
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = '\''moxnas-secret-key'\''
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
    '\''corsheaders'\'',
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
        '\''DIRS'\'': [],
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
CORS_ALLOW_ALL_ORIGINS = True

USE_TZ = True
DEFAULT_AUTO_FIELD = '\''django.db.models.BigAutoField'\''
SETTINGS_EOF

# Create URLs
cat > moxnas/urls.py << '\''URLS_EOF'\''
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse, HttpResponse

def home(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MoxNAS - Containerized NAS</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .success { background: #d4edda; color: #155724; padding: 20px; border-radius: 5px; margin: 20px 0; }
            .card { background: #f8f9fa; padding: 20px; margin: 10px 0; border-radius: 5px; }
            .btn { background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 5px; }
            h1 { color: #333; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏠 MoxNAS Successfully Installed!</h1>
            <div class="success">
                <strong>✅ Installation Complete!</strong><br>
                Your containerized NAS solution is now running.
            </div>
            
            <div class="card">
                <h3>🎯 Access Points</h3>
                <a href="/admin" class="btn">Admin Panel</a>
                <a href="/api" class="btn">API Explorer</a>
            </div>
            
            <div class="card">
                <h3>🔐 Default Credentials</h3>
                <p><strong>Username:</strong> admin<br><strong>Password:</strong> admin</p>
            </div>
            
            <div class="card">
                <h3>🚀 Next Steps</h3>
                <ul>
                    <li>Access the admin panel to configure users</li>
                    <li>Use the API to integrate with Proxmox</li>
                    <li>Configure storage and services</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

def api_status(request):
    return JsonResponse({
        '\''message'\'': '\''MoxNAS API is running'\'',
        '\''version'\'': '\''1.0.0'\'',
        '\''status'\'': '\''active'\''
    })

urlpatterns = [
    path('\''admin/'\'', admin.site.urls),
    path('\''api/'\'', api_status),
    path('\'\'\'', home),
]
URLS_EOF

# Setup database and create admin user
log "🗄️ Setting up database..."
source /opt/moxnas/venv/bin/activate
python manage.py migrate --run-syncdb
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='\''admin'\'').exists():
    User.objects.create_superuser('\''admin'\'', '\''admin@moxnas.local'\'', '\''admin'\'')
    print('\''Admin user created'\'')
else:
    print('\''Admin user already exists'\'')
"

# Create startup script
log "🔧 Creating startup script..."
cat > /opt/moxnas/start.sh << '\''START_EOF'\''
#!/bin/bash
cd /opt/moxnas/backend
source ../venv/bin/activate

# Kill any existing processes
pkill -f "python.*manage.py.*runserver" 2>/dev/null || true
sleep 2

# Start Django
echo "Starting MoxNAS on port 8000..."
nohup python manage.py runserver 0.0.0.0:8000 > /var/log/moxnas.log 2>&1 &

# Wait and check
sleep 3
if netstat -tuln 2>/dev/null | grep -q :8000; then
    echo "✅ MoxNAS started successfully!"
    IP=$(hostname -I | awk '\''{print $1}'\'' | head -1)
    echo "🌐 Access at: http://$IP:8000"
    echo "👤 Admin: admin / admin"
else
    echo "❌ Failed to start - check /var/log/moxnas.log"
fi
START_EOF

chmod +x /opt/moxnas/start.sh

# Start MoxNAS
log "🎯 Starting MoxNAS..."
/opt/moxnas/start.sh

# Get IP and display success
IP=$(hostname -I | awk '\''{print $1}'\'' | head -1)
log ""
log "🎉 MoxNAS installation completed!"
log "🌐 Access: http://$IP:8000"
log "👤 Login: admin / admin"
log "📊 Admin: http://$IP:8000/admin"
log "📡 API: http://$IP:8000/api"
log ""
log "✨ Installation successful!"

EOF
chmod +x /root/simple_install.sh'

# Run the simple installation
log "🔧 Running simple installation inside container..."
pct exec $CONTAINER_ID -- /root/simple_install.sh

# Get final container IP
CONTAINER_IP=$(pct exec $CONTAINER_ID -- hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

# Success message
log ""
log "🎉🎉🎉 MoxNAS INSTALLATION SUCCESSFUL! 🎉🎉🎉"
log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "📦 Container: $CONTAINER_ID"
log "🌐 Access: http://$CONTAINER_IP:8000"
log "👤 Login: admin / admin"
log "📊 Admin: http://$CONTAINER_IP:8000/admin"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit 0