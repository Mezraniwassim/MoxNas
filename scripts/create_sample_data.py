#!/usr/bin/env python
"""
Sample data creation script for MoxNAS
This script populates the database with sample data for testing

Note: For better import resolution, use the Django management command instead:
    cd backend && python manage.py create_sample_data
"""

import os
import sys
import django
from pathlib import Path

# Get the project root directory
project_root = Path(__file__).parent.parent
backend_path = project_root / 'backend'

# Add the backend directory to Python path
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')

# Check if we're in the correct directory
if not (backend_path / 'manage.py').exists():
    print(f"Error: Could not find Django project at {backend_path}")
    print("Make sure you're running this script from the correct directory.")
    sys.exit(1)

try:
    django.setup()
except Exception as e:
    print(f"Error setting up Django: {e}")
    print("Make sure Django is installed and the project is properly configured.")
    sys.exit(1)

# Import Django models after setup
try:
    from storage_services.models import StoragePool, Dataset, Share, AccessControlList
    from network_services.models import NetworkInterface, SambaSetting, NFSSetting, FTPSetting, SSHSetting
    from system_management.models import SystemInfo, SystemService, CronJob, SyncTask, UPSConfig, SNMPConfig
except ImportError as e:
    print(f"Error importing models: {e}")
    print("Make sure you're running this script from the correct directory and Django is properly installed.")
    sys.exit(1)

