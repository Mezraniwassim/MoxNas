"""Celery Beat Scheduler Configuration for MoxNAS"""
from celery import Celery
from celery.schedules import crontab
import os

# Create Celery app
celery = Celery('moxnas-beat')

# Load configuration
celery.config_from_object('app.config.CeleryConfig')

# Beat Schedule Configuration
beat_schedule = {
    # Device health monitoring - every 10 minutes
    'device-health-check': {
        'task': 'app.tasks.device_health_check',
        'schedule': crontab(minute='*/10'),
        'options': {'queue': 'health_checks'}
    },
    
    # SMART data update - every hour
    'smart-data-update': {
        'task': 'app.tasks.update_smart_data',
        'schedule': crontab(minute=0),
        'options': {'queue': 'monitoring'}
    },
    
    # System metrics collection - every 5 minutes
    'system-metrics-collection': {
        'task': 'app.tasks.collect_system_metrics',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'monitoring'}
    },
    
    # Storage pool scrub scheduling - daily at 2 AM
    'pool-scrub-check': {
        'task': 'app.tasks.check_scheduled_scrubs',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'storage'}
    },
    
    # Backup job scheduling - every minute to check for due jobs
    'backup-job-scheduler': {
        'task': 'app.tasks.schedule_backup_jobs',
        'schedule': crontab(minute='*'),
        'options': {'queue': 'backups'}
    },
    
    # Clean up old alerts - daily at 3 AM
    'cleanup-old-alerts': {
        'task': 'app.tasks.cleanup_old_alerts',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'maintenance'}
    },
    
    # Clean up old system metrics - daily at 3:30 AM
    'cleanup-old-metrics': {
        'task': 'app.tasks.cleanup_old_metrics',
        'schedule': crontab(hour=3, minute=30),
        'options': {'queue': 'maintenance'}
    },
    
    # Update network share connection counts - every 2 minutes
    'update-share-connections': {
        'task': 'app.tasks.update_share_connections',
        'schedule': crontab(minute='*/2'),
        'options': {'queue': 'monitoring'}
    },
    
    # Check for failed backup jobs - every 30 minutes
    'check-failed-backups': {
        'task': 'app.tasks.check_failed_backup_jobs',
        'schedule': crontab(minute='*/30'),
        'options': {'queue': 'backups'}
    },
    
    # Generate daily system report - daily at 6 AM
    'daily-system-report': {
        'task': 'app.tasks.generate_daily_report',
        'schedule': crontab(hour=6, minute=0),
        'options': {'queue': 'reports'}
    },
    
    # Security audit log cleanup - weekly on Sunday at 4 AM
    'cleanup-audit-logs': {
        'task': 'app.tasks.cleanup_audit_logs',
        'schedule': crontab(hour=4, minute=0, day_of_week=0),
        'options': {'queue': 'maintenance'}
    },
    
    # Certificate expiration check - daily at 8 AM
    'check-certificate-expiry': {
        'task': 'app.tasks.check_certificate_expiry',
        'schedule': crontab(hour=8, minute=0),
        'options': {'queue': 'security'}
    },
    
    # Database maintenance - weekly on Saturday at 1 AM
    'database-maintenance': {
        'task': 'app.tasks.database_maintenance',
        'schedule': crontab(hour=1, minute=0, day_of_week=6),
        'options': {'queue': 'maintenance'}
    },
    
    # Update external IP and network configuration - every hour
    'update-network-config': {
        'task': 'app.tasks.update_network_configuration',
        'schedule': crontab(minute=0),
        'options': {'queue': 'networking'}
    },
    
    # Check disk space and send alerts if low - every 15 minutes
    'disk-space-monitoring': {
        'task': 'app.tasks.monitor_disk_space',
        'schedule': crontab(minute='*/15'),
        'options': {'queue': 'monitoring'}
    },
    
    # Temperature monitoring for critical components - every 5 minutes
    'temperature-monitoring': {
        'task': 'app.tasks.monitor_temperatures',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'health_checks'}
    },
    
    # Service health monitoring - every 2 minutes
    'service-health-check': {
        'task': 'app.tasks.check_service_health',
        'schedule': crontab(minute='*/2'),
        'options': {'queue': 'health_checks'}
    },
    
    # User session cleanup - every hour
    'cleanup-expired-sessions': {
        'task': 'app.tasks.cleanup_expired_sessions',
        'schedule': crontab(minute=0),
        'options': {'queue': 'maintenance'}
    },
    
    # Update system package information - daily at 5 AM
    'update-package-info': {
        'task': 'app.tasks.update_system_packages',
        'schedule': crontab(hour=5, minute=0),
        'options': {'queue': 'system'}
    },
    
    # Generate storage usage trends - weekly on Monday at 7 AM
    'storage-usage-trends': {
        'task': 'app.tasks.generate_storage_trends',
        'schedule': crontab(hour=7, minute=0, day_of_week=1),
        'options': {'queue': 'reports'}
    }
}

