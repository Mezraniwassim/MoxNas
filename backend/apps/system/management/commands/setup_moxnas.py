from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.storage.services import StorageService
from apps.system.models import SystemSettings
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Initial MoxNAS setup'

    def handle(self, *args, **options):
        self.stdout.write('Setting up MoxNAS...')
        
        # Create default admin user if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@moxnas.local',
                password='admin123'
            )
            self.stdout.write(self.style.SUCCESS('Created admin user (admin/admin123)'))
        
        # Create default system settings
        default_settings = [
            ('general.hostname', 'moxnas', 'System hostname'),
            ('general.timezone', 'UTC', 'System timezone'),
            ('samba.workgroup', 'WORKGROUP', 'Samba workgroup'),
            ('nfs.domain', 'localdomain', 'NFS domain'),
            ('ftp.banner', 'Welcome to MoxNAS FTP Server', 'FTP welcome banner'),
        ]
        
        for key, value, description in default_settings:
            SystemSettings.objects.get_or_create(
                key=key,
                defaults={'value': value, 'description': description}
            )
        
        # Scan for disks
        try:
            storage_service = StorageService()
            disks = storage_service.scan_disks()
            self.stdout.write(self.style.SUCCESS(f'Scanned {len(disks)} disks'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to scan disks: {e}'))
        
        # Create required directories
        directories = [
            '/mnt/storage/shares',
            '/mnt/storage/nfs',
            '/mnt/storage/ftp',
            '/mnt/storage/backups',
            '/var/log/moxnas',
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                self.stdout.write(f'Created directory: {directory}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Could not create {directory}: {e}'))
        
        self.stdout.write(self.style.SUCCESS('MoxNAS setup completed!'))