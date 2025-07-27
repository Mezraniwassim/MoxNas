#!/usr/bin/env python3
"""
Test Proxmox connection from MoxNAS container
Quick verification that Proxmox integration is working
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

def test_proxmox_connection():
    """Test Proxmox API connection and basic functionality"""
    print("🔧 Testing Proxmox Integration")
    print("=" * 50)
    
    try:
        from proxmox_integration.manager import get_proxmox_manager
        from secure_config import SecureConfig
        
        # Get configuration
        config = SecureConfig.get_proxmox_config()
        
        print(f"📍 Proxmox Host: {config.get('host', 'NOT_CONFIGURED')}")
        print(f"👤 Username: {config.get('username', 'NOT_CONFIGURED')}")
        print(f"🔒 Realm: {config.get('realm', 'pam')}")
        print(f"🌐 Port: {config.get('port', 8006)}")
        print(f"🔐 SSL Verify: {config.get('ssl_verify', False)}")
        print()
        
        if not config.get('host') or not config.get('password'):
            print("⚠️  Proxmox not configured yet")
            print("💡 Run configure_proxmox.sh to set up connection")
            return False
        
        # Test connection
        print("🔌 Testing connection...")
        manager = get_proxmox_manager()
        
        if manager and manager.connect():
            print("✅ CONNECTION SUCCESSFUL!")
            
            # Test basic operations
            print("\n📊 Testing basic operations...")
            
            # Get cluster status
            try:
                nodes = manager.get_nodes()
                print(f"🖥️  Found {len(nodes)} Proxmox nodes:")
                for node in nodes[:3]:  # Show first 3 nodes
                    name = node.get('node', 'unknown')
                    status = node.get('status', 'unknown')
                    print(f"   • {name}: {status}")
                
                # Get containers
                containers = manager.get_containers()
                print(f"📦 Found {len(containers)} containers")
                
                print("\n🎉 Proxmox integration is WORKING!")
                return True
                
            except Exception as e:
                print(f"⚠️  Connection successful but API test failed: {e}")
                return False
                
        else:
            print("❌ CONNECTION FAILED!")
            print("💡 Check your Proxmox credentials and network connectivity")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure all dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def show_configuration_help():
    """Show help for configuring Proxmox"""
    print("\n" + "=" * 50)
    print("🔧 PROXMOX CONFIGURATION HELP")
    print("=" * 50)
    print()
    print("To configure Proxmox connection, you have several options:")
    print()
    print("1️⃣ AUTOMATED SETUP (Recommended)")
    print("   Run on Proxmox host:")
    print("   curl -sSL https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/configure_proxmox.sh | bash -s -- --interactive")
    print()
    print("2️⃣ MANUAL SETUP")
    print("   Create/edit .env file in MoxNAS:")
    print("   echo 'PROXMOX_HOST=your.proxmox.host' >> /opt/moxnas/.env")
    print("   echo 'PROXMOX_USERNAME=root' >> /opt/moxnas/.env")
    print("   echo 'PROXMOX_PASSWORD=your_password' >> /opt/moxnas/.env")
    print("   systemctl restart moxnas")
    print()
    print("3️⃣ WEB INTERFACE")
    print("   • Access MoxNAS web interface")
    print("   • Go to Proxmox tab")
    print("   • Add your Proxmox nodes")
    print()

def main():
    """Main test function"""
    success = test_proxmox_connection()
    
    if not success:
        show_configuration_help()
        sys.exit(1)
    else:
        print("\n✨ Ready to manage containers via MoxNAS web interface!")
        sys.exit(0)

if __name__ == "__main__":
    main()
