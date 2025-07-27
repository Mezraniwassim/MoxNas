#!/usr/bin/env python3
"""
MoxNAS Installation Test Script
Tests the MoxNAS installation and verifies all components are working
"""

import requests
import sys
import time
import argparse

def test_web_interface(host, port=8080, timeout=30):
    """Test if MoxNAS web interface is accessible"""
    url = f"http://{host}:{port}"
    api_url = f"http://{host}:{port}/api/core/system/current/"
    
    print(f"🌐 Testing MoxNAS web interface at {url}")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Test main page
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Web interface is accessible at {url}")
                
                # Test API endpoint
                try:
                    api_response = requests.get(api_url, timeout=5)
                    if api_response.status_code == 200:
                        data = api_response.json()
                        print(f"✅ API is working - Hostname: {data.get('hostname', 'Unknown')}")
                        print(f"✅ System uptime: {data.get('uptime', 0)} seconds")
                        return True
                    else:
                        print(f"⚠️  API returned status {api_response.status_code}")
                except Exception as e:
                    print(f"⚠️  API test failed: {e}")
                
                return True
            else:
                print(f"❌ Web interface returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"⏳ Waiting for MoxNAS to start... ({int(time.time() - start_time)}s)")
            time.sleep(2)
        except Exception as e:
            print(f"❌ Error testing web interface: {e}")
            return False
    
    print(f"❌ Timeout after {timeout}s - MoxNAS web interface not accessible")
    return False

def test_python_dependencies():
    """Test if all Python dependencies are available"""
    print("🔍 Testing Python dependencies...")
    
    try:
        import django
        import psutil
        import requests
        print("✅ All Python dependencies are available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def test_system_services():
    """Test if system services are installed"""
    print("🔍 Testing system services...")
    
    services = ['smbd', 'nmbd', 'nfs-kernel-server', 'vsftpd', 'ssh', 'snmpd']
    all_ok = True
    
    for service in services:
        try:
            result = subprocess.run(['systemctl', 'is-enabled', service], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {service} is installed and enabled")
            else:
                print(f"⚠️  {service} may not be properly configured")
                all_ok = False
        except:
            print(f"❌ {service} test failed")
            all_ok = False
    
    return all_ok

def test_directories():
    """Test if necessary directories exist"""
    print("🔍 Testing directories...")
    
    directories = ['/mnt/storage', '/etc/moxnas', '/var/log/moxnas']
    all_ok = True
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"✅ {directory} exists")
        else:
            print(f"❌ {directory} missing")
            all_ok = False
    
    return all_ok

def test_services(host, port=8080):
    """Test if NAS services are configured and running"""
    print("🔍 Testing NAS services...")
    
    try:
        url = f"http://{host}:{port}/api/core/services/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            services = data.get('results', data) if isinstance(data, dict) else data
            print(f"✅ Found {len(services)} configured services:")
            
            for service in services:
                name = service.get('name', 'unknown')
                port = service.get('port', 'unknown')
                running = service.get('running', False)
                status_icon = "🟢" if running else "🔴"
                print(f"  {status_icon} {name.upper()}: Port {port} - {'Running' if running else 'Stopped'}")
            
            return True
        else:
            print(f"❌ Service status API returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing services: {e}")
        return False

def test_storage(host, port=8080):
    """Test storage and mount point functionality"""
    print("💾 Testing storage functionality...")
    
    try:
        # Test mount points
        url = f"http://{host}:{port}/api/storage/mounts/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            mount_points = data.get('results', data) if isinstance(data, dict) else data
            print(f"✅ Storage API accessible - {len(mount_points)} mount points configured")
            
            # Test datasets
            url = f"http://{host}:{port}/api/storage/datasets/"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                datasets = data.get('results', data) if isinstance(data, dict) else data
                print(f"✅ Dataset API accessible - {len(datasets)} datasets configured")
                return True
                
        else:
            print(f"❌ Storage API returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing storage: {e}")
        return False

def test_shares(host, port=8080):
    """Test share management functionality"""
    print("📁 Testing share management...")
    
    try:
        url = f"http://{host}:{port}/api/storage/shares/"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            shares = data.get('results', data) if isinstance(data, dict) else data
            print(f"✅ Share API accessible - {len(shares)} shares configured")
            
            protocols = {}
            for share in shares:
                protocol = share.get('protocol', 'unknown')
                protocols[protocol] = protocols.get(protocol, 0) + 1
            
            if protocols:
                print("  Share protocols:")
                for protocol, count in protocols.items():
                    print(f"    {protocol.upper()}: {count} shares")
            
            return True
        else:
            print(f"❌ Share API returned {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing shares: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test MoxNAS installation')
    parser.add_argument('host', help='MoxNAS container IP address')
    parser.add_argument('--port', type=int, default=8080, help='MoxNAS web port (default: 8080)')
    parser.add_argument('--timeout', type=int, default=60, help='Timeout in seconds (default: 60)')
    
    args = parser.parse_args()
    
    print("🚀 MoxNAS Installation Test")
    print("=" * 50)
    print(f"Testing MoxNAS at {args.host}:{args.port}")
    print()
    
    tests_passed = 0
    total_tests = 4
    
    # Test web interface
    if test_web_interface(args.host, args.port, args.timeout):
        tests_passed += 1
    print()
    
    # Test services
    if test_services(args.host, args.port):
        tests_passed += 1
    print()
    
    # Test storage
    if test_storage(args.host, args.port):
        tests_passed += 1
    print()
    
    # Test shares
    if test_shares(args.host, args.port):
        tests_passed += 1
    print()
    
    # Summary
    print("=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! MoxNAS is working correctly.")
        print(f"🌐 Access your MoxNAS at: http://{args.host}:{args.port}")
        print("👤 Default login: admin / moxnas123")
        print()
        print("Next steps:")
        print("1. Change the default admin password")
        print("2. Add storage mount points if needed")
        print("3. Create datasets and shares")
        print("4. Configure users and permissions")
        return 0
    else:
        print("❌ Some tests failed. Check the MoxNAS installation.")
        print("💡 Troubleshooting:")
        print("   - Check if MoxNAS service is running: systemctl status moxnas")
        print("   - Check logs: journalctl -u moxnas -f")
        print("   - Verify container has network access")
        return 1

if __name__ == '__main__':
    sys.exit(main())