def create_sample_data():
    """Create sample data for all models"""
    
    print("Creating sample storage data...")
    
    # Create storage pools
    pool1, created = StoragePool.objects.get_or_create(
        name='main-pool',
        defaults={
            'mount_path': '/mnt/storage/main-pool',
            'description': 'Main storage pool for documents and media',
            'total_size': 1000000000000,  # 1TB in bytes
            'used_size': 250000000000,    # 250GB in bytes
            'is_active': True
        }
    )
    
    pool2, created = StoragePool.objects.get_or_create(
        name='backup-pool',
        defaults={
            'mount_path': '/mnt/storage/backup-pool',
            'description': 'Backup storage pool',
            'total_size': 2000000000000,  # 2TB in bytes
            'used_size': 500000000000,    # 500GB in bytes
            'is_active': True
        }
    )
    
    # Create datasets
    dataset1, created = Dataset.objects.get_or_create(
        name='documents',
        storage_pool=pool1,
        defaults={
            'path': 'documents',
            'description': 'Document storage dataset',
            'compression': 'lz4',
            'quota': 500000000000,  # 500GB in bytes
            'readonly': False
        }
    )
    
    dataset2, created = Dataset.objects.get_or_create(
        name='media',
        storage_pool=pool1,
        defaults={
            'path': 'media',
            'description': 'Media storage dataset',
            'compression': 'none',
            'quota': 1000000000000,  # 1TB in bytes
            'readonly': False
        }
    )
    
    dataset3, created = Dataset.objects.get_or_create(
        name='backups',
        storage_pool=pool2,
        defaults={
            'path': 'backups',
            'description': 'Backup storage dataset',
            'compression': 'gzip',
            'quota': 2000000000000,  # 2TB in bytes
            'readonly': False
        }
    )
    
    # Create shares
    share1, created = Share.objects.get_or_create(
        name='documents-share',
        defaults={
            'share_type': 'smb',
            'dataset': dataset1,
            'path': '/documents',
            'description': 'Documents SMB share',
            'enabled': True,
            'readonly': False,
            'guest_access': False
        }
    )
    
    share2, created = Share.objects.get_or_create(
        name='media-share',
        defaults={
            'share_type': 'nfs',
            'dataset': dataset2,
            'path': '/media',
            'description': 'Media NFS share',
            'enabled': True,
            'readonly': True,
            'guest_access': True
        }
    )
    
    share3, created = Share.objects.get_or_create(
        name='backup-share',
        defaults={
            'share_type': 'ftp',
            'dataset': dataset3,
            'path': '/backups',
            'description': 'Backup FTP share',
            'enabled': False,
            'readonly': False,
            'guest_access': False
        }
    )
    
    print("Creating sample network data...")
    
    # Create network interfaces
    eth0, created = NetworkInterface.objects.get_or_create(
        name='eth0',
        defaults={
            'ip_address': '192.168.1.100',
            'netmask': '255.255.255.0',
            'gateway': '192.168.1.1',
            'enabled': True,
            'dhcp': False
        }
    )
    
    eth1, created = NetworkInterface.objects.get_or_create(
        name='eth1',
        defaults={
            'ip_address': '10.0.0.100',
            'netmask': '255.255.255.0',
            'gateway': '10.0.0.1',
            'enabled': False,
            'dhcp': True
        }
    )
    
    # Create network service settings
    samba, created = SambaSetting.objects.get_or_create(
        workgroup='WORKGROUP',
        defaults={
            'netbios_name': 'MOXNAS',
            'description': 'MoxNAS Server',
            'enable_smb1': False,
            'enable_smb2': True,
            'enable_smb3': True
        }
    )
    
    nfs, created = NFSSetting.objects.get_or_create(
        defaults={
            'enable_v3': True,
            'enable_v4': True,
            'threads': 8,
            'udp': False
        }
    )
    
    ftp, created = FTPSetting.objects.get_or_create(
        defaults={
            'port': 21,
            'passive_ports_min': 20000,
            'passive_ports_max': 25000,
            'max_clients': 50,
            'timeout': 300,
            'anonymous_login': False
        }
    )
    
    ssh, created = SSHSetting.objects.get_or_create(
        defaults={
            'port': 22,
            'password_authentication': True,
            'key_authentication': True,
            'root_login': False,
            'sftp_enabled': True
        }
    )
    
    print("Creating sample system data...")
    
    # Create system info
    sysinfo, created = SystemInfo.objects.get_or_create(
        hostname='moxnas',
        defaults={
            'cpu_model': 'Intel Core i7-10700K',
            'cpu_cores': 8,
            'total_memory': '32GB',
            'kernel_version': '5.15.0-generic',
            'uptime': '7 days, 12:30:45'
        }
    )
    
    # Create system services
    services_data = [
        ('samba', 'Samba SMB/CIFS Server', 'running', True),
        ('nfs-server', 'NFS Server', 'running', True),
        ('vsftpd', 'FTP Server', 'stopped', False),
        ('ssh', 'SSH Server', 'running', True),
        ('snmpd', 'SNMP Daemon', 'running', True),
        ('ups', 'UPS Monitor', 'stopped', False),
    ]
    
    for name, description, status, enabled in services_data:
        service, created = SystemService.objects.get_or_create(
            name=name,
            defaults={
                'description': description,
                'status': status,
                'enabled': enabled
            }
        )
    
    # Create cron jobs
    cron1, created = CronJob.objects.get_or_create(
        name='daily-backup',
        defaults={
            'command': '/usr/local/bin/backup-script.sh',
            'schedule': '0 2 * * *',
            'description': 'Daily backup at 2 AM',
            'enabled': True
        }
    )
    
    cron2, created = CronJob.objects.get_or_create(
        name='weekly-cleanup',
        defaults={
            'command': '/usr/local/bin/cleanup-logs.sh',
            'schedule': '0 3 * * 0',
            'description': 'Weekly log cleanup',
            'enabled': True
        }
    )
    
    # Create sync tasks
    sync1, created = SyncTask.objects.get_or_create(
        name='documents-backup',
        defaults={
            'task_type': 'rsync',
            'source_path': '/mnt/storage/main-pool/documents',
            'destination_path': '/mnt/storage/backup-pool/backups/documents',
            'schedule': '0 1 * * *',
            'enabled': True,
            'delete_destination': False,
            'compress': True
        }
    )
    
    sync2, created = SyncTask.objects.get_or_create(
        name='cloud-sync',
        defaults={
            'task_type': 'cloud_sync',
            'source_path': '/mnt/storage/main-pool/media',
            'destination_path': 's3://mybucket/media',
            'schedule': '0 4 * * *',
            'enabled': False,
            'delete_destination': False,
            'compress': True
        }
    )
    
    # Create UPS config
    ups, created = UPSConfig.objects.get_or_create(
        name='main-ups',
        defaults={
            'driver': 'usbhid-ups',
            'port': 'auto',
            'description': 'Main UPS System',
            'shutdown_battery': 20,
            'shutdown_time': 300
        }
    )
    
    # Create SNMP config
    snmp, created = SNMPConfig.objects.get_or_create(
        defaults={
            'community': 'public',
            'contact': 'admin@moxnas.local',
            'location': 'Server Room',
            'enabled': True
        }
    )
    
    print("Sample data creation completed!")
    print(f"Created:")
    print(f"  - {StoragePool.objects.count()} storage pools")
    print(f"  - {Dataset.objects.count()} datasets")
    print(f"  - {Share.objects.count()} shares")
    print(f"  - {NetworkInterface.objects.count()} network interfaces")
    print(f"  - {SystemService.objects.count()} system services")
    print(f"  - {CronJob.objects.count()} cron jobs")
    print(f"  - {SyncTask.objects.count()} sync tasks")

if __name__ == '__main__':
    create_sample_data()
