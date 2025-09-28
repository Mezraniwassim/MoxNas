"""Enhanced error handling utilities with retry logic, circuit breakers, and graceful degradation"""
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Union, List, Type
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import logging
from flask import current_app

from app.utils.enhanced_logging import get_logger


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    DATABASE = "database"
    STORAGE = "storage"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for errors"""
    operation: str
    category: ErrorCategory
    severity: ErrorSeverity
    user_id: Optional[int] = None
    ip_address: Optional[str] = None
    resource_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MoxNASError(Exception):
    """Base exception class for MoxNAS with enhanced error handling"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recoverable: bool = True,
        retry_after: Optional[int] = None,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.retry_after = retry_after
        self.context = context
        self.original_exception = original_exception
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for API responses"""
        return {
            'error': {
                'message': self.message,
                'category': self.category.value,
                'severity': self.severity.value,
                'recoverable': self.recoverable,
                'retry_after': self.retry_after,
                'timestamp': self.timestamp.isoformat(),
                'context': {
                    'operation': self.context.operation if self.context else None,
                    'resource_id': self.context.resource_id if self.context else None,
                } if self.context else None
            }
        }


class StorageError(MoxNASError):
    """Storage-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.STORAGE, **kwargs)


class DatabaseError(MoxNASError):
    """Database-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.DATABASE, **kwargs)


class NetworkError(MoxNASError):
    """Network-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)


class AuthenticationError(MoxNASError):
    """Authentication-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.AUTHENTICATION, **kwargs)


class ValidationError(MoxNASError):
    """Validation-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION, severity=ErrorSeverity.LOW, **kwargs)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics"""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    next_retry_time: Optional[datetime] = None


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 10,
        timeout_seconds: int = 60,
        recovery_threshold: int = 3
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.recovery_threshold = recovery_threshold
        self.stats = CircuitBreakerStats()
        self._lock = threading.RLock()
        self.logger = get_logger(f"circuit_breaker.{name}")
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        with self._lock:
            if self._should_reject_request():
                raise MoxNASError(
                    f"Circuit breaker '{self.name}' is OPEN",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.HIGH,
                    recoverable=True,
                    retry_after=self.timeout_seconds
                )
            
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            
            except Exception as e:
                self._record_failure()
                raise
    
    def _should_reject_request(self) -> bool:
        """Determine if request should be rejected"""
        now = datetime.utcnow()
        
        if self.stats.state == CircuitBreakerState.CLOSED:
            return False
        
        elif self.stats.state == CircuitBreakerState.OPEN:
            if (self.stats.next_retry_time and 
                now >= self.stats.next_retry_time):
                self.stats.state = CircuitBreakerState.HALF_OPEN
                self.logger.info(f"Circuit breaker '{self.name}' moved to HALF_OPEN")
                return False
            return True
        
        elif self.stats.state == CircuitBreakerState.HALF_OPEN:
            return False
        
        return False
    
    def _record_success(self):
        """Record successful operation"""
        with self._lock:
            self.stats.success_count += 1
            
            if self.stats.state == CircuitBreakerState.HALF_OPEN:
                if self.stats.success_count >= self.recovery_threshold:
                    self.stats.state = CircuitBreakerState.CLOSED
                    self.stats.failure_count = 0
                    self.stats.success_count = 0
                    self.logger.info(f"Circuit breaker '{self.name}' moved to CLOSED")
    
    def _record_failure(self):
        """Record failed operation"""
        with self._lock:
            self.stats.failure_count += 1
            self.stats.last_failure_time = datetime.utcnow()
            
            if (self.stats.state == CircuitBreakerState.CLOSED and 
                self.stats.failure_count >= self.failure_threshold):
                self.stats.state = CircuitBreakerState.OPEN
                self.stats.next_retry_time = (
                    datetime.utcnow() + timedelta(seconds=self.timeout_seconds)
                )
                self.logger.warning(f"Circuit breaker '{self.name}' moved to OPEN")
            
            elif self.stats.state == CircuitBreakerState.HALF_OPEN:
                self.stats.state = CircuitBreakerState.OPEN
                self.stats.next_retry_time = (
                    datetime.utcnow() + timedelta(seconds=self.timeout_seconds)
                )
                self.logger.warning(f"Circuit breaker '{self.name}' moved back to OPEN")


class RetryPolicy:
    """Retry policy configuration"""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        retryable_exceptions: List[Type[Exception]] = None
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError, TimeoutError, OSError, StorageError, NetworkError
        ]
    
    def is_retryable(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        if isinstance(exception, MoxNASError):
            return exception.recoverable
        
        return any(isinstance(exception, exc_type) 
                  for exc_type in self.retryable_exceptions)
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


class ErrorRecoveryManager:
    """Manages error recovery strategies"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = get_logger("error_recovery")
        self._lock = threading.RLock()
    
    def get_circuit_breaker(self, name: str, **kwargs) -> CircuitBreaker:
        """Get or create circuit breaker"""
        with self._lock:
            if name not in self.circuit_breakers:
                # Use config values if available
                config_values = {}
                if current_app:
                    config_values = {
                        'failure_threshold': current_app.config.get('ERROR_CIRCUIT_BREAKER_THRESHOLD', 10),
                        'timeout_seconds': current_app.config.get('ERROR_CIRCUIT_BREAKER_TIMEOUT', 60)
                    }
                config_values.update(kwargs)
                
                self.circuit_breakers[name] = CircuitBreaker(name, **config_values)
            
            return self.circuit_breakers[name]
    
    def with_retry(
        self,
        func: Callable,
        retry_policy: Optional[RetryPolicy] = None,
        context: Optional[ErrorContext] = None
    ):
        """Execute function with retry logic"""
        if retry_policy is None:
            retry_policy = RetryPolicy()
        
        last_exception = None
        
        for attempt in range(1, retry_policy.max_attempts + 1):
            try:
                return func()
            
            except Exception as e:
                last_exception = e
                
                if not retry_policy.is_retryable(e):
                    self.logger.error(
                        f"Non-retryable error on attempt {attempt}: {str(e)}",
                        category='error_recovery',
                        operation=context.operation if context else 'unknown',
                        attempt=attempt,
                        error_type=type(e).__name__
                    )
                    raise
                
                if attempt == retry_policy.max_attempts:
                    self.logger.error(
                        f"Max retry attempts ({retry_policy.max_attempts}) exceeded: {str(e)}",
                        category='error_recovery',
                        operation=context.operation if context else 'unknown',
                        final_attempt=attempt,
                        error_type=type(e).__name__
                    )
                    break
                
                delay = retry_policy.get_delay(attempt)
                self.logger.warning(
                    f"Retryable error on attempt {attempt}, retrying in {delay:.2f}s: {str(e)}",
                    category='error_recovery',
                    operation=context.operation if context else 'unknown',
                    attempt=attempt,
                    delay=delay,
                    error_type=type(e).__name__
                )
                
                time.sleep(delay)
        
        # If we get here, all retry attempts failed
        if isinstance(last_exception, MoxNASError):
            raise last_exception
        else:
            raise MoxNASError(
                f"Operation failed after {retry_policy.max_attempts} attempts: {str(last_exception)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                original_exception=last_exception,
                context=context
            )
    
    def with_circuit_breaker(
        self,
        name: str,
        func: Callable,
        *args,
        **kwargs
    ):
        """Execute function with circuit breaker protection"""
        circuit_breaker = self.get_circuit_breaker(name)
        return circuit_breaker.call(func, *args, **kwargs)


