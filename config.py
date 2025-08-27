"""Configuration settings for MoxNAS"""
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'moxnas-super-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://moxnas:moxnas@localhost/moxnas'
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
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/1'
    RATELIMIT_DEFAULT = '100 per hour'
    
    # Application settings
    MOXNAS_ADMIN_EMAIL = os.environ.get('MOXNAS_ADMIN_EMAIL') or 'admin@moxnas.local'
    MOXNAS_STORAGE_ROOT = os.environ.get('MOXNAS_STORAGE_ROOT') or '/mnt/storage'
    MOXNAS_BACKUP_ROOT = os.environ.get('MOXNAS_BACKUP_ROOT') or '/mnt/backups'
    MOXNAS_LOG_LEVEL = os.environ.get('MOXNAS_LOG_LEVEL') or 'INFO'
    
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
    
    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
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

class ProductionConfig(Config):
    """Production configuration"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://moxnas:moxnas@localhost/moxnas'
    SESSION_COOKIE_SECURE = True
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to syslog
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.WARNING)
        app.logger.addHandler(syslog_handler)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}