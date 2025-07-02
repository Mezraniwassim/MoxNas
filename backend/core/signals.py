from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps
from .models import ServiceStatus

@receiver(post_migrate)
def initialize_services_after_migration(sender, **kwargs):
    """Initialize default services after migrations"""
    if sender.name == 'core':
        try:
            # Only initialize if no services exist
            if ServiceStatus.objects.count() == 0:
                ServiceStatus.initialize_default_services()
                print("✅ Initialized default services")
        except Exception as e:
            print(f"⚠️  Could not initialize services: {e}")