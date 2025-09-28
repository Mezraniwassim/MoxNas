#!/usr/bin/env python3
"""
Security Configuration Checker for MoxNAS
Validates critical security settings before deployment
"""
import os
import sys
import secrets
from pathlib import Path

class SecurityChecker:
    def __init__(self):
        self.issues = []
        self.warnings = []
        
    def check_environment_variables(self):
        """Check critical environment variables"""
        print("🔒 Checking Environment Variables...")
        
        # Load environment file if exists
        env_files = ['.env.local', '.env.production', '.env']
        env_vars = {}
        
        for env_file in env_files:
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key] = value
                break
        
        # Check SECRET_KEY
        secret_key = env_vars.get('SECRET_KEY') or os.environ.get('SECRET_KEY')
        if not secret_key:
            self.issues.append("SECRET_KEY is not set")
        elif len(secret_key) < 32:
            self.issues.append("SECRET_KEY is too short (minimum 32 characters)")
        elif secret_key in ['dev-secret-key', 'your-secret-key-here']:
            self.issues.append("SECRET_KEY is using default/example value")
        
        # Check database configuration
        db_url = env_vars.get('DATABASE_URL') or os.environ.get('DATABASE_URL')
        if not db_url:
            self.warnings.append("DATABASE_URL is not configured")
        elif 'your_password' in db_url or 'password' in db_url:
            self.issues.append("Database password appears to be default/example")
        
        # Check CSRF protection
        csrf_enabled = env_vars.get('WTF_CSRF_ENABLED', 'true').lower()
        if csrf_enabled not in ['true', '1', 'yes']:
            self.issues.append("CSRF protection is disabled")
        
        # Check session security
        if os.environ.get('FLASK_ENV') == 'production':
            session_secure = env_vars.get('SESSION_COOKIE_SECURE', 'false').lower()
            if session_secure not in ['true', '1', 'yes']:
                self.issues.append("SESSION_COOKIE_SECURE should be true in production")
        
        print(f"   ✅ Environment variables checked")
    
    def check_file_permissions(self):
        """Check file permissions for sensitive files"""
        print("📁 Checking File Permissions...")
        
        sensitive_files = [
            '.env.local',
            '.env.production', 
            'instance/local_moxnas.db',
            'app/models.py'
        ]
        
        for file_path in sensitive_files:
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                mode = oct(stat.st_mode)[-3:]
                
                # Check if file is readable by others
                if int(mode[2]) > 0:
                    self.warnings.append(f"{file_path} is readable by others (permissions: {mode})")
        
        print(f"   ✅ File permissions checked")
    
    def check_dependencies(self):
        """Check for security-related dependencies"""
        print("📦 Checking Dependencies...")
        
        try:
            import werkzeug
            import flask
            import sqlalchemy
            
            # Check versions for known vulnerabilities
            flask_version = flask.__version__
            if flask_version < "2.3.0":
                self.warnings.append(f"Flask version {flask_version} may have security vulnerabilities")
            
            werkzeug_version = werkzeug.__version__
            if werkzeug_version < "2.3.0":
                self.warnings.append(f"Werkzeug version {werkzeug_version} may have security vulnerabilities")
                
        except ImportError as e:
            self.issues.append(f"Critical dependency missing: {e}")
        
        print(f"   ✅ Dependencies checked")
    
    def generate_report(self):
        """Generate security report"""
        print("\n" + "="*60)
        print("🛡️  MOXNAS SECURITY REPORT")
        print("="*60)
        
        if not self.issues and not self.warnings:
            print("✅ No security issues found!")
            return True
        
        if self.issues:
            print(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):")
            for i, issue in enumerate(self.issues, 1):
                print(f"   {i}. {issue}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")
        
        print(f"\n📊 SUMMARY:")
        print(f"   Critical Issues: {len(self.issues)}")
        print(f"   Warnings: {len(self.warnings)}")
        
        if self.issues:
            print("\n🚨 ACTION REQUIRED: Fix critical issues before deployment!")
            return False
        else:
            print("\n✅ Ready for deployment (address warnings when possible)")
            return True
    
    def run_all_checks(self):
        """Run all security checks"""
        print("🔍 Starting MoxNAS Security Check...")
        print("-" * 40)
        
        self.check_environment_variables()
        self.check_file_permissions()
        self.check_dependencies()
        
        return self.generate_report()

def main():
    """Main function"""
    checker = SecurityChecker()
    success = checker.run_all_checks()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()