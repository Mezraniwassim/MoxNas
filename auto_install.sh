#!/bin/bash

# MoxNAS Automated Installation Script
# Self-contained installation - no external dependencies required

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

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root"
    exit 1
fi

log "🚀 Starting MoxNAS Automated Installation..."

# Set environment
export DEBIAN_FRONTEND=noninteractive
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# Detect environment
IS_LXC=false
if [ -f /proc/1/environ ] && grep -q container=lxc /proc/1/environ; then
    IS_LXC=true
    log "🐳 Detected LXC container environment"
else
    log "🖥️ Detected host environment"
fi

# Install system dependencies
log "📦 Installing system dependencies..."
apt-get update -qq
apt-get install -y curl wget python3 python3-pip python3-venv nodejs npm sqlite3 unzip samba nfs-kernel-server vsftpd

# Check and install Node.js 18 if needed
NODE_VERSION=$(node --version 2>/dev/null | cut -d'v' -f2 | cut -d'.' -f1 || echo "0")
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

# Create backend directory structure
log "🏗️ Creating Django backend..."
mkdir -p backend/{core,users,storage,services,network,proxmox,proxmox_integration}
mkdir -p backend/moxnas

# Create Python virtual environment
log "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
log "📦 Installing Python dependencies..."
pip install Django==4.2 djangorestframework==3.14.0 django-cors-headers==4.0.0 \
            requests==2.31.0 cryptography==41.0.0 gunicorn==21.2.0 python-decouple==3.8

# Create Django project files
cat > backend/manage.py << 'EOF'
#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)
EOF

# Create Django settings
cat > backend/moxnas/settings.py << 'EOF'
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'moxnas-secret-key-change-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'core',
    'users',
    'storage',
    'services',
    'network',
    'proxmox',
    'proxmox_integration',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'moxnas.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR.parent, 'frontend', 'build')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR.parent, 'frontend', 'build', 'static'),
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'moxnas-cache',
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/moxnas/moxnas.log',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
EOF

# Create basic Django apps structure
for app in core users storage services network proxmox proxmox_integration; do
    mkdir -p "backend/$app"
    touch "backend/$app/__init__.py"
    cat > "backend/$app/models.py" << 'EOF'
from django.db import models
# Add your models here
EOF
    cat > "backend/$app/views.py" << 'EOF'
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
# Add your views here
EOF
    cat > "backend/$app/urls.py" << 'EOF'
from django.urls import path
urlpatterns = []
EOF
done

# Create main URLs
cat > backend/moxnas/urls.py << 'EOF'
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/core/', include('core.urls')),
    path('api/users/', include('users.urls')),
    path('api/storage/', include('storage.urls')),
    path('api/services/', include('services.urls')),
    path('api/network/', include('network.urls')),
    path('api/proxmox/', include('proxmox.urls')),
    path('api/proxmox-integration/', include('proxmox_integration.urls')),
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
]
EOF

cat > backend/moxnas/__init__.py << 'EOF'
EOF

# Create frontend directory
log "⚛️ Creating React frontend..."
mkdir -p frontend/src/{components,pages,services}
mkdir -p frontend/public

# Create package.json
cat > frontend/package.json << 'EOF'
{
  "name": "moxnas-frontend",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "react-bootstrap": "^2.7.0",
    "bootstrap": "^5.2.3",
    "react-icons": "^4.7.1",
    "axios": "^1.3.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "devDependencies": {
    "react-scripts": "5.0.1"
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
EOF

# Create basic React app structure
cat > frontend/public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>MoxNAS - Containerized NAS Solution</title>
</head>
<body>
    <div id="root"></div>
</body>
</html>
EOF

cat > frontend/src/index.js << 'EOF'
import React from 'react';
import ReactDOM from 'react-dom/client';
import 'bootstrap/dist/css/bootstrap.min.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
EOF

cat > frontend/src/App.js << 'EOF'
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Container, Navbar, Nav } from 'react-bootstrap';
import Dashboard from './pages/Dashboard';

