#!/bin/bash
#
# MoxNAS Quick Setup Script
# Quick configuration of Proxmox credentials after installation
#

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "       MoxNAS Quick Setup"
echo -e "==========================================${NC}"
echo ""

# Check if running inside container
if [ -f /.dockerenv ] || [ -f /run/.containerenv ] || [ -d /proc/vz ]; then
    echo -e "${GREEN}✓ Running inside container${NC}"
    CONFIG_FILE="/opt/moxnas/.env"
else
    echo -e "${YELLOW}⚠ This should be run inside the MoxNAS container${NC}"
    echo "Run: pct exec [container-id] -- /opt/moxnas/quick_setup.sh"
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}⚠ Configuration file not found${NC}"
    echo "Please run the full installation first"
    exit 1
fi

echo "Current configuration:"
echo "  Config file: $CONFIG_FILE"
echo ""

# Get current Proxmox host
CURRENT_HOST=$(grep "PROXMOX_HOST=" "$CONFIG_FILE" | cut -d'=' -f2)
CURRENT_USERNAME=$(grep "PROXMOX_USERNAME=" "$CONFIG_FILE" | cut -d'=' -f2)

echo "Current Proxmox host: ${CURRENT_HOST:-'Not set'}"
echo "Current username: ${CURRENT_USERNAME:-'Not set'}"
echo ""

# Prompt for password
echo -n "Enter Proxmox password for $CURRENT_USERNAME: "
read -s PROXMOX_PASSWORD
echo ""

if [ -z "$PROXMOX_PASSWORD" ]; then
    echo -e "${YELLOW}⚠ No password entered. Exiting.${NC}"
    exit 1
fi

# Update password in config file
if grep -q "PROXMOX_PASSWORD=" "$CONFIG_FILE"; then
    # Replace existing password
    sed -i "s/PROXMOX_PASSWORD=.*/PROXMOX_PASSWORD=$PROXMOX_PASSWORD/" "$CONFIG_FILE"
else
    # Add password line
    echo "PROXMOX_PASSWORD=$PROXMOX_PASSWORD" >> "$CONFIG_FILE"
fi

echo -e "${GREEN}✓ Password updated successfully${NC}"

# Test connection
echo ""
echo "Testing Proxmox connection..."

PROXMOX_HOST=$(grep "PROXMOX_HOST=" "$CONFIG_FILE" | cut -d'=' -f2)
PROXMOX_PORT=$(grep "PROXMOX_PORT=" "$CONFIG_FILE" | cut -d'=' -f2)
PROXMOX_USERNAME=$(grep "PROXMOX_USERNAME=" "$CONFIG_FILE" | cut -d'=' -f2)
PROXMOX_REALM=$(grep "PROXMOX_REALM=" "$CONFIG_FILE" | cut -d'=' -f2)

if curl -s --connect-timeout 10 --insecure \
    -d "username=${PROXMOX_USERNAME}@${PROXMOX_REALM}&password=${PROXMOX_PASSWORD}" \
    "https://${PROXMOX_HOST}:${PROXMOX_PORT}/api2/json/access/ticket" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connection to Proxmox successful!${NC}"
else
    echo -e "${YELLOW}⚠ Connection test failed. Please verify:${NC}"
    echo "  - Proxmox host IP: $PROXMOX_HOST"
    echo "  - Username: $PROXMOX_USERNAME"
    echo "  - Password entered correctly"
    echo "  - Network connectivity"
fi

# Restart MoxNAS service if available
echo ""
if systemctl is-active moxnas &> /dev/null; then
    echo "Restarting MoxNAS service..."
    systemctl restart moxnas
    echo -e "${GREEN}✓ MoxNAS service restarted${NC}"
else
    echo -e "${YELLOW}⚠ MoxNAS service not running${NC}"
    echo "You may need to start it manually: systemctl start moxnas"
fi

echo ""
echo -e "${BLUE}=========================================="
echo "           Setup Complete!"
echo -e "==========================================${NC}"
echo ""
echo "✓ Proxmox credentials configured"
echo "✓ Connection tested"
echo "✓ Service restarted"
echo ""
echo "Next steps:"
echo "1. Access MoxNAS web interface"
echo "2. Go to 'Proxmox' tab"
echo "3. Start managing containers!"
echo ""