#!/usr/bin/env python3
"""
Test MoxNAS API endpoints for Proxmox integration
"""

import os
import sys
import django
import json
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

def test_moxnas_api():
    """Test MoxNAS API endpoints"""
    print("🌐 Testing MoxNAS API Endpoints...")
    
    # Create test client
    client = Client()
    
    # Test 1: Frontend config endpoint
    print("\n1️⃣ Testing frontend config endpoint...")
    try:
        response = client.get('/proxmox_integration/config/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            config = response.json()
            print(f"   ✅ Frontend config loaded")
            print(f"   📝 Host: {config.get('host', 'not set')}")
            print(f"   📝 Port: {config.get('port', 'not set')}")
        else:
            print(f"   ❌ Frontend config failed: {response.content.decode()}")
    except Exception as e:
        print(f"   ❌ Frontend config error: {e}")
    
    # Test 2: Proxmox connection endpoint
    print("\n2️⃣ Testing Proxmox connection endpoint...")
    try:
        response = client.post('/proxmox_integration/connect/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Connection test completed")
            print(f"   📝 Success: {result.get('success', False)}")
            if result.get('success'):
                print(f"   📝 Message: {result.get('message', 'No message')}")
            else:
                print(f"   📝 Error: {result.get('error', 'No error details')}")
        else:
            print(f"   ❌ Connection test failed: {response.content.decode()}")
    except Exception as e:
        print(f"   ❌ Connection test error: {e}")
    
    # Test 3: List Proxmox hosts
    print("\n3️⃣ Testing Proxmox hosts API...")
    try:
        response = client.get('/proxmox_integration/api/hosts/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            hosts = response.json()
            print(f"   ✅ Hosts API working")
            print(f"   📝 Found {len(hosts.get('results', hosts))} hosts")
        else:
            print(f"   ❌ Hosts API failed: {response.content.decode()}")
    except Exception as e:
        print(f"   ❌ Hosts API error: {e}")
    
    # Test 4: List Proxmox nodes
    print("\n4️⃣ Testing Proxmox nodes API...")
    try:
        response = client.get('/proxmox_integration/api/nodes/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            nodes = response.json()
            print(f"   ✅ Nodes API working")
            print(f"   📝 Found {len(nodes.get('results', nodes))} nodes")
        else:
            print(f"   ❌ Nodes API failed: {response.content.decode()}")
    except Exception as e:
        print(f"   ❌ Nodes API error: {e}")
    
    # Test 5: List Proxmox containers
    print("\n5️⃣ Testing Proxmox containers API...")
    try:
        response = client.get('/proxmox_integration/api/containers/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            containers = response.json()
            print(f"   ✅ Containers API working")
            print(f"   📝 Found {len(containers.get('results', containers))} containers")
        else:
            print(f"   ❌ Containers API failed: {response.content.decode()}")
    except Exception as e:
        print(f"   ❌ Containers API error: {e}")
    
    # Test 6: Real-time data endpoint
    print("\n6️⃣ Testing real-time data endpoint...")
    try:
        response = client.get('/proxmox_integration/realtime/data/')
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Real-time data working")
            print(f"   📝 Data keys: {list(data.keys())}")
        else:
            print(f"   ❌ Real-time data failed: {response.content.decode()}")
    except Exception as e:
        print(f"   ❌ Real-time data error: {e}")

def test_create_container_via_api():
    """Test container creation through MoxNAS API"""
    print("\n\n🚀 Testing Container Creation via MoxNAS API...")
    
    client = Client()
    
    # Container creation data
    container_data = {
        'vmid': 999,
        'hostname': 'test-moxnas-api',
        'template': 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst',
        'memory': 1024,
        'cores': 1,
        'disk': 'local-lvm:10',
        'password': 'testpass123',
        'net0': 'name=eth0,bridge=vmbr0,ip=dhcp',
        'node': 'pve'
    }
    
    try:
        response = client.post(
            '/proxmox_integration/api/containers/',
            data=json.dumps(container_data),
            content_type='application/json'
        )
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 201]:
            result = response.json()
            print(f"   ✅ Container creation initiated")
            print(f"   📝 VMID: {result.get('vmid', 'unknown')}")
            print(f"   📝 Status: {result.get('status', 'unknown')}")
        else:
            print(f"   ❌ Container creation failed: {response.content.decode()}")
    except Exception as e:
        print(f"   ❌ Container creation error: {e}")

def main():
    print("🎯 MoxNAS API Integration Test")
    print("=" * 50)
    
    test_moxnas_api()
    test_create_container_via_api()
    
    print("\n" + "=" * 50)
    print("✨ MoxNAS API test completed!")

if __name__ == "__main__":
    main()