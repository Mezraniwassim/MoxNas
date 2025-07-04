#!/usr/bin/env python3
"""
Proxmox Connectivity Test Script for MoxNAS
Tests various aspects of Proxmox API connectivity and provides debugging information
"""

import os
import sys
import socket
import requests
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(InsecureRequestWarning)

# Add backend to path for Django imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

def test_network_connectivity(host, port=8006):
    """Test basic network connectivity to Proxmox host"""
    print(f"🌐 Testing network connectivity to {host}:{port}...")
    
    try:
        # Test if port is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"   ✅ Port {port} is open on {host}")
            return True
        else:
            print(f"   ❌ Port {port} is closed or filtered on {host}")
            return False
            
    except socket.gaierror as e:
        print(f"   ❌ DNS resolution failed for {host}: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Network connectivity test failed: {e}")
        return False

def test_proxmox_web_interface(host, port=8006):
    """Test if Proxmox web interface is accessible"""
    print(f"🌐 Testing Proxmox web interface at https://{host}:{port}...")
    
    try:
        url = f"https://{host}:{port}/api2/json/version"
        response = requests.get(url, verify=False, timeout=10)
        
        if response.status_code == 200:
            version_info = response.json()
            print(f"   ✅ Proxmox web interface accessible")
            print(f"   📊 Version: {version_info.get('data', {}).get('version', 'Unknown')}")
            return True
        else:
            print(f"   ❌ Proxmox web interface returned status {response.status_code}")
            return False
            
    except requests.exceptions.SSLError as e:
        print(f"   ❌ SSL Error: {e}")
        print("   💡 This is normal for self-signed certificates")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection Error: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"   ❌ Timeout Error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def test_authentication(host, username, password, realm='pam', port=8006):
    """Test Proxmox authentication"""
    print(f"🔐 Testing authentication for {username}@{realm}...")
    
    try:
        url = f"https://{host}:{port}/api2/json/access/ticket"
        data = {
            'username': f"{username}@{realm}",
            'password': password
        }
        
        response = requests.post(url, data=data, verify=False, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('data', {}).get('ticket'):
                print(f"   ✅ Authentication successful")
                return True
            else:
                print(f"   ❌ Authentication failed: No ticket received")
                return False
        else:
            print(f"   ❌ Authentication failed with status {response.status_code}")
            if response.status_code == 401:
                print("   💡 Check username and password")
            return False
            
    except Exception as e:
        print(f"   ❌ Authentication test failed: {e}")
        return False

def test_django_proxmox_integration():
    """Test Django Proxmox integration"""
    print("🔧 Testing Django Proxmox integration...")
    
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
        django.setup()
        
        from proxmox_integration.manager import ProxmoxManager
        from secure_config import SecureConfig
        
        config = SecureConfig.get_proxmox_config()
        print(f"   📝 Config loaded: {config['host']}:{config['port']}")
        
        manager = ProxmoxManager(config)
        print("   ✅ ProxmoxManager initialized")
        
        return True, manager, config
        
    except Exception as e:
        print(f"   ❌ Django integration test failed: {e}")
        return False, None, None

def test_proxmox_api_endpoints(manager, config):
    """Test specific Proxmox API endpoints"""
    print("🔍 Testing Proxmox API endpoints...")
    
    try:
        # Test connection
        if manager.connect():
            print("   ✅ Manager connection successful")
            
            # Test nodes
            try:
                nodes = manager.get_nodes()
                print(f"   ✅ Found {len(nodes)} node(s)")
                for node in nodes[:3]:  # Show first 3 nodes
                    print(f"      - {node.get('node', 'unknown')} ({node.get('status', 'unknown')})")
            except Exception as e:
                print(f"   ❌ Failed to get nodes: {e}")
            
            # Test containers
            try:
                containers = manager.get_containers()
                print(f"   ✅ Found {len(containers)} container(s)")
            except Exception as e:
                print(f"   ❌ Failed to get containers: {e}")
                
            return True
        else:
            print("   ❌ Manager connection failed")
            return False
            
    except Exception as e:
        print(f"   ❌ API endpoint test failed: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 60)
    print("🚀 MoxNAS Proxmox Connectivity Test")
    print("=" * 60)
    
    # Load configuration
    print("📋 Loading configuration from .env file...")
    
    # Check if .env exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_file):
        print(f"   ❌ .env file not found at {env_file}")
        print("   💡 Please create .env file with Proxmox credentials")
        return False
    
    # Parse .env file
    config = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()
    
    host = config.get('PROXMOX_HOST', '')
    username = config.get('PROXMOX_USER', 'root@pam').split('@')[0]
    password = config.get('PROXMOX_PASSWORD', '')
    realm = config.get('PROXMOX_USER', 'root@pam').split('@')[1] if '@' in config.get('PROXMOX_USER', '') else 'pam'
    port = int(config.get('PROXMOX_PORT', 8006))
    
    if not host or not password:
        print("   ❌ Missing Proxmox host or password in .env file")
        return False
    
    print(f"   ✅ Configuration loaded: {username}@{realm} -> {host}:{port}")
    
    # Run tests
    tests_passed = 0
    total_tests = 5
    
    # Test 1: Network connectivity
    if test_network_connectivity(host, port):
        tests_passed += 1
    
    # Test 2: Web interface
    if test_proxmox_web_interface(host, port):
        tests_passed += 1
    
    # Test 3: Authentication
    if test_authentication(host, username, password, realm, port):
        tests_passed += 1
    
    # Test 4: Django integration
    django_ok, manager, django_config = test_django_proxmox_integration()
    if django_ok:
        tests_passed += 1
    
    # Test 5: API endpoints (only if Django integration works)
    if django_ok and manager:
        if test_proxmox_api_endpoints(manager, django_config):
            tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    print("=" * 60)
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Proxmox connectivity is working correctly.")
        return True
    elif tests_passed >= 3:
        print("⚠️  Most tests passed. Minor issues detected.")
        return True
    else:
        print("❌ Multiple tests failed. Check network and configuration.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)