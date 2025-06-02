from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
import psutil
import subprocess
import time
import socket
import platform
from pathlib import Path
from .models import SystemInfo, SystemService, CronJob, SyncTask, UPSConfig, SNMPConfig


class SystemMonitoringService:
    """Service for system monitoring and management"""
    
    @staticmethod
    def get_real_time_stats():
        """Get real-time system statistics"""
        try:
            # CPU information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            load_avg = psutil.getloadavg()
            
            # Memory information
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk information
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            # Network information
            network_io = psutil.net_io_counters()
            network_connections = len(psutil.net_connections())
            
            # System information
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
            
            # Process information
            process_count = len(psutil.pids())
            
            return {
                'timestamp': time.time(),
                'cpu': {
                    'usage_percent': cpu_percent,
                    'count': cpu_count,
                    'frequency': cpu_freq._asdict() if cpu_freq else None,
                    'load_average': list(load_avg)
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'percent': memory.percent,
                    'swap_total': swap.total,
                    'swap_used': swap.used,
                    'swap_percent': swap.percent
                },
                'disk': {
                    'total': disk_usage.total,
                    'used': disk_usage.used,
                    'free': disk_usage.free,
                    'percent': (disk_usage.used / disk_usage.total) * 100,
                    'io_read_bytes': disk_io.read_bytes if disk_io else 0,
                    'io_write_bytes': disk_io.write_bytes if disk_io else 0
                },
                'network': {
                    'bytes_sent': network_io.bytes_sent,
                    'bytes_recv': network_io.bytes_recv,
                    'packets_sent': network_io.packets_sent,
                    'packets_recv': network_io.packets_recv,
                    'connections': network_connections
                },
                'system': {
                    'hostname': socket.gethostname(),
                    'platform': platform.platform(),
                    'uptime_seconds': uptime,
                    'process_count': process_count,
                    'boot_time': boot_time
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def get_service_status(service_name):
        """Get status of a specific system service"""
        try:
            result = subprocess.run([
                'systemctl', 'is-active', service_name
            ], capture_output=True, text=True, check=False)
            
            active = result.stdout.strip() == 'active'
            
            # Get more detailed info
            status_result = subprocess.run([
                'systemctl', 'status', service_name, '--no-pager', '-l'
            ], capture_output=True, text=True, check=False)
            
            return {
                'name': service_name,
                'active': active,
                'status': result.stdout.strip(),
                'details': status_result.stdout
            }
        except Exception as e:
            return {
                'name': service_name,
                'active': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_all_services():
        """Get status of all system services"""
        try:
            result = subprocess.run([
                'systemctl', 'list-units', '--type=service', '--no-pager'
            ], capture_output=True, text=True, check=True)
            
            services = []
            for line in result.stdout.split('\n')[1:]:  # Skip header
                if line.strip() and not line.startswith('●'):
                    parts = line.split()
                    if len(parts) >= 4:
                        services.append({
                            'unit': parts[0],
                            'load': parts[1],
                            'active': parts[2],
                            'sub': parts[3],
                            'description': ' '.join(parts[4:]) if len(parts) > 4 else ''
                        })
            return services
        except Exception as e:
            return []
    
    @staticmethod
    def manage_service(service_name, action):
        """Manage a system service (start, stop, restart, enable, disable)"""
        valid_actions = ['start', 'stop', 'restart', 'enable', 'disable', 'reload']
        if action not in valid_actions:
            return {'success': False, 'message': f'Invalid action. Use: {", ".join(valid_actions)}'}
        
        try:
            result = subprocess.run([
                'systemctl', action, service_name
            ], capture_output=True, text=True, check=True)
            
            return {
                'success': True,
                'message': f'Service {service_name} {action}ed successfully',
                'output': result.stdout
            }
        except subprocess.CalledProcessError as e:
            return {
                'success': False,
                'message': f'Failed to {action} {service_name}: {e.stderr}'
            }
    
    @staticmethod
    def get_log_entries(service_name=None, lines=100):
        """Get system log entries"""
        try:
            cmd = ['journalctl', '--no-pager', '-n', str(lines)]
            if service_name:
                cmd.extend(['-u', service_name])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            entries = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    entries.append(line)
            
            return entries
        except Exception as e:
            return []
    
    @staticmethod
    def get_disk_info():
        """Get detailed disk information"""
        disks = []
        try:
            # Get all disk partitions
            partitions = psutil.disk_partitions()
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
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
        except Exception:
            pass
        
        return disks
    
    @staticmethod
    def get_network_interfaces():
        """Get network interface information"""
        interfaces = []
        try:
            stats = psutil.net_if_stats()
            addrs = psutil.net_if_addrs()
            
            for interface_name, interface_stats in stats.items():
                interface_addrs = addrs.get(interface_name, [])
                
                # Get IP addresses
                ipv4_addrs = [addr.address for addr in interface_addrs if addr.family == socket.AF_INET]
                ipv6_addrs = [addr.address for addr in interface_addrs if addr.family == socket.AF_INET6]
                
                interfaces.append({
                    'name': interface_name,
                    'is_up': interface_stats.isup,
                    'duplex': interface_stats.duplex.name if interface_stats.duplex else 'unknown',
                    'speed': interface_stats.speed,
                    'mtu': interface_stats.mtu,
                    'ipv4_addresses': ipv4_addrs,
                    'ipv6_addresses': ipv6_addrs
                })
        except Exception:
            pass
        
        return interfaces

    @staticmethod
    def get_log_entries(service_name=None, lines=100):
        """Get system log entries"""
        try:
            if service_name:
                # Get logs for specific service
                cmd = ['journalctl', '-u', service_name, '-n', str(lines), '--no-pager']
            else:
                # Get system logs
                cmd = ['journalctl', '-n', str(lines), '--no-pager']
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                log_lines = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        # Parse journalctl output format
                        parts = line.split(' ', 5)
                        if len(parts) >= 6:
                            log_lines.append({
                                'timestamp': f"{parts[0]} {parts[1]} {parts[2]}",
                                'hostname': parts[3],
                                'service': parts[4].rstrip(':'),
                                'message': parts[5]
                            })
                        else:
                            # Fallback for unparseable lines
                            log_lines.append({
                                'timestamp': '',
                                'hostname': '',
                                'service': service_name or 'system',
                                'message': line
                            })
                return log_lines
            else:
                return [{'timestamp': '', 'hostname': '', 'service': 'error', 'message': f'Failed to get logs: {result.stderr}'}]
                
        except Exception as e:
            return [{'timestamp': '', 'hostname': '', 'service': 'error', 'message': f'Error getting logs: {str(e)}'}]


@api_view(['GET'])
def system_logs(request):
    """Get system log entries"""
    try:
        service_name = request.GET.get('service')
        lines = int(request.GET.get('lines', 100))
        
        logs = SystemMonitoringService.get_log_entries(service_name, lines)
        return JsonResponse({'logs': logs})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SystemServiceViewSet(viewsets.ModelViewSet):
    queryset = SystemService.objects.all()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitoring_service = SystemMonitoringService()
    
    def list(self, request):
        services = self.get_queryset()
        data = [
            {
                'id': service.id,
                'name': service.name,
                'description': service.description,
                'status': service.status,
                'enabled': service.enabled,
                'pid': service.pid
            } for service in services
        ]
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def system_services(self, request):
        """Get all system services"""
        services = self.monitoring_service.get_all_services()
        return Response(services)
    
    @action(detail=False, methods=['post'])
    def manage_service(self, request):
        """Manage a system service"""
        service_name = request.data.get('service_name')
        action = request.data.get('action')
        
        if not service_name or not action:
            return Response({'error': 'service_name and action required'}, status=400)
        
        result = self.monitoring_service.manage_service(service_name, action)
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def service_status(self, request):
        """Get status of specific service"""
        service_name = request.query_params.get('name')
        if not service_name:
            return Response({'error': 'service name required'}, status=400)
        
        status_info = self.monitoring_service.get_service_status(service_name)
        return Response(status_info)


@method_decorator(csrf_exempt, name='dispatch')
class SystemStatsViewSet(viewsets.ViewSet):
    """ViewSet for real-time system statistics"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitoring_service = SystemMonitoringService()
    
    def list(self, request):
        """Get current system statistics"""
        stats = self.monitoring_service.get_real_time_stats()
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def disk_info(self, request):
        """Get detailed disk information"""
        disks = self.monitoring_service.get_disk_info()
        return Response(disks)
    
    @action(detail=False, methods=['get'])
    def network_interfaces(self, request):
        """Get network interface information"""
        interfaces = self.monitoring_service.get_network_interfaces()
        return Response(interfaces)
    
    @action(detail=False, methods=['get'])
    def system_logs(self, request):
        """Get system log entries"""
        service_name = request.query_params.get('service')
        lines = int(request.query_params.get('lines', 100))
        
        logs = self.monitoring_service.get_log_entries(service_name, lines)
        return Response({'logs': logs})


@method_decorator(csrf_exempt, name='dispatch')
class CronJobViewSet(viewsets.ModelViewSet):
    queryset = CronJob.objects.all()
    
    def list(self, request):
        jobs = self.get_queryset()
        data = [
            {
                'id': job.id,
                'name': job.name,
                'command': job.command,
                'schedule': job.schedule,
                'enabled': job.enabled,
                'description': job.description
            } for job in jobs
        ]
        return Response(data)


@method_decorator(csrf_exempt, name='dispatch')
class SyncTaskViewSet(viewsets.ModelViewSet):
    queryset = SyncTask.objects.all()
    
    def list(self, request):
        tasks = self.get_queryset()
        data = [
            {
                'id': task.id,
                'name': task.name,
                'sync_type': task.sync_type,
                'source_path': task.source_path,
                'destination_path': task.destination_path,
                'schedule': task.schedule,
                'enabled': task.enabled,
                'status': task.status,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None
            } for task in tasks
        ]
        return Response(data)


@csrf_exempt
@api_view(['GET'])
def system_info(request):
    """Get system information"""
    try:
        info = SystemInfo.objects.first()
        if info:
            data = {
                'hostname': info.hostname,
                'kernel_version': info.kernel_version,
                'uptime': info.uptime,
                'load_average': info.load_average,
                'cpu_usage': info.cpu_usage,
                'memory_total': info.memory_total,
                'memory_used': info.memory_used,
                'memory_usage': info.memory_usage,
                'disk_usage': info.disk_usage,
                'network_rx_bytes': info.network_rx_bytes,
                'network_tx_bytes': info.network_tx_bytes,
                'temperature': info.temperature
            }
        else:
            # Default data if no system info exists
            data = {
                'hostname': 'moxnas-container',
                'kernel_version': '5.15.0-generic',
                'uptime': '1 day, 2:30:45',
                'load_average': '0.25, 0.20, 0.15',
                'cpu_usage': 12.5,
                'memory_total': 8589934592,  # 8GB
                'memory_used': 2147483648,   # 2GB
                'memory_usage': 25.0,
                'disk_usage': 45.2,
                'network_rx_bytes': 1048576000,  # 1GB
                'network_tx_bytes': 524288000,   # 500MB
                'temperature': 42.0
            }
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


def system_dashboard(request):
    """System management dashboard"""
    data = {
        'title': 'System Management',
        'features': ['Services', 'Cron Jobs', 'UPS', 'SNMP'],
    }
    return JsonResponse(data)
