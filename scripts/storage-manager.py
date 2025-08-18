#!/usr/bin/env python3
"""
Storage management utilities for MoxNAS
"""

import subprocess
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StorageManager:
    """Storage management utility class"""
    
    def __init__(self):
        self.logger = logger
    
    def run_command(self, command, check=True):
        """Run a system command and return the result"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
    
    def scan_disks(self):
        """Scan for available disks"""
        returncode, output, error = self.run_command(['lsblk', '-J'])
        
        if returncode != 0:
            self.logger.error(f"Failed to scan disks: {error}")
            return []
        
        try:
            data = json.loads(output)
            disks = []
            
            for device in data.get('blockdevices', []):
                if device.get('type') == 'disk':
                    disk_info = {
                        'name': device.get('name'),
                        'size': device.get('size'),
                        'model': device.get('model', ''),
                        'type': self._detect_disk_type(device.get('name')),
                        'mountpoint': device.get('mountpoint'),
                        'children': device.get('children', [])
                    }
                    disks.append(disk_info)
            
            return disks
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse disk scan output: {e}")
            return []
    
    def _detect_disk_type(self, device_name):
        """Detect if disk is HDD, SSD, or NVMe"""
        if device_name.startswith('nvme'):
            return 'nvme'
        
        # Check rotational property
        try:
            with open(f'/sys/block/{device_name}/queue/rotational', 'r') as f:
                rotational = f.read().strip()
                return 'hdd' if rotational == '1' else 'ssd'
        except:
            return 'unknown'
    
    def get_disk_smart_info(self, device):
        """Get SMART information for a disk"""
        returncode, output, error = self.run_command(['smartctl', '-i', f'/dev/{device}'], check=False)
        
        smart_info = {
            'device': device,
            'available': returncode in [0, 1, 2],
            'model': '',
            'serial': '',
            'capacity': '',
            'health': 'unknown'
        }
        
        if smart_info['available']:
            lines = output.split('\n')
            for line in lines:
                if 'Device Model:' in line:
                    smart_info['model'] = line.split(':', 1)[1].strip()
                elif 'Serial Number:' in line:
                    smart_info['serial'] = line.split(':', 1)[1].strip()
                elif 'User Capacity:' in line:
                    smart_info['capacity'] = line.split(':', 1)[1].strip()
        
        return smart_info
    
    def create_zfs_pool(self, pool_name, disk_list, pool_type='single'):
        """Create a ZFS pool"""
        if not pool_name or not disk_list:
            raise ValueError("Pool name and disk list are required")
        
        # Prepare disk devices
        devices = [f'/dev/{disk}' for disk in disk_list]
        
        # Build zpool create command
        cmd = ['zpool', 'create', '-f', pool_name]
        
        if pool_type == 'mirror':
            cmd.extend(['mirror'] + devices)
        elif pool_type == 'raidz':
            cmd.extend(['raidz'] + devices)
        elif pool_type == 'raidz2':
            cmd.extend(['raidz2'] + devices)
        elif pool_type == 'stripe':
            cmd.extend(devices)
        else:  # single
            if len(devices) != 1:
                raise ValueError("Single disk pool requires exactly one disk")
            cmd.extend(devices)
        
        returncode, output, error = self.run_command(cmd)
        
        if returncode == 0:
            self.logger.info(f"Successfully created ZFS pool: {pool_name}")
            return True, output
        else:
            self.logger.error(f"Failed to create ZFS pool: {error}")
            return False, error
    
    def destroy_zfs_pool(self, pool_name):
        """Destroy a ZFS pool"""
        returncode, output, error = self.run_command(['zpool', 'destroy', '-f', pool_name])
        
        if returncode == 0:
            self.logger.info(f"Successfully destroyed ZFS pool: {pool_name}")
            return True, output
        else:
            self.logger.error(f"Failed to destroy ZFS pool: {error}")
            return False, error
    
    def get_pool_status(self, pool_name=None):
        """Get ZFS pool status"""
        cmd = ['zpool', 'status']
        if pool_name:
            cmd.append(pool_name)
        
        returncode, output, error = self.run_command(cmd, check=False)
        
        if returncode == 0:
            return output
        else:
            return f"Error getting pool status: {error}"
    
    def scrub_pool(self, pool_name):
        """Start a pool scrub"""
        returncode, output, error = self.run_command(['zpool', 'scrub', pool_name])
        
        if returncode == 0:
            self.logger.info(f"Scrub started for pool: {pool_name}")
            return True, output
        else:
            self.logger.error(f"Failed to start scrub: {error}")
            return False, error
    
    def create_dataset(self, pool_name, dataset_name, mount_point=None):
        """Create a ZFS dataset"""
        full_name = f"{pool_name}/{dataset_name}"
        cmd = ['zfs', 'create']
        
        if mount_point:
            cmd.extend(['-o', f'mountpoint={mount_point}'])
        
        cmd.append(full_name)
        
        returncode, output, error = self.run_command(cmd)
        
        if returncode == 0:
            self.logger.info(f"Successfully created dataset: {full_name}")
            return True, output
        else:
            self.logger.error(f"Failed to create dataset: {error}")
            return False, error
    
    def create_snapshot(self, dataset_name, snapshot_name):
        """Create a ZFS snapshot"""
        full_name = f"{dataset_name}@{snapshot_name}"
        returncode, output, error = self.run_command(['zfs', 'snapshot', full_name])
        
        if returncode == 0:
            self.logger.info(f"Successfully created snapshot: {full_name}")
            return True, output
        else:
            self.logger.error(f"Failed to create snapshot: {error}")
            return False, error


def main():
    """Command line interface for storage manager"""
    if len(sys.argv) < 2:
        print("Usage: storage-manager.py <command> [args...]")
        print("Commands:")
        print("  scan-disks              - Scan for available disks")
        print("  smart-info <device>     - Get SMART info for device")
        print("  create-pool <name> <type> <disks...> - Create ZFS pool")
        print("  pool-status [name]      - Get pool status")
        print("  scrub <pool>            - Start pool scrub")
        sys.exit(1)
    
    manager = StorageManager()
    command = sys.argv[1]
    
    if command == 'scan-disks':
        disks = manager.scan_disks()
        print(json.dumps(disks, indent=2))
    
    elif command == 'smart-info':
        if len(sys.argv) != 3:
            print("Usage: storage-manager.py smart-info <device>")
            sys.exit(1)
        device = sys.argv[2]
        info = manager.get_disk_smart_info(device)
        print(json.dumps(info, indent=2))
    
    elif command == 'create-pool':
        if len(sys.argv) < 5:
            print("Usage: storage-manager.py create-pool <name> <type> <disk1> [disk2...]")
            sys.exit(1)
        pool_name = sys.argv[2]
        pool_type = sys.argv[3]
        disks = sys.argv[4:]
        success, output = manager.create_zfs_pool(pool_name, disks, pool_type)
        print(output)
        sys.exit(0 if success else 1)
    
    elif command == 'pool-status':
        pool_name = sys.argv[2] if len(sys.argv) > 2 else None
        status = manager.get_pool_status(pool_name)
        print(status)
    
    elif command == 'scrub':
        if len(sys.argv) != 3:
            print("Usage: storage-manager.py scrub <pool>")
            sys.exit(1)
        pool_name = sys.argv[2]
        success, output = manager.scrub_pool(pool_name)
        print(output)
        sys.exit(0 if success else 1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()