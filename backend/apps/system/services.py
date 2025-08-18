import psutil
import subprocess
import socket
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class SystemMonitor:
    """System monitoring service"""

    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory usage
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk usage
            disk_usage = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_usage.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
                    })
                except PermissionError:
                    continue
            
            # Network interfaces
            network_interfaces = []
            for interface, addrs in psutil.net_if_addrs().items():
                if interface != 'lo':  # Skip loopback
                    for addr in addrs:
                        if addr.family == socket.AF_INET:
                            network_interfaces.append({
                                'interface': interface,
                                'ip_address': addr.address,
                                'netmask': addr.netmask,
                            })
            
            # Network IO
            network_io = psutil.net_io_counters()
            
            # Boot time
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            
            # Load average (Linux only)
            try:
                load_avg = os.getloadavg()
            except OSError:
                load_avg = [0, 0, 0]
            
            return {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'frequency': cpu_freq._asdict() if cpu_freq else None,
                    'load_avg': {
                        '1min': load_avg[0],
                        '5min': load_avg[1],
                        '15min': load_avg[2],
                    }
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent,
                    'swap_total': swap.total,
                    'swap_used': swap.used,
                    'swap_percent': swap.percent,
                },
                'disk': disk_usage,
                'network': {
                    'interfaces': network_interfaces,
                    'io': {
                        'bytes_sent': network_io.bytes_sent,
                        'bytes_recv': network_io.bytes_recv,
                        'packets_sent': network_io.packets_sent,
                        'packets_recv': network_io.packets_recv,
                    }
                },
                'system': {
                    'boot_time': boot_time.isoformat(),
                    'uptime_seconds': uptime.total_seconds(),
                    'hostname': socket.gethostname(),
                    'platform': os.uname()._asdict(),
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            raise

    def get_service_status(self) -> List[Dict[str, Any]]:
        """Get status of key services"""
        services = [
            {'name': 'moxnas', 'description': 'MoxNAS Web Interface'},
            {'name': 'nginx', 'description': 'Web Server'},
            {'name': 'smbd', 'description': 'Samba SMB Service'},
            {'name': 'nmbd', 'description': 'Samba NetBIOS Service'},
            {'name': 'nfs-kernel-server', 'description': 'NFS Server'},
            {'name': 'vsftpd', 'description': 'FTP Server'},
            {'name': 'ssh', 'description': 'SSH Server'},
        ]
        
        status_list = []
        
        for service in services:
            try:
                # Check if service is active
                result = subprocess.run(
                    ['systemctl', 'is-active', service['name']], 
                    capture_output=True, text=True
                )
                is_active = result.stdout.strip() == 'active'
                
                # Check if service is enabled
                result = subprocess.run(
                    ['systemctl', 'is-enabled', service['name']], 
                    capture_output=True, text=True
                )
                is_enabled = result.stdout.strip() == 'enabled'
                
                # Get service status details
                result = subprocess.run(
                    ['systemctl', 'status', service['name']], 
                    capture_output=True, text=True
                )
                
                status_list.append({
                    'name': service['name'],
                    'description': service['description'],
                    'is_active': is_active,
                    'is_enabled': is_enabled,
                    'status': 'running' if is_active else 'stopped',
                    'uptime': self._get_service_uptime(service['name']) if is_active else None,
                })
                
            except Exception as e:
                logger.error(f"Error getting status for service {service['name']}: {e}")
                status_list.append({
                    'name': service['name'],
                    'description': service['description'],
                    'is_active': False,
                    'is_enabled': False,
                    'status': 'error',
                    'error': str(e),
                })
        
        return status_list

    def _get_service_uptime(self, service_name: str) -> str:
        """Get service uptime"""
        try:
            result = subprocess.run(
                ['systemctl', 'show', service_name, '--property=ActiveEnterTimestamp'], 
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                timestamp_line = result.stdout.strip()
                if '=' in timestamp_line:
                    timestamp_str = timestamp_line.split('=', 1)[1]
                    if timestamp_str and timestamp_str != 'n/a':
                        start_time = datetime.strptime(timestamp_str, '%a %Y-%m-%d %H:%M:%S %Z')
                        uptime = datetime.now() - start_time
                        return str(uptime).split('.')[0]
            
            return 'Unknown'
            
        except Exception as e:
            logger.error(f"Error getting uptime for {service_name}: {e}")
            return 'Unknown'

    def control_service(self, service_name: str, action: str) -> Dict[str, Any]:
        """Control a system service"""
        valid_actions = ['start', 'stop', 'restart', 'reload', 'enable', 'disable']
        
        if action not in valid_actions:
            raise ValueError(f"Invalid action: {action}")
        
        try:
            result = subprocess.run(
                ['systemctl', action, service_name], 
                capture_output=True, text=True
            )
            
            success = result.returncode == 0
            
            return {
                'success': success,
                'message': f"Service {service_name} {action}ed successfully" if success else result.stderr,
                'stdout': result.stdout,
                'stderr': result.stderr,
            }
            
        except Exception as e:
            logger.error(f"Error controlling service {service_name} ({action}): {e}")
            return {
                'success': False,
                'message': str(e),
            }

class SystemManager:
    """System management service"""

    def __init__(self):
        self.monitor = SystemMonitor()

    def get_system_overview(self) -> Dict[str, Any]:
        """Get complete system overview"""
        try:
            stats = self.monitor.get_system_stats()
            services = self.monitor.get_service_status()
            
            # Calculate overall health
            active_services = sum(1 for s in services if s['is_active'])
            total_services = len(services)
            service_health = (active_services / total_services) * 100 if total_services > 0 else 0
            
            # System health indicators
            cpu_health = 100 - stats['cpu']['percent']
            memory_health = 100 - stats['memory']['percent']
            
            overall_health = (service_health + cpu_health + memory_health) / 3
            
            return {
                'stats': stats,
                'services': services,
                'health': {
                    'overall': overall_health,
                    'cpu': cpu_health,
                    'memory': memory_health,
                    'services': service_health,
                    'status': 'healthy' if overall_health > 80 else 'warning' if overall_health > 60 else 'critical'
                },
                'summary': {
                    'active_services': active_services,
                    'total_services': total_services,
                    'cpu_usage': stats['cpu']['percent'],
                    'memory_usage': stats['memory']['percent'],
                    'disk_count': len(stats['disk']),
                    'uptime': stats['system']['uptime_seconds'],
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            raise