#!/usr/bin/env python3
"""
Test Django API for container creation
"""

import requests
import json

def test_django_container_api():
    """Test Django container creation API endpoint"""
    
    # Django API endpoint
    url = "http://localhost:8001/api/proxmox/api/containers/create_container/"
    
    # Container creation data
    container_data = {
        "node": "pve",
        "vmid": 940,
        "hostname": "django-test-940",
        "memory": 2048,
        "cores": 2,
        "disk_size": "16",  # Size without G suffix
        "storage_pool": "local-lvm",  # Explicitly specify correct storage
        "template_storage": "local",
        "network_bridge": "vmbr0",
        "ip_type": "dhcp"
    }
    
    print("=== Testing Django Container Creation API ===")
    print(f"URL: {url}")
    print("Request data:")
    print(json.dumps(container_data, indent=2))
    
    try:
        # Send POST request
        response = requests.post(url, json=container_data, timeout=30)
        
        print(f"\nResponse Status: {response.status_code}")
        print("Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        
        print("\nResponse Body:")
        try:
            response_json = response.json()
            print(json.dumps(response_json, indent=2))
        except:
            print(response.text)
        
        if response.status_code == 200:
            print("\n✅ Container creation API call successful!")
            return True
        else:
            print(f"\n❌ API call failed with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is Django server running on port 8001?")
        print("💡 Run: python manage.py runserver 8001")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_simple_django_connection():
    """Test basic Django server connection"""
    try:
        response = requests.get("http://localhost:8001/", timeout=5)
        print(f"Django server responding: {response.status_code}")
        return True
    except:
        print("Django server not responding")
        return False

if __name__ == "__main__":
    print("1. Testing Django server connection...")
    if test_simple_django_connection():
        print("\n2. Testing container creation API...")
        test_django_container_api()
    else:
        print("\n❌ Django server not available")
        print("💡 Start the server with: python manage.py runserver 8001")
