"""Celery worker for background tasks"""
import os
from app import create_app, make_celery

# Create Flask app and Celery instance
flask_app = create_app(os.environ.get('FLASK_ENV') or 'production')
celery = make_celery(flask_app)

# Import all tasks to register them
from app.tasks import *