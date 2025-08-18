#!/usr/bin/env python3
"""
Samba configuration management for MoxNAS
"""

import os
import subprocess
import tempfile
from pathlib import Path
from jinja2 import Template
import logging

logger = logging.getLogger(__name__)


class SambaConfig:
    """Samba configuration manager"""
    
    TEMPLATE_PATH = Path(__file__).parent / "smb.conf.template"
    CONFIG_PATH = Path("/etc/samba/smb.conf")
    BACKUP_PATH = Path("/etc/samba/smb.conf.bak")
    
    def __init__(self):
        self.template = self._load_template()
    
    def _load_template(self):
        """Load the Samba configuration template"""
        try:
            with open(self.TEMPLATE_PATH, 'r') as f:
                return Template(f.read())
        except Exception as e:
            logger.error(f"Failed to load template: {e}")
            raise
    
    def generate_config(self, config_data):
        """Generate Samba configuration from template"""
        try:
            return self.template.render(**config_data)
        except Exception as e:
            logger.error(f"Failed to render template: {e}")
            raise
    
    def backup_current_config(self):
        """Backup current Samba configuration"""
        try:
            if self.CONFIG_PATH.exists():
                subprocess.run(['cp', str(self.CONFIG_PATH), str(self.BACKUP_PATH)], check=True)
                logger.info(f"Backed up config to {self.BACKUP_PATH}")
        except Exception as e:
            logger.error(f"Failed to backup config: {e}")
            raise
    
    def write_config(self, config_content):
        """Write new Samba configuration"""
        try:
            # Backup current config
            self.backup_current_config()
            
            # Write new config
            with open(self.CONFIG_PATH, 'w') as f:
                f.write(config_content)
            
            # Set proper permissions
            os.chmod(self.CONFIG_PATH, 0o644)
            logger.info(f"Written new config to {self.CONFIG_PATH}")
            
        except Exception as e:
            logger.error(f"Failed to write config: {e}")
            raise
    
    def test_config(self):
        """Test Samba configuration syntax"""
        try:
            result = subprocess.run(['testparm', '-s'], 
                                  capture_output=True, text=True, check=True)
            logger.info("Samba configuration test passed")
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Samba configuration test failed: {e.stderr}")
            return False, e.stderr
    
    def reload_config(self):
        """Reload Samba configuration"""
        try:
            subprocess.run(['systemctl', 'reload', 'smbd'], check=True)
            subprocess.run(['systemctl', 'reload', 'nmbd'], check=True)
            logger.info("Samba configuration reloaded")
        except Exception as e:
            logger.error(f"Failed to reload Samba: {e}")
            raise
    
    def add_share(self, share_config):
        """Add a new share to Samba configuration"""
        # This would typically update the database and regenerate config
        pass
    
    def remove_share(self, share_name):
        """Remove a share from Samba configuration"""
        # This would typically update the database and regenerate config
        pass
    
    def add_user(self, username, password):
        """Add Samba user"""
        try:
            # Add system user if not exists
            subprocess.run(['useradd', '-s', '/bin/false', username], 
                         check=False)  # Don't fail if user exists
            
            # Add Samba user
            proc = subprocess.Popen(['smbpasswd', '-a', username], 
                                  stdin=subprocess.PIPE, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  text=True)
            stdout, stderr = proc.communicate(input=f"{password}\n{password}\n")
            
            if proc.returncode == 0:
                logger.info(f"Added Samba user: {username}")
                return True
            else:
                logger.error(f"Failed to add Samba user: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding Samba user: {e}")
            return False
    
    def remove_user(self, username):
        """Remove Samba user"""
        try:
            subprocess.run(['smbpasswd', '-x', username], check=True)
            logger.info(f"Removed Samba user: {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove Samba user: {e}")
            return False
    
    def enable_user(self, username):
        """Enable Samba user"""
        try:
            subprocess.run(['smbpasswd', '-e', username], check=True)
            logger.info(f"Enabled Samba user: {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to enable Samba user: {e}")
            return False
    
    def disable_user(self, username):
        """Disable Samba user"""
        try:
            subprocess.run(['smbpasswd', '-d', username], check=True)
            logger.info(f"Disabled Samba user: {username}")
            return True
        except Exception as e:
            logger.error(f"Failed to disable Samba user: {e}")
            return False


def main():
    """Example usage"""
    config = SambaConfig()
    
    # Example configuration data
    config_data = {
        'workgroup': 'MOXNAS',
        'server_string': 'MoxNAS File Server',
        'netbios_name': 'MOXNAS-01',
        'shares': [
            {
                'name': 'documents',
                'path': '/tank/documents',
                'comment': 'Document Storage',
                'writable': 'yes',
                'guest_ok': 'no',
                'valid_users': '@users'
            },
            {
                'name': 'public',
                'path': '/tank/public',
                'comment': 'Public Storage',
                'writable': 'yes',
                'guest_ok': 'yes'
            }
        ]
    }
    
    # Generate and write configuration
    config_content = config.generate_config(config_data)
    print(config_content)
    
    # Test configuration
    # valid, output = config.test_config()
    # if valid:
    #     config.write_config(config_content)
    #     config.reload_config()


if __name__ == '__main__':
    main()