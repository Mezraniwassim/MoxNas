from flask import request, jsonify
from flask_login import login_required, current_user
from app.api import bp
from app.models import User, SystemLog, LogLevel
from app import limiter
from app.utils.error_handler import secure_route, validate_input, DatabaseErrorHandler
from app.security.hardening import InputSanitizer


# Authentication API with enhanced rate limiting
@bp.route("/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
@limiter.limit("20 per hour")
@limiter.limit("100 per day")
@secure_route
@validate_input(
    username=lambda x: InputSanitizer.sanitize_username(x) == x,
    password=lambda x: len(x) >= 8 and len(x) <= 128,
)
def api_login():
    """API login endpoint"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password) and user.is_active:
            # Check if user account is locked
            if user.is_locked():
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category="auth",
                    message=f"Login attempt on locked account: {username}",
                    ip_address=request.remote_addr,
                )
                return jsonify({"error": "Account is temporarily locked"}), 423

            # Reset failed login attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.update_last_login()

            # In a real API, you would generate a JWT token here
            SystemLog.log_event(
                level=LogLevel.INFO,
                category="auth",
                message=f"Successful API login: {username}",
                user_id=user.id,
                ip_address=request.remote_addr,
            )

            return jsonify(
                {
                    "success": True,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "role": user.role.value,
                        "last_login": user.last_login.isoformat() if user.last_login else None,
                    },
                }
            )
        else:
            # Handle failed login attempt
            if user:
                user.increment_failed_login_attempts()
                if user.failed_login_attempts >= 5:
                    SystemLog.log_event(
                        level=LogLevel.CRITICAL,
                        category="security",
                        message=f"Account locked due to repeated failed login attempts: {username}",
                        ip_address=request.remote_addr,
                    )

            SystemLog.log_event(
                level=LogLevel.WARNING,
                category="auth",
                message=f"API login failed for user: {username}",
                ip_address=request.remote_addr,
            )
            return jsonify({"error": "Invalid credentials"}), 401


@bp.route("/auth/user", methods=["GET"])
@login_required
@secure_route
def api_current_user():
    """Get current user information"""
    return jsonify(
        {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role.value,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            "totp_enabled": current_user.totp_enabled,
        }
    )
