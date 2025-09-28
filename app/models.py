"""Database models for MoxNAS"""
from __future__ import annotations
from typing import Dict, List, Optional, Any, Union
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import enum
import json
import re
from app import db


# Enums for better data integrity
class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"


class PoolStatus(enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    OFFLINE = "offline"
    SCRUBBING = "scrubbing"


class DeviceStatus(enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    FAILED = "failed"
    OFFLINE = "offline"
    SMART_FAIL = "smart_fail"


class ShareProtocol(enum.Enum):
    SMB = "smb"
    NFS = "nfs"
    FTP = "ftp"
    SFTP = "sftp"


class ShareStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class BackupStatus(enum.Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogLevel(enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SourceType(enum.Enum):
    DIRECTORY = "directory"
    DEVICE = "device"
    DATASET = "dataset"


class DestinationType(enum.Enum):
    DIRECTORY = "directory"
    S3 = "s3"
    REMOTE = "remote"
    FTP = "ftp"


class User(UserMixin, db.Model):
    """User model with enhanced security features"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER, index=True)

    # Personal information
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))

    # Security fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, index=True)
    last_login = db.Column(db.DateTime)
    last_password_change = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    force_password_change = db.Column(db.Boolean, default=False)

    # 2FA support
    totp_secret = db.Column(db.String(32))
    totp_enabled = db.Column(db.Boolean, default=False)
    backup_codes = db.Column(db.Text)  # JSON stored backup codes

    # Audit trail
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active = db.Column(db.Boolean, default=True, index=True)

    # Relationships
    created_by = db.relationship("User", remote_side=[id], backref="created_users")
    shares = db.relationship(
        "Share", backref="owner", lazy="dynamic", foreign_keys="Share.owner_id"
    )
    backup_jobs = db.relationship("BackupJob", backref="created_by_user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash and set password with security checks"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", password):
            raise ValueError("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:",.<>/?]', password):
            raise ValueError("Password must contain at least one special character")

        self.password_hash = generate_password_hash(password)
        self.last_password_change = datetime.now(timezone.utc)

    def check_password(self, password: str) -> bool:
        """Check password and handle failed attempts"""
        # Import here to avoid circular imports
        from flask import current_app

        # Skip lockout logic if security hardening is disabled (e.g., in tests)
        security_enabled: bool = current_app.config.get("SECURITY_HARDENING_ENABLED", True)

        if security_enabled and self.is_locked():
            return False

        if check_password_hash(self.password_hash, password):
            self.failed_login_attempts = 0
            self.last_login = datetime.now(timezone.utc)
            return True
        else:
            if security_enabled:
                self.failed_login_attempts += 1
                if self.failed_login_attempts >= 5:
                    self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
            return False

    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.locked_until and datetime.now(timezone.utc) < self.locked_until:
            return True
        if self.locked_until and datetime.now(timezone.utc) >= self.locked_until:
            # Account lock has expired, reset it
            self.locked_until = None
            self.failed_login_attempts = 0
            # Try to commit the changes, but don't fail if it doesn't work
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
        return False

    def unlock_account(self) -> None:
        """Unlock account (admin function)"""
        self.locked_until = None
        self.failed_login_attempts = 0

    def increment_failed_login_attempts(self) -> None:
        """Safely increment failed login attempts"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)

    def update_last_login(self) -> None:
        """Safely update last login timestamp"""
        self.last_login = datetime.now(timezone.utc)
        self.failed_login_attempts = 0
        self.locked_until = None
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class StorageDevice(db.Model):
    """Physical storage device model"""

    __tablename__ = "storage_devices"

    id = db.Column(db.Integer, primary_key=True)
    device_path = db.Column(db.String(255), unique=True, nullable=False, index=True)
    device_name = db.Column(db.String(128), nullable=False)
    device_model = db.Column(db.String(128))
    device_serial = db.Column(db.String(64), index=True)
    device_size = db.Column(db.BigInteger)  # Size in bytes
    sector_size = db.Column(db.Integer, default=512)

    # Status and health
    status = db.Column(
        db.Enum(DeviceStatus), nullable=False, default=DeviceStatus.HEALTHY, index=True
    )
    smart_data = db.Column(db.Text)  # JSON stored SMART data
    temperature = db.Column(db.Integer)  # Celsius
    power_on_hours = db.Column(db.Integer)

    # Pool membership
    pool_id = db.Column(db.Integer, db.ForeignKey("storage_pools.id"), index=True)

    # Audit trail
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def update_smart_data(self, smart_info: Dict[str, Any]) -> None:
        """Update SMART data and status"""
        self.smart_data = json.dumps(smart_info)
        self.updated_at = datetime.now(timezone.utc)

        # Update status based on SMART data
        if smart_info.get("overall_health") == "FAILED":
            self.status = DeviceStatus.SMART_FAIL
        elif smart_info.get("temperature", 0) > 60:
            self.status = DeviceStatus.WARNING
        else:
            self.status = DeviceStatus.HEALTHY

    def get_smart_data(self) -> Dict[str, Any]:
        """Get parsed SMART data"""
        if self.smart_data:
            return json.loads(self.smart_data)
        return {}

    @property
    def serial_number(self) -> Optional[str]:
        """Alias for device_serial for compatibility"""
        return self.device_serial

    @serial_number.setter
    def serial_number(self, value: str) -> None:
        """Setter for serial_number alias"""
        self.device_serial = value

    def __repr__(self) -> str:
        return f"<StorageDevice {self.device_name}>"


class StoragePool(db.Model):
    """Storage pool (RAID) model"""

    __tablename__ = "storage_pools"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False, index=True)
    raid_level = db.Column(db.String(32), nullable=False)  # raid0, raid1, raid5, raid10
    filesystem_type = db.Column(db.String(32), nullable=False, default="ext4")
    mount_point = db.Column(db.String(255), unique=True, nullable=False)

    # Pool properties
    total_size = db.Column(db.BigInteger)  # Total size in bytes
    used_size = db.Column(db.BigInteger, default=0)
    available_size = db.Column(db.BigInteger)

    # Status and health
    status = db.Column(db.Enum(PoolStatus), nullable=False, default=PoolStatus.HEALTHY, index=True)
    last_scrub = db.Column(db.DateTime, index=True)
    scrub_progress = db.Column(db.Integer, default=0)  # Percentage

    # Configuration
    auto_scrub_enabled = db.Column(db.Boolean, default=True)
    scrub_schedule = db.Column(db.String(128))  # Cron expression

    # Audit trail
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    devices = db.relationship("StorageDevice", backref="pool", lazy="dynamic")
    datasets = db.relationship("Dataset", backref="pool", lazy="dynamic")
    created_by = db.relationship("User", backref="created_pools")

    def calculate_usage(self) -> None:
        """Calculate current usage statistics"""
        # This would be implemented with actual filesystem calls
        pass

    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage"""
        if not self.total_size or self.total_size == 0:
            return 0.0
        return (self.used_size / self.total_size) * 100.0

    @property
    def available_space(self) -> int:
        """Calculate available space"""
        if not self.total_size:
            return 0
        return self.total_size - (self.used_size or 0)

    def start_scrub(self) -> None:
        """Start a scrub operation"""
        self.status = PoolStatus.SCRUBBING
        self.scrub_progress = 0

    def __repr__(self) -> str:
        return f"<StoragePool {self.name}>"


class Dataset(db.Model):
    """Dataset (directory/filesystem) model"""

    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    path = db.Column(db.String(512), unique=True, nullable=False)
    pool_id = db.Column(db.Integer, db.ForeignKey("storage_pools.id"), nullable=False, index=True)

    # Quota and usage
    quota_size = db.Column(db.BigInteger)  # Quota in bytes
    used_size = db.Column(db.BigInteger, default=0)

    # Permissions
    owner_uid = db.Column(db.Integer, default=0)
    owner_gid = db.Column(db.Integer, default=0)
    permissions = db.Column(db.String(10), default="755")

    # Audit trail
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    shares = db.relationship("Share", backref="dataset", lazy="dynamic")
    created_by = db.relationship("User", backref="created_datasets")

    def __repr__(self) -> str:
        return f"<Dataset {self.name}>"


class Share(db.Model):
    """Network share model"""

    __tablename__ = "shares"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False, index=True)
    protocol = db.Column(db.Enum(ShareProtocol), nullable=False, index=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("datasets.id"), nullable=False, index=True)
    path = db.Column(db.String(512))  # Share path

    # Access control
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    guest_access = db.Column(db.Boolean, default=False)
    read_only = db.Column(db.Boolean, default=False)

    # Network settings
    allowed_hosts = db.Column(db.Text)  # JSON list of allowed IP addresses

    # Status
    status = db.Column(
        db.Enum(ShareStatus), nullable=False, default=ShareStatus.INACTIVE, index=True
    )

    # Statistics
    bytes_transferred = db.Column(db.BigInteger, default=0)
    connections_count = db.Column(db.Integer, default=0)
    last_access = db.Column(db.DateTime, index=True)

    # Audit trail
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    created_by = db.relationship("User", foreign_keys=[created_by_id], backref="created_shares")

    def get_allowed_hosts(self) -> List[str]:
        """Get list of allowed hosts"""
        if self.allowed_hosts:
            return json.loads(self.allowed_hosts)
        return []

    def set_allowed_hosts(self, hosts: List[str]) -> None:
        """Set allowed hosts list"""
        self.allowed_hosts = json.dumps(hosts)

    def __repr__(self) -> str:
        return f"<Share {self.name}>"


class BackupJob(db.Model):
    """Backup job model"""

    __tablename__ = "backup_jobs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False, index=True)
    source_type = db.Column(
        db.Enum(SourceType), nullable=False, default=SourceType.DIRECTORY, index=True
    )
    source_path = db.Column(db.String(512), nullable=False)
    destination_type = db.Column(
        db.Enum(DestinationType), nullable=False, default=DestinationType.DIRECTORY, index=True
    )
    destination_path = db.Column(db.String(512), nullable=False)

    # Backup settings
    backup_type = db.Column(
        db.String(32), nullable=False, default="incremental"
    )  # full, incremental, differential
    schedule = db.Column(db.String(128), index=True)  # Cron expression
    retention_days = db.Column(db.Integer, default=30)
    compression = db.Column(db.Boolean, default=True)
    encryption = db.Column(db.Boolean, default=False)

    # Status
    status = db.Column(
        db.Enum(BackupStatus), nullable=False, default=BackupStatus.SCHEDULED, index=True
    )
    last_run = db.Column(db.DateTime, index=True)
    next_run = db.Column(db.DateTime, index=True)
    bytes_backed_up = db.Column(db.BigInteger, default=0)

    # Error handling
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)

    # Audit trail
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active = db.Column(db.Boolean, default=True, index=True)

    def __repr__(self) -> str:
        return f"<BackupJob {self.name}>"


class SystemLog(db.Model):
    """System audit and event log"""

    __tablename__ = "system_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    level = db.Column(db.Enum(LogLevel), nullable=False, index=True)
    category = db.Column(
        db.String(64), nullable=False, index=True
    )  # auth, storage, share, backup, system
    message = db.Column(db.Text, nullable=False)

    # User context
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    ip_address = db.Column(db.String(45), index=True)  # IPv6 support
    user_agent = db.Column(db.Text)

    # Additional context
    details = db.Column(db.Text)  # JSON stored additional details

    # Relationships
    user = db.relationship("User", backref="log_entries")

    @staticmethod
    def log_event(
        level: LogLevel, 
        category: str, 
        message: str, 
        user_id: Optional[int] = None, 
        ip_address: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create a log entry"""
        log_entry = SystemLog(
            level=level,
            category=category,
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            details=json.dumps(details) if details else None,
        )
        db.session.add(log_entry)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    def get_details(self) -> Dict[str, Any]:
        """Get parsed details"""
        if self.details:
            return json.loads(self.details)
        return {}

    def __repr__(self) -> str:
        return f"<SystemLog {self.level.value}: {self.message[:50]}>"


class Alert(db.Model):
    """System alert model"""

    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.Enum(AlertSeverity), nullable=False, index=True)
    category = db.Column(db.String(64), nullable=False, index=True)
    component = db.Column(db.String(64), index=True)  # Component that generated the alert

    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    acknowledged_at = db.Column(db.DateTime, index=True)
    acknowledged_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)

    # Auto-resolution
    auto_resolve = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, index=True)

    # Audit trail
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    acknowledged_by = db.relationship("User", backref="acknowledged_alerts")

    def acknowledge(self, user_id: int) -> None:
        """Acknowledge the alert"""
        self.acknowledged_at = datetime.now(timezone.utc)
        self.acknowledged_by_id = user_id
        self.is_active = False

    def __repr__(self) -> str:
        return f"<Alert {self.title}>"
