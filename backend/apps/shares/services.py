import os
import subprocess
import logging
from pathlib import Path
from jinja2 import Template
from typing import List, Dict, Any

from .models import SMBShare, NFSShare, FTPShare

logger = logging.getLogger(__name__)

class ShareService:
    """Service for managing share configurations"""

    def __init__(self):
        self.samba_config_path = '/etc/samba/smb.conf'
        self.nfs_exports_path = '/etc/exports'
        self.vsftpd_config_path = '/etc/vsftpd.conf'

    def update_samba_config(self) -> bool:
        """Update Samba configuration with current shares"""
        try:
            shares = SMBShare.objects.filter(enabled=True)
            
            # Generate configuration
            config = self._generate_samba_config(shares)
            
            # Backup current config
            if os.path.exists(self.samba_config_path):
                subprocess.run(['cp', self.samba_config_path, f'{self.samba_config_path}.backup'])
            
            # Write new config
            with open(self.samba_config_path, 'w') as f:
                f.write(config)
            
            # Test configuration
            result = subprocess.run(['testparm', '-s'], capture_output=True, text=True)
            if result.returncode != 0:
                # Restore backup
                if os.path.exists(f'{self.samba_config_path}.backup'):
                    subprocess.run(['mv', f'{self.samba_config_path}.backup', self.samba_config_path])
                raise Exception(f"Invalid Samba config: {result.stderr}")
            
            # Reload Samba
            self._reload_samba()
            
            logger.info("Updated Samba configuration successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update Samba config: {e}")
            return False

    def _generate_samba_config(self, shares) -> str:
        """Generate Samba configuration"""
        template_str = """
[global]
workgroup = WORKGROUP
server string = MoxNAS Server
netbios name = moxnas
security = user
map to guest = bad user
dns proxy = no
socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=65536 SO_SNDBUF=65536
local master = yes
os level = 20
domain master = yes
preferred master = yes
encrypt passwords = yes
passdb backend = tdbsam
obey pam restrictions = yes
unix password sync = yes
passwd program = /usr/bin/passwd %u
passwd chat = *Enter\\snew\\s*\\spassword:* %n\\n *Retype\\snew\\s*\\spassword:* %n\\n *password\\supdated\\ssuccessfully* .
pam password change = yes
load printers = no
printing = bsd
printcap name = /dev/null
disable spoolss = yes

{% for share in shares %}
[{{ share.name }}]
path = {{ share.path }}
{% if share.comment %}comment = {{ share.comment }}{% endif %}
browseable = {{ share.browseable|lower }}
writable = {{ not share.read_only|lower }}
guest ok = {{ share.guest_ok|lower }}
read only = {{ share.read_only|lower }}
create mask = {{ share.create_mask }}
directory mask = {{ share.directory_mask }}
{% if share.valid_users %}valid users = {{ share.valid_users }}{% endif %}
{% if share.write_list %}write list = {{ share.write_list }}{% endif %}
{% if share.force_user %}force user = {{ share.force_user }}{% endif %}
{% if share.force_group %}force group = {{ share.force_group }}{% endif %}
{% if share.inherit_acls %}inherit acls = yes{% endif %}
{% if share.inherit_permissions %}inherit permissions = yes{% endif %}

{% endfor %}
"""
        
        template = Template(template_str)
        return template.render(shares=shares)

    def _reload_samba(self):
        """Reload Samba configuration"""
        try:
            # Try reload first
            result = subprocess.run(['smbcontrol', 'all', 'reload-config'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                # If reload fails, restart services
                subprocess.run(['systemctl', 'restart', 'smbd', 'nmbd'], check=True)
        except Exception as e:
            logger.error(f"Failed to reload Samba: {e}")
            # Force restart as fallback
            subprocess.run(['systemctl', 'restart', 'smbd', 'nmbd'])

    def update_nfs_exports(self) -> bool:
        """Update NFS exports configuration"""
        try:
            shares = NFSShare.objects.filter(enabled=True)
            
            # Generate exports content
            exports_content = self._generate_nfs_exports(shares)
            
            # Backup current exports
            if os.path.exists(self.nfs_exports_path):
                subprocess.run(['cp', self.nfs_exports_path, f'{self.nfs_exports_path}.backup'])
            
            # Write new exports
            with open(self.nfs_exports_path, 'w') as f:
                f.write(exports_content)
            
            # Reload NFS exports
            subprocess.run(['exportfs', '-ra'], check=True)
            
            logger.info("Updated NFS exports successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update NFS exports: {e}")
            return False

    def _generate_nfs_exports(self, shares) -> str:
        """Generate NFS exports file content"""
        content = "# /etc/exports: NFS exports managed by MoxNAS\n\n"
        
        for share in shares:
            content += f"{share.get_export_line()}\n"
        
        return content

    def test_samba_connection(self) -> Dict[str, Any]:
        """Test Samba service status"""
        try:
            # Check if services are running
            smbd_status = subprocess.run(['systemctl', 'is-active', 'smbd'], 
                                       capture_output=True, text=True)
            nmbd_status = subprocess.run(['systemctl', 'is-active', 'nmbd'], 
                                       capture_output=True, text=True)
            
            # Test configuration
            testparm = subprocess.run(['testparm', '-s'], 
                                    capture_output=True, text=True)
            
            return {
                'smbd_running': smbd_status.stdout.strip() == 'active',
                'nmbd_running': nmbd_status.stdout.strip() == 'active',
                'config_valid': testparm.returncode == 0,
                'config_errors': testparm.stderr if testparm.returncode != 0 else None,
                'shares_count': SMBShare.objects.filter(enabled=True).count()
            }
            
        except Exception as e:
            logger.error(f"Error testing Samba connection: {e}")
            return {'error': str(e)}

    def get_share_usage(self, share_path: str) -> Dict[str, Any]:
        """Get usage statistics for a share"""
        try:
            import psutil
            usage = psutil.disk_usage(share_path)
            
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting share usage for {share_path}: {e}")
            return {'error': str(e)}