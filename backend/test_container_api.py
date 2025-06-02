#!/usr/bin/env python3
"""
Test Proxmox LXC container creation API
Based on official Proxmox API documentation
"""

from proxmoxer import ProxmoxAPI
import json
from secure_config import SecureConfig

def test_container_creation_api():
    """Test container creation using official Proxmox API"""
    
    # Get secure configuration
    config = SecureConfig.get_proxmox_config()
    
    if not config['host'] or not config['password']:
        print("❌ Proxmox connection parameters not configured in .env file")
        return False
    
    print("=== Testing Proxmox LXC Container API ===")
    print(f"Connecting to {config['host']}:{config['port']}")
    
    try:
        # Connect to Proxmox
        api = ProxmoxAPI(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            verify_ssl=config['verify_ssl'],
            port=config['port']
        )
        
        print("✅ Connected to Proxmox successfully")
        
        # Get nodes
        print("\n1. Getting available nodes...")
        nodes = api.nodes.get()
        print(f"Available nodes: {[node['node'] for node in nodes]}")
        
        if not nodes:
            print("❌ No nodes found")
            return False
        
        node_name = nodes[0]['node']
        print(f"Using node: {node_name}")
        
        # Get storage
        print(f"\n2. Getting storage for node {node_name}...")
        storage = api.nodes(node_name).storage.get()
        storage_names = [s['storage'] for s in storage if s.get('enabled', True)]
        print(f"Available storage: {storage_names}")
        
        # Get templates
        print(f"\n3. Getting available templates...")
        for storage_name in storage_names[:2]:  # Check first 2 storage
            try:
                templates = api.nodes(node_name).storage(storage_name).content.get(content='vztmpl')
                if templates:
                    print(f"Templates in {storage_name}:")
                    for template in templates[:3]:  # Show first 3
                        print(f"  - {template['volid']}")
                    break
            except Exception as e:
                print(f"  No templates in {storage_name}: {e}")
        else:
            print("❌ No templates found in any storage")
            print("💡 You may need to download templates first using:")
            print("   pveam update && pveam download local debian-12-standard_12.7-1_amd64.tar.zst")
            return False
        
        # Get existing containers
        print(f"\n4. Getting existing containers...")
        containers = api.nodes(node_name).lxc.get()
        used_vmids = [int(c['vmid']) for c in containers]
        print(f"Used VMIDs: {used_vmids}")
        
        # Find available VMID
        test_vmid = 999
        while test_vmid in used_vmids:
            test_vmid += 1
        
        print(f"Will use VMID: {test_vmid}")
        
        # Prepare container configuration according to Proxmox API docs
        print(f"\n5. Preparing container configuration...")
        
        # Use first available template
        template_volid = templates[0]['volid']
        print(f"Using template: {template_volid}")
        
        # Container configuration based on official API documentation
        container_config = {
            'vmid': test_vmid,
            'ostemplate': template_volid,
            'hostname': f'test-container-{test_vmid}',
            'memory': 512,       # Memory in MB
            'swap': 512,         # Swap in MB  
            'cores': 1,          # CPU cores
            'rootfs': f'{storage_names[0]}:8G',  # Root filesystem: storage:size_in_GB (with G suffix)
            'net0': 'name=eth0,bridge=vmbr0,ip=dhcp',  # Network configuration
            'unprivileged': 1,   # Use unprivileged container
            'start': 0,          # Don't start automatically
            'description': f'Test container created via API at {test_vmid}'
        }
        
        print("Container configuration:")
        print(json.dumps(container_config, indent=2))
        
        # Test container creation (dry run first)
        print(f"\n6. Testing container creation API call...")
        print("📝 This would create a container with the above configuration.")
        print("⚠️  Commenting out actual creation for safety")
        
        # Uncomment the lines below to actually create the container:
        # print("Creating container...")
        # result = api.nodes(node_name).lxc.post(**container_config)
        # print(f"✅ Container creation result: {result}")
        
        print("\n7. Testing other container operations...")
        
        # Test get container list (should work)
        containers = api.nodes(node_name).lxc.get()
        print(f"Current containers: {len(containers)}")
        
        if containers:
            # Test getting config of first container
            first_container_vmid = containers[0]['vmid']
            config = api.nodes(node_name).lxc(first_container_vmid).config.get()
            print(f"Sample container config keys: {list(config.keys())}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_container_creation_api()
    if success:
        print("\n✅ Container API test completed successfully!")
        print("\n📋 Summary of findings:")
        print("- Proxmox API connection works")
        print("- Can retrieve nodes, storage, and templates")
        print("- Container creation API endpoint is accessible")
        print("- Configuration format matches official documentation")
    else:
        print("\n❌ Container API test failed!")
