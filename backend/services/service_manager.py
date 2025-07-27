#!/usr/bin/env python3
"""
MoxNAS Service Manager
Handles actual configuration and management of NAS services
"""

import os
import subprocess
import configparser
import logging
import shutil
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

class ServiceManager:
    """Manages actual NAS services configuration"""
    
    def __init__(self):
        self.config_path = Path(getattr(settings, 'MOXNAS_CONFIG_PATH', '/etc/moxnas'))
        self.storage_path = Path(getattr(settings, 'MOXNAS_STORAGE_PATH', '/mnt/storage'))
        
    def is_service_running(self, service_name):
        """Check if a service is running"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and result.stdout.strip() == 'active'
        except Exception as e:
            logger.error(f"Error checking service {service_name}: {e}")
            return False
    
    def start_service(self, service_name):
        """Start a service"""
        try:
            result = subprocess.run(
                ['systemctl', 'start', service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Service {service_name} started successfully")
                return True
            else:
                logger.error(f"Failed to start {service_name}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error starting service {service_name}: {e}")
            return False
    
    def stop_service(self, service_name):
        """Stop a service"""
        try:
            result = subprocess.run(
                ['systemctl', 'stop', service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Service {service_name} stopped successfully")
                return True
            else:
                logger.error(f"Failed to stop {service_name}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error stopping service {service_name}: {e}")
            return False
    
    def restart_service(self, service_name):
        """Restart a service"""
        try:
            result = subprocess.run(
                ['systemctl', 'restart', service_name],
                capture_output=True,
                text=True,
                timeout=15
            )
            if result.returncode == 0:
                logger.info(f"Service {service_name} restarted successfully")
                return True
            else:
                logger.error(f"Failed to restart {service_name}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error restarting service {service_name}: {e}")
            return False

class SambaManager:
    """Manages Samba/SMB configuration"""
    
    def __init__(self):
        self.config_file = Path('/etc/samba/smb.conf')
        self.service_manager = ServiceManager()
    
    def create_share(self, share_name, path, read_only=False, guest_ok=False, **kwargs):
        """Create a new SMB share"""
        try:
            # Validate and normalize path
            if not path or not isinstance(path, str):
                raise ValueError("Path cannot be empty")
            
            path = os.path.abspath(path.strip())
            
            # Security check - ensure path is within allowed directories
            allowed_bases = ['/mnt/storage', '/opt/moxnas/storage', '/home', '/tmp/moxnas']
            if not any(path.startswith(base) for base in allowed_bases):
                logger.warning(f"Path {path} not in allowed directories, using /mnt/storage")
                path = '/mnt/storage'
            
            # Ensure directory exists with proper permissions
            try:
                os.makedirs(path, exist_ok=True)
                os.chmod(path, 0o755)
            except OSError as e:
                logger.error(f"Failed to create directory {path}: {e}")
                # Try to create in default storage location
                fallback_path = f"/mnt/storage/{share_name}"
                os.makedirs(fallback_path, exist_ok=True)
                os.chmod(fallback_path, 0o755)
                path = fallback_path
                logger.info(f"Using fallback path: {path}")
            
            # Backup existing config
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix('.conf.backup')
                if not backup_file.exists():
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
            
            # Read existing config with proper handling
            config = configparser.ConfigParser(allow_no_value=True)
            config.optionxform = str  # Preserve case
            if self.config_file.exists():
                config.read(self.config_file)
            
            # Add new share section
            section_name = share_name
            if section_name not in config.sections():
                config.add_section(section_name)
            
            config.set(section_name, 'path', str(path))
            config.set(section_name, 'browseable', 'yes')
            config.set(section_name, 'writable', 'no' if read_only else 'yes')
            config.set(section_name, 'guest ok', 'yes' if guest_ok else 'no')
            config.set(section_name, 'read only', 'yes' if read_only else 'no')
            config.set(section_name, 'create mask', '0664')
            config.set(section_name, 'directory mask', '0775')
            config.set(section_name, 'force create mode', '0664')
            config.set(section_name, 'force directory mode', '0775')
            
            # Write config back with proper formatting
            with open(self.config_file, 'w') as f:
                config.write(f)
            
            # Test samba configuration before restarting
            result = subprocess.run(['testparm', '-s'], capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning(f"Samba config test failed: {result.stderr}")
            
            # Restart samba services
            self.service_manager.restart_service('smbd')
            self.service_manager.restart_service('nmbd')
            
            logger.info(f"SMB share '{share_name}' created at {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create SMB share {share_name}: {e}")
            return False
    
    def remove_share(self, share_name):
        """Remove an SMB share"""
        try:
            config = configparser.ConfigParser()
            config.read(self.config_file)
            
            if share_name in config.sections():
                config.remove_section(share_name)
                
                with open(self.config_file, 'w') as f:
                    config.write(f)
                
                self.service_manager.restart_service('smbd')
                logger.info(f"SMB share '{share_name}' removed")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove SMB share {share_name}: {e}")
            return False

class NFSManager:
    """Manages NFS exports"""
    
    def __init__(self):
        self.exports_file = Path('/etc/exports')
        self.service_manager = ServiceManager()
    
    def create_export(self, path, read_only=False, sync=True, **kwargs):
        """Create a new NFS export"""
        try:
            # Validate and normalize path
            if not path or not isinstance(path, str):
                raise ValueError("Path cannot be empty")
            
            path = os.path.abspath(path.strip())
            
            # Security check - ensure path is within allowed directories
            allowed_bases = ['/mnt/storage', '/opt/moxnas/storage', '/home', '/tmp/moxnas']
            if not any(path.startswith(base) for base in allowed_bases):
                logger.warning(f"Path {path} not in allowed directories, using /mnt/storage")
                path = '/mnt/storage'
            
            # Ensure directory exists with proper permissions
            try:
                os.makedirs(path, exist_ok=True)
                os.chmod(path, 0o755)
            except OSError as e:
                logger.error(f"Failed to create directory {path}: {e}")
                # Try to create in default storage location
                fallback_path = "/mnt/storage"
                if not os.path.exists(fallback_path):
                    os.makedirs(fallback_path, exist_ok=True)
                    os.chmod(fallback_path, 0o755)
                path = fallback_path
                logger.info(f"Using fallback path: {path}")
            
            # Build export options
            options = []
            if read_only:
                options.append('ro')
            else:
                options.append('rw')
            
            if sync:
                options.append('sync')
            else:
                options.append('async')
            
            options.extend(['no_subtree_check', 'no_root_squash', 'insecure'])
            options_str = ','.join(options)
            
            # Create export line with proper formatting
            export_line = f"{path} *({options_str})\n"
            
            # Backup existing exports
            if self.exports_file.exists():
                backup_file = self.exports_file.with_suffix('.backup')
                if not backup_file.exists():
                    import shutil
                    shutil.copy2(self.exports_file, backup_file)
            
            # Read existing exports
            existing_exports = []
            if self.exports_file.exists():
                with open(self.exports_file, 'r') as f:
                    existing_exports = f.readlines()
            
            # Check if export already exists and remove old entry
            filtered_exports = [line for line in existing_exports 
                              if not line.strip().startswith(str(path) + ' ')]
            
            # Add new export
            filtered_exports.append(export_line)
            
            # Write all exports back
            with open(self.exports_file, 'w') as f:
                f.writelines(filtered_exports)
            
            # Ensure proper ownership and permissions
            os.chown(self.exports_file, 0, 0)  # root:root
            os.chmod(self.exports_file, 0o644)
            
            # Reload exports with error handling
            try:
                subprocess.run(['exportfs', '-ra'], check=True, timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("NFS export reload timed out")
            except subprocess.CalledProcessError as e:
                logger.warning(f"NFS export reload failed: {e}")
            
            # Restart NFS service to ensure changes take effect
            self.service_manager.restart_service('nfs-kernel-server')
            
            logger.info(f"NFS export created for {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create NFS export for {path}: {e}")
            return False
    
    def remove_export(self, path):
        """Remove an NFS export"""
        try:
            if not self.exports_file.exists():
                return True
            
            # Read and filter exports
            with open(self.exports_file, 'r') as f:
                lines = f.readlines()
            
            # Remove lines starting with the path
            filtered_lines = [line for line in lines if not line.startswith(str(path) + ' ')]
            
            # Write back
            with open(self.exports_file, 'w') as f:
                f.writelines(filtered_lines)
            
            # Reload exports
            subprocess.run(['exportfs', '-ra'], check=True)
            logger.info(f"NFS export removed for {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove NFS export for {path}: {e}")
            return False

class SystemInfoManager:
    """Manages system information collection"""
    
    def get_system_stats(self):
        """Get current system statistics"""
        import psutil
        
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = {
                'total': memory.total,
                'used': memory.used,
                'free': memory.available,
                'percent': memory.percent
            }
            
            # Disk usage for main storage
            storage_path = getattr(settings, 'MOXNAS_STORAGE_PATH', '/mnt/storage')
            if os.path.exists(storage_path):
                disk = psutil.disk_usage(storage_path)
                disk_usage = {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'percent': (disk.used / disk.total) * 100
                }
            else:
                disk_usage = {'total': 0, 'used': 0, 'free': 0, 'percent': 0}
            
            # Network interfaces
            network_interfaces = []
            for interface, addrs in psutil.net_if_addrs().items():
                if interface.startswith(('lo', 'docker', 'br-')):
                    continue
                
                addresses = []
                for addr in addrs:
                    if addr.family == 2:  # AF_INET (IPv4)
                        addresses.append({
                            'ip': addr.address,
                            'netmask': addr.netmask
                        })
                
                if addresses:
                    network_interfaces.append({
                        'name': interface,
                        'addresses': addresses
                    })
            
            # System uptime
            boot_time = psutil.boot_time()
            import time
            uptime = int(time.time() - boot_time)
            
            return {
                'hostname': os.uname().nodename,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'network_interfaces': network_interfaces,
                'uptime': uptime
            }
            
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {}


class FTPManager:
    """Manages FTP/VSFTPD configuration and shares"""
    
    def __init__(self):
        self.config_file = Path('/etc/vsftpd.conf')
        self.service_manager = ServiceManager()
    
    def configure_ftp(self, anonymous_enable=True, local_enable=True, write_enable=True, **kwargs):
        """Configure FTP server settings"""
        try:
            # Ensure FTP root directory exists with fallback
            ftp_root = kwargs.get('ftp_root', '/mnt/storage')
            
            try:
                os.makedirs(ftp_root, exist_ok=True)
                os.chmod(ftp_root, 0o755)
            except OSError as e:
                logger.warning(f"Failed to create FTP root {ftp_root}: {e}")
                # Fallback to default storage
                ftp_root = '/mnt/storage'
                os.makedirs(ftp_root, exist_ok=True)
                os.chmod(ftp_root, 0o755)
            
            # Backup original config if it exists
            if self.config_file.exists():
                backup_file = self.config_file.with_suffix('.conf.backup')
                if not backup_file.exists():
                    shutil.copy2(self.config_file, backup_file)
            
            # Read existing configuration
            config_lines = []
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config_lines = f.readlines()
            
            # Configuration settings to apply
            config_settings = {
                'anonymous_enable': 'YES' if anonymous_enable else 'NO',
                'local_enable': 'YES' if local_enable else 'NO',
                'write_enable': 'YES' if write_enable else 'NO',
                'anon_upload_enable': 'YES' if anonymous_enable and write_enable else 'NO',
                'anon_mkdir_write_enable': 'YES' if anonymous_enable and write_enable else 'NO',
                'anon_root': ftp_root,
                'anon_other_write_enable': 'YES' if anonymous_enable and write_enable else 'NO',
                'pasv_enable': 'YES',
                'pasv_min_port': '40000',
                'pasv_max_port': '50000',
                'seccomp_sandbox': 'NO',  # Required for LXC containers
                'allow_writeable_chroot': 'YES',
                'listen': 'YES',
                'listen_ipv6': 'NO',
                'dirmessage_enable': 'YES',
                'use_localtime': 'YES',
                'xferlog_enable': 'YES',
                'connect_from_port_20': 'YES',
                'chroot_local_user': 'NO',  # Don't chroot to avoid path issues
                'secure_chroot_dir': '/var/run/vsftpd/empty'
            }
            
            # Add additional kwargs to config
            config_settings.update(kwargs)
            
            # Update configuration
            updated_lines = []
            settings_added = set()
            
            for line in config_lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    updated_lines.append(line)
                    continue
                
                if '=' in line:
                    key = line.split('=')[0].strip()
                    if key in config_settings:
                        updated_lines.append(f"{key}={config_settings[key]}")
                        settings_added.add(key)
                    else:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)
            
            # Add any new settings
            for key, value in config_settings.items():
                if key not in settings_added:
                    updated_lines.append(f"{key}={value}")
            
            # Write updated configuration
            with open(self.config_file, 'w') as f:
                for line in updated_lines:
                    f.write(line + '\n')
            
            # Ensure vsftpd secure directory exists
            secure_dir = '/var/run/vsftpd/empty'
            os.makedirs(secure_dir, exist_ok=True)
            os.chmod(secure_dir, 0o755)
            
            logger.info("FTP configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure FTP: {e}")
            return False
    
    def create_ftp_user(self, username, password, home_dir=None):
        """Create FTP user with home directory"""
        try:
            if home_dir is None:
                home_dir = f"/mnt/storage/ftp_users/{username}"
            
            # Create home directory
            os.makedirs(home_dir, exist_ok=True)
            
            # Create user account
            result = subprocess.run([
                'useradd', '-d', home_dir, '-s', '/bin/bash', username
            ], capture_output=True, text=True)
            
            if result.returncode != 0 and 'already exists' not in result.stderr:
                logger.error(f"Failed to create user {username}: {result.stderr}")
                return False
            
            # Set password
            result = subprocess.run([
                'chpasswd'
            ], input=f"{username}:{password}\n", text=True, capture_output=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to set password for {username}: {result.stderr}")
                return False
            
            # Set proper ownership and permissions
            subprocess.run(['chown', '-R', f"{username}:{username}", home_dir])
            subprocess.run(['chmod', '755', home_dir])
            
            logger.info(f"FTP user {username} created with home directory {home_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create FTP user {username}: {e}")
            return False
    
    def delete_ftp_user(self, username):
        """Delete FTP user and home directory"""
        try:
            # Remove user
            result = subprocess.run([
                'userdel', '-r', username
            ], capture_output=True, text=True)
            
            if result.returncode != 0 and 'does not exist' not in result.stderr:
                logger.error(f"Failed to delete user {username}: {result.stderr}")
                return False
            
            logger.info(f"FTP user {username} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete FTP user {username}: {e}")
            return False
    
    def set_ftp_permissions(self, path, read_only=False):
        """Set FTP permissions for a directory"""
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            
            if read_only:
                # Set read-only permissions
                subprocess.run(['chmod', '555', path])
            else:
                # Set read-write permissions
                subprocess.run(['chmod', '755', path])
            
            logger.info(f"FTP permissions set for {path} (read_only: {read_only})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set FTP permissions for {path}: {e}")
            return False
    
    def get_ftp_status(self):
        """Get FTP service status and configuration"""
        try:
            # Check service status
            service_status = 'running' if self.service_manager.is_service_running('vsftpd') else 'stopped'
            
            # Read configuration
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
            
            return {
                'service_status': service_status,
                'configuration': config,
                'config_file': str(self.config_file)
            }
            
        except Exception as e:
            logger.error(f"Failed to get FTP status: {e}")
            return {'error': str(e)}
    
    def restart_ftp_service(self):
        """Restart FTP service"""
        try:
            return self.service_manager.restart_service('vsftpd')
        except Exception as e:
            logger.error(f"Failed to restart FTP service: {e}")
            return False