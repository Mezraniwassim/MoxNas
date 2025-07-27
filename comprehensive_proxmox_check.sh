#!/bin/bash

# Comprehensive Proxmox Host Check Script
# Target: 172.16.135.128:8006
# User: user
# Password: wc305ekb

PROXMOX_HOST="172.16.135.128"
PROXMOX_PORT="8006"
PROXMOX_USER="user"
PROXMOX_PASS="wc305ekb"
SSH_USER="root"  # Default SSH user for Proxmox
LOG_FILE="/tmp/proxmox_check_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "$1" | tee -a "$LOG_FILE"
}

print_header() {
    log "${BLUE}================================${NC}"
    log "${BLUE}$1${NC}"
    log "${BLUE}================================${NC}"
}

print_success() {
    log "${GREEN}✓ $1${NC}"
}

print_error() {
    log "${RED}✗ $1${NC}"
}

print_warning() {
    log "${YELLOW}⚠ $1${NC}"
}

print_info() {
    log "${BLUE}ℹ $1${NC}"
}

# Check if required tools are installed
check_prerequisites() {
    print_header "CHECKING PREREQUISITES"
    
    local missing_tools=()
    
    for tool in curl ssh sshpass nc jq; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        else
            print_success "$tool is installed"
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_info "Install missing tools with: sudo apt-get install ${missing_tools[*]}"
        return 1
    fi
    
    print_success "All prerequisites met"
    return 0
}

# Test basic network connectivity
test_network_connectivity() {
    print_header "TESTING NETWORK CONNECTIVITY"
    
    # Ping test
    if ping -c 3 "$PROXMOX_HOST" &> /dev/null; then
        print_success "Ping to $PROXMOX_HOST successful"
    else
        print_error "Ping to $PROXMOX_HOST failed"
        return 1
    fi
    
    # Port connectivity tests
    local ports=(22 8006)
    for port in "${ports[@]}"; do
        if nc -z -w5 "$PROXMOX_HOST" "$port" 2>/dev/null; then
            print_success "Port $port is open on $PROXMOX_HOST"
        else
            print_error "Port $port is closed or filtered on $PROXMOX_HOST"
        fi
    done
    
    return 0
}

# Test SSH connectivity
test_ssh_connectivity() {
    print_header "TESTING SSH CONNECTIVITY"
    
    # Test SSH with root user (default for Proxmox)
    if sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$SSH_USER@$PROXMOX_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
        print_success "SSH connection to $SSH_USER@$PROXMOX_HOST successful"
        
        # Get basic system info via SSH
        print_info "Getting system information via SSH:"
        sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" "
            echo 'Hostname: \$(hostname)'
            echo 'Uptime: \$(uptime)'
            echo 'Proxmox Version: \$(pveversion)'
            echo 'CPU Info: \$(grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs)'
            echo 'Memory: \$(free -h | grep Mem | awk '{print \$2\" total, \"\$3\" used, \"\$7\" available\"}')'
            echo 'Disk Usage: \$(df -h / | tail -1 | awk '{print \$3\" used of \"\$2\" (\"\$5\" full)\"}')'
        " 2>/dev/null | while read line; do
            print_info "$line"
        done
        
        return 0
    else
        print_error "SSH connection failed. Trying with user '$PROXMOX_USER'..."
        
        # Try with the API user
        if sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$PROXMOX_USER@$PROXMOX_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
            print_success "SSH connection to $PROXMOX_USER@$PROXMOX_HOST successful"
            return 0
        else
            print_error "SSH connection failed with both root and $PROXMOX_USER"
            return 1
        fi
    fi
}

# Test Proxmox API connectivity
test_api_connectivity() {
    print_header "TESTING PROXMOX API CONNECTIVITY"
    
    # Test HTTPS connectivity
    if curl -k -s --connect-timeout 10 "https://$PROXMOX_HOST:$PROXMOX_PORT/api2/json/version" &> /dev/null; then
        print_success "HTTPS connection to Proxmox API successful"
    else
        print_error "HTTPS connection to Proxmox API failed"
        return 1
    fi
    
    # Get authentication ticket
    print_info "Attempting to authenticate with Proxmox API..."
    
    local auth_response
    auth_response=$(curl -k -s -d "username=$PROXMOX_USER" -d "password=$PROXMOX_PASS" \
        "https://$PROXMOX_HOST:$PROXMOX_PORT/api2/json/access/ticket" 2>/dev/null)
    
    if echo "$auth_response" | jq -e '.data.ticket' &> /dev/null; then
        print_success "Proxmox API authentication successful"
        
        # Extract ticket and CSRF token
        local ticket
        local csrf_token
        ticket=$(echo "$auth_response" | jq -r '.data.ticket')
        csrf_token=$(echo "$auth_response" | jq -r '.data.CSRFPreventionToken')
        
        # Test API calls with authentication
        test_authenticated_api_calls "$ticket" "$csrf_token"
        
        return 0
    else
        print_error "Proxmox API authentication failed"
        print_info "Response: $auth_response"
        return 1
    fi
}

# Test authenticated API calls
test_authenticated_api_calls() {
    local ticket="$1"
    local csrf_token="$2"
    
    print_header "TESTING AUTHENTICATED API CALLS"
    
    local cookie="PVEAuthCookie=$ticket"
    local csrf_header="CSRFPreventionToken: $csrf_token"
    
    # Test various API endpoints
    local endpoints=(
        "/api2/json/version"
        "/api2/json/cluster/status"
        "/api2/json/nodes"
        "/api2/json/storage"
        "/api2/json/pools"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local response
        response=$(curl -k -s -b "$cookie" -H "$csrf_header" \
            "https://$PROXMOX_HOST:$PROXMOX_PORT$endpoint" 2>/dev/null)
        
        if echo "$response" | jq -e '.data' &> /dev/null; then
            print_success "API call to $endpoint successful"
            
            # Display relevant information based on endpoint
            case "$endpoint" in
                "/api2/json/version")
                    local version
                    version=$(echo "$response" | jq -r '.data.version // "Unknown"')
                    print_info "Proxmox Version: $version"
                    ;;
                "/api2/json/nodes")
                    print_info "Available nodes:"
                    echo "$response" | jq -r '.data[] | "  - \(.node) (Status: \(.status), Type: \(.type))"' 2>/dev/null | while read line; do
                        print_info "$line"
                    done
                    ;;
                "/api2/json/storage")
                    print_info "Storage pools:"
                    echo "$response" | jq -r '.data[] | "  - \(.storage) (Type: \(.type), Content: \(.content))"' 2>/dev/null | while read line; do
                        print_info "$line"
                    done
                    ;;
            esac
        else
            print_error "API call to $endpoint failed"
            print_info "Response: $response"
        fi
    done
}

