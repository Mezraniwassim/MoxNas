from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ServiceConfig(models.Model):
    """Configuration for various NAS services"""
    SERVICE_CHOICES = [
        ('smb', 'SMB/CIFS'),
        ('nfs', 'NFS'),
        ('ftp', 'FTP'),
        ('ssh', 'SSH'),
        ('snmp', 'SNMP'),
        ('iscsi', 'iSCSI'),
    ]
    
    name = models.CharField(max_length=50, choices=SERVICE_CHOICES, unique=True)
    enabled = models.BooleanField(default=False)
    port = models.IntegerField()
    config_data = models.JSONField(default=dict, blank=True)
    auto_start = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.get_name_display()} ({'Enabled' if self.enabled else 'Disabled'})"

class CloudSyncTask(models.Model):
    """Cloud synchronization tasks"""
    PROVIDER_CHOICES = [
        ('aws_s3', 'Amazon S3'),
        ('azure_blob', 'Azure Blob Storage'),
        ('google_drive', 'Google Drive'),
        ('dropbox', 'Dropbox'),
        ('backblaze_b2', 'Backblaze B2'),
        ('ftp', 'FTP Server'),
        ('sftp', 'SFTP Server'),
    ]
    
    DIRECTION_CHOICES = [
        ('push', 'Push to Cloud'),
        ('pull', 'Pull from Cloud'),
        ('sync', 'Bidirectional Sync'),
    ]
    
    SCHEDULE_CHOICES = [
        ('hourly', 'Every Hour'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('manual', 'Manual Only'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    local_path = models.CharField(max_length=512)
    remote_path = models.CharField(max_length=512)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    schedule = models.CharField(max_length=20, choices=SCHEDULE_CHOICES)
    enabled = models.BooleanField(default=True)
    credentials = models.JSONField(default=dict, blank=True)  # Encrypted in production
    exclude_patterns = models.TextField(blank=True, help_text="One pattern per line")
    compression = models.BooleanField(default=False)
    encryption = models.BooleanField(default=False)
    last_run = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=50, default='never_run')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_display()})"
    
    class Meta:
        ordering = ['-created_at']

class RsyncTask(models.Model):
    """Rsync synchronization tasks"""
    DIRECTION_CHOICES = [
        ('push', 'Push to Remote'),
        ('pull', 'Pull from Remote'),
    ]
    
    SCHEDULE_CHOICES = [
        ('hourly', 'Every Hour'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('manual', 'Manual Only'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    source_path = models.CharField(max_length=512)
    destination_path = models.CharField(max_length=512)
    remote_host = models.CharField(max_length=255, blank=True)
    remote_user = models.CharField(max_length=100, blank=True)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    schedule = models.CharField(max_length=20, choices=SCHEDULE_CHOICES)
    enabled = models.BooleanField(default=True)
    preserve_permissions = models.BooleanField(default=True)
    preserve_timestamps = models.BooleanField(default=True)
    compress = models.BooleanField(default=False)
    delete_destination = models.BooleanField(default=False)
    exclude_patterns = models.TextField(blank=True, help_text="One pattern per line")
    rsync_options = models.CharField(max_length=255, blank=True, help_text="Additional rsync options")
    last_run = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=50, default='never_run')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.source_path} -> {self.destination_path})"
    
    class Meta:
        ordering = ['-created_at']

class TaskLog(models.Model):
    """Logs for sync tasks"""
    TASK_TYPE_CHOICES = [
        ('cloud_sync', 'Cloud Sync'),
        ('rsync', 'Rsync'),
    ]
    
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    task_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    log_output = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    files_transferred = models.IntegerField(default=0)
    bytes_transferred = models.BigIntegerField(default=0)
    
    def __str__(self):
        return f"{self.get_task_type_display()} #{self.task_id} - {self.status}"
    
    class Meta:
        ordering = ['-started_at']

class UPSConfig(models.Model):
    """UPS (Uninterruptible Power Supply) configuration"""
    UPS_TYPE_CHOICES = [
        ('usb', 'USB'),
        ('serial', 'Serial'),
        ('network', 'Network'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    ups_type = models.CharField(max_length=20, choices=UPS_TYPE_CHOICES)
    device_path = models.CharField(max_length=255, blank=True, help_text="For USB/Serial UPS")
    network_host = models.CharField(max_length=255, blank=True, help_text="For Network UPS")
    network_port = models.IntegerField(default=3493, blank=True)
    driver = models.CharField(max_length=100, default='usbhid-ups')
    enabled = models.BooleanField(default=False)
    shutdown_command = models.CharField(max_length=255, default='shutdown -h now')
    low_battery_runtime = models.IntegerField(default=300, help_text="Seconds before shutdown")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_ups_type_display()})"