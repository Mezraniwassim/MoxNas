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
            import secrets
            import string
            
            # Generate secure random password
            alphabet = string.ascii_letters + string.digits
            admin_password = ''.join(secrets.choice(alphabet) for _ in range(16))
            
            # Check for environment variable override
            admin_password = os.environ.get('MOXNAS_ADMIN_PASSWORD', admin_password)
            
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@moxnas.local',
                password=admin_password
            )
            if hasattr(admin_user, 'full_name'):
                admin_user.full_name = 'MoxNAS Administrator'
                admin_user.save()
            
            # Save password to secure location for first-time setup
            password_file = '/opt/moxnas/admin_password.txt'
            try:
                os.makedirs('/opt/moxnas', exist_ok=True)
                with open(password_file, 'w') as f:
                    f.write(f"Admin Username: admin\nAdmin Password: {admin_password}\n")
                os.chmod(password_file, 0o600)  # Read-write for owner only
                self.stdout.write(
                    self.style.SUCCESS(f'Created admin user. Password saved to {password_file}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Admin user created with password: {admin_password}')
                )
                self.stdout.write(
                    self.style.WARNING(f'Could not save to file: {e}')
                )
        
        total_services = ServiceStatus.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'✅ Initialization complete! {total_services} services ready.')
        )