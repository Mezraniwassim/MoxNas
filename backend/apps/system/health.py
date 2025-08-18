"""
Health check utilities for MoxNAS system monitoring
"""

import os
import time
import psutil
import logging
from pathlib import Path
from django.db import connection
from django.conf import settings
from django.core.cache import cache
from apps.services.managers import samba_manager, nfs_manager, ftp_manager

logger = logging.getLogger(__name__)


class HealthChecker:
    """Comprehensive health check system for MoxNAS"""
    
    def __init__(self):
        self.checks = {}
        self.start_time = time.time()
    
    def run_all_checks(self):
        """Run all health checks and return results"""
        checks = {
            'database': self.check_database,
            'services': self.check_services,
            'storage': self.check_storage,
            'system': self.check_system,
            'cache': self.check_cache,
            'network': self.check_network,
        }
        
        results = {}
        overall_status = 'healthy'
        
        for check_name, check_func in checks.items():
            try:
                result = check_func()
                results[check_name] = result
                
                if result['status'] == 'critical':
                    overall_status = 'critical'
                elif result['status'] == 'warning' and overall_status == 'healthy':
                    overall_status = 'warning'
                    
            except Exception as e:
                logger.error(f"Health check {check_name} failed: {e}")
                results[check_name] = {
                    'status': 'critical',
                    'message': f'Health check failed: {str(e)}',
                    'details': {}
                }
                overall_status = 'critical'
        
        return {
            'status': overall_status,
            'timestamp': time.time(),
            'uptime': time.time() - self.start_time,
            'checks': results
        }
    
    def check_database(self):
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            if response_time > 1000:  # > 1 second
                status = 'critical'
                message = f'Database response time is slow: {response_time:.2f}ms'
            elif response_time > 500:  # > 500ms
                status = 'warning'
                message = f'Database response time is elevated: {response_time:.2f}ms'
            else:
                status = 'healthy'
                message = f'Database is responsive: {response_time:.2f}ms'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'response_time_ms': round(response_time, 2),
                    'vendor': connection.vendor,
                    'queries': len(connection.queries) if settings.DEBUG else None
                }
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'message': f'Database connection failed: {str(e)}',
                'details': {}
            }
    
    def check_services(self):
        """Check status of NAS services"""
        services = {
            'samba': samba_manager,
            'nfs': nfs_manager,
            'ftp': ftp_manager
        }
        
        service_status = {}
        critical_down = 0
        warning_issues = 0
        
        for service_name, manager in services.items():
            try:
                status = manager.status()
                service_status[service_name] = status
                
                if not status['active']:
                    critical_down += 1
                elif not status['enabled']:
                    warning_issues += 1
                    
            except Exception as e:
                service_status[service_name] = {
                    'active': False,
                    'enabled': False,
                    'status': 'error',
                    'error': str(e)
                }
                critical_down += 1
        
        if critical_down > 0:
            status = 'critical'
            message = f'{critical_down} services are down'
        elif warning_issues > 0:
            status = 'warning'
            message = f'{warning_issues} services have configuration issues'
        else:
            status = 'healthy'
            message = 'All services are running normally'
        
        return {
            'status': status,
            'message': message,
            'details': service_status
        }
    
    def check_storage(self):
        """Check storage space and mount points"""
        try:
            storage_issues = []
            mount_points = []
            
            # Check main storage areas
            paths_to_check = [
                '/',  # Root filesystem
                '/opt/moxnas',  # Application directory
                '/var/log',  # Log directory
                '/mnt/storage',  # Storage mount point
            ]
            
            for path in paths_to_check:
                if os.path.exists(path):
                    usage = psutil.disk_usage(path)
                    percent_used = (usage.used / usage.total) * 100
                    
                    mount_info = {
                        'path': path,
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2),
                        'percent_used': round(percent_used, 1)
                    }
                    mount_points.append(mount_info)
                    
                    if percent_used > 95:
                        storage_issues.append(f'{path}: {percent_used:.1f}% full (critical)')
                    elif percent_used > 80:
                        storage_issues.append(f'{path}: {percent_used:.1f}% full (warning)')
            
            if any('critical' in issue for issue in storage_issues):
                status = 'critical'
                message = 'Critical storage space issues detected'
            elif storage_issues:
                status = 'warning'
                message = 'Storage space warnings detected'
            else:
                status = 'healthy'
                message = 'Storage space is adequate'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'mount_points': mount_points,
                    'issues': storage_issues
                }
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'message': f'Storage check failed: {str(e)}',
                'details': {}
            }
    
    def check_system(self):
        """Check system resources (CPU, memory, etc.)"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Load average
            load_avg = os.getloadavg()
            cpu_count = psutil.cpu_count()
            load_avg_percent = (load_avg[0] / cpu_count) * 100
            
            # Process count
            process_count = len(psutil.pids())
            
            issues = []
            
            if cpu_percent > 90:
                issues.append(f'High CPU usage: {cpu_percent}%')
            elif cpu_percent > 80:
                issues.append(f'Elevated CPU usage: {cpu_percent}%')
            
            if memory_percent > 90:
                issues.append(f'High memory usage: {memory_percent}%')
            elif memory_percent > 80:
                issues.append(f'Elevated memory usage: {memory_percent}%')
            
            if load_avg_percent > 100:
                issues.append(f'High system load: {load_avg[0]:.2f}')
            
            if any('High' in issue for issue in issues):
                status = 'critical'
                message = 'Critical system resource usage'
            elif issues:
                status = 'warning'
                message = 'Elevated system resource usage'
            else:
                status = 'healthy'
                message = 'System resources are normal'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'load_average': load_avg,
                    'process_count': process_count,
                    'issues': issues
                }
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'message': f'System check failed: {str(e)}',
                'details': {}
            }
    
    def check_cache(self):
        """Check cache system (Redis) if available"""
        try:
            # Test cache connectivity
            cache_key = 'health_check_test'
            test_value = str(time.time())
            
            cache.set(cache_key, test_value, timeout=60)
            retrieved_value = cache.get(cache_key)
            
            if retrieved_value == test_value:
                status = 'healthy'
                message = 'Cache system is working'
                cache.delete(cache_key)
            else:
                status = 'warning'
                message = 'Cache system may have issues'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown')
                }
            }
            
        except Exception as e:
            return {
                'status': 'warning',
                'message': f'Cache check failed: {str(e)}',
                'details': {}
            }
    
    def check_network(self):
        """Check network connectivity and interfaces"""
        try:
            network_interfaces = []
            network_issues = []
            
            # Get network interface information
            interfaces = psutil.net_if_addrs()
            interface_stats = psutil.net_if_stats()
            
            for interface, addresses in interfaces.items():
                if interface == 'lo':  # Skip loopback
                    continue
                
                stats = interface_stats.get(interface, {})
                
                interface_info = {
                    'name': interface,
                    'is_up': stats.isup if hasattr(stats, 'isup') else False,
                    'addresses': []
                }
                
                for addr in addresses:
                    if addr.family.name in ['AF_INET', 'AF_INET6']:
                        interface_info['addresses'].append({
                            'family': addr.family.name,
                            'address': addr.address,
                            'netmask': addr.netmask
                        })
                
                network_interfaces.append(interface_info)
                
                if not interface_info['is_up']:
                    network_issues.append(f'Interface {interface} is down')
                elif not interface_info['addresses']:
                    network_issues.append(f'Interface {interface} has no IP address')
            
            if network_issues:
                status = 'warning'
                message = 'Network interface issues detected'
            else:
                status = 'healthy'
                message = 'Network interfaces are functioning'
            
            return {
                'status': status,
                'message': message,
                'details': {
                    'interfaces': network_interfaces,
                    'issues': network_issues
                }
            }
            
        except Exception as e:
            return {
                'status': 'warning',
                'message': f'Network check failed: {str(e)}',
                'details': {}
            }


# Global health checker instance
health_checker = HealthChecker()