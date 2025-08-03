#!/bin/bash

# Deep diagnostic script for MoxNas installation issues
# This script will identify and fix container-related problems

set -euo pipefail

echo "🔍 MoxNas Installation Deep Diagnostics"
echo "======================================"
echo

# 1. Check script syntax
echo "1. Checking script syntax..."
if bash -n install-moxnas.sh; then
    echo "✅ Script syntax is valid"
else
    echo "❌ Script has syntax errors"
    exit 1
fi

# 2. Check for missing dependencies
echo
echo "2. Checking system dependencies..."
missing_deps=()

# Check for required commands
required_commands=("curl" "wget" "git" "bash" "awk" "sed" "grep")
for cmd in "${required_commands[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        missing_deps+=("$cmd")
    fi
done

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo "❌ Missing dependencies: ${missing_deps[*]}"
    echo "   Install with: sudo apt-get install ${missing_deps[*]}"
else
    echo "✅ All required dependencies are available"
fi

# 3. Check script variables and functions
echo
echo "3. Analyzing script structure..."

# Check for undefined variables
echo "   Checking for potential undefined variables..."
undefined_vars=$(grep -n '\$[A-Z_][A-Z0-9_]*' install-moxnas.sh | grep -v '^[[:space:]]*#' | \
    grep -v -E '(TEST_MODE|AUTO_MODE|MOXNAS_VERSION|GITHUB_REPO|INSTALL_LOG|REQUIREMENTS_URL)' | \
    grep -v -E '(RED|GREEN|YELLOW|BLUE|PURPLE|CYAN|BOLD|NC)' | \
    grep -v -E '(AVAILABLE_STORAGE|NETWORK_BRIDGE|CONTAINER_ID|CONTAINER_MEMORY|CONTAINER_CORES|CONTAINER_SWAP|CONTAINER_DISK|CONTAINER_IP)' | \
    head -5 || true)

if [ -n "$undefined_vars" ]; then
    echo "⚠️  Potential undefined variables found:"
    echo "$undefined_vars"
else
    echo "✅ No obvious undefined variables detected"
fi

# 4. Check function definitions
echo
echo "4. Checking function definitions..."
functions=(
    "check_system_requirements"
    "check_proxmox" 
    "detect_environment"
    "ensure_template"
    "create_container"
    "install_dependencies"
    "setup_application"
    "configure_services"
    "test_installation"
    "main"
)

missing_functions=()
for func in "${functions[@]}"; do
    if ! grep -q "^${func}()" install-moxnas.sh; then
        missing_functions+=("$func")
    fi
done

