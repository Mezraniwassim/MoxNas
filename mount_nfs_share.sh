#!/bin/bash

# MoxNAS NFS Share Mount Helper
# This script helps you easily mount and access your NFS shares

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NFS_SERVER="192.168.1.109"
NFS_PATH="/home/wassim/Documents/MoxNAS/storage_pools/data/datasets/www"
MOUNT_POINT="$HOME/Desktop/MoxNAS-NFS-Share"

echo -e "${BLUE}🔗 MoxNAS NFS Share Mount Helper${NC}"
echo "=================================="

# Check if NFS server is accessible
echo -e "\n${YELLOW}1️⃣ Checking NFS server accessibility...${NC}"
if showmount -e "$NFS_SERVER" | grep -q "$NFS_PATH"; then
    echo -e "${GREEN}✅ NFS server is accessible${NC}"
    echo "Available exports:"
    showmount -e "$NFS_SERVER" | grep -E "(MoxNAS|datasets)" | sed 's/^/   📁 /'
else
    echo -e "${RED}❌ NFS server is not accessible${NC}"
    echo "Please check:"
    echo "  - Is MoxNAS running?"
    echo "  - Is the NFS server active? (systemctl status nfs-server)"
    echo "  - Are you on the same network?"
    exit 1
fi

# Check if already mounted
echo -e "\n${YELLOW}2️⃣ Checking mount status...${NC}"
if mount | grep -q "$MOUNT_POINT"; then
    echo -e "${GREEN}✅ NFS share is already mounted at: $MOUNT_POINT${NC}"
    ACTION="remount"
else
    echo -e "${YELLOW}📁 NFS share is not mounted yet${NC}"
    ACTION="mount"
fi

# Create mount point if needed
echo -e "\n${YELLOW}3️⃣ Preparing mount point...${NC}"
if [ ! -d "$MOUNT_POINT" ]; then
    mkdir -p "$MOUNT_POINT"
    echo -e "${GREEN}✅ Created mount point: $MOUNT_POINT${NC}"
else
    echo -e "${GREEN}✅ Mount point exists: $MOUNT_POINT${NC}"
fi

# Mount or remount
echo -e "\n${YELLOW}4️⃣ Mounting NFS share...${NC}"
if [ "$ACTION" = "remount" ]; then
    echo "Unmounting existing mount..."
    fusermount -u "$MOUNT_POINT" 2>/dev/null || umount "$MOUNT_POINT" 2>/dev/null || true
fi

# Try different mount methods
echo "Attempting to mount NFS share..."

# Method 1: Try with curlftpfs (if available) - for user space mounting
if command -v curlftpfs >/dev/null 2>&1; then
    echo "Trying curlftpfs method..."
    if curlftpfs "nfs://$NFS_SERVER$NFS_PATH" "$MOUNT_POINT" 2>/dev/null; then
        echo -e "${GREEN}✅ Mounted using curlftpfs${NC}"
        MOUNT_SUCCESS=true
    fi
fi

# Method 2: Direct user mount (if NFS client supports it)
if [ -z "$MOUNT_SUCCESS" ]; then
    echo "Trying direct NFS mount..."
    if mount -t nfs "$NFS_SERVER:$NFS_PATH" "$MOUNT_POINT" 2>/dev/null; then
        echo -e "${GREEN}✅ Mounted using direct NFS mount${NC}"
        MOUNT_SUCCESS=true
    fi
fi

# Method 3: Sudo mount (most reliable)
if [ -z "$MOUNT_SUCCESS" ]; then
    echo "Trying sudo mount..."
    if sudo mount -t nfs "$NFS_SERVER:$NFS_PATH" "$MOUNT_POINT" 2>/dev/null; then
        echo -e "${GREEN}✅ Mounted using sudo (requires admin privileges)${NC}"
        MOUNT_SUCCESS=true
    fi
fi

if [ -z "$MOUNT_SUCCESS" ]; then
    echo -e "${RED}❌ Failed to mount NFS share${NC}"
    echo -e "\n${YELLOW}Manual mount command:${NC}"
    echo "sudo mount -t nfs $NFS_SERVER:$NFS_PATH $MOUNT_POINT"
    exit 1
fi

# Verify mount and show contents
echo -e "\n${YELLOW}5️⃣ Verifying mount and showing contents...${NC}"
if [ -d "$MOUNT_POINT" ] && [ "$(ls -A $MOUNT_POINT)" ]; then
    echo -e "${GREEN}✅ NFS share successfully mounted!${NC}"
    echo -e "\n${BLUE}📂 Contents of your NFS share:${NC}"
    ls -la "$MOUNT_POINT" | sed 's/^/   /'
    
    echo -e "\n${BLUE}📄 Sample file contents:${NC}"
    if [ -f "$MOUNT_POINT/welcome.txt" ]; then
        echo -e "${YELLOW}📄 welcome.txt:${NC}"
        cat "$MOUNT_POINT/welcome.txt" | sed 's/^/   /'
    fi
    
    if [ -f "$MOUNT_POINT/README.md" ]; then
        echo -e "\n${YELLOW}📄 README.md (first 10 lines):${NC}"
        head -10 "$MOUNT_POINT/README.md" | sed 's/^/   /'
    fi
else
    echo -e "${RED}❌ Mount succeeded but directory appears empty${NC}"
    exit 1
fi

# Success message and instructions
echo -e "\n${GREEN}🎉 SUCCESS!${NC}"
echo "=================================="
echo -e "${BLUE}Your NFS share is now accessible at:${NC}"
echo -e "   📁 $MOUNT_POINT"
echo ""
echo -e "${BLUE}You can now:${NC}"
echo -e "   📖 Browse files: ${YELLOW}nautilus '$MOUNT_POINT'${NC} (or your file manager)"
echo -e "   📝 Edit files: ${YELLOW}gedit '$MOUNT_POINT/welcome.txt'${NC}"
echo -e "   📤 Copy files: ${YELLOW}cp ~/Documents/myfile.txt '$MOUNT_POINT/'${NC}"
echo -e "   🔍 List files: ${YELLOW}ls -la '$MOUNT_POINT'${NC}"
echo ""
echo -e "${YELLOW}To unmount later:${NC}"
echo -e "   umount '$MOUNT_POINT' ${RED}(or)${NC} fusermount -u '$MOUNT_POINT'"
echo ""
echo -e "${BLUE}Access from other computers:${NC}"
echo -e "   ${YELLOW}nfs://$NFS_SERVER$NFS_PATH${NC}"

# Open file manager if available
if command -v nautilus >/dev/null 2>&1; then
    echo ""
    read -p "🔍 Open file manager to browse files? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        nautilus "$MOUNT_POINT" &
        echo -e "${GREEN}📂 File manager opened!${NC}"
    fi
elif command -v dolphin >/dev/null 2>&1; then
    echo ""
    read -p "🔍 Open file manager to browse files? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        dolphin "$MOUNT_POINT" &
        echo -e "${GREEN}📂 File manager opened!${NC}"
    fi
fi