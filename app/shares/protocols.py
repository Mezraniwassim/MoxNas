"""Network share protocol handlers"""
import os
import subprocess
import tempfile
from typing import Tuple, Dict, List
from app.models import Share, ShareProtocol, ShareStatus, SystemLog, LogLevel

class ShareProtocolManager:
    """Manage network sharing protocols"""
    
    def __init__(self):
        self.smb_config_path = '/etc/samba/smb.conf'
        self.nfs_exports_path = '/etc/exports'
        self.vsftpd_config_path = '/etc/vsftpd.conf'
    
    def run_command(self, command: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """Execute system command safely"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, '', f'Command timed out after {timeout} seconds'
        except Exception as e:
            return False, '', str(e)

class SMBManager(ShareProtocolManager):
    """SMB/CIFS share management"""
    
    def create_smb_share(self, share: Share) -> Tuple[bool, str]:
        """Create SMB share configuration"""
        try:
            # Generate SMB share configuration
            share_config = f"""
[{share.name}]
    path = {share.dataset.path}
    valid users = {share.owner.username}
    read only = {'yes' if share.read_only else 'no'}
    browseable = yes
    writable = {'no' if share.read_only else 'yes'}
    guest ok = {'yes' if share.guest_access else 'no'}
    create mask = 0755
    directory mask = 0755
"""
            
            # Read current SMB configuration
            smb_content = ''
            if os.path.exists(self.smb_config_path):
                with open(self.smb_config_path, 'r') as f:
                    smb_content = f.read()
            
            # Check if share already exists
            if f'[{share.name}]' in smb_content:
                return False, f'SMB share {share.name} already exists'
            
            # Append new share configuration
            with open(self.smb_config_path, 'a') as f:
                f.write(share_config)
            
            # Test SMB configuration
            success, stdout, stderr = self.run_command(['testparm', '-s'])
            if not success:
                return False, f'SMB configuration test failed: {stderr}'
            
            # Reload SMB service
            success, stdout, stderr = self.run_command(['systemctl', 'reload', 'smbd'])
            if not success:
                return False, f'Failed to reload SMB service: {stderr}'
            
            return True, f'SMB share {share.name} created successfully'
            
        except Exception as e:
            return False, f'Error creating SMB share: {str(e)}'
    
    def delete_smb_share(self, share: Share) -> Tuple[bool, str]:
        """Delete SMB share configuration"""
        try:
            if not os.path.exists(self.smb_config_path):
                return True, 'SMB configuration file not found'
            
            # Read current configuration
            with open(self.smb_config_path, 'r') as f:
                lines = f.readlines()
            
            # Remove share section
            new_lines = []
            in_share_section = False
            share_section_name = f'[{share.name}]'
            
            for line in lines:
                line_stripped = line.strip()
                
                if line_stripped == share_section_name:
                    in_share_section = True
                    continue
                
                if in_share_section and line_stripped.startswith('[') and line_stripped.endswith(']'):
                    in_share_section = False
                
                if not in_share_section:
                    new_lines.append(line)
            
            # Write updated configuration
            with open(self.smb_config_path, 'w') as f:
                f.writelines(new_lines)
            
            # Reload SMB service
            success, stdout, stderr = self.run_command(['systemctl', 'reload', 'smbd'])
            if not success:
                return False, f'Failed to reload SMB service: {stderr}'
            
            return True, f'SMB share {share.name} deleted successfully'
            
        except Exception as e:
            return False, f'Error deleting SMB share: {str(e)}'
    
    def get_smb_connections(self) -> List[Dict]:
        """Get active SMB connections"""
        connections = []
        
        try:
            success, stdout, stderr = self.run_command(['smbstatus', '-p'])
            if success:
                lines = stdout.split('\\n')
                for line in lines:
                    if 'DENY_NONE' in line or 'RDONLY' in line or 'WRONLY' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            connections.append({
                                'pid': parts[0],
                                'username': parts[1],
                                'group': parts[2],
                                'machine': parts[3],
                                'protocol': parts[4]
                            })
        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='shares',
                message=f'Failed to get SMB connections: {str(e)}'
            )
        
        return connections
    
    def get_active_connections(self) -> List[Dict]:
        """Alias for get_smb_connections for compatibility"""
        return self.get_smb_connections()
    
    def restart_service(self) -> bool:
        """Restart SMB service"""
        try:
            success, stdout, stderr = self.run_command(['systemctl', 'restart', 'smbd'])
            if success:
                success, stdout, stderr = self.run_command(['systemctl', 'restart', 'nmbd'])
            return success
        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category='shares',
                message=f'Failed to restart SMB service: {str(e)}'
            )
            return False

class NFSManager(ShareProtocolManager):
    """NFS share management"""
    
    def create_nfs_share(self, share: Share) -> Tuple[bool, str]:
        """Create NFS export"""
        try:
            # Build export options
            options = []
            if share.read_only:
                options.append('ro')
            else:
                options.append('rw')
            
            options.extend(['sync', 'no_subtree_check'])
            
            if not share.guest_access:
                options.append('root_squash')
            else:
                options.append('no_root_squash')
            
            # Build allowed hosts list
            allowed_hosts = share.get_allowed_hosts() or ['*']
            
            # Create export entry
            export_line = f"{share.dataset.path}"
            for host in allowed_hosts:
                export_line += f" {host}({','.join(options)})"
            export_line += "\n"
            
            # Read current exports
            exports_content = ''
            if os.path.exists(self.nfs_exports_path):
                with open(self.nfs_exports_path, 'r') as f:
                    exports_content = f.read()
            
            # Check if export already exists
            if share.dataset.path in exports_content:
                return False, f'NFS export for {share.dataset.path} already exists'
            
            # Add export
            with open(self.nfs_exports_path, 'a') as f:
                f.write(export_line)
            
            # Export the new share
            success, stdout, stderr = self.run_command(['exportfs', '-a'])
            if not success:
                return False, f'Failed to export NFS share: {stderr}'
            
            return True, f'NFS share {share.name} created successfully'
            
        except Exception as e:
            return False, f'Error creating NFS share: {str(e)}'
    
    def delete_nfs_share(self, share: Share) -> Tuple[bool, str]:
        """Delete NFS export"""
        try:
            if not os.path.exists(self.nfs_exports_path):
                return True, 'NFS exports file not found'
            
            # Read current exports
            with open(self.nfs_exports_path, 'r') as f:
                lines = f.readlines()
            
            # Remove export line
            new_lines = []
            for line in lines:
                if share.dataset.path not in line:
                    new_lines.append(line)
            
            # Write updated exports
            with open(self.nfs_exports_path, 'w') as f:
                f.writelines(new_lines)
            
            # Unexport the share
            success, stdout, stderr = self.run_command(['exportfs', '-u', share.dataset.path])
            if not success:
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category='shares',
                    message=f'Failed to unexport NFS share {share.name}: {stderr}'
                )
            
            # Re-export all
            success, stdout, stderr = self.run_command(['exportfs', '-a'])
            if not success:
                return False, f'Failed to reload NFS exports: {stderr}'
            
            return True, f'NFS share {share.name} deleted successfully'
            
        except Exception as e:
            return False, f'Error deleting NFS share: {str(e)}'
    
    def get_nfs_connections(self) -> List[Dict]:
        """Get active NFS connections"""
        connections = []
        
        try:
            success, stdout, stderr = self.run_command(['showmount', '-a'])
            if success:
                lines = stdout.split('\\n')
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            connections.append({
                                'client': parts[0],
                                'mount_path': parts[1]
                            })
        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='shares',
                message=f'Failed to get NFS connections: {str(e)}'
            )
        
        return connections
    
    def get_exports(self) -> List[Dict]:
        """Get current NFS exports"""
        exports = []
        try:
            success, stdout, stderr = self.run_command(['exportfs'])
            if success:
                lines = stdout.split('\\n')
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 2:
                            exports.append({
                                'path': parts[0],
                                'client': parts[1] if len(parts) > 1 else '*'
                            })
        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='shares',
                message=f'Failed to get NFS exports: {str(e)}'
            )
        return exports
    
    def get_active_connections(self) -> List[Dict]:
        """Alias for get_nfs_connections for compatibility"""
        return self.get_nfs_connections()

class FTPManager(ShareProtocolManager):
    """FTP share management"""
    
    def create_ftp_share(self, share: Share) -> Tuple[bool, str]:
        """Configure FTP access for share"""
        try:
            # For FTP, we typically create a symbolic link in the FTP root
            # to the actual dataset path
            ftp_root = '/srv/ftp'
            ftp_share_path = os.path.join(ftp_root, share.name)
            
            # Ensure FTP root exists
            os.makedirs(ftp_root, exist_ok=True)
            
            # Create symbolic link
            if os.path.exists(ftp_share_path):
                return False, f'FTP share path {ftp_share_path} already exists'
            
            os.symlink(share.dataset.path, ftp_share_path)
            
            # Set appropriate permissions
            os.chmod(ftp_share_path, 0o755 if not share.read_only else 0o555)
            
            # Restart FTP service to pick up changes
            success, stdout, stderr = self.run_command(['systemctl', 'restart', 'vsftpd'])
            if not success:
                # Cleanup on failure
                if os.path.islink(ftp_share_path):
                    os.unlink(ftp_share_path)
                return False, f'Failed to restart FTP service: {stderr}'
            
            return True, f'FTP share {share.name} created successfully'
            
        except Exception as e:
            return False, f'Error creating FTP share: {str(e)}'
    
    def delete_ftp_share(self, share: Share) -> Tuple[bool, str]:
        """Delete FTP share"""
        try:
            ftp_root = '/srv/ftp'
            ftp_share_path = os.path.join(ftp_root, share.name)
            
            # Remove symbolic link
            if os.path.islink(ftp_share_path):
                os.unlink(ftp_share_path)
            elif os.path.exists(ftp_share_path):
                return False, f'FTP share path {ftp_share_path} exists but is not a symbolic link'
            
            return True, f'FTP share {share.name} deleted successfully'
            
        except Exception as e:
            return False, f'Error deleting FTP share: {str(e)}'
    
    def get_ftp_connections(self) -> List[Dict]:
        """Get active FTP connections"""
        connections = []
        
        try:
            # Check for active FTP processes
            success, stdout, stderr = self.run_command(['ps', 'aux'])
            if success:
                lines = stdout.split('\\n')
                for line in lines:
                    if 'vsftpd' in line and 'priv' not in line:
                        parts = line.split()
                        if len(parts) >= 11:
                            connections.append({
                                'user': parts[0],
                                'pid': parts[1],
                                'cpu': parts[2],
                                'mem': parts[3],
                                'command': ' '.join(parts[10:])
                            })
        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='shares',
                message=f'Failed to get FTP connections: {str(e)}'
            )
        
        return connections

# Protocol manager instances
smb_manager = SMBManager()
nfs_manager = NFSManager()
ftp_manager = FTPManager()

def get_protocol_manager(protocol: ShareProtocol):
    """Get appropriate protocol manager"""
    managers = {
        ShareProtocol.SMB: smb_manager,
        ShareProtocol.NFS: nfs_manager,
        ShareProtocol.FTP: ftp_manager,
        ShareProtocol.SFTP: ftp_manager  # SFTP uses FTP manager for now
    }
    return managers.get(protocol)