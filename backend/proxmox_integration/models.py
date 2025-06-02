"""
Django models for Proxmox integration
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import json


class ProxmoxHost(models.Model):
    """Proxmox host configuration"""
    
    name = models.CharField(max_length=100, unique=True)
    host = models.CharField(max_length=255, help_text="IP address or hostname")
    port = models.IntegerField(default=8006)
    user = models.CharField(max_length=100, default="root@pam")
    verify_ssl = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_connected = models.BooleanField(default=False)
    last_connected = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.host})"


class ProxmoxNode(models.Model):
    """Proxmox cluster nodes"""
    
    proxmox_host = models.ForeignKey(ProxmoxHost, on_delete=models.CASCADE, related_name='nodes')
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default='unknown')
    uptime = models.BigIntegerField(default=0)
    cpu_usage = models.FloatField(default=0.0)
    memory_total = models.BigIntegerField(default=0)
    memory_used = models.BigIntegerField(default=0)
    storage_total = models.BigIntegerField(default=0)
    storage_used = models.BigIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['proxmox_host', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.proxmox_host.name}:{self.name}"
    
    @property
    def memory_usage_percentage(self):
        if self.memory_total == 0:
            return 0
        return (self.memory_used / self.memory_total) * 100
    
    @property
    def storage_usage_percentage(self):
        if self.storage_total == 0:
            return 0
        return (self.storage_used / self.storage_total) * 100


class ProxmoxContainer(models.Model):
    """LXC containers managed by Proxmox"""
    
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('suspended', 'Suspended'),
        ('unknown', 'Unknown'),
    ]
    
    proxmox_node = models.ForeignKey(ProxmoxNode, on_delete=models.CASCADE, related_name='containers')
    vmid = models.IntegerField()
    name = models.CharField(max_length=100)
    hostname = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    template = models.CharField(max_length=100, blank=True)
    cores = models.IntegerField(default=1)
    memory = models.BigIntegerField(default=512)  # MB
    swap = models.BigIntegerField(default=0)      # MB
    disk_size = models.BigIntegerField(default=0) # GB
    uptime = models.BigIntegerField(default=0)    # seconds
    cpu_usage = models.FloatField(default=0.0)
    memory_usage = models.BigIntegerField(default=0)
    is_moxnas = models.BooleanField(default=False, help_text="Is this a MoxNAS container?")
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['proxmox_node', 'vmid']
        ordering = ['vmid']
    
    def __str__(self):
        return f"CT{self.vmid} - {self.name} ({self.status})"
    
    @property
    def memory_usage_percentage(self):
        if self.memory == 0:
            return 0
        return (self.memory_usage / (self.memory * 1024 * 1024)) * 100  # Convert MB to bytes


class ProxmoxStorage(models.Model):
    """Storage pools in Proxmox"""
    
    TYPE_CHOICES = [
        ('dir', 'Directory'),
        ('lvm', 'LVM'),
        ('lvmthin', 'LVM-Thin'),
        ('zfs', 'ZFS'),
        ('nfs', 'NFS'),
        ('cifs', 'CIFS'),
        ('glusterfs', 'GlusterFS'),
        ('cephfs', 'CephFS'),
        ('rbd', 'RBD'),
    ]
    
    proxmox_node = models.ForeignKey(ProxmoxNode, on_delete=models.CASCADE, related_name='storage')
    storage_id = models.CharField(max_length=100)
    storage_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    content_types = models.TextField(default='[]', help_text="JSON list of content types")
    total_space = models.BigIntegerField(default=0)  # bytes
    used_space = models.BigIntegerField(default=0)   # bytes
    available_space = models.BigIntegerField(default=0)  # bytes
    enabled = models.BooleanField(default=True)
    shared = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['proxmox_node', 'storage_id']
        ordering = ['storage_id']
    
    def __str__(self):
        return f"{self.proxmox_node.name}:{self.storage_id} ({self.storage_type})"
    
    @property
    def usage_percentage(self):
        if self.total_space == 0:
            return 0
        return (self.used_space / self.total_space) * 100
    
    @property
    def content_types_list(self):
        try:
            return json.loads(self.content_types)
        except json.JSONDecodeError:
            return []


class ProxmoxTask(models.Model):
    """Proxmox tasks and jobs"""
    
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('ok', 'OK'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('unknown', 'Unknown'),
    ]
    
    proxmox_node = models.ForeignKey(ProxmoxNode, on_delete=models.CASCADE, related_name='tasks')
    upid = models.CharField(max_length=255, unique=True)
    task_type = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    exitstatus = models.CharField(max_length=10, blank=True)
    starttime = models.DateTimeField()
    endtime = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0)  # seconds
    user = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['-starttime']
    
    def __str__(self):
        return f"{self.task_type} - {self.status} ({self.upid})"
