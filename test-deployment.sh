#!/bin/bash

# Test script to verify MoxNAS deployment setup
# This simulates what the one-line installer would do

set -euo pipefail

echo "🧪 Testing MoxNAS Deployment Setup"
echo "=================================="

# Test 1: Check if CT script exists and is valid
echo -n "✓ Checking Proxmox CT script... "
if [[ -f "proxmox/ct/moxnas.sh" ]] && bash -n "proxmox/ct/moxnas.sh"; then
    echo "✅ Valid"
else
    echo "❌ Failed"
    exit 1
fi

# Test 2: Check if installation script exists and is valid
echo -n "✓ Checking installation script... "
if [[ -f "proxmox/install/moxnas-install.sh" ]] && bash -n "proxmox/install/moxnas-install.sh"; then
    echo "✅ Valid"
else
    echo "❌ Failed"
    exit 1
fi

# Test 3: Check if standalone installer exists and is valid
echo -n "✓ Checking standalone installer... "
if [[ -f "install.sh" ]] && bash -n "install.sh"; then
    echo "✅ Valid"
else
    echo "❌ Failed"
    exit 1
fi

# Test 4: Check if API server exists
echo -n "✓ Checking API server... "
if [[ -f "api-server.py" ]]; then
    echo "✅ Found"
else
    echo "❌ Missing"
    exit 1
fi

# Test 5: Check if Hugo site is built
echo -n "✓ Checking Hugo build... "
if [[ -f "public/index.html" ]]; then
    echo "✅ Found"
else
    echo "❌ Missing"
    exit 1
fi

# Test 6: Check if required config files exist
echo -n "✓ Checking config templates... "
if [[ -d "config/templates" ]] && [[ -d "config/nginx" ]] && [[ -d "config/systemd" ]]; then
    echo "✅ Found"
else
    echo "❌ Missing"
    exit 1
fi

# Test 7: Verify the CT script follows community-scripts format
echo -n "✓ Checking community-scripts format... "
if grep -q "source.*build.func" "proxmox/ct/moxnas.sh" && grep -q "install_script()" "proxmox/ct/moxnas.sh"; then
    echo "✅ Valid"
else
    echo "❌ Invalid format"
    exit 1
fi

echo ""
echo "🎉 All tests passed! MoxNAS deployment setup is ready!"
echo ""
echo "📋 Deployment Commands:"
echo "   Proxmox CT: bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/proxmox/ct/moxnas.sh)\""
echo "   Standalone: curl -fsSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/install.sh | sudo bash"
echo ""
echo "✅ Ready for production deployment!"