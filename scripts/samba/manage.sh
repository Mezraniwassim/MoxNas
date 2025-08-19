#!/bin/bash
# MoxNAS Samba Share Management Script
# Copyright (c) 2024 MoxNAS Contributors
# License: MIT

set -euo pipefail

SHARES_DIR="/mnt/shares"
SMB_CONF="/etc/samba/smb.conf"
LOG_FILE="/var/log/moxnas/samba.log"

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

# Backup Samba configuration
backup_config() {
    local backup_file="${SMB_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$SMB_CONF" "$backup_file"
    log "Backed up Samba config to $backup_file"
}

# Validate share name
validate_share_name() {
    local name="$1"
    
    if [[ -z "$name" ]]; then
        log_error "Share name cannot be empty"
        return 1
    fi
    
    if [[ "$name" =~ [[:space:]] ]]; then
        log_error "Share name cannot contain spaces"
        return 1
    fi
    
    if [[ "$name" == "global" ]] || [[ "$name" == "homes" ]] || [[ "$name" == "printers" ]]; then
        log_error "Share name '$name' is reserved"
        return 1
    fi
    
    return 0
}

# Check if share exists
share_exists() {
    local name="$1"
    grep -q "^\[$name\]" "$SMB_CONF"
}

# Create Samba share
create_share() {
    local name="$1"
    local path="${2:-${SHARES_DIR}/${name}}"
    local read_only="${3:-no}"
    local guest_ok="${4:-yes}"
    local browseable="${5:-yes}"
    local create_mask="${6:-0755}"
    local directory_mask="${7:-0755}"
    
    log "Creating Samba share: $name"
    
    # Validate input
    if ! validate_share_name "$name"; then
        return 1
    fi
    
    # Check if share already exists
    if share_exists "$name"; then
        log_error "Share '$name' already exists"
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
    
    # Backup configuration
    backup_config
    
    # Add share configuration to smb.conf
    cat >> "$SMB_CONF" << EOL

[${name}]
   comment = MoxNAS ${name} share
   path = ${path}
   browseable = ${browseable}
   read only = ${read_only}
   guest ok = ${guest_ok}
   create mask = ${create_mask}
   directory mask = ${directory_mask}
   force user = nobody
   force group = nogroup
   map archive = no
   store dos attributes = yes
   vfs objects = catia fruit streams_xattr
   fruit:metadata = stream
   fruit:model = MacSamba
   fruit:posix_rename = yes
   fruit:veto_appledouble = no
   fruit:wipe_intentionally_left_blank_rfork = yes
   fruit:delete_empty_adfiles = yes
EOL
    
    # Test Samba configuration
    if testparm -s "$SMB_CONF" > /dev/null 2>&1; then
        log_success "Samba configuration is valid"
    else
        log_error "Samba configuration is invalid"
        return 1
    fi
    
    # Reload Samba service
    if systemctl reload smbd; then
        log_success "Samba service reloaded"
    else
        log_error "Failed to reload Samba service"
        return 1
    fi
    
    log_success "Share '$name' created successfully at '$path'"
    return 0
}

# Delete Samba share
delete_share() {
    local name="$1"
    local remove_directory="${2:-no}"
    
    log "Deleting Samba share: $name"
    
    # Validate input
    if ! validate_share_name "$name"; then
        return 1
    fi
    
    # Check if share exists
    if ! share_exists "$name"; then
        log_error "Share '$name' does not exist"
        return 1
    fi
    
    # Get share path before deletion
    local share_path
    share_path=$(get_share_path "$name")
    
    # Backup configuration
    backup_config
    
    # Remove share from smb.conf
    if remove_share_from_config "$name"; then
        log_success "Removed share '$name' from configuration"
    else
        log_error "Failed to remove share from configuration"
        return 1
    fi
    
    # Test Samba configuration
    if testparm -s "$SMB_CONF" > /dev/null 2>&1; then
        log_success "Samba configuration is valid after removal"
    else
        log_error "Samba configuration is invalid after removal"
        return 1
    fi
    
    # Reload Samba service
    if systemctl reload smbd; then
        log_success "Samba service reloaded"
    else
        log_error "Failed to reload Samba service"
        return 1
    fi
    
    # Remove directory if requested
    if [[ "$remove_directory" == "yes" ]] && [[ -n "$share_path" ]] && [[ -d "$share_path" ]]; then
        rm -rf "$share_path"
        log_success "Removed directory: $share_path"
    fi
    
    log_success "Share '$name' deleted successfully"
    return 0
}

