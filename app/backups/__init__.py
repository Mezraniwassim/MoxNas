"""Enhanced Backup Management Blueprint"""
from flask import Blueprint

bp = Blueprint("backups", __name__)

# Initialize enhanced backup system
try:
    from app.backups.enhanced_backup import enhanced_backup_manager

    enhanced_backup_manager.initialize()
except ImportError:
    pass

from app.backups import routes
