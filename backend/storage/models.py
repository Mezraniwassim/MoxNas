from django.db import models
from django.core.validators import RegexValidator

class Dataset(models.Model):
    name = models.CharField(
        max_length=255, 
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[a-zA-Z0-9_-]+$',
                message='Dataset name can only contain letters, numbers, underscores, and hyphens'
            )
        ]
    )
    path = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    compression = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Share(models.Model):
    PROTOCOL_CHOICES = [
        ('smb', 'SMB/CIFS'),
        ('nfs', 'NFS'),
        ('ftp', 'FTP'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    path = models.CharField(max_length=512)
    protocol = models.CharField(max_length=10, choices=PROTOCOL_CHOICES)
    description = models.TextField(blank=True)
    read_only = models.BooleanField(default=False)
    guest_ok = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # SMB specific fields
    smb_browseable = models.BooleanField(default=True)
    smb_writable = models.BooleanField(default=True)
    
    # NFS specific fields
    nfs_readonly = models.BooleanField(default=False)
    nfs_sync = models.BooleanField(default=True)
    nfs_subtree_check = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} ({self.get_protocol_display()})"
    
    class Meta:
        ordering = ['name']

class MountPoint(models.Model):
    path = models.CharField(max_length=512, unique=True)
    source = models.CharField(max_length=512)
    filesystem = models.CharField(max_length=50, default='ext4')
    options = models.CharField(max_length=255, default='defaults')
    auto_mount = models.BooleanField(default=True)
    mounted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.source} -> {self.path}"
    
    class Meta:
        ordering = ['path']