#!/usr/bin/env python
"""
Create sample system services for MoxNAS
"""
import os
import sys
import django

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from django.contrib.auth.models import User
from system_management.models import SystemService, CronJob, SyncTask

def create_sample_services():
    """Create sample system services"""
    
    # Get or create a default user for cron jobs
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@moxnas.local',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        user.set_password('admin')
        user.save()
        print(f"Created default user: {user.username}")
    
    # Clear existing services
    SystemService.objects.all().delete()
    CronJob.objects.all().delete()
    SyncTask.objects.all().delete()
    
    # Core NAS services
    services_data = [
        {
            'name': 'smbd',
            'description': 'Samba SMB/CIFS Server',
            'status': 'running',
            'enabled': True,
            'pid': 1234
        },
        {
            'name': 'nmbd',
            'description': 'Samba NetBIOS Name Server',
            'status': 'running',
            'enabled': True,
            'pid': 1235
        },
        {
            'name': 'nfs-server',
            'description': 'NFS Server',
            'status': 'running',
            'enabled': True,
            'pid': 1236
        },
        {
            'name': 'vsftpd',
            'description': 'FTP Server',
            'status': 'running',
            'enabled': True,
            'pid': 1237
        },
        {
            'name': 'tgtd',
            'description': 'iSCSI Target Daemon',
            'status': 'running',
            'enabled': True,
            'pid': 1238
        },
        {
            'name': 'ssh',
            'description': 'SSH Server',
            'status': 'running',
            'enabled': True,
            'pid': 1239
        },
        {
            'name': 'snmpd',
            'description': 'SNMP Daemon',
            'status': 'stopped',
            'enabled': False,
            'pid': None
        }
    ]
    
    for service_data in services_data:
        service = SystemService.objects.create(**service_data)
        print(f"Created service: {service.name}")
    
    # Create sample cron jobs
    cron_jobs_data = [
        {
            'name': 'System Backup',
            'command': '/usr/local/bin/backup-system.sh',
            'schedule': '0 2 * * *',
            'enabled': True,
            'description': 'Daily system backup at 2 AM'
        },
        {
            'name': 'Log Rotation',
            'command': '/usr/sbin/logrotate /etc/logrotate.conf',
            'schedule': '0 1 * * *',
            'enabled': True,
            'description': 'Daily log rotation at 1 AM'
        },
        {
            'name': 'Storage Health Check',
            'command': '/usr/local/bin/check-storage.sh',
            'schedule': '*/30 * * * *',
            'enabled': True,
            'description': 'Check storage health every 30 minutes'
        }
    ]
    
    for job_data in cron_jobs_data:
        job_data['user'] = user  # Add the user to job data
        job = CronJob.objects.create(**job_data)
        print(f"Created cron job: {job.name}")
    
    # Create sample sync tasks
    sync_tasks_data = [
        {
            'name': 'Cloud Backup Sync',
            'source_path': '/mnt/tank/backup',
            'destination_path': 's3://backup-bucket/moxnas/',
            'sync_type': 'rsync',
            'schedule': '0 3 * * *',
            'enabled': True
        },
        {
            'name': 'Offsite Mirror',
            'source_path': '/mnt/tank/documents',
            'destination_path': 'rsync://backup-server/documents/',
            'sync_type': 'rsync',
            'schedule': '0 4 * * 0',
            'enabled': True
        }
    ]
    
    for task_data in sync_tasks_data:
        task = SyncTask.objects.create(**task_data)
        print(f"Created sync task: {task.name}")
    
    print("\nSample system services, cron jobs, and sync tasks created successfully!")

if __name__ == '__main__':
    create_sample_services()
