from django.db import models
from apps.containers.models import MoxNasContainer


class ServiceConfiguration(models.Model):
    """NAS Service configurations"""
    SERVICE_TYPES = [
        ('ftp', 'FTP Server'),
        ('nfs', 'NFS Server'),
        ('smb', 'SMB/CIFS Server'),
        ('ssh', 'SSH Server'),
        ('webdav', 'WebDAV Server'),
    ]
    
    container = models.ForeignKey(MoxNasContainer, on_delete=models.CASCADE, related_name='service_configs')
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    is_enabled = models.BooleanField(default=False)
    config = models.JSONField(default=dict)
    
    class Meta:
        unique_together = ['container', 'service_type']
    
    def __str__(self):
        return f"{self.get_service_type_display()} on {self.container.name}"