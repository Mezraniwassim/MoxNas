#!/usr/bin/env python3
"""
MoxNAS - PCT Container Management for Proxmox

This module provides utilities to create and manage LXC containers
specifically configured for MoxNAS deployment.
"""

import os
import subprocess
import json
import argparse
from pathlib import Path
import sys

# Add parent directory to path to import secure_config
sys.path.append(str(Path(__file__).parent.parent / 'backend'))
try:
    from secure_config import SecureConfig
except ImportError:
    print("Warning: secure_config not found. Using default values.")
    SecureConfig = None


class ProxmoxPCTManager:
    """Manage LXC containers using PCT commands"""
    
    def __init__(self, template=None, storage=None):
        # Get configuration from environment or use defaults
        if SecureConfig:
            storage_config = SecureConfig.get_storage_config()
            container_config = SecureConfig.get_container_config()
            self.template = template or "debian-12-standard"
            self.storage = storage or storage_config.get('pool', 'local-lvm')
            default_password = container_config.get('root_password', 'moxnas123')
        else:
            self.template = template or "debian-12-standard"
            self.storage = storage or "local"
            default_password = "moxnas123"
        
        self.base_config = {
            "memory": 2048,
            "cores": 2,
            "disk": "8G",
            "features": ["nesting=1"],  # Required for some container operations
            "network": "name=eth0,bridge=vmbr0,ip=dhcp",
            "hostname": "moxnas",
            "password": default_password,  # From environment or default
        }
    
    def check_pct_available(self):
        """Check if PCT commands are available"""
        try:
            result = subprocess.run(['pct', '--version'], 
                                  capture_output=True, text=True, check=True)
            print(f"PCT available: {result.stdout.strip()}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: PCT commands not available. Are you running on Proxmox?")
            return False
    
    def list_templates(self):
        """List available LXC templates"""
        try:
            result = subprocess.run(['pveam', 'available', '--section', 'system'], 
                                  capture_output=True, text=True, check=True)
            print("Available templates:")
            print(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error listing templates: {e}")
            return False
    
    def get_next_vmid(self):
        """Get the next available VM ID"""
        try:
            result = subprocess.run(['pvesh', 'get', '/cluster/nextid'], 
                                  capture_output=True, text=True, check=True)
            return int(result.stdout.strip())
        except subprocess.CalledProcessError:
            # Fallback: scan existing VMs
            try:
                result = subprocess.run(['pct', 'list'], 
                                      capture_output=True, text=True, check=True)
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                vmids = []
                for line in lines:
                    parts = line.split()
                    if parts:
                        vmids.append(int(parts[0]))
                return max(vmids) + 1 if vmids else 100
            except:
                return 100  # Default starting ID
    
    def create_container(self, vmid=None, hostname=None, **kwargs):
        """Create a new LXC container for MoxNAS"""
        if not self.check_pct_available():
            return False
        
        if vmid is None:
            vmid = self.get_next_vmid()
        
        config = self.base_config.copy()
        config.update(kwargs)
        
        if hostname:
            config["hostname"] = hostname
        
        # Build PCT create command
        cmd = [
            'pct', 'create', str(vmid),
            f"{self.storage}:vztmpl/{self.template}.tar.zst",
            f"--memory={config['memory']}",
            f"--cores={config['cores']}",
            f"--rootfs={self.storage}:{config['disk']}",
            f"--hostname={config['hostname']}",
            f"--password={config['password']}",
            f"--net0={config['network']}",
            "--unprivileged=1",
            "--onboot=1",
        ]
        
        # Add features
        for feature in config.get("features", []):
            cmd.append(f"--features={feature}")
        
        try:
            print(f"Creating container {vmid} with hostname {config['hostname']}...")
            print(f"Command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"Container {vmid} created successfully!")
            print(result.stdout)
            
            return vmid
        except subprocess.CalledProcessError as e:
            print(f"Error creating container: {e}")
            print(f"Error output: {e.stderr}")
            return False
    
    def configure_storage_mounts(self, vmid, mount_points):
        """Configure storage mount points for the container"""
        for i, mount_point in enumerate(mount_points):
            host_path = mount_point.get("host_path")
            container_path = mount_point.get("container_path", f"/mnt/storage{i}")
            
            if not host_path:
                continue
            
            cmd = [
                'pct', 'set', str(vmid),
                f"--mp{i}={host_path},mp={container_path}"
            ]
            
            try:
                subprocess.run(cmd, check=True)
                print(f"Mount point {i}: {host_path} -> {container_path}")
            except subprocess.CalledProcessError as e:
                print(f"Error setting mount point {i}: {e}")
    
    def start_container(self, vmid):
        """Start the container"""
        try:
            subprocess.run(['pct', 'start', str(vmid)], check=True)
            print(f"Container {vmid} started successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error starting container: {e}")
            return False
    
    def install_moxnas(self, vmid):
        """Install MoxNAS into the container"""
        commands = [
            "apt-get update",
            "apt-get install -y python3 python3-pip python3-venv git curl",
            "git clone https://github.com/user/MoxNAS.git /opt/moxnas",
            "cd /opt/moxnas && python3 -m venv venv",
            "cd /opt/moxnas && source venv/bin/activate && pip install -r requirements.txt",
            "cd /opt/moxnas/backend && python manage.py migrate",
            "systemctl enable --now ssh"
        ]
        
        for cmd in commands:
            try:
                print(f"Executing: {cmd}")
                result = subprocess.run([
                    'pct', 'exec', str(vmid), '--', 'bash', '-c', cmd
                ], capture_output=True, text=True, check=True)
                print(f"✓ {cmd}")
            except subprocess.CalledProcessError as e:
                print(f"✗ Error executing '{cmd}': {e}")
                print(f"Error output: {e.stderr}")
                return False
        
        return True


def main():
    parser = argparse.ArgumentParser(description='MoxNAS PCT Container Manager')
    parser.add_argument('--action', choices=['create', 'list-templates', 'install'], 
                       default='create', help='Action to perform')
    parser.add_argument('--vmid', type=int, help='Container VM ID')
    parser.add_argument('--hostname', default='moxnas', help='Container hostname')
    parser.add_argument('--template', default='debian-12-standard', 
                       help='LXC template to use')
    parser.add_argument('--storage', default='local', help='Storage location')
    parser.add_argument('--memory', type=int, default=2048, help='Memory in MB')
    parser.add_argument('--cores', type=int, default=2, help='CPU cores')
    parser.add_argument('--mount-points', type=str, 
                       help='JSON string of mount points')
    
    args = parser.parse_args()
    
    manager = ProxmoxPCTManager(template=args.template, storage=args.storage)
    
    if args.action == 'list-templates':
        manager.list_templates()
    
    elif args.action == 'create':
        mount_points = []
        if args.mount_points:
            try:
                mount_points = json.loads(args.mount_points)
            except json.JSONDecodeError:
                print("Error: Invalid JSON format for mount-points")
                return
        
        vmid = manager.create_container(
            vmid=args.vmid,
            hostname=args.hostname,
            memory=args.memory,
            cores=args.cores
        )
        
        if vmid:
            if mount_points:
                manager.configure_storage_mounts(vmid, mount_points)
            
            if manager.start_container(vmid):
                print(f"\nContainer {vmid} created and started successfully!")
                print(f"You can access it with: pct enter {vmid}")
                print(f"Or via SSH: ssh root@<container-ip>")
    
    elif args.action == 'install':
        if not args.vmid:
            print("Error: --vmid required for install action")
            return
        
        if manager.install_moxnas(args.vmid):
            print(f"\nMoxNAS installed successfully in container {args.vmid}")
        else:
            print(f"Failed to install MoxNAS in container {args.vmid}")


if __name__ == "__main__":
    main()
