#!/usr/bin/env python3
"""
Test Proxmox connection and sync data for MoxNAS
"""

import os
import sys
import django
from secure_config import SecureConfig

# Add the backend directory to Python path
sys.path.append('/home/wassim/Documents/MoxNas/backend')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from proxmox_integration.manager import initialize_proxmox_connection, get_proxmox_manager
from proxmox_integration.models import ProxmoxHost


def test_proxmox_connection():
    """Test connection to Proxmox host and sync basic data"""
    
    # Get secure configuration from environment variables
    config = SecureConfig.get_proxmox_config()
    
    if not config['host'] or not config['password']:
        print("❌ Proxmox connection parameters not configured in .env file")
        print("Please check your .env file and ensure PROXMOX_HOST and PROXMOX_PASSWORD are set")
        return False
    
    print(f"Testing connection to Proxmox at {config['host']}:{config['port']}")
    print(f"User: {config['user']}")
    print("-" * 50)
    
    # Initialize connection
    success = initialize_proxmox_connection(
        config['host'], 
        config['user'], 
        config['password'], 
        config['port'], 
        config['verify_ssl']
    )
    
    if not success:
        print("❌ Failed to connect to Proxmox")
        return False
    
    print("✅ Connected to Proxmox successfully!")
    
    # Get manager instance
    manager = get_proxmox_manager()
    
    try:
        # Test cluster status
        print("\n📊 Getting cluster status...")
        cluster_status = manager.get_cluster_status()
        print(f"Cluster status: {cluster_status}")
        
        # Get nodes
        print("\n🖥️  Getting nodes...")
        nodes = manager.get_nodes()
        print(f"Found {len(nodes)} node(s):")
        
        for node in nodes:
            node_name = node.get('node')
            status = node.get('status')
            print(f"  - {node_name}: {status}")
            
            # Get node details
            node_status = manager.get_node_status(node_name)
            if 'uptime' in node_status:
                uptime_hours = node_status['uptime'] / 3600
                print(f"    Uptime: {uptime_hours:.1f} hours")
            
            if 'memory' in node_status:
                mem_total = node_status['memory'].get('total', 0) / (1024**3)  # GB
                mem_used = node_status['memory'].get('used', 0) / (1024**3)   # GB
                mem_percent = (mem_used / mem_total * 100) if mem_total > 0 else 0
                print(f"    Memory: {mem_used:.1f}GB / {mem_total:.1f}GB ({mem_percent:.1f}%)")
            
            # Get containers
            print(f"\n📦 Getting containers for node {node_name}...")
            containers = manager.get_containers(node_name)
            print(f"Found {len(containers)} container(s):")
            
            for container in containers:
                vmid = container.get('vmid')
                name = container.get('name', f'CT{vmid}')
                status = container.get('status')
                print(f"  - CT{vmid} ({name}): {status}")
            
            # Get storage
            print(f"\n💾 Getting storage for node {node_name}...")
            storage = manager.get_storage(node_name)
            print(f"Found {len(storage)} storage pool(s):")
            
            for store in storage:
                storage_id = store.get('storage')
                storage_type = store.get('type')
                enabled = store.get('enabled', 0) == 1
                status_text = "enabled" if enabled else "disabled"
                print(f"  - {storage_id} ({storage_type}): {status_text}")
                
                if 'total' in store and store['total'] > 0:
                    total_gb = store['total'] / (1024**3)
                    used_gb = store.get('used', 0) / (1024**3)
                    usage_percent = (used_gb / total_gb * 100) if total_gb > 0 else 0
                    print(f"    Usage: {used_gb:.1f}GB / {total_gb:.1f}GB ({usage_percent:.1f}%)")
        
        # Create/update ProxmoxHost record
        print(f"\n💾 Updating database record...")
        proxmox_host, created = ProxmoxHost.objects.get_or_create(
            host=config['host'],
            defaults={
                'name': f"Proxmox-{config['host']}",
                'user': config['user'],
                'port': config['port'],
                'verify_ssl': config['verify_ssl'],
                'is_connected': True,
                'is_active': True,
            }
        )
        
        if not created:
            proxmox_host.is_connected = True
            proxmox_host.is_active = True
            proxmox_host.save()
        
        action = "Created" if created else "Updated"
        print(f"✅ {action} ProxmoxHost record: {proxmox_host}")
        
        print(f"\n🎉 Proxmox integration test completed successfully!")
        print(f"You can now access Proxmox APIs at: http://localhost:8001/api/proxmox/")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_proxmox_connection()
