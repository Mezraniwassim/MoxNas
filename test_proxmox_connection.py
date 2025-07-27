#!/usr/bin/env python3
"""
Test Proxmox Connection
Verify that MoxNAS can connect to Proxmox with the provided credentials
"""

import os
import sys
from pathlib import Path
from decouple import config

# Add the backend directory to Python path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')

import django
django.setup()

from proxmox.proxmox_client import ProxmoxAPI

def test_proxmox_connection():
    """Test connection to Proxmox using environment variables"""
    print("🧪 Testing Proxmox Connection")
    print("=" * 50)
    
    # Load configuration from .env
    host = config('PROXMOX_HOST', default='')
    port = config('PROXMOX_PORT', default=8006, cast=int)
    username = config('PROXMOX_USERNAME', default='root')
    password = config('PROXMOX_PASSWORD', default='')
    realm = config('PROXMOX_REALM', default='pam')
    ssl_verify = config('PROXMOX_SSL_VERIFY', default=False, cast=bool)
    
    print(f"🔧 Configuration:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Username: {username}@{realm}")
    print(f"   SSL Verify: {ssl_verify}")
    print()
    
    if not host or not password:
        print("❌ Error: PROXMOX_HOST and PROXMOX_PASSWORD must be set in .env file")
        return False
    
    try:
        # Create Proxmox API client
        client = ProxmoxAPI(
            host=host,
            port=port,
            username=username,
            password=password,
            realm=realm,
            ssl_verify=ssl_verify
        )
        
        print("🔐 Testing authentication...")
        if client.authenticate():
            print("✅ Authentication successful!")
            
            # Test getting nodes
            print("\n📡 Testing node listing...")
            nodes = client.get_nodes()
            print(f"✅ Found {len(nodes)} Proxmox nodes:")
            for node in nodes:
                print(f"   - {node.get('node', 'Unknown')} (Status: {node.get('status', 'Unknown')})")
            
            # Test getting containers
            print("\n📦 Testing container listing...")
            containers = client.get_containers()
            print(f"✅ Found {len(containers)} LXC containers:")
            for container in containers[:5]:  # Show first 5
                vmid = container.get('vmid', 'Unknown')
                name = container.get('name', 'Unnamed')
                status = container.get('status', 'Unknown')
                print(f"   - CT{vmid}: {name} ({status})")
            
            if len(containers) > 5:
                print(f"   ... and {len(containers) - 5} more containers")
            
            print("\n🎉 Proxmox connection test successful!")
            print("\n💡 You can now:")
            print("   1. Start MoxNAS: python3 start_moxnas.py")
            print("   2. Access web interface: http://localhost:8080")
            print("   3. Go to Proxmox tab to manage containers")
            
            return True
            
        else:
            print("❌ Authentication failed!")
            print("   Check your username and password in .env file")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check if Proxmox host is reachable")
        print("   2. Verify credentials in .env file")
        print("   3. Check if Proxmox web interface is accessible")
        print(f"   4. Try: https://{host}:{port}")
        return False

if __name__ == "__main__":
    success = test_proxmox_connection()
    sys.exit(0 if success else 1)