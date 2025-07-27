#!/bin/bash
#
# Fix MoxNAS Container - Run on Proxmox host
#

CONTAINER_ID=200

echo "🔧 Fixing MoxNAS Container $CONTAINER_ID"
echo "========================================"

# Check if container is running
if ! pct status $CONTAINER_ID | grep -q "running"; then
    echo "🚀 Starting container..."
    pct start $CONTAINER_ID
    sleep 5
fi

echo "📁 Checking MoxNAS directory..."
if pct exec $CONTAINER_ID -- test -d /opt/moxnas; then
    echo "✅ MoxNAS directory exists"
else
    echo "❌ MoxNAS directory not found - reinstallation needed"
    exit 1
fi

echo "🔧 Setting up environment..."
pct exec $CONTAINER_ID -- bash -c "
    cd /opt/moxnas || exit 1
    
    # Create necessary directories
    mkdir -p /mnt/storage /var/log/moxnas /etc/moxnas
    chmod 755 /mnt/storage /var/log/moxnas /etc/moxnas
    
    # Create .env file if missing
    if [ ! -f .env ]; then
        echo 'Creating .env file...'
        cat > .env << 'EOF'
DEBUG=False
SECRET_KEY=moxnas-production-key-change-me-in-production
MOXNAS_STORAGE_PATH=/mnt/storage
MOXNAS_CONFIG_PATH=/etc/moxnas
MOXNAS_LOG_PATH=/var/log/moxnas
EOF
    fi
    
    # Fix virtual environment if needed
    if [ ! -f venv/bin/activate ]; then
        echo 'Creating virtual environment...'
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    fi
    
    # Run database migrations
    source venv/bin/activate
    python manage.py makemigrations --noinput
    python manage.py migrate --noinput
    
    # Create superuser if doesn't exist
    python manage.py shell << 'PYEOF'
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@moxnas.local', 'moxnas123')
    print('Superuser created: admin/moxnas123')
else:
    print('Superuser already exists')
PYEOF
"

echo "🚀 Starting NAS services..."
services=("ssh" "smbd" "nmbd" "nfs-kernel-server" "vsftpd" "snmpd")
for service in "${services[@]}"; do
    echo "Starting $service..."
    pct exec $CONTAINER_ID -- systemctl enable $service 2>/dev/null || true
    pct exec $CONTAINER_ID -- systemctl start $service 2>/dev/null || true
done

echo "🌐 Starting MoxNAS web interface..."
pct exec $CONTAINER_ID -- bash -c "
    cd /opt/moxnas
    source venv/bin/activate
    
    # Kill any existing gunicorn processes
    pkill -f 'gunicorn.*moxnas' || true
    sleep 2
    
    # Start MoxNAS in background
    nohup python3 start_moxnas.py production > /var/log/moxnas/startup.log 2>&1 &
    echo \$! > /var/run/moxnas.pid
    
    # Wait a moment for startup
    sleep 5
    
    # Check if it's running
    if ps -p \$(cat /var/run/moxnas.pid 2>/dev/null) > /dev/null 2>&1; then
        echo 'MoxNAS started successfully'
    else
        echo 'MoxNAS failed to start, checking logs...'
        tail -20 /var/log/moxnas/startup.log
    fi
"

# Get container IP
CONTAINER_IP=$(pct exec $CONTAINER_ID -- hostname -I | awk '{print $1}')

echo ""
echo "✅ MoxNAS Container Fixed!"
echo "=========================="
echo "🌐 Web Interface: http://$CONTAINER_IP:8080"
echo "👤 Login: admin / moxnas123"
echo ""
echo "🔧 Service Status:"
for service in ssh smbd nmbd nfs-kernel-server vsftpd; do
    if pct exec $CONTAINER_ID -- systemctl is-active --quiet $service; then
        echo "✅ $service: running"
    else
        echo "❌ $service: stopped"
    fi
done

echo ""
echo "🔍 Testing web interface..."
HTTP_CODE=$(pct exec $CONTAINER_ID -- curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    echo "✅ Web interface is responding (HTTP $HTTP_CODE)"
else
    echo "❌ Web interface not responding (HTTP $HTTP_CODE)"
    echo "📋 Checking MoxNAS logs..."
    pct exec $CONTAINER_ID -- tail -10 /var/log/moxnas/startup.log 2>/dev/null || echo "No logs found"
fi

echo ""
echo "🔧 If needed, you can:"
echo "1. Access container: pct enter $CONTAINER_ID"
echo "2. Check logs: pct exec $CONTAINER_ID -- tail -f /var/log/moxnas/startup.log"
echo "3. Restart MoxNAS: pct exec $CONTAINER_ID -- /opt/moxnas/start_container.sh"