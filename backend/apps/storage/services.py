import subprocess
import json
import psutil
import os
import logging
from typing import List, Dict, Any

from .models import Disk, MountPoint, StoragePool

logger = logging.getLogger(__name__)

class StorageService:
    """Service class for storage operations"""

    def scan_disks(self) -> List[Dict[str, Any]]:
        """Scan system for available disks"""
        try:
            # Use lsblk to get disk information
            result = subprocess.run([
                'lsblk', '-J', '-o', 
                'NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,SERIAL,ROTA,RM'
            ], capture_output=True, text=True)

            if result.returncode != 0:
                raise Exception(f"lsblk failed: {result.stderr}")

            data = json.loads(result.stdout)
            disks = []

            for device in data['blockdevices']:
                if device['type'] == 'disk':
                    disk_info = self._process_disk_info(device)
                    disks.append(disk_info)
                    
                    # Update or create disk in database
                    self._update_or_create_disk(disk_info)

            return disks

        except Exception as e:
            logger.error(f"Error scanning disks: {e}")
            raise

    def _process_disk_info(self, device: Dict) -> Dict[str, Any]:
        """Process disk information from lsblk"""
        device_path = f"/dev/{device['name']}"
        
        return {
            'device': device_path,
            'name': device.get('model', device['name']),
            'size': self._parse_size(device.get('size', '0')),
            'size_human': device.get('size', '0'),
            'filesystem': device.get('fstype', ''),
            'mount_point': device.get('mountpoint', ''),
            'is_mounted': bool(device.get('mountpoint')),
            'is_removable': device.get('rm') == '1',
            'is_system': self._is_system_disk(device_path),
            'model': device.get('model', ''),
            'serial': device.get('serial', ''),
            'type': 'SSD' if device.get('rota') == '0' else 'HDD'
        }

    def _parse_size(self, size_str: str) -> int:
        """Parse size string to bytes"""
        if not size_str:
            return 0
        
        size_str = size_str.strip().upper()
        multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
        
        if size_str[-1] in multipliers:
            return int(float(size_str[:-1]) * multipliers[size_str[-1]])
        
        try:
            return int(size_str)
        except ValueError:
            return 0

    def _is_system_disk(self, device_path: str) -> bool:
        """Check if disk is system disk"""
        try:
            # Check if root filesystem is on this disk
            result = subprocess.run([
                'findmnt', '-n', '-o', 'SOURCE', '/'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                root_device = result.stdout.strip()
                return device_path in root_device
            
            return False
        except Exception:
            return False

    def _update_or_create_disk(self, disk_info: Dict) -> Disk:
        """Update or create disk in database"""
        disk, created = Disk.objects.update_or_create(
            device=disk_info['device'],
            defaults={
                'name': disk_info['name'],
                'size': disk_info['size'],
                'filesystem': disk_info['filesystem'],
                'mount_point': disk_info['mount_point'],
                'is_mounted': disk_info['is_mounted'],
                'is_system': disk_info['is_system'],
                'is_removable': disk_info['is_removable'],
                'model': disk_info['model'],
                'serial': disk_info['serial'],
            }
        )
        
        if created:
            logger.info(f"Created new disk: {disk.device}")
        else:
            logger.info(f"Updated disk: {disk.device}")
        
        return disk

    def get_storage_overview(self) -> Dict[str, Any]:
        """Get overall storage statistics"""
        try:
            disks = Disk.objects.all()
            total_size = 0
            used_size = 0
            available_size = 0
            
            for disk in disks:
                if disk.usage and not disk.is_system:
                    total_size += disk.usage['total']
                    used_size += disk.usage['used']
                    available_size += disk.usage['free']
            
            usage_percent = (used_size / total_size * 100) if total_size > 0 else 0
            
            return {
                'total_disks': disks.count(),
                'mounted_disks': disks.filter(is_mounted=True).count(),
                'total_size': total_size,
                'used_size': used_size,
                'available_size': available_size,
                'usage_percent': usage_percent,
                'pools': StoragePool.objects.count(),
                'mount_points': MountPoint.objects.count(),
            }
            
        except Exception as e:
            logger.error(f"Error getting storage overview: {e}")
            raise

    def create_filesystem(self, device: str, filesystem: str = 'ext4') -> bool:
        """Create filesystem on device"""
        try:
            if filesystem == 'ext4':
                cmd = ['mkfs.ext4', '-F', device]
            elif filesystem == 'xfs':
                cmd = ['mkfs.xfs', '-f', device]
            elif filesystem == 'ntfs':
                cmd = ['mkfs.ntfs', '-F', device]
            else:
                raise ValueError(f"Unsupported filesystem: {filesystem}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Created {filesystem} filesystem on {device}")
                return True
            else:
                logger.error(f"Failed to create filesystem on {device}: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating filesystem on {device}: {e}")
            return False