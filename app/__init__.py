"""Enhanced MoxNAS Application Factory with Enterprise Features"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_cors import CORS
from flask_socketio import SocketIO
import redis
from celery import Celery
import os
import logging
from logging.handlers import RotatingFileHandler

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()
cors = CORS()
socketio = SocketIO()


def make_celery(app):
    """Create Celery instance with Flask app context"""
    celery = Celery(
        app.import_name,
        backend=app.config.get("CELERY_RESULT_BACKEND"),
        broker=app.config.get("CELERY_BROKER_URL"),
    )

    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context"""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app(config_name="default"):
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    from config import config

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Only initialize rate limiter if enabled
    if app.config.get("RATELIMIT_ENABLED", True):
        limiter.init_app(app)

    mail.init_app(app)
    # Configure CORS with secure settings
    cors_origins = []
    if app.config.get("CORS_ORIGINS"):
        cors_origins = app.config["CORS_ORIGINS"].split(",")
    elif app.config.get("FLASK_ENV") == "development":
        cors_origins = ["http://localhost:5000", "http://127.0.0.1:5000"]

    cors.init_app(app, origins=cors_origins, supports_credentials=True)

    # Configure SocketIO with secure settings
    socketio_cors_origins = cors_origins if cors_origins else "*"
    socketio.init_app(app, cors_allowed_origins=socketio_cors_origins, async_mode="threading")

    # Initialize enhanced security
    if os.environ.get("SECURITY_HARDENING_ENABLED", "True").lower() in ["true", "1", "yes"]:
        try:
            from app.security import security_hardening

            security_hardening.init_app(app)
            app.logger.info("Enhanced security hardening activated")
        except ImportError as e:
            app.logger.warning(f"Enhanced security hardening not available: {e}")
    else:
        app.logger.info("Security hardening disabled via environment variable")

    # Defer initialization of enhanced modules to avoid app context issues
    app.logger.info("Enhanced storage manager available (will initialize on first request)")
    app.logger.info("ZFS support available (will check on first request)")
    app.logger.info("Enhanced SMB/NFS protocols available")

    # Login manager configuration
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User

        return User.query.get(int(user_id))

    # Register blueprints
    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")

    from app.api import bp as api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    from app.api.services import bp as services_api_bp

    app.register_blueprint(services_api_bp, url_prefix="/api")

    from app.storage import bp as storage_bp

    app.register_blueprint(storage_bp, url_prefix="/storage")

    from app.shares import bp as shares_bp

    app.register_blueprint(shares_bp, url_prefix="/shares")

    from app.backups import bp as backups_bp

    app.register_blueprint(backups_bp, url_prefix="/backups")

    from app.monitoring import bp as monitoring_bp

    app.register_blueprint(monitoring_bp, url_prefix="/monitoring")

    from app.errors import bp as errors_bp

    app.register_blueprint(errors_bp)

    # Register WebSocket events
    try:
        from app.websocket import register_websocket_events

        register_websocket_events(socketio)
        app.logger.info("WebSocket real-time updates enabled")
    except ImportError as e:
        app.logger.warning(f"WebSocket functionality not available: {e}")

    # Configure enhanced logging
    _setup_enhanced_logging(app)
    
    # Setup request correlation IDs
    @app.before_request
    def before_request():
        from app.utils.enhanced_logging import setup_correlation_id
        setup_correlation_id()
    
    # Setup error recovery manager
    from app.utils.error_handling import error_recovery
    app.error_recovery = error_recovery
    
    app.logger.info("MoxNAS startup with enhanced logging and error handling")

    # Register CLI commands
    @app.cli.command()
    def init_db():
        """Initialize the database"""
        # Import models here to avoid circular imports
        from app import models

        db.create_all()
        print("Database initialized.")

    @app.cli.command()
    def create_admin():
        """Create admin user"""
        from app.models import User, UserRole

        admin = User(
            username="admin",
            email="admin@moxnas.local",
            role=UserRole.ADMIN,
            first_name="System",
            last_name="Administrator",
        )
        admin.set_password("AdminPassword123!")
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")

    return app


