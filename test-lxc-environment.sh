#!/usr/bin/env bash

# MoxNAS LXC Environment Testing Script
# Validates MoxNAS deployment in LXC container environment

set -euo pipefail

# Colors
YW='\033[33m'
RD='\033[01;31m'
BL='\033[36m'
GN='\033[1;92m'
CL='\033[m'
BOLD='\033[1m'

# Configuration
MOXNAS_DIR="/opt/moxnas"
TEST_LOG="/var/log/moxnas-test.log"

log() {
    echo -e "${BL}[TEST]${CL} $1" | tee -a "$TEST_LOG"
}

success() {
    echo -e "${GN}[PASS]${CL} $1" | tee -a "$TEST_LOG"
}

error() {
    echo -e "${RD}[FAIL]${CL} $1" | tee -a "$TEST_LOG"
}

warn() {
    echo -e "${YW}[WARN]${CL} $1" | tee -a "$TEST_LOG"
}

# Initialize test log
echo "=== MoxNAS LXC Environment Test - $(date) ===" > "$TEST_LOG"

header() {
    echo -e "${BOLD}🧪 MoxNAS LXC Environment Test Suite${CL}"
    echo "========================================"
    echo
}

# Test 1: Container Environment Detection
test_container_environment() {
    log "Testing container environment detection..."
    
    if [[ -f /proc/1/environ ]] && grep -q container /proc/1/environ 2>/dev/null; then
        success "Running inside container environment"
        return 0
    else
        error "Container environment not detected"
        return 1
    fi
}

# Test 2: System Prerequisites
test_system_prerequisites() {
    log "Testing system prerequisites..."
    
    local tests_passed=0
    local total_tests=5
    
    # Check if running as root
    if [[ $EUID -eq 0 ]]; then
        success "Running as root user"
        ((tests_passed++))
    else
        error "Not running as root"
    fi
    
    # Check OS compatibility
    if command -v apt-get >/dev/null 2>&1; then
        success "APT package manager available"
        ((tests_passed++))
    else
        error "APT package manager not found"
    fi
    
    # Check Python availability
    if command -v python3 >/dev/null 2>&1; then
        success "Python 3 available"
        ((tests_passed++))
    else
        error "Python 3 not found"
    fi
    
    # Check network connectivity
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        success "Network connectivity OK"
        ((tests_passed++))
    else
        error "No network connectivity"
    fi
    
    # Check available disk space
    local disk_space=$(df / | tail -1 | awk '{print $4}')
    if [[ $disk_space -gt 5000000 ]]; then  # 5GB in KB
        success "Sufficient disk space available"
        ((tests_passed++))
    else
        error "Insufficient disk space (need at least 5GB)"
    fi
    
    log "System prerequisites: $tests_passed/$total_tests passed"
    return $((total_tests - tests_passed))
}

# Test 3: MoxNAS Application Structure
test_application_structure() {
    log "Testing MoxNAS application structure..."
    
    local tests_passed=0
    local total_tests=8
    
    # Core directories
    local directories=(
        "$MOXNAS_DIR"
        "$MOXNAS_DIR/app"
        "$MOXNAS_DIR/app/static"
        "$MOXNAS_DIR/app/templates"
        "/mnt/storage"
        "/mnt/backups"
    )
    
    for dir in "${directories[@]}"; do
        if [[ -d "$dir" ]]; then
            success "Directory exists: $dir"
            ((tests_passed++))
        else
            error "Directory missing: $dir"
        fi
    done
    
    # Core files
    local files=(
        "$MOXNAS_DIR/wsgi.py"
        "$MOXNAS_DIR/requirements.txt"
    )
    
    for file in "${files[@]}"; do
        if [[ -f "$file" ]]; then
            success "File exists: $file"
            ((tests_passed++))
        else
            error "File missing: $file"
        fi
    done
    
    log "Application structure: $tests_passed/$total_tests passed"
    return $((total_tests - tests_passed))
}

# Test 4: Python Virtual Environment
test_python_environment() {
    log "Testing Python virtual environment..."
    
    local tests_passed=0
    local total_tests=3
    
    # Check virtual environment
    if [[ -d "$MOXNAS_DIR/venv" ]]; then
        success "Virtual environment exists"
        ((tests_passed++))
    else
        error "Virtual environment missing"
    fi
    
    # Check Python executable
    if [[ -f "$MOXNAS_DIR/venv/bin/python" ]]; then
        success "Python executable in venv"
        ((tests_passed++))
    else
        error "Python executable missing from venv"
    fi
    
    # Test package installation
    if [[ -f "$MOXNAS_DIR/venv/bin/pip" ]] && "$MOXNAS_DIR/venv/bin/pip" list | grep -q Flask; then
        success "Flask package installed in venv"
        ((tests_passed++))
    else
        error "Flask package not found in venv"
    fi
    
    log "Python environment: $tests_passed/$total_tests passed"
    return $((total_tests - tests_passed))
}

