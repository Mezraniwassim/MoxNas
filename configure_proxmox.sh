#!/bin/bash
"""
MoxNAS Proxmox Configuration Script
Easily configure MoxNAS to connect with your Proxmox environment
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CONTAINER_ID="200"
PROXMOX_HOST=""
PROXMOX_USERNAME="root"
PROXMOX_PASSWORD=""
PROXMOX_REALM="pam"
PROXMOX_PORT="8006"
PROXMOX_SSL_VERIFY="False"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
🔧 MoxNAS Proxmox Configuration Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -c, --container-id ID    MoxNAS container ID (default: 200)
    -h, --host HOST         Proxmox host IP address
    -u, --username USER     Proxmox username (default: root)
    -p, --password PASS     Proxmox password
    -r, --realm REALM       Proxmox realm (default: pam)
    -P, --port PORT         Proxmox port (default: 8006)
    --ssl-verify            Enable SSL verification (default: disabled)
    --interactive           Interactive configuration mode
    --help                  Show this help message

EXAMPLES:
    # Interactive mode (recommended)
    $0 --interactive

    # Direct configuration
    $0 -h 192.168.1.100 -p your_password

    # Custom container and settings
    $0 -c 201 -h 10.0.0.5 -u admin -p secret123 -r pve

NOTES:
    - The script will test the connection before applying configuration
    - MoxNAS service will be restarted after configuration
    - All sensitive data is handled securely
EOF
}

# Interactive configuration
interactive_config() {
    log_info "🎯 Interactive Proxmox Configuration"
    echo "=================================="
    echo ""

    # Get container ID
    read -p "Enter MoxNAS container ID [default: 200]: " input
    CONTAINER_ID=${input:-200}

    # Verify container exists
    if ! pct status "$CONTAINER_ID" &>/dev/null; then
        log_error "Container $CONTAINER_ID does not exist!"
        exit 1
    fi

    log_success "Found container $CONTAINER_ID"
    echo ""

    # Get Proxmox host
    while [[ -z "$PROXMOX_HOST" ]]; do
        read -p "Enter Proxmox host IP address: " PROXMOX_HOST
        if [[ -z "$PROXMOX_HOST" ]]; then
            log_warning "Proxmox host is required!"
        fi
    done

    # Get username
    read -p "Enter Proxmox username [default: root]: " input
    PROXMOX_USERNAME=${input:-root}

    # Get password
    while [[ -z "$PROXMOX_PASSWORD" ]]; do
        read -s -p "Enter Proxmox password: " PROXMOX_PASSWORD
        echo ""
        if [[ -z "$PROXMOX_PASSWORD" ]]; then
            log_warning "Password is required!"
        fi
    done

    # Get realm
    read -p "Enter Proxmox realm [default: pam]: " input
    PROXMOX_REALM=${input:-pam}

    # Get port
    read -p "Enter Proxmox port [default: 8006]: " input
    PROXMOX_PORT=${input:-8006}

    # SSL verification
    read -p "Enable SSL verification? (y/N): " input
    if [[ "$input" =~ ^[Yy]$ ]]; then
        PROXMOX_SSL_VERIFY="True"
    fi

    echo ""
    log_info "Configuration Summary:"
    echo "  Container ID: $CONTAINER_ID"
    echo "  Proxmox Host: $PROXMOX_HOST"
    echo "  Username: $PROXMOX_USERNAME"
    echo "  Realm: $PROXMOX_REALM"
    echo "  Port: $PROXMOX_PORT"
    echo "  SSL Verify: $PROXMOX_SSL_VERIFY"
    echo ""

    read -p "Apply this configuration? (y/N): " input
    if [[ ! "$input" =~ ^[Yy]$ ]]; then
        log_info "Configuration cancelled."
        exit 0
    fi
}

# Test Proxmox connection
test_connection() {
    log_info "Testing Proxmox connection..."
    
    # Create test script
    cat > /tmp/test_proxmox.py << 'EOF'
#!/usr/bin/env python3
import sys
import json
try:
    from proxmoxer import ProxmoxAPI
    
    config = json.loads(sys.argv[1])
    
    # Test connection
    proxmox = ProxmoxAPI(
        host=config['host'],
        user=f"{config['username']}@{config['realm']}",
        password=config['password'],
        verify_ssl=config['ssl_verify'],
        port=int(config['port'])
    )
    
    # Try to get cluster status
    cluster_status = proxmox.cluster.status.get()
    nodes = [node for node in cluster_status if node['type'] == 'node']
    
    print(f"SUCCESS: Connected to Proxmox cluster with {len(nodes)} nodes")
    for node in nodes:
        print(f"  - {node['name']}: {node['online']}")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
EOF

    # Test connection from container
    config_json=$(cat << EOF
{
    "host": "$PROXMOX_HOST",
    "username": "$PROXMOX_USERNAME", 
    "password": "$PROXMOX_PASSWORD",
    "realm": "$PROXMOX_REALM",
    "port": "$PROXMOX_PORT",
    "ssl_verify": $([ "$PROXMOX_SSL_VERIFY" = "True" ] && echo "true" || echo "false")
}
EOF
)

    if pct exec "$CONTAINER_ID" -- python3 /tmp/test_proxmox.py "$config_json" 2>/dev/null; then
        log_success "✅ Proxmox connection test successful!"
        return 0
    else
        log_error "❌ Proxmox connection test failed!"
        log_warning "Please check your credentials and network connectivity"
        return 1
    fi
}

# Apply configuration
apply_config() {
    log_info "Applying Proxmox configuration to container $CONTAINER_ID..."

    # Create .env configuration
    pct exec "$CONTAINER_ID" -- bash -c "
        cat > /opt/moxnas/.env << 'EOF'
# MoxNAS Configuration
SECRET_KEY=moxnas-secret-key-\$(openssl rand -hex 32)
DEBUG=False
ALLOWED_HOSTS=*

# Storage Configuration
MOXNAS_STORAGE_PATH=/mnt/storage
MOXNAS_CONFIG_PATH=/etc/moxnas
MOXNAS_LOG_PATH=/var/log/moxnas

# Proxmox Integration Settings
PROXMOX_HOST=$PROXMOX_HOST
PROXMOX_PORT=$PROXMOX_PORT
PROXMOX_USERNAME=$PROXMOX_USERNAME
PROXMOX_PASSWORD=$PROXMOX_PASSWORD
PROXMOX_REALM=$PROXMOX_REALM
PROXMOX_SSL_VERIFY=$PROXMOX_SSL_VERIFY

# Network Settings
NETWORK_TIMEOUT=30
NETWORK_RETRIES=3
EOF
    "

    log_success "Configuration file created"

    # Restart MoxNAS service
    log_info "Restarting MoxNAS service..."
    pct exec "$CONTAINER_ID" -- systemctl restart moxnas

    # Wait for service to start
    sleep 5

    # Check service status
    if pct exec "$CONTAINER_ID" -- systemctl is-active moxnas &>/dev/null; then
        log_success "✅ MoxNAS service restarted successfully"
    else
        log_error "❌ MoxNAS service failed to start"
        return 1
    fi

    # Get container IP
    CONTAINER_IP=$(pct exec "$CONTAINER_ID" -- hostname -I | awk '{print $1}')
    
    echo ""
    log_success "🎉 Proxmox integration configured successfully!"
    echo ""
    echo "📊 Access Information:"
    echo "  Web Interface: http://$CONTAINER_IP:8000"
    echo "  Container IP:  $CONTAINER_IP"
    echo "  Container ID:  $CONTAINER_ID"
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Open the web interface"
    echo "  2. Navigate to the 'Proxmox' tab"
    echo "  3. Add your Proxmox nodes"
    echo "  4. Start managing containers!"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--container-id)
            CONTAINER_ID="$2"
            shift 2
            ;;
        -h|--host)
            PROXMOX_HOST="$2"
            shift 2
            ;;
        -u|--username)
            PROXMOX_USERNAME="$2"
            shift 2
            ;;
        -p|--password)
            PROXMOX_PASSWORD="$2"
            shift 2
            ;;
        -r|--realm)
            PROXMOX_REALM="$2"
            shift 2
            ;;
        -P|--port)
            PROXMOX_PORT="$2"
            shift 2
            ;;
        --ssl-verify)
            PROXMOX_SSL_VERIFY="True"
            shift
            ;;
        --interactive)
            INTERACTIVE_MODE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log_info "🚀 MoxNAS Proxmox Integration Setup"
    echo "====================================="
    echo ""

    # Check if we're running on Proxmox host
    if ! command -v pct &>/dev/null; then
        log_error "This script must be run on a Proxmox VE host"
        exit 1
    fi

    # Interactive mode or parameter validation
    if [[ "$INTERACTIVE_MODE" == "true" ]]; then
        interactive_config
    else
        # Validate required parameters
        if [[ -z "$PROXMOX_HOST" ]]; then
            log_error "Proxmox host is required. Use --host or --interactive mode"
            exit 1
        fi
        
        if [[ -z "$PROXMOX_PASSWORD" ]]; then
            log_error "Proxmox password is required. Use --password or --interactive mode"
            exit 1
        fi
    fi

    # Verify container exists
    if ! pct status "$CONTAINER_ID" &>/dev/null; then
        log_error "Container $CONTAINER_ID does not exist!"
        exit 1
    fi

    # Test connection first
    if ! test_connection; then
        log_error "Configuration aborted due to connection failure"
        exit 1
    fi

    # Apply configuration
    if apply_config; then
        log_success "🎉 Configuration completed successfully!"
    else
        log_error "Configuration failed"
        exit 1
    fi
}

# Execute main function
main "$@"
