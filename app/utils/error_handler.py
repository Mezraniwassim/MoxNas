"""
Centralized error handling utilities for MoxNAS
Provides secure error handling that prevents information disclosure
"""
from __future__ import annotations
from typing import Dict, Any, Optional, Tuple, Union, Callable, List
import logging
import traceback
from functools import wraps
from flask import jsonify, request, current_app, Response
from werkzeug.exceptions import HTTPException
from app.models import SystemLog, LogLevel
from app import db


class SecureErrorHandler:
    """Secure error handling with information disclosure prevention"""

    # Generic error messages to prevent information disclosure
    GENERIC_MESSAGES: Dict[int, str] = {
        400: "Invalid request parameters",
        401: "Authentication required",
        403: "Access denied",
        404: "Resource not found",
        405: "Method not allowed",
        429: "Too many requests",
        500: "Internal server error",
        503: "Service temporarily unavailable",
    }

    @staticmethod
    def handle_error(error: Exception, user_id: Optional[int] = None) -> Tuple[Response, int]:
        """Handle errors securely with proper logging"""
        error_id = SecureErrorHandler._generate_error_id()

        # Log detailed error information for administrators
        SecureErrorHandler._log_error_details(error, error_id, user_id)

        # Return sanitized error response
        if isinstance(error, HTTPException):
            status_code = error.code
            message = SecureErrorHandler.GENERIC_MESSAGES.get(status_code, "An error occurred")
        else:
            status_code = 500
            message = SecureErrorHandler.GENERIC_MESSAGES[500]

        response_data = {
            "error": True,
            "message": message,
            "error_id": error_id,
            "status_code": status_code,
        }

        # Add specific error details only in development mode
        if current_app.debug and not current_app.testing:
            response_data["debug_message"] = str(error)

        return jsonify(response_data), status_code

    @staticmethod
    def _generate_error_id() -> str:
        """Generate unique error ID for tracking"""
        import secrets

        return secrets.token_hex(8)

    @staticmethod
    def _log_error_details(error: Exception, error_id: str, user_id: Optional[int] = None) -> None:
        """Log detailed error information securely"""
        try:
            error_details = {
                "error_id": error_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "request_method": getattr(request, "method", "Unknown"),
                "request_path": getattr(request, "path", "Unknown"),
                "user_agent": request.headers.get("User-Agent", "Unknown")
                if request
                else "Unknown",
                "traceback": traceback.format_exc() if current_app.debug else None,
            }

            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="error_handler",
                message=f"Application error occurred: {error_id}",
                user_id=user_id,
                ip_address=getattr(request, "remote_addr", None) if request else None,
                details=error_details,
            )

        except Exception as log_error:
            # Fallback logging if database is unavailable
            logging.error(f"Failed to log error to database: {log_error}")
            logging.error(f"Original error: {error}")


def secure_route(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for secure route handling with error management"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            # Get current user ID if available
            user_id = None
            try:
                from flask_login import current_user

                if hasattr(current_user, "id"):
                    user_id = current_user.id
            except:
                pass

            return SecureErrorHandler.handle_error(e, user_id)

    return decorated_function


def validate_input(**validators: Callable[[Any], bool]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for input validation with secure error handling"""

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            from app.security.hardening import InputSanitizer

            # Validate request data
            errors: List[str] = []

            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()

            for field, validator_func in validators.items():
                if field in data:
                    try:
                        if not validator_func(data[field]):
                            errors.append(f"Invalid {field} format")
                    except Exception:
                        errors.append(f"Validation error for {field}")

            if errors:
                return (
                    jsonify({"error": True, "message": "Validation failed", "details": errors}),
                    400,
                )

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def log_sensitive_operation(operation_type: str, resource_type: Optional[str] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for logging sensitive operations"""

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # Get current user ID
            user_id: Optional[int] = None
            try:
                from flask_login import current_user

                if hasattr(current_user, "id"):
                    user_id = current_user.id
            except:
                pass

            # Log operation attempt
            operation_details: Dict[str, Any] = {
                "operation": operation_type,
                "resource_type": resource_type,
                "function": f.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
            }

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="sensitive_operation",
                message=f"Sensitive operation attempted: {operation_type}",
                user_id=user_id,
                ip_address=getattr(request, "remote_addr", None) if request else None,
                details=operation_details,
            )

            try:
                result = f(*args, **kwargs)

                # Log successful operation
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="sensitive_operation",
                    message=f"Sensitive operation completed: {operation_type}",
                    user_id=user_id,
                    ip_address=getattr(request, "remote_addr", None) if request else None,
                )

                return result

            except Exception as e:
                # Log failed operation
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="sensitive_operation",
                    message=f"Sensitive operation failed: {operation_type}",
                    user_id=user_id,
                    ip_address=getattr(request, "remote_addr", None) if request else None,
                    details={"error": str(e)},
                )
                raise

        return decorated_function

    return decorator


class DatabaseErrorHandler:
    """Specialized error handling for database operations"""

    @staticmethod
    def safe_commit() -> Tuple[bool, Optional[str]]:
        """Safely commit database changes with error handling"""
        try:
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            error_msg = "Database operation failed"

            # Log database error
            logging.error(f"Database commit failed: {e}")

            return False, error_msg

    @staticmethod
    def safe_delete(model_instance: Any) -> Tuple[bool, Optional[str]]:
        """Safely delete model instance with error handling"""
        try:
            db.session.delete(model_instance)
            success, error = DatabaseErrorHandler.safe_commit()
            return success, error
        except Exception as e:
            db.session.rollback()
            logging.error(f"Database delete failed: {e}")
            return False, "Delete operation failed"

    @staticmethod
    def safe_create(model_instance: Any) -> Tuple[bool, Optional[str]]:
        """Safely create model instance with error handling"""
        try:
            db.session.add(model_instance)
            success, error = DatabaseErrorHandler.safe_commit()
            return success, error
        except Exception as e:
            db.session.rollback()
            logging.error(f"Database create failed: {e}")
            return False, "Create operation failed"


def handle_file_operation_errors(f: Callable[..., Any]) -> Callable[..., Tuple[bool, str]]:
    """Decorator for secure file operation error handling"""

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Tuple[bool, str]:
        try:
            return f(*args, **kwargs)
        except PermissionError:
            return False, "Insufficient permissions for file operation"
        except FileNotFoundError:
            return False, "File or directory not found"
        except OSError as e:
            logging.error(f"File operation error: {e}")
            return False, "File system error occurred"
        except Exception as e:
            logging.error(f"Unexpected file operation error: {e}")
            return False, "File operation failed"

    return decorated_function
