#!/bin/bash
#
# MoxNAS Complete Installation Test Script
# This script verifies that MoxNAS is working correctly after installation
#

set -e

# Configuration
CONTAINER_ID=${1:-200}
TIMEOUT=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✅ PASS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠ WARN]${NC} $1"; }
log_error() { echo -e "${RED}[❌ FAIL]${NC} $1"; }

# Test result tracking
test_pass() {
    log_success "$1"
    ((TESTS_PASSED++))
}

test_fail() {
    log_error "$1"
    FAILED_TESTS+=("$1")
    ((TESTS_FAILED++))
}

echo "🧪 MoxNAS Complete Installation Test"
echo "Testing Container ID: $CONTAINER_ID"
echo "=================================================="
echo ""

# Test 1: Container exists and is running
test_container_status() {
    log_info "Testing container status..."
    
    if ! pct status "$CONTAINER_ID" >/dev/null 2>&1; then
        test_fail "Container $CONTAINER_ID does not exist"
        return 1
    fi
    
    local status=$(pct status "$CONTAINER_ID")
    if [[ "$status" == "status: running" ]]; then
        test_pass "Container $CONTAINER_ID is running"
    else
        test_fail "Container $CONTAINER_ID is not running (status: $status)"
        return 1
    fi
}

# Test 2: Check directory structure
test_directory_structure() {
    log_info "Testing directory structure..."
    
    local directories=(
        "/opt/moxnas"
        "/opt/moxnas/venv"
        "/opt/moxnas/backend"
        "/mnt/storage"
        "/var/log/moxnas"
    )
    
    for dir in "${directories[@]}"; do
        if pct exec "$CONTAINER_ID" -- test -d "$dir"; then
            test_pass "Directory exists: $dir"
        else
            test_fail "Directory missing: $dir"
        fi
    done
}

# Test 3: Check virtual environment
test_virtual_environment() {
    log_info "Testing Python virtual environment..."
    
    if pct exec "$CONTAINER_ID" -- test -f "/opt/moxnas/venv/bin/activate"; then
        test_pass "Virtual environment exists"
    else
        test_fail "Virtual environment missing"
        return 1
    fi
    
    # Test Python and pip in venv
    if pct exec "$CONTAINER_ID" -- bash -c "cd /opt/moxnas && source venv/bin/activate && python --version" >/dev/null 2>&1; then
        test_pass "Python accessible in virtual environment"
    else
        test_fail "Python not accessible in virtual environment"
    fi
    
    # Test Django
    if pct exec "$CONTAINER_ID" -- bash -c "cd /opt/moxnas && source venv/bin/activate && python -c 'import django; print(django.VERSION)'" >/dev/null 2>&1; then
        test_pass "Django installed in virtual environment"
    else
        test_fail "Django not installed in virtual environment"
    fi
}

# Continue with additional tests...
echo "Additional comprehensive tests would continue here..."
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
CONTAINER_ID=${1:-200}
TEST_RESULTS=()

# Add test result
add_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    TEST_RESULTS+=("$test_name|$status|$message")
    
    if [ "$status" = "PASS" ]; then
        log_success "✅ $test_name: $message"
    elif [ "$status" = "FAIL" ]; then
        log_error "❌ $test_name: $message"
    else
        log_warning "⚠️ $test_name: $message"
    fi
}

# Test container existence and status
test_container_status() {
    log_info "Testing container status..."
    
    if pct status "$CONTAINER_ID" &>/dev/null; then
        local status=$(pct status "$CONTAINER_ID")
        if [[ "$status" == *"running"* ]]; then
            add_result "Container Status" "PASS" "Container $CONTAINER_ID is running"
            return 0
        else
            add_result "Container Status" "FAIL" "Container $CONTAINER_ID is not running: $status"
            return 1
        fi
    else
        add_result "Container Status" "FAIL" "Container $CONTAINER_ID does not exist"
        return 1
    fi
}

# Test network connectivity
test_network() {
    log_info "Testing network connectivity..."
    
    # Get container IP
    local container_ip
    container_ip=$(pct exec "$CONTAINER_ID" -- hostname -I | awk '{print $1}' 2>/dev/null)
    
    if [ -n "$container_ip" ]; then
        add_result "Network IP" "PASS" "Container IP: $container_ip"
        
        # Test ping to container
        if ping -c 1 "$container_ip" &>/dev/null; then
            add_result "Network Ping" "PASS" "Container is reachable"
        else
            add_result "Network Ping" "WARN" "Container not pingable (may be firewall)"
        fi
        
        export CONTAINER_IP="$container_ip"
        return 0
    else
        add_result "Network IP" "FAIL" "Could not get container IP"
        return 1
    fi
}

