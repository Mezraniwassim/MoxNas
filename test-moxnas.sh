#!/bin/bash
# MoxNAS Testing and Validation Script
# Copyright (c) 2024 MoxNAS Contributors
# License: MIT

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test configuration
API_URL="http://127.0.0.1:8001/api"
WEB_URL="http://127.0.0.1:8000"
TEST_TIMEOUT=10
PASSED_TESTS=0
FAILED_TESTS=0
TOTAL_TESTS=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_TESTS++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_TESTS++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

run_test() {
    local test_name="$1"
    ((TOTAL_TESTS++))
    echo -e "\n${BLUE}Testing:${NC} $test_name"
}

# Test API endpoint
test_api_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local test_name="$3"
    
    run_test "$test_name"
    
    local response
    local status_code
    
    if response=$(curl -s -w "HTTPSTATUS:%{http_code}" --max-time $TEST_TIMEOUT "$API_URL$endpoint" 2>/dev/null); then
        status_code=$(echo "$response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
        
        if [[ "$status_code" -eq "$expected_status" ]]; then
            log_success "API endpoint $endpoint returned status $status_code"
            return 0
        else
            log_fail "API endpoint $endpoint returned status $status_code, expected $expected_status"
            return 1
        fi
    else
        log_fail "API endpoint $endpoint is unreachable"
        return 1
    fi
}

# Test web endpoint
test_web_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local test_name="$3"
    
    run_test "$test_name"
    
    local status_code
    
    if status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TEST_TIMEOUT "$WEB_URL$endpoint" 2>/dev/null); then
        if [[ "$status_code" -eq "$expected_status" ]]; then
            log_success "Web endpoint $endpoint returned status $status_code"
            return 0
        else
            log_fail "Web endpoint $endpoint returned status $status_code, expected $expected_status"
            return 1
        fi
    else
        log_fail "Web endpoint $endpoint is unreachable"
        return 1
    fi
}

# Test service status
test_service_status() {
    local service="$1"
    local test_name="Test $service service"
    
    run_test "$test_name"
    
    if systemctl is-active --quiet "$service"; then
        log_success "Service $service is running"
        return 0
    else
        log_fail "Service $service is not running"
        return 1
    fi
}

# Test port availability
test_port() {
    local port="$1"
    local test_name="Test port $port availability"
    
    run_test "$test_name"
    
    if netstat -ln 2>/dev/null | grep -q ":$port "; then
        log_success "Port $port is listening"
        return 0
    elif ss -ln 2>/dev/null | grep -q ":$port "; then
        log_success "Port $port is listening"
        return 0
    else
        log_fail "Port $port is not listening"
        return 1
    fi
}

# Test file system permissions
test_permissions() {
    local path="$1"
    local expected_owner="$2"
    local expected_permissions="$3"
    local test_name="Test $path permissions"
    
    run_test "$test_name"
    
    if [[ ! -e "$path" ]]; then
        log_fail "Path $path does not exist"
        return 1
    fi
    
    local actual_owner actual_permissions
    actual_owner=$(stat -c '%U:%G' "$path" 2>/dev/null || echo "unknown")
    actual_permissions=$(stat -c '%a' "$path" 2>/dev/null || echo "000")
    
    local success=true
    
    if [[ "$actual_owner" != "$expected_owner" ]]; then
        log_fail "Path $path owner is $actual_owner, expected $expected_owner"
        success=false
    fi
    
    if [[ "$actual_permissions" != "$expected_permissions" ]]; then
        log_fail "Path $path permissions are $actual_permissions, expected $expected_permissions"
        success=false
    fi
    
    if $success; then
        log_success "Path $path has correct permissions ($expected_permissions) and owner ($expected_owner)"
        return 0
    else
        return 1
    fi
}

