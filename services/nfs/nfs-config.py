#!/usr/bin/env python3
"""
NFS configuration management for MoxNAS
"""

import os
import subprocess
import tempfile
from pathlib import Path
from jinja2 import Template
import logging

logger = logging.getLogger(__name__)


class NFSConfig:
    """NFS configuration manager"""
    
    TEMPLATE_PATH = Path(__file__).parent / "exports.template"
    EXPORTS_PATH = Path("/etc/exports")
    BACKUP_PATH = Path("/etc/exports.bak")
    
    def __init__(self):
        self.template = self._load_template()
    
    def _load_template(self):
        """Load the NFS exports template"""
        try:
            with open(self.TEMPLATE_PATH, 'r') as f:
                return Template(f.read())
        except Exception as e:
            logger.error(f"Failed to load template: {e}")
            raise
    
    def generate_exports(self, exports_data):
        """Generate NFS exports from template"""
        try:
            return self.template.render(exports=exports_data)
        except Exception as e:
            logger.error(f"Failed to render template: {e}")
            raise
    
    def backup_current_exports(self):
        """Backup current NFS exports"""
        try:
            if self.EXPORTS_PATH.exists():
                subprocess.run(['cp', str(self.EXPORTS_PATH), str(self.BACKUP_PATH)], check=True)
                logger.info(f"Backed up exports to {self.BACKUP_PATH}")
        except Exception as e:
            logger.error(f"Failed to backup exports: {e}")
            raise
    
    def write_exports(self, exports_content):
        """Write new NFS exports configuration"""
        try:
            # Backup current exports
            self.backup_current_exports()
            
            # Write new exports
            with open(self.EXPORTS_PATH, 'w') as f:
                f.write(exports_content)
            
            # Set proper permissions
            os.chmod(self.EXPORTS_PATH, 0o644)
            logger.info(f"Written new exports to {self.EXPORTS_PATH}")
            
        except Exception as e:
            logger.error(f"Failed to write exports: {e}")
            raise
    
    def test_exports(self):
        """Test NFS exports configuration"""
        try:
            result = subprocess.run(['exportfs', '-r'], 
                                  capture_output=True, text=True, check=True)
            logger.info("NFS exports test passed")
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"NFS exports test failed: {e.stderr}")
            return False, e.stderr
    
    def reload_exports(self):
        """Reload NFS exports"""
        try:
            subprocess.run(['exportfs', '-ra'], check=True)
            logger.info("NFS exports reloaded")
        except Exception as e:
            logger.error(f"Failed to reload NFS exports: {e}")
            raise
    
    def show_exports(self):
        """Show current NFS exports"""
        try:
            result = subprocess.run(['exportfs', '-v'], 
                                  capture_output=True, text=True, check=True)
            return result.stdout
        except Exception as e:
            logger.error(f"Failed to show exports: {e}")
            return ""
    
    def add_export(self, export_config):
        """Add a new NFS export"""
        # This would typically update the database and regenerate exports
        pass
    
    def remove_export(self, export_path):
        """Remove an NFS export"""
        # This would typically update the database and regenerate exports
        pass
    
    def start_nfs_service(self):
        """Start NFS services"""
        try:
            services = ['rpcbind', 'nfs-kernel-server']
            for service in services:
                subprocess.run(['systemctl', 'start', service], check=True)
                subprocess.run(['systemctl', 'enable', service], check=True)
            logger.info("NFS services started and enabled")
        except Exception as e:
            logger.error(f"Failed to start NFS services: {e}")
            raise
    
    def stop_nfs_service(self):
        """Stop NFS services"""
        try:
            services = ['nfs-kernel-server', 'rpcbind']
            for service in services:
                subprocess.run(['systemctl', 'stop', service], check=True)
            logger.info("NFS services stopped")
        except Exception as e:
            logger.error(f"Failed to stop NFS services: {e}")
            raise
    
    def restart_nfs_service(self):
        """Restart NFS services"""
        try:
            subprocess.run(['systemctl', 'restart', 'nfs-kernel-server'], check=True)
            logger.info("NFS services restarted")
        except Exception as e:
            logger.error(f"Failed to restart NFS services: {e}")
            raise
    
    def get_nfs_status(self):
        """Get NFS service status"""
        try:
            result = subprocess.run(['systemctl', 'is-active', 'nfs-kernel-server'], 
                                  capture_output=True, text=True)
            return result.stdout.strip() == 'active'
        except Exception as e:
            logger.error(f"Failed to get NFS status: {e}")
            return False


def main():
    """Example usage"""
    config = NFSConfig()
    
    # Example exports data
    exports_data = [
        {
            'name': 'data',
            'path': '/tank/data',
            'comment': 'Data storage export',
            'clients': [
                {
                    'network': '192.168.1.0/24',
                    'options': ['rw', 'sync', 'no_subtree_check']
                },
                {
                    'network': '10.0.0.0/8',
                    'options': ['ro', 'sync', 'no_subtree_check']
                }
            ]
        },
        {
            'name': 'backup',
            'path': '/tank/backup',
            'comment': 'Backup storage export',
            'clients': [
                {
                    'network': '192.168.1.100',
                    'options': ['rw', 'sync', 'no_subtree_check', 'no_root_squash']
                }
            ]
        },
        {
            'name': 'public',
            'path': '/tank/public',
            'comment': 'Public read-only export',
            'clients': [
                {
                    'network': '*',
                    'options': ['ro', 'sync', 'no_subtree_check', 'all_squash', 'anonuid=65534', 'anongid=65534']
                }
            ]
        }
    ]
    
    # Generate and display exports
    exports_content = config.generate_exports(exports_data)
    print(exports_content)
    
    # Test and apply configuration
    # config.write_exports(exports_content)
    # valid, output = config.test_exports()
    # if valid:
    #     config.reload_exports()


if __name__ == '__main__':
    main()