def _setup_enhanced_logging(app):
    """Setup enhanced logging system"""
    from app.utils.enhanced_logging import (
        StructuredLogFilter, PerformanceLogFilter, SecurityLogFilter
    )
    import logging.handlers
    import json
    
    if app.debug or app.testing:
        # Simple logging for development/testing
        logging.basicConfig(
            level=logging.DEBUG if app.debug else logging.INFO,
            format='[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s:%(lineno)d - %(message)s'
        )
    else:
        # Enhanced logging for production-like environments
        if not os.path.exists("logs"):
            os.mkdir("logs")
        
        # Main application log
        file_handler = logging.handlers.RotatingFileHandler(
            "logs/moxnas.log", 
            maxBytes=app.config.get('LOG_MAX_BYTES', 10485760), 
            backupCount=app.config.get('LOG_BACKUP_COUNT', 5)
        )
        
        # Error-only log
        error_handler = logging.handlers.RotatingFileHandler(
            "logs/moxnas-errors.log", 
            maxBytes=app.config.get('LOG_MAX_BYTES', 10485760), 
            backupCount=app.config.get('LOG_BACKUP_COUNT', 5)
        )
        error_handler.setLevel(logging.ERROR)
        
        # Security events log
        security_handler = logging.handlers.RotatingFileHandler(
            "logs/moxnas-security.log", 
            maxBytes=app.config.get('LOG_MAX_BYTES', 10485760), 
            backupCount=app.config.get('LOG_BACKUP_COUNT', 5)
        )
        security_handler.addFilter(lambda record: getattr(record, 'category', '') in ['auth', 'security'])
        
        # Setup formatters
        if app.config.get('LOG_JSON_FORMAT'):
            class JSONFormatter(logging.Formatter):
                def format(self, record):
                    log_entry = {
                        'timestamp': self.formatTime(record),
                        'level': record.levelname,
                        'logger': record.name,
                        'message': record.getMessage(),
                        'module': record.module,
                        'function': record.funcName,
                        'line': record.lineno,
                    }
                    
                    # Add extra fields
                    for key, value in record.__dict__.items():
                        if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                                     'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                                     'relativeCreated', 'thread', 'threadName', 'processName', 
                                     'process', 'getMessage']:
                            log_entry[key] = value
                    
                    return json.dumps(log_entry)
            
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s [%(correlation_id)s] in %(module)s.%(funcName)s:%(lineno)d - '
                '%(message)s [U:%(user_id)s IP:%(ip_address)s]'
            )
        
        # Apply formatters
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        security_handler.setFormatter(formatter)
        
        # Add filters
        structured_filter = StructuredLogFilter()
        performance_filter = PerformanceLogFilter()
        security_filter = SecurityLogFilter()
        
        for handler in [file_handler, error_handler, security_handler]:
            handler.addFilter(structured_filter)
            handler.addFilter(performance_filter)
            handler.addFilter(security_filter)
        
        # Set levels
        log_level = getattr(logging, app.config.get('MOXNAS_LOG_LEVEL', 'INFO').upper())
        file_handler.setLevel(log_level)
        
        # Add handlers to app logger
        app.logger.addHandler(file_handler)
        app.logger.addHandler(error_handler)
        app.logger.addHandler(security_handler)
        app.logger.setLevel(log_level)
        
        # Add stdout logging if configured
        if app.config.get('LOG_TO_STDOUT'):
            stdout_handler = logging.StreamHandler()
            stdout_handler.setFormatter(formatter)
            stdout_handler.addFilter(structured_filter)
            stdout_handler.setLevel(log_level)
            app.logger.addHandler(stdout_handler)


# Export socketio for use in run scripts
__all__ = ["create_app", "db", "socketio"]
