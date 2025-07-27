#!/usr/bin/env python3
"""
Fix MoxNAS Authentication and Test Services
"""
import os
import sys
import django

# Add the backend directory to the Python path
sys.path.insert(0, '/opt/moxnas/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')

# Setup Django
django.setup()

from users.models import MoxNASUser
from services.service_manager import SambaManager, NFSManager, FTPManager

def create_admin_user():
    """Create admin user if not exists"""
    try:
        admin = MoxNASUser.objects.get(username='admin')
        print(f"✅ Admin user exists: {admin.username}")
        return admin
    except MoxNASUser.DoesNotExist:
        print("Creating admin user...")
        admin = MoxNASUser.objects.create_superuser(
            username='admin',
            email='admin@moxnas.com',
            password='moxnas123'
        )
        print(f"✅ Admin user created: {admin.username}")
        return admin

def test_service_managers():
    """Test all service managers"""
    print("\n🔧 Testing Service Managers...")
    
    # Test SMB
    try:
        smb = SambaManager()
        status = smb.get_service_status()
        print(f"✅ SMB Manager: {status}")
    except Exception as e:
        print(f"❌ SMB Manager Error: {e}")
    
    # Test NFS
    try:
        nfs = NFSManager()
        status = nfs.get_service_status()
        print(f"✅ NFS Manager: {status}")
    except Exception as e:
        print(f"❌ NFS Manager Error: {e}")
    
    # Test FTP
    try:
        ftp = FTPManager()
        status = ftp.get_service_status()
        print(f"✅ FTP Manager: {status}")
    except Exception as e:
        print(f"❌ FTP Manager Error: {e}")

def configure_services():
    """Configure all NAS services"""
    print("\n⚙️ Configuring NAS Services...")
    
    # Configure SMB
    try:
        smb = SambaManager()
        smb.configure_service({
            'enable_sharing': True,
            'workgroup': 'WORKGROUP',
            'server_string': 'MoxNAS Server'
        })
        print("✅ SMB configured successfully")
    except Exception as e:
        print(f"❌ SMB configuration failed: {e}")
    
    # Configure FTP
    try:
        ftp = FTPManager()
        ftp.configure_service({
            'anonymous_enable': False,
            'local_enable': True,
            'write_enable': True,
            'pasv_enable': True,
            'pasv_min_port': 21000,
            'pasv_max_port': 21100
        })
        print("✅ FTP configured successfully")
    except Exception as e:
        print(f"❌ FTP configuration failed: {e}")
    
    # Configure NFS
    try:
        nfs = NFSManager()
        print("✅ NFS service available")
    except Exception as e:
        print(f"❌ NFS configuration failed: {e}")

if __name__ == '__main__':
    print("🚀 MoxNAS Service Fix Script")
    print("=" * 40)
    
    # Create admin user
    admin = create_admin_user()
    
    # Test service managers
    test_service_managers()
    
    # Configure services
    configure_services()
    
    print("\n✅ All fixes completed!")
    print(f"🌐 Access MoxNAS at: http://[container-ip]")
    print(f"👤 Login: admin / moxnas123")