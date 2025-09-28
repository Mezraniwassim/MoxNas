"""
Comprehensive input validation decorators and utilities for MoxNAS
Provides standardized validation for all user inputs across the application
"""
from functools import wraps
from flask import request, jsonify, current_app
from typing import Any, Dict, List, Callable, Optional, Union
import re
from app.security.hardening import InputSanitizer
from app.models import SystemLog, LogLevel
from app.utils.error_handler import SecureErrorHandler


class ValidationError(Exception):
    """Custom exception for validation errors"""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error in {field}: {message}")


class ValidationRule:
    """Base class for validation rules"""

    def __init__(self, field_name: str, required: bool = True, allow_empty: bool = False):
        self.field_name = field_name
        self.required = required
        self.allow_empty = allow_empty

    def validate(self, value: Any) -> bool:
        """Override in subclasses"""
        return True

    def get_error_message(self) -> str:
        """Override in subclasses"""
        return f"Invalid value for {self.field_name}"


class StringRule(ValidationRule):
    """String validation rule"""

    def __init__(
        self,
        field_name: str,
        min_length: int = 0,
        max_length: int = 255,
        pattern: Optional[str] = None,
        required: bool = True,
        allow_empty: bool = False,
    ):
        super().__init__(field_name, required, allow_empty)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False

        if len(value) < self.min_length or len(value) > self.max_length:
            return False

        if self.pattern and not self.pattern.match(value):
            return False

        return True

    def get_error_message(self) -> str:
        if self.pattern:
            return f"{self.field_name} must match the required format"
        return (
            f"{self.field_name} must be between {self.min_length} and {self.max_length} characters"
        )


class EmailRule(ValidationRule):
    """Email validation rule"""

    def validate(self, value: Any) -> bool:
        return InputSanitizer.validate_email(value)

    def get_error_message(self) -> str:
        return f"{self.field_name} must be a valid email address"


class UsernameRule(ValidationRule):
    """Username validation rule"""

    def validate(self, value: Any) -> bool:
        return InputSanitizer.validate_username(value)

    def get_error_message(self) -> str:
        return f"{self.field_name} must be 3-32 characters, containing only letters, numbers, underscore, and dash"


class PathRule(ValidationRule):
    """File path validation rule"""

    def __init__(
        self,
        field_name: str,
        required: bool = True,
        allow_empty: bool = False,
        must_exist: bool = False,
    ):
        super().__init__(field_name, required, allow_empty)
        self.must_exist = must_exist

    def validate(self, value: Any) -> bool:
        if not InputSanitizer.validate_path(value):
            return False

        if self.must_exist:
            import os

            return os.path.exists(value)

        return True

    def get_error_message(self) -> str:
        if self.must_exist:
            return f"{self.field_name} must be a valid existing path"
        return f"{self.field_name} must be a valid path"


class IPAddressRule(ValidationRule):
    """IP address validation rule"""

    def validate(self, value: Any) -> bool:
        return InputSanitizer.validate_ip_address(value)

    def get_error_message(self) -> str:
        return f"{self.field_name} must be a valid IP address"


class ChoiceRule(ValidationRule):
    """Choice validation rule - value must be in allowed choices"""

    def __init__(self, field_name: str, choices: List[Any], required: bool = True):
        super().__init__(field_name, required)
        self.choices = choices

    def validate(self, value: Any) -> bool:
        return value in self.choices

    def get_error_message(self) -> str:
        return f"{self.field_name} must be one of: {', '.join(map(str, self.choices))}"


class IntegerRule(ValidationRule):
    """Integer validation rule"""

    def __init__(
        self,
        field_name: str,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None,
        required: bool = True,
    ):
        super().__init__(field_name, required)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any) -> bool:
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return False

        if self.min_value is not None and int_value < self.min_value:
            return False

        if self.max_value is not None and int_value > self.max_value:
            return False

        return True

    def get_error_message(self) -> str:
        if self.min_value is not None and self.max_value is not None:
            return f"{self.field_name} must be an integer between {self.min_value} and {self.max_value}"
        elif self.min_value is not None:
            return f"{self.field_name} must be an integer >= {self.min_value}"
        elif self.max_value is not None:
            return f"{self.field_name} must be an integer <= {self.max_value}"
        return f"{self.field_name} must be a valid integer"


