#!/usr/bin/env python3
"""
Test script to populate MoxNAS database with sample data
"""

import os
import sys
import django

# Setup Django
sys.path.append('/home/wassim/Documents/MoxNas/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from storage_services.models import StoragePool, Dataset, Share, AccessControlList
from network_services.models import NetworkInterface, SambaSetting, NFSSetting, FTPSetting, SSHSetting
from system_management.models import SystemInfo, SystemService, CronJob, SyncTask, UPSConfig, SNMPConfig

def create_storage_pools():
    """Create sample storage pools"""
    print("Creating storage pools...")
    
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
            print(f'Created storage pool: {pool.name}')
        else:
            print(f'Storage pool already exists: {pool.name}')

def create_datasets():
    """Create sample datasets"""
    print("Creating datasets...")
    
    tank_pool = StoragePool.objects.get(name='tank')
    backup_pool = StoragePool.objects.get(name='backup')
    
    datasets = [
        {
            'name': 'documents',
            'storage_pool': tank_pool,
            'path': 'documents',
            'description': 'Document storage area',
            'compression': 'lz4',
            'quota': 1000000000000,  # 1TB quota
            'readonly': False
        },
        {
            'name': 'media',
            'storage_pool': tank_pool,
            'path': 'media',
            'description': 'Media files storage',
            'compression': 'none',
            'quota': 500000000000,  # 500GB quota
            'readonly': False
        },
        {
            'name': 'backups',
            'storage_pool': backup_pool,
            'path': 'backups',
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
            print(f'Created dataset: {dataset.name}')
        else:
            print(f'Dataset already exists: {dataset.name}')

def create_shares():
    """Create sample shares"""
    print("Creating shares...")
    
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
            print(f'Created share: {share.name}')
        else:
            print(f'Share already exists: {share.name}')

if __name__ == '__main__':
    print("Starting sample data creation...")
    
    try:
        create_storage_pools()
        create_datasets()
        create_shares()
        print("Sample data creation completed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
