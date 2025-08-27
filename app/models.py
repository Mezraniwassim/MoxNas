"""Database models for MoxNAS"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import enum
import json
from app import db

# Enums for better data integrity
class UserRole(enum.Enum):
    ADMIN = 'admin'
    USER = 'user'

class PoolStatus(enum.Enum):
    HEALTHY = 'healthy'
    DEGRADED = 'degraded'
    FAILED = 'failed'
    OFFLINE = 'offline'
    SCRUBBING = 'scrubbing'

class DeviceStatus(enum.Enum):
    HEALTHY = 'healthy'
    WARNING = 'warning'
    FAILED = 'failed'
    OFFLINE = 'offline'
    SMART_FAIL = 'smart_fail'

class ShareProtocol(enum.Enum):
    SMB = 'smb'
    NFS = 'nfs'
    FTP = 'ftp'
    SFTP = 'sftp'

class ShareStatus(enum.Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ERROR = 'error'

class BackupStatus(enum.Enum):
    SCHEDULED = 'scheduled'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class LogLevel(enum.Enum):
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'

class User(UserMixin, db.Model):
    """User model with enhanced security features"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)
    
    # Security fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    last_password_change = db.Column(db.DateTime, default=datetime.utcnow)
    force_password_change = db.Column(db.Boolean, default=False)
    
    # 2FA support
    totp_secret = db.Column(db.String(32))
    totp_enabled = db.Column(db.Boolean, default=False)
    backup_codes = db.Column(db.Text)  # JSON stored backup codes
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    created_by = db.relationship('User', remote_side=[id], backref='created_users')
    shares = db.relationship('Share', backref='owner', lazy='dynamic', foreign_keys='Share.owner_id')
    backup_jobs = db.relationship('BackupJob', backref='created_by_user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set password with security checks"""
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters long')
        self.password_hash = generate_password_hash(password)
        self.last_password_change = datetime.utcnow()
    
    def check_password(self, password):
        """Check password and handle failed attempts"""
        if self.is_locked():
            return False
            
        if check_password_hash(self.password_hash, password):
            self.failed_login_attempts = 0
            self.last_login = datetime.utcnow()
            db.session.commit()
            return True
        else:
            self.failed_login_attempts += 1
            if self.failed_login_attempts >= 5:
                self.locked_until = datetime.utcnow() + timedelta(minutes=30)
            db.session.commit()
            return False
    
    def is_locked(self):
        """Check if account is locked"""
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        if self.locked_until and datetime.utcnow() >= self.locked_until:
            self.locked_until = None
            self.failed_login_attempts = 0
            db.session.commit()
        return False
    
    def unlock_account(self):
        """Unlock account (admin function)"""
        self.locked_until = None
        self.failed_login_attempts = 0
    
    def is_admin(self):
        return self.role == UserRole.ADMIN
    
    def __repr__(self):
        return f'<User {self.username}>'

class StorageDevice(db.Model):
    """Physical storage device model"""
    __tablename__ = 'storage_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    device_path = db.Column(db.String(255), unique=True, nullable=False)
    device_name = db.Column(db.String(128), nullable=False)
    device_model = db.Column(db.String(128))
    device_serial = db.Column(db.String(64))
    device_size = db.Column(db.BigInteger)  # Size in bytes
    sector_size = db.Column(db.Integer, default=512)
    
    # Status and health
    status = db.Column(db.Enum(DeviceStatus), nullable=False, default=DeviceStatus.HEALTHY)
    smart_data = db.Column(db.Text)  # JSON stored SMART data
    temperature = db.Column(db.Integer)  # Celsius
    power_on_hours = db.Column(db.Integer)
    
    # Pool membership
    pool_id = db.Column(db.Integer, db.ForeignKey('storage_pools.id'))
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def update_smart_data(self, smart_info):
        """Update SMART data and status"""
        self.smart_data = json.dumps(smart_info)
        self.updated_at = datetime.utcnow()
        
        # Update status based on SMART data
        if smart_info.get('overall_health') == 'FAILED':
            self.status = DeviceStatus.SMART_FAIL
        elif smart_info.get('temperature', 0) > 60:
            self.status = DeviceStatus.WARNING
        else:
            self.status = DeviceStatus.HEALTHY
    
    def get_smart_data(self):
        """Get parsed SMART data"""
        if self.smart_data:
            return json.loads(self.smart_data)
        return {}
    
    def __repr__(self):
        return f'<StorageDevice {self.device_name}>'

class StoragePool(db.Model):
    """Storage pool (RAID) model"""
    __tablename__ = 'storage_pools'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    raid_level = db.Column(db.String(32), nullable=False)  # raid0, raid1, raid5, raid10
    filesystem_type = db.Column(db.String(32), nullable=False, default='ext4')
    mount_point = db.Column(db.String(255), unique=True, nullable=False)
    
    # Pool properties
    total_size = db.Column(db.BigInteger)  # Total size in bytes
    used_size = db.Column(db.BigInteger, default=0)
    available_size = db.Column(db.BigInteger)
    
    # Status and health
    status = db.Column(db.Enum(PoolStatus), nullable=False, default=PoolStatus.HEALTHY)
    last_scrub = db.Column(db.DateTime)
    scrub_progress = db.Column(db.Integer, default=0)  # Percentage
    
    # Configuration
    auto_scrub_enabled = db.Column(db.Boolean, default=True)
    scrub_schedule = db.Column(db.String(128))  # Cron expression
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    devices = db.relationship('StorageDevice', backref='pool', lazy='dynamic')
    datasets = db.relationship('Dataset', backref='pool', lazy='dynamic')
    created_by = db.relationship('User', backref='created_pools')
    
    def calculate_usage(self):
        """Calculate current usage statistics"""
        # This would be implemented with actual filesystem calls
        pass
    
    def start_scrub(self):
        """Start a scrub operation"""
        self.status = PoolStatus.SCRUBBING
        self.scrub_progress = 0
    
    def __repr__(self):
        return f'<StoragePool {self.name}>'

class Dataset(db.Model):
    """Dataset (directory/filesystem) model"""
    __tablename__ = 'datasets'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    path = db.Column(db.String(512), unique=True, nullable=False)
    pool_id = db.Column(db.Integer, db.ForeignKey('storage_pools.id'), nullable=False)
    
    # Quota and usage
    quota_size = db.Column(db.BigInteger)  # Quota in bytes
    used_size = db.Column(db.BigInteger, default=0)
    
    # Permissions
    owner_uid = db.Column(db.Integer, default=0)
    owner_gid = db.Column(db.Integer, default=0)
    permissions = db.Column(db.String(10), default='755')
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    shares = db.relationship('Share', backref='dataset', lazy='dynamic')
    created_by = db.relationship('User', backref='created_datasets')
    
    def __repr__(self):
        return f'<Dataset {self.name}>'

class Share(db.Model):
    """Network share model"""
    __tablename__ = 'shares'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    protocol = db.Column(db.Enum(ShareProtocol), nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey('datasets.id'), nullable=False)
    
    # Access control
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    guest_access = db.Column(db.Boolean, default=False)
    read_only = db.Column(db.Boolean, default=False)
    
    # Network settings
    allowed_hosts = db.Column(db.Text)  # JSON list of allowed IP addresses
    
    # Status
    status = db.Column(db.Enum(ShareStatus), nullable=False, default=ShareStatus.INACTIVE)
    
    # Statistics
    bytes_transferred = db.Column(db.BigInteger, default=0)
    connections_count = db.Column(db.Integer, default=0)
    last_access = db.Column(db.DateTime)
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_shares')
    
    def get_allowed_hosts(self):
        """Get list of allowed hosts"""
        if self.allowed_hosts:
            return json.loads(self.allowed_hosts)
        return []
    
    def set_allowed_hosts(self, hosts):
        """Set allowed hosts list"""
        self.allowed_hosts = json.dumps(hosts)
    
    def __repr__(self):
        return f'<Share {self.name}>'

class BackupJob(db.Model):
    """Backup job model"""
    __tablename__ = 'backup_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    source_path = db.Column(db.String(512), nullable=False)
    destination_path = db.Column(db.String(512), nullable=False)
    
    # Backup settings
    backup_type = db.Column(db.String(32), nullable=False, default='incremental')  # full, incremental, differential
    schedule = db.Column(db.String(128))  # Cron expression
    retention_days = db.Column(db.Integer, default=30)
    compression = db.Column(db.Boolean, default=True)
    encryption = db.Column(db.Boolean, default=False)
    
    # Status
    status = db.Column(db.Enum(BackupStatus), nullable=False, default=BackupStatus.SCHEDULED)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    bytes_backed_up = db.Column(db.BigInteger, default=0)
    
    # Error handling
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<BackupJob {self.name}>'

class SystemLog(db.Model):
    """System audit and event log"""
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    level = db.Column(db.Enum(LogLevel), nullable=False, index=True)
    category = db.Column(db.String(64), nullable=False, index=True)  # auth, storage, share, backup, system
    message = db.Column(db.Text, nullable=False)
    
    # User context
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.Text)
    
    # Additional context
    details = db.Column(db.Text)  # JSON stored additional details
    
    # Relationships
    user = db.relationship('User', backref='log_entries')
    
    @staticmethod
    def log_event(level, category, message, user_id=None, ip_address=None, details=None):
        """Create a log entry"""
        log_entry = SystemLog(
            level=level,
            category=category,
            message=message,
            user_id=user_id,
            ip_address=ip_address,
            details=json.dumps(details) if details else None
        )
        db.session.add(log_entry)
        db.session.commit()
    
    def get_details(self):
        """Get parsed details"""
        if self.details:
            return json.loads(self.details)
        return {}
    
    def __repr__(self):
        return f'<SystemLog {self.level.value}: {self.message[:50]}>'

class Alert(db.Model):
    """System alert model"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.Enum(LogLevel), nullable=False)
    category = db.Column(db.String(64), nullable=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    acknowledged_at = db.Column(db.DateTime)
    acknowledged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Auto-resolution
    auto_resolve = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)
    
    # Audit trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    acknowledged_by = db.relationship('User', backref='acknowledged_alerts')
    
    def acknowledge(self, user_id):
        """Acknowledge the alert"""
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by_id = user_id
        self.is_active = False
    
    def __repr__(self):
        return f'<Alert {self.title}>'