class SMBShareNameRule(ValidationRule):
    """SMB share name validation rule"""

    def validate(self, value: Any) -> bool:
        return InputSanitizer.validate_smb_share_name(value)

    def get_error_message(self) -> str:
        return f"{self.field_name} must be a valid SMB share name (1-80 characters, no forbidden names)"


class NFSHostRule(ValidationRule):
    """NFS host specification validation rule"""

    def validate(self, value: Any) -> bool:
        return InputSanitizer.validate_nfs_host(value)

    def get_error_message(self) -> str:
        return f"{self.field_name} must be a valid NFS host specification"


class PasswordRule(ValidationRule):
    """Password validation rule"""

    def __init__(
        self,
        field_name: str,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digits: bool = True,
        require_special: bool = True,
        required: bool = True,
    ):
        super().__init__(field_name, required)
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digits = require_digits
        self.require_special = require_special

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str) or len(value) < self.min_length:
            return False

        if self.require_uppercase and not re.search(r"[A-Z]", value):
            return False

        if self.require_lowercase and not re.search(r"[a-z]", value):
            return False

        if self.require_digits and not re.search(r"[0-9]", value):
            return False

        if self.require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            return False

        return True

    def get_error_message(self) -> str:
        requirements = [f"at least {self.min_length} characters"]
        if self.require_uppercase:
            requirements.append("uppercase letter")
        if self.require_lowercase:
            requirements.append("lowercase letter")
        if self.require_digits:
            requirements.append("digit")
        if self.require_special:
            requirements.append("special character")

        return f"{self.field_name} must contain " + ", ".join(requirements)


