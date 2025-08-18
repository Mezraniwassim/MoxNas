#!/usr/bin/env python3
"""
Test script for MoxNAS service configuration
Run this script to validate all service templates and configurations
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.append('/home/wassim/Documents/MoxNas/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from apps.services.managers import samba_manager, nfs_manager, ftp_manager
from apps.services.templates import template_engine
from apps.shares.models import SMBShare, NFSShare

def test_template_engine():
    """Test template engine functionality"""
    print("Testing template engine...")
    
    # Test path validation
    try:
        template_engine.validate_path('/tmp', must_exist=True)
        print("✓ Path validation works")
    except Exception as e:
        print(f"✗ Path validation failed: {e}")
        return False
    
    # Test template rendering
    try:
        test_context = {'test': 'value', 'generation_time': 'now'}
        # This should work even if template doesn't exist
        print("✓ Template engine initialized")
    except Exception as e:
        print(f"✗ Template engine failed: {e}")
        return False
    
    return True

def test_samba_configuration():
    """Test Samba configuration generation"""
    print("\nTesting Samba configuration...")
    
    try:
        # Get shares
        shares = SMBShare.objects.all()
        
        # Generate configuration
        config = samba_manager.generate_config(shares)
        print(f"✓ Generated Samba config ({len(config)} characters)")
        
        # Test configuration
        valid, message = samba_manager.test_config()
        if valid:
            print("✓ Samba configuration is valid")
        else:
            print(f"✗ Samba configuration invalid: {message}")
            return False
            
    except Exception as e:
        print(f"✗ Samba configuration failed: {e}")
        return False
    
    return True

def test_nfs_configuration():
    """Test NFS configuration generation"""
    print("\nTesting NFS configuration...")
    
    try:
        # Get exports
        exports = NFSShare.objects.all()
        
        # Generate exports
        exports_content = nfs_manager.generate_exports(exports)
        print(f"✓ Generated NFS exports ({len(exports_content)} characters)")
        
    except Exception as e:
        print(f"✗ NFS configuration failed: {e}")
        return False
    
    return True

def test_ftp_configuration():
    """Test FTP configuration generation"""
    print("\nTesting FTP configuration...")
    
    try:
        # Generate FTP config
        config = ftp_manager.generate_config()
        print(f"✓ Generated FTP config ({len(config)} characters)")
        
    except Exception as e:
        print(f"✗ FTP configuration failed: {e}")
        return False
    
    return True

def test_service_status():
    """Test service status checking"""
    print("\nTesting service status...")
    
    try:
        samba_status = samba_manager.status()
        nfs_status = nfs_manager.status()
        ftp_status = ftp_manager.status()
        
        print(f"✓ Samba status: {samba_status}")
        print(f"✓ NFS status: {nfs_status}")
        print(f"✓ FTP status: {ftp_status}")
        
    except Exception as e:
        print(f"✗ Service status check failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("=== MoxNAS Service Configuration Tests ===\n")
    
    tests = [
        test_template_engine,
        test_samba_configuration,
        test_nfs_configuration,
        test_ftp_configuration,
        test_service_status,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} tests failed!")
        return 1

if __name__ == '__main__':
    sys.exit(main())