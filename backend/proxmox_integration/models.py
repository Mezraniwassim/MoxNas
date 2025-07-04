"""
Proxmox Integration Models for MoxNAS
Enhanced models for advanced Proxmox integration
"""
from django.db import models
from django.utils import timezone
import json


class ProxmoxHost(models.Model):
    """
    Proxmox host/cluster configuration
    """
    name = models.CharField(max_length=255, unique=True)
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=8006)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)  # Should be encrypted in production
    realm = models.CharField(max_length=50, default='pam')
    ssl_verify = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    cluster_name = models.CharField(max_length=255, blank=True, null=True)
    api_version = models.CharField(max_length=20, default='2.0')
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.host})"
    
    class Meta:
        ordering = ['name']


class ProxmoxNode(models.Model):
    """
    Individual Proxmox node within a host/cluster
    """
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('unknown', 'Unknown'),
    ]
    
    host = models.ForeignKey(ProxmoxHost, on_delete=models.CASCADE, related_name='nodes')
    name = models.CharField(max_length=255)
    node_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    cpu_cores = models.IntegerField(default=0)
    cpu_usage = models.FloatField(default=0.0)  # Percentage
    memory_total = models.BigIntegerField(default=0)  # Bytes
    memory_used = models.BigIntegerField(default=0)  # Bytes
    disk_total = models.BigIntegerField(default=0)  # Bytes
    disk_used = models.BigIntegerField(default=0)  # Bytes
    uptime = models.BigIntegerField(default=0)  # Seconds
    kernel_version = models.CharField(max_length=255, blank=True)
    pve_version = models.CharField(max_length=100, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.host.name} - {self.name}"
    
    class Meta:
        unique_together = ['host', 'node_id']
        ordering = ['host', 'name']


class ProxmoxContainer(models.Model):
    """
    LXC containers managed through Proxmox
    """
    STATUS_CHOICES = [
        ('stopped', 'Stopped'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('template', 'Template'),
        ('unknown', 'Unknown'),
    ]
    
    TYPE_CHOICES = [
        ('lxc', 'LXC Container'),
        ('qemu', 'QEMU VM'),
    ]
    
    host = models.ForeignKey(ProxmoxHost, on_delete=models.CASCADE, related_name='containers')
    node = models.ForeignKey(ProxmoxNode, on_delete=models.CASCADE, related_name='containers')
    vmid = models.IntegerField()
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='lxc')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    
    # Resource allocation
    memory = models.IntegerField(default=2048)  # MB
    memory_usage = models.IntegerField(default=0)  # MB
    disk_size = models.BigIntegerField(default=8589934592)  # Bytes (8GB default)
    disk_usage = models.BigIntegerField(default=0)  # Bytes
    cores = models.IntegerField(default=2)
    cpu_usage = models.FloatField(default=0.0)  # Percentage
    
    # Network configuration
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    mac_address = models.CharField(max_length=17, blank=True)
    network_in = models.BigIntegerField(default=0)  # Bytes
    network_out = models.BigIntegerField(default=0)  # Bytes
    
    # Template and OS information
    template = models.CharField(max_length=255, default='ubuntu-22.04-standard')
    os_type = models.CharField(max_length=50, blank=True)
    
    # Metadata
    description = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True)
    protection = models.BooleanField(default=False)
    
    # Timestamps
    uptime = models.BigIntegerField(default=0)  # Seconds
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.type.upper()}{self.vmid} - {self.name}"
    
    def get_memory_usage_percentage(self):
        """Calculate memory usage percentage"""
        if self.memory > 0:
            return (self.memory_usage / self.memory) * 100
        return 0
    
    def get_disk_usage_percentage(self):
        """Calculate disk usage percentage"""
        if self.disk_size > 0:
            return (self.disk_usage / self.disk_size) * 100
        return 0
    
    class Meta:
        unique_together = ['host', 'vmid']
        ordering = ['vmid']


class ProxmoxStorage(models.Model):
    """
    Storage configurations in Proxmox
    """
    STORAGE_TYPES = [
        ('dir', 'Directory'),
        ('nfs', 'NFS'),
        ('cifs', 'CIFS/SMB'),
        ('lvm', 'LVM'),
        ('zfs', 'ZFS'),
        ('cephfs', 'CephFS'),
        ('glusterfs', 'GlusterFS'),
        ('iscsi', 'iSCSI'),
    ]
    
    host = models.ForeignKey(ProxmoxHost, on_delete=models.CASCADE, related_name='storages')
    node = models.ForeignKey(ProxmoxNode, on_delete=models.CASCADE, related_name='storages', null=True, blank=True)
    storage_id = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=STORAGE_TYPES)
    path = models.CharField(max_length=500, blank=True)
    server = models.CharField(max_length=255, blank=True)
    export = models.CharField(max_length=500, blank=True)
    
    # Storage metrics
    total_space = models.BigIntegerField(default=0)  # Bytes
    used_space = models.BigIntegerField(default=0)  # Bytes
    available_space = models.BigIntegerField(default=0)  # Bytes
    
    # Configuration
    content_types = models.CharField(max_length=200, default='images,vztmpl,iso,backup')
    enabled = models.BooleanField(default=True)
    shared = models.BooleanField(default=False)
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.storage_id} ({self.type})"
    
    def get_usage_percentage(self):
        """Calculate storage usage percentage"""
        if self.total_space > 0:
            return (self.used_space / self.total_space) * 100
        return 0
    
    class Meta:
        unique_together = ['host', 'storage_id']
        ordering = ['storage_id']


class ProxmoxTask(models.Model):
    """
    Proxmox task tracking
    """
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('ok', 'OK'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('unknown', 'Unknown'),
    ]
    
    TYPE_CHOICES = [
        ('backup', 'Backup'),
        ('restore', 'Restore'),
        ('create', 'Create'),
        ('destroy', 'Destroy'),
        ('start', 'Start'),
        ('stop', 'Stop'),
        ('migrate', 'Migrate'),
        ('clone', 'Clone'),
        ('template', 'Template'),
        ('other', 'Other'),
    ]
    
    host = models.ForeignKey(ProxmoxHost, on_delete=models.CASCADE, related_name='tasks')
    node = models.ForeignKey(ProxmoxNode, on_delete=models.CASCADE, related_name='tasks')
    task_id = models.CharField(max_length=100)
    upid = models.CharField(max_length=200, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='other')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    user = models.CharField(max_length=100)
    
    # Task details
    description = models.TextField(blank=True)
    progress = models.FloatField(default=0.0)  # Percentage
    starttime = models.DateTimeField()
    endtime = models.DateTimeField(null=True, blank=True)
    
    # Related objects
    vmid = models.IntegerField(null=True, blank=True)
    container = models.ForeignKey(
        ProxmoxContainer, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='tasks'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.type} - {self.task_id}"
    
    def get_duration(self):
        """Calculate task duration"""
        if self.endtime:
            return self.endtime - self.starttime
        return timezone.now() - self.starttime
    
    class Meta:
        ordering = ['-starttime']