# Apply beat schedule
celery.conf.beat_schedule = beat_schedule

# Timezone configuration
celery.conf.timezone = os.environ.get('TZ', 'UTC')

# Task routing configuration
celery.conf.task_routes = {
    'app.tasks.device_health_check': {'queue': 'health_checks'},
    'app.tasks.update_smart_data': {'queue': 'monitoring'},
    'app.tasks.collect_system_metrics': {'queue': 'monitoring'},
    'app.tasks.check_scheduled_scrubs': {'queue': 'storage'},
    'app.tasks.schedule_backup_jobs': {'queue': 'backups'},
    'app.tasks.run_backup_job': {'queue': 'backups'},
    'app.tasks.cleanup_old_alerts': {'queue': 'maintenance'},
    'app.tasks.cleanup_old_metrics': {'queue': 'maintenance'},
    'app.tasks.update_share_connections': {'queue': 'monitoring'},
    'app.tasks.check_failed_backup_jobs': {'queue': 'backups'},
    'app.tasks.generate_daily_report': {'queue': 'reports'},
    'app.tasks.cleanup_audit_logs': {'queue': 'maintenance'},
    'app.tasks.check_certificate_expiry': {'queue': 'security'},
    'app.tasks.database_maintenance': {'queue': 'maintenance'},
    'app.tasks.update_network_configuration': {'queue': 'networking'},
    'app.tasks.monitor_disk_space': {'queue': 'monitoring'},
    'app.tasks.monitor_temperatures': {'queue': 'health_checks'},
    'app.tasks.check_service_health': {'queue': 'health_checks'},
    'app.tasks.cleanup_expired_sessions': {'queue': 'maintenance'},
    'app.tasks.update_system_packages': {'queue': 'system'},
    'app.tasks.generate_storage_trends': {'queue': 'reports'},
}

# Additional Beat configuration
celery.conf.update(
    # Beat database file location
    beat_dburi=os.environ.get('CELERY_BEAT_DATABASE', 'redis://localhost:6379/1'),
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Result backend configuration
    result_expires=3600,  # 1 hour
    result_compression='gzip',
    
    # Task execution configuration
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    task_reject_on_worker_lost=True,
    
    # Monitoring configuration
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Queue configuration with priorities
    task_default_queue='default',
    task_queue_max_priority=10,
    task_default_priority=5,
    worker_disable_rate_limits=True,
    
    # Security configuration
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    result_accept_content=['json'],
    
    # Error handling
    task_annotations={
        '*': {'rate_limit': '100/m'},  # Global rate limit
        'app.tasks.device_health_check': {'rate_limit': '6/m'},  # Once per 10 seconds max
        'app.tasks.collect_system_metrics': {'rate_limit': '12/m'},  # Once per 5 seconds max
        'app.tasks.run_backup_job': {
            'rate_limit': '2/m',  # Max 2 backup jobs per minute
            'soft_time_limit': 1800,  # 30 minutes
            'time_limit': 3600,  # 1 hour
        },
        'app.tasks.storage_pool_scrub': {
            'rate_limit': '1/h',  # Max 1 scrub per hour
            'soft_time_limit': 7200,  # 2 hours
            'time_limit': 14400,  # 4 hours
        },
    }
)

if __name__ == '__main__':
    celery.start()