from django.db import models
from django.contrib.auth.models import User
import os


class StoragePool(models.Model):
    """Storage pool representing mounted storage"""
    name = models.CharField(max_length=100, unique=True)
    mount_path = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    total_size = models.BigIntegerField(default=0)  # in bytes
    used_size = models.BigIntegerField(default=0)   # in bytes
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.mount_path})"

    @property
    def available_size(self):
        return self.total_size - self.used_size

    @property
    def usage_percentage(self):
        if self.total_size == 0:
            return 0
        return (self.used_size / self.total_size) * 100

    def update_size_info(self):
        """Update storage size information from filesystem"""
        if os.path.exists(self.mount_path):
            stat = os.statvfs(self.mount_path)
            self.total_size = stat.f_frsize * stat.f_blocks
            self.used_size = stat.f_frsize * (stat.f_blocks - stat.f_available)
            self.save()


class Dataset(models.Model):
    """Dataset within a storage pool"""
    COMPRESSION_CHOICES = [
        ('none', 'None'),
        ('gzip', 'Gzip'),
        ('lz4', 'LZ4'),
    ]

    name = models.CharField(max_length=100)
    storage_pool = models.ForeignKey(StoragePool, on_delete=models.CASCADE, related_name='datasets')
    path = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    compression = models.CharField(max_length=20, choices=COMPRESSION_CHOICES, default='none')
    quota = models.BigIntegerField(null=True, blank=True)  # in bytes
    readonly = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ['storage_pool', 'name']

    def __str__(self):
        return f"{self.storage_pool.name}/{self.name}"

    @property
    def full_path(self):
        return os.path.join(self.storage_pool.mount_path, self.path)


class Share(models.Model):
    """Network shares (SMB, NFS, etc.)"""
    SHARE_TYPES = [
        ('smb', 'SMB/CIFS'),
        ('nfs', 'NFS'),
        ('ftp', 'FTP'),
    ]

    name = models.CharField(max_length=100, unique=True)
    share_type = models.CharField(max_length=10, choices=SHARE_TYPES)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name='shares')
    path = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    readonly = models.BooleanField(default=False)
    guest_access = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.share_type.upper()})"


class AccessControlList(models.Model):
    """Access Control Lists for shares"""
    PERMISSION_CHOICES = [
        ('read', 'Read'),
        ('write', 'Write'),
        ('full', 'Full Control'),
    ]

    share = models.ForeignKey(Share, on_delete=models.CASCADE, related_name='acls')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    group_name = models.CharField(max_length=100, blank=True)  # For system groups
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['share', 'user', 'group_name']

    def __str__(self):
        target = self.user.username if self.user else self.group_name
        return f"{self.share.name} - {target} ({self.permission})"