# Check Proxmox services via SSH
check_proxmox_services() {
    print_header "CHECKING PROXMOX SERVICES"
    
    if ! sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" "command -v systemctl" &> /dev/null; then
        print_warning "Cannot check services - SSH connection or systemctl not available"
        return 1
    fi
    
    local services=(
        "pve-cluster"
        "pvedaemon"
        "pveproxy"
        "pvestatd"
        "pve-firewall"
        "corosync"
        "qemu-server"
        "lxc"
    )
    
    for service in "${services[@]}"; do
        local status
        status=$(sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" \
            "systemctl is-active $service 2>/dev/null || echo 'inactive'")
        
        if [ "$status" = "active" ]; then
            print_success "$service is running"
        else
            print_error "$service is not running (status: $status)"
        fi
    done
}

# Check storage configuration
check_storage_configuration() {
    print_header "CHECKING STORAGE CONFIGURATION"
    
    if ! sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" "command -v pvesm" &> /dev/null; then
        print_warning "Cannot check storage - SSH connection or pvesm not available"
        return 1
    fi
    
    print_info "Storage status:"
    sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" \
        "pvesm status 2>/dev/null" | while read line; do
        print_info "$line"
    done
    
    print_info "Disk usage:"
    sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" \
        "df -h 2>/dev/null" | while read line; do
        print_info "$line"
    done
}

# Check network configuration
check_network_configuration() {
    print_header "CHECKING NETWORK CONFIGURATION"
    
    if ! sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" "command -v ip" &> /dev/null; then
        print_warning "Cannot check network - SSH connection or ip command not available"
        return 1
    fi
    
    print_info "Network interfaces:"
    sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" \
        "ip addr show 2>/dev/null" | grep -E "^[0-9]+:|inet " | while read line; do
        print_info "$line"
    done
    
    print_info "Network bridges:"
    sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" \
        "brctl show 2>/dev/null" | while read line; do
        print_info "$line"
    done
}

# Check VMs and containers
check_vms_containers() {
    print_header "CHECKING VMs AND CONTAINERS"
    
    if ! sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" "command -v qm" &> /dev/null; then
        print_warning "Cannot check VMs/containers - SSH connection not available"
        return 1
    fi
    
    print_info "Virtual Machines:"
    sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" \
        "qm list 2>/dev/null" | while read line; do
        print_info "$line"
    done
    
    print_info "Containers:"
    sshpass -p "$PROXMOX_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$PROXMOX_HOST" \
        "pct list 2>/dev/null" | while read line; do
        print_info "$line"
    done
}

# Main execution
main() {
    print_header "COMPREHENSIVE PROXMOX HOST CHECK"
    print_info "Target: $PROXMOX_HOST:$PROXMOX_PORT"
    print_info "User: $PROXMOX_USER"
    print_info "Log file: $LOG_FILE"
    print_info "Started: $(date)"
    echo
    
    local overall_status=0
    
    # Run all checks
    check_prerequisites || overall_status=1
    echo
    
    test_network_connectivity || overall_status=1
    echo
    
    test_ssh_connectivity || overall_status=1
    echo
    
    test_api_connectivity || overall_status=1
    echo
    
    check_proxmox_services || overall_status=1
    echo
    
    check_storage_configuration || overall_status=1
    echo
    
    check_network_configuration || overall_status=1
    echo
    
    check_vms_containers || overall_status=1
    echo
    
    # Final summary
    print_header "FINAL SUMMARY"
    if [ $overall_status -eq 0 ]; then
        print_success "All checks completed successfully!"
    else
        print_warning "Some checks failed or had warnings. Check the log for details."
    fi
    
    print_info "Full log saved to: $LOG_FILE"
    print_info "Completed: $(date)"
    
    return $overall_status
}

# Run the main function
main "$@"