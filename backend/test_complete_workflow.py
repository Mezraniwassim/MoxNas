#!/usr/bin/env python3
"""
Test complete container creation workflow with Proxmox connection
"""

import requests
import json
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='/home/wassim/Documents/MoxNas/.env')

def test_complete_container_workflow():
    """Test the complete container creation workflow"""
    
    print("=== Complete Container Creation Workflow Test ===")
    
    base_url = "http://localhost:8001"
    
    # Step 1: Initialize Proxmox connection using our manager directly
    print("1. Initializing Proxmox connection...")
    
    # We need to call the initialization directly since there's no connect endpoint
    # Let's create a simple script that does this
    init_script = f'''
import sys
import os
import django
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path='/home/wassim/Documents/MoxNas/.env')

sys.path.append('/home/wassim/Documents/MoxNas/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from proxmox_integration.manager import initialize_proxmox_connection

# Initialize connection using environment variables
success = initialize_proxmox_connection(
    host=os.getenv("PROXMOX_HOST", ""),
    user=os.getenv("PROXMOX_USER", "root@pam"), 
    password=os.getenv("PROXMOX_PASSWORD", ""),
    port=int(os.getenv("PROXMOX_PORT", "8006")),
    verify_ssl=os.getenv("PROXMOX_VERIFY_SSL", "False").lower() == "true"
)

print(f"Connection successful: {{success}}")
'''
    
    # Write the initialization script
    with open('/tmp/init_proxmox.py', 'w') as f:
        f.write(init_script)
    
    # Run the initialization
    import subprocess
    result = subprocess.run([
        'python', '/tmp/init_proxmox.py'
    ], capture_output=True, text=True, cwd='/home/wassim/Documents/MoxNas/backend')
    
    print(f"Initialization output: {result.stdout}")
    if result.stderr:
        print(f"Initialization errors: {result.stderr}")
    
    connection_success = "Connection successful: True" in result.stdout
    
    if not connection_success:
        print("❌ Failed to initialize Proxmox connection")
        return False
    
    print("✅ Proxmox connection initialized")
    
    # Step 2: Test container creation
    print("\n2. Testing container creation...")
    
    container_data = {
        "node": "pve",
        "vmid": 996,
        "hostname": "test-workflow-996",
        "memory": 512,
        "cores": 1,
        "disk_size": "8",
        "storage_pool": "local-lvm",
        "bridge": "vmbr0",
        "ip_type": "dhcp"
    }
    
    print(f"Container data:")
    print(json.dumps(container_data, indent=2))
    
    try:
        response = requests.post(
            f"{base_url}/api/proxmox/api/containers/create_container/",
            json=container_data,
            headers={"Content-Type": "application/json"},
            timeout=120  # Longer timeout for actual container creation
        )
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"Response Data:")
            print(json.dumps(response_data, indent=2))
            
            if response_data.get('success'):
                if 'Demo Mode' in response_data.get('message', ''):
                    print("⚠️  Still in demo mode - connection may not be established")
                    return False
                else:
                    print("✅ Container created successfully on Proxmox!")
                    return True
            else:
                print(f"❌ Container creation failed: {response_data.get('error')}")
                return False
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during container creation: {e}")
        return False

if __name__ == "__main__":
    success = test_complete_container_workflow()
    sys.exit(0 if success else 1)
