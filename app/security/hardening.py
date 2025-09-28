"""
Security hardening module for MoxNAS
Implements additional security measures beyond basic Flask security
"""
import secrets
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from flask import request, current_app, session, g
from functools import wraps
import re
import ipaddress
from app.models import SystemLog, LogLevel, User
from app import db


class SecurityHardening:
    """Centralized security hardening utilities"""

    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize security hardening with Flask app"""
        app.config.setdefault("SECURITY_HARDENING_ENABLED", True)
        app.config.setdefault("MAX_LOGIN_ATTEMPTS", 5)
        app.config.setdefault("LOCKOUT_DURATION", 1800)  # 30 minutes
        app.config.setdefault("SESSION_TIMEOUT", 28800)  # 8 hours
        app.config.setdefault("FAILED_LOGIN_TRACKING", True)

        # Register security handlers
        app.before_request(self.security_headers)
        app.before_request(self.session_security)
        app.after_request(self.response_security_headers)

    def security_headers(self):
        """Add security headers to requests"""
        if not current_app.config.get("SECURITY_HARDENING_ENABLED"):
            return

        # Track session security
        if "last_activity" in session:
            last_activity = datetime.fromisoformat(session["last_activity"])
            if datetime.utcnow() - last_activity > timedelta(
                seconds=current_app.config["SESSION_TIMEOUT"]
            ):
                session.clear()
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="auth",
                    message="Session expired due to inactivity",
                    ip_address=request.remote_addr,
                )

        session["last_activity"] = datetime.utcnow().isoformat()

    def session_security(self):
        """Enhanced session security checks"""
        if not current_app.config.get("SECURITY_HARDENING_ENABLED"):
            return

        # Check for session fixation attempts
        if "session_creation_time" not in session:
            session["session_creation_time"] = time.time()
            session["original_ip_hash"] = self._hash_ip(request.remote_addr)
            session["original_user_agent_hash"] = self._hash_user_agent(
                request.headers.get("User-Agent", "")
            )
        else:
            # Verify session integrity with more flexible IP checking
            current_ip_hash = self._hash_ip(request.remote_addr)
            current_ua_hash = self._hash_user_agent(request.headers.get("User-Agent", ""))

            # Only invalidate session if both IP and User-Agent changed (prevents NAT issues)
            if (
                session.get("original_ip_hash") != current_ip_hash
                and session.get("original_user_agent_hash") != current_ua_hash
            ):
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category="security",
                    message="Session fingerprint mismatch detected - possible session hijacking",
                    ip_address=request.remote_addr,
                )
                session.clear()
                return

        # Rotate session ID periodically (every 15 minutes)
        if time.time() - session.get("session_creation_time", 0) > 900:
            session.permanent = True
            # Flask doesn't have session.regenerate(), so we manually refresh the session
            old_data = dict(session)
            session.clear()
            session.update(old_data)
            session["session_creation_time"] = time.time()

    def response_security_headers(self, response):
        """Add security headers to responses"""
        if not current_app.config.get("SECURITY_HARDENING_ENABLED"):
            return response

        # Generate nonce for inline scripts and styles
        nonce = secrets.token_urlsafe(16)
        g.csp_nonce = nonce

        # Content Security Policy - Allow CSS files to load properly
        csp = (
            "default-src 'self'; "
            f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://cdn.socket.io; "
            f"style-src 'self' 'unsafe-inline' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests"
        )
        response.headers["Content-Security-Policy"] = csp

        # Additional security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response

    def _hash_ip(self, ip_address):
        """Hash IP address for privacy-preserving session validation"""
        try:
            # Normalize IP address and hash it
            ip = ipaddress.ip_address(ip_address)
            return hashlib.sha256(str(ip).encode()).hexdigest()[:16]
        except ValueError:
            # Fallback for invalid IP addresses
            return hashlib.sha256(ip_address.encode()).hexdigest()[:16]

    def _hash_user_agent(self, user_agent):
        """Hash user agent for session fingerprinting"""
        return hashlib.sha256(user_agent.encode()).hexdigest()[:16]


class InputSanitizer:
    """Input validation and sanitization utilities"""

    # Regex patterns for validation
    USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    FILENAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
    PATH_PATTERN = re.compile(r"^[a-zA-Z0-9._/-]+$")
    SMB_SHARE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")
    SMB_COMMENT_PATTERN = re.compile(r"^[a-zA-Z0-9\s._-]{0,100}$")
    NFS_PATH_PATTERN = re.compile(r"^/[a-zA-Z0-9._/-]*$")
    NFS_HOST_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+$|^\*$|^[0-9./]+$")
    IP_PATTERN = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if not username or len(username) < 3 or len(username) > 32:
            return False
        return bool(InputSanitizer.USERNAME_PATTERN.match(username))

    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email or len(email) > 120:
            return False
        return bool(InputSanitizer.EMAIL_PATTERN.match(email))

    @staticmethod
    def validate_filename(filename):
        """Validate filename for security"""
        if not filename or ".." in filename or filename.startswith("/"):
            return False
        return bool(InputSanitizer.FILENAME_PATTERN.match(filename))
    
    @staticmethod
    def sanitize_filename(filename):
        """Sanitize filename by removing invalid characters"""
        if not filename:
            return ""
        # Remove invalid characters and return cleaned filename
        import re
        # Allow letters, numbers, underscores, hyphens, and dots
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        # Remove consecutive dots and leading/trailing dots
        sanitized = re.sub(r'\.+', '.', sanitized).strip('.')
        return sanitized

    @staticmethod
    def validate_path(path):
        """Validate file path for security"""
        if not path or ".." in path:
            return False
        return bool(InputSanitizer.PATH_PATTERN.match(path))

    @staticmethod
    def validate_ip_address(ip):
        """Validate IP address"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def sanitize_string(value, max_length=255):
        """Sanitize string input"""
        if not value:
            return ""

        # Remove null bytes and control characters
        sanitized = "".join(char for char in value if ord(char) >= 32 or char in "\n\r\t")

        # Truncate to max length
        return sanitized[:max_length].strip()

    @staticmethod
    def validate_smb_share_name(name):
        """Validate SMB share name"""
        if not name or len(name) > 80:
            return False
        # Forbidden names in Windows
        forbidden = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        if name.upper() in forbidden:
            return False
        return bool(InputSanitizer.SMB_SHARE_NAME_PATTERN.match(name))

    @staticmethod
    def validate_smb_comment(comment):
        """Validate SMB share comment"""
        if not comment:
            return True  # Empty comments are allowed
        return bool(InputSanitizer.SMB_COMMENT_PATTERN.match(comment))

    @staticmethod
    def validate_nfs_path(path):
        """Validate NFS export path"""
        if not path or not path.startswith("/") or ".." in path:
            return False
        return bool(InputSanitizer.NFS_PATH_PATTERN.match(path))

    @staticmethod
    def validate_nfs_host(host):
        """Validate NFS client host specification"""
        if not host:
            return False
        # Allow wildcard, IP addresses, hostnames
        return bool(InputSanitizer.NFS_HOST_PATTERN.match(host))

    @staticmethod
    def sanitize_shell_argument(arg):
        """Sanitize argument for shell command execution"""
        if not arg:
            return ""

        # Remove dangerous characters
        dangerous_chars = ["|", "&", ";", "(", ")", "<", ">", "`", "$", "\\", '"', "'", "\n", "\r"]
        sanitized = arg
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")

        # Only allow alphanumeric, dots, slashes, dashes, underscores
        sanitized = re.sub(r"[^a-zA-Z0-9./_-]", "", sanitized)

        return sanitized[:1000]  # Limit length


