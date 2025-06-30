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
    
    name = models.CharField(max_length=20, choices=SERVICE_CHOICES, unique=True)
    enabled = models.BooleanField(default=True)
    running = models.BooleanField(default=False)
    port = models.IntegerField()
    last_checked = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_name_display()} - {'Running' if self.running else 'Stopped'}"

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