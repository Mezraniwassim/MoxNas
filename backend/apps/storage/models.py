from django.db import models
import psutil
import os
import subprocess
import logging

logger = logging.getLogger(__name__)

class Disk(models.Model):
    """Physical disk or block device"""
    device = models.CharField(max_length=255, unique=True, help_text="Device path (e.g., /dev/sda)")
    name = models.CharField(max_length=255, help_text="Human readable name")
    size = models.BigIntegerField(help_text="Size in bytes")
    filesystem = models.CharField(max_length=50, blank=True, help_text="Filesystem type")
    mount_point = models.CharField(max_length=255, blank=True, help_text="Current mount point")
    is_mounted = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False, help_text="System disk (not for storage)")
    is_removable = models.BooleanField(default=False)
    model = models.CharField(max_length=255, blank=True)
    serial = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.device} ({self.name})"

    @property
    def usage(self):
        """Get disk usage statistics"""
        if self.is_mounted and self.mount_point:
            try:
                usage = psutil.disk_usage(self.mount_point)
                return {
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
                }
            except Exception as e:
                logger.error(f"Error getting disk usage for {self.device}: {e}")
        return None

    @property
    def size_human(self):
        """Human readable size"""
        return self._format_bytes(self.size)

    def _format_bytes(self, bytes_value):
        """Format bytes to human readable format"""
        if not bytes_value:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"

    def refresh_info(self):
        """Refresh disk information from system"""
        try:
            # Get disk info using lsblk
            result = subprocess.run([
                'lsblk', '-J', '-o', 'NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL,SERIAL',
                self.device
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                if data['blockdevices']:
                    disk_info = data['blockdevices'][0]
                    self.size = self._parse_size(disk_info.get('size', ''))
                    self.filesystem = disk_info.get('fstype', '')
                    self.mount_point = disk_info.get('mountpoint', '')
                    self.is_mounted = bool(self.mount_point)
                    self.model = disk_info.get('model', '')
                    self.serial = disk_info.get('serial', '')
                    self.save()
        except Exception as e:
            logger.error(f"Error refreshing disk info for {self.device}: {e}")

    def _parse_size(self, size_str):
        """Parse size string like '100G' to bytes"""
        if not size_str:
            return 0
        
        size_str = size_str.strip().upper()
        multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
        
        if size_str[-1] in multipliers:
            return int(float(size_str[:-1]) * multipliers[size_str[-1]])
        return int(size_str)

class MountPoint(models.Model):
    """Mount point configuration"""
    path = models.CharField(max_length=255, unique=True, help_text="Mount point path")
    disk = models.ForeignKey(Disk, on_delete=models.CASCADE, related_name='mount_points')
    filesystem = models.CharField(max_length=50, default='ext4')
    options = models.TextField(default='defaults', help_text="Mount options")
    enabled = models.BooleanField(default=True)
    auto_mount = models.BooleanField(default=True, help_text="Mount automatically at boot")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['path']

    def __str__(self):
        return f"{self.disk.device} -> {self.path}"

    def mount(self):
        """Mount the filesystem"""
        try:
            if not os.path.exists(self.path):
                os.makedirs(self.path, exist_ok=True)
            
            cmd = ['mount', '-t', self.filesystem, '-o', self.options, self.disk.device, self.path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.disk.mount_point = self.path
                self.disk.is_mounted = True
                self.disk.save()
                logger.info(f"Successfully mounted {self.disk.device} to {self.path}")
                return True
            else:
                logger.error(f"Failed to mount {self.disk.device}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error mounting {self.disk.device}: {e}")
            return False

    def unmount(self):
        """Unmount the filesystem"""
        try:
            result = subprocess.run(['umount', self.path], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.disk.mount_point = ''
                self.disk.is_mounted = False
                self.disk.save()
                logger.info(f"Successfully unmounted {self.path}")
                return True
            else:
                logger.error(f"Failed to unmount {self.path}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error unmounting {self.path}: {e}")
            return False

class StoragePool(models.Model):
    """Storage pool grouping multiple mount points"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    mount_points = models.ManyToManyField(MountPoint, related_name='pools', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_size(self):
        """Total size of all mount points in pool"""
        total = 0
        for mp in self.mount_points.all():
            if mp.disk.usage:
                total += mp.disk.usage['total']
        return total

    @property
    def used_size(self):
        """Used size of all mount points in pool"""
        used = 0
        for mp in self.mount_points.all():
            if mp.disk.usage:
                used += mp.disk.usage['used']
        return used

    @property
    def available_size(self):
        """Available size in pool"""
        return self.total_size - self.used_size

    @property
    def usage_percent(self):
        """Usage percentage"""
        if self.total_size > 0:
            return (self.used_size / self.total_size) * 100
        return 0