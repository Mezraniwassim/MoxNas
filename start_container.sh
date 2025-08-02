#!/bin/bash

# MoxNAS Container Startup Script
# This script should be run inside the LXC container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m' 
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Function to check if we're in a container
check_container() {
    if [ -f /.dockerenv ] || [ -f /run/.containerenv ] || systemd-detect-virt -c >/dev/null 2>&1; then
        log "Container environment detected"
        return 0
    else
        warn "Not running in a container environment"
        return 1
    fi
}

# Function to ensure required directories exist
ensure_directories() {
    log "Ensuring required directories exist..."
    
    local dirs=(
        "/mnt/storage"
        "/var/log/moxnas"
        "/etc/moxnas"
        "/var/run/moxnas"
        "/opt/moxnas"
    )
    
    for dir in "${dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            chmod 755 "$dir"
            log "Created directory: $dir"
        fi
    done
}

# Function to check if MoxNAS is installed
check_moxnas_installation() {
    if [ ! -d "/opt/moxnas" ] || [ ! -f "/opt/moxnas/backend/manage.py" ]; then
        error "MoxNAS is not installed. Please run the installation script first."
        exit 1
    fi
    log "MoxNAS installation found"
}

# Function to start essential services
start_services() {
    log "Starting essential services..."
    
    # Services to start
    local services=(
        "ssh"
    )
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log "Service $service is already running"
        else
            log "Starting service: $service"
            if systemctl start "$service" 2>/dev/null; then
                log "Service $service started successfully"
            else
                warn "Failed to start service $service via systemctl"
                # Try alternative methods for containers
                case "$service" in
                    "ssh")
                        if /usr/sbin/sshd -D &>/dev/null &; then
                            log "SSH started using alternative method"
                        fi
                        ;;
                esac
            fi
        fi
    done
}

# Function to check port availability
check_port() {
    local port=$1
    if netstat -tuln | grep -q ":$port "; then
        return 1  # Port is in use
    else
        return 0  # Port is available
    fi
}

# Function to kill processes on port
kill_port_processes() {
    local port=$1
    log "Checking for processes on port $port..."
    
    local pids=$(lsof -ti ":$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        log "Killing processes on port $port: $pids"
        echo "$pids" | xargs -r kill -9
        sleep 2
    fi
}

# Function to start MoxNAS web interface
start_moxnas_web() {
    log "Starting MoxNAS web interface..."
    
    cd /opt/moxnas || exit 1
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        error "Python virtual environment not found. Please run installation script."
        exit 1
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Change to backend directory
    cd backend || exit 1
    
    # Set environment variables
    export DJANGO_SETTINGS_MODULE=moxnas.settings
    export PYTHONPATH="/opt/moxnas/backend:$PYTHONPATH"
    
    # Check if Django is working
    if ! python manage.py check --deploy 2>/dev/null; then
        warn "Django check failed, but continuing..."
    fi
    
    # Run migrations
    log "Running database migrations..."
    python manage.py migrate --noinput || warn "Migration failed"
    
    # Collect static files
    log "Collecting static files..."
    python manage.py collectstatic --noinput || warn "Static files collection failed"
    
    # Initialize services
    log "Initializing MoxNAS services..."
    python manage.py initialize_services || warn "Service initialization failed"
    
    # Kill any existing processes on port 8000
    kill_port_processes 8000
    
    # Start gunicorn
    local port=8000
    local workers=3
    
    log "Starting gunicorn on port $port..."
    
    # Create log files if they don't exist
    touch /var/log/moxnas/access.log
    touch /var/log/moxnas/error.log
    chmod 644 /var/log/moxnas/*.log
    
    # Start gunicorn with proper configuration
    exec gunicorn \
        --bind "0.0.0.0:$port" \
        --workers "$workers" \
        --timeout 120 \
        --keep-alive 2 \
        --max-requests 1000 \
        --preload \
        --user root \
        --group root \
        --access-logfile /var/log/moxnas/access.log \
        --error-logfile /var/log/moxnas/error.log \
        --log-level info \
        --daemon \
        moxnas.wsgi:application
    
    # Wait a moment and check if it started
    sleep 3
    
    if check_port 8000; then
        error "Gunicorn failed to start on port 8000"
        # Try development server as fallback
        log "Trying Django development server as fallback..."
        exec python manage.py runserver 0.0.0.0:8000
    else
        log "✅ MoxNAS web interface started successfully on port 8000"
        
        # Get container IP
        local container_ip=$(hostname -I | awk '{print $1}')
        log "🌐 Access MoxNAS at: http://$container_ip:8000"
    fi
}

# Function to show status
show_status() {
    log "MoxNAS Container Status:"
    log "========================"
    
    # Check MoxNAS web interface
    if check_port 8000; then
        warn "MoxNAS web interface: NOT RUNNING"
    else
        log "MoxNAS web interface: RUNNING on port 8000"
    fi
    
    # Check essential services
    local services=("ssh" "smbd" "nmbd" "vsftpd" "nfs-kernel-server")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log "Service $service: RUNNING"
        elif pgrep -f "$service" >/dev/null 2>&1; then
            log "Service $service: RUNNING (detected via process)"
        else
            warn "Service $service: NOT RUNNING"
        fi
    done
    
    # Show disk usage
    log "Storage usage:"
    df -h /mnt/storage 2>/dev/null || log "Storage not mounted"
    
    # Show memory usage
    log "Memory usage:"
    free -h
}

# Main function
main() {
    case "${1:-start}" in
        "start")
            log "🚀 Starting MoxNAS container services..."
            check_container
            ensure_directories
            check_moxnas_installation
            start_services
            start_moxnas_web
            ;;
        "status")
            show_status
            ;;
        "stop")
            log "Stopping MoxNAS services..."
            kill_port_processes 8000
            log "MoxNAS services stopped"
            ;;
        "restart")
            log "Restarting MoxNAS services..."
            kill_port_processes 8000
            sleep 2
            start_moxnas_web
            ;;
        *)
            log "Usage: $0 {start|stop|restart|status}"
            log "  start   - Start MoxNAS services (default)"
            log "  stop    - Stop MoxNAS services"
            log "  restart - Restart MoxNAS services"
            log "  status  - Show service status"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"