# Test MoxNAS web interface
test_web_interface() {
    log_info "Testing MoxNAS web interface..."
    
    if [ -z "$CONTAINER_IP" ]; then
        add_result "Web Interface" "FAIL" "No container IP available"
        return 1
    fi
    
    # Test if gunicorn is running
    if pct exec "$CONTAINER_ID" -- ps aux | grep -q "gunicorn.*8000"; then
        add_result "Gunicorn Process" "PASS" "Gunicorn is running on port 8000"
    else
        add_result "Gunicorn Process" "FAIL" "Gunicorn not running"
        return 1
    fi
    
    # Test HTTP response
    if curl -s -I "http://$CONTAINER_IP:8000" | grep -q "HTTP.*200\|HTTP.*301\|HTTP.*302"; then
        add_result "Web Interface" "PASS" "Web interface is accessible"
    else
        add_result "Web Interface" "FAIL" "Web interface not accessible"
        return 1
    fi
    
    # Test API endpoints
    if curl -s "http://$CONTAINER_IP:8000/api/system/status/" | grep -q "hostname\|cpu_usage"; then
        add_result "API Endpoints" "PASS" "API is responding"
    else
        add_result "API Endpoints" "WARN" "API may not be working properly"
    fi
}

# Test NAS services
test_nas_services() {
    log_info "Testing NAS services..."
    
    # Test Samba/SMB
    if pct exec "$CONTAINER_ID" -- systemctl is-active smbd &>/dev/null; then
        add_result "SMB Service" "PASS" "Samba is running"
        
        # Test SMB share
        if pct exec "$CONTAINER_ID" -- smbclient -L localhost -N 2>/dev/null | grep -q "moxnas-share"; then
            add_result "SMB Share" "PASS" "SMB shares are configured"
        else
            add_result "SMB Share" "WARN" "SMB shares may not be properly configured"
        fi
    else
        add_result "SMB Service" "FAIL" "Samba is not running"
    fi
    
    # Test NFS
    if pct exec "$CONTAINER_ID" -- systemctl is-active nfs-kernel-server &>/dev/null; then
        add_result "NFS Service" "PASS" "NFS server is running"
        
        # Test NFS exports
        if pct exec "$CONTAINER_ID" -- exportfs -v | grep -q "/mnt/storage"; then
            add_result "NFS Export" "PASS" "NFS exports are configured"
        else
            add_result "NFS Export" "WARN" "NFS exports may not be properly configured"
        fi
    else
        add_result "NFS Service" "FAIL" "NFS server is not running"
    fi
    
    # Test FTP
    if pct exec "$CONTAINER_ID" -- systemctl is-active vsftpd &>/dev/null; then
        add_result "FTP Service" "PASS" "FTP server is running"
        
        # Test FTP connection
        if echo "quit" | pct exec "$CONTAINER_ID" -- timeout 5 ftp localhost 2>/dev/null | grep -q "220"; then
            add_result "FTP Connection" "PASS" "FTP server accepts connections"
        else
            add_result "FTP Connection" "WARN" "FTP connection test failed"
        fi
    else
        add_result "FTP Service" "FAIL" "FTP server is not running"
    fi
    
    # Test SSH
    if pct exec "$CONTAINER_ID" -- systemctl is-active ssh &>/dev/null; then
        add_result "SSH Service" "PASS" "SSH server is running"
    else
        add_result "SSH Service" "FAIL" "SSH server is not running"
    fi
}

# Test storage configuration
test_storage() {
    log_info "Testing storage configuration..."
    
    # Test storage directories
    if pct exec "$CONTAINER_ID" -- [ -d "/mnt/storage" ]; then
        add_result "Storage Directory" "PASS" "/mnt/storage exists"
        
        # Test permissions
        local perms
        perms=$(pct exec "$CONTAINER_ID" -- stat -c "%a" "/mnt/storage")
        if [ "$perms" = "755" ]; then
            add_result "Storage Permissions" "PASS" "Storage has correct permissions (755)"
        else
            add_result "Storage Permissions" "WARN" "Storage permissions: $perms (expected 755)"
        fi
    else
        add_result "Storage Directory" "FAIL" "/mnt/storage does not exist"
    fi
    
    # Test write access
    if pct exec "$CONTAINER_ID" -- touch "/mnt/storage/test_write" 2>/dev/null; then
        add_result "Storage Write" "PASS" "Storage is writable"
        pct exec "$CONTAINER_ID" -- rm "/mnt/storage/test_write" 2>/dev/null || true
    else
        add_result "Storage Write" "FAIL" "Storage is not writable"
    fi
}

