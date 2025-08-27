"""Storage Management Backend"""
import os
import subprocess
import json
import re
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from app.models import StorageDevice, StoragePool, DeviceStatus, PoolStatus, SystemLog, LogLevel
from app import db

class StorageManager:
    """Comprehensive storage management with RAID support"""
    
    def __init__(self):
        self.mdadm_path = '/sbin/mdadm'
        self.smartctl_path = '/usr/sbin/smartctl'
        self.lsblk_path = '/bin/lsblk'
        self.mkfs_paths = {
            'ext4': '/sbin/mkfs.ext4',
            'xfs': '/sbin/mkfs.xfs'
        }
        
    def run_command(self, command: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """Execute system command safely with timeout"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, '', f'Command timed out after {timeout} seconds'
        except Exception as e:
            return False, '', str(e)
    
    def scan_storage_devices(self) -> List[Dict]:
        """Scan for available storage devices"""
        devices = []
        
        # Use lsblk to get device information
        success, stdout, stderr = self.run_command([
            self.lsblk_path, '-J', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,MODEL,SERIAL,ROTA,HOTPLUG'
        ])
        
        if not success:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category='storage',
                message=f'Failed to scan storage devices: {stderr}'
            )
            return devices
        
        try:
            lsblk_data = json.loads(stdout)
            for device in lsblk_data.get('blockdevices', []):
                if device.get('type') == 'disk' and not device.get('mountpoint'):
                    # Get additional device information
                    device_path = f\"/dev/{device['name']}\"
                    device_info = self._get_device_details(device_path)
                    
                    if device_info:
                        devices.append({
                            'path': device_path,
                            'name': device['name'],
                            'size': self._parse_size(device.get('size', '0')),
                            'model': device.get('model', 'Unknown'),
                            'serial': device.get('serial', 'Unknown'),
                            'rotational': device.get('rota', '1') == '1',
                            'removable': device.get('hotplug', '0') == '1',
                            **device_info
                        })
        except json.JSONDecodeError as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category='storage',
                message=f'Failed to parse device scan results: {str(e)}'
            )
        
        return devices
    
    def _get_device_details(self, device_path: str) -> Optional[Dict]:
        """Get detailed device information including SMART data"""
        details = {}
        
        # Get SMART information
        smart_data = self.get_smart_data(device_path)
        if smart_data:
            details.update(smart_data)
        
        # Get device capacity and sector size
        success, stdout, stderr = self.run_command([
            'blockdev', '--getsize64', '--getss', device_path
        ])
        
        if success:
            lines = stdout.strip().split('\\n')
            if len(lines) >= 2:
                details['size_bytes'] = int(lines[0])
                details['sector_size'] = int(lines[1])
        
        return details
    
    def get_smart_data(self, device_path: str) -> Optional[Dict]:
        """Get SMART data for a device"""
        if not os.path.exists(self.smartctl_path):
            return None
        
        success, stdout, stderr = self.run_command([
            self.smartctl_path, '-a', '-j', device_path
        ])
        
        if not success:
            return None
        
        try:
            smart_data = json.loads(stdout)
            
            # Extract key information
            result = {
                'smart_status': smart_data.get('smart_status', {}).get('passed', False),
                'temperature': None,
                'power_on_hours': None,
                'device_model': smart_data.get('device', {}).get('name', ''),
                'serial_number': smart_data.get('serial_number', ''),
                'firmware_version': smart_data.get('firmware_version', ''),
                'overall_health': 'PASSED' if smart_data.get('smart_status', {}).get('passed', False) else 'FAILED'
            }
            
            # Extract temperature from SMART attributes
            if 'ata_smart_attributes' in smart_data:
                for attr in smart_data['ata_smart_attributes']['table']:
                    if attr['name'] == 'Temperature_Celsius':
                        result['temperature'] = attr['raw']['value']
                    elif attr['name'] == 'Power_On_Hours':
                        result['power_on_hours'] = attr['raw']['value']
            
            return result
            
        except (json.JSONDecodeError, KeyError) as e:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='storage',
                message=f'Failed to parse SMART data for {device_path}: {str(e)}'
            )
            return None
    
    def create_raid_array(self, name: str, level: str, devices: List[str], 
                         filesystem: str = 'ext4') -> Tuple[bool, str]:
        \"\"\"Create RAID array using mdadm\"\"\"
        
        # Validate inputs
        if level not in ['raid0', 'raid1', 'raid5', 'raid10']:
            return False, f'Unsupported RAID level: {level}'
        
        if len(devices) < self._get_min_devices_for_raid(level):
            return False, f'Insufficient devices for {level}. Need at least {self._get_min_devices_for_raid(level)} devices'
        
        # Check if devices are available
        for device in devices:
            if not os.path.exists(device):
                return False, f'Device {device} does not exist'
            
            # Check if device is already in use
            existing_device = StorageDevice.query.filter_by(device_path=device).first()
            if existing_device and existing_device.pool_id:
                return False, f'Device {device} is already in use by pool {existing_device.pool.name}'
        
        try:
            # Create RAID array
            raid_device = f'/dev/md/{name}'
            mdadm_level = level.replace('raid', '')
            
            create_command = [
                self.mdadm_path, '--create', raid_device,
                '--level', mdadm_level,
                '--raid-devices', str(len(devices))
            ] + devices
            
            success, stdout, stderr = self.run_command(create_command, timeout=300)
            if not success:
                return False, f'Failed to create RAID array: {stderr}'
            
            # Wait for array to be ready
            time.sleep(2)
            
            # Create filesystem
            if filesystem in self.mkfs_paths:
                mkfs_command = [self.mkfs_paths[filesystem], raid_device]
                success, stdout, stderr = self.run_command(mkfs_command, timeout=300)
                if not success:
                    # Cleanup RAID array
                    self.run_command([self.mdadm_path, '--stop', raid_device])
                    return False, f'Failed to create filesystem: {stderr}'
            
            # Create mount point
            mount_point = f'/mnt/{name}'
            os.makedirs(mount_point, exist_ok=True)
            
            # Mount the filesystem
            mount_command = ['mount', raid_device, mount_point]
            success, stdout, stderr = self.run_command(mount_command)
            if not success:
                return False, f'Failed to mount filesystem: {stderr}'
            
            # Get array size
            array_size = self._get_device_size(raid_device)
            
            return True, f'RAID array {name} created successfully at {mount_point}'
            
        except Exception as e:
            return False, f'Unexpected error creating RAID array: {str(e)}'
    
    def delete_raid_array(self, pool: StoragePool) -> Tuple[bool, str]:
        \"\"\"Delete RAID array and cleanup\"\"\"
        try:
            raid_device = f'/dev/md/{pool.name}'
            
            # Unmount filesystem
            if pool.mount_point:
                umount_command = ['umount', pool.mount_point]
                self.run_command(umount_command)
            
            # Stop RAID array
            stop_command = [self.mdadm_path, '--stop', raid_device]
            success, stdout, stderr = self.run_command(stop_command)
            if not success:
                return False, f'Failed to stop RAID array: {stderr}'
            
            # Zero superblocks on member devices
            for device in pool.devices:
                zero_command = [self.mdadm_path, '--zero-superblock', device.device_path]
                self.run_command(zero_command)
            
            # Remove mount point
            if pool.mount_point and os.path.exists(pool.mount_point):
                try:
                    os.rmdir(pool.mount_point)
                except OSError:
                    pass  # Directory not empty or other issue
            
            return True, f'RAID array {pool.name} deleted successfully'
            
        except Exception as e:
            return False, f'Unexpected error deleting RAID array: {str(e)}'
    
    def scrub_raid_array(self, pool: StoragePool) -> Tuple[bool, str]:
        \"\"\"Start scrubbing/checking RAID array\"\"\"
        try:
            raid_device = f'/dev/md/{pool.name}'
            
            # Check if array exists and is active
            check_command = [self.mdadm_path, '--detail', raid_device]
            success, stdout, stderr = self.run_command(check_command)
            if not success:
                return False, f'RAID array not found or inactive: {stderr}'
            
            # Start check/repair
            scrub_command = ['echo', 'check', '>', f'/sys/block/md{pool.name}/md/sync_action']
            success, stdout, stderr = self.run_command(scrub_command)
            if not success:
                return False, f'Failed to start scrub: {stderr}'
            
            return True, f'Scrub started for RAID array {pool.name}'
            
        except Exception as e:
            return False, f'Unexpected error starting scrub: {str(e)}'
    
    def get_raid_status(self, pool: StoragePool) -> Dict:
        \"\"\"Get detailed RAID array status\"\"\"
        raid_device = f'/dev/md/{pool.name}'
        status = {
            'name': pool.name,
            'status': 'unknown',
            'sync_progress': 0,
            'devices': [],
            'errors': []
        }
        
        try:
            # Get detailed array information
            detail_command = [self.mdadm_path, '--detail', raid_device]
            success, stdout, stderr = self.run_command(detail_command)
            
            if success:
                lines = stdout.split('\\n')
                for line in lines:
                    line = line.strip()
                    if 'State :' in line:
                        if 'clean' in line.lower():
                            status['status'] = 'healthy'
                        elif 'degraded' in line.lower():
                            status['status'] = 'degraded'
                        elif 'failed' in line.lower():
                            status['status'] = 'failed'
                    elif 'Resync Status :' in line or 'Check Status :' in line:
                        # Extract sync progress
                        progress_match = re.search(r'(\\d+)%', line)
                        if progress_match:
                            status['sync_progress'] = int(progress_match.group(1))
            
            # Check individual device status
            for device in pool.devices:
                device_status = {
                    'path': device.device_path,
                    'status': device.status.value,
                    'smart_status': device.get_smart_data().get('overall_health', 'unknown')
                }
                status['devices'].append(device_status)
                
        except Exception as e:
            status['errors'].append(str(e))
        
        return status
    
    def _get_min_devices_for_raid(self, level: str) -> int:
        \"\"\"Get minimum devices required for RAID level\"\"\"
        min_devices = {
            'raid0': 2,
            'raid1': 2,
            'raid5': 3,
            'raid10': 4
        }
        return min_devices.get(level, 2)
    
    def _parse_size(self, size_str: str) -> int:
        \"\"\"Parse size string to bytes\"\"\"
        if not size_str or size_str == '0':
            return 0
        
        # Remove any whitespace
        size_str = size_str.strip().upper()
        
        # Handle different size units
        multipliers = {
            'K': 1024,
            'M': 1024**2,
            'G': 1024**3,
            'T': 1024**4,
            'P': 1024**5
        }
        
        for unit, multiplier in multipliers.items():
            if size_str.endswith(unit):
                try:
                    number = float(size_str[:-1])
                    return int(number * multiplier)
                except ValueError:
                    continue
        
        # Try to parse as plain number
        try:
            return int(float(size_str))
        except ValueError:
            return 0
    
    def _get_device_size(self, device_path: str) -> int:
        \"\"\"Get device size in bytes\"\"\"
        success, stdout, stderr = self.run_command(['blockdev', '--getsize64', device_path])
        if success:
            try:
                return int(stdout.strip())
            except ValueError:
                pass
        return 0
    
    def update_device_database(self):
        \"\"\"Update database with current device information\"\"\"
        try:
            devices = self.scan_storage_devices()
            
            for device_info in devices:
                # Check if device exists in database
                db_device = StorageDevice.query.filter_by(
                    device_path=device_info['path']
                ).first()
                
                if db_device:
                    # Update existing device
                    db_device.device_name = device_info['name']
                    db_device.device_model = device_info.get('model', 'Unknown')
                    db_device.device_serial = device_info.get('serial', 'Unknown')
                    db_device.device_size = device_info.get('size_bytes', 0)
                    db_device.sector_size = device_info.get('sector_size', 512)
                    db_device.temperature = device_info.get('temperature')
                    db_device.power_on_hours = device_info.get('power_on_hours')
                    
                    # Update SMART data
                    if 'overall_health' in device_info:
                        smart_data = {
                            'overall_health': device_info['overall_health'],
                            'temperature': device_info.get('temperature'),
                            'power_on_hours': device_info.get('power_on_hours'),
                            'smart_status': device_info.get('smart_status', False)
                        }
                        db_device.update_smart_data(smart_data)
                    
                    db_device.updated_at = datetime.utcnow()
                else:
                    # Create new device
                    db_device = StorageDevice(
                        device_path=device_info['path'],
                        device_name=device_info['name'],
                        device_model=device_info.get('model', 'Unknown'),
                        device_serial=device_info.get('serial', 'Unknown'),
                        device_size=device_info.get('size_bytes', 0),
                        sector_size=device_info.get('sector_size', 512),
                        temperature=device_info.get('temperature'),
                        power_on_hours=device_info.get('power_on_hours'),
                        status=DeviceStatus.HEALTHY
                    )
                    
                    # Set SMART data for new device
                    if 'overall_health' in device_info:
                        smart_data = {
                            'overall_health': device_info['overall_health'],
                            'temperature': device_info.get('temperature'),
                            'power_on_hours': device_info.get('power_on_hours'),
                            'smart_status': device_info.get('smart_status', False)
                        }
                        db_device.update_smart_data(smart_data)
                    
                    db.session.add(db_device)
            
            db.session.commit()
            
            SystemLog.log_event(
                level=LogLevel.INFO,
                category='storage',
                message=f'Updated {len(devices)} storage devices in database'
            )
            
        except Exception as e:
            db.session.rollback()
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category='storage',
                message=f'Failed to update device database: {str(e)}'
            )

# Global storage manager instance
storage_manager = StorageManager()