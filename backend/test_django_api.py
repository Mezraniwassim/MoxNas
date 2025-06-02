#!/usr/bin/env python3
"""
Test actual container creation through our Django API
"""

import requests
import json
import sys

def test_container_creation_api():
    """Test our Django API for container creation"""
    
    print("=== Testing Django Container Creation API ===")
    
    # API endpoint
    base_url = "http://localhost:8001"
    
    # Test basic connectivity
    try:
        response = requests.get(base_url, timeout=5)
        print(f"✅ Server accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Server not accessible: {e}")
        return False
    
    # Check available endpoints
    try:
        response = requests.get(f"{base_url}/api/proxmox/", timeout=5)
        print(f"Proxmox API endpoint: {response.status_code}")
    except Exception as e:
        print(f"Proxmox API endpoint error: {e}")
    
    # Test container creation directly
    container_data = {
        "node": "pve",
        "vmid": 997,
        "hostname": "test-api-997",
        "memory": 512,
        "cores": 1,
        "disk_size": "8",
        "storage_pool": "local-lvm",
        "bridge": "vmbr0",
        "ip_type": "dhcp"
    }
    
    print(f"\nTesting container creation with data:")
    print(json.dumps(container_data, indent=2))
    
    try:
        response = requests.post(
            f"{base_url}/api/proxmox/api/containers/create_container/",
            json=container_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response Data:")
            print(json.dumps(response_data, indent=2))
        except:
            print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            print("✅ Container creation API call successful!")
            return True
        else:
            print(f"❌ Container creation failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error calling container creation API: {e}")
        return False

if __name__ == "__main__":
    success = test_container_creation_api()
    sys.exit(0 if success else 1)
