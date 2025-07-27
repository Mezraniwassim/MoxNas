#!/bin/bash
#
# MoxNAS Container Startup Script
# This script ensures MoxNAS starts properly inside LXC containers
#

set -e

# Configuration
MOXNAS_HOME="/opt/moxnas"
VENV_PATH="$MOXNAS_HOME/venv"
BACKEND_PATH="$MOXNAS_HOME/backend"
PID_FILE="/var/run/moxnas.pid"
LOG_DIR="/var/log/moxnas"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "🚀 Starting MoxNAS Container..."

# Create necessary directories
setup_directories() {
    log_info "Setting up directories..."
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    
    # Create storage directory
    mkdir -p /mnt/storage
    chmod 755 /mnt/storage
    
    # Create MoxNAS storage directory
    mkdir -p /opt/moxnas/storage
    chmod 755 /opt/moxnas/storage
    
    log_success "Directories created"
}

# Check if already running
check_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_warning "MoxNAS is already running (PID: $PID)"
            return 0
        else
            log_warning "Stale PID file found, removing..."
            rm -f "$PID_FILE"
        fi
    fi
    
    # Check for gunicorn processes
    if pgrep -f "gunicorn.*moxnas" > /dev/null 2>&1; then
        log_warning "Gunicorn processes found, stopping them..."
        pkill -f "gunicorn.*moxnas" || true
        sleep 2
    fi
    
    return 1
}

# Start services
start_services() {
    log_info "Starting NAS services..."
    
    services=("ssh" "smbd" "nmbd" "nfs-kernel-server" "vsftpd" "snmpd" "tgt")
    
    for service in "${services[@]}"; do
        if systemctl is-enabled "$service" >/dev/null 2>&1; then
            systemctl start "$service" || log_warning "Failed to start $service"
        else
            systemctl enable "$service" >/dev/null 2>&1 || true
            systemctl start "$service" || log_warning "Failed to start $service"
        fi
    done
    
    log_success "NAS services started"
}

# Setup and check running
setup_directories
if check_running; then
    exit 0
fi
start_services

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