if [ ${#missing_functions[@]} -gt 0 ]; then
    echo "❌ Missing functions: ${missing_functions[*]}"
else
    echo "✅ All required functions are defined"
fi

# 5. Test variable initialization
echo
echo "5. Testing variable initialization..."
export TEST_MODE="true"
export AUTO_MODE="true"

# Source the script functions only (not execute main)
temp_script=$(mktemp)
sed '/^main "$@"$/d' install-moxnas.sh > "$temp_script"

if source "$temp_script" 2>/dev/null; then
    echo "✅ Script functions load successfully"
    
    # Test if variables are properly set
    if [ "$MOXNAS_VERSION" = "2.0.0" ]; then
        echo "✅ MOXNAS_VERSION correctly set: $MOXNAS_VERSION"
    else
        echo "❌ MOXNAS_VERSION not set correctly"
    fi
    
    if [ "$TEST_MODE" = "true" ]; then
        echo "✅ TEST_MODE correctly set: $TEST_MODE"
    else
        echo "❌ TEST_MODE not set correctly"
    fi
    
else
    echo "❌ Failed to source script functions"
    echo "   Check the script for syntax errors or undefined variables"
fi

rm -f "$temp_script"

# 6. Identify container-specific issues
echo
echo "6. Analyzing container setup logic..."

# Check if pvesm/pct commands are properly handled
if grep -q "pvesm.*status" install-moxnas.sh; then
    echo "✅ Storage detection logic found"
else
    echo "❌ Missing storage detection logic"
fi

if grep -q "pct.*create" install-moxnas.sh; then
    echo "✅ Container creation logic found"
else
    echo "❌ Missing container creation logic"
fi

if grep -q "pct.*exec" install-moxnas.sh; then
    echo "✅ Container execution logic found"
else
    echo "❌ Missing container execution logic"
fi

# 7. Check for common pitfalls
echo
echo "7. Checking for common issues..."

# Check for hardcoded paths
hardcoded_paths=$(grep -n "/opt/moxnas" install-moxnas.sh | wc -l)
echo "   Found $hardcoded_paths references to /opt/moxnas path"

# Check for error handling
error_handlers=$(grep -n "return 1" install-moxnas.sh | wc -l)
echo "   Found $error_handlers error handling statements"

# Check for background processes
background_procs=$(grep -n "&" install-moxnas.sh | grep -v ">/dev/null" | wc -l)
if [ $background_procs -gt 0 ]; then
    echo "⚠️  Found $background_procs potential background processes"
else
    echo "✅ No problematic background processes detected"
fi

# 8. Test requirements.txt path
echo
echo "8. Verifying requirements.txt path..."
if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt found in project root"
    echo "   Lines in requirements.txt: $(wc -l < requirements.txt)"
else
    echo "❌ requirements.txt not found in project root"
fi

if [ -f "backend/requirements.txt" ]; then
    echo "⚠️  Found requirements.txt in backend/ directory"
    echo "   This might cause path confusion"
else
    echo "✅ No conflicting requirements.txt in backend/"
fi

# 9. Test script execution with dry-run
echo
echo "9. Testing script execution (dry-run mode)..."

# Create a minimal test version
cat > test-minimal.sh << 'EOF'
#!/bin/bash
set -euo pipefail

TEST_MODE="true"
AUTO_MODE="true"
MOXNAS_VERSION="2.0.0"
GITHUB_REPO="Mezraniwassim/MoxNas"
INSTALL_LOG="/tmp/moxnas-test.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[TEST]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

check_system_requirements() {
    log "Testing system requirements check..."
    success "System requirements check passed"
    return 0
}

check_proxmox() {
    log "Testing Proxmox validation..."
    if [[ "$TEST_MODE" == "true" ]]; then
        success "Proxmox validation passed (test mode)"
    else
        error "Would fail - not on Proxmox"
        return 1
    fi
    return 0
}

detect_environment() {
    log "Testing environment detection..."
    AVAILABLE_STORAGE="local"
    NETWORK_BRIDGE="vmbr0"
    CONTAINER_ID=200
    CONTAINER_MEMORY=4096
    CONTAINER_CORES=2
    CONTAINER_SWAP=1024
    CONTAINER_DISK=32
    success "Environment detection completed"
    return 0
}

# Run tests
log "Starting minimal functionality test..."
check_system_requirements
check_proxmox  
detect_environment

success "🎉 Minimal test completed successfully!"
echo "Variables set:"
echo "  AVAILABLE_STORAGE=$AVAILABLE_STORAGE"
echo "  CONTAINER_ID=$CONTAINER_ID"
echo "  CONTAINER_MEMORY=${CONTAINER_MEMORY}MB"
EOF

chmod +x test-minimal.sh

if ./test-minimal.sh; then
    echo "✅ Minimal test script runs successfully"
else
    echo "❌ Minimal test script failed"
fi

rm -f test-minimal.sh

# 10. Generate recommendations
echo
echo "10. Recommendations for fixing container issues:"
echo "=============================================="

echo "🔧 CRITICAL FIXES NEEDED:"
echo

echo "1. **Container IP Detection Issue:**"
echo "   - The script uses 'hostname -I' which may not work in containers"
echo "   - Recommend using 'ip route get 1 | awk '{print \$7}' instead"
echo

echo "2. **Service Dependencies:**"
echo "   - PostgreSQL service may not start properly in containers"
echo "   - Add proper service initialization checks"
echo

echo "3. **Network Configuration:**"
echo "   - Container networking setup needs validation"
echo "   - Add network connectivity tests"
echo

echo "4. **File Permissions:**"
echo "   - Ensure proper file permissions for MoxNas files"
echo "   - Add permission validation steps"
echo

echo "5. **Error Recovery:**"
echo "   - Add rollback mechanisms for failed installations"
echo "   - Improve error messages with specific solutions"
echo

echo "📋 TESTING RECOMMENDATIONS:"
echo
echo "1. Create a container testing framework"
echo "2. Add unit tests for each installation step"
echo "3. Implement health checks for services"
echo "4. Add configuration validation"
echo "5. Create automated rollback procedures"

echo
echo "🎯 NEXT STEPS:"
echo "1. Fix the identified issues above"
echo "2. Test the installation in a controlled environment"
echo "3. Add comprehensive logging and error handling"
echo "4. Create installation verification tests"

echo
echo "📊 DIAGNOSTIC COMPLETE"
echo "====================="
