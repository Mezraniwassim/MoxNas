#!/bin/bash

# MoxNas One-Link Installation Script
# This is the ultimate one-command installer for MoxNas
# Usage: curl -sSL https://install.moxnas.com | bash
# Alternative: curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/one-install.sh | bash

set -euo pipefail

# Version and repository
MOXNAS_VERSION="2.0.0"
GITHUB_REPO="Mezraniwassim/MoxNas"
INSTALL_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/master/install-moxnas.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Banner
echo -e "${PURPLE}${BOLD}
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│    ███╗   ███╗ ██████╗ ██╗  ██╗███╗   ██╗ █████╗ ███████╗         │
│    ████╗ ████║██╔═══██╗╚██╗██╔╝████╗  ██║██╔══██╗██╔════╝         │
│    ██╔████╔██║██║   ██║ ╚███╔╝ ██╔██╗ ██║███████║███████╗         │
│    ██║╚██╔╝██║██║   ██║ ██╔██╗ ██║╚██╗██║██╔══██║╚════██║         │
│    ██║ ╚═╝ ██║╚██████╔╝██╔╝ ██╗██║ ╚████║██║  ██║███████║         │
│    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝         │
│                                                                    │
│         🚀 Professional NAS Management for Proxmox VE             │
│                        One-Command Installation                    │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘${NC}
"

echo -e "${BLUE}Version: ${MOXNAS_VERSION}${NC}"
echo -e "${BLUE}Repository: https://github.com/${GITHUB_REPO}${NC}"
echo

# Quick validation
echo -e "${YELLOW}🔍 Performing quick validation...${NC}"

# Check Proxmox
if ! command -v pct >/dev/null 2>&1; then
    echo -e "${RED}❌ This script requires Proxmox VE${NC}"
    echo -e "${YELLOW}💡 Please run this on a Proxmox VE host${NC}"
    exit 1
fi

# Check root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}❌ This script must be run as root${NC}"
    echo -e "${YELLOW}💡 Please run: sudo $0${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment validation passed${NC}"
echo

# Download and execute main installer
echo -e "${BLUE}📥 Downloading MoxNas installer...${NC}"

# Create temporary file
TEMP_INSTALLER=$(mktemp)

# Download with progress
if curl -#L "$INSTALL_URL" -o "$TEMP_INSTALLER"; then
    echo -e "${GREEN}✅ Installer downloaded successfully${NC}"
else
    echo -e "${RED}❌ Failed to download installer${NC}"
    exit 1
fi

# Make executable
chmod +x "$TEMP_INSTALLER"

echo -e "${BLUE}🚀 Starting MoxNas installation...${NC}"
echo

# Execute installer
if "$TEMP_INSTALLER" "$@"; then
    echo
    echo -e "${GREEN}${BOLD}🎉 MoxNas installation completed successfully!${NC}"
    echo
    echo -e "${BLUE}📚 Next steps:${NC}"
    echo "1. Access the web interface using the URL shown above"
    echo "2. Login with the provided credentials"
    echo "3. Change the default admin password"
    echo "4. Configure Proxmox connection settings"
    echo
    echo -e "${BLUE}📖 Documentation: https://github.com/${GITHUB_REPO}${NC}"
    echo -e "${BLUE}💬 Support: https://github.com/${GITHUB_REPO}/issues${NC}"
else
    echo
    echo -e "${RED}❌ Installation failed${NC}"
    echo -e "${YELLOW}📋 Check the installation log for details${NC}"
    echo -e "${BLUE}💬 Get help: https://github.com/${GITHUB_REPO}/issues${NC}"
    exit 1
fi

# Cleanup
rm -f "$TEMP_INSTALLER"