# Test 5: Database Services
test_database_services() {
    log "Testing database services..."
    
    local tests_passed=0
    local total_tests=4
    
    # PostgreSQL service
    if systemctl is-active postgresql >/dev/null 2>&1; then
        success "PostgreSQL service is running"
        ((tests_passed++))
    else
        error "PostgreSQL service not running"
    fi
    
    # Redis service
    if systemctl is-active redis-server >/dev/null 2>&1; then
        success "Redis service is running"
        ((tests_passed++))
    else
        error "Redis service not running"
    fi
    
    # Database connectivity
    if sudo -u postgres psql -c "SELECT 1" >/dev/null 2>&1; then
        success "PostgreSQL connectivity OK"
        ((tests_passed++))
    else
        error "PostgreSQL connectivity failed"
    fi
    
    # Redis connectivity
    if redis-cli ping >/dev/null 2>&1; then
        success "Redis connectivity OK"
        ((tests_passed++))
    else
        error "Redis connectivity failed"
    fi
    
    log "Database services: $tests_passed/$total_tests passed"
    return $((total_tests - tests_passed))
}

# Test 6: Web Services
test_web_services() {
    log "Testing web services..."
    
    local tests_passed=0
    local total_tests=3
    
    # Nginx service
    if systemctl is-active nginx >/dev/null 2>&1; then
        success "Nginx service is running"
        ((tests_passed++))
    else
        error "Nginx service not running"
    fi
    
    # MoxNAS service
    if systemctl is-active moxnas >/dev/null 2>&1; then
        success "MoxNAS service is running"
        ((tests_passed++))
    else
        error "MoxNAS service not running"
    fi
    
    # Port availability
    if netstat -tlnp | grep -q ':443.*nginx'; then
        success "HTTPS port (443) is listening"
        ((tests_passed++))
    else
        error "HTTPS port (443) not listening"
    fi
    
    log "Web services: $tests_passed/$total_tests passed"
    return $((total_tests - tests_passed))
}

# Test 7: File Sharing Services
test_file_sharing() {
    log "Testing file sharing services..."
    
    local tests_passed=0
    local total_tests=3
    
    # SMB service
    if systemctl is-active smbd >/dev/null 2>&1; then
        success "SMB service is running"
        ((tests_passed++))
    else
        error "SMB service not running"
    fi
    
    # NFS service
    if systemctl is-active nfs-kernel-server >/dev/null 2>&1; then
        success "NFS service is running"
        ((tests_passed++))
    else
        error "NFS service not running"
    fi
    
    # FTP service
    if systemctl is-active vsftpd >/dev/null 2>&1; then
        success "FTP service is running"
        ((tests_passed++))
    else
        error "FTP service not running"
    fi
    
    log "File sharing services: $tests_passed/$total_tests passed"
    return $((total_tests - tests_passed))
}

# Test 8: Web Interface Connectivity
test_web_interface() {
    log "Testing web interface connectivity..."
    
    local tests_passed=0
    local total_tests=3
    
    # HTTP redirect test
    local http_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "000")
    if [[ "$http_response" == "301" ]] || [[ "$http_response" == "302" ]]; then
        success "HTTP redirect working (status: $http_response)"
        ((tests_passed++))
    else
        error "HTTP redirect not working (status: $http_response)"
    fi
    
    # HTTPS response test
    local https_response=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost/ 2>/dev/null || echo "000")
    if [[ "$https_response" == "200" ]] || [[ "$https_response" == "302" ]]; then
        success "HTTPS response OK (status: $https_response)"
        ((tests_passed++))
    else
        error "HTTPS response failed (status: $https_response)"
    fi
    
    # SSL certificate test
    if openssl x509 -in /etc/ssl/certs/moxnas.crt -noout -text >/dev/null 2>&1; then
        success "SSL certificate is valid"
        ((tests_passed++))
    else
        error "SSL certificate is invalid"
    fi
    
    log "Web interface: $tests_passed/$total_tests passed"
    return $((total_tests - tests_passed))
}

# Test 9: Application Health
test_application_health() {
    log "Testing MoxNAS application health..."
    
    local tests_passed=0
    local total_tests=4
    
    # Database schema
    if cd "$MOXNAS_DIR" && sudo -u moxnas bash -c 'source venv/bin/activate && python -c "from app import create_app, db; app = create_app(\"production\"); app.app_context().push(); print(\"Tables:\", len(db.metadata.tables))"' >/dev/null 2>&1; then
        success "Database schema is accessible"
        ((tests_passed++))
    else
        error "Database schema not accessible"
    fi
    
    # Admin user exists
    if cd "$MOXNAS_DIR" && sudo -u moxnas bash -c 'source venv/bin/activate && python -c "from app import create_app, db; from app.models import User; app = create_app(\"production\"); app.app_context().push(); admin = User.query.filter_by(username=\"admin\").first(); print(\"Admin exists:\", admin is not None)"' 2>/dev/null | grep -q "True"; then
        success "Admin user exists in database"
        ((tests_passed++))
    else
        error "Admin user not found in database"
    fi
    
    # Application logs
    if journalctl -u moxnas --no-pager --lines=10 | grep -q -E "(Started|Running|Serving)"; then
        success "Application logs show healthy status"
        ((tests_passed++))
    else
        warn "Application logs don't show clear healthy status"
    fi
    
    # Worker process
    if systemctl is-active moxnas-worker >/dev/null 2>&1; then
        success "Worker process is running"
        ((tests_passed++))
    else
        error "Worker process not running"
    fi
    
    log "Application health: $tests_passed/$total_tests passed"
    return $((total_tests - tests_passed))
}

