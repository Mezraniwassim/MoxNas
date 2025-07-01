#!/bin/bash
#
# MoxNAS Proxmox Configuration Script
# Configures Proxmox host credentials for MoxNAS integration
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration file path
CONFIG_FILE="/opt/moxnas/.env"
PROXMOX_CONFIG="/opt/moxnas/config/proxmox.conf"

echo "=========================================="
echo "     MoxNAS Proxmox Configuration        "
echo "=========================================="
echo ""

# Function to prompt for input with validation
prompt_input() {
    local prompt="$1"
    local var_name="$2"
    local default="$3"
    local hide_input="$4"
    
    while true; do
        if [ "$hide_input" = "true" ]; then
            echo -n "$prompt: "
            read -s input
            echo ""
        else
            if [ -n "$default" ]; then
                echo -n "$prompt [$default]: "
            else
                echo -n "$prompt: "
            fi
            read input
        fi
        
        # Use default if input is empty
        if [ -z "$input" ] && [ -n "$default" ]; then
            input="$default"
        fi
        
        # Validate input
        if [ -n "$input" ]; then
            eval "$var_name='$input'"
            break
        else
            log_warning "This field is required. Please enter a value."
        fi
    done
}

# Function to validate IP address
validate_ip() {
    local ip=$1
    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        return 0
    else
        return 1
    fi
}

# Function to test Proxmox connection
test_proxmox_connection() {
    local host="$1"
    local port="$2"
    local username="$3"
    local password="$4"
    local realm="$5"
    
    log_info "Testing connection to Proxmox..."
    
    # Try to connect to Proxmox API
    if curl -s --connect-timeout 10 --insecure \
        -d "username=${username}@${realm}&password=${password}" \
        "https://${host}:${port}/api2/json/access/ticket" > /dev/null 2>&1; then
        log_success "Connection to Proxmox successful!"
        return 0
    else
        log_warning "Connection test failed. Please verify credentials."
        return 1
    fi
}

# Collect Proxmox configuration
log_info "Please provide your Proxmox host information:"
echo ""

# Get Proxmox host IP
while true; do
    prompt_input "Proxmox Host IP address" PROXMOX_HOST
    if validate_ip "$PROXMOX_HOST"; then
        break
    else
        log_warning "Invalid IP address format. Please try again."
    fi
done

# Get Proxmox port
prompt_input "Proxmox Web UI Port" PROXMOX_PORT "8006"

# Get username
prompt_input "Proxmox Username" PROXMOX_USERNAME "root"

# Get realm
prompt_input "Proxmox Realm" PROXMOX_REALM "pam"

# Get password
prompt_input "Proxmox Password" PROXMOX_PASSWORD "" "true"

# SSL verification
echo ""
log_info "SSL Certificate Verification:"
echo "1) Verify SSL certificates (recommended for production)"
echo "2) Skip SSL verification (for self-signed certificates)"
echo -n "Choose option [1]: "
read ssl_choice

if [ "$ssl_choice" = "2" ]; then
    PROXMOX_SSL_VERIFY="False"
    log_warning "SSL verification disabled"
else
    PROXMOX_SSL_VERIFY="True"
    log_info "SSL verification enabled"
fi

echo ""

# Test connection
if test_proxmox_connection "$PROXMOX_HOST" "$PROXMOX_PORT" "$PROXMOX_USERNAME" "$PROXMOX_PASSWORD" "$PROXMOX_REALM"; then
    echo ""
    log_success "Proxmox connection verified!"
else
    echo ""
    log_warning "Connection test failed, but configuration will be saved anyway."
    echo -n "Continue with configuration? (y/N): "
    read continue_choice
    if [ "$continue_choice" != "y" ] && [ "$continue_choice" != "Y" ]; then
        log_info "Configuration cancelled."
        exit 1
    fi
fi

# Create configuration directory if it doesn't exist
mkdir -p "$(dirname "$CONFIG_FILE")"
mkdir -p "$(dirname "$PROXMOX_CONFIG")"

# Update .env file
log_info "Updating MoxNAS configuration..."

# Create or update .env file
if [ -f "$CONFIG_FILE" ]; then
    # Remove existing Proxmox settings
    sed -i '/^PROXMOX_/d' "$CONFIG_FILE"
else
    # Create new .env file with basic settings
    cat > "$CONFIG_FILE" << EOF
# MoxNAS Configuration
SECRET_KEY=moxnas-secret-key-$(openssl rand -hex 32)
DEBUG=False
ALLOWED_HOSTS=*
MOXNAS_STORAGE_PATH=/mnt/storage
MOXNAS_CONFIG_PATH=/etc/moxnas
MOXNAS_LOG_PATH=/var/log/moxnas
CORS_ALLOW_ALL_ORIGINS=True
EOF
fi

# Add Proxmox configuration to .env
cat >> "$CONFIG_FILE" << EOF

# Proxmox Configuration
PROXMOX_HOST=$PROXMOX_HOST
PROXMOX_PORT=$PROXMOX_PORT
PROXMOX_USERNAME=$PROXMOX_USERNAME
PROXMOX_PASSWORD=$PROXMOX_PASSWORD
PROXMOX_REALM=$PROXMOX_REALM
PROXMOX_SSL_VERIFY=$PROXMOX_SSL_VERIFY
EOF

# Create detailed Proxmox configuration file
cat > "$PROXMOX_CONFIG" << EOF
# MoxNAS Proxmox Integration Configuration
# Generated on $(date)

[proxmox]
host = $PROXMOX_HOST
port = $PROXMOX_PORT
username = $PROXMOX_USERNAME
realm = $PROXMOX_REALM
ssl_verify = $PROXMOX_SSL_VERIFY

[moxnas]
# Default container settings
default_memory = 2048
default_cores = 2
default_disk_size = 8
default_template = ubuntu-22.04-standard_22.04-1_amd64.tar.zst
default_storage = local-lvm

# Network settings
bridge = vmbr0
dhcp = true

# Container features
nesting = true
unprivileged = false
onboot = true
EOF

# Set appropriate permissions
chmod 600 "$CONFIG_FILE"
chmod 600 "$PROXMOX_CONFIG"

log_success "Configuration saved successfully!"

echo ""
echo "=========================================="
echo "         Configuration Summary            "
echo "=========================================="
echo ""
echo "Proxmox Host: $PROXMOX_HOST:$PROXMOX_PORT"
echo "Username: $PROXMOX_USERNAME@$PROXMOX_REALM"
echo "SSL Verify: $PROXMOX_SSL_VERIFY"
echo ""
echo "Configuration files:"
echo "  Environment: $CONFIG_FILE"
echo "  Proxmox Config: $PROXMOX_CONFIG"
echo ""

# Offer to restart MoxNAS service if running
if systemctl is-active moxnas &> /dev/null; then
    echo -n "Restart MoxNAS service to apply changes? (y/N): "
    read restart_choice
    if [ "$restart_choice" = "y" ] || [ "$restart_choice" = "Y" ]; then
        log_info "Restarting MoxNAS service..."
        systemctl restart moxnas
        log_success "MoxNAS service restarted!"
    fi
fi

echo ""
log_info "Next steps:"
echo "1. Access MoxNAS web interface"
echo "2. Go to 'Proxmox' tab to manage containers"
echo "3. Test container creation and management"
echo ""
log_success "Proxmox configuration completed!"