# Global error recovery manager
error_recovery = ErrorRecoveryManager()


def with_error_handling(
    operation: str,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    retry_policy: Optional[RetryPolicy] = None,
    circuit_breaker_name: Optional[str] = None,
    fallback_func: Optional[Callable] = None
):
    """Decorator for comprehensive error handling"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            context = ErrorContext(
                operation=f"{func.__name__}:{operation}",
                category=category,
                severity=ErrorSeverity.MEDIUM
            )
            
            def execute_function():
                if circuit_breaker_name:
                    return error_recovery.with_circuit_breaker(
                        circuit_breaker_name, func, *args, **kwargs
                    )
                else:
                    return func(*args, **kwargs)
            
            try:
                if retry_policy:
                    return error_recovery.with_retry(execute_function, retry_policy, context)
                else:
                    return execute_function()
            
            except Exception as e:
                # Log the error
                logger.error(
                    f"Operation failed: {operation} - {str(e)}",
                    category=category.value,
                    operation=operation,
                    error_type=type(e).__name__,
                    context=context.additional_data
                )
                
                # Try fallback if available
                if fallback_func:
                    try:
                        logger.info(f"Attempting fallback for operation: {operation}")
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback also failed: {str(fallback_error)}")
                
                # Re-raise the original error
                raise
        
        return wrapper
    return decorator


@contextmanager
def error_context(
    operation: str,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    **additional_data
):
    """Context manager for error handling with enhanced context"""
    logger = get_logger("error_context")
    context = ErrorContext(
        operation=operation,
        category=category,
        severity=severity,
        additional_data=additional_data
    )
    
    try:
        yield context
    except Exception as e:
        # Enhance the exception with context if it's not already a MoxNASError
        if not isinstance(e, MoxNASError):
            enhanced_error = MoxNASError(
                str(e),
                category=category,
                severity=severity,
                context=context,
                original_exception=e
            )
            raise enhanced_error from e
        else:
            # Add context to existing MoxNASError
            e.context = context
            raise


def graceful_degradation(
    primary_func: Callable,
    fallback_func: Callable,
    condition_func: Optional[Callable] = None,
    timeout_seconds: Optional[float] = None
):
    """Implement graceful degradation pattern"""
    logger = get_logger("graceful_degradation")
    
    # Check if we should use fallback due to system condition
    if condition_func and not condition_func():
        logger.info("Using fallback due to system condition")
        return fallback_func()
    
    try:
        if timeout_seconds:
            # Implement timeout logic here if needed
            pass
        
        return primary_func()
    
    except Exception as e:
        logger.warning(f"Primary function failed, using fallback: {str(e)}")
        try:
            return fallback_func()
        except Exception as fallback_error:
            logger.error(f"Fallback also failed: {str(fallback_error)}")
            raise MoxNASError(
                "Both primary and fallback operations failed",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                original_exception=e
            ) from fallback_error


def handle_database_errors(func):
    """Decorator specifically for database error handling"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError as SQLTimeoutError
            
            if isinstance(e, IntegrityError):
                raise DatabaseError(
                    "Data integrity constraint violation",
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=False,
                    original_exception=e
                )
            elif isinstance(e, (OperationalError, SQLTimeoutError)):
                raise DatabaseError(
                    "Database operation failed or timed out",
                    severity=ErrorSeverity.HIGH,
                    recoverable=True,
                    original_exception=e
                )
            else:
                raise DatabaseError(
                    f"Database error: {str(e)}",
                    severity=ErrorSeverity.HIGH,
                    original_exception=e
                )
    
    return wrapper