from django.db import models
from django.core.validators import RegexValidator
from core.models import BaseModel


class NetworkInterface(BaseModel):
    """Network interface configuration"""
    INTERFACE_TYPES = [
        ('ethernet', 'Ethernet'),
        ('wireless', 'Wireless'),
        ('bridge', 'Bridge'),
        ('bond', 'Bond'),
        ('vlan', 'VLAN'),
    ]
    
    name = models.CharField(max_length=20, unique=True, help_text="Interface name (e.g., eth0, wlan0)")
    interface_type = models.CharField(max_length=20, choices=INTERFACE_TYPES, default='ethernet')
    mac_address = models.CharField(
        max_length=17,
        validators=[RegexValidator(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')],
        blank=True,
        help_text="MAC address in format AA:BB:CC:DD:EE:FF"
    )
    enabled = models.BooleanField(default=True)
    auto_start = models.BooleanField(default=True, help_text="Start interface on boot")
    mtu = models.IntegerField(default=1500, help_text="Maximum Transmission Unit")
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name} ({self.interface_type})"


class IPConfiguration(BaseModel):
    """IP configuration for network interfaces"""
    CONFIG_METHODS = [
        ('static', 'Static IP'),
        ('dhcp', 'DHCP'),
        ('manual', 'Manual'),
    ]
    
    interface = models.ForeignKey(NetworkInterface, on_delete=models.CASCADE, related_name='ip_configs')
    method = models.CharField(max_length=10, choices=CONFIG_METHODS, default='dhcp')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    netmask = models.GenericIPAddressField(null=True, blank=True)
    gateway = models.GenericIPAddressField(null=True, blank=True)
    dns_servers = models.TextField(blank=True, help_text="Comma-separated DNS servers")
    is_primary = models.BooleanField(default=False, help_text="Primary IP configuration")
    
    class Meta:
        ordering = ['-is_primary', 'ip_address']
        
    def __str__(self):
        if self.ip_address:
            return f"{self.interface.name}: {self.ip_address}"
        return f"{self.interface.name}: {self.method}"


class NetworkRoute(BaseModel):
    """Static network routes"""
    destination = models.CharField(max_length=18, help_text="Destination network (e.g., 192.168.1.0/24)")
    gateway = models.GenericIPAddressField(help_text="Gateway IP address")
    interface = models.ForeignKey(NetworkInterface, on_delete=models.CASCADE, null=True, blank=True)
    metric = models.IntegerField(default=100, help_text="Route metric/priority")
    enabled = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['destination']
        unique_together = ['destination', 'gateway']
        
    def __str__(self):
        return f"{self.destination} via {self.gateway}"


class VLANConfiguration(BaseModel):
    """VLAN configuration for interfaces"""
    parent_interface = models.ForeignKey(NetworkInterface, on_delete=models.CASCADE, related_name='vlans')
    vlan_id = models.IntegerField(help_text="VLAN ID (1-4094)")
    name = models.CharField(max_length=50, help_text="VLAN name")
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['vlan_id']
        unique_together = ['parent_interface', 'vlan_id']
        
    def __str__(self):
        return f"{self.parent_interface.name}.{self.vlan_id} ({self.name})"


class FirewallRule(BaseModel):
    """Basic firewall rules"""
    ACTIONS = [
        ('accept', 'Accept'),
        ('drop', 'Drop'),
        ('reject', 'Reject'),
    ]
    
    PROTOCOLS = [
        ('tcp', 'TCP'),
        ('udp', 'UDP'),
        ('icmp', 'ICMP'),
        ('all', 'All'),
    ]
    
    name = models.CharField(max_length=100, help_text="Rule name")
    enabled = models.BooleanField(default=True)
    action = models.CharField(max_length=10, choices=ACTIONS, default='accept')
    protocol = models.CharField(max_length=10, choices=PROTOCOLS, default='tcp')
    source_ip = models.CharField(max_length=18, blank=True, help_text="Source IP/CIDR (blank for any)")
    destination_ip = models.CharField(max_length=18, blank=True, help_text="Destination IP/CIDR (blank for any)")
    source_port = models.CharField(max_length=20, blank=True, help_text="Source port(s)")
    destination_port = models.CharField(max_length=20, blank=True, help_text="Destination port(s)")
    interface = models.ForeignKey(NetworkInterface, on_delete=models.CASCADE, null=True, blank=True)
    priority = models.IntegerField(default=100, help_text="Rule priority (lower = higher priority)")
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['priority', 'name']
        
    def __str__(self):
        return f"{self.name}: {self.action} {self.protocol}"