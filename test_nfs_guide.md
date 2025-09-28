# 🧪 How to Test NFS Functionality in MoxNAS

This guide shows you multiple ways to verify that NFS is working correctly.

## 📋 Prerequisites

- MoxNAS running at http://localhost:5000
- At least one dataset created
- NFS share configured for the dataset

## 🔍 Method 1: Quick Status Check

### Check NFS Services
```bash
# Check if NFS server is running
systemctl status nfs-server

# Check if RPC is running
systemctl status rpcbind

# Check NFS ports are listening
ss -tlnp | grep :2049  # NFS port
ss -tlnp | grep :111   # RPC port
```

### Check Current Exports
```bash
# Show all current NFS exports
showmount -e localhost

# Show detailed export information
exportfs -v
```

## 🌐 Method 2: Test via MoxNAS Interface

1. **Open MoxNAS**: Go to http://localhost:5000
2. **Login**: Use admin/AdminPassword123!
3. **Navigate**: Go to Shares → View Shares
4. **Check Status**: Look for NFS shares with "Active" status
5. **View Details**: Click on a share to see configuration

## 💾 Method 3: Create and Test a New NFS Share

### Step 1: Create a Dataset
1. Go to Storage → Datasets → Create Dataset
2. Enter name: `test-nfs`
3. Select pool: `data`
4. Click Create

### Step 2: Create NFS Share
1. Go to Shares → Create Share
2. Fill in:
   - Name: `test-share`
   - Dataset: `test-nfs`
   - Protocol: `NFS`
   - Read-only: No
   - Guest access: Yes
3. Click Create

### Step 3: Verify Share Creation
```bash
# Check if export was added
showmount -e localhost
# Should show: /home/wassim/Documents/MoxNAS/storage_pools/data/datasets/test-nfs
```

## 🔬 Method 4: Mount and Test File Operations

### Mount the NFS Share
```bash
# Create mount point
mkdir -p /tmp/nfs-test

# Mount the share
sudo mount -t nfs localhost:/home/wassim/Documents/MoxNAS/storage_pools/data/datasets/www /tmp/nfs-test

# Check if mounted
mount | grep nfs
df -h | grep nfs
```

### Test File Operations
```bash
# Test writing
echo "Hello from NFS client" | sudo tee /tmp/nfs-test/client-test.txt

# Test reading
cat /tmp/nfs-test/client-test.txt

# Test listing
ls -la /tmp/nfs-test/

# Verify file appears in original location
ls -la /home/wassim/Documents/MoxNAS/storage_pools/data/datasets/www/
```

### Cleanup
```bash
# Unmount
sudo umount /tmp/nfs-test

# Remove test directory
rmdir /tmp/nfs-test
```

## 🖥️ Method 5: Test from Another Computer

### On the MoxNAS Server
```bash
# Get server IP address
ip addr show | grep inet

# Make sure NFS is accessible externally
sudo ufw allow nfs  # If firewall is running
```

### On Another Linux/Mac Computer
```bash
# Check if you can see the exports (replace IP_ADDRESS)
showmount -e IP_ADDRESS

# Mount from remote computer
sudo mkdir -p /mnt/moxnas-test
sudo mount -t nfs IP_ADDRESS:/home/wassim/Documents/MoxNAS/storage_pools/data/datasets/www /mnt/moxnas-test

# Test operations
ls -la /mnt/moxnas-test/
echo "Remote test" | sudo tee /mnt/moxnas-test/remote-test.txt

# Unmount when done
sudo umount /mnt/moxnas-test
```

## 🐧 Method 6: Automated Test Script

Save this as `test_nfs.sh`:

```bash
#!/bin/bash

echo "🧪 NFS Functionality Test"
echo "========================="

# Test 1: Service Status
echo "1️⃣  Checking NFS services..."
if systemctl is-active --quiet nfs-server; then
    echo "✅ NFS server is running"
else
    echo "❌ NFS server is not running"
    exit 1
fi

# Test 2: Exports
echo "2️⃣  Checking NFS exports..."
if showmount -e localhost | grep -q "/home/wassim/Documents/MoxNAS"; then
    echo "✅ MoxNAS datasets are exported"
    showmount -e localhost | grep MoxNAS
else
    echo "❌ No MoxNAS exports found"
fi

# Test 3: Mount Test
echo "3️⃣  Testing NFS mount..."
TEST_MOUNT="/tmp/nfs-mount-test-$$"
mkdir -p "$TEST_MOUNT"

EXPORT_PATH=$(showmount -e localhost | grep MoxNAS | head -1 | awk '{print $1}')
if [ -n "$EXPORT_PATH" ]; then
    if sudo mount -t nfs "localhost:$EXPORT_PATH" "$TEST_MOUNT"; then
        echo "✅ Successfully mounted NFS share"
        
        # Test file operations
        TEST_FILE="$TEST_MOUNT/nfs-test-$$"
        if echo "NFS test content" | sudo tee "$TEST_FILE" > /dev/null; then
            echo "✅ Write operation successful"
            
            if [ -f "$TEST_FILE" ] && grep -q "NFS test content" "$TEST_FILE"; then
                echo "✅ Read operation successful"
            else
                echo "❌ Read operation failed"
            fi
            
            sudo rm -f "$TEST_FILE"
        else
            echo "❌ Write operation failed"
        fi
        
        sudo umount "$TEST_MOUNT"
        echo "✅ Unmount successful"
    else
        echo "❌ Mount failed"
    fi
else
    echo "❌ No export path found"
fi

rmdir "$TEST_MOUNT"

echo "✅ NFS test completed!"
```

Make it executable and run:
```bash
chmod +x test_nfs.sh
./test_nfs.sh
```

## 🔍 Method 7: Check MoxNAS Logs

```bash
# Check application logs
tail -f /home/wassim/Documents/MoxNAS/logs/app.log  # if exists

# Or check the running application output
# Look for NFS-related messages in the console where you started MoxNAS
```

## 📊 What Success Looks Like

### ✅ Successful NFS Test Results:
- NFS server status: **Active**
- RPC bind status: **Active**
- Ports 2049 and 111: **Listening**
- Exports visible: **showmount shows your datasets**
- Mount successful: **No errors when mounting**
- File operations work: **Can read/write files**
- MoxNAS interface shows: **Active NFS shares**

### ❌ Common Issues and Solutions:

**Problem**: "Permission denied" on /etc/exports
- **Solution**: This is normal in development mode. MoxNAS uses config simulation.

**Problem**: "No exports" shown
- **Solution**: Create an NFS share through MoxNAS interface first.

**Problem**: "Connection refused" when mounting
- **Solution**: Check if NFS server and RPC are running, verify firewall settings.

**Problem**: Can mount but can't write files
- **Solution**: Check share permissions, ensure it's not read-only.

## 🎯 Quick Success Test

The fastest way to verify NFS is working:

```bash
# 1. Check exports
showmount -e localhost | grep MoxNAS

# 2. Quick mount test  
sudo mkdir /tmp/quick-nfs-test
sudo mount -t nfs localhost:/home/wassim/Documents/MoxNAS/storage_pools/data/datasets/www /tmp/quick-nfs-test
ls /tmp/quick-nfs-test
sudo umount /tmp/quick-nfs-test
rmdir /tmp/quick-nfs-test

echo "✅ If no errors appeared, NFS is working!"
```

This should complete without errors if NFS is properly functional.