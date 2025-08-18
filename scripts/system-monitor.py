#!/usr/bin/env python3
"""
System monitoring utilities for MoxNAS
"""

import psutil
import time
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemMonitor:
    """System monitoring utility class"""
    
    def __init__(self):
        self.logger = logger
    
    def get_system_info(self):
        """Get basic system information"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        
        return {
            'hostname': psutil.os.uname().nodename,
            'platform': psutil.os.uname().system,
            'architecture': psutil.os.uname().machine,
            'kernel': psutil.os.uname().release,
            'boot_time': boot_time.isoformat(),
            'uptime_seconds': int(time.time() - psutil.boot_time())
        }
    
    def get_cpu_info(self):
        """Get CPU information and usage"""
        cpu_count = psutil.cpu_count()
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        load_avg = psutil.getloadavg()
        
        return {
            'physical_cores': cpu_count,
            'logical_cores': cpu_count_logical,
            'current_frequency': cpu_freq.current if cpu_freq else 0,
            'min_frequency': cpu_freq.min if cpu_freq else 0,
            'max_frequency': cpu_freq.max if cpu_freq else 0,
            'usage_percent': sum(cpu_percent) / len(cpu_percent),
            'usage_per_core': cpu_percent,
            'load_average': {
                '1min': load_avg[0],
                '5min': load_avg[1],
                '15min': load_avg[2]
            }
        }
    
    def get_memory_info(self):
        """Get memory information and usage"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'free': memory.free,
            'percent': memory.percent,
            'buffers': getattr(memory, 'buffers', 0),
            'cached': getattr(memory, 'cached', 0),
            'swap': {
                'total': swap.total,
                'used': swap.used,
                'free': swap.free,
                'percent': swap.percent
            }
        }
    
    def get_disk_info(self):
        """Get disk information and usage"""
        disks = []
        
        # Get disk partitions
        partitions = psutil.disk_partitions()
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info = {
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'filesystem': partition.fstype,
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
                }
                disks.append(disk_info)
            except PermissionError:
                # Can't access this partition
                continue
        
        # Get disk I/O statistics
        disk_io = psutil.disk_io_counters(perdisk=True)
        io_stats = {}
        
        for device, io in disk_io.items():
            io_stats[device] = {
                'read_count': io.read_count,
                'write_count': io.write_count,
                'read_bytes': io.read_bytes,
                'write_bytes': io.write_bytes,
                'read_time': io.read_time,
                'write_time': io.write_time
            }
        
        return {
            'partitions': disks,
            'io_stats': io_stats
        }
    
    def get_network_info(self):
        """Get network information and usage"""
        # Network interfaces
        interfaces = {}
        net_if_addrs = psutil.net_if_addrs()
        net_if_stats = psutil.net_if_stats()
        
        for interface, addresses in net_if_addrs.items():
            interface_info = {
                'addresses': [],
                'stats': {}
            }
            
            # Get addresses
            for addr in addresses:
                addr_info = {
                    'family': addr.family.name,
                    'address': addr.address,
                    'netmask': addr.netmask,
                    'broadcast': addr.broadcast
                }
                interface_info['addresses'].append(addr_info)
            
            # Get interface statistics
            if interface in net_if_stats:
                stats = net_if_stats[interface]
                interface_info['stats'] = {
                    'is_up': stats.isup,
                    'duplex': stats.duplex.name if stats.duplex else 'unknown',
                    'speed': stats.speed,
                    'mtu': stats.mtu
                }
            
            interfaces[interface] = interface_info
        
        # Network I/O statistics
        net_io = psutil.net_io_counters(pernic=True)
        io_stats = {}
        
        for interface, io in net_io.items():
            io_stats[interface] = {
                'bytes_sent': io.bytes_sent,
                'bytes_recv': io.bytes_recv,
                'packets_sent': io.packets_sent,
                'packets_recv': io.packets_recv,
                'errin': io.errin,
                'errout': io.errout,
                'dropin': io.dropin,
                'dropout': io.dropout
            }
        
        return {
            'interfaces': interfaces,
            'io_stats': io_stats
        }
    
    def get_process_info(self, top_n=10):
        """Get information about running processes"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'memory_info']):
            try:
                proc_info = proc.info
                proc_info['memory_rss'] = proc_info['memory_info'].rss if proc_info['memory_info'] else 0
                proc_info['memory_vms'] = proc_info['memory_info'].vms if proc_info['memory_info'] else 0
                del proc_info['memory_info']  # Remove the namedtuple
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage and get top N
        processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
        
        return {
            'total_processes': len(processes),
            'top_cpu': processes[:top_n],
            'top_memory': sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:top_n]
        }
    
    def get_temperature_info(self):
        """Get system temperature information"""
        temperatures = {}
        
        try:
            temps = psutil.sensors_temperatures()
            for sensor_name, sensor_list in temps.items():
                temperatures[sensor_name] = []
                for sensor in sensor_list:
                    temp_info = {
                        'label': sensor.label or 'unknown',
                        'current': sensor.current,
                        'high': sensor.high,
                        'critical': sensor.critical
                    }
                    temperatures[sensor_name].append(temp_info)
        except AttributeError:
            # psutil.sensors_temperatures() not available on this platform
            pass
        
        return temperatures
    
    def get_full_system_stats(self):
        """Get comprehensive system statistics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'system': self.get_system_info(),
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'disk': self.get_disk_info(),
            'network': self.get_network_info(),
            'processes': self.get_process_info(),
            'temperature': self.get_temperature_info()
        }
    
    def monitor_continuously(self, interval=60, output_file=None):
        """Continuously monitor system and optionally save to file"""
        while True:
            try:
                stats = self.get_full_system_stats()
                
                if output_file:
                    with open(output_file, 'a') as f:
                        f.write(json.dumps(stats) + '\n')
                else:
                    print(json.dumps(stats, indent=2))
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error during monitoring: {e}")
                time.sleep(interval)


def main():
    """Command line interface for system monitor"""
    if len(sys.argv) < 2:
        print("Usage: system-monitor.py <command> [args...]")
        print("Commands:")
        print("  info                    - Get basic system info")
        print("  cpu                     - Get CPU info")
        print("  memory                  - Get memory info")
        print("  disk                    - Get disk info")
        print("  network                 - Get network info")
        print("  processes [n]           - Get top N processes")
        print("  temperature             - Get temperature info")
        print("  all                     - Get all stats")
        print("  monitor [interval]      - Monitor continuously")
        sys.exit(1)
    
    monitor = SystemMonitor()
    command = sys.argv[1]
    
    if command == 'info':
        info = monitor.get_system_info()
        print(json.dumps(info, indent=2))
    
    elif command == 'cpu':
        cpu_info = monitor.get_cpu_info()
        print(json.dumps(cpu_info, indent=2))
    
    elif command == 'memory':
        memory_info = monitor.get_memory_info()
        print(json.dumps(memory_info, indent=2))
    
    elif command == 'disk':
        disk_info = monitor.get_disk_info()
        print(json.dumps(disk_info, indent=2))
    
    elif command == 'network':
        network_info = monitor.get_network_info()
        print(json.dumps(network_info, indent=2))
    
    elif command == 'processes':
        top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        process_info = monitor.get_process_info(top_n)
        print(json.dumps(process_info, indent=2))
    
    elif command == 'temperature':
        temp_info = monitor.get_temperature_info()
        print(json.dumps(temp_info, indent=2))
    
    elif command == 'all':
        stats = monitor.get_full_system_stats()
        print(json.dumps(stats, indent=2))
    
    elif command == 'monitor':
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        monitor.monitor_continuously(interval)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()