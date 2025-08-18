import subprocess
import psutil
import time
import logging
from pathlib import Path
from django.core.exceptions import ValidationError
from .templates import template_engine

logger = logging.getLogger(__name__)

class ServiceManager:
    """Base class for service management"""
    
    def __init__(self, service_name):
        self.service_name = service_name
    
    def start(self):
        """Start the service"""
        return self._systemctl('start')
    
    def stop(self):
        """Stop the service"""
        return self._systemctl('stop')
    
    def restart(self):
        """Restart the service"""
        return self._systemctl('restart')
    
    def reload(self):
        """Reload the service configuration"""
        return self._systemctl('reload')
    
    def enable(self):
        """Enable service to start on boot"""
        return self._systemctl('enable')
    
    def disable(self):
        """Disable service from starting on boot"""
        return self._systemctl('disable')
    
    def status(self):
        """Get service status"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', self.service_name],
                capture_output=True, text=True, timeout=10
            )
            active = result.stdout.strip() == 'active'
            
            result = subprocess.run(
                ['systemctl', 'is-enabled', self.service_name],
                capture_output=True, text=True, timeout=10
            )
            enabled = result.stdout.strip() == 'enabled'
            
            return {
                'active': active,
                'enabled': enabled,
                'status': 'running' if active else 'stopped'
            }
        except Exception as e:
            logger.error(f"Failed to get status for {self.service_name}: {e}")
            return {'active': False, 'enabled': False, 'status': 'unknown'}
    
    def _systemctl(self, action):
        """Execute systemctl command"""
        try:
            result = subprocess.run(
                ['systemctl', action, self.service_name],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully {action}ed {self.service_name}")
                return True
            else:
                logger.error(f"Failed to {action} {self.service_name}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout while trying to {action} {self.service_name}")
            return False
        except Exception as e:
            logger.error(f"Error executing {action} on {self.service_name}: {e}")
            return False

class SambaManager(ServiceManager):
    """Samba service management"""
    
    def __init__(self):
        super().__init__('smbd')
        self.config_path = '/etc/samba/smb.conf'
    
    def generate_config(self, shares_queryset, global_settings=None):
        """Generate Samba configuration from Django models"""
        from ..shares.models import SMBShare
        
        # Prepare context
        context = {
            'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'shares': [],
            'workgroup': global_settings.get('workgroup', 'WORKGROUP') if global_settings else 'WORKGROUP',
            'server_string': global_settings.get('server_string', 'MoxNAS Server') if global_settings else 'MoxNAS Server',
            'netbios_name': global_settings.get('netbios_name', 'MOXNAS') if global_settings else 'MOXNAS',
        }
        
        # Process shares
        for share in shares_queryset:
            # Validate share path
            template_engine.validate_path(share.path, must_exist=True)
            
            # Get valid users
            valid_users = []
            for user in share.allowed_users.all():
                valid_users.append(user.username)
            for group in share.allowed_groups.all():
                valid_users.append(f"@{group.name}")
            
            share_config = {
                'name': share.name,
                'path': share.path,
                'comment': share.comment,
                'read_only': not share.writable,
                'browseable': share.browseable,
                'guest_ok': share.guest_access,
                'valid_users': valid_users,
                'create_mask': share.create_mask,
                'directory_mask': share.directory_mask,
                'hide_dot_files': share.hide_dot_files,
                'inherit_permissions': share.inherit_permissions,
                'recycle_bin': share.recycle_bin,
                'audit': share.audit_enabled,
            }
            context['shares'].append(share_config)
        
        # Generate configuration
        config_content = template_engine.render_template('samba/smb.conf.j2', context)
        
        # Write configuration
        template_engine.write_config(self.config_path, config_content)
        
        return config_content
    
    def test_config(self):
        """Test Samba configuration syntax"""
        try:
            result = subprocess.run(
                ['testparm', '-s', self.config_path],
                capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)
    
    def reload_config(self):
        """Reload Samba configuration"""
        valid, message = self.test_config()
        if not valid:
            raise ValidationError(f"Invalid Samba configuration: {message}")
        
        return self.reload()
    
    def add_user(self, username, password):
        """Add user to Samba"""
        try:
            # Add to smbpasswd
            proc = subprocess.Popen(
                ['smbpasswd', '-a', username],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = proc.communicate(input=f"{password}\n{password}\n")
            
            if proc.returncode == 0:
                logger.info(f"Successfully added Samba user: {username}")
                return True
            else:
                logger.error(f"Failed to add Samba user {username}: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding Samba user {username}: {e}")
            return False

class NFSManager(ServiceManager):
    """NFS service management"""
    
    def __init__(self):
        super().__init__('nfs-kernel-server')
        self.exports_path = '/etc/exports'
    
    def generate_exports(self, exports_queryset):
        """Generate NFS exports configuration"""
        from ..shares.models import NFSShare
        
        context = {
            'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'exports': []
        }
        
        for export in exports_queryset:
            # Validate export path
            template_engine.validate_path(export.path, must_exist=True)
            
            # Build options list
            options = []
            if export.read_only:
                options.append('ro')
            else:
                options.append('rw')
            
            if export.sync:
                options.append('sync')
            else:
                options.append('async')
            
            if export.root_squash:
                options.append('root_squash')
            else:
                options.append('no_root_squash')
            
            # Add custom options
            if export.options:
                options.extend(export.options.split(','))
            
            export_config = {
                'path': export.path,
                'network': export.network or '*',
                'options': options,
                'comment': export.comment
            }
            context['exports'].append(export_config)
        
        # Generate exports file
        exports_content = template_engine.render_template('nfs/exports.j2', context)
        
        # Write exports file
        template_engine.write_config(self.exports_path, exports_content)
        
        return exports_content
    
    def reload_exports(self):
        """Reload NFS exports"""
        try:
            result = subprocess.run(
                ['exportfs', '-ra'],
                capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to reload NFS exports: {e}")
            return False

class FTPManager(ServiceManager):
    """FTP service management"""
    
    def __init__(self):
        super().__init__('vsftpd')
        self.config_path = '/etc/vsftpd.conf'
    
    def generate_config(self, global_settings=None):
        """Generate vsftpd configuration"""
        
        context = {
            'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'anonymous_enable': global_settings.get('anonymous_enable', False) if global_settings else False,
            'write_enable': global_settings.get('write_enable', True) if global_settings else True,
            'local_umask': global_settings.get('local_umask', '022') if global_settings else '022',
            'chroot_local_user': global_settings.get('chroot_local_user', True) if global_settings else True,
            'ssl_enable': global_settings.get('ssl_enable', False) if global_settings else False,
            'pasv_min_port': global_settings.get('pasv_min_port', 20000) if global_settings else 20000,
            'pasv_max_port': global_settings.get('pasv_max_port', 20100) if global_settings else 20100,
            'custom_options': global_settings.get('custom_options', {}) if global_settings else {}
        }
        
        # Generate configuration
        config_content = template_engine.render_template('ftp/vsftpd.conf.j2', context)
        
        # Write configuration
        template_engine.write_config(self.config_path, config_content)
        
        return config_content

# Service manager instances
samba_manager = SambaManager()
nfs_manager = NFSManager()
ftp_manager = FTPManager()