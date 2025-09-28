#!/bin/bash

echo "🧪 Quick NFS Test for MoxNAS"
echo "============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ $2${NC}"
        ((TESTS_FAILED++))
    fi
}

echo "1️⃣  Checking NFS Server Status..."
systemctl is-active --quiet nfs-server
test_result $? "NFS server is running"

systemctl is-active --quiet rpcbind
test_result $? "RPC bind service is running"

echo ""
echo "2️⃣  Checking Network Ports..."
ss -tlnp | grep -q :2049
test_result $? "NFS port 2049 is listening"

ss -tlnp | grep -q :111
test_result $? "RPC port 111 is listening"

echo ""
echo "3️⃣  Checking NFS Exports..."
EXPORTS=$(showmount -e localhost 2>/dev/null)
echo "$EXPORTS" | grep -q "MoxNAS"
test_result $? "MoxNAS datasets are exported"

if [ $? -eq 0 ]; then
    echo -e "${YELLOW}Current exports:${NC}"
    echo "$EXPORTS" | grep MoxNAS
fi

echo ""
echo "4️⃣  Testing File System Access..."
DATASET_PATH="/home/wassim/Documents/MoxNAS/storage_pools/data/datasets/www"
if [ -d "$DATASET_PATH" ]; then
    test_result 0 "Dataset directory exists"
    
    # Test write
    TEST_FILE="$DATASET_PATH/nfs-quick-test.tmp"
    echo "Test content" > "$TEST_FILE" 2>/dev/null
    test_result $? "Can write to dataset directory"
    
    # Test read
    if [ -f "$TEST_FILE" ]; then
        cat "$TEST_FILE" >/dev/null 2>&1
        test_result $? "Can read from dataset directory"
        rm -f "$TEST_FILE"
    fi
else
    test_result 1 "Dataset directory exists"
fi

echo ""
echo "5️⃣  Testing NFS Mount (requires sudo)..."
MOUNT_POINT="/tmp/moxnas-quick-test-$$"
mkdir -p "$MOUNT_POINT"

# Find the first MoxNAS export
EXPORT_PATH=$(echo "$EXPORTS" | grep MoxNAS | head -1 | awk '{print $1}')

if [ -n "$EXPORT_PATH" ]; then
    echo "Attempting to mount: $EXPORT_PATH"
    
    if sudo mount -t nfs "localhost:$EXPORT_PATH" "$MOUNT_POINT" 2>/dev/null; then
        test_result 0 "NFS mount successful"
        
        # Test operations on mounted share
        NFS_TEST_FILE="$MOUNT_POINT/nfs-mount-test.tmp"
        echo "NFS mount test" | sudo tee "$NFS_TEST_FILE" >/dev/null 2>&1
        test_result $? "Write through NFS mount"
        
        if [ -f "$NFS_TEST_FILE" ]; then
            sudo cat "$NFS_TEST_FILE" >/dev/null 2>&1
            test_result $? "Read through NFS mount"
            sudo rm -f "$NFS_TEST_FILE"
        fi
        
        # Unmount
        sudo umount "$MOUNT_POINT" 2>/dev/null
        test_result $? "NFS unmount successful"
    else
        test_result 1 "NFS mount successful"
    fi
else
    test_result 1 "Found MoxNAS export to test"
fi

rmdir "$MOUNT_POINT" 2>/dev/null

echo ""
echo "6️⃣  Checking MoxNAS Database..."
cd /home/wassim/Documents/MoxNAS
python3 -c "
import os, sys
os.environ['DATABASE_URL'] = 'sqlite:///local_moxnas.db'
os.environ['FLASK_ENV'] = 'development'
from app import create_app, db
from app.models import Share, ShareProtocol
app = create_app()
with app.app_context():
    nfs_shares = Share.query.filter_by(protocol=ShareProtocol.NFS).count()
    print(f'NFS shares in database: {nfs_shares}')
    exit(0 if nfs_shares > 0 else 1)
" 2>/dev/null
test_result $? "NFS shares exist in MoxNAS database"

echo ""
echo "📊 Test Summary"
echo "==============="
echo -e "${GREEN}Tests Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed! NFS is working correctly.${NC}"
    echo ""
    echo "🔗 You can access your NFS shares at:"
    echo "$EXPORTS" | grep MoxNAS | sed 's/^/   /'
    echo ""
    echo "📝 To mount from another computer:"
    echo "   sudo mount -t nfs $(hostname -I | awk '{print $1}'):$EXPORT_PATH /mnt/moxnas"
else
    echo -e "${RED}⚠️  Some tests failed. Check the output above for details.${NC}"
fi