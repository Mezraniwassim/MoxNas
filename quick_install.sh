#!/bin/bash

# MoxNAS Automated Installation Script
# Self-contained installation with embedded files

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
    error "Run as root or with sudo"
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

# Update system and install dependencies
log "📦 Installing system dependencies..."
apt-get update -qq
apt-get install -y curl wget git python3 python3-pip python3-venv nodejs npm sqlite3 unzip

# Check Node.js version and install if needed
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

# Create MoxNAS project structure automatically
log "🏗️ Creating MoxNAS project structure..."
create_moxnas_project

# Get container IP
CONTAINER_IP=$(hostname -I | awk '{print $1}' | head -1)
if [ -z "$CONTAINER_IP" ]; then
    CONTAINER_IP="localhost"
fi

# Display success message
log "🎉 MoxNAS installation completed successfully!"
log ""
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "🌐 Access MoxNAS at: http://$CONTAINER_IP:8000"
log "📊 Admin Panel: http://$CONTAINER_IP:8000/admin"
log "🔧 API Docs: http://$CONTAINER_IP:8000/api"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log ""
log "📋 Quick Commands:"
log "   Status: /opt/moxnas/start_container.sh status"
log "   Restart: /opt/moxnas/start_container.sh restart"
log "   Logs: tail -f /var/log/moxnas/error.log"
log ""
log "✨ MoxNAS is now running and ready to use!"

# Cleanup
cd /
rm -rf "$TEMP_DIR"