#!/usr/bin/env python3
"""
Quick test to verify MoxNAS is working
"""

import subprocess
import time

def test_server_response():
    """Test if server responds"""
    try:
        result = subprocess.run([
            'curl', '-s', '-w', '%{http_code}', '-o', '/dev/null',
            'http://localhost:5000/auth/login'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0 and result.stdout.strip() == '200':
            print("✅ Server responds correctly")
            return True
        else:
            print(f"❌ Server response: {result.stdout.strip()}")
            return False
    except Exception as e:
        print(f"❌ Server test failed: {e}")
        return False

def test_static_files():
    """Test static files"""
    try:
        result = subprocess.run([
            'curl', '-s', '-w', '%{http_code}', '-o', '/dev/null',
            'http://localhost:5000/static/css/style.css'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0 and result.stdout.strip() == '200':
            print("✅ Static files accessible")
            return True
        else:
            print(f"❌ Static files: {result.stdout.strip()}")
            return False
    except Exception as e:
        print(f"❌ Static files test failed: {e}")
        return False

def main():
    print("🧪 Quick MoxNAS Functionality Test")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 2
    
    if test_server_response():
        tests_passed += 1
    
    if test_static_files():
        tests_passed += 1
    
    print("\n" + "=" * 40)
    print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 MoxNAS is working correctly!")
    elif tests_passed > 0:
        print("⚠️  Basic functionality works")
    else:
        print("❌ Server not responding")

if __name__ == "__main__":
    main()
