#!/bin/bash
#
# MoxNAS Manual Installation Helper
# This script helps you manually create the container with the correct storage
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

CONTAINER_ID=${1:-200}

echo "=========================================="
echo "   MoxNAS Manual Installation Helper     "
echo "=========================================="
echo ""

log_info "Analyzing your Proxmox storage configuration..."

# Check storage
log_info "Available storage:"
pvesm status

echo ""

# Check LVM
log_info "LVM Volume Groups:"
vgs 2>/dev/null || log_warning "No LVM volume groups found"

echo ""

log_info "LVM Logical Volumes:" 
lvs 2>/dev/null || log_warning "No LVM logical volumes found"

echo ""

# Find best storage for containers
log_info "Checking storage types that support containers..."

BEST_STORAGE=""
while IFS= read -r line; do
    storage_name=$(echo "$line" | awk '{print $1}')
    storage_type=$(echo "$line" | awk '{print $2}')
    storage_status=$(echo "$line" | awk '{print $3}')
    storage_total=$(echo "$line" | awk '{print $4}')
    storage_avail=$(echo "$line" | awk '{print $5}')
    
    # Skip header and inactive storage
    if [[ "$storage_name" == "Name" ]] || [[ "$storage_status" != "active" ]]; then
        continue
    fi
    
    # Show storage info
    echo "Storage: $storage_name"
    echo "  Type: $storage_type"
    echo "  Status: $storage_status"
    echo "  Available: $storage_avail KB"
    
    # Check if supports containers
    content=$(pvesm status -storage "$storage_name" 2>/dev/null | grep -o "content.*" || echo "unknown")
    echo "  Content types: $content"
    
    if echo "$content" | grep -q "images\|rootdir"; then
        if [[ "$storage_type" == "lvmthin" ]] || [[ "$storage_type" == "dir" ]]; then
            if [ -z "$BEST_STORAGE" ]; then
                BEST_STORAGE="$storage_name"
                log_success "  ✅ RECOMMENDED for containers"
            else
                log_success "  ✅ Also suitable for containers"
            fi
        else
            log_info "  ⚠️  Supports containers but not optimal type"
        fi
    else
        log_warning "  ❌ Does not support containers"
    fi
    echo ""
    
done < <(pvesm status)

# Check available templates
log_info "Available Ubuntu templates:"
TEMPLATE=$(pveam list local | grep ubuntu-22.04 | head -1 | awk '{print $1}' | sed 's/.*://')
if [ -n "$TEMPLATE" ]; then
    log_success "Found template: $TEMPLATE"
else
    log_warning "No Ubuntu 22.04 template found. Download with:"
    echo "  pveam update"
    echo "  pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
    TEMPLATE="ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
fi

echo ""

# Generate manual commands
if [ -n "$BEST_STORAGE" ]; then
    log_success "RECOMMENDED INSTALLATION COMMAND:"
    echo "----------------------------------------"
    echo "pct create $CONTAINER_ID local:vztmpl/$TEMPLATE \\"
    echo "  --hostname moxnas \\"
    echo "  --password moxnas123 \\"
    echo "  --cores 2 \\"
    echo "  --memory 2048 \\"
    echo "  --rootfs $BEST_STORAGE:8G \\"
    echo "  --net0 name=eth0,bridge=vmbr0,ip=dhcp \\"
    echo "  --features nesting=1 \\"
    echo "  --unprivileged 0 \\"
    echo "  --start 1"
    echo "----------------------------------------"
    
    log_info "After container creation, install MoxNAS with:"
    echo "pct exec $CONTAINER_ID -- bash -c 'apt update && apt install -y git curl python3-pip'"
    echo "pct exec $CONTAINER_ID -- bash -c 'cd /opt && git clone https://github.com/Mezraniwassim/MoxNas.git moxnas'"
    echo "pct exec $CONTAINER_ID -- bash -c 'cd /opt/moxnas && python3 start_moxnas.py --production'"
    
else
    log_error "No suitable storage found for containers!"
    log_error "Please configure storage that supports 'images' or 'rootdir' content types."
    log_error "Check Proxmox web interface: Datacenter -> Storage"
fi

echo ""
log_info "Manual installation helper completed."