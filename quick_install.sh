#!/bin/bash

# MoxNAS One-Line Installation Script
# Usage: curl -sSL https://raw.githubusercontent.com/your-repo/MoxNas/main/quick_install.sh | bash

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
    error "Run: sudo bash <(curl -sSL https://raw.githubusercontent.com/your-repo/MoxNas/main/quick_install.sh)"
    exit 1
fi

log "🚀 Starting MoxNAS One-Line Installation..."

# Set environment
export DEBIAN_FRONTEND=noninteractive
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# Update system and install essential packages
log "📦 Installing system dependencies..."
apt-get update -qq && apt-get install -y curl wget git python3 python3-pip python3-venv nodejs npm

# Download and extract MoxNAS
log "⬇️ Downloading MoxNAS..."
INSTALL_DIR="/opt/moxnas"
TEMP_DIR="/tmp/moxnas-install"

mkdir -p "$TEMP_DIR"
cd "$TEMP_DIR"

# Try multiple methods to download MoxNAS
log "📥 Downloading MoxNAS from GitHub..."

# Method 1: Git clone (preferred)
if git clone https://github.com/Mezraniwassim/MoxNas.git . 2>/dev/null; then
    log "✅ Downloaded via git clone"
# Method 2: wget archive
elif wget -q -O moxnas.zip "https://github.com/Mezraniwassim/MoxNas/archive/main.zip" 2>/dev/null && unzip -q moxnas.zip 2>/dev/null && mv MoxNas-main/* . 2>/dev/null; then
    log "✅ Downloaded via wget"
    rm -f moxnas.zip
# Method 3: curl archive  
elif curl -sL "https://github.com/Mezraniwassim/MoxNas/archive/main.zip" -o moxnas.zip 2>/dev/null && unzip -q moxnas.zip 2>/dev/null && mv MoxNas-main/* . 2>/dev/null; then
    log "✅ Downloaded via curl"
    rm -f moxnas.zip
else
    error "❌ Failed to download MoxNAS from GitHub"
    error "Please check your internet connection and try again"
    exit 1
fi

# Run the main installation
log "🔧 Running installation..."
chmod +x install_moxnas.sh
./install_moxnas.sh

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