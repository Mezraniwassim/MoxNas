#!/usr/bin/env python3
"""
Test script to run inside LXC container to verify Proxmox connectivity
This should be run from within the deployed MoxNAS LXC container
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from proxmox_integration.manager import ProxmoxManager
from secure_config import SecureConfig

def test_from_container():
    """Test Proxmox connectivity from within LXC container"""
    print("🔧 Testing Proxmox connectivity from LXC container...")
    
    try:
        # Get configuration
        config = SecureConfig.get_proxmox_config()
        print(f"📝 Using config: {config['host']}:{config['port']}")
        print(f"👤 User: {config['username']}@{config['realm']}")
        
        # Create manager
        manager = ProxmoxManager(config)
        
        # Test connection
        print("🔌 Attempting to connect...")
        if manager.connect():
            print("✅ Connected to Proxmox successfully!")
            
            # Test operations
            print("📋 Testing API operations...")
            
            # Get nodes
            nodes = manager.get_nodes()
            print(f"🖥️  Found {len(nodes)} node(s):")
            for node in nodes:
                print(f"   - {node.get('node', 'unknown')} ({node.get('status', 'unknown')})")
            
            # Get containers
            containers = manager.get_containers()
            print(f"📦 Found {len(containers)} container(s):")
            for container in containers[:5]:  # Show first 5
                print(f"   - CT{container.get('vmid', '?')} {container.get('name', 'unknown')} ({container.get('status', 'unknown')})")
            
            print("🎉 All Proxmox operations successful!")
            return True
            
        else:
            print("❌ Failed to connect to Proxmox")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_from_container()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Proxmox connectivity test")
    sys.exit(0 if success else 1)