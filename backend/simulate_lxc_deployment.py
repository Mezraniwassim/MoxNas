#!/usr/bin/env python3
"""
Simulate testing MoxNAS functionality from within an LXC container
This script validates that all components are properly configured for deployment
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

from django.conf import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_django_configuration():
    """Test Django configuration and apps"""
    print("🔧 Testing Django Configuration...")
    
    # Check installed apps
    required_apps = [
        'proxmox_integration',
        'management', 
        'core',
        'storage',
        'services',
        'network',
        'users'
    ]
    
    for app in required_apps:
        if app in settings.INSTALLED_APPS:
            print(f"   ✅ {app} app installed")
        else:
            print(f"   ❌ {app} app missing")
            return False
    
    # Check Proxmox configuration
    proxmox_settings = [
        'PROXMOX_HOST',
        'PROXMOX_PORT', 
        'PROXMOX_USERNAME',
        'PROXMOX_PASSWORD'
    ]
    
    for setting in proxmox_settings:
        value = getattr(settings, setting, None)
        if value:
            if setting == 'PROXMOX_PASSWORD':
                print(f"   ✅ {setting}: ***")
            else:
                print(f"   ✅ {setting}: {value}")
        else:
            print(f"   ❌ {setting} not configured")
            return False
    
    return True

def test_imports():
    """Test that all required modules can be imported"""
    print("\n📦 Testing Module Imports...")
    
    try:
        from proxmox_integration.manager import ProxmoxManager
        print("   ✅ ProxmoxManager import successful")
    except ImportError as e:
        print(f"   ❌ ProxmoxManager import failed: {e}")
        return False
    
    try:
        from secure_config import SecureConfig
        print("   ✅ SecureConfig import successful")
    except ImportError as e:
        print(f"   ❌ SecureConfig import failed: {e}")
        return False
    
    try:
        from services.service_manager import SambaManager, NFSManager, FTPManager
        print("   ✅ Service managers import successful")
    except ImportError as e:
        print(f"   ❌ Service managers import failed: {e}")
        return False
    
    try:
        import proxmoxer
        print("   ✅ Proxmoxer library available")
    except ImportError as e:
        print(f"   ❌ Proxmoxer library missing: {e}")
        return False
    
    return True

def test_proxmox_manager_initialization():
    """Test ProxmoxManager can be initialized with current config"""
    print("\n🚀 Testing ProxmoxManager Initialization...")
    
    try:
        from proxmox_integration.manager import ProxmoxManager
        from secure_config import SecureConfig
        
        config = SecureConfig.get_proxmox_config()
        manager = ProxmoxManager(config)
        
        print("   ✅ ProxmoxManager initialized successfully")
        print(f"   📝 Host: {config['host']}:{config['port']}")
        print(f"   📝 User: {config['username']}@{config['realm']}")
        print(f"   📝 SSL Verify: {config['ssl_verify']}")
        
        # Note: We can't test actual connection from development environment
        print("   💡 Connection test skipped (requires Proxmox network access)")
        
        return True
    except Exception as e:
        print(f"   ❌ ProxmoxManager initialization failed: {e}")
        return False

def test_service_managers():
    """Test service managers can be initialized"""
    print("\n🛠️  Testing Service Managers...")
    
    try:
        from services.service_manager import SambaManager, NFSManager, FTPManager
        
        # Test Samba Manager
        samba = SambaManager()
        print("   ✅ SambaManager initialized")
        
        # Test NFS Manager  
        nfs = NFSManager()
        print("   ✅ NFSManager initialized")
        
        # Test FTP Manager
        ftp = FTPManager()
        print("   ✅ FTPManager initialized")
        
        return True
    except Exception as e:
        print(f"   ❌ Service manager initialization failed: {e}")
        return False

def test_database_models():
    """Test database models can be imported and are ready"""
    print("\n🗄️  Testing Database Models...")
    
    try:
        from proxmox_integration.models import ProxmoxHost, ProxmoxNode, ProxmoxContainer
        print("   ✅ Proxmox models imported successfully")
        
        # Test model creation (without saving)
        test_host = ProxmoxHost(
            name="test-host",
            host="172.16.135.128",
            port=8006,
            username="root",
            realm="pam"
        )
        print("   ✅ ProxmoxHost model can be instantiated")
        
        return True
    except Exception as e:
        print(f"   ❌ Database models test failed: {e}")
        return False

def simulate_lxc_container_operations():
    """Simulate LXC container operations that would work in Proxmox environment"""
    print("\n📦 Simulating LXC Container Operations...")
    
    try:
        from proxmox_integration.manager import ProxmoxManager
        from secure_config import SecureConfig
        
        config = SecureConfig.get_proxmox_config()
        manager = ProxmoxManager(config)
        
        # Simulate container creation parameters
        container_config = {
            'vmid': 999,
            'hostname': 'test-moxnas',
            'template': 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst',
            'memory': 2048,
            'cores': 2,
            'disk': 'local-lvm:20',
            'password': 'test-password',
            'net0': 'name=eth0,bridge=vmbr0,ip=dhcp'
        }
        
        print("   ✅ Container configuration prepared")
        print(f"   📝 VMID: {container_config['vmid']}")
        print(f"   📝 Hostname: {container_config['hostname']}")
        print(f"   📝 Memory: {container_config['memory']}MB")
        print(f"   📝 Cores: {container_config['cores']}")
        print("   💡 Actual container creation requires Proxmox API connection")
        
        return True
    except Exception as e:
        print(f"   ❌ Container operation simulation failed: {e}")
        return False

def main():
    """Run all deployment readiness tests"""
    print("🎯 MoxNAS LXC Deployment Readiness Test")
    print("=" * 50)
    
    tests = [
        ("Django Configuration", test_django_configuration),
        ("Module Imports", test_imports),
        ("ProxmoxManager", test_proxmox_manager_initialization),
        ("Service Managers", test_service_managers),
        ("Database Models", test_database_models),
        ("LXC Operations", simulate_lxc_container_operations)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        if test_func():
            passed += 1
        else:
            print(f"   ⚠️  {test_name} test failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 MoxNAS is ready for LXC deployment!")
        print("💡 Deploy to LXC container within Proxmox network for full connectivity")
    else:
        print("❌ Some tests failed - check configuration before deployment")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)