from django.db import models

class ProxmoxNode(models.Model):
    """Proxmox node configuration"""
    name = models.CharField(max_length=255, unique=True)
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=8006)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)  # Should be encrypted in production
    realm = models.CharField(max_length=50, default='pam')
    ssl_verify = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.host})"

class LXCContainer(models.Model):
    """LXC container managed by MoxNAS"""
    STATUS_CHOICES = [
        ('stopped', 'Stopped'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('unknown', 'Unknown'),
    ]
    
    vmid = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    node = models.ForeignKey(ProxmoxNode, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unknown')
    memory = models.IntegerField(default=2048)  # MB
    disk_size = models.IntegerField(default=8)  # GB
    cores = models.IntegerField(default=2)
    template = models.CharField(max_length=255, default='ubuntu-22.04-standard')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"CT{self.vmid} - {self.name}"
    
    class Meta:
        ordering = ['vmid']