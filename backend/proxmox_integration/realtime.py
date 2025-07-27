"""
Real-time monitoring module for Proxmox integration
Handles real-time data aggregation and monitoring
"""
import threading
import time
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from django.utils import timezone
from .models import ProxmoxHost, ProxmoxNode, ProxmoxContainer
from .manager import ProxmoxManager

logger = logging.getLogger(__name__)


class RealtimeAggregator:
    """
    Aggregates real-time data from Proxmox nodes
    """
    
    def __init__(self):
        self.is_running = False
        self.update_interval = 10  # seconds
        self.thread = None
        self.callbacks = []
        self.last_update = None
        self.data_cache = {}
        self.lock = threading.Lock()
    
    def add_callback(self, callback: Callable):
        """Add a callback function to be called on data updates"""
        with self.lock:
            self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Remove a callback function"""
        with self.lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
    
    def start(self):
        """Start real-time monitoring"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.thread.start()
            logger.info("Real-time monitoring started")
    
    def stop(self):
        """Stop real-time monitoring"""
        if self.is_running:
            self.is_running = False
            if self.thread:
                self.thread.join(timeout=5)
            logger.info("Real-time monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                self._collect_data()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.update_interval)
    
    def _collect_data(self):
        """Collect data from all configured Proxmox hosts"""
        aggregated_data = {
            'timestamp': timezone.now().isoformat(),
            'hosts': [],
            'summary': {
                'total_nodes': 0,
                'online_nodes': 0,
                'total_containers': 0,
                'running_containers': 0,
                'total_memory': 0,
                'used_memory': 0,
                'total_disk': 0,
                'used_disk': 0,
                'cpu_usage': 0.0,
            }
        }
        
        hosts = ProxmoxHost.objects.filter(enabled=True)
        
        for host in hosts:
            try:
                host_data = self._collect_host_data(host)
                aggregated_data['hosts'].append(host_data)
                
                # Update summary
                aggregated_data['summary']['total_nodes'] += len(host_data['nodes'])
                aggregated_data['summary']['online_nodes'] += len([n for n in host_data['nodes'] if n['status'] == 'online'])
                aggregated_data['summary']['total_containers'] += len(host_data['containers'])
                aggregated_data['summary']['running_containers'] += len([c for c in host_data['containers'] if c['status'] == 'running'])
                
                # Aggregate resource usage
                for node in host_data['nodes']:
                    aggregated_data['summary']['total_memory'] += node['memory_total']
                    aggregated_data['summary']['used_memory'] += node['memory_used']
                    aggregated_data['summary']['total_disk'] += node['disk_total']
                    aggregated_data['summary']['used_disk'] += node['disk_used']
                    aggregated_data['summary']['cpu_usage'] += node['cpu_usage']
                
            except Exception as e:
                logger.error(f"Error collecting data from host {host.name}: {e}")
        
        # Calculate averages
        if aggregated_data['summary']['total_nodes'] > 0:
            aggregated_data['summary']['cpu_usage'] /= aggregated_data['summary']['total_nodes']
        
        # Update cache and notify callbacks
        with self.lock:
            self.data_cache = aggregated_data
            self.last_update = timezone.now()
            
            for callback in self.callbacks:
                try:
                    callback(aggregated_data)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
    
    def _collect_host_data(self, host: ProxmoxHost) -> Dict:
        """Collect data from a specific Proxmox host"""
        manager = ProxmoxManager(host)
        
        try:
            # Get node information
            nodes_data = []
            nodes = manager.get_nodes()
            
            for node in nodes:
                node_info = manager.get_node_info(node['node'])
                nodes_data.append({
                    'name': node['node'],
                    'status': node['status'],
                    'cpu_usage': node_info.get('cpu', 0) * 100,  # Convert to percentage
                    'memory_total': node_info.get('maxmem', 0),
                    'memory_used': node_info.get('mem', 0),
                    'disk_total': node_info.get('maxdisk', 0),
                    'disk_used': node_info.get('disk', 0),
                    'uptime': node_info.get('uptime', 0),
                })
            
            # Get container information
            containers_data = []
            containers = manager.get_containers()
            
            for container in containers:
                container_info = manager.get_container_info(container['node'], container['vmid'])
                containers_data.append({
                    'vmid': container['vmid'],
                    'name': container['name'],
                    'node': container['node'],
                    'status': container['status'],
                    'memory': container_info.get('maxmem', 0),
                    'memory_usage': container_info.get('mem', 0),
                    'disk_size': container_info.get('maxdisk', 0),
                    'disk_usage': container_info.get('disk', 0),
                    'cpu_usage': container_info.get('cpu', 0) * 100,  # Convert to percentage
                    'uptime': container_info.get('uptime', 0),
                })
            
            return {
                'host_id': host.id,
                'host_name': host.name,
                'nodes': nodes_data,
                'containers': containers_data,
                'last_updated': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error collecting data from host {host.name}: {e}")
            return {
                'host_id': host.id,
                'host_name': host.name,
                'nodes': [],
                'containers': [],
                'error': str(e),
                'last_updated': timezone.now().isoformat(),
            }
    
    def get_cached_data(self) -> Optional[Dict]:
        """Get the last cached data"""
        with self.lock:
            return self.data_cache.copy() if self.data_cache else None
    
    def get_last_update(self) -> Optional[datetime]:
        """Get the timestamp of the last update"""
        with self.lock:
            return self.last_update


# Global aggregator instance
_aggregator = None


def get_realtime_aggregator() -> RealtimeAggregator:
    """Get the global real-time aggregator instance"""
    global _aggregator
    if _aggregator is None:
        _aggregator = RealtimeAggregator()
    return _aggregator


def start_realtime_monitoring():
    """Start real-time monitoring"""
    aggregator = get_realtime_aggregator()
    aggregator.start()


def stop_realtime_monitoring():
    """Stop real-time monitoring"""
    aggregator = get_realtime_aggregator()
    aggregator.stop()


def get_realtime_data() -> Optional[Dict]:
    """Get the latest real-time data"""
    aggregator = get_realtime_aggregator()
    return aggregator.get_cached_data()


def add_realtime_callback(callback: Callable):
    """Add a callback for real-time data updates"""
    aggregator = get_realtime_aggregator()
    aggregator.add_callback(callback)


def remove_realtime_callback(callback: Callable):
    """Remove a callback for real-time data updates"""
    aggregator = get_realtime_aggregator()
    aggregator.remove_callback(callback)


class RealtimeDataUpdater:
    """
    Updates database models with real-time data
    """
    
    def __init__(self):
        self.aggregator = get_realtime_aggregator()
        self.aggregator.add_callback(self._update_database)
    
    def _update_database(self, data: Dict):
        """Update database models with real-time data"""
        try:
            for host_data in data['hosts']:
                host = ProxmoxHost.objects.get(id=host_data['host_id'])
                
                # Update nodes
                for node_data in host_data['nodes']:
                    node, created = ProxmoxNode.objects.update_or_create(
                        host=host,
                        name=node_data['name'],
                        defaults={
                            'status': node_data['status'],
                            'cpu_usage': node_data['cpu_usage'],
                            'memory_total': node_data['memory_total'],
                            'memory_used': node_data['memory_used'],
                            'disk_total': node_data['disk_total'],
                            'disk_used': node_data['disk_used'],
                            'uptime': node_data['uptime'],
                        }
                    )
                
                # Update containers
                for container_data in host_data['containers']:
                    container, created = ProxmoxContainer.objects.update_or_create(
                        host=host,
                        vmid=container_data['vmid'],
                        defaults={
                            'name': container_data['name'],
                            'status': container_data['status'],
                            'memory': container_data['memory'],
                            'memory_usage': container_data['memory_usage'],
                            'disk_size': container_data['disk_size'],
                            'disk_usage': container_data['disk_usage'],
                            'cpu_usage': container_data['cpu_usage'],
                            'uptime': container_data['uptime'],
                        }
                    )
                
                # Update host last_seen
                host.last_seen = timezone.now()
                host.save()
                
        except Exception as e:
            logger.error(f"Error updating database with real-time data: {e}")


# Initialize database updater
_db_updater = RealtimeDataUpdater()