# Test configuration files
test_config_file() {
    local config_file="$1"
    local test_name="Test $config_file configuration"
    
    run_test "$test_name"
    
    if [[ ! -f "$config_file" ]]; then
        log_fail "Configuration file $config_file does not exist"
        return 1
    fi
    
    if [[ ! -r "$config_file" ]]; then
        log_fail "Configuration file $config_file is not readable"
        return 1
    fi
    
    # Basic validation based on file type
    case "$config_file" in
        *.json)
            if python3 -m json.tool "$config_file" >/dev/null 2>&1; then
                log_success "JSON configuration $config_file is valid"
                return 0
            else
                log_fail "JSON configuration $config_file is invalid"
                return 1
            fi
            ;;
        */smb.conf)
            if testparm -s "$config_file" >/dev/null 2>&1; then
                log_success "Samba configuration $config_file is valid"
                return 0
            else
                log_fail "Samba configuration $config_file is invalid"
                return 1
            fi
            ;;
        */nginx.conf|*/sites-available/*)
            if nginx -t -c /etc/nginx/nginx.conf >/dev/null 2>&1; then
                log_success "Nginx configuration is valid"
                return 0
            else
                log_fail "Nginx configuration is invalid"
                return 1
            fi
            ;;
        *)
            log_success "Configuration file $config_file exists and is readable"
            return 0
            ;;
    esac
}

# Test share functionality
test_share_creation() {
    local test_name="Test share creation via API"
    
    run_test "$test_name"
    
    local share_data='{"name": "test-share", "type": "smb", "path": "/mnt/shares/test-share", "guest": true}'
    local response
    
    if response=$(curl -s -X POST -H "Content-Type: application/json" -d "$share_data" --max-time $TEST_TIMEOUT "$API_URL/shares" 2>/dev/null); then
        if echo "$response" | grep -q '"success":true'; then
            log_success "Share creation API works"
            
            # Cleanup test share
            curl -s -X DELETE --max-time $TEST_TIMEOUT "$API_URL/shares/test-share" >/dev/null 2>&1 || true
            rm -rf /mnt/shares/test-share 2>/dev/null || true
            
            return 0
        else
            log_fail "Share creation API failed: $response"
            return 1
        fi
    else
        log_fail "Share creation API is unreachable"
        return 1
    fi
}

# Test system resources
test_system_resources() {
    local test_name="Test system resources"
    
    run_test "$test_name"
    
    # Check available memory (should have at least 100MB free)
    local available_memory
    available_memory=$(free -m | awk 'NR==2{print $7}' 2>/dev/null || echo "0")
    
    if [[ "$available_memory" -ge 100 ]]; then
        log_success "System has adequate memory (${available_memory}MB available)"
    else
        log_warning "System has low memory (${available_memory}MB available)"
    fi
    
    # Check disk space (should have at least 1GB free)
    local available_disk
    available_disk=$(df / | awk 'NR==2 {print int($4/1024)}' 2>/dev/null || echo "0")
    
    if [[ "$available_disk" -ge 1024 ]]; then
        log_success "System has adequate disk space (${available_disk}MB available)"
    else
        log_warning "System has low disk space (${available_disk}MB available)"
    fi
    
    # Check CPU load
    local load_average
    load_average=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',' 2>/dev/null || echo "0.00")
    
    log_success "System load average: $load_average"
    
    return 0
}

# Main test functions
test_basic_functionality() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                          Basic Functionality Tests                   ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    
    # Test services
    test_service_status "moxnas-api"
    test_service_status "nginx"
    test_service_status "smbd"
    test_service_status "nfs-kernel-server"
    test_service_status "vsftpd"
    
    # Test ports
    test_port "8000"  # Web interface
    test_port "8001"  # API server
    test_port "445"   # SMB
    test_port "2049"  # NFS
    test_port "21"    # FTP
}

test_web_interface() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                          Web Interface Tests                        ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    
    # Test web endpoints
    test_web_endpoint "/" 200 "Main dashboard page"
    test_web_endpoint "/health" 200 "Health check endpoint"
    test_web_endpoint "/css/style.css" 200 "CSS assets"
    test_web_endpoint "/js/app.js" 200 "JavaScript assets"
    test_web_endpoint "/nonexistent" 404 "404 error handling"
}

test_api_endpoints() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                             API Tests                               ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    
    # Test API endpoints
    test_api_endpoint "/system-stats" 200 "System statistics API"
    test_api_endpoint "/services" 200 "Services status API"
    test_api_endpoint "/shares" 200 "Shares list API"
    test_api_endpoint "/storage" 200 "Storage information API"
    test_api_endpoint "/network" 200 "Network information API"
    test_api_endpoint "/users" 200 "Users list API"
    
    # Test share creation
    test_share_creation
}

test_file_system() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                         File System Tests                          ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    
    # Test directory structure and permissions
    test_permissions "/opt/moxnas" "root:root" "755"
    test_permissions "/var/www/moxnas" "www-data:www-data" "755"
    test_permissions "/etc/moxnas" "root:root" "755"
    test_permissions "/var/log/moxnas" "root:root" "755"
    test_permissions "/mnt/shares" "root:root" "755"
    test_permissions "/mnt/shares/public" "nobody:nogroup" "777"
}

test_configurations() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                       Configuration Tests                          ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    
    # Test configuration files
    test_config_file "/etc/samba/smb.conf"
    test_config_file "/etc/exports"
    test_config_file "/etc/vsftpd.conf"
    test_config_file "/etc/nginx/sites-available/moxnas.conf"
    test_config_file "/etc/moxnas/users.json"
    
    # Test if configuration files exist
    [[ -f "/etc/systemd/system/moxnas-api.service" ]] && log_success "Systemd service file exists" || log_fail "Systemd service file missing"
}

test_system_health() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                         System Health Tests                        ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    
    test_system_resources
}

show_test_results() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                            Test Results                            ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    
    echo -e "\nTotal Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"
    
    local success_rate=0
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    fi
    
    echo -e "Success Rate: ${success_rate}%"
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 All tests passed! MoxNAS is working correctly.${NC}"
        return 0
    else
        echo -e "\n${RED}⚠️  Some tests failed. Please check the issues above.${NC}"
        
        if [[ $success_rate -ge 80 ]]; then
            echo -e "${YELLOW}MoxNAS should still be functional, but some features may not work properly.${NC}"
        else
            echo -e "${RED}MoxNAS may not be working correctly. Please review the installation.${NC}"
        fi
        
        return 1
    fi
}

show_help() {
    cat << EOF
MoxNAS Testing and Validation Script

Usage: $0 [OPTIONS]

Options:
    --basic         Run only basic functionality tests
    --web           Run only web interface tests  
    --api           Run only API tests
    --filesystem    Run only file system tests
    --config        Run only configuration tests
    --health        Run only system health tests
    --help          Show this help message

Examples:
    $0                  # Run all tests
    $0 --basic          # Run only basic tests
    $0 --api --web      # Run API and web tests

EOF
}

main() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                     MoxNAS Test Suite                            ║"
    echo "║              Comprehensive System Validation                     ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    local run_basic=false
    local run_web=false
    local run_api=false
    local run_filesystem=false
    local run_config=false
    local run_health=false
    local run_all=true
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --basic)
                run_basic=true
                run_all=false
                shift
                ;;
            --web)
                run_web=true
                run_all=false
                shift
                ;;
            --api)
                run_api=true
                run_all=false
                shift
                ;;
            --filesystem)
                run_filesystem=true
                run_all=false
                shift
                ;;
            --config)
                run_config=true
                run_all=false
                shift
                ;;
            --health)
                run_health=true
                run_all=false
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_warning "Unknown option: $1"
                shift
                ;;
        esac
    done
    
    # Run selected tests
    if $run_all || $run_basic; then
        test_basic_functionality
    fi
    
    if $run_all || $run_web; then
        test_web_interface
    fi
    
    if $run_all || $run_api; then
        test_api_endpoints
    fi
    
    if $run_all || $run_filesystem; then
        test_file_system
    fi
    
    if $run_all || $run_config; then
        test_configurations
    fi
    
    if $run_all || $run_health; then
        test_system_health
    fi
    
    show_test_results
}

# Run main function
main "$@"