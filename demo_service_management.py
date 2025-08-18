#!/usr/bin/env python3
"""
Demo script showing MoxNAS service management capabilities
"""

import os
import sys
import django

# Setup Django
sys.path.append('/home/wassim/Documents/MoxNas/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
django.setup()

from apps.services.managers import samba_manager, nfs_manager, ftp_manager
from apps.services.templates import template_engine

def demo_service_status():
    """Demonstrate service status checking"""
    print("=== Service Status Demo ===")
    
    services = [
        ('Samba', samba_manager),
        ('NFS', nfs_manager),
        ('FTP', ftp_manager)
    ]
    
    for name, manager in services:
        status = manager.status()
        print(f"{name:10} | Active: {status['active']:5} | Enabled: {status['enabled']:5} | Status: {status['status']}")

def demo_template_rendering():
    """Demonstrate template rendering"""
    print("\n=== Template Rendering Demo ===")
    
    # Demo Samba configuration
    context = {
        'generation_time': '2025-01-17 12:00:00',
        'workgroup': 'DEMO',
        'server_string': 'MoxNAS Demo Server',
        'shares': [
            {
                'name': 'demo_share',
                'path': '/tmp/demo',
                'comment': 'Demo Share',
                'read_only': False,
                'browseable': True,
                'guest_ok': False,
                'valid_users': ['user1', 'user2'],
                'create_mask': '0664',
                'directory_mask': '0775',
                'hide_dot_files': True,
                'inherit_permissions': False,
                'recycle_bin': True,
                'audit': False
            }
        ]
    }
    
    try:
        config = template_engine.render_template('samba/smb.conf.j2', context)
        print("✓ Generated Samba configuration:")
        print("=" * 50)
        print(config[:300] + "..." if len(config) > 300 else config)
        print("=" * 50)
    except Exception as e:
        print(f"✗ Template rendering failed: {e}")

def demo_configuration_management():
    """Demonstrate configuration management"""
    print("\n=== Configuration Management Demo ===")
    
    print("Available management commands:")
    print("• python manage.py configure_services --help")
    print("• python manage.py configure_services --service=samba --test-only")
    print("• python manage.py configure_services --service=all --restart")
    
    print("\nAvailable API endpoints:")
    print("• POST /api/services/control/     - Control services (start/stop/restart)")
    print("• GET  /api/services/status/      - Get service status")
    print("• POST /api/services/regenerate-config/ - Regenerate configurations")
    print("• POST /api/services/test-config/ - Test configuration syntax")

def main():
    """Run all demos"""
    print("🚀 MoxNAS Service Management Demo\n")
    
    try:
        demo_service_status()
        demo_template_rendering()
        demo_configuration_management()
        
        print("\n🎉 Demo completed successfully!")
        print("\nNext steps:")
        print("1. Run migrations: python manage.py migrate")
        print("2. Test services: python test_service_configuration.py")
        print("3. Configure services: python manage.py configure_services --test-only")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())