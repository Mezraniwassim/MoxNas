"""
Real-time data monitoring for Proxmox hosts
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from threading import Thread, Event
import psutil
from django.core.cache import cache
from .manager import get_proxmox_manager
from .models import ProxmoxHost, ProxmoxNode, ProxmoxContainer

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System metrics data structure"""
    timestamp: float
    cpu_usage: float
    memory_usage: float
    memory_total: int
    memory_available: int
    disk_usage: float
    disk_total: int
    disk_free: int
    network_io_sent: int
    network_io_recv: int
    uptime: int
    load_average: List[float]


@dataclass
class ContainerMetrics:
    """Container metrics data structure"""
    vmid: int
    name: str
    status: str
    cpu_usage: float
    memory_usage: int
    memory_limit: int
    disk_usage: int
    network_io: Dict[str, int]
    uptime: int
    timestamp: float


@dataclass
class NodeMetrics:
    """Node metrics data structure"""
    node_name: str
    timestamp: float
    status: str
    cpu_usage: float
    memory_usage: int
    memory_total: int
    storage_usage: int
    storage_total: int
    uptime: int
    containers: List[ContainerMetrics]


class RealTimeMonitor:
    """Real-time monitoring service for Proxmox data"""
    
    def __init__(self, update_interval: int = 5):
        self.update_interval = update_interval
        self.is_running = False
        self.stop_event = Event()
        self.monitor_thread = None
        self.cache_prefix = "proxmox_realtime"
        self.cache_timeout = 300  # 5 minutes
        
    def start(self):
        """Start real-time monitoring"""
        if self.is_running:
            logger.warning("Real-time monitor is already running")
            return
            
        self.is_running = True
        self.stop_event.clear()
        self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Real-time monitoring started")
        
    def stop(self):
        """Stop real-time monitoring"""
        if not self.is_running:
            return
            
        self.is_running = False
        self.stop_event.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        logger.info("Real-time monitoring stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_running and not self.stop_event.is_set():
            try:
                start_time = time.time()
                
                # Collect metrics from all sources
                self._collect_system_metrics()
                self._collect_proxmox_metrics()
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.update_interval - elapsed)
                
                if self.stop_event.wait(sleep_time):
                    break
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                if self.stop_event.wait(5):  # Wait 5 seconds before retrying
                    break
                    
    def _collect_system_metrics(self):
        """Collect local system metrics"""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage (root filesystem)
            disk = psutil.disk_usage('/')
            
            # Network IO
            network = psutil.net_io_counters()
            
            # System uptime
            uptime = int(time.time() - psutil.boot_time())
            
            # Load average
            load_avg = list(psutil.getloadavg())
            
            metrics = SystemMetrics(
                timestamp=time.time(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                memory_total=memory.total,
                memory_available=memory.available,
                disk_usage=disk.percent,
                disk_total=disk.total,
                disk_free=disk.free,
                network_io_sent=network.bytes_sent,
                network_io_recv=network.bytes_recv,
                uptime=uptime,
                load_average=load_avg
            )
            
            # Cache the metrics
            cache_key = f"{self.cache_prefix}:system"
            cache.set(cache_key, asdict(metrics), self.cache_timeout)
            
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            
    def _collect_proxmox_metrics(self):
        """Collect Proxmox cluster metrics"""
        try:
            manager = get_proxmox_manager()
            if not manager:
                logger.debug("No Proxmox manager available, skipping metrics collection")
                return
                
            # Get all nodes
            nodes = manager.get_node_list()
            node_metrics = []
            
            for node_info in nodes:
                node_name = node_info.get('node')
                if not node_name:
                    continue
                    
                try:
                    # Get node status and statistics
                    node_status = manager.get_node_status(node_name)
                    containers = manager.get_containers(node_name)
                    
                    # Process container metrics
                    container_metrics = []
                    for container in containers:
                        try:
                            # Get detailed container statistics
                            container_stats = self._get_container_stats(manager, node_name, container)
                            if container_stats:
                                container_metrics.append(container_stats)
                        except Exception as e:
                            logger.debug(f"Failed to get stats for container {container.get('vmid')}: {e}")
                            
                    # Create node metrics
                    node_metric = NodeMetrics(
                        node_name=node_name,
                        timestamp=time.time(),
                        status=node_status.get('status', 'unknown'),
                        cpu_usage=node_status.get('cpu', 0) * 100,
                        memory_usage=node_status.get('memory', {}).get('used', 0),
                        memory_total=node_status.get('memory', {}).get('total', 0),
                        storage_usage=node_status.get('rootfs', {}).get('used', 0),
                        storage_total=node_status.get('rootfs', {}).get('total', 0),
                        uptime=node_status.get('uptime', 0),
                        containers=container_metrics
                    )
                    
                    node_metrics.append(node_metric)
                    
                    # Cache individual node metrics
                    cache_key = f"{self.cache_prefix}:node:{node_name}"
                    cache.set(cache_key, asdict(node_metric), self.cache_timeout)
                    
                except Exception as e:
                    logger.error(f"Failed to collect metrics for node {node_name}: {e}")
                    
            # Cache all nodes metrics
            cache_key = f"{self.cache_prefix}:nodes"
            cache.set(cache_key, [asdict(nm) for nm in node_metrics], self.cache_timeout)
            
        except Exception as e:
            logger.error(f"Failed to collect Proxmox metrics: {e}")
            
    def _get_container_stats(self, manager, node_name: str, container: Dict) -> Optional[ContainerMetrics]:
        """Get detailed statistics for a container"""
        try:
            vmid = container.get('vmid')
            if not vmid:
                return None
                
            # Get container configuration and current stats
            config = manager.get_container_config(node_name, vmid)
            if not config:
                return None
                
            # Extract metrics from container info
            cpu_usage = container.get('cpu', 0) * 100
            memory_usage = container.get('mem', 0)
            memory_limit = container.get('maxmem', 0)
            disk_usage = container.get('disk', 0)
            uptime = container.get('uptime', 0)
            
            # Network IO (if available)
            network_io = {
                'bytes_in': container.get('netin', 0),
                'bytes_out': container.get('netout', 0),
                'packets_in': container.get('diskread', 0),
                'packets_out': container.get('diskwrite', 0)
            }
            
            return ContainerMetrics(
                vmid=vmid,
                name=container.get('name', f'ct-{vmid}'),
                status=container.get('status', 'unknown'),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                memory_limit=memory_limit,
                disk_usage=disk_usage,
                network_io=network_io,
                uptime=uptime,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.debug(f"Failed to get container stats: {e}")
            return None
            
    def get_cached_metrics(self, metric_type: str, node_name: str = None) -> Optional[Dict]:
        """Get cached metrics"""
        try:
            if metric_type == "system":
                cache_key = f"{self.cache_prefix}:system"
            elif metric_type == "nodes":
                cache_key = f"{self.cache_prefix}:nodes"
            elif metric_type == "node" and node_name:
                cache_key = f"{self.cache_prefix}:node:{node_name}"
            else:
                return None
                
            return cache.get(cache_key)
            
        except Exception as e:
            logger.error(f"Failed to get cached metrics: {e}")
            return None
            
    def get_historical_metrics(self, metric_type: str, hours: int = 24) -> List[Dict]:
        """Get historical metrics (placeholder for future implementation)"""
        # This would typically query a time-series database
        # For now, return empty list
        return []


class RealTimeDataAggregator:
    """Aggregates real-time data from multiple sources"""
    
    def __init__(self):
        self.monitor = RealTimeMonitor()
        
    def start_monitoring(self):
        """Start the monitoring service"""
        self.monitor.start()
        
    def stop_monitoring(self):
        """Stop the monitoring service"""
        self.monitor.stop()
        
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        try:
            dashboard_data = {
                'timestamp': time.time(),
                'system': self.monitor.get_cached_metrics('system'),
                'nodes': self.monitor.get_cached_metrics('nodes'),
                'status': 'connected' if get_proxmox_manager() else 'disconnected'
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {
                'timestamp': time.time(),
                'system': None,
                'nodes': [],
                'status': 'error',
                'error': str(e)
            }
            
    def get_node_data(self, node_name: str) -> Dict[str, Any]:
        """Get detailed data for a specific node"""
        try:
            node_data = self.monitor.get_cached_metrics('node', node_name)
            if not node_data:
                return {'error': f'No data available for node {node_name}'}
                
            return {
                'timestamp': time.time(),
                'node': node_data,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Failed to get node data: {e}")
            return {
                'timestamp': time.time(),
                'node': None,
                'status': 'error',
                'error': str(e)
            }
            
    def get_container_data(self, node_name: str, vmid: int) -> Dict[str, Any]:
        """Get detailed data for a specific container"""
        try:
            node_data = self.monitor.get_cached_metrics('node', node_name)
            if not node_data:
                return {'error': f'No data available for node {node_name}'}
                
            # Find the specific container
            container_data = None
            for container in node_data.get('containers', []):
                if container.get('vmid') == vmid:
                    container_data = container
                    break
                    
            if not container_data:
                return {'error': f'Container {vmid} not found on node {node_name}'}
                
            return {
                'timestamp': time.time(),
                'container': container_data,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Failed to get container data: {e}")
            return {
                'timestamp': time.time(),
                'container': None,
                'status': 'error',
                'error': str(e)
            }


# Global instance
_realtime_aggregator = None

def get_realtime_aggregator() -> RealTimeDataAggregator:
    """Get or create the real-time data aggregator"""
    global _realtime_aggregator
    if _realtime_aggregator is None:
        _realtime_aggregator = RealTimeDataAggregator()
    return _realtime_aggregator

def start_realtime_monitoring():
    """Start real-time monitoring service"""
    aggregator = get_realtime_aggregator()
    aggregator.start_monitoring()
    
def stop_realtime_monitoring():
    """Stop real-time monitoring service"""
    aggregator = get_realtime_aggregator()
    aggregator.stop_monitoring()
