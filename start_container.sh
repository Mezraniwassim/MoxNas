#!/bin/bash

# MoxNAS Container Startup Script
# Use this script inside the LXC container to start MoxNAS

set -e

echo "🚀 Starting MoxNAS Container..."

# Change to MoxNAS directory
cd /opt/moxnas || { echo "❌ MoxNAS not found in /opt/moxnas"; exit 1; }

# Activate virtual environment
source venv/bin/activate || { echo "❌ Virtual environment not found"; exit 1; }

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating default .env file..."
    cat > .env << 'EOF'
DEBUG=False
SECRET_KEY=moxnas-production-key-change-me-in-production
MOXNAS_STORAGE_PATH=/mnt/storage
MOXNAS_CONFIG_PATH=/etc/moxnas
MOXNAS_LOG_PATH=/var/log/moxnas
EOF
fi

# Set up storage directories
mkdir -p /mnt/storage
mkdir -p /etc/moxnas
mkdir -p /var/log/moxnas

# Set permissions
chmod 755 /mnt/storage

# Start essential services if not running
echo "🔧 Starting NAS services..."
systemctl start ssh 2>/dev/null || true
systemctl start smbd 2>/dev/null || true
systemctl start nmbd 2>/dev/null || true

# Start MoxNAS in production mode
echo "🌐 Starting MoxNAS Web Interface on port 8080..."
echo "📍 Access the web interface at: http://$(hostname -I | awk '{print $1}'):8080"
echo "👤 Default login: admin / moxnas123"
echo ""
python3 start_moxnas.py production