# Test 10: Network Shares
test_network_shares() {
    log "Testing network shares configuration..."
    
    local tests_passed=0
    local total_tests=3
    
    # SMB shares
    if testparm -s 2>/dev/null | grep -q "moxnas-storage"; then
        success "SMB shares configured"
        ((tests_passed++))
    else
        error "SMB shares not configured"
    fi
    
    # NFS exports
    if exportfs | grep -q "/mnt/storage"; then
        success "NFS exports configured"
        ((tests_passed++))
    else
        error "NFS exports not configured"
    fi
    
    # Test files exist
    if [[ -f "/mnt/storage/README.txt" ]]; then
        success "Test files exist in storage"
        ((tests_passed++))
    else
        error "Test files missing from storage"
    fi
    
    log "Network shares: $tests_passed/$total_tests passed"
    return $((total_tests - tests_passed))
}

# Generate test report
generate_report() {
    local total_failures=$1
    local container_ip=$(hostname -I | awk '{print $1}')
    
    echo | tee -a "$TEST_LOG"
    echo "===============================================" | tee -a "$TEST_LOG"
    echo "           MoxNAS LXC Test Report" | tee -a "$TEST_LOG"
    echo "===============================================" | tee -a "$TEST_LOG"
    echo "Test Date: $(date)" | tee -a "$TEST_LOG"
    echo "Container IP: $container_ip" | tee -a "$TEST_LOG"
    echo "Total Test Failures: $total_failures" | tee -a "$TEST_LOG"
    echo | tee -a "$TEST_LOG"
    
    if [[ $total_failures -eq 0 ]]; then
        echo -e "${GN}🎉 ALL TESTS PASSED!${CL}" | tee -a "$TEST_LOG"
        echo "MoxNAS is ready for production use." | tee -a "$TEST_LOG"
        echo | tee -a "$TEST_LOG"
        echo "Access Information:" | tee -a "$TEST_LOG"
        echo "  Web Interface: https://$container_ip" | tee -a "$TEST_LOG"
        echo "  Username: admin" | tee -a "$TEST_LOG"
        echo "  Password: moxnas1234" | tee -a "$TEST_LOG"
        echo | tee -a "$TEST_LOG"
        echo "Network Shares:" | tee -a "$TEST_LOG"
        echo "  SMB: //$container_ip/moxnas-storage" | tee -a "$TEST_LOG"
        echo "  NFS: $container_ip:/mnt/storage" | tee -a "$TEST_LOG"
    elif [[ $total_failures -le 5 ]]; then
        echo -e "${YW}⚠️  TESTS PASSED WITH MINOR ISSUES${CL}" | tee -a "$TEST_LOG"
        echo "MoxNAS is mostly functional but may need attention." | tee -a "$TEST_LOG"
    else
        echo -e "${RD}❌ MULTIPLE TEST FAILURES${CL}" | tee -a "$TEST_LOG"
        echo "MoxNAS deployment has significant issues." | tee -a "$TEST_LOG"
    fi
    
    echo | tee -a "$TEST_LOG"
    echo "Full test log saved to: $TEST_LOG" | tee -a "$TEST_LOG"
}

# Main test execution
main() {
    header
    
    local total_failures=0
    
    # Run all tests
    test_container_environment || ((total_failures++))
    echo
    
    test_system_prerequisites
    total_failures=$((total_failures + $?))
    echo
    
    test_application_structure  
    total_failures=$((total_failures + $?))
    echo
    
    test_python_environment
    total_failures=$((total_failures + $?))
    echo
    
    test_database_services
    total_failures=$((total_failures + $?))
    echo
    
    test_web_services
    total_failures=$((total_failures + $?))
    echo
    
    test_file_sharing
    total_failures=$((total_failures + $?))
    echo
    
    test_web_interface
    total_failures=$((total_failures + $?))
    echo
    
    test_application_health
    total_failures=$((total_failures + $?))
    echo
    
    test_network_shares
    total_failures=$((total_failures + $?))
    echo
    
    # Generate report
    generate_report $total_failures
    
    return $total_failures
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "MoxNAS LXC Environment Test Script"
        echo
        echo "Usage: $0 [OPTIONS]"
        echo
        echo "This script validates MoxNAS deployment in LXC container."
        echo "It checks all critical components and services."
        echo
        echo "Options:"
        echo "  --help    Show this help message"
        echo
        echo "The script tests:"
        echo "  - Container environment"
        echo "  - System prerequisites"
        echo "  - Application structure"
        echo "  - Python virtual environment"
        echo "  - Database services"
        echo "  - Web services"
        echo "  - File sharing"
        echo "  - Network connectivity" 
        echo "  - Application health"
        echo
        exit 0
        ;;
    *)
        main "$@"
        exit $?
        ;;
esac
