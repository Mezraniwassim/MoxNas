from django.db import models
from django.contrib.auth.models import User
import json


class SystemInfo(models.Model):
    """System information and status"""
    hostname = models.CharField(max_length=100)
    version = models.CharField(max_length=50)
    uptime = models.BigIntegerField(default=0)  # seconds
    cpu_usage = models.FloatField(default=0.0)  # percentage
    memory_total = models.BigIntegerField(default=0)  # bytes
    memory_used = models.BigIntegerField(default=0)   # bytes
    load_average = models.TextField(default='0.0,0.0,0.0')  # 1,5,15 min
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"System Info - {self.hostname}"

    @property
    def memory_usage_percentage(self):
        if self.memory_total == 0:
            return 0
        return (self.memory_used / self.memory_total) * 100

    @property
    def load_averages(self):
        try:
            return [float(x) for x in self.load_average.split(',')]
        except:
            return [0.0, 0.0, 0.0]


class SystemService(models.Model):
    """System services management"""
    SERVICE_STATUS = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('failed', 'Failed'),
        ('unknown', 'Unknown'),
    ]

    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=SERVICE_STATUS, default='unknown')
    enabled = models.BooleanField(default=False)
    pid = models.IntegerField(null=True, blank=True)
    memory_usage = models.BigIntegerField(default=0)  # KB
    cpu_usage = models.FloatField(default=0.0)
    last_checked = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_name']

    def __str__(self):
        return f"{self.display_name} ({self.status})"


class CronJob(models.Model):
    """Scheduled tasks management"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    command = models.TextField()
    schedule = models.CharField(max_length=100)  # cron format
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.schedule})"


class SyncTask(models.Model):
    """Sync tasks (rsync, cloud sync, etc.)"""
    SYNC_TYPES = [
        ('rsync', 'Rsync'),
        ('cloud', 'Cloud Sync'),
        ('replication', 'Replication'),
    ]

    SYNC_STATUS = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    name = models.CharField(max_length=100)
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPES)
    source_path = models.CharField(max_length=500)
    destination_path = models.CharField(max_length=500)
    schedule = models.CharField(max_length=100, blank=True)  # cron format
    enabled = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=SYNC_STATUS, default='pending')
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    options = models.TextField(blank=True)  # JSON options
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.sync_type})"

    @property
    def sync_options(self):
        if self.options:
            try:
                return json.loads(self.options)
            except json.JSONDecodeError:
                return {}
        return {}


class UPSConfig(models.Model):
    """UPS configuration and monitoring"""
    UPS_MODES = [
        ('standalone', 'Standalone'),
        ('netserver', 'Network Server'),
        ('netclient', 'Network Client'),
    ]

    enabled = models.BooleanField(default=False)
    driver = models.CharField(max_length=100, blank=True)
    port = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=200, blank=True)
    mode = models.CharField(max_length=20, choices=UPS_MODES, default='standalone')
    shutdown_mode = models.CharField(max_length=50, default='ups_loss')
    shutdown_timer = models.IntegerField(default=30)  # seconds
    email_notify = models.BooleanField(default=False)
    email_subject = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"UPS Config ({self.mode})"


class SNMPConfig(models.Model):
    """SNMP configuration"""
    enabled = models.BooleanField(default=False)
    location = models.CharField(max_length=200, blank=True)
    contact = models.CharField(max_length=200, blank=True)
    community = models.CharField(max_length=100, default='public')
    v3_enabled = models.BooleanField(default=False)
    v3_username = models.CharField(max_length=100, blank=True)
    v3_auth_type = models.CharField(max_length=20, default='MD5')
    v3_privacy_type = models.CharField(max_length=20, default='AES')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "SNMP Configuration"
