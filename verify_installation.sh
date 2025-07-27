#!/bin/bash
#
# MoxNAS Installation Verification Script
# Run this on your Proxmox host to check the MoxNAS container status
#

echo "🔍 MoxNAS Installation Verification"
echo "=================================="

# Check if container exists and is running
echo "📦 Checking container status..."
if pct list 2>/dev/null | grep -q "moxnas"; then
    CONTAINER_ID=$(pct list 2>/dev/null | grep "moxnas" | head -1 | awk '{print $1}')
    echo "✅ Container found: ID $CONTAINER_ID"
    
    # Check container status
    STATUS=$(pct status $CONTAINER_ID | awk '{print $2}')
    echo "📊 Container status: $STATUS"
    
    if [ "$STATUS" = "running" ]; then
        echo "✅ Container is running"
        
        # Get container IP
        CONTAINER_IP=$(pct exec $CONTAINER_ID -- hostname -I | awk '{print $1}')
        echo "🌐 Container IP: $CONTAINER_IP"
        
        # Check if MoxNAS web interface is accessible
        echo "🔗 Checking web interface..."
        if pct exec $CONTAINER_ID -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ | grep -q "200\|302"; then
            echo "✅ Web interface is responding"
            echo "📍 Access URL: http://$CONTAINER_IP:8080"
            echo "👤 Default login: admin / moxnas123"
        else
            echo "❌ Web interface not responding"
            echo "🔧 Trying to start MoxNAS..."
            pct exec $CONTAINER_ID -- /opt/moxnas/start_container.sh
        fi
        
        # Check services status
        echo ""
        echo "🔧 Checking NAS services..."
        services=("ssh" "smbd" "nmbd" "nfs-kernel-server" "vsftpd")
        for service in "${services[@]}"; do
            if pct exec $CONTAINER_ID -- systemctl is-active --quiet "$service"; then
                echo "✅ $service: running"
            else
                echo "❌ $service: not running"
            fi
        done
        
        # Check storage directory
        echo ""
        echo "📁 Checking storage setup..."
        if pct exec $CONTAINER_ID -- ls -la /mnt/storage > /dev/null 2>&1; then
            echo "✅ Storage directory exists"
            pct exec $CONTAINER_ID -- df -h /mnt/storage
        else
            echo "❌ Storage directory not found"
        fi
        
    else
        echo "❌ Container is not running"
        echo "🚀 Starting container..."
        pct start $CONTAINER_ID
        sleep 10
        echo "🔄 Re-checking status..."
        pct status $CONTAINER_ID
    fi
else
    echo "❌ MoxNAS container not found"
    echo "💡 Available containers:"
    pct list
fi

echo ""
echo "📋 Verification Summary:"
echo "- Container ID: ${CONTAINER_ID:-'Not found'}"
echo "- Container Status: ${STATUS:-'Unknown'}"
echo "- Web Interface: http://${CONTAINER_IP:-'Unknown'}:8080"
echo "- Default Credentials: admin / moxnas123"
echo ""
echo "🔧 If there are issues, you can:"
echo "1. Access container console: pct enter $CONTAINER_ID"
echo "2. Check logs: pct exec $CONTAINER_ID -- journalctl -f"
echo "3. Restart MoxNAS: pct exec $CONTAINER_ID -- /opt/moxnas/start_container.sh"