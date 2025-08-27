#!/usr/bin/env python3
"""Update storage pool sizes"""
import requests

BASE_URL = 'http://localhost:5000'
session = requests.Session()

def login():
    """Login to get authenticated session"""
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    response = session.post(f'{BASE_URL}/auth/login', data=login_data)
    return response.status_code == 200 or "Dashboard" in response.text

def update_sizes():
    """Update pool sizes"""
    response = session.post(f'{BASE_URL}/storage/pools/update-sizes')
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("✅ Pool sizes updated successfully!")
            return True
        else:
            print(f"❌ Failed: {result.get('error')}")
    else:
        print(f"❌ Request failed with status: {response.status_code}")
    return False

if __name__ == '__main__':
    print("🔄 Updating storage pool sizes...")
    
    if login():
        print("✅ Login successful")
        if update_sizes():
            print("🎉 Pool size update completed!")
        else:
            print("❌ Pool size update failed!")
    else:
        print("❌ Login failed")