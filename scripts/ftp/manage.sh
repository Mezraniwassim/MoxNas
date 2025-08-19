#!/bin/bash
# MoxNAS FTP Management Script
# Copyright (c) 2024 MoxNAS Contributors
# License: MIT

set -euo pipefail

VSFTPD_CONF="/etc/vsftpd.conf"
FTP_ROOT="/mnt/shares/ftp"
LOG_FILE="/var/log/moxnas/ftp.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Backup vsftpd configuration
backup_config() {
    local backup_file="${VSFTPD_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$VSFTPD_CONF" "$backup_file"
    log "Backed up vsftpd config to $backup_file"
}

# Check if vsftpd is installed
check_vsftpd() {
    if ! command -v vsftpd >/dev/null 2>&1; then
        log_error "vsftpd is not installed"
        return 1
    fi
    return 0
}

# Setup FTP directory structure
setup_ftp_structure() {
    local root_dir="$1"
    
    log "Setting up FTP directory structure at $root_dir"
    
    # Create FTP root directory
    mkdir -p "$root_dir"
    
    # Create subdirectories
    mkdir -p "$root_dir/upload"
    mkdir -p "$root_dir/download" 
    mkdir -p "$root_dir/public"
    
    # Set permissions
    chown -R ftp:ftp "$root_dir"
    chmod 755 "$root_dir"
    chmod 755 "$root_dir/download"
    chmod 755 "$root_dir/public"
    chmod 777 "$root_dir/upload"
    
    log_success "FTP directory structure created"
}

# Configure vsftpd for anonymous access
configure_anonymous() {
    local ftp_root="${1:-$FTP_ROOT}"
    local allow_upload="${2:-yes}"
    local allow_download="${3:-yes}"
    
    log "Configuring vsftpd for anonymous access"
    
    if ! check_vsftpd; then
        return 1
    fi
    
    # Setup FTP structure
    setup_ftp_structure "$ftp_root"
    
    # Backup configuration
    backup_config
    
    # Create vsftpd configuration
    cat > "$VSFTPD_CONF" << EOF
# MoxNAS vsftpd Configuration
# Listen on IPv4
listen=YES
listen_ipv6=NO

# Anonymous FTP settings
anonymous_enable=YES
local_enable=NO
write_enable=YES

# Anonymous user settings
anon_upload_enable=$([ "$allow_upload" = "yes" ] && echo "YES" || echo "NO")
anon_mkdir_write_enable=$([ "$allow_upload" = "yes" ] && echo "YES" || echo "NO")
anon_other_write_enable=$([ "$allow_upload" = "yes" ] && echo "YES" || echo "NO")

# Anonymous root directory
anon_root=${ftp_root}

# Security settings
chroot_local_user=YES
allow_writeable_chroot=YES
secure_chroot_dir=/var/run/vsftpd/empty

# Connection settings
max_clients=50
max_per_ip=5
connect_from_port_20=YES
ftp_data_port=20

# Logging
xferlog_enable=YES
xferlog_file=/var/log/vsftpd.log
log_ftp_protocol=YES

# Messages
ftpd_banner=Welcome to MoxNAS FTP Service
dirmessage_enable=YES
message_file=.message

# Timeouts
idle_session_timeout=300
data_connection_timeout=120

# Passive mode settings
pasv_enable=YES
pasv_min_port=30000
pasv_max_port=31000

# Performance
use_localtime=YES
check_shell=NO

# SSL/TLS (disabled by default)
ssl_enable=NO
allow_anon_ssl=NO

# Hide dot files
hide_file={.*}
hide_ids=YES
EOF
    
    log_success "vsftpd configured for anonymous access"
}

# Configure vsftpd for local users
configure_local_users() {
    local allow_anonymous="${1:-no}"
    
    log "Configuring vsftpd for local users"
    
    if ! check_vsftpd; then
        return 1
    fi
    
    # Backup configuration
    backup_config
    
    # Create vsftpd configuration
    cat > "$VSFTPD_CONF" << EOF
# MoxNAS vsftpd Configuration - Local Users
# Listen on IPv4
listen=YES
listen_ipv6=NO

# Local user settings
local_enable=YES
write_enable=YES
local_umask=022

# Anonymous settings
anonymous_enable=$([ "$allow_anonymous" = "yes" ] && echo "YES" || echo "NO")

# Chroot settings
chroot_local_user=YES
chroot_list_enable=NO
allow_writeable_chroot=YES
secure_chroot_dir=/var/run/vsftpd/empty

# Connection settings
max_clients=50
max_per_ip=5
connect_from_port_20=YES
ftp_data_port=20

# Logging
xferlog_enable=YES
xferlog_file=/var/log/vsftpd.log
log_ftp_protocol=YES

# Messages
ftpd_banner=Welcome to MoxNAS FTP Service
dirmessage_enable=YES

# Timeouts
idle_session_timeout=600
data_connection_timeout=120

# Passive mode settings
pasv_enable=YES
pasv_min_port=30000
pasv_max_port=31000

# Performance
use_localtime=YES

# SSL/TLS (disabled by default)
ssl_enable=NO

# User list (if needed)
userlist_enable=NO
EOF
    
    log_success "vsftpd configured for local users"
}

