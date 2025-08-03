from django.db import models
from django.contrib.auth.models import User
from apps.proxmox.models import ProxmoxNode


class MoxNasContainer(models.Model):
    """Model to track MoxNas containers"""
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('creating', 'Creating'),
        ('deleting', 'Deleting'),
        ('error', 'Error'),
    ]
    
    vmid = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    hostname = models.CharField(max_length=100)
    node = models.ForeignKey(ProxmoxNode, on_delete=models.CASCADE, related_name='containers')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='stopped')
    
    # Container specifications
    memory = models.PositiveIntegerField(default=2048)  # MB
    cores = models.PositiveIntegerField(default=2)
    swap = models.PositiveIntegerField(default=512)  # MB
    storage = models.CharField(max_length=100, default='local-lvm')
    
    # Network configuration
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    gateway = models.GenericIPAddressField(null=True, blank=True)
    bridge = models.CharField(max_length=20, default='vmbr0')
    
    # MoxNas specific
    is_moxnas_ready = models.BooleanField(default=False)
    moxnas_version = models.CharField(max_length=50, blank=True)
    installation_log = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'MoxNas Container'
        verbose_name_plural = 'MoxNas Containers'
        ordering = ['vmid']
    
    def __str__(self):
        return f"Container {self.vmid} - {self.name}"
    
    @property
    def web_url(self):
        """Get the web interface URL for this container"""
        if self.ip_address and self.is_moxnas_ready:
            return f"http://{self.ip_address}:8000"
        return None


class ContainerService(models.Model):
    """Services running in a container"""
    SERVICE_TYPES = [
        ('ftp', 'FTP Server'),
        ('nfs', 'NFS Server'),
        ('smb', 'SMB/CIFS Server'),
        ('ssh', 'SSH Server'),
        ('webdav', 'WebDAV Server'),
    ]
    
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
        ('configuring', 'Configuring'),
    ]
    
    container = models.ForeignKey(MoxNasContainer, on_delete=models.CASCADE, related_name='services')
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='stopped')
    port = models.PositiveIntegerField()
    config = models.JSONField(default=dict, blank=True)
    
    is_enabled = models.BooleanField(default=True)
    auto_start = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Container Service'
        verbose_name_plural = 'Container Services'
        unique_together = ['container', 'service_type']
    
    def __str__(self):
        return f"{self.get_service_type_display()} on {self.container.name}"


class ContainerBackup(models.Model):
    """Container backup information"""
    container = models.ForeignKey(MoxNasContainer, on_delete=models.CASCADE, related_name='backups')
    backup_file = models.CharField(max_length=255)
    backup_type = models.CharField(max_length=20, choices=[
        ('snapshot', 'Snapshot'),
        ('backup', 'Full Backup'),
        ('clone', 'Clone'),
    ])
    size = models.BigIntegerField(null=True, blank=True)  # bytes
    description = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Container Backup'
        verbose_name_plural = 'Container Backups'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Backup of {self.container.name} - {self.backup_type}"