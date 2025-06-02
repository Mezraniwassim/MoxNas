#!/usr/bin/env python3
"""
Environment Variable Validation Script for MoxNAS

This script validates that all required environment variables are properly configured
and provides guidance for fixing any issues.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class EnvironmentValidator:
    """Validates MoxNAS environment configuration"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success = []
    
    def validate_required_vars(self):
        """Validate required environment variables"""
        required_vars = {
            'SECRET_KEY': {
                'description': 'Django secret key for cryptographic signing',
                'min_length': 32,
                'required': True
            },
            'PROXMOX_HOST': {
                'description': 'Proxmox server IP address or hostname',
                'required': True
            },
            'PROXMOX_PASSWORD': {
                'description': 'Proxmox authentication password',
                'min_length': 8,
                'required': True
            },
            'CONTAINER_ROOT_PASSWORD': {
                'description': 'Default root password for new containers',
                'min_length': 8,
                'required': True
            }
        }
        
        for var_name, config in required_vars.items():
            value = os.getenv(var_name)
            
            if not value:
                if config['required']:
                    self.errors.append(f"❌ {var_name}: Required but not set - {config['description']}")
                else:
                    self.warnings.append(f"⚠️  {var_name}: Optional but recommended - {config['description']}")
            else:
                if 'min_length' in config and len(value) < config['min_length']:
                    self.warnings.append(f"⚠️  {var_name}: Should be at least {config['min_length']} characters")
                else:
                    self.success.append(f"✅ {var_name}: Configured")
    
    def validate_optional_vars(self):
        """Validate optional environment variables"""
        optional_vars = {
            'DEBUG': {
                'description': 'Django debug mode (True/False)',
                'valid_values': ['True', 'False', 'true', 'false']
            },
            'LOG_LEVEL': {
                'description': 'Logging level',
                'valid_values': ['DEBUG', 'INFO', 'WARNING', 'ERROR']
            },
            'PROXMOX_VERIFY_SSL': {
                'description': 'Verify SSL certificates for Proxmox (True/False)',
                'valid_values': ['True', 'False', 'true', 'false']
            }
        }
        
        for var_name, config in optional_vars.items():
            value = os.getenv(var_name)
            
            if value:
                if 'valid_values' in config and value not in config['valid_values']:
                    self.warnings.append(f"⚠️  {var_name}: Invalid value '{value}'. Valid: {', '.join(config['valid_values'])}")
                else:
                    self.success.append(f"✅ {var_name}: {value}")
            else:
                self.warnings.append(f"⚠️  {var_name}: Not set, using default - {config['description']}")
    
    def validate_security_settings(self):
        """Validate security-related settings"""
        secret_key = os.getenv('SECRET_KEY')
        if secret_key:
            if 'django-insecure' in secret_key:
                self.warnings.append("⚠️  SECRET_KEY: Using default insecure key. Generate a new one!")
            elif len(secret_key) < 50:
                self.warnings.append("⚠️  SECRET_KEY: Consider using a longer secret key (50+ characters)")
        
        debug = os.getenv('DEBUG', 'True').lower()
        if debug == 'true':
            self.warnings.append("⚠️  DEBUG: Debug mode is enabled. Disable for production!")
        
        verify_ssl = os.getenv('PROXMOX_VERIFY_SSL', 'False').lower()
        if verify_ssl == 'false':
            self.warnings.append("⚠️  PROXMOX_VERIFY_SSL: SSL verification disabled. Enable for production!")
    
    def validate_file_permissions(self):
        """Validate .env file permissions"""
        env_file = Path('.env')
        if env_file.exists():
            stat = env_file.stat()
            permissions = oct(stat.st_mode)[-3:]
            
            if permissions != '600':
                self.warnings.append(f"⚠️  .env file permissions: {permissions} (should be 600 for security)")
                self.warnings.append("   Run: chmod 600 .env")
            else:
                self.success.append("✅ .env file permissions: Secure (600)")
        else:
            self.errors.append("❌ .env file not found. Copy .env.example to .env and configure it.")
    
    def run_validation(self):
        """Run all validations and return results"""
        print("🔍 MoxNAS Environment Validation")
        print("=" * 50)
        
        # Check if .env file exists
        if not Path('.env').exists():
            print("❌ .env file not found!")
            print("📋 To fix this:")
            print("   1. Copy .env.example to .env")
            print("   2. Edit .env with your configuration")
            print("   3. Run this validator again")
            return False
        
        self.validate_required_vars()
        self.validate_optional_vars()
        self.validate_security_settings()
        self.validate_file_permissions()
        
        # Display results
        if self.success:
            print("\n✅ Successful Configurations:")
            for msg in self.success:
                print(f"   {msg}")
        
        if self.warnings:
            print("\n⚠️  Warnings:")
            for msg in self.warnings:
                print(f"   {msg}")
        
        if self.errors:
            print("\n❌ Errors (must be fixed):")
            for msg in self.errors:
                print(f"   {msg}")
        
        # Summary
        total_checks = len(self.success) + len(self.warnings) + len(self.errors)
        print(f"\n📊 Summary: {len(self.success)} OK, {len(self.warnings)} warnings, {len(self.errors)} errors")
        
        if self.errors:
            print("\n📋 Next Steps:")
            print("   1. Fix all errors listed above")
            print("   2. Consider addressing warnings for better security")
            print("   3. Run this validator again to verify fixes")
            return False
        elif self.warnings:
            print("\n📋 Configuration is functional but consider addressing warnings for better security.")
            return True
        else:
            print("\n🎉 Environment configuration is excellent!")
            return True

def generate_secure_key():
    """Generate a secure Django secret key"""
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(alphabet) for _ in range(50))

def main():
    """Main validation function"""
    validator = EnvironmentValidator()
    is_valid = validator.run_validation()
    
    if not is_valid:
        print("\n🔧 Quick Fixes:")
        
        # Check if SECRET_KEY needs to be generated
        if not os.getenv('SECRET_KEY') or 'django-insecure' in os.getenv('SECRET_KEY', ''):
            print("   Generate a new SECRET_KEY:")
            print(f"   SECRET_KEY={generate_secure_key()}")
        
        print("\n📚 Documentation:")
        print("   • See SECURITY.md for detailed configuration guide")
        print("   • Example configuration available in .env.example")
    
    return is_valid

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
