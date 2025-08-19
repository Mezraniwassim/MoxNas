#!/bin/bash
# MoxNAS NFS Share Management Script
# Copyright (c) 2024 MoxNAS Contributors
# License: MIT

set -euo pipefail

EXPORTS_FILE="/etc/exports"
SHARES_DIR="/mnt/shares"
LOG_FILE="/var/log/moxnas/nfs.log"

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

# Backup exports file
backup_exports() {
    local backup_file="${EXPORTS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$EXPORTS_FILE" "$backup_file" 2>/dev/null || touch "$backup_file"
    log "Backed up exports file to $backup_file"
}

# Validate export path
validate_export_path() {
    local path="$1"
    
    if [[ -z "$path" ]]; then
        log_error "Export path cannot be empty"
        return 1
    fi
    
    if [[ ! "$path" =~ ^/ ]]; then
        log_error "Export path must be absolute (start with /)"
        return 1
    fi
    
    return 0
}

# Check if export exists
export_exists() {
    local path="$1"
    [[ -f "$EXPORTS_FILE" ]] && grep -q "^$path " "$EXPORTS_FILE"
}

# Create NFS export
create_export() {
    local path="$1"
    local clients="${2:-*}"
    local options="${3:-rw,sync,no_subtree_check,all_squash,anonuid=65534,anongid=65534}"
    
    log "Creating NFS export: $path"
    
    # Validate input
    if ! validate_export_path "$path"; then
        return 1
    fi
    
    # Check if export already exists
    if export_exists "$path"; then
        log_error "Export '$path' already exists"
        return 1
    fi
    
    # Create directory if it doesn't exist
    if [[ ! -d "$path" ]]; then
        mkdir -p "$path"
        log "Created directory: $path"
    fi
    
    # Set proper permissions
    chown nobody:nogroup "$path"
    chmod 755 "$path"
    
    # Backup exports file
    backup_exports
    
    # Add export to exports file
    echo "$path $clients($options)" >> "$EXPORTS_FILE"
    
    # Export the new share
    if exportfs -ra; then
        log_success "NFS exports reloaded"
    else
        log_error "Failed to reload NFS exports"
        return 1
    fi
    
    log_success "Export '$path' created successfully"
    return 0
}

# Delete NFS export
delete_export() {
    local path="$1"
    local remove_directory="${2:-no}"
    
    log "Deleting NFS export: $path"
    
    # Validate input
    if ! validate_export_path "$path"; then
        return 1
    fi
    
    # Check if export exists
    if ! export_exists "$path"; then
        log_error "Export '$path' does not exist"
        return 1
    fi
    
    # Backup exports file
    backup_exports
    
    # Remove export from exports file
    if remove_export_from_file "$path"; then
        log_success "Removed export '$path' from exports file"
    else
        log_error "Failed to remove export from exports file"
        return 1
    fi
    
    # Unexport the share
    if exportfs -u "$path"; then
        log_success "Unexported '$path'"
    else
        log_warning "Failed to unexport '$path' (may not have been active)"
    fi
    
    # Reload exports
    if exportfs -ra; then
        log_success "NFS exports reloaded"
    else
        log_error "Failed to reload NFS exports"
        return 1
    fi
    
    # Remove directory if requested
    if [[ "$remove_directory" == "yes" ]] && [[ -d "$path" ]]; then
        rm -rf "$path"
        log_success "Removed directory: $path"
    fi
    
    log_success "Export '$path' deleted successfully"
    return 0
}

# Remove export from exports file
remove_export_from_file() {
    local path="$1"
    local temp_file
    temp_file=$(mktemp)
    
    # Remove line that starts with the export path
    grep -v "^$path " "$EXPORTS_FILE" > "$temp_file" 2>/dev/null || true
    
    if mv "$temp_file" "$EXPORTS_FILE"; then
        return 0
    else
        rm -f "$temp_file"
        return 1
    fi
}

