#!/usr/bin/env python3
"""Test Proxmox connection with the new configuration."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Import Django and configure it
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from proxmoxer import ProxmoxAPI
from proxmoxer.tools import Tasks

def test_proxmox_connection():
    """Test connection to Proxmox server."""
    try:
        print("=== Testing Proxmox Connection ===")
        print(f"Host: {settings.PROXMOX_CONFIG['HOST']}")
        print(f"User: {settings.PROXMOX_CONFIG['USER']}")
        print(f"Port: {settings.PROXMOX_CONFIG['PORT']}")
        print(f"SSL Verification: {settings.PROXMOX_CONFIG['VERIFY_SSL']}")
        
        # Create Proxmox API connection
        proxmox = ProxmoxAPI(
            settings.PROXMOX_CONFIG['HOST'],
            user=settings.PROXMOX_CONFIG['USER'],
            password=settings.PROXMOX_CONFIG['PASSWORD'],
            verify_ssl=settings.PROXMOX_CONFIG['VERIFY_SSL'],
            port=settings.PROXMOX_CONFIG['PORT']
        )
        
        print("\n=== Connection successful! ===")
        
        # Test basic API calls
        print("\n=== Getting cluster version ===")
        version = proxmox.version.get()
        print(f"Proxmox version: {version}")
        
        print("\n=== Getting nodes ===")
        nodes = proxmox.nodes.get()
        for node in nodes:
            print(f"Node: {node['node']} - Status: {node['status']} - Type: {node['type']}")
            
        print("\n=== Getting node resources ===")
        if nodes:
            first_node = nodes[0]['node']
            resources = proxmox.nodes(first_node).get()
            print(f"Node {first_node} details:")
            print(f"  CPU: {resources.get('cpu', 'N/A')}")
            print(f"  Memory: {resources.get('mem', 'N/A')} / {resources.get('maxmem', 'N/A')}")
            print(f"  Disk: {resources.get('disk', 'N/A')} / {resources.get('maxdisk', 'N/A')}")
            print(f"  Uptime: {resources.get('uptime', 'N/A')}")
            
            print(f"\n=== Getting containers on {first_node} ===")
            try:
                containers = proxmox.nodes(first_node).lxc.get()
                if containers:
                    for container in containers:
                        print(f"Container {container['vmid']}: {container.get('name', 'Unnamed')} - Status: {container['status']}")
                else:
                    print("No containers found")
            except Exception as e:
                print(f"Error getting containers: {e}")
                
            print(f"\n=== Getting VMs on {first_node} ===")
            try:
                vms = proxmox.nodes(first_node).qemu.get()
                if vms:
                    for vm in vms:
                        print(f"VM {vm['vmid']}: {vm.get('name', 'Unnamed')} - Status: {vm['status']}")
                else:
                    print("No VMs found")
            except Exception as e:
                print(f"Error getting VMs: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n=== Connection failed ===")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_proxmox_connection()
    if success:
        print("\n✅ Proxmox connection test passed!")
    else:
        print("\n❌ Proxmox connection test failed!")
        sys.exit(1)
