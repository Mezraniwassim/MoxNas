"""Authentication decorators for MoxNAS"""
from functools import wraps
from flask import abort, current_app, g, request
from flask_login import current_user
from app.models import SystemLog, LogLevel
from datetime import datetime


def admin_required(f):
    """Decorator to require admin privileges"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)

        if not current_user.is_admin:
            # Log unauthorized access attempt
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category="auth",
                message=f"Unauthorized admin access attempt by {current_user.username}",
                user_id=current_user.id,
                ip_address=request.remote_addr,
            )
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


def api_token_required(f):
    """Decorator for API token authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")

        if auth_header:
            try:
                # Bearer token format
                token = auth_header.split(" ")[1]
            except IndexError:
                pass

        if not token:
            return {"error": "Token is missing"}, 401

        # Verify token (implement your token verification logic)
        # For now, we'll just check for a valid format
        if len(token) < 10:
            return {"error": "Invalid token"}, 401

        return f(*args, **kwargs)

    return decorated_function


def rate_limit_by_user(f):
    """Additional rate limiting by user"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            # Additional user-specific rate limiting can be implemented here
            pass
        return f(*args, **kwargs)

    return decorated_function
