from django.db import models
from django.utils import timezone

class SystemInfo(models.Model):
    hostname = models.CharField(max_length=255)
    version = models.CharField(max_length=50, default="1.0.0")
    uptime = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "System Information"
        verbose_name_plural = "System Information"

class ServiceStatus(models.Model):
    SERVICE_CHOICES = [
        ('smb', 'SMB/CIFS'),
        ('nfs', 'NFS'),
        ('ftp', 'FTP'),
        ('ssh', 'SSH'),
        ('snmp', 'SNMP'),
        ('iscsi', 'iSCSI'),
    ]
    
    # Default service configurations
    DEFAULT_SERVICES = {
        'smb': {'port': 445, 'enabled': True},
        'nfs': {'port': 2049, 'enabled': True},
        'ftp': {'port': 21, 'enabled': True},
        'ssh': {'port': 22, 'enabled': True},
        'snmp': {'port': 161, 'enabled': True},
        'iscsi': {'port': 3260, 'enabled': True},
    }
    
    name = models.CharField(max_length=20, choices=SERVICE_CHOICES, unique=True)
    enabled = models.BooleanField(default=True)
    running = models.BooleanField(default=False)
    port = models.IntegerField()
    last_checked = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_name_display()} - {'Running' if self.running else 'Stopped'}"
    
    @classmethod
    def initialize_default_services(cls):
        """Initialize default services if they don't exist"""
        for service_name, config in cls.DEFAULT_SERVICES.items():
            cls.objects.get_or_create(
                name=service_name,
                defaults={
                    'port': config['port'],
                    'enabled': config['enabled'],
                    'running': False
                }
            )
    
    @classmethod
    def ensure_services_exist(cls):
        """Ensure all required services exist in database"""
        if cls.objects.count() == 0:
            cls.initialize_default_services()
        return cls.objects.all()

class LogEntry(models.Model):
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    timestamp = models.DateTimeField(default=timezone.now)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    service = models.CharField(max_length=50)
    message = models.TextField()
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.timestamp} - {self.level} - {self.service}"