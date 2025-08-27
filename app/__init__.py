"""MoxNAS Application Factory"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_cors import CORS
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

def make_celery(app):
    """Create Celery instance with Flask app context"""
    celery = Celery(
        app.import_name,
        backend=app.config.get('CELERY_RESULT_BACKEND'),
        broker=app.config.get('CELERY_BROKER_URL')
    )
    
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

def create_app(config_name='default'):
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
    limiter.init_app(app)
    mail.init_app(app)
    cors.init_app(app)
    
    # Login manager configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    from app.api.services import bp as services_api_bp
    app.register_blueprint(services_api_bp, url_prefix='/api')
    
    from app.storage import bp as storage_bp
    app.register_blueprint(storage_bp, url_prefix='/storage')
    
    from app.shares import bp as shares_bp
    app.register_blueprint(shares_bp, url_prefix='/shares')
    
    from app.backups import bp as backups_bp
    app.register_blueprint(backups_bp, url_prefix='/backups')
    
    from app.monitoring import bp as monitoring_bp
    app.register_blueprint(monitoring_bp, url_prefix='/monitoring')
    
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)
    
    # Configure logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/moxnas.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('MoxNAS startup')
    
    return app

# Import models to register them with SQLAlchemy
from app import models