# Enable SSL/TLS
enable_ssl() {
    log "Enabling SSL/TLS for FTP"
    
    if ! check_vsftpd; then
        return 1
    fi
    
    # Check if SSL certificate exists
    if [[ ! -f /etc/ssl/certs/vsftpd.pem ]]; then
        log "Creating self-signed SSL certificate"
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /etc/ssl/private/vsftpd.key \
            -out /etc/ssl/certs/vsftpd.pem \
            -subj "/C=US/ST=State/L=City/O=MoxNAS/CN=moxnas-ftp" 2>/dev/null
        
        chmod 600 /etc/ssl/private/vsftpd.key
        chmod 644 /etc/ssl/certs/vsftpd.pem
        log_success "SSL certificate created"
    fi
    
    # Backup configuration
    backup_config
    
    # Add SSL settings to configuration
    cat >> "$VSFTPD_CONF" << EOF

# SSL/TLS Configuration
ssl_enable=YES
allow_anon_ssl=NO
force_local_data_ssl=YES
force_local_logins_ssl=YES
ssl_tlsv1=YES
ssl_sslv2=NO
ssl_sslv3=NO
rsa_cert_file=/etc/ssl/certs/vsftpd.pem
rsa_private_key_file=/etc/ssl/private/vsftpd.key
require_ssl_reuse=NO
ssl_ciphers=HIGH
EOF
    
    log_success "SSL/TLS enabled for FTP"
}

# Create FTP user
create_ftp_user() {
    local username="$1"
    local home_dir="${2:-/mnt/shares/ftp/$username}"
    
    log "Creating FTP user: $username"
    
    # Check if user already exists
    if id "$username" &>/dev/null; then
        log_error "User '$username' already exists"
        return 1
    fi
    
    # Create user with FTP home directory
    useradd -d "$home_dir" -m -s /bin/bash "$username"
    
    # Set initial password (user should change this)
    echo "$username:moxnas123" | chpasswd
    
    # Create user's FTP directories
    mkdir -p "$home_dir/upload"
    mkdir -p "$home_dir/download"
    
    # Set proper ownership and permissions
    chown -R "$username:$username" "$home_dir"
    chmod 755 "$home_dir"
    chmod 755 "$home_dir/download"
    chmod 777 "$home_dir/upload"
    
    log_success "FTP user '$username' created with home directory '$home_dir'"
    log_warning "Default password is 'moxnas123' - user should change it immediately"
}

# Delete FTP user
delete_ftp_user() {
    local username="$1"
    local remove_home="${2:-no}"
    
    log "Deleting FTP user: $username"
    
    # Check if user exists
    if ! id "$username" &>/dev/null; then
        log_error "User '$username' does not exist"
        return 1
    fi
    
    # Remove user
    if [[ "$remove_home" == "yes" ]]; then
        userdel -r "$username"
        log_success "User '$username' and home directory removed"
    else
        userdel "$username"
        log_success "User '$username' removed (home directory preserved)"
    fi
}

# List FTP users
list_ftp_users() {
    log "Listing FTP users:"
    
    echo "Username        Home Directory                    Shell"
    echo "--------        ---------------                    -----"
    
    # List users with home directories in FTP area
    while IFS=: read -r username _ uid gid _ home shell; do
        if [[ "$home" =~ ^/mnt/shares/ftp ]] || [[ "$username" == "ftp" ]]; then
            printf "%-15s %-30s %s\n" "$username" "$home" "$shell"
        fi
    done < /etc/passwd
}

# Check FTP service status
check_status() {
    log "Checking FTP service status:"
    
    if systemctl is-active --quiet vsftpd; then
        log_success "vsftpd service is running"
        
        # Show FTP connections
        echo
        log "Active FTP connections:"
        if command -v ss >/dev/null 2>&1; then
            ss -tn state established '( sport = 21 or dport = 21 )' 2>/dev/null || log "No active FTP connections"
        elif command -v netstat >/dev/null 2>&1; then
            netstat -tn | grep ':21 ' 2>/dev/null || log "No active FTP connections"
        fi
        
        # Show passive port range
        echo
        log "Passive port range:"
        grep -E "pasv_(min|max)_port" "$VSFTPD_CONF" 2>/dev/null || log "Passive mode not configured"
        
    else
        log_error "vsftpd service is not running"
        return 1
    fi
}