# Get share path from configuration
get_share_path() {
    local name="$1"
    
    awk -v share="[$name]" '
        $0 == share { in_share = 1; next }
        /^\[/ && in_share { in_share = 0 }
        in_share && /^[[:space:]]*path[[:space:]]*=/ {
            sub(/^[[:space:]]*path[[:space:]]*=[[:space:]]*/, "")
            print
            exit
        }
    ' "$SMB_CONF"
}

# Remove share section from smb.conf
remove_share_from_config() {
    local name="$1"
    local temp_file
    temp_file=$(mktemp)
    
    awk -v share="[$name]" '
        $0 == share { in_share = 1; next }
        /^\[/ && in_share { in_share = 0 }
        !in_share { print }
    ' "$SMB_CONF" > "$temp_file"
    
    if mv "$temp_file" "$SMB_CONF"; then
        return 0
    else
        rm -f "$temp_file"
        return 1
    fi
}

# List all Samba shares
list_shares() {
    log "Listing Samba shares:"
    
    if [[ ! -f "$SMB_CONF" ]]; then
        log_error "Samba configuration file not found: $SMB_CONF"
        return 1
    fi
    
    echo "Share Name      Path                           Read Only   Guest OK"
    echo "----------      ----                           ---------   --------"
    
    awk '
        /^\[.*\]/ && $0 != "[global]" {
            gsub(/[\[\]]/, "", $0)
            share_name = $0
            path = ""
            read_only = "no"
            guest_ok = "no"
        }
        /^[[:space:]]*path[[:space:]]*=/ {
            sub(/^[[:space:]]*path[[:space:]]*=[[:space:]]*/, "")
            path = $0
        }
        /^[[:space:]]*read only[[:space:]]*=/ {
            sub(/^[[:space:]]*read only[[:space:]]*=[[:space:]]*/, "")
            read_only = $0
        }
        /^[[:space:]]*guest ok[[:space:]]*=/ {
            sub(/^[[:space:]]*guest ok[[:space:]]*=[[:space:]]*/, "")
            guest_ok = $0
        }
        /^\[.*\]/ && share_name != "" && path != "" {
            printf "%-15s %-30s %-11s %s\n", prev_share, prev_path, prev_readonly, prev_guest
            prev_share = share_name
            prev_path = path
            prev_readonly = read_only
            prev_guest = guest_ok
            path = ""
        }
        END {
            if (share_name != "" && path != "") {
                printf "%-15s %-30s %-11s %s\n", share_name, path, read_only, guest_ok
            }
        }
    ' "$SMB_CONF"
}

# Check Samba service status
check_status() {
    log "Checking Samba service status:"
    
    if systemctl is-active --quiet smbd; then
        log_success "Samba service is running"
        
        # Show share connections
        if command -v smbstatus >/dev/null 2>&1; then
            echo
            log "Active connections:"
            smbstatus --shares 2>/dev/null || log_warning "Could not get share status"
        fi
    else
        log_error "Samba service is not running"
        return 1
    fi
}

# Test Samba configuration
test_config() {
    log "Testing Samba configuration:"
    
    if testparm -s "$SMB_CONF" > /dev/null 2>&1; then
        log_success "Samba configuration is valid"
        return 0
    else
        log_error "Samba configuration has errors:"
        testparm -s "$SMB_CONF"
        return 1
    fi
}

# Show help
show_help() {
    cat << EOF
MoxNAS Samba Management Script

Usage: $0 COMMAND [OPTIONS]

Commands:
  create NAME [PATH] [OPTIONS]  Create a new Samba share
  delete NAME [--remove-dir]    Delete a Samba share
  list                         List all Samba shares
  status                       Check Samba service status
  test                         Test Samba configuration
  help                         Show this help message

Create Options:
  --read-only yes|no          Set share as read-only (default: no)
  --guest-ok yes|no           Allow guest access (default: yes)
  --browseable yes|no         Make share browseable (default: yes)
  --create-mask MASK          File creation mask (default: 0755)
  --directory-mask MASK       Directory creation mask (default: 0755)

Delete Options:
  --remove-dir               Also remove the share directory

Examples:
  $0 create documents
  $0 create backup /mnt/backup --read-only yes --guest-ok no
  $0 delete documents --remove-dir
  $0 list
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
                log_error "Share name required for create command"
                show_help
                exit 1
            fi
            
            local name="$2"
            local path="${3:-${SHARES_DIR}/${name}}"
            local read_only="no"
            local guest_ok="yes"
            local browseable="yes"
            local create_mask="0755"
            local directory_mask="0755"
            
            # Parse additional options
            shift 3 2>/dev/null || shift 2
            while [[ $# -gt 0 ]]; do
                case "$1" in
                    --read-only)
                        read_only="$2"
                        shift 2
                        ;;
                    --guest-ok)
                        guest_ok="$2"
                        shift 2
                        ;;
                    --browseable)
                        browseable="$2"
                        shift 2
                        ;;
                    --create-mask)
                        create_mask="$2"
                        shift 2
                        ;;
                    --directory-mask)
                        directory_mask="$2"
                        shift 2
                        ;;
                    *)
                        log_error "Unknown option: $1"
                        exit 1
                        ;;
                esac
            done
            
            create_share "$name" "$path" "$read_only" "$guest_ok" "$browseable" "$create_mask" "$directory_mask"
            ;;
            
        delete)
            if [[ $# -lt 2 ]]; then
                log_error "Share name required for delete command"
                show_help
                exit 1
            fi
            
            local name="$2"
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
            
            delete_share "$name" "$remove_directory"
            ;;
            
        list)
            list_shares
            ;;
            
        status)
            check_status
            ;;
            
        test)
            test_config
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