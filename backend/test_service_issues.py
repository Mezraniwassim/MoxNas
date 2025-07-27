#!/usr/bin/env python3
"""
Test script to identify MoxNAS service configuration issues
"""
import sys
import os
import subprocess
import json
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, '/home/wassim/Documents/MoxNas/backend')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')

import django
django.setup()

from services.service_manager import ServiceManager, SambaManager, NFSManager, SystemInfoManager
from services.models import ServiceConfig

def test_service_availability():
    """Test if required services are available on the system"""
    print("=== Testing Service Availability ===")
    
    services_to_check = [
        ('smbd', 'SMB/CIFS'),
        ('nfs-kernel-server', 'NFS'),
        ('vsftpd', 'FTP'),
        ('ssh', 'SSH'),
        ('snmpd', 'SNMP'),
        ('tgt', 'iSCSI'),
    ]
    
    missing_services = []
    
    for service_name, display_name in services_to_check:
        try:
            result = subprocess.run(
                ['systemctl', 'list-unit-files', service_name],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and service_name in result.stdout:
                print(f"✓ {display_name} ({service_name}) - Available")
            else:
                print(f"✗ {display_name} ({service_name}) - NOT AVAILABLE")
                missing_services.append((service_name, display_name))
        except Exception as e:
            print(f"✗ {display_name} ({service_name}) - ERROR: {e}")
            missing_services.append((service_name, display_name))
    
    return missing_services

def test_service_manager():
    """Test ServiceManager functionality"""
    print("\n=== Testing ServiceManager ===")
    
    sm = ServiceManager()
    
    # Test service status check
    try:
        status = sm.is_service_running('smbd')
        print(f"✓ SMB service status check: {status}")
    except Exception as e:
        print(f"✗ SMB service status check failed: {e}")
    
    # Test configuration paths
    print(f"Config path: {sm.config_path}")
    print(f"Storage path: {sm.storage_path}")
    
    if not sm.config_path.exists():
        print(f"✗ Config path does not exist: {sm.config_path}")
    else:
        print(f"✓ Config path exists: {sm.config_path}")
    
    if not sm.storage_path.exists():
        print(f"✗ Storage path does not exist: {sm.storage_path}")
    else:
        print(f"✓ Storage path exists: {sm.storage_path}")

def test_samba_manager():
    """Test SambaManager functionality"""
    print("\n=== Testing SambaManager ===")
    
    sm = SambaManager()
    
    # Check if smb.conf exists
    if not sm.config_file.exists():
        print(f"✗ Samba config file does not exist: {sm.config_file}")
        return False
    else:
        print(f"✓ Samba config file exists: {sm.config_file}")
    
    # Check if it's readable
    try:
        with open(sm.config_file, 'r') as f:
            content = f.read()
        print(f"✓ Samba config file is readable ({len(content)} chars)")
    except Exception as e:
        print(f"✗ Cannot read Samba config file: {e}")
        return False
    
    return True

def test_nfs_manager():
    """Test NFSManager functionality"""
    print("\n=== Testing NFSManager ===")
    
    nm = NFSManager()
    
    # Check if exports file exists
    if not nm.exports_file.exists():
        print(f"✗ NFS exports file does not exist: {nm.exports_file}")
        return False
    else:
        print(f"✓ NFS exports file exists: {nm.exports_file}")
    
    # Check if it's readable
    try:
        with open(nm.exports_file, 'r') as f:
            content = f.read()
        print(f"✓ NFS exports file is readable ({len(content)} chars)")
    except Exception as e:
        print(f"✗ Cannot read NFS exports file: {e}")
        return False
    
    return True

def test_ftp_configuration():
    """Test FTP configuration"""
    print("\n=== Testing FTP Configuration ===")
    
    vsftpd_conf = Path('/etc/vsftpd.conf')
    
    if not vsftpd_conf.exists():
        print(f"✗ FTP config file does not exist: {vsftpd_conf}")
        return False
    else:
        print(f"✓ FTP config file exists: {vsftpd_conf}")
    
    # Check if it's readable
    try:
        with open(vsftpd_conf, 'r') as f:
            content = f.read()
        print(f"✓ FTP config file is readable ({len(content)} chars)")
    except Exception as e:
        print(f"✗ Cannot read FTP config file: {e}")
        return False
    
    return True

def test_database_models():
    """Test database models and data"""
    print("\n=== Testing Database Models ===")
    
    try:
        # Test ServiceConfig model
        services = ServiceConfig.objects.all()
        print(f"✓ ServiceConfig model works - {services.count()} services in database")
        
        for service in services:
            print(f"  - {service.name}: enabled={service.enabled}, port={service.port}")
    
    except Exception as e:
        print(f"✗ ServiceConfig model error: {e}")
        return False
    
    return True

def test_system_info():
    """Test system information gathering"""
    print("\n=== Testing System Information ===")
    
    try:
        sim = SystemInfoManager()
        stats = sim.get_system_stats()
        
        if stats:
            print(f"✓ System stats collected successfully")
            print(f"  - Hostname: {stats.get('hostname', 'N/A')}")
            print(f"  - CPU usage: {stats.get('cpu_usage', 'N/A')}%")
            print(f"  - Memory usage: {stats.get('memory_usage', {}).get('percent', 'N/A')}%")
            print(f"  - Network interfaces: {len(stats.get('network_interfaces', []))}")
        else:
            print("✗ System stats collection failed")
            return False
    
    except Exception as e:
        print(f"✗ System info error: {e}")
        return False
    
    return True

def test_permissions():
    """Test file permissions"""
    print("\n=== Testing Permissions ===")
    
    paths_to_check = [
        '/etc/samba/smb.conf',
        '/etc/exports',
        '/etc/vsftpd.conf',
        '/mnt/storage',
        '/etc/moxnas',
        '/var/log/moxnas'
    ]
    
    for path in paths_to_check:
        path_obj = Path(path)
        try:
            if path_obj.exists():
                stat = path_obj.stat()
                print(f"✓ {path} - exists, mode: {oct(stat.st_mode)[-3:]}")
            else:
                print(f"✗ {path} - does not exist")
        except Exception as e:
            print(f"✗ {path} - permission error: {e}")

def generate_recommendations(missing_services):
    """Generate recommendations for fixing issues"""
    print("\n=== RECOMMENDATIONS ===")
    
    if missing_services:
        print("Missing services detected. To fix:")
        print("1. Install missing services:")
        
        install_commands = []
        for service_name, display_name in missing_services:
            if service_name == 'smbd':
                install_commands.append('samba')
            elif service_name == 'nfs-kernel-server':
                install_commands.append('nfs-kernel-server')
            elif service_name == 'vsftpd':
                install_commands.append('vsftpd')
            elif service_name == 'ssh':
                install_commands.append('openssh-server')
            elif service_name == 'snmpd':
                install_commands.append('snmp')
            elif service_name == 'tgt':
                install_commands.append('tgt')
        
        if install_commands:
            print(f"   sudo apt update && sudo apt install -y {' '.join(set(install_commands))}")
    
    print("\n2. Create required directories:")
    print("   sudo mkdir -p /mnt/storage /etc/moxnas /var/log/moxnas")
    print("   sudo chmod 755 /mnt/storage /etc/moxnas /var/log/moxnas")
    
    print("\n3. Configure services:")
    print("   sudo systemctl enable smbd nmbd nfs-kernel-server vsftpd ssh snmpd tgt")
    
    print("\n4. Set up initial configurations:")
    print("   # For SMB - create basic smb.conf")
    print("   # For NFS - create /etc/exports") 
    print("   # For FTP - configure vsftpd.conf")

def main():
    """Main test function"""
    print("MoxNAS Service Configuration Issues Test")
    print("=" * 50)
    
    # Test service availability
    missing_services = test_service_availability()
    
    # Test service managers
    test_service_manager()
    test_samba_manager()
    test_nfs_manager()
    test_ftp_configuration()
    
    # Test database
    test_database_models()
    
    # Test system info
    test_system_info()
    
    # Test permissions
    test_permissions()
    
    # Generate recommendations
    generate_recommendations(missing_services)
    
    print("\n" + "=" * 50)
    print("Test completed. Check the recommendations above.")

if __name__ == '__main__':
    main()