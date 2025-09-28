"""Configuration settings for MoxNAS"""
import os
import secrets
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Generate secure key if not provided
    if not SECRET_KEY:
        if os.environ.get('FLASK_ENV') == 'development':
            SECRET_KEY = secrets.token_hex(32)
            print("⚠️  WARNING: Using generated SECRET_KEY for development. Set SECRET_KEY environment variable for production.")
        else:
            # For production, still generate but warn
            SECRET_KEY = secrets.token_hex(32)
            print("⚠️  CRITICAL: Generated SECRET_KEY for production. Set SECRET_KEY environment variable immediately!")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Redis and Celery
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND') or 'redis://localhost:6379/0'
    
    # Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = '[MoxNAS] '
    MAIL_SENDER = os.environ.get('MAIL_SENDER') or 'MoxNAS <noreply@moxnas.local>'
    
    # Security settings\n    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # Rate limiting
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI') or os.environ.get('REDIS_URL') or 'redis://localhost:6379/1'
    RATELIMIT_DEFAULT = '100 per hour'
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'true').lower() == 'true'
    
    # Application settings
    MOXNAS_ADMIN_EMAIL = os.environ.get('MOXNAS_ADMIN_EMAIL') or 'admin@moxnas.local'
    MOXNAS_STORAGE_ROOT = os.environ.get('MOXNAS_STORAGE_ROOT') or '/mnt/storage'
    MOXNAS_BACKUP_ROOT = os.environ.get('MOXNAS_BACKUP_ROOT') or '/mnt/backups'
    MOXNAS_LOG_LEVEL = os.environ.get('MOXNAS_LOG_LEVEL') or 'INFO'
    
    # Enhanced logging settings
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'false').lower() == 'true'
    LOG_JSON_FORMAT = os.environ.get('LOG_JSON_FORMAT', 'false').lower() == 'true'
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES') or '10485760')  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT') or '5')
    LOG_REQUEST_ID_HEADER = os.environ.get('LOG_REQUEST_ID_HEADER') or 'X-Request-ID'
    
    # Error handling settings
    ERROR_RETRY_MAX_ATTEMPTS = int(os.environ.get('ERROR_RETRY_MAX_ATTEMPTS') or '3')
    ERROR_RETRY_DELAY = float(os.environ.get('ERROR_RETRY_DELAY') or '1.0')
    ERROR_RETRY_BACKOFF_FACTOR = float(os.environ.get('ERROR_RETRY_BACKOFF_FACTOR') or '2.0')
    ERROR_CIRCUIT_BREAKER_THRESHOLD = int(os.environ.get('ERROR_CIRCUIT_BREAKER_THRESHOLD') or '10')
    ERROR_CIRCUIT_BREAKER_TIMEOUT = int(os.environ.get('ERROR_CIRCUIT_BREAKER_TIMEOUT') or '60')
    
    # Operation timeouts
    STORAGE_OPERATION_TIMEOUT = int(os.environ.get('STORAGE_OPERATION_TIMEOUT') or '300')
    SHARE_OPERATION_TIMEOUT = int(os.environ.get('SHARE_OPERATION_TIMEOUT') or '30')
    BACKUP_OPERATION_TIMEOUT = int(os.environ.get('BACKUP_OPERATION_TIMEOUT') or '3600')
    DATABASE_OPERATION_TIMEOUT = int(os.environ.get('DATABASE_OPERATION_TIMEOUT') or '30')
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    
    # Storage settings
    RAID_LEVELS = ['raid0', 'raid1', 'raid5', 'raid10']
    FILESYSTEM_TYPES = ['ext4', 'xfs']
    
    # Share protocols
    SHARE_PROTOCOLS = ['smb', 'nfs', 'ftp']
    
    # Monitoring settings
    MONITORING_INTERVAL = 60  # seconds
    SMART_CHECK_INTERVAL = 3600  # seconds
    ALERT_EMAIL_THROTTLE = 300  # seconds
    
    # Security validation
    @classmethod
    def validate_security_config(cls):
        """Validate critical security configurations"""
        errors = []
        
        if not os.environ.get('SECRET_KEY'):
            errors.append("SECRET_KEY environment variable must be set")
        
        secret_key = os.environ.get('SECRET_KEY')
        if secret_key and len(secret_key) < 32:
            errors.append("SECRET_KEY must be at least 32 characters long")
        
        if errors:
            raise ValueError("Security configuration errors: " + "; ".join(errors))
        
        return True
    
    @staticmethod
    def init_app(app):
        """Initialize logging for base config"""
        # Setup basic logging for non-production environments
        import logging
        import os
        from logging.handlers import RotatingFileHandler
        
        if not app.debug and not app.testing:
            log_dir = 'logs'
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Setup file handler
            file_handler = RotatingFileHandler(
                f'{log_dir}/moxnas.log',
                maxBytes=app.config.get('LOG_MAX_BYTES', 10485760),
                backupCount=app.config.get('LOG_BACKUP_COUNT', 5)
            )
            
            # Setup formatter
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s:%(lineno)d - '
                '%(message)s [PID:%(process)d]'
            )
            file_handler.setFormatter(formatter)
            
            # Set level
            log_level = getattr(logging, app.config.get('MOXNAS_LOG_LEVEL', 'INFO').upper())
            file_handler.setLevel(log_level)
            app.logger.addHandler(file_handler)
            app.logger.setLevel(log_level)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or os.environ.get('DATABASE_URL') or \
        'postgresql://moxnas:moxnas@localhost/moxnas_dev'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or os.environ.get('DATABASE_URL') or os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///test.db'
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'false').lower() == 'true'
    REDIS_URL = os.environ.get('REDIS_URL') or 'memory://'
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL') or 'memory://'
    CELERY_TASK_ALWAYS_EAGER = os.environ.get('CELERY_TASK_ALWAYS_EAGER', 'false').lower() == 'true'
    CELERY_TASK_EAGER_PROPAGATES = os.environ.get('CELERY_TASK_EAGER_PROPAGATES', 'false').lower() == 'true'
    
    # Override engine options for SQLite compatibility
    SQLALCHEMY_ENGINE_OPTIONS = {}
    
    # Disable security hardening in tests
    SECURITY_HARDENING_ENABLED = False

