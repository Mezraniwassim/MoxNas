import os
import subprocess
import logging
import time
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.services.managers import samba_manager, nfs_manager, ftp_manager
from apps.services.templates import template_engine
from apps.shares.models import SMBShare, NFSShare

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configure all MoxNAS services'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--service',
            choices=['all', 'samba', 'nfs', 'ftp', 'nginx', 'systemd'],
            default='all',
            help='Which service to configure'
        )
        parser.add_argument(
            '--restart',
            action='store_true',
            help='Restart services after configuration'
        )
        parser.add_argument(
            '--test-only',
            action='store_true',
            help='Only test configurations, do not apply'
        )
    
    def handle(self, *args, **options):
        service = options['service']
        restart_services = options['restart']
        test_only = options['test_only']
        
        self.stdout.write(
            self.style.SUCCESS(f'Configuring MoxNAS services: {service}')
        )
        
        try:
            if service in ['all', 'samba']:
                self.configure_samba(test_only, restart_services)
            
            if service in ['all', 'nfs']:
                self.configure_nfs(test_only, restart_services)
            
            if service in ['all', 'ftp']:
                self.configure_ftp(test_only, restart_services)
            
            if service in ['all', 'nginx']:
                self.configure_nginx(test_only, restart_services)
            
            if service in ['all', 'systemd']:
                self.configure_systemd(test_only, restart_services)
            
            self.stdout.write(
                self.style.SUCCESS('Service configuration completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Configuration failed: {e}')
            )
            raise
    
    def configure_samba(self, test_only, restart_service):
        """Configure Samba service"""
        self.stdout.write('Configuring Samba...')
        
        # Get active SMB shares
        shares = SMBShare.objects.filter(enabled=True)
        
        # Generate configuration
        config_content = samba_manager.generate_config(shares)
        
        if test_only:
            # Only test configuration
            valid, message = samba_manager.test_config()
            if valid:
                self.stdout.write(
                    self.style.SUCCESS('✓ Samba configuration is valid')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Samba configuration is invalid: {message}')
                )
            return
        
        # Test and reload
        valid, message = samba_manager.test_config()
        if not valid:
            raise Exception(f'Invalid Samba configuration: {message}')
        
        if restart_service:
            samba_manager.restart()
        else:
            samba_manager.reload()
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Samba configured with {shares.count()} shares')
        )
    
    def configure_nfs(self, test_only, restart_service):
        """Configure NFS service"""
        self.stdout.write('Configuring NFS...')
        
        # Get active NFS exports
        exports = NFSShare.objects.filter(enabled=True)
        
        # Generate exports
        exports_content = nfs_manager.generate_exports(exports)
        
        if test_only:
            self.stdout.write(
                self.style.SUCCESS(f'✓ NFS exports generated for {exports.count()} shares')
            )
            return
        
        # Reload exports
        if nfs_manager.reload_exports():
            self.stdout.write(
                self.style.SUCCESS(f'✓ NFS configured with {exports.count()} exports')
            )
        else:
            raise Exception('Failed to reload NFS exports')
        
        if restart_service:
            nfs_manager.restart()
    
    def configure_ftp(self, test_only, restart_service):
        """Configure FTP service"""
        self.stdout.write('Configuring FTP...')
        
        # Generate FTP configuration
        config_content = ftp_manager.generate_config()
        
        if test_only:
            self.stdout.write(
                self.style.SUCCESS('✓ FTP configuration generated')
            )
            return
        
        if restart_service:
            ftp_manager.restart()
        
        self.stdout.write(
            self.style.SUCCESS('✓ FTP service configured')
        )
    
    def configure_nginx(self, test_only, restart_service):
        """Configure Nginx reverse proxy"""
        self.stdout.write('Configuring Nginx...')
        
        context = {
            'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'server_name': '_',
            'max_upload_size': '1G',
            'ssl_enabled': False,
        }
        
        # Generate Nginx configuration
        config_content = template_engine.render_template('nginx/moxnas.conf.j2', context)
        
        if test_only:
            self.stdout.write(
                self.style.SUCCESS('✓ Nginx configuration generated')
            )
            return
        
        # Write Nginx configuration
        nginx_config_path = '/etc/nginx/sites-available/moxnas'
        template_engine.write_config(nginx_config_path, config_content)
        
        # Enable site
        nginx_enabled_path = '/etc/nginx/sites-enabled/moxnas'
        if not os.path.exists(nginx_enabled_path):
            os.symlink(nginx_config_path, nginx_enabled_path)
        
        # Test Nginx configuration
        result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f'Invalid Nginx configuration: {result.stderr}')
        
        if restart_service:
            subprocess.run(['systemctl', 'restart', 'nginx'])
        else:
            subprocess.run(['systemctl', 'reload', 'nginx'])
        
        self.stdout.write(
            self.style.SUCCESS('✓ Nginx configured and reloaded')
        )
    
    def configure_systemd(self, test_only, restart_service):
        """Configure systemd services"""
        self.stdout.write('Configuring systemd services...')
        
        # Create service directories
        dirs_to_create = [
            '/var/log/moxnas',
            '/run/moxnas',
            '/etc/systemd/system'
        ]
        
        for dir_path in dirs_to_create:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # MoxNAS main service
        main_service_context = {
            'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'app_user': 'root',
            'app_group': 'root',
            'workers': '3',
            'timeout': '300',
            'log_level': 'info'
        }
        
        main_service_content = template_engine.render_template(
            'systemd/moxnas.service.j2', 
            main_service_context
        )
        
        # Monitor service
        monitor_service_context = {
            'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'app_user': 'root',
            'app_group': 'root'
        }
        
        monitor_service_content = template_engine.render_template(
            'systemd/moxnas-monitor.service.j2',
            monitor_service_context
        )
        
        if test_only:
            self.stdout.write(
                self.style.SUCCESS('✓ Systemd service files generated')
            )
            return
        
        # Write service files
        template_engine.write_config(
            '/etc/systemd/system/moxnas.service',
            main_service_content
        )
        
        template_engine.write_config(
            '/etc/systemd/system/moxnas-monitor.service',
            monitor_service_content
        )
        
        # Reload systemd
        subprocess.run(['systemctl', 'daemon-reload'])
        
        # Enable services
        subprocess.run(['systemctl', 'enable', 'moxnas'])
        subprocess.run(['systemctl', 'enable', 'moxnas-monitor'])
        
        if restart_service:
            subprocess.run(['systemctl', 'restart', 'moxnas'])
            subprocess.run(['systemctl', 'restart', 'moxnas-monitor'])
        
        self.stdout.write(
            self.style.SUCCESS('✓ Systemd services configured and enabled')
        )