class TokenGenerator:
    """Secure token generation utilities"""

    @staticmethod
    def generate_csrf_token():
        """Generate secure CSRF token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_api_token():
        """Generate secure API token"""
        return secrets.token_urlsafe(64)

    @staticmethod
    def generate_backup_codes(count=10):
        """Generate backup codes for 2FA"""
        codes = []
        for _ in range(count):
            code = secrets.randbelow(1000000)
            codes.append(f"{code:06d}")
        return codes

    @staticmethod
    def create_secure_hash(data, salt=None):
        """Create secure hash with salt"""
        if salt is None:
            salt = secrets.token_bytes(32)

        if isinstance(data, str):
            data = data.encode("utf-8")

        return hashlib.pbkdf2_hmac("sha256", data, salt, 100000), salt


class RateLimiter:
    """Enhanced rate limiting functionality"""

    def __init__(self):
        self.attempts = {}

    def is_rate_limited(self, identifier, max_attempts=5, window=300):
        """Check if identifier is rate limited"""
        now = time.time()

        if identifier not in self.attempts:
            self.attempts[identifier] = []

        # Clean old attempts
        self.attempts[identifier] = [
            timestamp for timestamp in self.attempts[identifier] if now - timestamp < window
        ]

        # Check if rate limited
        if len(self.attempts[identifier]) >= max_attempts:
            return True

        # Record attempt
        self.attempts[identifier].append(now)
        return False


def security_audit_decorator(audit_action):
    """Decorator for auditing security-sensitive actions"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()

            try:
                result = f(*args, **kwargs)

                # Log successful action
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="security",
                    message=f"Security action completed: {audit_action}",
                    user_id=getattr(g, "current_user", {}).get("id"),
                    ip_address=request.remote_addr,
                    details={
                        "action": audit_action,
                        "duration": time.time() - start_time,
                        "success": True,
                    },
                )

                return result

            except Exception as e:
                # Log failed action
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="security",
                    message=f"Security action failed: {audit_action}",
                    user_id=getattr(g, "current_user", {}).get("id"),
                    ip_address=request.remote_addr,
                    details={
                        "action": audit_action,
                        "duration": time.time() - start_time,
                        "error": str(e),
                        "success": False,
                    },
                )
                raise

        return decorated_function

    return decorator


