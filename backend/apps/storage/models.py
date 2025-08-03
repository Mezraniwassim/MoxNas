from django.db import models
from django.contrib.auth.models import User
from apps.containers.models import MoxNasContainer


class Dataset(models.Model):
    """Storage datasets"""
    container = models.ForeignKey(MoxNasContainer, on_delete=models.CASCADE, related_name='datasets')
    name = models.CharField(max_length=100)
    path = models.CharField(max_length=255)
    mount_point = models.CharField(max_length=255, blank=True)
    size_limit = models.BigIntegerField(null=True, blank=True)  # bytes
    used_space = models.BigIntegerField(default=0)  # bytes
    
    # Dataset properties
    compression = models.CharField(max_length=20, default='lz4', choices=[
        ('off', 'Off'),
        ('lz4', 'LZ4'),
        ('gzip', 'GZIP'),
        ('zstd', 'ZSTD'),
    ])
    deduplication = models.BooleanField(default=False)
    readonly = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['container', 'name']
        verbose_name = 'Dataset'
        verbose_name_plural = 'Datasets'
    
    def __str__(self):
        return f"{self.name} on {self.container.name}"
    
    @property
    def usage_percentage(self):
        if not self.size_limit:
            return 0
        return min(100, (self.used_space / self.size_limit) * 100)


class Share(models.Model):
    """NAS shares"""
    SHARE_TYPES = [
        ('nfs', 'NFS Share'),
        ('smb', 'SMB/CIFS Share'),
        ('ftp', 'FTP Share'),
        ('webdav', 'WebDAV Share'),
    ]
    
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='shares')
    name = models.CharField(max_length=100)
    share_type = models.CharField(max_length=10, choices=SHARE_TYPES)
    path = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Share settings
    is_enabled = models.BooleanField(default=True)
    readonly = models.BooleanField(default=False)
    browseable = models.BooleanField(default=True)
    guest_access = models.BooleanField(default=False)
    
    # Configuration JSON for service-specific settings
    config = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['dataset', 'name', 'share_type']
        verbose_name = 'Share'
        verbose_name_plural = 'Shares'
    
    def __str__(self):
        return f"{self.name} ({self.get_share_type_display()})"


class ShareACL(models.Model):
    """Access Control Lists for shares"""
    ACL_TYPES = [
        ('user', 'User'),
        ('group', 'Group'),
        ('everyone', 'Everyone'),
    ]
    
    PERMISSION_CHOICES = [
        ('read', 'Read Only'),
        ('write', 'Read/Write'),
        ('full', 'Full Control'),
        ('none', 'No Access'),
    ]
    
    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name='acls')
    acl_type = models.CharField(max_length=10, choices=ACL_TYPES)
    identifier = models.CharField(max_length=100)  # username, group name, or 'everyone'
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES)
    
    # Advanced permissions
    allow_read = models.BooleanField(default=True)
    allow_write = models.BooleanField(default=False)
    allow_execute = models.BooleanField(default=False)
    allow_delete = models.BooleanField(default=False)
    allow_modify_acl = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['share', 'acl_type', 'identifier']
        verbose_name = 'Share ACL'
        verbose_name_plural = 'Share ACLs'
    
    def __str__(self):
        return f"{self.share.name} - {self.identifier} ({self.permission})"


class UserAccount(models.Model):
    """NAS user accounts (separate from Django users)"""
    container = models.ForeignKey(MoxNasContainer, on_delete=models.CASCADE, related_name='nas_users')
    username = models.CharField(max_length=50)
    full_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    
    # Account settings
    is_active = models.BooleanField(default=True)
    home_directory = models.CharField(max_length=255, blank=True)
    shell = models.CharField(max_length=50, default='/bin/bash')
    
    # Service access
    allow_ssh = models.BooleanField(default=False)
    allow_ftp = models.BooleanField(default=True)
    allow_smb = models.BooleanField(default=True)
    allow_webdav = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['container', 'username']
        verbose_name = 'NAS User'
        verbose_name_plural = 'NAS Users'
    
    def __str__(self):
        return f"{self.username} on {self.container.name}"


class UserGroup(models.Model):
    """NAS user groups"""
    container = models.ForeignKey(MoxNasContainer, on_delete=models.CASCADE, related_name='nas_groups')
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    users = models.ManyToManyField(UserAccount, related_name='groups', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['container', 'name']
        verbose_name = 'NAS Group'
        verbose_name_plural = 'NAS Groups'
    
    def __str__(self):
        return f"{self.name} on {self.container.name}"