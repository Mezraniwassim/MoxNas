#!/bin/bash

# Quick Proxmox Connection Test for MoxNAS
# Tests if MoxNAS can connect to client's Proxmox environment

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

CONTAINER_ID=${1:-200}

echo "🧪 MoxNAS Proxmox Connection Test"
echo "================================="
echo ""

# Check if container exists
if ! pct status "$CONTAINER_ID" >/dev/null 2>&1; then
    echo -e "${RED}❌ Container $CONTAINER_ID not found${NC}"
    echo "Please install MoxNAS first:"
    echo "curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install_moxnas.sh | bash"
    exit 1
fi

echo -e "${BLUE}ℹ️  Testing container $CONTAINER_ID...${NC}"

# Get container IP
CONTAINER_IP=$(pct exec "$CONTAINER_ID" -- hostname -I 2>/dev/null | awk '{print $1}' || echo "")
if [ -n "$CONTAINER_IP" ]; then
    echo -e "${GREEN}✅ Container IP: $CONTAINER_IP${NC}"
else
    echo -e "${YELLOW}⚠️  Could not determine container IP${NC}"
fi

# Check if MoxNAS service is running
if pct exec "$CONTAINER_ID" -- systemctl is-active moxnas >/dev/null 2>&1; then
    echo -e "${GREEN}✅ MoxNAS service is running${NC}"
else
    echo -e "${RED}❌ MoxNAS service is not running${NC}"
    echo "Try: pct exec $CONTAINER_ID -- systemctl start moxnas"
    exit 1
fi

# Check if web interface is accessible
if [ -n "$CONTAINER_IP" ]; then
    if curl -s -I "http://$CONTAINER_IP:8000" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Web interface is accessible${NC}"
    else
        echo -e "${YELLOW}⚠️  Web interface not responding (may take a moment to start)${NC}"
    fi
fi

# Check if .env file exists
if pct exec "$CONTAINER_ID" -- test -f /opt/moxnas/.env 2>/dev/null; then
    echo -e "${GREEN}✅ Proxmox configuration file exists${NC}"
    
    # Check configuration
    echo ""
    echo -e "${BLUE}📋 Current Proxmox Configuration:${NC}"
    pct exec "$CONTAINER_ID" -- grep -E "PROXMOX_HOST|PROXMOX_USERNAME" /opt/moxnas/.env 2>/dev/null || echo "No Proxmox config found"
else
    echo -e "${YELLOW}⚠️  No Proxmox configuration found${NC}"
    echo ""
    echo "To configure Proxmox integration:"
    echo "curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/configure_proxmox.sh | bash -s -- --interactive"
fi

echo ""
echo -e "${BLUE}🌐 Access MoxNAS:${NC}"
if [ -n "$CONTAINER_IP" ]; then
    echo "   Web Interface: http://$CONTAINER_IP:8000"
else
    echo "   Find IP: pct exec $CONTAINER_ID -- hostname -I"
fi
echo "   Default Login: admin / moxnas123"
echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo "   Restart service: pct exec $CONTAINER_ID -- systemctl restart moxnas"
echo "   View logs: pct exec $CONTAINER_ID -- journalctl -u moxnas -f"
echo "   Container shell: pct enter $CONTAINER_ID"
