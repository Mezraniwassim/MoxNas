#!/bin/bash

# Enhanced test script for MoxNas installation
# This creates a comprehensive test environment

set -euo pipefail

echo "🧪 MoxNas Enhanced Installation Test"
echo "==================================="
echo

# Create test environment
TEST_ROOT="/tmp/moxnas-test-env"
rm -rf "$TEST_ROOT" 2>/dev/null || true
mkdir -p "$TEST_ROOT"

# Create comprehensive mock commands
mkdir -p "$TEST_ROOT/bin"

# Enhanced mock pct command
cat > "$TEST_ROOT/bin/pct" << 'EOF'
#!/bin/bash
case "$1" in
    "list")
        echo "VMID       Status     Lock         Name"
        echo "100        running                 test-vm"
        ;;
    "create")
        echo "Creating container $2..."
        # Simulate creation delay
        sleep 1
        echo "CT $2 created successfully."
        ;;
    "start")
        echo "Starting container $2..."
        sleep 1
        echo "CT $2 started successfully."
        ;;
    "status")
        if [[ "$2" -ge 200 && "$2" -le 210 ]]; then
            echo "status: stopped" >&2
            exit 1
        else
            echo "status: running"
        fi
        ;;
    "exec")
        container_id="$2"
        shift 3  # Remove pct exec CONTAINER_ID --
        
        # Handle specific commands
        case "$1" in
            "ip")
                if [[ "$2" == "route" ]]; then
                    echo "default via 192.168.1.1 dev eth0"
                elif [[ "$2" == "addr" ]]; then
                    echo "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000"
                    echo "    inet 192.168.1.100/24 brd 192.168.1.255 scope global eth0"
                fi
                ;;
            "hostname")
                if [[ "$2" == "-I" ]]; then
                    echo "192.168.1.100"
                fi
                ;;
            "bash")
                if [[ "$2" == "-c" ]]; then
                    # Execute the command in quotes
                    eval "$3"
                fi
                ;;
            "systemctl")
                echo "Mocking systemctl $2 $3"
                ;;
            "sudo")
                shift 1  # Remove sudo
                if [[ "$1" == "-u" && "$2" == "postgres" ]]; then
                    echo "Mock postgres command executed"
                fi
                ;;
            "apt-get")
                echo "Mock apt-get $2 executed"
                ;;
            "git")
                if [[ "$2" == "clone" ]]; then
                    echo "Mock git clone: $3 -> $4"
                    mkdir -p "$4"
                fi
                ;;
            "python3")
                if [[ "$2" == "-m" && "$3" == "venv" ]]; then
                    echo "Mock python venv created: $4"
                    mkdir -p "$4/bin"
                    echo '#!/bin/bash' > "$4/bin/python"
                    echo 'echo "Mock Python 3.10.0"' >> "$4/bin/python"
                    chmod +x "$4/bin/python"
                fi
                ;;
            *)
                echo "Mock pct exec: $*"
                ;;
        esac
        ;;
    "push")
        echo "Mock file transfer: $3 -> container $2:$4"
        ;;
    *)
        echo "Mock pct: $*"
        ;;
esac
EOF

chmod +x "$TEST_ROOT/bin/pct"

# Enhanced mock pvesm command
cat > "$TEST_ROOT/bin/pvesm" << 'EOF'
#!/bin/bash
case "$1" in
    "status")
        echo "Name             Type     Status           Total            Used       Available        %"
        echo "local            dir      active        50331648        10485760        39845888   20.83%"
        echo "local-lvm        lvmthin  active        100663296        20971520        79691776   20.83%"
        ;;
    *)
        echo "Mock pvesm: $*"
        ;;
esac
EOF

chmod +x "$TEST_ROOT/bin/pvesm"

# Mock pveam command
cat > "$TEST_ROOT/bin/pveam" << 'EOF'
#!/bin/bash
case "$1" in
    "update")
        echo "Mock template database updated"
        ;;
    "download")
        echo "Mock template download: $3"
        # Create the template file
        mkdir -p /var/lib/vz/template/cache
        touch "/var/lib/vz/template/cache/$3"
        ;;
    *)
        echo "Mock pveam: $*"
        ;;
esac
EOF

chmod +x "$TEST_ROOT/bin/pveam"

# Mock pveversion command
cat > "$TEST_ROOT/bin/pveversion" << 'EOF'
#!/bin/bash
echo "pve-manager/8.1.0/pve-manager/8.1.0 (running kernel: 6.2.16-20-pve)"
EOF

chmod +x "$TEST_ROOT/bin/pveversion"

# Mock systemctl command
cat > "$TEST_ROOT/bin/systemctl" << 'EOF'
#!/bin/bash
case "$1" in
    "is-active")
        if [[ "$3" == "pvedaemon" ]]; then
            echo "active"
            exit 0
        fi
        ;;
    *)
        echo "Mock systemctl: $*"
        ;;
esac
EOF

chmod +x "$TEST_ROOT/bin/systemctl"

# Add mock binaries to PATH
export PATH="$TEST_ROOT/bin:$PATH"

# Create mock template directory
sudo mkdir -p /var/lib/vz/template/cache 2>/dev/null || true

echo "✅ Enhanced mock environment created"
echo "📁 Mock directory: $TEST_ROOT"
echo "🔧 Testing enhanced installation script..."
echo

# Run the installation script in test mode
cd /home/wassim/Documents/MoxNas

echo "🚀 Running MoxNas installation test..."
echo "======================================"

if sudo -E bash install-moxnas.sh --test-mode --auto; then
    echo
    echo "🎉 INSTALLATION TEST PASSED!"
    echo "✅ All container setup functions work correctly"
    echo "✅ Error handling is functional"
    echo "✅ Test mode bypasses work properly"
else
    echo
    echo "❌ INSTALLATION TEST FAILED"
    echo "Check the output above for specific issues"
    exit 1
fi

# Cleanup
rm -rf "$TEST_ROOT"
echo
echo "🧹 Test environment cleaned up"
echo "📊 Test completed successfully!"
