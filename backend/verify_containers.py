#!/usr/bin/env python3
"""
Verify container creation by checking Proxmox
"""

from proxmoxer import ProxmoxAPI
import time
from secure_config import SecureConfig

def check_container_creation():
    """Check if containers were actually created"""
    
    # Get secure configuration
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
        
        print("=== Verifying Container Creation ===")
        
        # Get containers from node 'pve'
        containers = api.nodes('pve').lxc.get()
        
        print(f"Total containers found: {len(containers)}")
        print("\nRecent containers (sorted by VMID):")
        
        # Sort by VMID and show details
        containers_sorted = sorted(containers, key=lambda x: int(x['vmid']), reverse=True)
        
        for container in containers_sorted[:10]:  # Show top 10 most recent
            vmid = container['vmid']
            name = container.get('name', 'N/A')
            status = container.get('status', 'unknown')
            
            # Get more details for specific containers we created
            if int(vmid) >= 995:  # Our test containers
                try:
                    config = api.nodes('pve').lxc(vmid).config.get()
                    hostname = config.get('hostname', 'N/A')
                    memory = config.get('memory', 'N/A')
                    rootfs = config.get('rootfs', 'N/A')
                    
                    print(f"\n🔍 Container {vmid}:")
                    print(f"   Name: {name}")
                    print(f"   Hostname: {hostname}")
                    print(f"   Status: {status}")
                    print(f"   Memory: {memory} MB")
                    print(f"   RootFS: {rootfs}")
                    
                    # Check if this looks like our test containers
                    if 'test-container' in hostname or 'debug-container' in hostname:
                        print(f"   ✅ This is our test container!")
                        
                except Exception as e:
                    print(f"   ❌ Error getting config for {vmid}: {e}")
            else:
                print(f"   Container {vmid}: {name} ({status})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = check_container_creation()
    if success:
        print("\n✅ Container verification completed")
    else:
        print("\n❌ Container verification failed")
