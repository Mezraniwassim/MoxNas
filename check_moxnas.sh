#!/bin/bash
#
# Simple MoxNAS Container Check
#

echo "🔍 MoxNAS Container Check"
echo "========================"

# List all containers first
echo "📦 All containers:"
pct list 2>/dev/null

echo ""
echo "🔍 Looking for MoxNAS containers..."
pct list 2>/dev/null | grep -i moxnas

echo ""
echo "📝 Please identify the correct MoxNAS container ID from above"
echo "Then run these commands manually:"
echo ""
echo "# Check specific container (replace XXX with container ID):"
echo "pct status XXX"
echo "pct start XXX"
echo "pct exec XXX -- hostname -I"
echo "pct exec XXX -- systemctl status smbd"
echo ""
echo "# Access web interface:"
echo "# http://<container_ip>:8080"
echo "# Login: admin / moxnas123"