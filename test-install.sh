#!/bin/bash

# Test installation script by mocking Proxmox commands
# This creates a simulated environment to test the installation logic

set -euo pipefail

# Create mock directory structure
MOCK_ROOT="/tmp/moxnas-test"
rm -rf "$MOCK_ROOT" 2>/dev/null || true
mkdir -p "$MOCK_ROOT"
mkdir -p /var/lib/vz/template/cache

# Create mock executables
mkdir -p "$MOCK_ROOT/bin"

# Mock pct command
cat > "$MOCK_ROOT/bin/pct" << 'EOF'
#!/bin/bash
case "$1" in
    "list")
        echo "VMID       Status     Lock         Name"
        echo "100        running                 test-vm"
        ;;
    "create")
        echo "Creating container..."
        ;;
    "start")
        echo "Starting container..."
        ;;
    "exec")
        # Skip the container ID argument
        shift
        # Skip the "--" separator
        shift
        # Execute the command in our mock environment
        if [[ "$1" == "bash" && "$2" == "-c" ]]; then
            # Handle complex commands
            eval "$3"
        else
            # Handle simple commands
            "$@"
        fi
        ;;
    *)
        echo "Mock pct: $*"
        ;;
esac
EOF

chmod +x "$MOCK_ROOT/bin/pct"

# Mock pvesm command
cat > "$MOCK_ROOT/bin/pvesm" << 'EOF'
#!/bin/bash
case "$1" in
    "status")
        echo "Name                Type     Status           Total            Used       Available        %"
        echo "local               dir      active      946927616       158089472       740498432   16.69%"
        echo "local-lvm           lvmthin  active       20971520               0        20971520    0.00%"
        ;;
    *)
        echo "Mock pvesm: $*"
        ;;
esac
EOF

chmod +x "$MOCK_ROOT/bin/pvesm"

# Mock pveam command
cat > "$MOCK_ROOT/bin/pveam" << 'EOF'
#!/bin/bash
case "$1" in
    "update")
        echo "Mock: Template database updated"
        ;;
    "download")
        echo "Mock: Downloading template $3"
        mkdir -p /var/lib/vz/template/cache
        touch "/var/lib/vz/template/cache/$3"
        ;;
    *)
        echo "Mock pveam: $*"
        ;;
esac
EOF

chmod +x "$MOCK_ROOT/bin/pveam"

# Mock pveversion command
cat > "$MOCK_ROOT/bin/pveversion" << 'EOF'
#!/bin/bash
echo "pve-manager/8.1.0/8d7c4b68b2a8e86c (running kernel: 6.5.11-8-pve)"
EOF

chmod +x "$MOCK_ROOT/bin/pveversion"

# Add mock binaries to PATH
export PATH="$MOCK_ROOT/bin:$PATH"

# Create mock Proxmox environment
mkdir -p "$MOCK_ROOT/etc/pve"
echo "8.1.0" > "$MOCK_ROOT/etc/pve/.version"

echo "🧪 Mock environment created at: $MOCK_ROOT"
echo "🔧 Testing installation script..."
echo

# Set up environment variables for the test
export TEST_MODE="true"

# Run the installation script
cd /home/wassim/Documents/MoxNas
sudo -E bash install-moxnas.sh --test-mode --auto

echo
echo "🎉 Test completed!"
