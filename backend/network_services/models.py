from django.db import models
import json


class NetworkInterface(models.Model):
    """Network interface configuration"""
    name = models.CharField(max_length=50, unique=True)
    interface_type = models.CharField(max_length=20, default='ethernet')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    netmask = models.CharField(max_length=15, blank=True)
    gateway = models.GenericIPAddressField(null=True, blank=True)
    dns_servers = models.TextField(blank=True)  # JSON list
    dhcp_enabled = models.BooleanField(default=True)
    enabled = models.BooleanField(default=True)
    mtu = models.IntegerField(default=1500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.ip_address or 'DHCP'})"

    @property
    def dns_list(self):
        if self.dns_servers:
            try:
                return json.loads(self.dns_servers)
            except json.JSONDecodeError:
                return []
        return []

    @dns_list.setter
    def dns_list(self, value):
        self.dns_servers = json.dumps(value)


class SambaSetting(models.Model):
    """Samba/SMB configuration settings"""
    workgroup = models.CharField(max_length=50, default='WORKGROUP')
    server_string = models.CharField(max_length=100, default='MoxNAS Server')
    netbios_name = models.CharField(max_length=15, default='MOXNAS')
    security = models.CharField(max_length=20, default='user')
    guest_account = models.CharField(max_length=50, default='nobody')
    map_to_guest = models.CharField(max_length=20, default='Bad User')
    enable_recycle_bin = models.BooleanField(default=True)
    audit_enable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Samba Config - {self.netbios_name}"


class NFSSetting(models.Model):
    """NFS configuration settings"""
    nfs_v3_enabled = models.BooleanField(default=True)
    nfs_v4_enabled = models.BooleanField(default=True)
    rpc_mountd_port = models.IntegerField(default=20048)
    rpc_statd_port = models.IntegerField(default=20049)
    rpc_lockd_port = models.IntegerField(default=20050)
    enable_udp = models.BooleanField(default=True)
    servers = models.IntegerField(default=4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "NFS Configuration"


class FTPSetting(models.Model):
    """FTP configuration settings"""
    enabled = models.BooleanField(default=False)
    port = models.IntegerField(default=21)
    max_clients = models.IntegerField(default=50)
    max_per_ip = models.IntegerField(default=5)
    max_login_fail = models.IntegerField(default=3)
    timeout = models.IntegerField(default=600)
    anonymous_access = models.BooleanField(default=False)
    local_user_access = models.BooleanField(default=True)
    passive_ports_min = models.IntegerField(default=20000)
    passive_ports_max = models.IntegerField(default=25000)
    tls_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"FTP Configuration (Port {self.port})"


class SSHSetting(models.Model):
    """SSH configuration settings"""
    enabled = models.BooleanField(default=True)
    port = models.IntegerField(default=22)
    permit_root_login = models.BooleanField(default=False)
    password_authentication = models.BooleanField(default=True)
    pubkey_authentication = models.BooleanField(default=True)
    x11_forwarding = models.BooleanField(default=False)
    max_auth_tries = models.IntegerField(default=3)
    client_alive_interval = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SSH Configuration (Port {self.port})"
