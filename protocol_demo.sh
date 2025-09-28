#!/bin/bash

# MoxNAS Protocol Testing Demo
# Shows how to access the same data through different protocols

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SERVER_IP="192.168.1.109"
DATA_PATH="/home/wassim/Documents/MoxNAS/storage_pools/data/datasets/www"
NFS_PATH="$DATA_PATH"
TEST_FILE="protocol-test-$(date +%s).txt"

echo -e "${BLUE}🌐 MoxNAS Multi-Protocol Access Demo${NC}"
echo "===================================="
echo -e "Testing access to the same data through different protocols"
echo -e "Dataset: ${YELLOW}$DATA_PATH${NC}"
echo

# Test 1: Direct File System Access
echo -e "${PURPLE}1️⃣ DIRECT FILE SYSTEM ACCESS${NC}"
echo "-----------------------------"
echo "Writing test file directly to filesystem..."
echo "Test from filesystem access - $(date)" > "$DATA_PATH/$TEST_FILE"
echo -e "${GREEN}✅ File written directly${NC}"
echo -e "Content: $(cat "$DATA_PATH/$TEST_FILE")"
echo

# Test 2: NFS Protocol
echo -e "${PURPLE}2️⃣ NFS (Network File System) PROTOCOL${NC}"
echo "---------------------------------------"

# Check if already mounted
if mount | grep -q "nfs.*MoxNAS-NFS"; then
    echo -e "${GREEN}✅ NFS already mounted${NC}"
    NFS_MOUNT="$HOME/Desktop/MoxNAS-NFS"
else
    echo "Mounting NFS share..."
    NFS_MOUNT="/tmp/nfs-protocol-test"
    mkdir -p "$NFS_MOUNT"
    
    if sudo mount -t nfs "$SERVER_IP:$NFS_PATH" "$NFS_MOUNT" 2>/dev/null; then
        echo -e "${GREEN}✅ NFS mounted successfully${NC}"
        MOUNTED_NFS=true
    else
        echo -e "${RED}❌ NFS mount failed${NC}"
        NFS_MOUNT="$HOME/Desktop/MoxNAS-NFS"  # Use existing mount
    fi
fi

echo -e "📁 NFS Access: ${YELLOW}nfs://$SERVER_IP$NFS_PATH${NC}"
echo -e "📂 Mount point: ${YELLOW}$NFS_MOUNT${NC}"

if [ -f "$NFS_MOUNT/$TEST_FILE" ]; then
    echo -e "${GREEN}✅ Test file visible via NFS${NC}"
    echo -e "NFS Content: $(cat "$NFS_MOUNT/$TEST_FILE")"
    
    # Write via NFS
    echo "Test from NFS access - $(date)" >> "$NFS_MOUNT/$TEST_FILE"
    echo -e "${GREEN}✅ File modified via NFS${NC}"
else
    echo -e "${RED}❌ Test file not visible via NFS${NC}"
fi

# Show NFS commands for other computers
echo -e "${BLUE}🔧 NFS Access Commands:${NC}"
echo -e "   showmount -e $SERVER_IP"
echo -e "   sudo mount -t nfs $SERVER_IP:$NFS_PATH /mnt/moxnas"
echo

# Test 3: SMB/CIFS Protocol  
echo -e "${PURPLE}3️⃣ SMB/CIFS (Samba) PROTOCOL${NC}"
echo "------------------------------"

# Check SMB service
if systemctl is-active --quiet smbd; then
    echo -e "${GREEN}✅ SMB/Samba service is running${NC}"
    
    # Test SMB access
    echo "Testing SMB share access..."
    if smbclient -L localhost -N 2>/dev/null | grep -q "Disk"; then
        echo -e "${GREEN}✅ SMB server is accessible${NC}"
        echo "Available SMB shares:"
        smbclient -L localhost -N 2>/dev/null | grep "Disk" | sed 's/^/   📁 /'
    else
        echo -e "${YELLOW}⚠️ SMB accessible but no custom shares found${NC}"
        echo "📝 SMB configuration: /home/wassim/Documents/MoxNAS/config_simulation/smb.conf"
    fi
    
    echo -e "${BLUE}🔧 SMB Access Methods:${NC}"
    echo -e "   File manager: ${YELLOW}smb://$SERVER_IP/${NC}"
    echo -e "   Windows: ${YELLOW}\\\\$SERVER_IP\\share-name${NC}"
    echo -e "   Linux: ${YELLOW}sudo mount -t cifs //$SERVER_IP/share-name /mnt/smb${NC}"
else
    echo -e "${YELLOW}⚠️ SMB/Samba service not running${NC}"
    echo "To start: sudo systemctl start smbd"
fi
echo

