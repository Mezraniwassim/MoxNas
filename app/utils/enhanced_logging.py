"""Enhanced logging utilities with structured logging and correlation IDs"""
import logging
import json
import uuid
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, Union
from contextlib import contextmanager
from functools import wraps
from flask import request, g, current_app, has_request_context


class CorrelationContext:
    """Thread-local context for correlation IDs and request metadata"""
    
    def __init__(self):
        self._local = threading.local()
    
    @property
    def correlation_id(self) -> Optional[str]:
        return getattr(self._local, 'correlation_id', None)
    
    @correlation_id.setter
    def correlation_id(self, value: str):
        self._local.correlation_id = value
    
    @property
    def user_id(self) -> Optional[int]:
        return getattr(self._local, 'user_id', None)
    
    @user_id.setter
    def user_id(self, value: int):
        self._local.user_id = value
    
    @property
    def ip_address(self) -> Optional[str]:
        return getattr(self._local, 'ip_address', None)
    
    @ip_address.setter
    def ip_address(self, value: str):
        self._local.ip_address = value
    
    @property
    def operation(self) -> Optional[str]:
        return getattr(self._local, 'operation', None)
    
    @operation.setter
    def operation(self, value: str):
        self._local.operation = value
    
    def clear(self):
        """Clear all context data"""
        for attr in ['correlation_id', 'user_id', 'ip_address', 'operation']:
            if hasattr(self._local, attr):
                delattr(self._local, attr)


# Global correlation context
correlation_context = CorrelationContext()


class StructuredLogFilter(logging.Filter):
    """Filter to add structured data to log records"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add correlation ID
        record.correlation_id = correlation_context.correlation_id or 'unknown'
        
        # Add user context
        record.user_id = correlation_context.user_id
        record.ip_address = correlation_context.ip_address
        record.operation = correlation_context.operation
        
        # Add Flask request context if available
        if has_request_context():
            record.request_method = request.method
            record.request_url = request.url
            record.request_endpoint = request.endpoint
            record.user_agent = request.headers.get('User-Agent', 'Unknown')
        
        return True


class PerformanceLogFilter(logging.Filter):
    """Filter to add performance metrics to log records"""
    
    def __init__(self):
        super().__init__()
        self.start_times = threading.local()
    
    def start_operation(self, operation_name: str):
        """Start tracking an operation"""
        if not hasattr(self.start_times, 'operations'):
            self.start_times.operations = {}
        self.start_times.operations[operation_name] = time.time()
    
    def end_operation(self, operation_name: str) -> float:
        """End tracking an operation and return duration"""
        if (hasattr(self.start_times, 'operations') and 
            operation_name in self.start_times.operations):
            duration = time.time() - self.start_times.operations[operation_name]
            del self.start_times.operations[operation_name]
            return duration
        return 0.0
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add performance context if available
        if hasattr(record, 'operation_duration'):
            record.performance_ms = round(record.operation_duration * 1000, 2)
        
        return True


class SecurityLogFilter(logging.Filter):
    """Filter for security-related logging with data sanitization"""
    
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'key', 'credential',
        'auth', 'session', 'cookie', 'totp_secret'
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Mark security-related logs
        if hasattr(record, 'category') and record.category in ['auth', 'security']:
            record.security_event = True
            
            # Sanitize sensitive data in the message
            if hasattr(record, 'details') and isinstance(record.details, dict):
                record.details = self._sanitize_dict(record.details)
        
        return True
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask sensitive information"""
        sanitized = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.SENSITIVE_FIELDS):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            else:
                sanitized[key] = value
        return sanitized