# List all NFS exports
list_exports() {
    log "Listing NFS exports:"
    
    if [[ ! -f "$EXPORTS_FILE" ]]; then
        log_warning "Exports file not found: $EXPORTS_FILE"
        return 0
    fi
    
    echo "Export Path             Clients     Options"
    echo "-----------             -------     -------"
    
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Parse export line
        local path clients_options
        path=$(echo "$line" | awk '{print $1}')
        clients_options=$(echo "$line" | cut -d' ' -f2-)
        
        # Extract clients and options
        local clients options
        if [[ "$clients_options" =~ ^([^(]+)\((.+)\)$ ]]; then
            clients="${BASH_REMATCH[1]}"
            options="${BASH_REMATCH[2]}"
        else
            clients="$clients_options"
            options=""
        fi
        
        printf "%-23s %-11s %s\n" "$path" "$clients" "$options"
    done < "$EXPORTS_FILE"
}

# Show active NFS exports
show_active() {
    log "Showing active NFS exports:"
    
    if command -v exportfs >/dev/null 2>&1; then
        exportfs -v
    else
        log_error "exportfs command not found"
        return 1
    fi
}

# Check NFS service status
check_status() {
    log "Checking NFS service status:"
    
    local services=("nfs-kernel-server" "rpcbind")
    local all_running=true
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log_success "$service is running"
        else
            log_error "$service is not running"
            all_running=false
        fi
    done
    
    if $all_running; then
        echo
        log "NFS statistics:"
        if command -v nfsstat >/dev/null 2>&1; then
            nfsstat -s 2>/dev/null || log_warning "Could not get NFS statistics"
        fi
        
        echo
        log "Active NFS mounts:"
        if command -v showmount >/dev/null 2>&1; then
            showmount -a 2>/dev/null || log_warning "No active mounts or showmount failed"
        fi
    fi
    
    return $($all_running && echo 0 || echo 1)
}

# Test NFS configuration
test_config() {
    log "Testing NFS configuration:"
    
    if [[ ! -f "$EXPORTS_FILE" ]]; then
        log_warning "Exports file does not exist: $EXPORTS_FILE"
        return 0
    fi
    
    # Test exports syntax
    if exportfs -ra > /dev/null 2>&1; then
        log_success "NFS exports configuration is valid"
        return 0
    else
        log_error "NFS exports configuration has errors"
        exportfs -ra
        return 1
    fi
}

# Reload NFS exports
reload_exports() {
    log "Reloading NFS exports:"
    
    if exportfs -ra; then
        log_success "NFS exports reloaded successfully"
        return 0
    else
        log_error "Failed to reload NFS exports"
        return 1
    fi
}

# Show NFS client connections
show_connections() {
    log "Showing NFS client connections:"
    
    if command -v ss >/dev/null 2>&1; then
        echo "NFS connections (port 2049):"
        ss -tn state established '( sport = 2049 or dport = 2049 )' 2>/dev/null || log_warning "No NFS connections found"
    elif command -v netstat >/dev/null 2>&1; then
        echo "NFS connections (port 2049):"
        netstat -tn | grep ':2049 ' 2>/dev/null || log_warning "No NFS connections found"
    else
        log_warning "Neither ss nor netstat found"
    fi
}

# Show help
show_help() {
    cat << EOF
MoxNAS NFS Management Script

Usage: $0 COMMAND [OPTIONS]

Commands:
  create PATH [CLIENTS] [OPTIONS]  Create a new NFS export
  delete PATH [--remove-dir]       Delete an NFS export
  list                            List all NFS exports
  active                          Show active NFS exports
  status                          Check NFS service status
  test                           Test NFS configuration
  reload                         Reload NFS exports
  connections                    Show client connections
  help                           Show this help message

Create Options:
  PATH                           Export path (must be absolute)
  CLIENTS                        Client specification (default: *)
  OPTIONS                        Mount options (default: rw,sync,no_subtree_check,all_squash,anonuid=65534,anongid=65534)

Delete Options:
  --remove-dir                   Also remove the export directory

Client Examples:
  *                              All clients
  192.168.1.0/24                Subnet
  client1.example.com           Specific host
  *.example.com                 Domain wildcard

Option Examples:
  rw,sync,no_subtree_check      Read-write, synchronous
  ro,sync,no_subtree_check      Read-only
  rw,async,no_root_squash       Read-write, allow root access

Examples:
  $0 create /mnt/shares/documents
  $0 create /mnt/shares/backup "192.168.1.0/24" "ro,sync,no_subtree_check"
  $0 delete /mnt/shares/documents --remove-dir
  $0 list
  $0 active
  $0 status

EOF
}

# Main script logic
main() {
    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")"
    
    case "${1:-}" in
        create)
            if [[ $# -lt 2 ]]; then
                log_error "Export path required for create command"
                show_help
                exit 1
            fi
            
            local path="$2"
            local clients="${3:-*}"
            local options="${4:-rw,sync,no_subtree_check,all_squash,anonuid=65534,anongid=65534}"
            
            create_export "$path" "$clients" "$options"
            ;;
            
        delete)
            if [[ $# -lt 2 ]]; then
                log_error "Export path required for delete command"
                show_help
                exit 1
            fi
            
            local path="$2"
            local remove_directory="no"
            
            # Parse options
            shift 2
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --remove-dir)
                        remove_directory="yes"
                        shift
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
            done
            
            delete_export "$path" "$remove_directory"
            ;;
            
        list)
            list_exports
            ;;
            
        active)
            show_active
            ;;
            
        status)
            check_status
            ;;
            
        test)
            test_config
            ;;
            
        reload)
            reload_exports
            ;;
            
        connections)
            show_connections
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