# Test 4: FTP Protocol
echo -e "${PURPLE}4️⃣ FTP (File Transfer Protocol)${NC}"
echo "-------------------------------"

# Check FTP service
if systemctl is-active --quiet vsftpd; then
    echo -e "${GREEN}✅ FTP service is running${NC}"
    
    # Test FTP access
    echo "Testing FTP server access..."
    if nc -z localhost 21 2>/dev/null; then
        echo -e "${GREEN}✅ FTP server is listening on port 21${NC}"
        
        # Check FTP share directory
        FTP_SHARE_DIR="/home/wassim/Documents/MoxNAS/config_simulation/ftp_shares"
        if [ -d "$FTP_SHARE_DIR" ]; then
            echo -e "${GREEN}✅ FTP shares directory exists${NC}"
            echo "📁 FTP shares:"
            ls -la "$FTP_SHARE_DIR" | tail -n +2 | sed 's/^/   /'
            
            if [ -L "$FTP_SHARE_DIR/www-ftp" ]; then
                echo -e "${GREEN}✅ FTP link to dataset exists${NC}"
                echo -e "🔗 Links to: $(readlink "$FTP_SHARE_DIR/www-ftp")"
            fi
        fi
    else
        echo -e "${YELLOW}⚠️ FTP server not listening on port 21${NC}"
    fi
    
    echo -e "${BLUE}🔧 FTP Access Methods:${NC}"
    echo -e "   File manager: ${YELLOW}ftp://$SERVER_IP/${NC}"
    echo -e "   Command line: ${YELLOW}ftp $SERVER_IP${NC}"
    echo -e "   Browser: ${YELLOW}ftp://$SERVER_IP/${NC}"
else
    echo -e "${YELLOW}⚠️ FTP service not running${NC}"
    echo "To start: sudo systemctl start vsftpd"
fi
echo

# Test 5: HTTP/Web Access (Bonus)
echo -e "${PURPLE}5️⃣ HTTP/WEB ACCESS (MoxNAS Interface)${NC}"
echo "-----------------------------------"

if curl -s http://localhost:5000 >/dev/null; then
    echo -e "${GREEN}✅ MoxNAS web interface is accessible${NC}"
    echo -e "${BLUE}🌐 Web Interface: ${YELLOW}http://$SERVER_IP:5000${NC}"
    echo -e "   📊 Dashboard: http://$SERVER_IP:5000/"
    echo -e "   🗂️ Storage: http://$SERVER_IP:5000/storage/"
    echo -e "   🌐 Shares: http://$SERVER_IP:5000/shares/"
else
    echo -e "${YELLOW}⚠️ MoxNAS web interface not running${NC}"
    echo "To start: python3 run_local.py"
fi
echo

# Summary and Verification
echo -e "${PURPLE}📊 VERIFICATION & SUMMARY${NC}"
echo "========================="

echo "Checking if test file exists and has been modified..."
if [ -f "$DATA_PATH/$TEST_FILE" ]; then
    echo -e "${GREEN}✅ Test file exists in original location${NC}"
    echo -e "${BLUE}📄 Final file content:${NC}"
    cat "$DATA_PATH/$TEST_FILE" | sed 's/^/   /'
    
    # Count lines to see if NFS write worked
    LINES=$(wc -l < "$DATA_PATH/$TEST_FILE")
    if [ "$LINES" -gt 1 ]; then
        echo -e "${GREEN}✅ File was modified through network protocols${NC}"
    fi
else
    echo -e "${RED}❌ Test file not found${NC}"
fi

echo
echo -e "${GREEN}🎉 PROTOCOL TESTING COMPLETED!${NC}"
echo "================================"
echo -e "${BLUE}Your data is accessible through:${NC}"
echo -e "   🗄️ Direct: $DATA_PATH"
echo -e "   📁 NFS: nfs://$SERVER_IP$NFS_PATH"
echo -e "   🖥️ SMB: smb://$SERVER_IP/share-name"
echo -e "   📡 FTP: ftp://$SERVER_IP/"
echo -e "   🌐 Web: http://$SERVER_IP:5000"

echo
echo -e "${YELLOW}💡 Tips:${NC}"
echo "   • NFS is best for Linux/Unix systems"
echo "   • SMB/CIFS is best for Windows compatibility"
echo "   • FTP is universal but less secure"
echo "   • Use the web interface for management"

# Cleanup
if [ "$MOUNTED_NFS" = true ]; then
    echo
    echo "Cleaning up temporary NFS mount..."
    sudo umount "$NFS_MOUNT" 2>/dev/null || true
    rmdir "$NFS_MOUNT" 2>/dev/null || true
fi

echo
echo -e "${GREEN}✅ Demo completed successfully!${NC}"