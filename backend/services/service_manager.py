#!/usr/bin/env python3
"""
MoxNAS Service Manager
Handles actual configuration and management of NAS services
"""

import os
import subprocess
import configparser
import logging
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
            # Ensure directory exists
            os.makedirs(path, exist_ok=True)
            
            # Read existing config
            config = configparser.ConfigParser()
            config.read(self.config_file)
            
            # Add new share section
            section_name = share_name
            if section_name not in config.sections():
                config.add_section(section_name)
            
            config.set(section_name, 'path', str(path))
            config.set(section_name, 'browseable', 'yes')
            config.set(section_name, 'writable', 'no' if read_only else 'yes')
            config.set(section_name, 'guest ok', 'yes' if guest_ok else 'no')
            config.set(section_name, 'create mask', '0664')
            config.set(section_name, 'directory mask', '0775')
            
            # Write config back
            with open(self.config_file, 'w') as f:
                config.write(f)
            
            # Restart samba
            self.service_manager.restart_service('smbd')
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
            # Ensure directory exists
            os.makedirs(path, exist_ok=True)
            
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
            
            options.extend(['no_subtree_check', 'no_root_squash'])
            options_str = ','.join(options)
            
            # Create export line
            export_line = f"{path} *(rw,{options_str})\n"
            
            # Read existing exports
            existing_exports = []
            if self.exports_file.exists():
                with open(self.exports_file, 'r') as f:
                    existing_exports = f.readlines()
            
            # Check if export already exists
            path_exists = any(line.startswith(str(path) + ' ') for line in existing_exports)
            
            if not path_exists:
                # Add new export
                with open(self.exports_file, 'a') as f:
                    f.write(export_line)
                
                # Reload exports
                subprocess.run(['exportfs', '-ra'], check=True)
                logger.info(f"NFS export created for {path}")
                return True
            
            return True  # Already exists
            
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