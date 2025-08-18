"""
Advanced logging configuration for MoxNAS
Provides structured logging, error tracking, and monitoring integration
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from django.conf import settings


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record):
        # Add custom fields to log record
        record.service = 'moxnas'
        record.component = getattr(record, 'component', record.module)
        
        # Create structured message
        if hasattr(record, 'extra_data'):
            extra = record.extra_data
        else:
            extra = {}
        
        # Base structured format
        structured_msg = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'service': record.service,
            'component': record.component,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra data if present
        if extra:
            structured_msg['extra'] = extra
        
        # Add exception info if present
        if record.exc_info:
            structured_msg['exception'] = self.formatException(record.exc_info)
        
        return str(structured_msg)


class MoxNASFilter(logging.Filter):
    """Custom filter to add MoxNAS-specific context"""
    
    def filter(self, record):
        # Add hostname
        record.hostname = os.uname().nodename
        
        # Add process info
        record.pid = os.getpid()
        
        # Mark as MoxNAS log
        record.is_moxnas = True
        
        return True


class ErrorNotificationHandler(logging.Handler):
    """Custom handler for critical error notifications"""
    
    def __init__(self):
        super().__init__()
        self.setLevel(logging.ERROR)
    
    def emit(self, record):
        """Send error notifications for critical issues"""
        try:
            if record.levelno >= logging.ERROR:
                self._send_notification(record)
        except Exception:
            # Don't let notification failures break logging
            pass
    
    def _send_notification(self, record):
        """Send error notification via configured channels"""
        error_msg = self.format(record)
        
        # Email notification (if configured)
        try:
            from django.core.mail import mail_admins
            mail_admins(
                subject=f'MoxNAS Error: {record.levelname}',
                message=error_msg,
                fail_silently=True
            )
        except Exception:
            pass
        
        # Log to system journal
        try:
            import subprocess
            subprocess.run([
                'logger',
                '-t', 'moxnas-error',
                '-p', 'daemon.err',
                error_msg
            ], check=False)
        except Exception:
            pass


def setup_logging():
    """Configure comprehensive logging for MoxNAS"""
    
    # Create log directory
    log_dir = Path('/var/log/moxnas')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler for development/container logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(MoxNASFilter())
    
    # File handler for application logs
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / 'moxnas.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = StructuredFormatter()
    file_handler.setFormatter(file_formatter)
    file_handler.addFilter(MoxNASFilter())
    
    # Error file handler for errors only
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / 'error.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    error_handler.addFilter(MoxNASFilter())
    
    # Security log handler
    security_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / 'security.log',
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=10,
        encoding='utf-8'
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(file_formatter)
    
    # Audit log handler (for service changes)
    audit_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / 'audit.log',
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=20,
        encoding='utf-8'
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(file_formatter)
    
    # Critical error notification handler
    notification_handler = ErrorNotificationHandler()
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(notification_handler)
    
    # Configure specific loggers
    
    # Django loggers
    django_logger = logging.getLogger('django')
    django_logger.setLevel(logging.INFO)
    django_logger.addHandler(file_handler)
    
    # Django security logger
    security_logger = logging.getLogger('django.security')
    security_logger.setLevel(logging.WARNING)
    security_logger.addHandler(security_handler)
    security_logger.addHandler(notification_handler)
    
    # MoxNAS application logger
    moxnas_logger = logging.getLogger('moxnas')
    moxnas_logger.setLevel(logging.DEBUG)
    moxnas_logger.addHandler(file_handler)
    
    # Services logger (for service management)
    services_logger = logging.getLogger('apps.services')
    services_logger.setLevel(logging.INFO)
    services_logger.addHandler(audit_handler)
    
    # Storage logger (for storage operations)
    storage_logger = logging.getLogger('apps.storage')
    storage_logger.setLevel(logging.INFO)
    storage_logger.addHandler(audit_handler)
    
    # System logger (for system operations)
    system_logger = logging.getLogger('apps.system')
    system_logger.setLevel(logging.INFO)
    system_logger.addHandler(audit_handler)
    
    return root_logger


def log_security_event(event_type, details, user=None, ip_address=None):
    """Log security-related events"""
    security_logger = logging.getLogger('django.security')
    
    log_data = {
        'event_type': event_type,
        'details': details,
        'user': str(user) if user else None,
        'ip_address': ip_address,
    }
    
    security_logger.warning(
        f'Security event: {event_type}',
        extra={'extra_data': log_data}
    )


def log_audit_event(action, resource, user=None, changes=None):
    """Log audit events for compliance and tracking"""
    audit_logger = logging.getLogger('moxnas.audit')
    
    log_data = {
        'action': action,
        'resource': resource,
        'user': str(user) if user else None,
        'changes': changes,
    }
    
    audit_logger.info(
        f'Audit: {action} on {resource}',
        extra={'extra_data': log_data}
    )


def log_service_event(service, action, result, details=None):
    """Log service management events"""
    services_logger = logging.getLogger('apps.services')
    
    log_data = {
        'service': service,
        'action': action,
        'result': result,
        'details': details or {},
    }
    
    level = logging.INFO if result == 'success' else logging.WARNING
    services_logger.log(
        level,
        f'Service {action}: {service} - {result}',
        extra={'extra_data': log_data}
    )


# Custom log levels
AUDIT_LEVEL = 25
logging.addLevelName(AUDIT_LEVEL, 'AUDIT')

def audit(self, message, *args, **kwargs):
    if self.isEnabledFor(AUDIT_LEVEL):
        self._log(AUDIT_LEVEL, message, args, **kwargs)

logging.Logger.audit = audit