def validate_request_data(rules: Dict[str, ValidationRule], log_errors: bool = True):
    """
    Decorator for validating request data against defined rules
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get request data
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = dict(request.form)
                data.update(dict(request.args))

            errors = {}
            sanitized_data = {}

            # Validate each field against its rule
            for field_name, rule in rules.items():
                value = data.get(field_name)

                # Check if required field is missing
                if rule.required and (value is None or (value == "" and not rule.allow_empty)):
                    errors[field_name] = f"{field_name} is required"
                    continue

                # Skip validation if field is optional and not provided
                if not rule.required and value is None:
                    continue

                # Skip validation if field is empty and empty is allowed
                if rule.allow_empty and value == "":
                    sanitized_data[field_name] = value
                    continue

                # Validate the field
                if not rule.validate(value):
                    errors[field_name] = rule.get_error_message()
                else:
                    # Sanitize the value
                    if isinstance(value, str):
                        sanitized_data[field_name] = InputSanitizer.sanitize_string(value)
                    else:
                        sanitized_data[field_name] = value

            # Log validation errors if enabled
            if errors and log_errors:
                try:
                    from flask_login import current_user

                    user_id = current_user.id if hasattr(current_user, "id") else None
                except:
                    user_id = None

                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category="validation",
                    message=f"Input validation failed for {f.__name__}",
                    user_id=user_id,
                    ip_address=getattr(request, "remote_addr", None),
                    details={"errors": errors, "endpoint": request.endpoint},
                )

            # Return validation errors if any
            if errors:
                if request.is_json or request.content_type == "application/json":
                    return (
                        jsonify(
                            {
                                "error": True,
                                "message": "Validation failed",
                                "validation_errors": errors,
                            }
                        ),
                        400,
                    )
                else:
                    # For HTML forms, flash messages and redirect
                    from flask import flash, redirect, url_for

                    for field, error in errors.items():
                        flash(f"Validation error: {error}", "danger")
                    return redirect(request.url)

            # Add sanitized data to request context
            request.validated_data = sanitized_data

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def validate_json_schema(schema: Dict[str, Any]):
    """
    Decorator for validating JSON request data against a schema
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": True, "message": "Request must be JSON"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": True, "message": "Invalid JSON data"}), 400

            errors = []

            # Validate schema
            for field, field_schema in schema.items():
                if field_schema.get("required", False) and field not in data:
                    errors.append(f"Missing required field: {field}")
                    continue

                if field not in data:
                    continue

                value = data[field]
                field_type = field_schema.get("type")

                # Type validation
                if field_type == "string" and not isinstance(value, str):
                    errors.append(f"{field} must be a string")
                elif field_type == "integer" and not isinstance(value, int):
                    errors.append(f"{field} must be an integer")
                elif field_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"{field} must be a boolean")
                elif field_type == "list" and not isinstance(value, list):
                    errors.append(f"{field} must be a list")

                # Length validation
                if isinstance(value, str):
                    min_len = field_schema.get("min_length", 0)
                    max_len = field_schema.get("max_length", float("inf"))
                    if len(value) < min_len or len(value) > max_len:
                        errors.append(f"{field} length must be between {min_len} and {max_len}")

                # Choice validation
                if "choices" in field_schema and value not in field_schema["choices"]:
                    errors.append(f"{field} must be one of: {', '.join(field_schema['choices'])}")

                # Pattern validation
                if "pattern" in field_schema and isinstance(value, str):
                    if not re.match(field_schema["pattern"], value):
                        errors.append(f"{field} does not match required format")

            if errors:
                return (
                    jsonify(
                        {
                            "error": True,
                            "message": "Schema validation failed",
                            "validation_errors": errors,
                        }
                    ),
                    400,
                )

            # Add validated data to request context
            request.validated_json = data

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Pre-defined validation rule sets for common use cases
COMMON_VALIDATION_RULES = {
    "user_creation": {
        "username": UsernameRule("username"),
        "email": EmailRule("email"),
        "password": PasswordRule("password"),
        "first_name": StringRule("first_name", max_length=64, required=False, allow_empty=True),
        "last_name": StringRule("last_name", max_length=64, required=False, allow_empty=True),
    },
    "user_login": {
        "username": UsernameRule("username"),
        "password": StringRule("password", min_length=1),
    },
    "storage_pool_creation": {
        "name": StringRule("name", min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$"),
        "raid_level": ChoiceRule("raid_level", ["raid0", "raid1", "raid5", "raid10"]),
        "filesystem": ChoiceRule("filesystem", ["ext4", "xfs"]),
        "devices": StringRule("devices", min_length=1),  # JSON string validation
    },
    "smb_share_creation": {
        "name": SMBShareNameRule("name"),
        "path": PathRule("path", must_exist=True),
        "comment": StringRule("comment", max_length=100, required=False, allow_empty=True),
        "writable": ChoiceRule("writable", ["true", "false", True, False]),
        "guest_ok": ChoiceRule("guest_ok", ["true", "false", True, False], required=False),
    },
    "nfs_share_creation": {
        "name": StringRule("name", min_length=1, max_length=64),
        "path": PathRule("path", must_exist=True),
        "allowed_hosts": NFSHostRule("allowed_hosts"),
        "options": StringRule("options", max_length=200, required=False, allow_empty=True),
    },
    "backup_job_creation": {
        "name": StringRule("name", min_length=1, max_length=128),
        "source_path": PathRule("source_path", must_exist=True),
        "destination_path": PathRule("destination_path"),
        "schedule": StringRule(
            "schedule",
            pattern=r"^(\*|[0-59]|\*/[0-9]+)\s+(\*|[0-23]|\*/[0-9]+)\s+(\*|[1-31]|\*/[0-9]+)\s+(\*|[1-12]|\*/[0-9]+)\s+(\*|[0-7]|\*/[0-9]+)$",
        ),
        "enabled": ChoiceRule("enabled", ["true", "false", True, False], required=False),
    },
}


def get_validation_rules(rule_set_name: str) -> Dict[str, ValidationRule]:
    """Get pre-defined validation rules by name"""
    return COMMON_VALIDATION_RULES.get(rule_set_name, {})


def validate_file_upload(allowed_extensions: List[str], max_size_mb: int = 16):
    """
    Decorator for validating file uploads
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "file" not in request.files:
                return jsonify({"error": True, "message": "No file uploaded"}), 400

            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": True, "message": "No file selected"}), 400

            # Check file extension
            if not any(file.filename.lower().endswith(ext.lower()) for ext in allowed_extensions):
                return (
                    jsonify(
                        {
                            "error": True,
                            "message": f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}',
                        }
                    ),
                    400,
                )

            # Check file size
            file.seek(0, 2)  # Seek to end of file
            file_size = file.tell()
            file.seek(0)  # Reset file pointer

            if file_size > max_size_mb * 1024 * 1024:
                return (
                    jsonify(
                        {"error": True, "message": f"File too large. Maximum size: {max_size_mb}MB"}
                    ),
                    413,
                )

            # Validate filename
            if not InputSanitizer.validate_filename(file.filename):
                return jsonify({"error": True, "message": "Invalid filename"}), 400

            return f(*args, **kwargs)

        return decorated_function

    return decorator