function App() {
  return (
    <Router>
      <Navbar bg="dark" variant="dark" expand="lg">
        <Container>
          <Navbar.Brand href="/">MoxNAS</Navbar.Brand>
          <Nav className="me-auto">
            <Nav.Link href="/">Dashboard</Nav.Link>
          </Nav>
        </Container>
      </Navbar>
      <Container className="mt-4">
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </Container>
    </Router>
  );
}

export default App;
EOF

cat > frontend/src/pages/Dashboard.js << 'EOF'
import React, { useState, useEffect } from 'react';
import { Card, Alert } from 'react-bootstrap';

const Dashboard = () => {
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    setStatus('running');
  }, []);

  return (
    <div>
      <h1>MoxNAS Dashboard</h1>
      <Alert variant="success">
        🎉 MoxNAS is successfully installed and running!
      </Alert>
      <Card>
        <Card.Body>
          <Card.Title>Welcome to MoxNAS</Card.Title>
          <Card.Text>
            Your containerized NAS solution is ready. This is a basic installation.
            The full feature set includes Proxmox integration, storage management, 
            and advanced authentication.
          </Card.Text>
        </Card.Body>
      </Card>
    </div>
  );
};

export default Dashboard;
EOF

# Install frontend dependencies and build
log "📦 Installing frontend dependencies..."
cd frontend
npm install --silent
npm run build

# Return to main directory
cd "$INSTALL_DIR"

# Setup Django database
log "🗄️ Setting up database..."
cd backend
source ../venv/bin/activate
python manage.py migrate --run-syncdb
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@moxnas.local', 'admin') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

# Create startup script
log "🚀 Creating startup script..."
cat > "$INSTALL_DIR/start_moxnas.sh" << 'EOF'
#!/bin/bash

INSTALL_DIR="/opt/moxnas"
cd "$INSTALL_DIR/backend"

# Activate virtual environment
source ../venv/bin/activate

# Check if port 8000 is available
if netstat -tuln | grep -q :8000; then
    echo "Port 8000 is in use, killing existing processes..."
    pkill -f "python.*manage.py.*runserver" || true
    pkill -f "gunicorn.*moxnas" || true
    sleep 2
fi

# Start Django development server
echo "Starting MoxNAS on port 8000..."
python manage.py runserver 0.0.0.0:8000 &

# Wait a moment and check if it's running
sleep 3
if netstat -tuln | grep -q :8000; then
    echo "✅ MoxNAS started successfully!"
    echo "🌐 Access at: http://$(hostname -I | awk '{print $1}'):8000"
    echo "👤 Admin: admin / admin"
else
    echo "❌ Failed to start MoxNAS"
    exit 1
fi
EOF

chmod +x "$INSTALL_DIR/start_moxnas.sh"

# Create log directory
mkdir -p /var/log/moxnas
chown -R www-data:www-data /var/log/moxnas 2>/dev/null || true

# Start MoxNAS
log "🎯 Starting MoxNAS..."
"$INSTALL_DIR/start_moxnas.sh"

# Get container/host IP
CONTAINER_IP=$(hostname -I | awk '{print $1}' | head -1)
if [ -z "$CONTAINER_IP" ]; then
    CONTAINER_IP="localhost"
fi

# Success message
log "🎉 MoxNAS installation completed successfully!"
log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "🌐 Access MoxNAS at: http://$CONTAINER_IP:8000"
log "👤 Admin Login: admin / admin"
log "📊 Admin Panel: http://$CONTAINER_IP:8000/admin"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log ""
log "📋 Management Commands:"
log "   Start/Restart: $INSTALL_DIR/start_moxnas.sh"
log "   Logs: tail -f /var/log/moxnas/moxnas.log"
log ""
log "✨ MoxNAS is now running and ready to use!"

exit 0