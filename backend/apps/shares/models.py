from django.db import models
from apps.storage.models import MountPoint
import os
import logging

logger = logging.getLogger(__name__)

class SMBShare(models.Model):
    """SMB/CIFS Share configuration"""
    name = models.CharField(max_length=100, unique=True, help_text="Share name")
    path = models.CharField(max_length=255, help_text="Share path")
    mount_point = models.ForeignKey(
        MountPoint, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Associated mount point"
    )
    comment = models.TextField(blank=True, help_text="Share description")
    read_only = models.BooleanField(default=False)
    guest_ok = models.BooleanField(default=False, help_text="Allow guest access")
    browseable = models.BooleanField(default=True, help_text="Visible in network browser")
    enabled = models.BooleanField(default=True)
    valid_users = models.TextField(
        blank=True, 
        help_text="Comma-separated list of users with access"
    )
    write_list = models.TextField(
        blank=True, 
        help_text="Comma-separated list of users with write access"
    )
    create_mask = models.CharField(max_length=10, default='0755', help_text="File creation mask")
    directory_mask = models.CharField(max_length=10, default='0755', help_text="Directory creation mask")
    
    # Advanced options
    force_user = models.CharField(max_length=100, blank=True)
    force_group = models.CharField(max_length=100, blank=True)
    inherit_acls = models.BooleanField(default=False)
    inherit_permissions = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        """Validate share configuration"""
        from django.core.exceptions import ValidationError
        
        # Validate path exists
        if not os.path.exists(self.path):
            raise ValidationError(f"Path {self.path} does not exist")
        
        # Validate permissions
        if not os.access(self.path, os.R_OK):
            raise ValidationError(f"Path {self.path} is not readable")

class NFSShare(models.Model):
    """NFS Share configuration"""
    path = models.CharField(max_length=255, unique=True, help_text="Export path")
    mount_point = models.ForeignKey(
        MountPoint, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Associated mount point"
    )
    network = models.CharField(
        max_length=100, 
        default='*', 
        help_text="Network/host pattern (e.g., 192.168.1.0/24, *, hostname)"
    )
    options = models.CharField(
        max_length=255, 
        default='rw,sync,no_subtree_check',
        help_text="NFS export options"
    )
    enabled = models.BooleanField(default=True)
    comment = models.TextField(blank=True)
    
    # NFS specific options
    root_squash = models.BooleanField(default=True, help_text="Map root user to anonymous")
    all_squash = models.BooleanField(default=False, help_text="Map all users to anonymous")
    anonuid = models.IntegerField(null=True, blank=True, help_text="Anonymous user ID")
    anongid = models.IntegerField(null=True, blank=True, help_text="Anonymous group ID")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['path']

    def __str__(self):
        return f"{self.path} ({self.network})"

    def get_export_line(self):
        """Generate exports file line"""
        options = self.options
        
        if not self.root_squash:
            options += ',no_root_squash'
        if self.all_squash:
            options += ',all_squash'
        if self.anonuid:
            options += f',anonuid={self.anonuid}'
        if self.anongid:
            options += f',anongid={self.anongid}'
            
        return f"{self.path} {self.network}({options})"

class FTPShare(models.Model):
    """FTP Share/Directory configuration"""
    name = models.CharField(max_length=100, unique=True, help_text="FTP directory name")
    path = models.CharField(max_length=255, help_text="Local directory path")
    mount_point = models.ForeignKey(
        MountPoint, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="Associated mount point"
    )
    enabled = models.BooleanField(default=True)
    read_only = models.BooleanField(default=False)
    anonymous_access = models.BooleanField(default=False, help_text="Allow anonymous FTP access")
    valid_users = models.TextField(
        blank=True, 
        help_text="Comma-separated list of users with access"
    )
    comment = models.TextField(blank=True)
    
    # FTP specific settings
    upload_enable = models.BooleanField(default=True)
    download_enable = models.BooleanField(default=True)
    max_clients = models.IntegerField(default=10, help_text="Maximum concurrent clients")
    max_per_ip = models.IntegerField(default=3, help_text="Maximum connections per IP")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class SharePermission(models.Model):
    """Share permission management"""
    PERMISSION_CHOICES = [
        ('read', 'Read Only'),
        ('write', 'Read/Write'),
        ('full', 'Full Control'),
        ('deny', 'Deny Access'),
    ]
    
    SHARE_TYPE_CHOICES = [
        ('smb', 'SMB Share'),
        ('nfs', 'NFS Share'),
        ('ftp', 'FTP Share'),
    ]
    
    share_type = models.CharField(max_length=10, choices=SHARE_TYPE_CHOICES)
    share_id = models.IntegerField(help_text="ID of the share")
    user = models.CharField(max_length=100, help_text="Username")
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['share_type', 'share_id', 'user']
        ordering = ['share_type', 'share_id', 'user']

    def __str__(self):
        return f"{self.share_type} - {self.user} - {self.permission}"