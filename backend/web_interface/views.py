from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.generic import TemplateView
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import os
import psutil
import platform
import json
import subprocess
import socket
import time
from datetime import datetime, timedelta

class MainDashboardView(View):
    """Main dashboard view for MoxNAS interface - serves frontend"""
    
    def get(self, request):
        """Serve the frontend index.html file"""
        frontend_path = os.path.join(settings.BASE_DIR.parent, 'frontend', 'index.html')
        try:
            with open(frontend_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HttpResponse(content, content_type='text/html')
        except FileNotFoundError:
            return HttpResponse('Frontend file not found', status=404)
    
    def get_context_data_old(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # System information
        context.update({
            'hostname': platform.node(),
            'system_version': 'MoxNAS 1.0.0',
            'uptime': self.get_uptime(),
            'load_average': self.get_load_average(),
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': self.get_memory_usage(),
            'storage_pools': self.get_storage_info(),
            'network_interfaces': self.get_network_info(),
            'active_services': self.get_services_status(),
            'recent_activity': self.get_recent_activity(),
            'system_alerts': self.get_system_alerts(),
        })
        
        return context
    
    def get_uptime(self):
        """Get system uptime"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = datetime.now().timestamp() - boot_time
            uptime_delta = timedelta(seconds=uptime_seconds)
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{days}d {hours}h {minutes}m"
        except:
            return "Unknown"
    
    def get_load_average(self):
        """Get system load average"""
        try:
            load = os.getloadavg()
            return f"{load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"
        except:
            return "0.00, 0.00, 0.00"
    
    def get_memory_usage(self):
        """Get memory usage information"""
        try:
            memory = psutil.virtual_memory()
            return {
                'percent': memory.percent,
                'used': round(memory.used / (1024**3), 2),
                'total': round(memory.total / (1024**3), 2),
                'available': round(memory.available / (1024**3), 2)
            }
        except:
            return {'percent': 0, 'used': 0, 'total': 0, 'available': 0}
    
    def get_storage_info(self):
        """Get storage information"""
        try:
            pools = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    pools.append({
                        'name': partition.device,
                        'mountpoint': partition.mountpoint,
                        'total': round(usage.total / (1024**3), 2),
                        'used': round(usage.used / (1024**3), 2),
                        'free': round(usage.free / (1024**3), 2),
                        'percent': round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0,
                        'status': 'Online'
                    })
                except (PermissionError, OSError):
                    continue
            return pools
        except:
            return []
    
    def get_network_info(self):
        """Get network interfaces information"""
        try:
            interfaces = []
            stats = psutil.net_io_counters(pernic=True)
            addrs = psutil.net_if_addrs()
            
            for interface, addresses in addrs.items():
                if interface.startswith('lo'):
                    continue
                    
                ip_address = 'N/A'
                for addr in addresses:
                    if addr.family == 2:  # IPv4
                        ip_address = addr.address
                        break
                
                interface_stats = stats.get(interface)
                interfaces.append({
                    'name': interface,
                    'ip': ip_address,
                    'status': 'Up' if interface_stats else 'Down',
                    'bytes_sent': round(interface_stats.bytes_sent / (1024**2), 2) if interface_stats else 0,
                    'bytes_recv': round(interface_stats.bytes_recv / (1024**2), 2) if interface_stats else 0
                })
            
            return interfaces
        except:
            return []
    
    def get_services_status(self):
        """Get active services status"""
        # Mock data for now - in real implementation, check actual services
        return [
            {'name': 'SSH', 'status': 'Running', 'port': 22},
            {'name': 'HTTP', 'status': 'Running', 'port': 80},
            {'name': 'HTTPS', 'status': 'Running', 'port': 443},
            {'name': 'NFS', 'status': 'Stopped', 'port': 2049},
            {'name': 'SMB', 'status': 'Running', 'port': 445},
        ]
    
    def get_recent_activity(self):
        """Get recent system activity"""
        # Mock data for now - in real implementation, read from logs
        return [
            {
                'timestamp': datetime.now() - timedelta(minutes=5),
                'type': 'System',
                'action': 'User login',
                'details': 'admin logged in from 192.168.1.100'
            },
            {
                'timestamp': datetime.now() - timedelta(minutes=15),
                'type': 'Storage',
                'action': 'Pool scrub completed',
                'details': 'tank pool scrub finished successfully'
            },
            {
                'timestamp': datetime.now() - timedelta(hours=1),
                'type': 'Network',
                'action': 'Interface status change',
                'details': 'eth0 interface went up'
            },
            {
                'timestamp': datetime.now() - timedelta(hours=2),
                'type': 'System',
                'action': 'Service restart',
                'details': 'SMB service restarted'
            },
        ]
    
    def get_system_alerts(self):
        """Get system alerts"""
        # Mock data for now - in real implementation, check actual system status
        alerts = []
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            alerts.append({
                'level': 'warning',
                'message': f'High memory usage: {memory.percent:.1f}%',
                'timestamp': datetime.now()
            })
        
        # Check disk usage
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                percent = (usage.used / usage.total) * 100
                if percent > 85:
                    alerts.append({
                        'level': 'critical',
                        'message': f'High disk usage on {partition.mountpoint}: {percent:.1f}%',
                        'timestamp': datetime.now()
                    })
            except (PermissionError, OSError):
                continue
        
        return alerts

def main_dashboard(request):
    """Main dashboard function view (legacy)"""
    context = {
        'title': 'MoxNAS Dashboard',
        'version': '1.0.0',
    }
    return render(request, 'web_interface/dashboard.html', context)

def api_status(request):
    """API status endpoint"""
    return JsonResponse({
        'status': 'online',
        'version': '1.0.0',
        'services': {
            'web': True,
            'api': True,
            'database': True
        }
    })

def api_system_info(request):
    """API endpoint for system information"""
    try:
        memory = psutil.virtual_memory()
        data = {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': {
                'percent': memory.percent,
                'used': round(memory.used / (1024**3), 2),
                'total': round(memory.total / (1024**3), 2),
                'available': round(memory.available / (1024**3), 2)
            },
            'load_average': list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0, 0, 0],
            'timestamp': datetime.now().isoformat()
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class SystemAPIView(View):
    """Enhanced API view for system monitoring data"""
    
    def get(self, request):
        """Get comprehensive system information"""
        try:
            data = {
                'system_info': self.get_enhanced_system_info(),
                'cpu_info': self.get_cpu_info(),
                'memory_info': self.get_enhanced_memory_info(),
                'storage_pools': self.get_enhanced_storage_info(),
                'network_interfaces': self.get_enhanced_network_info(),
                'services': self.get_enhanced_services_status(),
                'alerts': self.get_enhanced_system_alerts(),
                'timestamp': datetime.now().isoformat()
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def get_enhanced_system_info(self):
        """Get enhanced system information"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = datetime.now().timestamp() - boot_time
            uptime_delta = timedelta(seconds=uptime_seconds)
            
            # Get CPU temperature if available
            cpu_temp = self.get_cpu_temperature()
            
            # Get active users
            active_users = len(psutil.users())
            
            # Get running processes count
            running_processes = len(psutil.pids())
            
            return {
                'hostname': platform.node(),
                'version': 'MoxNAS 1.0.0 (TrueNAS-inspired)',
                'uptime': f"{uptime_delta.days}d {uptime_delta.seconds//3600}h {(uptime_delta.seconds%3600)//60}m",
                'uptime_seconds': int(uptime_seconds),
                'load_average': self.get_load_average(),
                'temperature': cpu_temp,
                'active_users': active_users,
                'running_processes': running_processes,
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'machine': platform.machine(),
                    'processor': platform.processor()
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_cpu_info(self):
        """Get detailed CPU information"""
        try:
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_freq = psutil.cpu_freq()
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            
            return {
                'usage_percent': sum(cpu_percent) / len(cpu_percent),
                'usage_per_core': cpu_percent,
                'cores_physical': cpu_count,
                'cores_logical': cpu_count_logical,
                'frequency': {
                    'current': cpu_freq.current if cpu_freq else 0,
                    'min': cpu_freq.min if cpu_freq else 0,
                    'max': cpu_freq.max if cpu_freq else 0
                },
                'model': platform.processor() or 'Unknown',
                'temperature': self.get_cpu_temperature()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_enhanced_memory_info(self):
        """Get enhanced memory information"""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total': round(memory.total / (1024**3), 2),
                'available': round(memory.available / (1024**3), 2),
                'used': round(memory.used / (1024**3), 2),
                'free': round(memory.free / (1024**3), 2),
                'cached': round(getattr(memory, 'cached', 0) / (1024**3), 2),
                'buffers': round(getattr(memory, 'buffers', 0) / (1024**3), 2),
                'percent': memory.percent,
                'swap': {
                    'total': round(swap.total / (1024**3), 2),
                    'used': round(swap.used / (1024**3), 2),
                    'free': round(swap.free / (1024**3), 2),
                    'percent': swap.percent
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_enhanced_storage_info(self):
        """Get enhanced storage pool information"""
        try:
            pools = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    if usage.total == 0:
                        continue
                    
                    # Mock additional pool data for TrueNAS-style display
                    pool_health = 'ONLINE'
                    if usage.used / usage.total > 0.9:
                        pool_health = 'CRITICAL'
                    elif usage.used / usage.total > 0.8:
                        pool_health = 'DEGRADED'
                    
                    pools.append({
                        'name': partition.device.split('/')[-1] if '/' in partition.device else partition.device,
                        'mountpoint': partition.mountpoint,
                        'filesystem': partition.fstype,
                        'total': round(usage.total / (1024**3), 2),
                        'used': round(usage.used / (1024**3), 2),
                        'free': round(usage.free / (1024**3), 2),
                        'percent': round((usage.used / usage.total) * 100, 1),
                        'health': pool_health,
                        'disks': 1,  # Mock data
                        'type': 'Single',  # Mock data
                        'compression': 'On',  # Mock data
                        'deduplication': 'Off'  # Mock data
                    })
                except (PermissionError, OSError):
                    continue
            return pools
        except Exception as e:
            return {'error': str(e)}
    
    def get_enhanced_network_info(self):
        """Get enhanced network interfaces information"""
        try:
            interfaces = []
            stats = psutil.net_io_counters(pernic=True)
            addrs = psutil.net_if_addrs()
            
            for interface, addresses in addrs.items():
                if interface.startswith('lo'):
                    continue
                
                ip_address = 'N/A'
                netmask = 'N/A'
                for addr in addresses:
                    if addr.family == 2:  # IPv4
                        ip_address = addr.address
                        netmask = addr.netmask
                        break
                
                interface_stats = stats.get(interface)
                
                # Try to get interface speed and duplex (mock data for now)
                speed = '1000 Mbps'  # Mock data
                duplex = 'Full'  # Mock data
                
                interfaces.append({
                    'name': interface,
                    'ip': ip_address,
                    'netmask': netmask,
                    'status': 'up' if interface_stats and interface_stats.bytes_recv > 0 else 'down',
                    'speed': speed,
                    'duplex': duplex,
                    'mtu': 1500,  # Mock data
                    'statistics': {
                        'bytes_sent': interface_stats.bytes_sent if interface_stats else 0,
                        'bytes_recv': interface_stats.bytes_recv if interface_stats else 0,
                        'packets_sent': interface_stats.packets_sent if interface_stats else 0,
                        'packets_recv': interface_stats.packets_recv if interface_stats else 0,
                        'errors_in': interface_stats.errin if interface_stats else 0,
                        'errors_out': interface_stats.errout if interface_stats else 0,
                        'drops_in': interface_stats.dropin if interface_stats else 0,
                        'drops_out': interface_stats.dropout if interface_stats else 0
                    }
                })
            
            return interfaces
        except Exception as e:
            return {'error': str(e)}
    
    def get_enhanced_services_status(self):
        """Get enhanced services status"""
        try:
            services = []
            
            # Common services to check
            service_list = [
                {'name': 'SSH', 'port': 22, 'description': 'Secure Shell daemon'},
                {'name': 'HTTP', 'port': 80, 'description': 'Web server'},
                {'name': 'HTTPS', 'port': 443, 'description': 'Secure web server'},
                {'name': 'NFS', 'port': 2049, 'description': 'Network File System'},
                {'name': 'SMB/CIFS', 'port': 445, 'description': 'Samba file sharing'},
                {'name': 'FTP', 'port': 21, 'description': 'File Transfer Protocol'},
                {'name': 'DNS', 'port': 53, 'description': 'Domain Name System'},
                {'name': 'DHCP', 'port': 67, 'description': 'Dynamic Host Configuration'},
            ]
            
            for service in service_list:
                status = self.check_port_status(service['port'])
                services.append({
                    'name': service['name'],
                    'description': service['description'],
                    'status': 'running' if status else 'stopped',
                    'port': service['port'],
                    'enabled': True,  # Mock data
                    'autostart': True  # Mock data
                })
            
            return services
        except Exception as e:
            return {'error': str(e)}
    
    def get_enhanced_system_alerts(self):
        """Get enhanced system alerts"""
        try:
            alerts = []
            
            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                alerts.append({
                    'id': 'mem_critical',
                    'level': 'critical',
                    'title': 'Critical Memory Usage',
                    'message': f'Memory usage is critically high: {memory.percent:.1f}%',
                    'timestamp': datetime.now().isoformat(),
                    'source': 'System Monitor'
                })
            elif memory.percent > 80:
                alerts.append({
                    'id': 'mem_warning',
                    'level': 'warning',
                    'title': 'High Memory Usage',
                    'message': f'Memory usage is high: {memory.percent:.1f}%',
                    'timestamp': datetime.now().isoformat(),
                    'source': 'System Monitor'
                })
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                alerts.append({
                    'id': 'cpu_critical',
                    'level': 'critical',
                    'title': 'Critical CPU Usage',
                    'message': f'CPU usage is critically high: {cpu_percent:.1f}%',
                    'timestamp': datetime.now().isoformat(),
                    'source': 'System Monitor'
                })
            
            # Check disk usage
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    if usage.total == 0:
                        continue
                    percent = (usage.used / usage.total) * 100
                    if percent > 95:
                        alerts.append({
                            'id': f'disk_critical_{partition.mountpoint}',
                            'level': 'critical',
                            'title': 'Critical Disk Usage',
                            'message': f'Disk usage on {partition.mountpoint} is critically high: {percent:.1f}%',
                            'timestamp': datetime.now().isoformat(),
                            'source': 'Storage Monitor'
                        })
                    elif percent > 85:
                        alerts.append({
                            'id': f'disk_warning_{partition.mountpoint}',
                            'level': 'warning',
                            'title': 'High Disk Usage',
                            'message': f'Disk usage on {partition.mountpoint} is high: {percent:.1f}%',
                            'timestamp': datetime.now().isoformat(),
                            'source': 'Storage Monitor'
                        })
                except (PermissionError, OSError):
                    continue
            
            # Check CPU temperature
            cpu_temp = self.get_cpu_temperature()
            if cpu_temp and cpu_temp > 80:
                alerts.append({
                    'id': 'temp_warning',
                    'level': 'warning',
                    'title': 'High CPU Temperature',
                    'message': f'CPU temperature is high: {cpu_temp}°C',
                    'timestamp': datetime.now().isoformat(),
                    'source': 'Temperature Monitor'
                })
            
            return alerts
        except Exception as e:
            return {'error': str(e)}
    
    def get_cpu_temperature(self):
        """Get CPU temperature"""
        try:
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    return round(temps['coretemp'][0].current, 1)
                elif 'cpu_thermal' in temps:
                    return round(temps['cpu_thermal'][0].current, 1)
            return None
        except:
            return None
    
    def get_load_average(self):
        """Get system load average"""
        try:
            if hasattr(os, 'getloadavg'):
                load = os.getloadavg()
                return {
                    '1min': round(load[0], 2),
                    '5min': round(load[1], 2),
                    '15min': round(load[2], 2)
                }
            return {'1min': 0, '5min': 0, '15min': 0}
        except:
            return {'1min': 0, '5min': 0, '15min': 0}
    
    def check_port_status(self, port):
        """Check if a port is open/listening"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False

class TaskManagerAPIView(View):
    """API view for task management"""
    
    def get(self, request):
        """Get active tasks"""
        try:
            # Mock tasks for demonstration
            tasks = [
                {
                    'id': 'task_001',
                    'title': 'Pool Scrub - tank',
                    'description': 'Scrubbing ZFS pool for errors',
                    'status': 'running',
                    'progress': 65,
                    'started': (datetime.now() - timedelta(minutes=30)).isoformat(),
                    'estimated_completion': (datetime.now() + timedelta(minutes=15)).isoformat()
                },
                {
                    'id': 'task_002',
                    'title': 'Snapshot Creation',
                    'description': 'Creating dataset snapshots',
                    'status': 'completed',
                    'progress': 100,
                    'started': (datetime.now() - timedelta(hours=1)).isoformat(),
                    'completed': (datetime.now() - timedelta(minutes=45)).isoformat()
                }
            ]
            return JsonResponse({'tasks': tasks})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ServiceControlAPIView(View):
    """API view for service control"""
    
    def post(self, request):
        """Control services (start/stop/restart)"""
        try:
            data = json.loads(request.body)
            service = data.get('service')
            action = data.get('action')
            
            if not service or not action:
                return JsonResponse({'error': 'Service and action required'}, status=400)
            
            # Mock service control
            success = True  # In real implementation, execute actual service control
            
            return JsonResponse({
                'success': success,
                'service': service,
                'action': action,
                'message': f'Service {service} {action} {"successful" if success else "failed"}'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class RealtimeDataAPIView(View):
    """API view for real-time monitoring data"""
    
    def get(self, request):
        """Get real-time system metrics"""
        try:
            data = {
                'cpu_usage': psutil.cpu_percent(interval=0.1),
                'memory_usage': psutil.virtual_memory().percent,
                'timestamp': datetime.now().isoformat(),
                'load_average': list(os.getloadavg()) if hasattr(os, 'getloadavg') else [0, 0, 0],
                'active_connections': len(psutil.net_connections()),
                'disk_io': self.get_disk_io_stats(),
                'network_io': self.get_network_io_stats()
            }
            return JsonResponse(data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def get_disk_io_stats(self):
        """Get disk I/O statistics"""
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                return {
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes,
                    'read_count': disk_io.read_count,
                    'write_count': disk_io.write_count
                }
            return None
        except:
            return None
    
    def get_network_io_stats(self):
        """Get network I/O statistics"""
        try:
            net_io = psutil.net_io_counters()
            if net_io:
                return {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                }
            return None
        except:
            return None

class FormExampleView(TemplateView):
    """Example view to demonstrate enhanced form functionality"""
    template_name = 'form_example.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
