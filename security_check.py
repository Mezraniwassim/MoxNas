#!/usr/bin/env python3
"""
Security Validation Script for MoxNAS
Validates security configuration and identifies potential vulnerabilities
"""
import os
import sys
import secrets
import hashlib
from pathlib import Path

def generate_secure_secret_key():
    """Generate a cryptographically secure secret key"""
    return secrets.token_hex(32)

def validate_secret_key(secret_key):
    """Validate secret key strength"""
    if not secret_key:
        return False, "Secret key is empty"
    
    if len(secret_key) < 32:
        return False, f"Secret key too short: {len(secret_key)} characters (minimum 32)"
    
    if secret_key in ['dev-secret-key', 'test-secret-key', 'moxnas-super-secret-key-change-in-production']:
        return False, "Using default/example secret key"
    
    return True, "Secret key is secure"

def check_environment_variables():
    """Check for required environment variables"""
    required_vars = [
        'SECRET_KEY',
        'DATABASE_URL',
        'REDIS_URL'
    ]
    
    missing = []
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)
    
    return missing

def check_file_permissions():
    """Check critical file permissions"""
    critical_files = [
        '.env.local',
        'config.py',
        'instance/'
    ]
    
    issues = []
    for file_path in critical_files:
        if os.path.exists(file_path):
            stat_info = os.stat(file_path)
            mode = oct(stat_info.st_mode)[-3:]
            
            if file_path.endswith('.env.local') and mode != '600':
                issues.append(f"{file_path}: Should be 600 (currently {mode})")
            elif file_path == 'instance/' and mode[0] != '7':
                issues.append(f"{file_path}: Should be 700 (currently {mode})")
    
    return issues

def security_scan():
    """Perform comprehensive security scan"""
    print("🔒 MoxNAS Security Validation")
    print("=" * 50)
    
    # Check SECRET_KEY
    secret_key = os.environ.get('SECRET_KEY')
    is_valid, message = validate_secret_key(secret_key)
    
    if is_valid:
        print("✅ SECRET_KEY: Valid")
    else:
        print(f"❌ SECRET_KEY: {message}")
        if not secret_key:
            new_key = generate_secure_secret_key()
            print(f"💡 Generated secure key: {new_key}")
            print("   Add this to your .env.local file:")
            print(f"   SECRET_KEY={new_key}")
    
    # Check environment variables
    missing_vars = check_environment_variables()
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Create .env.local file with required variables")
    else:
        print("✅ Environment variables: All required variables present")
    
    # Check file permissions
    perm_issues = check_file_permissions()
    if perm_issues:
        print("❌ File permission issues:")
        for issue in perm_issues:
            print(f"   {issue}")
    else:
        print("✅ File permissions: Secure")
    
    # Check for development credentials
    dev_patterns = [
        'admin123',
        'password123',
        'dev-secret',
        'test-secret'
    ]
    
    dev_files_found = []
    for pattern in dev_patterns:
        try:
            result = os.system(f"grep -r '{pattern}' app/ config.py > /dev/null 2>&1")
            if result == 0:
                dev_files_found.append(pattern)
        except:
            pass
    
    if dev_files_found:
        print(f"⚠️  Development patterns found: {', '.join(dev_files_found)}")
        print("   Review and remove development credentials")
    else:
        print("✅ Development credentials: None found")
    
    print("\n🔒 Security Scan Complete")

if __name__ == '__main__':
    # Load .env.local if it exists
    env_file = Path('.env.local')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    security_scan()
