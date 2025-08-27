#!/usr/bin/env python3
"""Test pool edit functionality"""
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

def test_edit_functionality():
    """Test pool edit functionality"""
    print("=== Testing Pool Edit Functionality ===")
    
    # Test accessing edit page
    response = session.get(f'{BASE_URL}/storage/pools/1/edit')
    if response.status_code == 200:
        print("✅ Edit page accessible")
        
        # Test updating pool name and description
        edit_data = {
            'name': 'demo-pool-updated',
            'description': 'This is an updated description for the demo pool'
        }
        
        response = session.post(f'{BASE_URL}/storage/pools/1/edit', data=edit_data)
        
        if response.status_code == 200:
            if "successfully" in response.text.lower():
                print("✅ Pool edit successful")
                
                # Verify the changes
                response = session.get(f'{BASE_URL}/storage/pools/1')
                if "demo-pool-updated" in response.text:
                    print("✅ Pool name change verified")
                    return True
                else:
                    print("❌ Pool name change not reflected")
            else:
                print(f"❌ Pool edit failed: {response.text[:200]}...")
        else:
            print(f"❌ Pool edit failed with status: {response.status_code}")
    else:
        print(f"❌ Failed to access edit page: {response.status_code}")
    
    return False

if __name__ == '__main__':
    if login():
        print("✅ Login successful\n")
        success = test_edit_functionality()
        print(f"\n{'🎉 Test passed!' if success else '❌ Test failed!'}")
    else:
        print("❌ Login failed")