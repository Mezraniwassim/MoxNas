"""Storage management functionality for MoxNAS.

This module handles mount point-based storage operations for the TrueNAS Scale
LXC container, focusing on efficient storage management without ZFS dependencies.
"""

from typing import Optional, List, Dict, Union, Any
import logging
from pathlib import Path
import subprocess
import shutil
import os
import re

logger = logging.getLogger(__name__)

class StorageManager:
    """Manages storage operations for the TrueNAS Scale container."""

    def __init__(self, container_path: Path):
        """Initialize storage manager.
        
        Args:
            container_path: Path to the LXC container's root directory
        """
        self.container_path = container_path
        self.mounts_path = container_path / "rootfs" / "mnt"
        self.fstab_path = container_path / "fstab"
        self._mount_monitors = {}

    def ensure_mount_point(self, name: str) -> Path:
        """Ensure a mount point exists in the container.
        
        Args:
            name: Name of the mount point
            
        Returns:
            Path: Path to the created mount point
            
        Raises:
            OSError: If mount point creation fails
        """
        mount_path = self.mounts_path / name
        try:
            mount_path.mkdir(parents=True, exist_ok=True)
            return mount_path
        except Exception as e:
            logger.error(f"Failed to create mount point {mount_path}: {e}")
            raise OSError(f"Mount point creation failed: {e}")
            
    def is_mounted(self, mount_path: Path) -> bool:
        """Check if a path is mounted.
        
        Args:
            mount_path: Path to check
            
        Returns:
            bool: True if mounted, False otherwise
        """
        try:
            with open('/proc/mounts', 'r') as f:
                mounts = f.read()
                return str(mount_path.resolve()) in mounts
        except Exception as e:
            logger.error(f"Error checking mount status: {e}")
            return False
            
    def mount_directory(self, source: Path, mount_point: str, options: Optional[List[str]] = None) -> bool:
        """Mount a directory into the container.
        
        Args:
            source: Source directory to mount
            mount_point: Name of the mount point in the container
            options: Optional mount options
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            target = self.ensure_mount_point(mount_point)
            
            cmd = ["mount"]
            if options:
                cmd.extend(["-o", ",".join(options)])
            cmd.extend([str(source), str(target)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Mount failed: {result.stderr}")
                return False
                
            # Return success for mount operations
            return True
        except Exception as e:
            logger.error(f"Error mounting directory: {e}")
            return False
            
    def mount_device(self, device_path: Path, mount_point: str, filesystem: str = "ext4",
                    options: Optional[List[str]] = None) -> bool:
        """Mount a device into the container.
        
        Args:
            device_path: Path to the device (/dev/...)
            mount_point: Name of the mount point in the container
            filesystem: Filesystem type (default: ext4)
            options: Optional mount options
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If device path doesn't exist or isn't a block device
        """
        if not device_path.exists() or not device_path.is_block_device():
            raise ValueError(f"Invalid block device: {device_path}")
            
        try:
            target = self.ensure_mount_point(mount_point)
            
            cmd = ["mount", "-t", filesystem]
            if options:
                cmd.extend(["-o", ",".join(options)])
            cmd.extend([str(device_path), str(target)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Device mount failed: {result.stderr}")
                return False
                
            # Return success for device mount
            return True
        except Exception as e:
            logger.error(f"Error mounting device: {e}")
            return False
            
    def bind_mount(self, source: Path, mount_point: str,
                  read_only: bool = False) -> bool:
        """Create a bind mount in the container.
        
        Args:
            source: Source directory to bind mount
            mount_point: Name of the mount point in the container
            read_only: Make mount read-only if True
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not source.exists():
                logger.error(f"Source path does not exist: {source}")
                return False
                
            target = self.ensure_mount_point(mount_point)
            
            # First create the bind mount
            cmd = ["mount", "--bind", str(source), str(target)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Bind mount failed: {result.stderr}")
                return False
                
            # Make read-only if requested
            if read_only:
                remount_cmd = ["mount", "-o", "remount,ro", str(target)]
                result = subprocess.run(remount_cmd, capture_output=True, text=True, check=False)
                if result.returncode != 0:
                    logger.error(f"Failed to make mount read-only: {result.stderr}")
                    # Try to cleanup
                    subprocess.run(["umount", str(target)], capture_output=True)
                    return False
                    
            # Return success for bind mount operations
            return True
        except Exception as e:
            logger.error(f"Error creating bind mount: {e}")
            return False
            
    def add_to_fstab(self, source: Union[Path, str], mount_point: str,
                     fs_type: str = "none", options: Optional[List[str]] = None) -> bool:
        """Add a mount entry to container's fstab.
        
        Args:
            source: Source path or device
            mount_point: Mount point path (relative to container root)
            fs_type: Filesystem type
            options: Mount options
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            target = self.mounts_path / mount_point
            options = options or []
            
            # Ensure target path is relative to container root
            target_rel = target.relative_to(self.container_path / "rootfs")
            
            # Create fstab entry
            entry = f"{source} /{target_rel} {fs_type} {','.join(options)} 0 0\n"
            
            # Add to fstab if not already present
            if self.fstab_path.exists():
                with open(self.fstab_path, 'r') as f:
                    if any(line.startswith(str(source)) for line in f):
                        logger.warning(f"Mount entry for {source} already exists")
                        return False
                        
            with open(self.fstab_path, 'a') as f:
                f.write(entry)
                
            return True
        except Exception as e:
            logger.error(f"Error adding fstab entry: {e}")
            return False
            
    def unmount(self, mount_point: str, force: bool = False) -> bool:
        """Unmount a mounted directory.
        
        Args:
            mount_point: Name of the mount point
            force: Force unmount even if busy
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            target = self.mounts_path / mount_point
            
            # If not mounted and not forcing, nothing to do
            if not self.is_mounted(target) and not force:
                logger.warning(f"Mount point not mounted: {mount_point}")
                return True
                
            # Build unmount command, include force flag if requested
            cmd = ["umount"]
            if force:
                cmd.append("-f")
            cmd.append(str(target))
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Unmount failed: {result.stderr}")
                return False
                
            return not self.is_mounted(target)
        except Exception as e:
            logger.error(f"Error unmounting directory: {e}")
            return False
            
    def monitor_mount(self, mount_point: str, check_interval: int = 60) -> bool:
        """Set up monitoring for a mount point.
        
        Args:
            mount_point: Name of the mount point to monitor
            check_interval: How often to check mount status in seconds
            
        Returns:
            bool: True if monitoring was set up successfully
        """
        try:
            target = self.mounts_path / mount_point
            
            # Only monitor if the mount point exists and is mounted
            if not target.exists() or not self.is_mounted(target):
                logger.error(f"Mount point {mount_point} does not exist or is not mounted")
                return False

            # Check if systemd service unit already exists
            service_name = f"moxnas-mount-{mount_point}.service"
            service_path = Path("/etc/systemd/system") / service_name
            
            # Create systemd service unit for monitoring
            service_content = f"""[Unit]
Description=MoxNAS mount monitor for {mount_point}
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 -c '
import time, sys, os
from pathlib import Path
while True:
    try:
        target = Path("{target}")
        if not target.exists() or os.statvfs(str(target)).f_blocks == 0:
            sys.stderr.write("Mount {mount_point} is unavailable\\n")
            sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error checking mount {mount_point}: {{e}}\\n")
        sys.exit(1)
    time.sleep({check_interval})
'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
            # Write and enable systemd service
            try:
                with open(service_path, 'w') as f:
                    f.write(service_content)
                
                # Set correct permissions
                service_path.chmod(0o644)
                
                # Reload systemd and enable/start service
                subprocess.run(["systemctl", "daemon-reload"], check=True)
                subprocess.run(["systemctl", "enable", service_name], check=True)
                subprocess.run(["systemctl", "start", service_name], check=True)
                
                self._mount_monitors[mount_point] = service_name
                logger.info(f"Mount monitoring enabled for {mount_point}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to create mount monitor service: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to set up mount monitoring: {e}")
            return False
            
    def check_mount_status(self, mount_point: str) -> Dict[str, Any]:
        """Check the current status of a monitored mount point.
        
        Args:
            mount_point: Name of the mount point to check
            
        Returns:
            Dict containing status information:
            {
                'monitored': bool,
                'mounted': bool,
                'service_active': bool,
                'last_error': Optional[str]
            }
        """
        try:
            target = self.mounts_path / mount_point
            service_name = self._mount_monitors.get(mount_point)
            
            if not service_name:
                return {
                    'monitored': False,
                    'mounted': self.is_mounted(target),
                    'service_active': False,
                    'last_error': None
                }
                
            # Check systemd service status
            result = subprocess.run(
                ["systemctl", "status", service_name],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Get last error from journal if service failed
            last_error = None
            if result.returncode != 0:
                journal = subprocess.run(
                    ["journalctl", "-u", service_name, "-n", "1"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                last_error = journal.stdout.strip() if journal.stdout else None
                
            return {
                'monitored': True,
                'mounted': self.is_mounted(target),
                'service_active': result.returncode == 0,
                'last_error': last_error
            }
            
        except Exception as e:
            logger.error(f"Failed to check mount status: {e}")
            return {
                'monitored': False,
                'mounted': False,
                'service_active': False,
                'last_error': str(e)
            }
            
    def stop_monitoring(self, mount_point: str) -> bool:
        """Stop monitoring a mount point.
        
        Args:
            mount_point: Name of the mount point to stop monitoring
            
        Returns:
            bool: True if monitoring was stopped successfully
        """
        try:
            service_name = self._mount_monitors.get(mount_point)
            if not service_name:
                logger.warning(f"Mount point {mount_point} is not being monitored")
                return True
                
            # Stop and disable systemd service
            subprocess.run(["systemctl", "stop", service_name], check=False)
            subprocess.run(["systemctl", "disable", service_name], check=False)
            
            # Remove service file
            service_path = Path("/etc/systemd/system") / service_name
            if service_path.exists():
                service_path.unlink()
                
            # Reload systemd
            subprocess.run(["systemctl", "daemon-reload"], check=False)
            
            del self._mount_monitors[mount_point]
            logger.info(f"Mount monitoring disabled for {mount_point}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop mount monitoring: {e}")
            return False