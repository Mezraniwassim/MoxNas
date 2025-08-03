#!/bin/bash

# MoxNas Container Startup Script
# This script is meant to be run inside the LXC container to start MoxNas services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running inside container
check_container_environment() {
    if [ ! -f /.dockerenv ] && [ ! -d /proc/vz ] && [ ! -f /run/systemd/container ]; then
        if [ -z "$FORCE" ]; then
            warning "This script is designed to run inside an LXC container"
            warning "Set FORCE=1 to run anyway"
            exit 1
        fi
    fi
}

# Check if MoxNas is installed
check_moxnas_installation() {
    if [ ! -d "/opt/moxnas" ]; then
        error "MoxNas is not installed in /opt/moxnas"
        error "Please run the installation script first"
        exit 1
    fi
    
    if [ ! -f "/opt/moxnas/venv/bin/activate" ]; then
        error "Python virtual environment not found"
        error "Please reinstall MoxNas"
        exit 1
    fi
}

# Start MoxNas application
start_moxnas() {
    log "Starting MoxNas application..."
    
    cd /opt/moxnas
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Run database migrations (in case of updates)
    log "Running database migrations..."
    cd backend
    python manage.py migrate --noinput
    
    # Collect static files
    log "Collecting static files..."
    python manage.py collectstatic --noinput
    
    # Kill any existing gunicorn processes
    log "Stopping any existing MoxNas processes..."
    pkill -f "gunicorn.*moxnas.wsgi" 2>/dev/null || true
    sleep 2
    
    # Start Gunicorn server with the exact command that worked
    log "Starting Gunicorn server..."
    cd /opt/moxnas
    source venv/bin/activate
    gunicorn --bind 0.0.0.0:8000 --workers 3 --chdir backend --daemon moxnas.wsgi:application
    
    success "MoxNas application started"
}

# Check service status
check_services() {
    log "Checking service status..."
    
    # Check if Gunicorn is running
    if pgrep -f "gunicorn.*moxnas.wsgi" > /dev/null; then
        success "Gunicorn server is running"
    else
        error "Gunicorn server is not running"
        return 1
    fi
    
    # Check if port 8000 is listening
    if netstat -tlnp 2>/dev/null | grep -q ":8000 "; then
        success "MoxNas is listening on port 8000"
    else
        error "MoxNas is not listening on port 8000"
        return 1
    fi
    
    # Test HTTP response
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 | grep -q "200\|302"; then
        success "MoxNas web interface is responding"
    else
        warning "MoxNas web interface may not be responding correctly"
    fi
}

# Start additional services
start_additional_services() {
    log "Starting additional services..."
    
    # Start SSH service if available
    if systemctl is-enabled ssh >/dev/null 2>&1; then
        systemctl start ssh
        success "SSH service started"
    fi
    
    # Start nginx if configured
    if systemctl is-enabled nginx >/dev/null 2>&1; then
        systemctl start nginx
        success "Nginx service started"
    fi
    
    # You can add more services here as needed
    # Example:
    # if systemctl is-enabled vsftpd >/dev/null 2>&1; then
    #     systemctl start vsftpd
    #     success "FTP service started"
    # fi
}

# Display status information
show_status() {
    echo
    success "============================================"
    success "MoxNas Container Status"
    success "============================================"
    echo
    
    # Container information
    log "Container hostname: $(hostname)"
    log "Container IP: $(hostname -I | awk '{print $1}')"
    log "System uptime: $(uptime -p)"
    
    # Service status
    echo
    log "Service Status:"
    
    if pgrep -f "gunicorn.*moxnas.wsgi" > /dev/null; then
        log "  ✓ MoxNas Web Interface: RUNNING"
    else
        log "  ✗ MoxNas Web Interface: STOPPED"
    fi
    
    if systemctl is-active ssh >/dev/null 2>&1; then
        log "  ✓ SSH Service: RUNNING"
    else
        log "  ✗ SSH Service: STOPPED"
    fi
    
    if systemctl is-active nginx >/dev/null 2>&1; then
        log "  ✓ Nginx Service: RUNNING"
    else
        log "  ✗ Nginx Service: STOPPED"
    fi
    
    # Network information
    echo
    log "Network Access:"
    local ip_address=$(hostname -I | awk '{print $1}')
    if [ -n "$ip_address" ]; then
        log "  Web Interface: http://$ip_address:8000"
        log "  Admin Panel:   http://$ip_address:8000/admin"
    fi
    
    echo
    log "To stop MoxNas: pkill -f 'gunicorn.*moxnas.wsgi'"
    log "To restart MoxNas: systemctl restart moxnas"
    echo
}

# Stop MoxNas services
stop_moxnas() {
    log "Stopping MoxNas services..."
    
    # Stop Gunicorn processes
    if pgrep -f "gunicorn.*moxnas.wsgi" > /dev/null; then
        pkill -f "gunicorn.*moxnas.wsgi"
        sleep 2
        
        # Force kill if still running
        if pgrep -f "gunicorn.*moxnas.wsgi" > /dev/null; then
            pkill -9 -f "gunicorn.*moxnas.wsgi"
        fi
        
        success "MoxNas application stopped"
    else
        log "MoxNas application was not running"
    fi
}

# Main function
main() {
    case "${1:-start}" in
        start)
            echo "MoxNas Container Startup"
            echo "======================="
            echo
            
            check_container_environment
            check_moxnas_installation
            start_moxnas
            start_additional_services
            sleep 2
            check_services
            show_status
            ;;
        stop)
            echo "Stopping MoxNas Services"
            echo "======================="
            echo
            
            stop_moxnas
            success "MoxNas services stopped"
            ;;
        restart)
            echo "Restarting MoxNas Services"
            echo "========================="
            echo
            
            stop_moxnas
            sleep 2
            check_moxnas_installation
            start_moxnas
            start_additional_services
            sleep 2
            check_services
            show_status
            ;;
        status)
            echo "MoxNas Service Status"
            echo "===================="
            echo
            
            check_services
            show_status
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status}"
            echo
            echo "Commands:"
            echo "  start   - Start MoxNas services (default)"
            echo "  stop    - Stop MoxNas services"
            echo "  restart - Restart MoxNas services"
            echo "  status  - Show service status"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"