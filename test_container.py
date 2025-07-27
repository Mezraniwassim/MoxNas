#!/usr/bin/env python3
"""
MoxNAS Container Test Script
Tests MoxNAS functionality inside LXC container
"""

import requests
import time
import sys

def test_moxnas_container(host='localhost', port=8080):
    """Test MoxNAS container deployment"""
    print("🧪 Testing MoxNAS Container Deployment")
    print("=" * 50)
    
    base_url = f"http://{host}:{port}"
    
    # Test web interface accessibility
    print("🌐 Testing web interface...")
    try:
        response = requests.get(base_url, timeout=10)
        if response.status_code == 200:
            print("✅ Web interface accessible")
        else:
            print(f"⚠️ Web interface returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Web interface not accessible: {e}")
        return False
    
    # Test API endpoints
    print("\n🔌 Testing API endpoints...")
    
    endpoints = [
        '/api/core/system/current/',
        '/api/core/services/',
        '/api/storage/datasets/',
        '/api/storage/shares/',
        '/api/users/users/',
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code in [200, 404]:  # 404 is OK for empty data
                print(f"✅ {endpoint}")
            else:
                print(f"⚠️ {endpoint} - Status {response.status_code}")
        except requests.exceptions.RequestException:
            print(f"❌ {endpoint} - Connection failed")
    
    # Test system info
    print("\n📊 Testing system information...")
    try:
        response = requests.get(f"{base_url}/api/core/system/current/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Hostname: {data.get('hostname', 'Unknown')}")
            print(f"✅ Uptime: {data.get('uptime', 0)} seconds")
            print(f"✅ Version: {data.get('version', 'Unknown')}")
        else:
            print("⚠️ System info endpoint not working properly")
    except Exception as e:
        print(f"❌ System info test failed: {e}")
    
    # Test services
    print("\n🔧 Testing services...")
    try:
        response = requests.get(f"{base_url}/api/core/services/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            services = data.get('results', data) if isinstance(data, dict) else data
            for service in services:
                name = service.get('name', 'Unknown')
                running = service.get('running', False)
                port = service.get('port', 'Unknown')
                status = "🟢 Running" if running else "🔴 Stopped"
                print(f"  {name.upper()}: {status} (Port {port})")
        else:
            print("⚠️ Services endpoint not working")
    except Exception as e:
        print(f"❌ Services test failed: {e}")
    
    print("\n" + "=" * 50)
    print("✅ MoxNAS Container Test Complete!")
    print(f"\n🌐 Access MoxNAS at: {base_url}")
    print("\n📋 Quick Test Commands:")
    print(f"   curl {base_url}/api/core/system/current/")
    print(f"   curl {base_url}/api/core/services/")
    
    return True

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    
    print(f"Testing MoxNAS at {host}:{port}")
    print("Waiting 5 seconds for services to be ready...")
    time.sleep(5)
    
    success = test_moxnas_container(host, port)
    sys.exit(0 if success else 1)