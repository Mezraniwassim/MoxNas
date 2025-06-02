#!/usr/bin/env python3
"""
Debug container creation to see exact configuration
"""

import json
import requests

def test_container_creation_debug():
    """Test container creation and see exact configuration"""
    
    url = "http://localhost:8001/api/proxmox/api/containers/create_container/"
    
    # Test data
    data = {
        "node": "pve",
        "vmid": 996,
        "hostname": "debug-container-996",
        "memory": 512,
        "cores": 1,
        "disk_size": "8",
        "storage_pool": "local-lvm",
        "bridge": "vmbr0",
        "ip_type": "dhcp"
    }
    
    print("=== Container Creation Debug Test ===")
    print(f"Request URL: {url}")
    print(f"Request data:")
    print(json.dumps(data, indent=2))
    
    try:
        response = requests.post(url, json=data, timeout=60)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response Body:")
            print(json.dumps(response_data, indent=2))
        except:
            print(f"Response Text: {response.text}")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    success = test_container_creation_debug()
    if success:
        print("\n✅ Debug test completed")
    else:
        print("\n❌ Debug test failed")
