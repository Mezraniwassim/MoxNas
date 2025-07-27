#!/usr/bin/env python3
"""
Test live Proxmox connection
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

def test_live_connection():
    print("🔗 Testing live Proxmox connection...")
    
    try:
        from proxmox_integration.manager import ProxmoxManager
        from secure_config import SecureConfig
        
        config = SecureConfig.get_proxmox_config()
        print(f"📝 Config: {config['host']}:{config['port']} as {config['username']}@{config['realm']}")
        
        manager = ProxmoxManager(config)
        
        if manager.connect():
            print("✅ Connection successful!")
            
            # Test getting nodes
            try:
                nodes = manager.get_nodes()
                print(f"✅ Found {len(nodes)} nodes:")
                for node in nodes:
                    print(f"   - {node.get('node', 'unknown')} ({node.get('status', 'unknown')})")
            except Exception as e:
                print(f"❌ Failed to get nodes: {e}")
            
            # Test getting containers
            try:
                containers = manager.get_containers('pve')  # Use the node we found
                print(f"✅ Found {len(containers)} containers")
                if containers:
                    for container in containers[:3]:  # Show first 3
                        print(f"   - {container.get('vmid')}: {container.get('name', 'unnamed')} ({container.get('status')})")
            except Exception as e:
                print(f"❌ Failed to get containers: {e}")
            
        else:
            print("❌ Connection failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_live_connection()