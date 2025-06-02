#!/usr/bin/env python3
import requests

print("Starting test...")
try:
    response = requests.get("http://localhost:8000/api/proxmox/api/cluster-status/")
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.text}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
print("Test complete.")
