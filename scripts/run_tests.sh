#!/bin/bash

# Comprehensive test runner for MoxNAS
# Runs integration tests, validates deployment, and checks system health

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Check if we're in the right directory
check_environment() {
    if [[ ! -d "$BACKEND_DIR" ]]; then
        error "Backend directory not found. Are you running this from the project root?"
    fi
    
    if [[ ! -f "$BACKEND_DIR/manage.py" ]]; then
        error "Django manage.py not found in backend directory"
    fi
}

# Set up test environment
setup_test_environment() {
    log "Setting up test environment..."
    
    cd "$BACKEND_DIR"
    
    # Check if virtual environment exists
    if [[ ! -d "venv" ]]; then
        log "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install/upgrade test dependencies
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Install additional test packages
    pip install pytest pytest-django pytest-cov coverage factory-boy
    
    log "✓ Test environment ready"
}

# Run Django unit tests
run_django_tests() {
    log "Running Django unit tests..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Set test environment
    export DJANGO_SETTINGS_MODULE=moxnas.settings
    export DEBUG=True
    
    # Run Django tests
    python manage.py test --verbosity=2 --keepdb
    
    log "✓ Django unit tests completed"
}

# Run integration tests
run_integration_tests() {
    log "Running integration tests..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Set test environment
    export DJANGO_SETTINGS_MODULE=moxnas.settings
    export DEBUG=True
    
    # Run pytest for integration tests
    pytest tests/integration/ -v --tb=short
    
    log "✓ Integration tests completed"
}

# Test service management
test_service_management() {
    log "Testing service management system..."
    
    cd "$PROJECT_ROOT"
    
    # Run service configuration tests
    if [[ -f "test_service_configuration.py" ]]; then
        python test_service_configuration.py
    else
        warn "Service configuration test script not found"
    fi
    
    # Run demo script
    if [[ -f "demo_service_management.py" ]]; then
        python demo_service_management.py
    else
        warn "Service management demo script not found"
    fi
    
    log "✓ Service management tests completed"
}

# Validate database
validate_database() {
    log "Validating database..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Run database validation
    python manage.py validate_database --create-superuser --migrate
    
    log "✓ Database validation completed"
}

# Test API endpoints
test_api_endpoints() {
    log "Testing API endpoints..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Start Django server in background
    python manage.py runserver 127.0.0.1:8001 &
    SERVER_PID=$!
    
    # Wait for server to start
    sleep 5
    
    # Test health endpoints
    info "Testing health check endpoints..."
    
    # Test basic health check
    if curl -f -s http://127.0.0.1:8001/api/system/health/ > /dev/null; then
        log "✓ Health check endpoint working"
    else
        warn "Health check endpoint not responding"
    fi
    
    # Test readiness check
    if curl -f -s http://127.0.0.1:8001/api/system/health/ready/ > /dev/null; then
        log "✓ Readiness check endpoint working"
    else
        warn "Readiness check endpoint not responding"
    fi
    
    # Test liveness check
    if curl -f -s http://127.0.0.1:8001/api/system/health/live/ > /dev/null; then
        log "✓ Liveness check endpoint working"
    else
        warn "Liveness check endpoint not responding"
    fi
    
    # Test version endpoint
    if curl -f -s http://127.0.0.1:8001/api/system/version/ > /dev/null; then
        log "✓ Version endpoint working"
    else
        warn "Version endpoint not responding"
    fi
    
    # Test metrics endpoint
    if curl -f -s http://127.0.0.1:8001/api/system/metrics/prometheus/ > /dev/null; then
        log "✓ Metrics endpoint working"
    else
        warn "Metrics endpoint not responding"
    fi
    
    # Stop Django server
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    
    log "✓ API endpoint tests completed"
}

# Test configuration generation
test_configuration_generation() {
    log "Testing configuration generation..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Test service configuration
    python manage.py configure_services --test-only
    
    log "✓ Configuration generation tests completed"
}

# Generate test coverage report
generate_coverage_report() {
    log "Generating test coverage report..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Run tests with coverage
    coverage run --source='.' manage.py test
    coverage run --append -m pytest tests/integration/
    
    # Generate coverage report
    coverage report --show-missing
    coverage html --directory=htmlcov
    
    log "✓ Coverage report generated in htmlcov/"
}

# Performance tests
run_performance_tests() {
    log "Running performance tests..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Start Django server
    python manage.py runserver 127.0.0.1:8001 &
    SERVER_PID=$!
    sleep 5
    
    # Simple load test using curl
    info "Running basic load test..."
    for i in {1..10}; do
        if ! curl -f -s http://127.0.0.1:8001/api/system/health/ > /dev/null; then
            warn "Request $i failed"
        fi
    done
    
    # Stop server
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    
    log "✓ Performance tests completed"
}

# Security tests
run_security_tests() {
    log "Running security tests..."
    
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    # Check for security issues
    python manage.py check --deploy
    
    # Test for common security headers
    python manage.py runserver 127.0.0.1:8001 &
    SERVER_PID=$!
    sleep 5
    
    # Check security headers
    info "Checking security headers..."
    headers=$(curl -I -s http://127.0.0.1:8001/api/system/health/ || echo "")
    
    if echo "$headers" | grep -q "X-Content-Type-Options"; then
        log "✓ X-Content-Type-Options header present"
    else
        warn "X-Content-Type-Options header missing"
    fi
    
    if echo "$headers" | grep -q "X-Frame-Options"; then
        log "✓ X-Frame-Options header present"
    else
        warn "X-Frame-Options header missing"
    fi
    
    # Stop server
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
    
    log "✓ Security tests completed"
}

# Main test runner
main() {
    log "Starting MoxNAS comprehensive test suite..."
    
    local test_type="${1:-all}"
    local exit_code=0
    
    case "$test_type" in
        "unit")
            check_environment
            setup_test_environment
            run_django_tests
            ;;
        "integration")
            check_environment
            setup_test_environment
            run_integration_tests
            ;;
        "services")
            check_environment
            setup_test_environment
            test_service_management
            ;;
        "api")
            check_environment
            setup_test_environment
            test_api_endpoints
            ;;
        "config")
            check_environment
            setup_test_environment
            test_configuration_generation
            ;;
        "performance")
            check_environment
            setup_test_environment
            run_performance_tests
            ;;
        "security")
            check_environment
            setup_test_environment
            run_security_tests
            ;;
        "coverage")
            check_environment
            setup_test_environment
            generate_coverage_report
            ;;
        "all"|"")
            check_environment
            setup_test_environment
            run_django_tests || exit_code=1
            run_integration_tests || exit_code=1
            test_service_management || exit_code=1
            validate_database || exit_code=1
            test_api_endpoints || exit_code=1
            test_configuration_generation || exit_code=1
            run_performance_tests || exit_code=1
            run_security_tests || exit_code=1
            generate_coverage_report || exit_code=1
            ;;
        *)
            echo "Usage: $0 [unit|integration|services|api|config|performance|security|coverage|all]"
            exit 1
            ;;
    esac
    
    if [[ $exit_code -eq 0 ]]; then
        log "🎉 All tests completed successfully!"
    else
        error "❌ Some tests failed. Check the output above for details."
    fi
    
    exit $exit_code
}

# Run main function with all arguments
main "$@"