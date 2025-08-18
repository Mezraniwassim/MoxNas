"""
Performance metrics collection and export for MoxNAS
"""

import time
import psutil
import logging
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from apps.services.managers import samba_manager, nfs_manager, ftp_manager

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and format performance metrics for monitoring systems"""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
    
    def collect_all_metrics(self):
        """Collect all metrics and return in Prometheus format"""
        metrics = []
        
        # System metrics
        metrics.extend(self._collect_system_metrics())
        
        # Database metrics
        metrics.extend(self._collect_database_metrics())
        
        # Service metrics
        metrics.extend(self._collect_service_metrics())
        
        # Application metrics
        metrics.extend(self._collect_application_metrics())
        
        # Cache metrics
        metrics.extend(self._collect_cache_metrics())
        
        return '\n'.join(metrics)
    
    def _collect_system_metrics(self):
        """Collect system resource metrics"""
        metrics = []
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(f'moxnas_cpu_usage_percent {cpu_percent}')
            
            # Load average
            load_avg = psutil.getloadavg()
            metrics.append(f'moxnas_load_average_1m {load_avg[0]}')
            metrics.append(f'moxnas_load_average_5m {load_avg[1]}')
            metrics.append(f'moxnas_load_average_15m {load_avg[2]}')
            
            # Memory metrics
            memory = psutil.virtual_memory()
            metrics.append(f'moxnas_memory_total_bytes {memory.total}')
            metrics.append(f'moxnas_memory_used_bytes {memory.used}')
            metrics.append(f'moxnas_memory_available_bytes {memory.available}')
            metrics.append(f'moxnas_memory_usage_percent {memory.percent}')
            
            # Swap metrics
            swap = psutil.swap_memory()
            metrics.append(f'moxnas_swap_total_bytes {swap.total}')
            metrics.append(f'moxnas_swap_used_bytes {swap.used}')
            metrics.append(f'moxnas_swap_usage_percent {swap.percent}')
            
            # Disk metrics
            disk_usage = psutil.disk_usage('/')
            metrics.append(f'moxnas_disk_total_bytes {disk_usage.total}')
            metrics.append(f'moxnas_disk_used_bytes {disk_usage.used}')
            metrics.append(f'moxnas_disk_free_bytes {disk_usage.free}')
            metrics.append(f'moxnas_disk_usage_percent {(disk_usage.used / disk_usage.total) * 100}')
            
            # Network metrics
            network_io = psutil.net_io_counters()
            metrics.append(f'moxnas_network_bytes_sent_total {network_io.bytes_sent}')
            metrics.append(f'moxnas_network_bytes_recv_total {network_io.bytes_recv}')
            metrics.append(f'moxnas_network_packets_sent_total {network_io.packets_sent}')
            metrics.append(f'moxnas_network_packets_recv_total {network_io.packets_recv}')
            
            # Process metrics
            process_count = len(psutil.pids())
            metrics.append(f'moxnas_process_count {process_count}')
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            metrics.append(f'moxnas_system_metrics_error 1')
        
        return metrics
    
    def _collect_database_metrics(self):
        """Collect database performance metrics"""
        metrics = []
        
        try:
            start_time = time.time()
            
            # Test database connection and response time
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            response_time = (time.time() - start_time) * 1000
            metrics.append(f'moxnas_database_response_time_ms {response_time}')
            
            # Database connection status
            metrics.append(f'moxnas_database_connections_active 1')
            
            # Query count (if DEBUG is True)
            if settings.DEBUG:
                query_count = len(connection.queries)
                metrics.append(f'moxnas_database_queries_total {query_count}')
            
            # Database vendor info
            vendor_map = {'sqlite': 1, 'postgresql': 2, 'mysql': 3}
            vendor_value = vendor_map.get(connection.vendor, 0)
            metrics.append(f'moxnas_database_vendor {{vendor="{connection.vendor}"}} {vendor_value}')
            
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
            metrics.append(f'moxnas_database_connection_error 1')
        
        return metrics
    
    def _collect_service_metrics(self):
        """Collect NAS service metrics"""
        metrics = []
        
        services = {
            'samba': samba_manager,
            'nfs': nfs_manager,
            'ftp': ftp_manager
        }
        
        for service_name, manager in services.items():
            try:
                status = manager.status()
                
                # Service status (1 = active, 0 = inactive)
                active_value = 1 if status['active'] else 0
                metrics.append(f'moxnas_service_active {{service="{service_name}"}} {active_value}')
                
                # Service enabled (1 = enabled, 0 = disabled)
                enabled_value = 1 if status['enabled'] else 0
                metrics.append(f'moxnas_service_enabled {{service="{service_name}"}} {enabled_value}')
                
            except Exception as e:
                logger.error(f"Error collecting metrics for {service_name}: {e}")
                metrics.append(f'moxnas_service_error {{service="{service_name}"}} 1')
        
        return metrics
    
    def _collect_application_metrics(self):
        """Collect application-specific metrics"""
        metrics = []
        
        try:
            # Application uptime
            uptime = time.time() - self.start_time
            metrics.append(f'moxnas_uptime_seconds {uptime}')
            
            # Request counters (would be incremented by middleware)
            metrics.append(f'moxnas_requests_total {self.request_count}')
            metrics.append(f'moxnas_errors_total {self.error_count}')
            
            # Django version
            from django import VERSION as DJANGO_VERSION
            django_version = f"{DJANGO_VERSION[0]}.{DJANGO_VERSION[1]}.{DJANGO_VERSION[2]}"
            metrics.append(f'moxnas_django_version {{version="{django_version}"}} 1')
            
            # Python version
            import sys
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            metrics.append(f'moxnas_python_version {{version="{python_version}"}} 1')
            
            # Model counts (example for shares)
            try:
                from apps.shares.models import SMBShare, NFSShare
                smb_count = SMBShare.objects.count()
                nfs_count = NFSShare.objects.count()
                
                metrics.append(f'moxnas_smb_shares_total {smb_count}')
                metrics.append(f'moxnas_nfs_shares_total {nfs_count}')
                
                # Active shares
                smb_active = SMBShare.objects.filter(enabled=True).count()
                nfs_active = NFSShare.objects.filter(enabled=True).count()
                
                metrics.append(f'moxnas_smb_shares_active {smb_active}')
                metrics.append(f'moxnas_nfs_shares_active {nfs_active}')
                
            except Exception as e:
                logger.warning(f"Could not collect share metrics: {e}")
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
            metrics.append(f'moxnas_application_metrics_error 1')
        
        return metrics
    
    def _collect_cache_metrics(self):
        """Collect cache performance metrics"""
        metrics = []
        
        try:
            # Test cache performance
            cache_key = 'metrics_test'
            test_value = str(time.time())
            
            start_time = time.time()
            cache.set(cache_key, test_value, timeout=60)
            cache_set_time = (time.time() - start_time) * 1000
            
            start_time = time.time()
            retrieved_value = cache.get(cache_key)
            cache_get_time = (time.time() - start_time) * 1000
            
            # Cache response times
            metrics.append(f'moxnas_cache_set_time_ms {cache_set_time}')
            metrics.append(f'moxnas_cache_get_time_ms {cache_get_time}')
            
            # Cache hit/miss (1 = hit, 0 = miss)
            cache_hit = 1 if retrieved_value == test_value else 0
            metrics.append(f'moxnas_cache_hit {cache_hit}')
            
            # Clean up test key
            cache.delete(cache_key)
            
        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")
            metrics.append(f'moxnas_cache_error 1')
        
        return metrics
    
    def increment_request_count(self):
        """Increment request counter"""
        self.request_count += 1
    
    def increment_error_count(self):
        """Increment error counter"""
        self.error_count += 1


# Global metrics collector instance
metrics_collector = MetricsCollector()


class MetricsMiddleware:
    """Django middleware to collect request metrics"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Increment request count
        metrics_collector.increment_request_count()
        
        response = self.get_response(request)
        
        # Increment error count for 4xx/5xx responses
        if response.status_code >= 400:
            metrics_collector.increment_error_count()
        
        return response