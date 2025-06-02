"""
Django management command to populate MoxNAS database with sample data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from storage_services.models import StoragePool, Dataset, Share, AccessControlList
from network_services.models import NetworkInterface, SambaSetting, NFSSetting, FTPSetting, SSHSetting
from system_management.models import SystemInfo, SystemService, CronJob, SyncTask, UPSConfig, SNMPConfig


class Command(BaseCommand):
    help = 'Populate database with sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating new data',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Creating sample data...'))
        
        # Create storage pools
        self.create_storage_pools()
        
        # Create datasets
        self.create_datasets()
        
        # Create shares
        self.create_shares()
        
        # Create network interfaces
        self.create_network_interfaces()
        
        # Create network services
        self.create_network_services()
        
        # Create system services
        self.create_system_services()
        
        # Create system info
        self.create_system_info()
        
        # Create cron jobs
        self.create_cron_jobs()
        
        # Create sync tasks
        self.create_sync_tasks()
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))

    def clear_data(self):
        """Clear existing data"""
        models_to_clear = [
            AccessControlList, Share, Dataset, StoragePool,
            SambaSetting, NFSSetting, FTPSetting, SSHSetting, NetworkInterface,
            SyncTask, CronJob, SystemService, SystemInfo, UPSConfig, SNMPConfig
        ]
        
        for model in models_to_clear:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f'Deleted {count} {model.__name__} objects')

    def create_storage_pools(self):
        """Create sample storage pools"""
        pools = [
            {
                'name': 'tank',
                'mount_path': '/mnt/tank',
                'description': 'Primary storage pool for documents and media',
                'total_size': 2000000000000,  # 2TB
                'used_size': 500000000000,    # 500GB
                'is_active': True
            },
            {
                'name': 'backup',
                'mount_path': '/mnt/backup',
                'description': 'Backup storage pool for system backups',
                'total_size': 4000000000000,  # 4TB
                'used_size': 1000000000000,   # 1TB
                'is_active': True
            },
            {
                'name': 'cache',
                'mount_path': '/mnt/cache',
                'description': 'Cache storage pool for temporary files',
                'total_size': 500000000000,   # 500GB
                'used_size': 50000000000,     # 50GB
                'is_active': True
            }
        ]
        
        for pool_data in pools:
            pool, created = StoragePool.objects.get_or_create(
                name=pool_data['name'],
                defaults=pool_data
            )
            if created:
                self.stdout.write(f'Created storage pool: {pool.name}')

    def create_datasets(self):
        """Create sample datasets"""
        tank_pool = StoragePool.objects.get(name='tank')
        backup_pool = StoragePool.objects.get(name='backup')
        
        datasets = [
            {
                'name': 'documents',
                'storage_pool': tank_pool,
                'path': '/mnt/tank/documents',
                'description': 'Document storage',
                'compression': 'lz4',
                'quota': 200000000000,  # 200GB quota
                'readonly': False
            },
            {
                'name': 'media',
                'storage_pool': tank_pool,
                'path': '/mnt/tank/media',
                'description': 'Media files storage',
                'compression': 'none',
                'quota': 500000000000,  # 500GB quota
                'readonly': False
            },
            {
                'name': 'backups',
                'storage_pool': backup_pool,
                'path': '/mnt/backup/backups',
                'description': 'System and data backups',
                'compression': 'gzip',
                'quota': None,  # No quota limit
                'readonly': False
            }
        ]
        
        for dataset_data in datasets:
            dataset, created = Dataset.objects.get_or_create(
                name=dataset_data['name'],
                storage_pool=dataset_data['storage_pool'],
                defaults=dataset_data
            )
            if created:
                self.stdout.write(f'Created dataset: {dataset.name}')

    def create_shares(self):
        """Create sample shares"""
        documents_dataset = Dataset.objects.get(name='documents')
        media_dataset = Dataset.objects.get(name='media')
        
        shares = [
            {
                'name': 'Documents',
                'path': '/mnt/tank/documents',
                'dataset': documents_dataset,
                'share_type': 'smb',
                'enabled': True,
                'readonly': False,
                'guest_access': False,
                'description': 'Shared documents folder'
            },
            {
                'name': 'Media',
                'path': '/mnt/tank/media',
                'dataset': media_dataset,
                'share_type': 'smb',
                'enabled': True,
                'readonly': True,
                'guest_access': True,
                'description': 'Media library (read-only)'
            },
            {
                'name': 'Public',
                'path': '/mnt/tank/documents/public',
                'dataset': documents_dataset,
                'share_type': 'nfs',
                'enabled': True,
                'readonly': False,
                'guest_access': True,
                'description': 'Public file sharing via NFS'
            }
        ]
        
        for share_data in shares:
            share, created = Share.objects.get_or_create(
                name=share_data['name'],
                defaults=share_data
            )
            if created:
                self.stdout.write(f'Created share: {share.name}')

    def create_network_interfaces(self):
        """Create sample network interfaces"""
        interfaces = [
            {
                'name': 'eth0',
                'interface_type': 'ethernet',
                'ip_address': '192.168.1.100',
                'netmask': '255.255.255.0',
                'gateway': '192.168.1.1',
                'dns_servers': '["8.8.8.8", "8.8.4.4"]',
                'enabled': True,
                'dhcp_enabled': False
            },
            {
                'name': 'eth1',
                'interface_type': 'ethernet',
                'ip_address': '10.0.0.100',
                'netmask': '255.255.255.0',
                'gateway': '10.0.0.1',
                'dns_servers': '["1.1.1.1", "1.0.0.1"]',
                'enabled': False,
                'dhcp_enabled': True
            }
        ]
        
        for interface_data in interfaces:
            interface, created = NetworkInterface.objects.get_or_create(
                name=interface_data['name'],
                defaults=interface_data
            )
            if created:
                self.stdout.write(f'Created network interface: {interface.name}')

    def create_network_services(self):
        """Create sample network service configurations"""
        # SMB Settings
        smb_settings = {
            'workgroup': 'MOXNAS',
            'server_string': 'MoxNAS Server',
            'security': 'user',
            'guest_account': 'nobody',
            'enable_recycle_bin': True,
            'audit_enable': False
        }
        samba, created = SambaSetting.objects.get_or_create(defaults=smb_settings)
        if created:
            self.stdout.write('Created Samba settings')

        # NFS Settings
        nfs_settings = {
            'nfs_v3_enabled': True,
            'nfs_v4_enabled': True,
            'rpc_mountd_port': 20048,
            'rpc_statd_port': 20049,
            'rpc_lockd_port': 20050,
            'enable_udp': True,
            'servers': 4
        }
        nfs, created = NFSSetting.objects.get_or_create(defaults=nfs_settings)
        if created:
            self.stdout.write('Created NFS settings')

        # FTP Settings
        ftp_settings = {
            'enabled': False,
            'port': 21,
            'max_clients': 50,
            'max_per_ip': 5,
            'max_login_fail': 3,
            'timeout': 600,
            'anonymous_access': False,
            'local_user_access': True,
            'passive_ports_min': 20000,
            'passive_ports_max': 25000,
            'tls_enabled': False
        }
        ftp, created = FTPSetting.objects.get_or_create(defaults=ftp_settings)
        if created:
            self.stdout.write('Created FTP settings')

        # SSH Settings
        ssh_settings = {
            'enabled': True,
            'port': 22,
            'permit_root_login': False,
            'password_authentication': True,
            'pubkey_authentication': True,
            'x11_forwarding': False,
            'max_auth_tries': 3,
            'client_alive_interval': 0
        }
        ssh, created = SSHSetting.objects.get_or_create(defaults=ssh_settings)
        if created:
            self.stdout.write('Created SSH settings')

    def create_system_services(self):
        """Create sample system services"""
        services = [
            {
                'name': 'smbd',
                'description': 'Samba SMB/CIFS server',
                'status': 'running',
                'enabled': True,
                'pid': 1234
            },
            {
                'name': 'nmbd',
                'description': 'Samba NetBIOS nameserver',
                'status': 'running',
                'enabled': True,
                'pid': 1235
            },
            {
                'name': 'nfs-server',
                'description': 'NFS server',
                'status': 'stopped',
                'enabled': False,
                'pid': None
            },
            {
                'name': 'vsftpd',
                'description': 'FTP server',
                'status': 'stopped',
                'enabled': False,
                'pid': None
            },
            {
                'name': 'ssh',
                'description': 'SSH server',
                'status': 'running',
                'enabled': True,
                'pid': 1001
            },
            {
                'name': 'snmpd',
                'description': 'SNMP daemon',
                'status': 'stopped',
                'enabled': False,
                'pid': None
            }
        ]
        
        for service_data in services:
            service, created = SystemService.objects.get_or_create(
                name=service_data['name'],
                defaults=service_data
            )
            if created:
                self.stdout.write(f'Created system service: {service.name}')

    def create_system_info(self):
        """Create system information"""
        system_info = {
            'hostname': 'moxnas-01',
            'kernel_version': '5.15.0-72-generic',
            'uptime': '7 days, 14:32:18',
            'load_average': '0.15, 0.23, 0.18',
            'cpu_usage': 15.2,
            'memory_total': 8589934592,  # 8GB
            'memory_used': 2147483648,   # 2GB
            'memory_usage': 25.0,
            'disk_usage': 62.5,
            'network_rx_bytes': 1048576000,  # 1GB
            'network_tx_bytes': 524288000,   # 500MB
            'temperature': 45.5
        }
        
        info, created = SystemInfo.objects.get_or_create(defaults=system_info)
        if created:
            self.stdout.write('Created system info')

    def create_cron_jobs(self):
        """Create sample cron jobs"""
        jobs = [
            {
                'name': 'Daily Backup',
                'command': '/usr/local/bin/backup-script.sh',
                'schedule': '0 2 * * *',
                'enabled': True,
                'description': 'Daily backup at 2 AM'
            },
            {
                'name': 'Weekly Cleanup',
                'command': '/usr/local/bin/cleanup.sh',
                'schedule': '0 3 * * 0',
                'enabled': True,
                'description': 'Weekly cleanup on Sunday at 3 AM'
            },
            {
                'name': 'System Update Check',
                'command': 'apt update && apt list --upgradable',
                'schedule': '0 6 * * 1',
                'enabled': False,
                'description': 'Check for system updates on Monday at 6 AM'
            }
        ]
        
        for job_data in jobs:
            job, created = CronJob.objects.get_or_create(
                name=job_data['name'],
                defaults=job_data
            )
            if created:
                self.stdout.write(f'Created cron job: {job.name}')

    def create_sync_tasks(self):
        """Create sample sync tasks"""
        tasks = [
            {
                'name': 'Documents Sync',
                'task_type': 'rsync',
                'source_path': '/mnt/tank/documents',
                'destination_path': '/mnt/backup/documents-sync',
                'schedule': '0 1 * * *',
                'enabled': True,
                'options': '-avz --delete',
                'last_run': timezone.now(),
                'description': 'Sync documents to backup storage'
            },
            {
                'name': 'Cloud Backup',
                'task_type': 'cloud_sync',
                'source_path': '/mnt/tank/important',
                'destination_path': 's3://my-bucket/important',
                'schedule': '0 4 * * 0',
                'enabled': False,
                'options': '--exclude="*.tmp"',
                'description': 'Weekly cloud backup of important files'
            }
        ]
        
        for task_data in tasks:
            task, created = SyncTask.objects.get_or_create(
                name=task_data['name'],
                defaults=task_data
            )
            if created:
                self.stdout.write(f'Created sync task: {task.name}')
