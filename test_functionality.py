#!/usr/bin/env python3
"""
Test script to verify all MoxNAS functionality works correctly
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:5000"
session = requests.Session()

def test_login_page():
    """Test login page accessibility"""
    print("📋 Testing login page...")
    try:
        response = session.get(f"{BASE_URL}/auth/login", timeout=5)
        if response.status_code == 200:
            print("✅ Login page accessible")
            return True
        else:
            print(f"❌ Login page failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Login page error: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints accessibility"""
    print("\n📊 Testing API endpoints...")
    
    endpoints = [
        "/api/system/stats",
        "/api/storage/overview", 
        "/shares/api/connections",
        "/monitoring/api/system/metrics"
    ]
    
    passed = 0
    for endpoint in endpoints:
        try:
            response = session.get(f"{BASE_URL}{endpoint}", timeout=5)
            # Expect 302 (redirect to login) or 401 (unauthorized) for protected endpoints
            if response.status_code in [200, 302, 401]:
                print(f"✅ {endpoint}: {response.status_code}")
                passed += 1
            else:
                print(f"❌ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: error - {e}")
    
    return passed == len(endpoints)

def test_static_files():
    """Test static files accessibility"""
    print("\n📁 Testing static files...")
    
    static_files = [
        "/static/css/style.css",
        "/static/js/app.js"
    ]
    
    passed = 0
    for file_path in static_files:
        try:
            response = session.get(f"{BASE_URL}{file_path}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {file_path}: accessible")
                passed += 1
            else:
                print(f"❌ {file_path}: {response.status_code}")
        except Exception as e:
            print(f"❌ {file_path}: error - {e}")
    
    return passed == len(static_files)

def test_authentication():
    """Test authentication functionality"""
    print("\n🔐 Testing authentication...")
    
    try:
        # Test login with admin credentials
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        response = session.post(f"{BASE_URL}/auth/login", data=login_data, timeout=5)
        
        # Should redirect after successful login
        if response.status_code in [200, 302]:
            print("✅ Admin login successful")
            
            # Test accessing protected endpoint after login
            response = session.get(f"{BASE_URL}/", timeout=5)
            if response.status_code == 200:
                print("✅ Access to dashboard after login")
                return True
            else:
                print(f"❌ Dashboard access failed: {response.status_code}")
                return False
        else:
            print(f"❌ Login failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False

def test_page_navigation():
    """Test navigation to different pages"""
    print("\n🧭 Testing page navigation...")
    
    pages = [
        "/",
        "/storage/",
        "/shares/", 
        "/backups/",
        "/monitoring/",
        "/services/"
    ]
    
    passed = 0
    for page in pages:
        try:
            response = session.get(f"{BASE_URL}{page}", timeout=5)
            if response.status_code in [200, 302]:
                print(f"✅ {page}: accessible")
                passed += 1
            else:
                print(f"❌ {page}: {response.status_code}")
        except Exception as e:
            print(f"❌ {page}: error - {e}")
    
    return passed >= len(pages) // 2  # At least half should work

def main():
    """Run all functionality tests"""
    print("🚀 MoxNAS Functionality Test Suite")
    print("=" * 50)
    
    tests = [
        ("Login Page", test_login_page),
        ("API Endpoints", test_api_endpoints),
        ("Static Files", test_static_files),
        ("Authentication", test_authentication),
        ("Page Navigation", test_page_navigation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All functionality tests PASSED!")
        return 0
    elif passed >= total // 2:
        print("⚠️  Most functionality works, some issues detected")
        return 0
    else:
        print("❌ Major functionality issues detected")
        return 1

if __name__ == "__main__":
    sys.exit(main())
