from django.db import models
from django.contrib.auth.models import AbstractUser

class MoxNASUser(AbstractUser):
    """Custom user model for MoxNAS"""
    full_name = models.CharField(max_length=255, blank=True)
    home_directory = models.CharField(max_length=512, default='/mnt/storage/users/')
    shell = models.CharField(max_length=255, default='/bin/bash')
    samba_enabled = models.BooleanField(default=True)
    nfs_enabled = models.BooleanField(default=True)
    ftp_enabled = models.BooleanField(default=True)
    ssh_enabled = models.BooleanField(default=False)
    quota_bytes = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

class MoxNASGroup(models.Model):
    """Custom group model for MoxNAS"""
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    gid = models.IntegerField(unique=True, null=True, blank=True)
    users = models.ManyToManyField(MoxNASUser, related_name='moxnas_groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class AccessControlList(models.Model):
    """ACL for file/directory permissions"""
    ACL_TYPES = [
        ('user', 'User'),
        ('group', 'Group'),
        ('other', 'Other'),
        ('mask', 'Mask'),
    ]
    
    PERMISSION_CHOICES = [
        ('r', 'Read'),
        ('w', 'Write'),
        ('x', 'Execute'),
        ('rw', 'Read/Write'),
        ('rx', 'Read/Execute'),
        ('wx', 'Write/Execute'),
        ('rwx', 'Full Access'),
        ('-', 'No Access'),
    ]

    path = models.CharField(max_length=512)
    acl_type = models.CharField(max_length=10, choices=ACL_TYPES)
    target_user = models.ForeignKey(MoxNASUser, null=True, blank=True, on_delete=models.CASCADE)
    target_group = models.ForeignKey(MoxNASGroup, null=True, blank=True, on_delete=models.CASCADE)
    permissions = models.CharField(max_length=10, choices=PERMISSION_CHOICES)
    recursive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['path', 'acl_type', 'target_user', 'target_group']

    def __str__(self):
        target = self.target_user or self.target_group or 'other'
        return f"{self.path} - {self.acl_type}:{target}:{self.permissions}"