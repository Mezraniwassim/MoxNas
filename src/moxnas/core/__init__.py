"""Core container management functionality for MoxNAS.

This module provides the base container management capabilities required for
running TrueNAS Scale in an LXC environment.
"""

from typing import Optional, Dict, List, Tuple, Any
import logging
import subprocess
from pathlib import Path
import shutil
import os
import yaml
import time

logger = logging.getLogger(__name__)

class ContainerManager:
    """Manages LXC container operations for TrueNAS Scale."""
    
    def __init__(self, container_name: str, base_path: Optional[Path] = None):
        """Initialize container manager.
        
        Args:
            container_name: Name of the LXC container
            base_path: Base path for container storage, defaults to /var/lib/lxc
        """
        self.container_name = container_name
        self.base_path = base_path or Path("/var/lib/lxc")
        self.container_path = self.base_path / container_name
        self.config_path = self.container_path / "config"
        
    def check_container_exists(self) -> bool:
        """Check if the container exists.
        
        Returns:
            bool: True if container exists, False otherwise
        """
        try:
            result = subprocess.run(
                ["lxc-info", "-n", self.container_name],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error checking container existence: {e}")
            return False
            
    def get_container_status(self) -> Optional[str]:
        """Get current container status.
        
        Returns:
            Optional[str]: Container status (RUNNING, STOPPED, etc.) or None if error
        """
        try:
            result = subprocess.run(
                ["lxc-info", "-n", self.container_name, "-s"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split()[-1]
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return None
            
    def create_container(self, template_path: Path, config: Dict[str, Any]) -> bool:
        """Create a new TrueNAS Scale container.
        """
        try:
            if self.check_container_exists():
                logger.error(f"Container {self.container_name} already exists")
                return False
            
            # Create container from template
            cmd = [
                "lxc-create",
                "-n", self.container_name,
                "-t", str(template_path),
                "-B", config.get("backend", "dir")
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Container creation failed: {result.stderr}")
                return False
            
            # Ensure config file exists so update_config can read it
            if not self.config_path.exists():
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                self.config_path.write_text("")
            
            # Apply configuration
            return self.update_config(config)
        except Exception as e:
            logger.error(f"Error creating container: {e}")
            return False
            
    def update_config(self, config: Dict[str, Any]) -> bool:
        """Update container configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.config_path, 'r') as f:
                current_config = f.read()
                
            # Update configuration while preserving comments
            new_config = []
            for line in current_config.splitlines():
                if line.startswith('#') or not line.strip():
                    new_config.append(line)
                    continue
                    
                key = line.split('=')[0].strip()
                if key in config:
                    new_config.append(f"{key} = {config[key]}")
                    del config[key]
                else:
                    new_config.append(line)
                    
            # Add new configuration options
            for key, value in config.items():
                if not key.startswith('#'):
                    new_config.append(f"{key} = {value}")
                    
            with open(self.config_path, 'w') as f:
                f.write('\n'.join(new_config))
                
            return True
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return False
            
    def start(self, wait: bool = True, timeout: int = 60) -> bool:
        """Start the container.
        
        Args:
            wait: Wait for container to be running
            timeout: Timeout in seconds when waiting
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.check_container_exists():
                logger.error(f"Container {self.container_name} does not exist")
                return False
                
            cmd = ["lxc-start", "-n", self.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Container start failed: {result.stderr}")
                return False
                
            if wait:
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.get_container_status() == "RUNNING":
                        return True
                    time.sleep(1)
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error starting container: {e}")
            return False
            
    def stop(self, timeout: int = 30) -> bool:
        """Stop the container.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.check_container_exists():
                logger.error(f"Container {self.container_name} does not exist")
                return False
                
            cmd = ["lxc-stop", "-n", self.container_name, "-t", str(timeout)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Container stop failed: {result.stderr}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            return False
            
    def clone(self, new_name: str, snapshot: bool = True) -> bool:
        """Clone the container.
        
        Args:
            new_name: Name for the cloned container
            snapshot: Use snapshot clone if True
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.check_container_exists():
                logger.error(f"Container {self.container_name} does not exist")
                return False
                
            cmd = ["lxc-copy", "-n", self.container_name, "-N", new_name]
            if snapshot:
                cmd.append("-s")
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Container clone failed: {result.stderr}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error cloning container: {e}")
            return False
            
    def snapshot(self, name: str) -> bool:
        """Create a container snapshot.
        
        Args:
            name: Name of the snapshot
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.check_container_exists():
                logger.error(f"Container {self.container_name} does not exist")
                return False
                
            snapshot_path = self.container_path / "snaps" / name
            # Ensure snaps directory exists (including container path)
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            
            cmd = ["lxc-snapshot", "-n", self.container_name, "-N", name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Snapshot creation failed: {result.stderr}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error creating snapshot: {e}")
            return False
            
    def restore_snapshot(self, name: str) -> bool:
        """Restore a container snapshot.
        
        Args:
            name: Name of the snapshot to restore
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.check_container_exists():
                logger.error(f"Container {self.container_name} does not exist")
                return False
                
            snapshot_path = self.container_path / "snaps" / name
            if not snapshot_path.exists():
                logger.error(f"Snapshot {name} does not exist")
                return False
                
            # Stop container if running
            if self.get_container_status() == "RUNNING":
                self.stop()
                
            cmd = ["lxc-snapshot", "-n", self.container_name, "-r", name]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Snapshot restore failed: {result.stderr}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error restoring snapshot: {e}")
            return False