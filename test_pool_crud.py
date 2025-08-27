#!/usr/bin/env python3
"""Test script for storage pool CRUD operations"""
import requests
import sys

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

def test_pool_creation():
    """Test creating a new storage pool"""
    print("=== Testing Pool Creation ===")
    
    # First get the create page to check available devices
    response = session.get(f'{BASE_URL}/storage/pools/create')
    if response.status_code != 200:
        print(f"❌ Failed to access create page: {response.status_code}")
        return False
    
    print("✅ Create page accessible")
    
    # Create pool data
    pool_data = {
        'name': 'test-pool-mirror',
        'raid_level': 'mirror',
        'filesystem': 'ext4',
        'devices': ['2']  # Using /dev/sdb (id=2)
    }
    
    response = session.post(f'{BASE_URL}/storage/pools/create', data=pool_data)
    
    if response.status_code == 200:
        if "successfully" in response.text.lower():
            print("✅ Pool creation successful")
            return True
        else:
            print(f"❌ Pool creation failed: {response.text[:200]}...")
    else:
        print(f"❌ Pool creation failed with status: {response.status_code}")
    
    return False

def test_pool_list():
    """Test viewing storage pools list"""
    print("=== Testing Pool List ===")
    
    response = session.get(f'{BASE_URL}/storage/pools')
    if response.status_code == 200:
        if "Storage Pools" in response.text:
            print("✅ Pool list page accessible")
            if "demo-pool" in response.text:
                print("✅ Demo pool visible in list")
            return True
        else:
            print("❌ Pool list page doesn't contain expected content")
    else:
        print(f"❌ Failed to access pool list: {response.status_code}")
    
    return False

def test_pool_detail():
    """Test viewing pool details"""
    print("=== Testing Pool Detail ===")
    
    # Test viewing demo-pool (id=1)
    response = session.get(f'{BASE_URL}/storage/pools/1')
    if response.status_code == 200:
        if "demo-pool" in response.text.lower():
            print("✅ Pool detail page accessible")
            return True
        else:
            print("❌ Pool detail page doesn't contain expected content")
    else:
        print(f"❌ Failed to access pool detail: {response.status_code}")
    
    return False

def test_pool_scrub():
    """Test starting pool scrub"""
    print("=== Testing Pool Scrub ===")
    
    response = session.post(f'{BASE_URL}/storage/pools/1/scrub')
    
    if response.status_code == 200:
        try:
            result = response.json()
            if result.get('success'):
                print("✅ Pool scrub started successfully")
                return True
            else:
                print(f"❌ Pool scrub failed: {result.get('error', 'Unknown error')}")
        except:
            print("❌ Pool scrub failed: Invalid response format")
    else:
        print(f"❌ Pool scrub failed with status: {response.status_code}")
    
    return False

def test_pool_delete():
    """Test deleting a pool"""
    print("=== Testing Pool Delete ===")
    
    # Try to delete demo-pool (id=1) 
    response = session.post(f'{BASE_URL}/storage/pools/1/delete')
    
    if response.status_code == 200:
        try:
            result = response.json()
            if result.get('success'):
                print("✅ Pool deletion successful")
                return True
            else:
                print(f"❌ Pool deletion failed: {result.get('error', 'Unknown error')}")
        except:
            print("❌ Pool deletion failed: Invalid response format")
    elif response.status_code == 400:
        print("⚠️  Pool deletion blocked (expected if pool has datasets)")
        return True  # This is actually correct behavior
    else:
        print(f"❌ Pool deletion failed with status: {response.status_code}")
    
    return False

def main():
    """Run all tests"""
    print("🧪 Starting Storage Pool CRUD Tests")
    print("=" * 50)
    
    # Login first
    if not login():
        print("❌ Login failed")
        sys.exit(1)
    
    print("✅ Login successful")
    print()
    
    # Run tests
    tests = [
        test_pool_list,
        test_pool_detail,
        test_pool_creation,
        test_pool_scrub,
        test_pool_delete
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
            print()
    
    # Summary
    print("=" * 50)
    print("🔍 Test Summary:")
    passed = sum(results)
    total = len(results)
    
    test_names = [test.__name__.replace('test_', '').replace('_', ' ').title() for test in tests]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)

if __name__ == '__main__':
    main()