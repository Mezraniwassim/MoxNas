#!/bin/bash

# Fix AppArmor issues in LXC containers
# This script addresses AppArmor conflicts that can prevent services from starting

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m' 
YELLOW='\033[1;33m'
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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
        exit 1
    fi
}

# Check if AppArmor is active
check_apparmor() {
    if command -v aa-status >/dev/null 2>&1; then
        if aa-status >/dev/null 2>&1; then
            log "AppArmor is active"
            return 0
        else
            log "AppArmor is not active"
            return 1
        fi
    else
        log "AppArmor is not installed"
        return 1
    fi
}

# Disable problematic AppArmor profiles for containers
disable_problematic_profiles() {
    log "Disabling problematic AppArmor profiles for container environment..."
    
    # Common profiles that cause issues in containers
    local profiles=(
        "/usr/sbin/smbd"
        "/usr/sbin/nmbd"
        "/usr/sbin/vsftpd"
        "/usr/sbin/sshd"
        "/usr/bin/man"
        "/bin/ping"
        "/usr/lib/snapd/snapd"
    )
    
    for profile in "${profiles[@]}"; do
        # Check if profile exists and is enforced
        if aa-status | grep -q "$profile.*enforce" 2>/dev/null; then
            log "Disabling AppArmor profile: $profile"
            aa-disable "$profile" 2>/dev/null || warn "Failed to disable $profile"
        elif aa-status | grep -q "$profile.*complain" 2>/dev/null; then
            log "AppArmor profile $profile is in complain mode (OK)"
        else
            log "AppArmor profile $profile is not enforced"
        fi
    done
}

# Create AppArmor override for container services
create_apparmor_overrides() {
    log "Creating AppArmor overrides for container services..."
    
    # Create override directory
    mkdir -p /etc/apparmor.d/local
    
    # Create local overrides for common services
    cat > /etc/apparmor.d/local/usr.sbin.smbd << 'EOF'
# Local AppArmor overrides for smbd in containers
# Allow additional capabilities needed in container environments

capability sys_admin,
capability sys_resource,
capability dac_override,
capability dac_read_search,
capability chown,
capability fowner,
capability fsetid,

# Allow access to container filesystems
/mnt/** rwk,
/opt/** rwk,
/var/log/** rw,
/run/** rw,

# Allow proc access
/proc/sys/kernel/core_pattern r,
/proc/*/stat r,
/proc/*/status r,
EOF

    cat > /etc/apparmor.d/local/usr.sbin.vsftpd << 'EOF'
# Local AppArmor overrides for vsftpd in containers

capability sys_chroot,
capability sys_admin,
capability dac_override,
capability chown,
capability fowner,
capability setuid,
capability setgid,

# Allow access to container filesystems
/mnt/** rwk,
/opt/** rwk,
/var/log/** rw,
/run/** rw,
/var/run/vsftpd/** rwk,

# Allow network access
network inet stream,
network unix stream,
EOF

    log "AppArmor overrides created"
}

# Set container-friendly AppArmor configuration
configure_apparmor_for_container() {
    log "Configuring AppArmor for container environment..."
    
    # Create container-specific configuration
    cat > /etc/apparmor.d/lxc-containers << 'EOF'
# AppArmor profile for LXC containers
# This profile allows most operations needed by containerized services

#include <tunables/global>

profile lxc-container flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  #include <abstractions/nameservice>
  #include <abstractions/user-tmp>

  # Allow most capabilities for services
  capability,
  
  # Network access
  network,
  
  # File access - be permissive for container filesystems
  /mnt/** rwkl,
  /opt/** rwkl,
  /var/** rwkl,
  /tmp/** rwkl,
  /run/** rwkl,
  /proc/** r,
  /sys/** r,
  
  # Allow execution of system binaries
  /bin/** px,
  /sbin/** px,
  /usr/bin/** px,
  /usr/sbin/** px,
  /usr/lib/** px,
  
  # Allow shared libraries
  /lib/** mr,
  /lib64/** mr,
  /usr/lib/** mr,
  
  # Device access
  /dev/null rw,
  /dev/zero rw,
  /dev/random r,
  /dev/urandom r,
  /dev/pts/** rw,
  /dev/tty rw,
  
  # Signal handling
  signal,
  
  # Mount operations (for services that need it)
  mount,
  umount,
  
  # File locking
  capability file_lock,
}
EOF

    log "Container AppArmor profile created"
}

# Reload AppArmor profiles
reload_apparmor() {
    log "Reloading AppArmor profiles..."
    
    if systemctl is-active --quiet apparmor; then
        systemctl reload apparmor || warn "Failed to reload AppArmor"
        log "AppArmor profiles reloaded"
    else
        warn "AppArmor service is not active"
    fi
}

# Check service status after AppArmor changes
check_services() {
    log "Checking service status after AppArmor changes..."
    
    local services=("smbd" "nmbd" "vsftpd" "ssh")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log "Service $service: RUNNING"
        else
            warn "Service $service: NOT RUNNING"
            # Try to start the service
            if systemctl start "$service" 2>/dev/null; then
                log "Service $service: STARTED"
            else
                warn "Service $service: FAILED TO START"
            fi
        fi
    done
}

# Create a script to completely disable AppArmor if needed
create_disable_apparmor_script() {
    log "Creating AppArmor disable script as fallback option..."
    
    cat > /opt/moxnas/disable_apparmor.sh << 'EOF'
#!/bin/bash
# Emergency script to completely disable AppArmor
# Use only if AppArmor continues to cause issues

echo "Stopping AppArmor service..."
systemctl stop apparmor

echo "Disabling AppArmor service..."
systemctl disable apparmor

echo "Removing AppArmor kernel parameter..."
if [ -f /etc/default/grub ]; then
    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="\(.*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 apparmor=0"/' /etc/default/grub
    update-grub
fi

echo "AppArmor has been disabled"
echo "Reboot the container for changes to take effect"
EOF

    chmod +x /opt/moxnas/disable_apparmor.sh
    log "AppArmor disable script created at /opt/moxnas/disable_apparmor.sh"
}

# Main function
main() {
    log "Starting AppArmor configuration for MoxNAS container..."
    
    check_root
    
    if check_apparmor; then
        disable_problematic_profiles
        create_apparmor_overrides
        configure_apparmor_for_container
        reload_apparmor
        sleep 2
        check_services
        create_disable_apparmor_script
        
        log "✅ AppArmor configuration completed"
        log ""
        log "If services still fail to start due to AppArmor:"
        log "1. Check logs: journalctl -u apparmor"
        log "2. Check denials: dmesg | grep DENIED"
        log "3. As last resort, run: /opt/moxnas/disable_apparmor.sh"
        log ""
    else
        log "AppArmor is not active, no configuration needed"
    fi
}

# Run main function
main "$@"