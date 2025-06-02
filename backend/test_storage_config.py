#!/usr/bin/env python3
"""
Test Proxmox storage configuration for container creation
"""

from proxmoxer import ProxmoxAPI
import json
from secure_config import SecureConfig

def test_storage_configuration():
    """Test storage configuration to understand correct format"""
    
    config = SecureConfig.get_proxmox_config()
    
    if not config['host'] or not config['password']:
        print("❌ Proxmox connection parameters not configured in .env file")
        return False
    
    try:
        api = ProxmoxAPI(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            verify_ssl=config['verify_ssl'],
            port=config['port']
        )
        
        print("=== Proxmox Storage Configuration Analysis ===")
        
        # Get nodes
        nodes = api.nodes.get()
        node_name = nodes[0]['node']
        print(f"Node: {node_name}")
        
        # Get storage details
        print("\n1. Storage Information:")
        storage_list = api.nodes(node_name).storage.get()
        
        for storage in storage_list:
            if storage.get('enabled', True):
                print(f"\nStorage: {storage['storage']}")
                print(f"  Type: {storage.get('type', 'Unknown')}")
                print(f"  Content: {storage.get('content', 'Unknown')}")
                print(f"  Enabled: {storage.get('enabled', True)}")
                print(f"  Shared: {storage.get('shared', False)}")
                
                # Get storage status
                try:
                    status = api.nodes(node_name).storage(storage['storage']).status.get()
                    print(f"  Total: {status.get('total', 0) / (1024**3):.1f} GB")
                    print(f"  Used: {status.get('used', 0) / (1024**3):.1f} GB")
                    print(f"  Available: {status.get('avail', 0) / (1024**3):.1f} GB")
                except Exception as e:
                    print(f"  Status error: {e}")
        
        # Check existing containers to see their rootfs format
        print("\n2. Existing Container rootfs formats:")
        containers = api.nodes(node_name).lxc.get()
        
        for container in containers[:3]:  # Check first 3 containers
            vmid = container['vmid']
            try:
                config = api.nodes(node_name).lxc(vmid).config.get()
                rootfs = config.get('rootfs', 'Not found')
                print(f"  Container {vmid}: rootfs = {rootfs}")
            except Exception as e:
                print(f"  Container {vmid}: Error getting config - {e}")
        
        # Test what rootfs formats work
        print("\n3. Recommended rootfs formats:")
        
        # For LVM storage, the format should be: storage:size
        lvm_storage = [s for s in storage_list if s.get('type') == 'lvmthin' and s.get('enabled', True)]
        dir_storage = [s for s in storage_list if s.get('type') == 'dir' and s.get('enabled', True)]
        
        if lvm_storage:
            print(f"  LVM Thin storage: {lvm_storage[0]['storage']}:8 (for 8GB)")
        if dir_storage:
            print(f"  Directory storage: {dir_storage[0]['storage']}:8 (for 8GB)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_storage_configuration()