# Test Django application
test_django_app() {
    log_info "Testing Django application..."
    
    # Test Django admin
    if pct exec "$CONTAINER_ID" -- bash -c "cd /opt/moxnas && source venv/bin/activate && cd backend && python manage.py check" &>/dev/null; then
        add_result "Django Check" "PASS" "Django application is healthy"
    else
        add_result "Django Check" "FAIL" "Django application has issues"
    fi
    
    # Test database
    if pct exec "$CONTAINER_ID" -- [ -f "/opt/moxnas/backend/db.sqlite3" ]; then
        add_result "Database File" "PASS" "SQLite database exists"
    else
        add_result "Database File" "FAIL" "SQLite database missing"
    fi
    
    # Test migrations
    if pct exec "$CONTAINER_ID" -- bash -c "cd /opt/moxnas && source venv/bin/activate && cd backend && python manage.py showmigrations --plan" | grep -q "\[X\]"; then
        add_result "Database Migrations" "PASS" "Database migrations applied"
    else
        add_result "Database Migrations" "WARN" "Database migrations may not be applied"
    fi
}

# Test system resources
test_system_resources() {
    log_info "Testing system resources..."
    
    # Test memory usage
    local mem_usage
    mem_usage=$(pct exec "$CONTAINER_ID" -- free | awk '/^Mem:/ {printf "%.1f", $3/$2 * 100}')
    if (( $(echo "$mem_usage < 80" | bc -l) )); then
        add_result "Memory Usage" "PASS" "Memory usage: ${mem_usage}%"
    else
        add_result "Memory Usage" "WARN" "High memory usage: ${mem_usage}%"
    fi
    
    # Test disk usage
    local disk_usage
    disk_usage=$(pct exec "$CONTAINER_ID" -- df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -lt 80 ]; then
        add_result "Disk Usage" "PASS" "Disk usage: ${disk_usage}%"
    else
        add_result "Disk Usage" "WARN" "High disk usage: ${disk_usage}%"
    fi
}

# Generate test report
generate_report() {
    log_info "Generating test report..."
    
    local pass_count=0
    local fail_count=0
    local warn_count=0
    
    echo ""
    echo "=========================================="
    echo "       MoxNAS Installation Test Report    "
    echo "=========================================="
    echo ""
    
    for result in "${TEST_RESULTS[@]}"; do
        IFS='|' read -r test_name status message <<< "$result"
        case "$status" in
            "PASS") ((pass_count++)) ;;
            "FAIL") ((fail_count++)) ;;
            "WARN") ((warn_count++)) ;;
        esac
        printf "%-25s %-6s %s\n" "$test_name" "$status" "$message"
    done
    
    echo ""
    echo "Summary:"
    echo "  ✅ Passed: $pass_count"
    echo "  ❌ Failed: $fail_count"
    echo "  ⚠️  Warnings: $warn_count"
    echo ""
    
    if [ "$fail_count" -eq 0 ]; then
        if [ "$warn_count" -eq 0 ]; then
            log_success "🎉 All tests passed! MoxNAS is ready for delivery."
        else
            log_warning "⚠️ All tests passed with $warn_count warnings. MoxNAS is functional but may need attention."
        fi
        
        echo ""
        echo "🌐 Access MoxNAS: http://$CONTAINER_IP:8000"
        echo "📂 SMB Share: //$CONTAINER_IP/moxnas-share"
        echo "📁 NFS Export: $CONTAINER_IP:/mnt/storage"
        echo "🔗 FTP: ftp://$CONTAINER_IP"
        echo ""
        return 0
    else
        log_error "❌ $fail_count tests failed. MoxNAS needs fixes before delivery."
        echo ""
        echo "🔧 Run fix script: ./fix_moxnas_startup.sh $CONTAINER_ID"
        echo ""
        return 1
    fi
}

# Main test execution
main() {
    echo "=========================================="
    echo "       MoxNAS Installation Test Suite     "
    echo "=========================================="
    echo ""
    echo "Testing container ID: $CONTAINER_ID"
    echo ""
    
    # Run all tests
    test_container_status || exit 1
    test_network
    test_web_interface
    test_nas_services
    test_storage
    test_django_app
    test_system_resources
    
    # Generate report
    generate_report
}

# Check for help
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [container_id]"
    echo "Test complete MoxNAS installation in LXC container"
    echo "Default container ID: 200"
    exit 0
fi

# Check if bc is available for calculations
if ! command -v bc &> /dev/null; then
    apt-get update && apt-get install -y bc 2>/dev/null || {
        log_warning "bc calculator not available, some tests may be limited"
    }
fi

# Run main function
main "$@"