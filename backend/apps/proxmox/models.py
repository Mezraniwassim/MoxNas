from django.db import models
from django.contrib.auth.models import User


class ProxmoxNode(models.Model):
    name = models.CharField(max_length=100, unique=True)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField(default=8006)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=255)
    verify_ssl = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proxmox Node'
        verbose_name_plural = 'Proxmox Nodes'

    def __str__(self):
        return f"{self.name} ({self.host})"


class ProxmoxConnection(models.Model):
    """Store connection status and information"""
    node = models.OneToOneField(ProxmoxNode, on_delete=models.CASCADE, related_name='connection')
    is_connected = models.BooleanField(default=False)
    last_connected = models.DateTimeField(null=True, blank=True)
    connection_error = models.TextField(blank=True)
    proxmox_version = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return f"Connection to {self.node.name}"