def ip_whitelist_required(whitelist):
    """Decorator to restrict access to whitelisted IPs"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr

            # Check if IP is in whitelist
            for allowed_ip in whitelist:
                try:
                    if ipaddress.ip_address(client_ip) in ipaddress.ip_network(allowed_ip):
                        return f(*args, **kwargs)
                except ValueError:
                    continue

            # Log unauthorized access attempt
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category="security",
                message=f"Access denied from unauthorized IP: {client_ip}",
                ip_address=client_ip,
                details={"attempted_endpoint": request.endpoint},
            )

            return {"error": "Access denied"}, 403

        return decorated_function

    return decorator


class SecurityMonitor:
    """Security monitoring and alerting"""

    def __init__(self):
        self.threat_indicators = {
            "brute_force": self.detect_brute_force,
            "session_hijacking": self.detect_session_hijacking,
            "sql_injection": self.detect_sql_injection,
            "xss_attempt": self.detect_xss_attempt,
        }

    def detect_brute_force(self, request_data):
        """Detect potential brute force attacks"""
        ip = request_data.get("ip_address")
        if not ip:
            return False

        # Check failed login attempts in last 10 minutes
        recent_failures = SystemLog.query.filter(
            SystemLog.ip_address == ip,
            SystemLog.category == "auth",
            SystemLog.level == LogLevel.WARNING,
            SystemLog.timestamp > datetime.utcnow() - timedelta(minutes=10),
        ).count()

        return recent_failures >= 10

    def detect_session_hijacking(self, request_data):
        """Detect potential session hijacking"""
        # Implementation would check for session anomalies
        return False

    def detect_sql_injection(self, request_data):
        """Detect potential SQL injection attempts"""
        suspicious_patterns = [
            r"union\s+select",
            r"drop\s+table",
            r"insert\s+into",
            r"delete\s+from",
            r"update\s+set",
            r"--",
            r"/\*",
            r"\*/",
        ]

        request_content = str(request_data.get("content", ""))
        for pattern in suspicious_patterns:
            if re.search(pattern, request_content, re.IGNORECASE):
                return True

        return False

    def detect_xss_attempt(self, request_data):
        """Detect potential XSS attempts"""
        xss_patterns = [
            r"<script",
            r"javascript:",
            r"onload=",
            r"onerror=",
            r"alert\(",
            r"document\.cookie",
            r"window\.location",
        ]

        request_content = str(request_data.get("content", ""))
        for pattern in xss_patterns:
            if re.search(pattern, request_content, re.IGNORECASE):
                return True

        return False

    def analyze_request(self, request_data):
        """Analyze request for security threats"""
        threats = []

        for threat_name, detector in self.threat_indicators.items():
            if detector(request_data):
                threats.append(threat_name)

        if threats:
            SystemLog.log_event(
                level=LogLevel.CRITICAL,
                category="security",
                message=f'Security threats detected: {", ".join(threats)}',
                ip_address=request_data.get("ip_address"),
                details={"threats": threats, "request_data": request_data},
            )

        return threats


# Global security instances
security_hardening = SecurityHardening()
input_sanitizer = InputSanitizer()
token_generator = TokenGenerator()
rate_limiter = RateLimiter()
security_monitor = SecurityMonitor()