class MoxNASLogger:
    """Enhanced logger for MoxNAS with structured logging capabilities"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.performance_filter = PerformanceLogFilter()
        
        # Add filters
        self.logger.addFilter(StructuredLogFilter())
        self.logger.addFilter(self.performance_filter)
        self.logger.addFilter(SecurityLogFilter())
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log with additional context"""
        extra = {
            'category': kwargs.pop('category', 'general'),
            'operation_type': kwargs.pop('operation_type', None),
            'resource_id': kwargs.pop('resource_id', None),
            'details': kwargs.pop('details', {}),
        }
        
        # Add performance data if available
        if 'operation_duration' in kwargs:
            extra['operation_duration'] = kwargs.pop('operation_duration')
        
        # Add any remaining kwargs to details
        if kwargs:
            extra['details'].update(kwargs)
        
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    @contextmanager
    def operation_context(self, operation_name: str, **context):
        """Context manager for tracking operations with timing"""
        correlation_context.operation = operation_name
        
        # Set additional context
        for key, value in context.items():
            setattr(correlation_context, key, value)
        
        self.performance_filter.start_operation(operation_name)
        start_time = time.time()
        
        try:
            self.info(f"Operation started: {operation_name}", 
                     category='operation', operation_type='start')
            yield
            
            duration = time.time() - start_time
            self.info(f"Operation completed: {operation_name}", 
                     category='operation', operation_type='complete',
                     operation_duration=duration)
        
        except Exception as e:
            duration = time.time() - start_time
            self.error(f"Operation failed: {operation_name} - {str(e)}", 
                      category='operation', operation_type='error',
                      operation_duration=duration,
                      error_type=type(e).__name__)
            raise
        
        finally:
            self.performance_filter.end_operation(operation_name)
    
    def audit_log(self, action: str, resource_type: str, resource_id: Union[str, int], 
                  outcome: str = 'success', **details):
        """Log security/audit events"""
        self.info(
            f"Audit: {action} {resource_type} {resource_id} - {outcome}",
            category='audit',
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            details=details
        )
    
    def security_event(self, event_type: str, severity: str, description: str, **details):
        """Log security events with appropriate severity"""
        level_map = {
            'low': logging.INFO,
            'medium': logging.WARNING,
            'high': logging.ERROR,
            'critical': logging.CRITICAL
        }
        
        level = level_map.get(severity.lower(), logging.WARNING)
        
        self._log_with_context(
            level,
            f"Security Event [{event_type}]: {description}",
            category='security',
            event_type=event_type,
            severity=severity,
            details=details
        )


def get_logger(name: str) -> MoxNASLogger:
    """Get a MoxNAS logger instance"""
    return MoxNASLogger(name)


def setup_correlation_id():
    """Setup correlation ID for the current request"""
    if has_request_context():
        # Try to get correlation ID from header
        header_name = current_app.config.get('LOG_REQUEST_ID_HEADER', 'X-Request-ID')
        correlation_id = request.headers.get(header_name)
        
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        correlation_context.correlation_id = correlation_id
        g.correlation_id = correlation_id
        
        # Set user context if available
        from flask_login import current_user
        if hasattr(current_user, 'id') and current_user.is_authenticated:
            correlation_context.user_id = current_user.id
        
        # Set IP address
        correlation_context.ip_address = request.remote_addr
        
        return correlation_id
    
    return None


def log_operation(operation_name: str, category: str = 'general'):
    """Decorator to automatically log function operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            
            with logger.operation_context(f"{func.__name__}:{operation_name}", 
                                        category=category):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def log_performance(threshold_ms: float = 1000):
    """Decorator to log slow operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if duration * 1000 > threshold_ms:
                    logger.warning(
                        f"Slow operation detected: {func.__name__} took {duration*1000:.2f}ms",
                        category='performance',
                        function=func.__name__,
                        operation_duration=duration,
                        threshold_ms=threshold_ms
                    )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Operation failed: {func.__name__} after {duration*1000:.2f}ms - {str(e)}",
                    category='performance',
                    function=func.__name__,
                    operation_duration=duration,
                    error_type=type(e).__name__
                )
                raise
        
        return wrapper
    return decorator