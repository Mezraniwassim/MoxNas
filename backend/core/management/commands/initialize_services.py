from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import ServiceStatus, SystemInfo
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Initialize MoxNAS services and default data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-initialization even if data exists',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initializing MoxNAS services...'))
        
        # Initialize ServiceStatus entries
        services_created = 0
        for service_name, config in ServiceStatus.DEFAULT_SERVICES.items():
            service, created = ServiceStatus.objects.get_or_create(
                name=service_name,
                defaults={
                    'port': config['port'],
                    'enabled': config['enabled'],
                    'running': False
                }
            )
            if created:
                services_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created service: {service.get_name_display()}')
                )
            elif options['force']:
                service.port = config['port']
                service.enabled = config['enabled']
                service.save()
                self.stdout.write(
                    self.style.WARNING(f'Updated service: {service.get_name_display()}')
                )
        
        if services_created == 0 and not options['force']:
            self.stdout.write(
                self.style.WARNING('All services already exist. Use --force to update.')
            )
        
        # Initialize SystemInfo
        hostname = os.uname().nodename
        system_info, created = SystemInfo.objects.get_or_create(
            id=1,
            defaults={
                'hostname': hostname,
                'version': '1.0.0',
                'uptime': 0
            }
        )
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created system info for {hostname}')
            )
        
        # Create default admin user if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@moxnas.local',
                password='moxnas123'
            )
            if hasattr(admin_user, 'full_name'):
                admin_user.full_name = 'MoxNAS Administrator'
                admin_user.save()
            self.stdout.write(
                self.style.SUCCESS('Created admin user (admin/moxnas123)')
            )
        
        total_services = ServiceStatus.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'✅ Initialization complete! {total_services} services ready.')
        )