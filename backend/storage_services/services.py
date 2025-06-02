"""
Storage Services - Business logic for storage operations
"""
import os
import subprocess
import shutil
import json
import psutil
import time
import threading
import socket
from pathlib import Path
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone


class StorageService:
    """Service for managing storage pools and datasets"""

    def __init__(self):
        self.monitoring_interval = 30  # seconds
        self._monitoring_thread = None
        self._stop_monitoring = False

    def scan_mount_points(self):
        """Scan system for available mount points"""
        mount_points = []
        try:
            # Read /proc/mounts to find mounted filesystems
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        device, mount_point, fs_type = parts[0], parts[1], parts[2]
                        
                        # Filter relevant mount points
                        if (mount_point.startswith('/mnt/') or 
                            mount_point.startswith('/media/') or
                            mount_point.startswith(getattr(settings, 'MOXNAS_SETTINGS', {}).get('MOUNT_POINTS_BASE', '/mnt/storage'))):
                            
                            # Get size information
                            try:
                                stat = os.statvfs(mount_point)
                                total_size = stat.f_frsize * stat.f_blocks
                                available_size = stat.f_frsize * stat.f_available
                                
                                mount_points.append({
                                    'device': device,
                                    'mount_point': mount_point,
                                    'fs_type': fs_type,
                                    'total_size': total_size,
                                    'available_size': available_size,
                                })
                            except OSError:
                                continue
        except IOError:
            pass
        
        return mount_points

    def create_dataset_directory(self, dataset):
        """Create directory structure for a dataset"""
        try:
            os.makedirs(dataset.full_path, exist_ok=True)
            os.chmod(dataset.full_path, 0o755)
            return {'success': True, 'message': 'Dataset directory created'}
        except OSError as e:
            return {'success': False, 'message': f'Failed to create directory: {e}'}

    def set_dataset_permissions(self, dataset, permissions):
        """Set permissions on dataset directory"""
        try:
            # Convert permissions to octal
            mode = int(permissions, 8) if isinstance(permissions, str) else permissions
            os.chmod(dataset.full_path, mode)
            return {'success': True, 'message': 'Permissions updated'}
        except (OSError, ValueError) as e:
            return {'success': False, 'message': f'Failed to set permissions: {e}'}

    def get_storage_usage(self, mount_point):
        """Get detailed storage usage for a mount point"""
        try:
            usage = shutil.disk_usage(mount_point)
            return {
                'total': usage.total,
                'used': usage.total - usage.free,
                'free': usage.free,
                'usage_percent': ((usage.total - usage.free) / usage.total) * 100
            }
        except OSError:
            return None

    def monitor_storage_health(self):
        """Monitor storage health and performance"""
        health_data = {}
        
        for pool in self.scan_mount_points():
            mount_point = pool['mount_point']
            
            # Basic usage stats
            usage = self.get_storage_usage(mount_point)
            if not usage:
                continue
                
            # Performance metrics
            disk_io = psutil.disk_io_counters(perdisk=True)
            
            # Check for potential issues
            warnings = []
            if usage['usage_percent'] > 90:
                warnings.append('Storage usage critical (>90%)')
            elif usage['usage_percent'] > 80:
                warnings.append('Storage usage high (>80%)')
                
            health_data[mount_point] = {
                'usage': usage,
                'warnings': warnings,
                'last_check': timezone.now().isoformat(),
                'healthy': len(warnings) == 0
            }
            
        return health_data

    def start_monitoring(self):
        """Start background storage monitoring"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return False
            
        self._stop_monitoring = False
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self._monitoring_thread.daemon = True
        self._monitoring_thread.start()
        return True

    def stop_monitoring(self):
        """Stop background storage monitoring"""
        self._stop_monitoring = True
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)

    def _monitoring_loop(self):
        """Background monitoring loop"""
        while not self._stop_monitoring:
            try:
                health_data = self.monitor_storage_health()
                cache.set('storage_health', health_data, timeout=300)
                
                # Check for critical alerts
                for mount_point, data in health_data.items():
                    if not data['healthy']:
                        self._send_storage_alert(mount_point, data['warnings'])
                        
            except Exception as e:
                print(f"Storage monitoring error: {e}")
                
            time.sleep(self.monitoring_interval)

    def _send_storage_alert(self, mount_point, warnings):
        """Send storage alert (implement notification system)"""
        # TODO: Implement notification system
        print(f"STORAGE ALERT - {mount_point}: {', '.join(warnings)}")

    def create_snapshot(self, dataset_path, snapshot_name):
        """Create a snapshot of a dataset (filesystem-level)"""
        try:
            snapshot_dir = Path(dataset_path) / '.snapshots'
            snapshot_dir.mkdir(exist_ok=True)
            
            snapshot_path = snapshot_dir / f"{snapshot_name}_{int(time.time())}"
            
            # Create hard-link based snapshot (simple implementation)
            subprocess.run([
                'cp', '-al', dataset_path, str(snapshot_path)
            ], check=True)
            
            return {
                'success': True, 
                'message': f'Snapshot created: {snapshot_path}',
                'snapshot_path': str(snapshot_path)
            }
        except subprocess.CalledProcessError as e:
            return {'success': False, 'message': f'Snapshot failed: {e}'}

    def list_snapshots(self, dataset_path):
        """List available snapshots for a dataset"""
        try:
            snapshot_dir = Path(dataset_path) / '.snapshots'
            if not snapshot_dir.exists():
                return []
                
            snapshots = []
            for item in snapshot_dir.iterdir():
                if item.is_dir():
                    stat = item.stat()
                    snapshots.append({
                        'name': item.name,
                        'path': str(item),
                        'created': stat.st_ctime,
                        'size': self._get_directory_size(item)
                    })
                    
            return sorted(snapshots, key=lambda x: x['created'], reverse=True)
        except OSError:
            return []

    def _get_directory_size(self, path):
        """Calculate directory size"""
        try:
            result = subprocess.run([
                'du', '-sb', str(path)
            ], capture_output=True, text=True, check=True)
            return int(result.stdout.split()[0])
        except (subprocess.CalledProcessError, ValueError):
            return 0

    def cleanup_old_snapshots(self, dataset_path, keep_count=10):
        """Remove old snapshots, keeping only the specified number"""
        snapshots = self.list_snapshots(dataset_path)
        if len(snapshots) <= keep_count:
            return {'success': True, 'message': 'No cleanup needed'}
            
        to_remove = snapshots[keep_count:]
        removed_count = 0
        
        for snapshot in to_remove:
            try:
                shutil.rmtree(snapshot['path'])
                removed_count += 1
            except OSError:
                continue
                
        return {
            'success': True, 
            'message': f'Removed {removed_count} old snapshots'
        }

    def get_filesystem_info(self, path):
        """Get detailed filesystem information"""
        try:
            stat = os.statvfs(path)
            return {
                'block_size': stat.f_frsize,
                'total_blocks': stat.f_blocks,
                'free_blocks': stat.f_bavail,
                'total_inodes': stat.f_files,
                'free_inodes': stat.f_favail,
                'filesystem_id': stat.f_fsid,
                'mount_flags': stat.f_flag
            }
        except OSError:
            return None


class ShareService:
    """Service for managing network shares"""

    def __init__(self):
        # Use settings-based config directory instead of /etc/moxnas
        config_path = getattr(settings, 'MOXNAS_SETTINGS', {}).get('CONFIG_PATH', '/tmp/moxnas')
        self.config_dir = Path(config_path)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir = self.config_dir / 'templates'
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def generate_smb_config(self, shares):
        """Generate Samba configuration"""
        config_lines = [
            '[global]',
            '    workgroup = WORKGROUP',
            '    server string = MoxNAS Server',
            '    netbios name = MOXNAS',
            '    security = user',
            '    map to guest = Bad User',
            '    guest account = nobody',
            '    local master = yes',
            '    preferred master = yes',
            '    os level = 65',
            '',
        ]

        for share in shares.filter(share_type='smb', enabled=True):
            config_lines.extend([
                f'[{share.name}]',
                f'    path = {share.dataset.full_path}',
                f'    comment = {share.description}',
                f'    browseable = yes',
                f'    read only = {"yes" if share.readonly else "no"}',
                f'    guest ok = {"yes" if share.guest_access else "no"}',
                f'    create mask = 0664',
                f'    directory mask = 0775',
                '',
            ])

        return '\n'.join(config_lines)

    def generate_nfs_exports(self, shares):
        """Generate NFS exports configuration"""
        exports = []
        for share in shares.filter(share_type='nfs', enabled=True):
            options = 'rw,sync,no_subtree_check'
            if share.readonly:
                options = 'ro,sync,no_subtree_check'
            
            exports.append(f'{share.dataset.full_path} *(insecure,{options})')

        return '\n'.join(exports)

    def write_smb_config(self, shares):
        """Write Samba configuration to file"""
        config_content = self.generate_smb_config(shares)
        config_file = self.config_dir / 'smb.conf'
        
        try:
            with open(config_file, 'w') as f:
                f.write(config_content)
            return {'success': True, 'message': 'SMB config written'}
        except IOError as e:
            return {'success': False, 'message': f'Failed to write config: {e}'}

    def write_nfs_exports(self, shares):
        """Write NFS exports configuration"""
        exports_content = self.generate_nfs_exports(shares)
        exports_file = self.config_dir / 'exports'
        
        try:
            with open(exports_file, 'w') as f:
                f.write(exports_content)
            return {'success': True, 'message': 'NFS exports written'}
        except IOError as e:
            return {'success': False, 'message': f'Failed to write exports: {e}'}

    def restart_samba(self):
        """Restart Samba service"""
        try:
            subprocess.run(['systemctl', 'restart', 'smbd'], check=True)
            subprocess.run(['systemctl', 'restart', 'nmbd'], check=True)
            return {'success': True, 'message': 'Samba restarted'}
        except subprocess.CalledProcessError as e:
            return {'success': False, 'message': f'Failed to restart Samba: {e}'}

    def restart_nfs(self):
        """Restart NFS service"""
        try:
            subprocess.run(['systemctl', 'restart', 'nfs-kernel-server'], check=True)
            subprocess.run(['exportfs', '-ra'], check=True)
            return {'success': True, 'message': 'NFS restarted'}
        except subprocess.CalledProcessError as e:
            return {'success': False, 'message': f'Failed to restart NFS: {e}'}

    def enable_share(self, share):
        """Enable a specific share"""
        from .models import Share
        
        if share.share_type == 'smb':
            shares = Share.objects.filter(share_type='smb')
            self.write_smb_config(shares)
            return self.restart_samba()
        elif share.share_type == 'nfs':
            shares = Share.objects.filter(share_type='nfs')
            self.write_nfs_exports(shares)
            return self.restart_nfs()
        else:
            return {'success': False, 'message': 'Unsupported share type'}

    def disable_share(self, share):
        """Disable a specific share"""
        # Same as enable - regenerate configs without the disabled share
        return self.enable_share(share)

    def restart_all_services(self):
        """Restart all share services"""
        results = {}
        results['samba'] = self.restart_samba()
        results['nfs'] = self.restart_nfs()
        return results

    def validate_share_config(self, share_data):
        """Validate share configuration before creation"""
        errors = []
        
        # Check if name is valid
        if not share_data.get('name') or not share_data['name'].replace('_', '').replace('-', '').isalnum():
            errors.append('Share name must be alphanumeric with underscores or hyphens')
            
        # Check if path exists
        if share_data.get('path') and not os.path.exists(share_data['path']):
            errors.append('Share path does not exist')
            
        # Check for SMB-specific issues
        if share_data.get('share_type') == 'smb':
            if len(share_data.get('name', '')) > 12:
                errors.append('SMB share names should be 12 characters or less for compatibility')
                
        return errors

    def get_active_connections(self, share_type='all'):
        """Get active connections to shares"""
        connections = {}
        
        if share_type in ['smb', 'all']:
            connections['smb'] = self._get_smb_connections()
            
        if share_type in ['nfs', 'all']:
            connections['nfs'] = self._get_nfs_connections()
            
        return connections

    def _get_smb_connections(self):
        """Get active SMB connections"""
        try:
            result = subprocess.run(['smbstatus', '-b'], 
                                  capture_output=True, text=True, check=True)
            connections = []
            for line in result.stdout.split('\n'):
                if 'DENY_NONE' in line:  # Active connection line
                    parts = line.split()
                    if len(parts) >= 6:
                        connections.append({
                            'pid': parts[0],
                            'user': parts[1],
                            'share': parts[3],
                            'machine': parts[4],
                            'connected_at': parts[5] + ' ' + parts[6] if len(parts) > 6 else ''
                        })
            return connections
        except subprocess.CalledProcessError:
            return []

    def _get_nfs_connections(self):
        """Get active NFS connections"""
        try:
            # Check /proc/fs/nfsd/clients for NFS4 clients
            connections = []
            clients_file = Path('/proc/fs/nfsd/clients')
            if clients_file.exists():
                for client_dir in clients_file.iterdir():
                    if client_dir.is_dir():
                        info_file = client_dir / 'info'
                        if info_file.exists():
                            with open(info_file, 'r') as f:
                                client_info = f.read().strip()
                                connections.append({
                                    'client_id': client_dir.name,
                                    'info': client_info
                                })
            return connections
        except (OSError, IOError):
            return []

    def create_user_template(self, template_name, config):
        """Create a reusable share template"""
        template_file = self.templates_dir / f'{template_name}.json'
        try:
            with open(template_file, 'w') as f:
                json.dump(config, f, indent=2)
            return {'success': True, 'message': f'Template {template_name} created'}
        except IOError as e:
            return {'success': False, 'message': f'Failed to create template: {e}'}

    def apply_template(self, template_name, share_name, dataset):
        """Apply a template to create a new share"""
        template_file = self.templates_dir / f'{template_name}.json'
        if not template_file.exists():
            return {'success': False, 'message': 'Template not found'}
            
        try:
            with open(template_file, 'r') as f:
                template_config = json.load(f)
                
            # Apply template to create share
            from .models import Share
            share = Share.objects.create(
                name=share_name,
                dataset=dataset,
                **template_config
            )
            
            return {'success': True, 'message': f'Share created from template', 'share_id': share.id}
        except (IOError, json.JSONDecodeError) as e:
            return {'success': False, 'message': f'Failed to apply template: {e}'}

    def bulk_share_operation(self, share_ids, operation):
        """Perform bulk operations on multiple shares"""
        from .models import Share
        
        results = {}
        shares = Share.objects.filter(id__in=share_ids)
        
        for share in shares:
            try:
                if operation == 'enable':
                    share.enabled = True
                    share.save()
                    result = self.enable_share(share)
                elif operation == 'disable':
                    share.enabled = False
                    share.save()
                    result = self.disable_share(share)
                elif operation == 'restart':
                    result = self.enable_share(share)  # Restart by re-enabling
                else:
                    result = {'success': False, 'message': 'Unknown operation'}
                    
                results[share.id] = result
            except Exception as e:
                results[share.id] = {'success': False, 'message': str(e)}
                
        return results

    def generate_share_report(self):
        """Generate comprehensive share usage report"""
        from .models import Share
        
        shares = Share.objects.all()
        report = {
            'summary': {
                'total_shares': shares.count(),
                'enabled_shares': shares.filter(enabled=True).count(),
                'share_types': {}
            },
            'shares': [],
            'connections': self.get_active_connections(),
            'generated_at': timezone.now().isoformat()
        }
        
        # Count by type
        for share_type, _ in Share.SHARE_TYPES:
            count = shares.filter(share_type=share_type).count()
            report['summary']['share_types'][share_type] = count
            
        # Detailed share info
        for share in shares:
            usage = None
            if os.path.exists(share.dataset.full_path):
                try:
                    usage = shutil.disk_usage(share.dataset.full_path)
                except OSError:
                    pass
                    
            share_info = {
                'id': share.id,
                'name': share.name,
                'type': share.share_type,
                'enabled': share.enabled,
                'path': share.dataset.full_path,
                'readonly': share.readonly,
                'guest_access': share.guest_access,
                'usage': {
                    'total': usage.total if usage else 0,
                    'free': usage.free if usage else 0,
                    'used': (usage.total - usage.free) if usage else 0
                } if usage else None
            }
            report['shares'].append(share_info)
            
        return report

    def test_share_connectivity(self, share):
        """Test if a share is accessible"""
        tests = {}
        
        if share.share_type == 'smb':
            tests['smb'] = self._test_smb_share(share)
        elif share.share_type == 'nfs':
            tests['nfs'] = self._test_nfs_share(share)
            
        return tests

    def _test_smb_share(self, share):
        """Test SMB share accessibility"""
        try:
            # Test with smbclient
            result = subprocess.run([
                'smbclient', f'//{socket.gethostname()}/{share.name}', 
                '-N', '-c', 'ls'
            ], capture_output=True, text=True, timeout=10)
            
            return {
                'accessible': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr
            }
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            return {
                'accessible': False,
                'error': str(e)
            }

    def _test_nfs_share(self, share):
        """Test NFS share accessibility"""
        try:
            # Test with showmount
            result = subprocess.run([
                'showmount', '-e', 'localhost'
            ], capture_output=True, text=True, timeout=10)
            
            accessible = share.dataset.full_path in result.stdout
            return {
                'accessible': accessible,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            return {
                'accessible': False,
                'error': str(e)
            }


class ISCSIService:
    """Service for managing iSCSI targets"""

    def __init__(self):
        self.config_dir = Path('/etc/moxnas/iscsi')
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.targets_dir = self.config_dir / 'targets'
        self.targets_dir.mkdir(exist_ok=True)

    def list_targets(self):
        """List all iSCSI targets"""
        targets = []
        try:
            # Use tgtadm to list targets
            result = subprocess.run(['tgtadm', '--mode', 'target', '--op', 'show'], 
                                  capture_output=True, text=True, check=True)
            
            # Parse tgtadm output
            current_target = None
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('Target'):
                    if current_target:
                        targets.append(current_target)
                    current_target = {'id': None, 'name': None, 'luns': []}
                    parts = line.split()
                    if len(parts) >= 2:
                        current_target['id'] = parts[1].rstrip(':')
                elif line.startswith('LUN:') and current_target:
                    lun_info = self._parse_lun_info(line)
                    if lun_info:
                        current_target['luns'].append(lun_info)
                        
            if current_target:
                targets.append(current_target)
                
        except subprocess.CalledProcessError:
            pass
            
        return targets

    def _parse_lun_info(self, lun_line):
        """Parse LUN information from tgtadm output"""
        try:
            # Extract LUN details
            parts = lun_line.split()
            if len(parts) >= 2:
                lun_id = parts[1]
                # Get more details about this LUN
                return {
                    'id': lun_id,
                    'type': 'disk',  # Default
                    'backing_store': None  # Would need additional parsing
                }
        except (IndexError, ValueError):
            pass
        return None

    def create_target_advanced(self, config):
        """Create iSCSI target with advanced configuration"""
        try:
            target_name = config['name']
            backing_file = config.get('backing_file')
            size_gb = config.get('size_gb', 10)
            target_iqn = config.get('iqn', f'iqn.2024-01.com.moxnas:{target_name}')
            
            # Create backing file if needed
            if backing_file:
                backing_path = Path(backing_file)
            else:
                backing_path = self.targets_dir / f'{target_name}.img'
                
            if not backing_path.exists():
                # Create sparse file for efficiency
                with open(backing_path, 'wb') as f:
                    f.seek(size_gb * 1024**3 - 1)
                    f.write(b'\0')
                    
            # Create target using tgtadm
            target_id = self._get_next_target_id()
            
            # Create target
            subprocess.run([
                'tgtadm', '--mode', 'target', '--op', 'new',
                '--tid', str(target_id), '--targetname', target_iqn
            ], check=True)
            
            # Add LUN
            subprocess.run([
                'tgtadm', '--mode', 'logicalunit', '--op', 'new',
                '--tid', str(target_id), '--lun', '1',
                '--backing-store', str(backing_path)
            ], check=True)
            
            # Configure access if specified
            if config.get('allowed_initiators'):
                for initiator in config['allowed_initiators']:
                    subprocess.run([
                        'tgtadm', '--mode', 'target', '--op', 'bind',
                        '--tid', str(target_id), '--initiator-address', initiator
                    ], check=True)
            else:
                # Allow all initiators
                subprocess.run([
                    'tgtadm', '--mode', 'target', '--op', 'bind',
                    '--tid', str(target_id), '--initiator-address', 'ALL'
                ], check=True)
                
            # Save configuration
            self._save_target_config(target_id, config)
            
            return {
                'success': True, 
                'message': f'iSCSI target {target_name} created',
                'target_id': target_id,
                'iqn': target_iqn
            }
            
        except subprocess.CalledProcessError as e:
            return {'success': False, 'message': f'Failed to create target: {e}'}

    def _get_next_target_id(self):
        """Get the next available target ID"""
        existing_targets = self.list_targets()
        used_ids = [int(t['id']) for t in existing_targets if t['id'] and t['id'].isdigit()]
        
        next_id = 1
        while next_id in used_ids:
            next_id += 1
        return next_id

    def _save_target_config(self, target_id, config):
        """Save target configuration to file"""
        config_file = self.config_dir / f'target_{target_id}.json'
        try:
            with open(config_file, 'w') as f:
                json.dump({
                    'target_id': target_id,
                    'created_at': timezone.now().isoformat(),
                    **config
                }, f, indent=2)
        except IOError:
            pass

    def delete_target_advanced(self, target_id):
        """Delete iSCSI target by ID"""
        try:
            # Remove target
            subprocess.run([
                'tgtadm', '--mode', 'target', '--op', 'delete',
                '--tid', str(target_id)
            ], check=True)
            
            # Remove config file
            config_file = self.config_dir / f'target_{target_id}.json'
            if config_file.exists():
                config_file.unlink()
                
            return {'success': True, 'message': f'Target {target_id} deleted'}
        except subprocess.CalledProcessError as e:
            return {'success': False, 'message': f'Failed to delete target: {e}'}

    def get_target_sessions(self, target_id=None):
        """Get active iSCSI sessions"""
        try:
            cmd = ['tgtadm', '--mode', 'conn', '--op', 'show']
            if target_id:
                cmd.extend(['--tid', str(target_id)])
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            sessions = []
            current_session = None
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('Session:'):
                    if current_session:
                        sessions.append(current_session)
                    current_session = {'id': None, 'connection': None, 'initiator': None}
                    parts = line.split()
                    if len(parts) >= 2:
                        current_session['id'] = parts[1]
                elif 'Connection:' in line and current_session:
                    current_session['connection'] = line.split('Connection:')[1].strip()
                elif 'Initiator:' in line and current_session:
                    current_session['initiator'] = line.split('Initiator:')[1].strip()
                    
            if current_session:
                sessions.append(current_session)
                
            return sessions
        except subprocess.CalledProcessError:
            return []

    def get_target_stats(self, target_id):
        """Get statistics for a specific target"""
        try:
            result = subprocess.run([
                'tgtadm', '--mode', 'target', '--op', 'show',
                '--tid', str(target_id)
            ], capture_output=True, text=True, check=True)
            
            # Parse statistics from output
            stats = {
                'read_ops': 0,
                'write_ops': 0,
                'read_bytes': 0,
                'write_bytes': 0
            }
            
            # Simple parsing - would need more sophisticated parsing for real stats
            for line in result.stdout.split('\n'):
                if 'read' in line.lower() and 'sectors' in line.lower():
                    # Extract read statistics
                    pass
                elif 'write' in line.lower() and 'sectors' in line.lower():
                    # Extract write statistics
                    pass
                    
            return stats
        except subprocess.CalledProcessError:
            return {}

    def backup_target_config(self):
        """Backup all target configurations"""
        try:
            backup_file = self.config_dir / f'backup_{int(time.time())}.json'
            
            targets = self.list_targets()
            configs = []
            
            for target in targets:
                config_file = self.config_dir / f'target_{target["id"]}.json'
                if config_file.exists():
                    with open(config_file, 'r') as f:
                        configs.append(json.load(f))
                        
            with open(backup_file, 'w') as f:
                json.dump({
                    'backup_date': timezone.now().isoformat(),
                    'targets': configs
                }, f, indent=2)
                
            return {'success': True, 'backup_file': str(backup_file)}
        except (IOError, json.JSONDecodeError) as e:
            return {'success': False, 'message': f'Backup failed: {e}'}

    def restore_target_config(self, backup_file):
        """Restore target configurations from backup"""
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
                
            results = []
            for target_config in backup_data.get('targets', []):
                result = self.create_target_advanced(target_config)
                results.append(result)
                
            return {'success': True, 'results': results}
        except (IOError, json.JSONDecodeError) as e:
            return {'success': False, 'message': f'Restore failed: {e}'}


class BackupService:
    """Service for managing backups and synchronization"""
    
    def __init__(self):
        self.backup_dir = Path('/var/lib/moxnas/backups')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_dataset_backup(self, dataset, destination, compression=True):
        """Create a backup of a dataset"""
        try:
            timestamp = int(time.time())
            backup_name = f"{dataset.name}_{timestamp}"
            
            if compression:
                backup_file = self.backup_dir / f"{backup_name}.tar.gz"
                cmd = ['tar', '-czf', str(backup_file), '-C', str(Path(dataset.full_path).parent), dataset.name]
            else:
                backup_file = self.backup_dir / f"{backup_name}.tar"
                cmd = ['tar', '-cf', str(backup_file), '-C', str(Path(dataset.full_path).parent), dataset.name]
                
            subprocess.run(cmd, check=True)
            
            return {
                'success': True,
                'backup_file': str(backup_file),
                'size': backup_file.stat().st_size
            }
        except subprocess.CalledProcessError as e:
            return {'success': False, 'message': f'Backup failed: {e}'}
            
    def list_backups(self):
        """List available backups"""
        backups = []
        for backup_file in self.backup_dir.glob('*.tar*'):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'path': str(backup_file),
                'size': stat.st_size,
                'created': stat.st_ctime
            })
        return sorted(backups, key=lambda x: x['created'], reverse=True)
        
    def restore_backup(self, backup_file, destination):
        """Restore a backup to specified destination"""
        try:
            if backup_file.endswith('.gz'):
                cmd = ['tar', '-xzf', backup_file, '-C', destination]
            else:
                cmd = ['tar', '-xf', backup_file, '-C', destination]
                
            subprocess.run(cmd, check=True)
            return {'success': True, 'message': 'Backup restored successfully'}
        except subprocess.CalledProcessError as e:
            return {'success': False, 'message': f'Restore failed: {e}'}
