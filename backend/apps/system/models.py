from django.db import models
import json

class SystemSettings(models.Model):
    """System-wide settings"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50, default='general')
    is_encrypted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'key']

    def __str__(self):
        return f"{self.category}.{self.key}"

    def get_value(self):
        """Get typed value"""
        try:
            return json.loads(self.value)
        except json.JSONDecodeError:
            return self.value

    def set_value(self, value):
        """Set typed value"""
        if isinstance(value, (dict, list, bool, int, float)):
            self.value = json.dumps(value)
        else:
            self.value = str(value)

class SystemLog(models.Model):
    """System log entries"""
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    message = models.TextField()
    component = models.CharField(max_length=50, help_text="Component that generated the log")
    details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.level} - {self.component} - {self.message[:50]}"

class BackupJob(models.Model):
    """Backup job configuration"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    source_path = models.CharField(max_length=255)
    destination_path = models.CharField(max_length=255)
    schedule = models.CharField(max_length=100, help_text="Cron expression")
    enabled = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    last_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name