# Test FTP configuration
test_config() {
    log "Testing FTP configuration:"
    
    if [[ ! -f "$VSFTPD_CONF" ]]; then
        log_error "vsftpd configuration file not found: $VSFTPD_CONF"
        return 1
    fi
    
    # Test configuration by doing a dry run
    if vsftpd "$VSFTPD_CONF" -oDaemon=NO -oListen=NO 2>/dev/null; then
        log_success "vsftpd configuration is valid"
        return 0
    else
        log_error "vsftpd configuration has errors"
        return 1
    fi
}

# Show FTP logs
show_logs() {
    local lines="${1:-50}"
    
    log "Showing last $lines lines of FTP logs:"
    
    if [[ -f /var/log/vsftpd.log ]]; then
        tail -n "$lines" /var/log/vsftpd.log
    else
        log_warning "FTP log file not found"
    fi
}

# Show help
show_help() {
    cat << EOF
MoxNAS FTP Management Script

Usage: $0 COMMAND [OPTIONS]

Commands:
  setup-anonymous [ROOT] [UPLOAD] [DOWNLOAD]  Setup anonymous FTP access
  setup-users [ALLOW_ANON]                    Setup local user FTP access
  enable-ssl                                  Enable SSL/TLS encryption
  create-user USERNAME [HOME_DIR]             Create FTP user
  delete-user USERNAME [--remove-home]        Delete FTP user
  list-users                                  List FTP users
  status                                      Check FTP service status
  test                                        Test FTP configuration
  logs [LINES]                               Show FTP logs
  help                                        Show this help message

Setup Options:
  ROOT                                        FTP root directory (default: /mnt/shares/ftp)
  UPLOAD                                      Allow upload (yes/no, default: yes)
  DOWNLOAD                                    Allow download (yes/no, default: yes)
  ALLOW_ANON                                  Allow anonymous access (yes/no, default: no)

Examples:
  $0 setup-anonymous
  $0 setup-anonymous /mnt/ftp yes no
  $0 setup-users no
  $0 enable-ssl
  $0 create-user ftpuser1
  $0 delete-user ftpuser1 --remove-home
  $0 status
  $0 logs 100

Notes:
  - Anonymous FTP allows unrestricted access
  - Local user FTP requires system accounts
  - SSL/TLS creates self-signed certificates
  - Passive port range is 30000-31000
  - Default user password is 'moxnas123'

EOF
}

# Main script logic
main() {
    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")"
    
    case "${1:-}" in
        setup-anonymous)
            local ftp_root="${2:-$FTP_ROOT}"
            local allow_upload="${3:-yes}"
            local allow_download="${4:-yes}"
            
            configure_anonymous "$ftp_root" "$allow_upload" "$allow_download"
            
            # Restart service
            if systemctl restart vsftpd; then
                log_success "vsftpd service restarted"
            else
                log_error "Failed to restart vsftpd service"
                return 1
            fi
            ;;
            
        setup-users)
            local allow_anonymous="${2:-no}"
            
            configure_local_users "$allow_anonymous"
            
            # Restart service
            if systemctl restart vsftpd; then
                log_success "vsftpd service restarted"
            else
                log_error "Failed to restart vsftpd service"
                return 1
            fi
            ;;
            
        enable-ssl)
            enable_ssl
            
            # Restart service
            if systemctl restart vsftpd; then
                log_success "vsftpd service restarted with SSL"
            else
                log_error "Failed to restart vsftpd service"
                return 1
            fi
            ;;
            
        create-user)
            if [[ $# -lt 2 ]]; then
                log_error "Username required for create-user command"
                show_help
                exit 1
            fi
            
            local username="$2"
            local home_dir="${3:-/mnt/shares/ftp/$username}"
            
            create_ftp_user "$username" "$home_dir"
            ;;
            
        delete-user)
            if [[ $# -lt 2 ]]; then
                log_error "Username required for delete-user command"
                show_help
                exit 1
            fi
            
            local username="$2"
            local remove_home="no"
            
            # Parse options
            shift 2
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --remove-home)
                        remove_home="yes"
                        shift
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
            done
            
            delete_ftp_user "$username" "$remove_home"
            ;;
            
        list-users)
            list_ftp_users
            ;;
            
        status)
            check_status
            ;;
            
        test)
            test_config
            ;;
            
        logs)
            local lines="${2:-50}"
            show_logs "$lines"
            ;;
            
        help|--help|-h)
            show_help
            ;;
            
        "")
            log_error "No command specified"
            show_help
            exit 1
            ;;
            
        *)
            log_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi