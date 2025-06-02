#!/usr/bin/env python3
"""Simple test of Proxmox connection without Django."""

import os
from pathlib import Path
from dotenv import load_dotenv
from proxmoxer import ProxmoxAPI

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

def test_proxmox_direct():
    """Test connection to Proxmox server directly."""
    try:
        # Get configuration from environment
        host = os.getenv('PROXMOX_HOST')
        user = os.getenv('PROXMOX_USER', 'root@pam')
        password = os.getenv('PROXMOX_PASSWORD')
        verify_ssl = os.getenv('PROXMOX_VERIFY_SSL', 'False').lower() == 'true'
        port = int(os.getenv('PROXMOX_PORT', '8006'))
        
        print("=== Testing Proxmox Connection (Direct) ===")
        print(f"Host: {host}")
        print(f"User: {user}")
        print(f"Port: {port}")
        print(f"SSL Verification: {verify_ssl}")
        
        if not host or not password:
            print("❌ Missing host or password in environment variables")
            return False
        
        # Create Proxmox API connection
        proxmox = ProxmoxAPI(
            host,
            user=user,
            password=password,
            verify_ssl=verify_ssl,
            port=port
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
            resources = proxmox.nodes(first_node).status.get()
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
                
            print(f"\n=== Getting storage ===")
            try:
                storage = proxmox.nodes(first_node).storage.get()
                if storage:
                    for stor in storage:
                        print(f"Storage: {stor['storage']} - Type: {stor['type']} - Status: {stor.get('status', 'N/A')}")
                else:
                    print("No storage found")
            except Exception as e:
                print(f"Error getting storage: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n=== Connection failed ===")
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_proxmox_direct()
    if success:
        print("\n✅ Proxmox connection test passed!")
    else:
        print("\n❌ Proxmox connection test failed!")