class ProductionConfig(Config):
    """Production configuration"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://moxnas:your_actual_password@localhost/moxnas'
    SESSION_COOKIE_SECURE = True
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Validate security configuration
        cls.validate_security_config()
        
        # Enhanced production logging
        cls._setup_production_logging(app)
        
        # Setup error monitoring
        cls._setup_error_monitoring(app)
    
    @classmethod
    def _setup_production_logging(cls, app):
        """Setup comprehensive production logging"""
        import logging
        import logging.handlers
        import json
        from datetime import datetime
        
        # Create logs directory
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Custom JSON formatter for structured logging
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'function': record.funcName,
                    'line': record.lineno,
                    'process': record.process,
                    'thread': record.thread
                }
                
                # Add exception info if present
                if record.exc_info:
                    log_entry['exception'] = cls.formatException(record.exc_info)
                
                # Add extra fields
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                                 'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                                 'thread', 'threadName', 'processName', 'process', 'getMessage', 'exc_info',
                                 'exc_text', 'stack_info', 'message']:
                        log_entry[key] = value
                
                return json.dumps(log_entry)
        
        # Setup file handlers with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            f'{log_dir}/moxnas.log',
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        
        error_handler = logging.handlers.RotatingFileHandler(
            f'{log_dir}/moxnas-errors.log',
            maxBytes=app.config['LOG_MAX_BYTES'],
            backupCount=app.config['LOG_BACKUP_COUNT']
        )
        error_handler.setLevel(logging.ERROR)
        
        # Setup formatters
        if app.config['LOG_JSON_FORMAT']:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s:%(lineno)d - '
                '%(message)s [PID:%(process)d TID:%(thread)d]'
            )
        
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        
        # Set log levels
        log_level = getattr(logging, app.config['MOXNAS_LOG_LEVEL'].upper())
        file_handler.setLevel(log_level)
        
        # Add handlers
        app.logger.addHandler(file_handler)
        app.logger.addHandler(error_handler)
        app.logger.setLevel(log_level)
        
        # Log to stdout if configured (for containerized deployments)
        if app.config['LOG_TO_STDOUT']:
            stdout_handler = logging.StreamHandler()
            stdout_handler.setFormatter(formatter)
            stdout_handler.setLevel(log_level)
            app.logger.addHandler(stdout_handler)
        
        # Log to syslog for production systems
        try:
            from logging.handlers import SysLogHandler
            syslog_handler = SysLogHandler(address='/dev/log')
            syslog_formatter = logging.Formatter(
                'moxnas[%(process)d]: [%(levelname)s] %(module)s.%(funcName)s - %(message)s'
            )
            syslog_handler.setFormatter(syslog_formatter)
            syslog_handler.setLevel(logging.WARNING)
            app.logger.addHandler(syslog_handler)
        except Exception as e:
            app.logger.warning(f'Failed to setup syslog handler: {e}')
    
    @classmethod
    def _setup_error_monitoring(cls, app):
        """Setup error monitoring and alerting"""
        # This can be extended with services like Sentry, Datadog, etc.
        app.logger.info('Error monitoring initialized')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
# Configuration système adaptée
SYSTEM_ADAPTED = True
AVAILABLE_STORAGE_TYPES = ['ext4', 'ntfs', 'vfat']
ZFS_ENABLED = False
LVM_ENABLED = False
SAMBA_ENABLED = True
DEFAULT_SHARE_PATH = '/home/wassim/Documents/MoxNAS/data'
