#!/bin/bash
#
# MoxNAS Proxmox Storage Debug Script
# This script helps diagnose storage configuration issues
#

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

echo "=========================================="
echo "    MoxNAS Proxmox Storage Debugger      "
echo "=========================================="
echo ""

# Check if running on Proxmox
log_info "Checking if running on Proxmox VE..."
if ! command -v pct &> /dev/null; then
    log_error "This script must be run on a Proxmox VE host"
    exit 1
fi
log_success "Running on Proxmox VE"

# Show Proxmox version
log_info "Proxmox VE version:"
pveversion

echo ""

# Show storage status
log_info "Storage status:"
echo "----------------------------------------"
pvesm status
echo "----------------------------------------"

echo ""

# Show detailed storage information
log_info "Detailed storage information:"
echo "----------------------------------------"
while IFS= read -r line; do
    storage_name=$(echo "$line" | awk '{print $1}')
    storage_type=$(echo "$line" | awk '{print $2}')
    storage_status=$(echo "$line" | awk '{print $3}')
    
    # Skip header
    if [[ "$storage_name" == "Name" ]]; then
        continue
    fi
    
    echo "Storage: $storage_name"
    echo "  Type: $storage_type"
    echo "  Status: $storage_status"
    
    # Get storage content types
    if [[ "$storage_status" == "active" ]]; then
        content=$(pvesm status -storage "$storage_name" 2>/dev/null | grep -o "content.*" | head -1)
        echo "  Content: $content"
        
        # Check if supports containers
        if echo "$content" | grep -q "vztmpl\|rootdir\|images"; then
            log_success "  ✅ Supports containers"
        else
            log_warning "  ⚠️  May not support containers"
        fi
    else
        log_error "  ❌ Storage not active"
    fi
    echo ""
done < <(pvesm status)

echo "----------------------------------------"

# Check for common storage configurations
log_info "Checking common storage configurations:"

# Check for local storage
if pvesm status | grep -q "^local.*active"; then
    log_success "✅ 'local' storage found"
else
    log_warning "⚠️  'local' storage not found"
fi

# Check for local-lvm
if pvesm status | grep -q "^local-lvm.*active"; then
    log_success "✅ 'local-lvm' storage found"
else
    log_warning "⚠️  'local-lvm' storage not found"
fi

# Check for local-zfs
if pvesm status | grep -q "^local-zfs.*active"; then
    log_success "✅ 'local-zfs' storage found"
else
    log_warning "⚠️  'local-zfs' storage not found"
fi

echo ""

# Show recommended storage for MoxNAS
log_info "Recommended storage for MoxNAS containers:"
RECOMMENDED_STORAGE=""

# Find best storage
while IFS= read -r line; do
    storage_name=$(echo "$line" | awk '{print $1}')
    storage_type=$(echo "$line" | awk '{print $2}')
    storage_status=$(echo "$line" | awk '{print $3}')
    
    # Skip header and inactive storage
    if [[ "$storage_name" == "Name" ]] || [[ "$storage_status" != "active" ]]; then
        continue
    fi
    
    # Check if this storage supports containers
    content=$(pvesm status -storage "$storage_name" 2>/dev/null | grep -o "content.*" | head -1)
    if echo "$content" | grep -q "vztmpl\|rootdir\|images"; then
        RECOMMENDED_STORAGE="$storage_name"
        log_success "✅ Recommended: $storage_name (type: $storage_type)"
        break
    fi
done < <(pvesm status)

if [ -z "$RECOMMENDED_STORAGE" ]; then
    log_error "❌ No suitable storage found for containers"
    echo ""
    log_info "To fix this, you may need to:"
    log_info "1. Configure storage in Proxmox web interface"
    log_info "2. Enable container content type on existing storage"
    log_info "3. Check disk space and permissions"
else
    echo ""
    log_info "Use this storage for MoxNAS installation:"
    echo "  Storage name: $RECOMMENDED_STORAGE"
    echo ""
    log_info "Manual container creation command:"
    echo "pct create 200 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \\"
    echo "  --hostname moxnas \\"
    echo "  --password moxnas123 \\"
    echo "  --cores 2 \\"
    echo "  --memory 2048 \\"
    echo "  --rootfs $RECOMMENDED_STORAGE:8G \\"
    echo "  --net0 name=eth0,bridge=vmbr0,ip=dhcp \\"
    echo "  --features nesting=1 \\"
    echo "  --unprivileged 0 \\"
    echo "  --start 1"
fi

echo ""
log_info "Debug completed. Check the information above to resolve storage issues."