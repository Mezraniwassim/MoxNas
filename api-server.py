#!/usr/bin/env python3
"""
MoxNAS API Server
Lightweight Python API for NAS management
Copyright (c) 2024 MoxNAS Contributors
License: MIT
"""

import asyncio
import json
import subprocess
import time
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
import logging

try:
    import psutil
    import aiohttp.web
    import aiofiles
except ImportError:
    print("Required packages not installed. Run: pip3 install aiohttp aiofiles psutil")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/moxnas/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('moxnas-api')

class MoxNASAPI:
    def __init__(self):
        self.app = aiohttp.web.Application()
        self.setup_routes()
        self.setup_cors()
        self.shares_config = '/etc/moxnas/shares.json'
        self.users_config = '/etc/moxnas/users.json'
        
    def setup_routes(self):
        """Setup API routes"""
        self.app.router.add_get('/api/system-stats', self.get_system_stats)
        self.app.router.add_get('/api/services', self.get_services)
        self.app.router.add_post('/api/services/{service}/restart', self.restart_service)
        
        # Share management
        self.app.router.add_get('/api/shares', self.get_shares)
        self.app.router.add_post('/api/shares', self.create_share)
        self.app.router.add_delete('/api/shares/{name}', self.delete_share)
        
        # Storage management
        self.app.router.add_get('/api/storage', self.get_storage_info)
        self.app.router.add_get('/api/storage/mounts', self.get_mount_points)
        
        # Network management
        self.app.router.add_get('/api/network', self.get_network_info)
        
        # User management
        self.app.router.add_get('/api/users', self.get_users)
        self.app.router.add_post('/api/users', self.create_user)
        self.app.router.add_delete('/api/users/{username}', self.delete_user)
        
        # System logs
        self.app.router.add_get('/api/logs/{service}', self.get_logs)
        
    def setup_cors(self):
        """Setup CORS middleware"""
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
            
        self.app.middlewares.append(cors_middleware)
    
    async def get_system_stats(self, request):
        """Get real-time system statistics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # System uptime
            boot_time = psutil.boot_time()
            uptime = datetime.now() - datetime.fromtimestamp(boot_time)
            
            # Process count
            process_count = len(psutil.pids())
            
            stats = {
                'cpu': {
                    'percent': round(cpu_percent, 1),
                    'cores': psutil.cpu_count(),
                    'frequency': psutil.cpu_freq().current if psutil.cpu_freq() else 0
                },
                'memory': {
                    'percent': round(memory.percent, 1),
                    'used': self.bytes_to_human(memory.used),
                    'total': self.bytes_to_human(memory.total),
                    'available': self.bytes_to_human(memory.available)
                },
                'disk': {
                    'percent': round((disk.used / disk.total) * 100, 1),
                    'used': self.bytes_to_human(disk.used),
                    'total': self.bytes_to_human(disk.total),
                    'free': self.bytes_to_human(disk.free)
                },
                'network': {
                    'bytes_sent': self.bytes_to_human(network.bytes_sent),
                    'bytes_recv': self.bytes_to_human(network.bytes_recv),
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'system': {
                    'uptime': str(uptime).split('.')[0],
                    'processes': process_count,
                    'boot_time': boot_time
                },
                'timestamp': datetime.now().isoformat()
            }
            
            return aiohttp.web.json_response(stats)
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    async def get_services(self, request):
        """Get status of NAS services"""
        services = ['nginx', 'smbd', 'nfs-kernel-server', 'vsftpd', 'moxnas-api']
        status = {}
        
        for service in services:
            try:
                # Check if service is active
                result = await self.run_command(['systemctl', 'is-active', service])
                is_active = result.returncode == 0
                
                # Get service status details
                status_result = await self.run_command(['systemctl', 'status', service, '--no-pager', '-l'])
                
                status[service] = {
                    'active': is_active,
                    'status': result.stdout.strip() if result.stdout else 'inactive',
                    'enabled': await self.is_service_enabled(service),
                    'pid': await self.get_service_pid(service) if is_active else None
                }
                
            except Exception as e:
                logger.error(f"Error checking service {service}: {e}")
                status[service] = {
                    'active': False,
                    'status': 'error',
                    'error': str(e)
                }
        
        return aiohttp.web.json_response(status)
    
    async def restart_service(self, request):
        """Restart a service"""
        service = request.match_info['service']
        allowed_services = ['nginx', 'smbd', 'nfs-kernel-server', 'vsftpd']
        
        if service not in allowed_services:
            return aiohttp.web.json_response({'error': 'Service not allowed'}, status=400)
        
        try:
            result = await self.run_command(['systemctl', 'restart', service])
            
            if result.returncode == 0:
                return aiohttp.web.json_response({
                    'success': True,
                    'message': f'Service {service} restarted successfully'
                })
            else:
                return aiohttp.web.json_response({
                    'error': f'Failed to restart {service}: {result.stderr}'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error restarting service {service}: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    async def get_shares(self, request):
        """Get list of configured shares"""
        shares = []
        
        try:
            # Parse Samba shares
            samba_shares = await self.parse_samba_config()
            shares.extend(samba_shares)
            
            # Parse NFS shares
            nfs_shares = await self.parse_nfs_config()
            shares.extend(nfs_shares)
            
        except Exception as e:
            logger.error(f"Error getting shares: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
        
        return aiohttp.web.json_response(shares)
    
    async def create_share(self, request):
        """Create a new share"""
        try:
            data = await request.json()
            name = data.get('name')
            share_type = data.get('type', 'smb')
            path = data.get('path', f'/mnt/shares/{name}')
            guest_access = data.get('guest', True)
            
            if not name:
                return aiohttp.web.json_response({'error': 'Share name required'}, status=400)
            
            # Create directory
            os.makedirs(path, mode=0o755, exist_ok=True)
            
            if share_type == 'smb':
                await self.create_samba_share(name, path, guest_access)
            elif share_type == 'nfs':
                await self.create_nfs_share(name, path)
            else:
                return aiohttp.web.json_response({'error': 'Unsupported share type'}, status=400)
            
            return aiohttp.web.json_response({
                'success': True,
                'name': name,
                'type': share_type,
                'path': path
            })
            
        except Exception as e:
            logger.error(f"Error creating share: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    async def delete_share(self, request):
        """Delete a share"""
        name = request.match_info['name']
        
        try:
            # Remove from Samba config
            await self.remove_samba_share(name)
            
            # Remove from NFS config
            await self.remove_nfs_share(name)
            
            return aiohttp.web.json_response({
                'success': True,
                'message': f'Share {name} deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error deleting share {name}: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    async def get_storage_info(self, request):
        """Get storage device information"""
        try:
            storage_info = {
                'disks': [],
                'partitions': [],
                'usage': {}
            }
            
            # Get disk information
            for device, mountpoint in psutil.disk_partitions():
                if device.startswith('/dev/'):
                    try:
                        usage = psutil.disk_usage(mountpoint)
                        storage_info['disks'].append({
                            'device': device,
                            'mountpoint': mountpoint,
                            'total': self.bytes_to_human(usage.total),
                            'used': self.bytes_to_human(usage.used),
                            'free': self.bytes_to_human(usage.free),
                            'percent': round((usage.used / usage.total) * 100, 1)
                        })
                    except:
                        continue
            
            return aiohttp.web.json_response(storage_info)
            
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    async def get_mount_points(self, request):
        """Get mount points"""
        try:
            mounts = []
            for partition in psutil.disk_partitions():
                mounts.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'opts': partition.opts
                })
            
            return aiohttp.web.json_response(mounts)
            
        except Exception as e:
            logger.error(f"Error getting mount points: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    async def get_network_info(self, request):
        """Get network interface information"""
        try:
            network_info = {
                'interfaces': [],
                'stats': {}
            }
            
            # Get network interfaces
            for interface, addrs in psutil.net_if_addrs().items():
                interface_info = {
                    'name': interface,
                    'addresses': []
                }
                
                for addr in addrs:
                    interface_info['addresses'].append({
                        'family': str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    })
                
                network_info['interfaces'].append(interface_info)
            
            # Get network statistics
            stats = psutil.net_io_counters(pernic=True)
            for interface, stat in stats.items():
                network_info['stats'][interface] = {
                    'bytes_sent': stat.bytes_sent,
                    'bytes_recv': stat.bytes_recv,
                    'packets_sent': stat.packets_sent,
                    'packets_recv': stat.packets_recv,
                    'errin': stat.errin,
                    'errout': stat.errout,
                    'dropin': stat.dropin,
                    'dropout': stat.dropout
                }
            
            return aiohttp.web.json_response(network_info)
            
        except Exception as e:
            logger.error(f"Error getting network info: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    async def get_users(self, request):
        """Get system users"""
        try:
            if os.path.exists(self.users_config):
                async with aiofiles.open(self.users_config, 'r') as f:
                    users_data = json.loads(await f.read())
                    return aiohttp.web.json_response(users_data)
            else:
                # Default admin user
                default_users = {
                    'admin': {
                        'role': 'administrator',
                        'created': datetime.now().isoformat()
                    }
                }
                return aiohttp.web.json_response(default_users)
                
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    async def get_logs(self, request):
        """Get service logs"""
        service = request.match_info['service']
        lines = int(request.query.get('lines', 100))
        
        try:
            result = await self.run_command([
                'journalctl', '-u', service, '-n', str(lines), '--no-pager', '-o', 'json'
            ])
            
            if result.returncode == 0:
                logs = []
                for line in result.stdout.split('\n'):
                    if line.strip():
                        try:
                            log_entry = json.loads(line)
                            logs.append({
                                'timestamp': log_entry.get('__REALTIME_TIMESTAMP'),
                                'message': log_entry.get('MESSAGE', ''),
                                'priority': log_entry.get('PRIORITY', '6'),
                                'unit': log_entry.get('_SYSTEMD_UNIT', '')
                            })
                        except json.JSONDecodeError:
                            continue
                
                return aiohttp.web.json_response(logs)
            else:
                return aiohttp.web.json_response({'error': 'Failed to get logs'}, status=500)
                
        except Exception as e:
            logger.error(f"Error getting logs for {service}: {e}")
            return aiohttp.web.json_response({'error': str(e)}, status=500)
    
    # Helper methods
    
    async def run_command(self, cmd):
        """Run shell command asynchronously"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return type('Result', (), {
            'returncode': process.returncode,
            'stdout': stdout.decode() if stdout else '',
            'stderr': stderr.decode() if stderr else ''
        })()
    
    async def is_service_enabled(self, service):
        """Check if service is enabled"""
        try:
            result = await self.run_command(['systemctl', 'is-enabled', service])
            return result.returncode == 0
        except:
            return False
    
    async def get_service_pid(self, service):
        """Get service PID"""
        try:
            result = await self.run_command(['systemctl', 'show', service, '--property=MainPID'])
            if result.returncode == 0:
                pid_line = result.stdout.strip()
                pid = pid_line.split('=')[1]
                return int(pid) if pid != '0' else None
        except:
            return None
    
    async def parse_samba_config(self):
        """Parse Samba configuration"""
        shares = []
        try:
            with open('/etc/samba/smb.conf', 'r') as f:
                content = f.read()
                
            current_share = None
            current_path = None
            
            for line in content.split('\n'):
                line = line.strip()
                
                if line.startswith('[') and line.endswith(']') and line != '[global]':
                    if current_share and current_path:
                        shares.append({
                            'name': current_share,
                            'type': 'smb',
                            'path': current_path,
                            'active': True
                        })
                    
                    current_share = line[1:-1]
                    current_path = None
                    
                elif current_share and line.startswith('path ='):
                    current_path = line.split('=', 1)[1].strip()
            
            # Add the last share
            if current_share and current_path:
                shares.append({
                    'name': current_share,
                    'type': 'smb',
                    'path': current_path,
                    'active': True
                })
                
        except FileNotFoundError:
            logger.warning("Samba config file not found")
        except Exception as e:
            logger.error(f"Error parsing Samba config: {e}")
        
        return shares
    
    async def parse_nfs_config(self):
        """Parse NFS exports"""
        shares = []
        try:
            with open('/etc/exports', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            path = parts[0]
                            shares.append({
                                'name': os.path.basename(path),
                                'type': 'nfs',
                                'path': path,
                                'active': True,
                                'clients': parts[1:]
                            })
        except FileNotFoundError:
            logger.warning("NFS exports file not found")
        except Exception as e:
            logger.error(f"Error parsing NFS config: {e}")
        
        return shares
    
    async def create_samba_share(self, name, path, guest_access=True):
        """Add share to Samba config"""
        share_config = f"""
[{name}]
   path = {path}
   browseable = yes
   read only = no
   guest ok = {'yes' if guest_access else 'no'}
   create mask = 0755
   directory mask = 0755
"""
        
        with open('/etc/samba/smb.conf', 'a') as f:
            f.write(share_config)
        
        # Reload Samba
        await self.run_command(['systemctl', 'reload', 'smbd'])
    
    async def create_nfs_share(self, name, path):
        """Add share to NFS exports"""
        export_line = f"{path} *(rw,sync,no_subtree_check,all_squash,anonuid=65534,anongid=65534)\n"
        
        with open('/etc/exports', 'a') as f:
            f.write(export_line)
        
        # Reload NFS exports
        await self.run_command(['exportfs', '-ra'])
    
    async def remove_samba_share(self, name):
        """Remove share from Samba config"""
        try:
            with open('/etc/samba/smb.conf', 'r') as f:
                lines = f.readlines()
            
            new_lines = []
            in_share = False
            
            for line in lines:
                if line.strip() == f'[{name}]':
                    in_share = True
                    continue
                elif line.strip().startswith('[') and line.strip() != f'[{name}]':
                    in_share = False
                
                if not in_share:
                    new_lines.append(line)
            
            with open('/etc/samba/smb.conf', 'w') as f:
                f.writelines(new_lines)
            
            await self.run_command(['systemctl', 'reload', 'smbd'])
            
        except Exception as e:
            logger.error(f"Error removing Samba share {name}: {e}")
    
    async def remove_nfs_share(self, name):
        """Remove share from NFS exports"""
        try:
            with open('/etc/exports', 'r') as f:
                lines = f.readlines()
            
            new_lines = [line for line in lines if not line.strip().endswith(name)]
            
            with open('/etc/exports', 'w') as f:
                f.writelines(new_lines)
            
            await self.run_command(['exportfs', '-ra'])
            
        except Exception as e:
            logger.error(f"Error removing NFS share {name}: {e}")
    
    @staticmethod
    def bytes_to_human(bytes_value):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f}{unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f}PB"

def main():
    """Main function"""
    # Ensure log directory exists
    os.makedirs('/var/log/moxnas', exist_ok=True)
    
    # Create API instance
    api = MoxNASAPI()
    
    # Start the server
    logger.info("Starting MoxNAS API server on 127.0.0.1:8001")
    aiohttp.web.run_app(
        api.app, 
        host='127.0.0.1', 
        port=8001,
        access_log=logger
    )

if __name__ == '__main__':
    main()