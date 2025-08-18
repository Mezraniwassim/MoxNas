import os
import stat
import shutil
import time
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
from django.conf import settings
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

class ServiceTemplateEngine:
    """
    Template engine for generating service configuration files
    """
    
    def __init__(self):
        self.template_dir = Path(settings.BASE_DIR) / 'templates' / 'services'
        self.config_dir = Path(settings.MOXNAS_CONFIG_DIR)
        self.backup_dir = self.config_dir / 'backups'
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    def render_template(self, template_name, context):
        """Render a template with given context"""
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise ValidationError(f"Template rendering failed: {e}")
    
    def backup_config(self, config_path):
        """Create backup of existing configuration"""
        if os.path.exists(config_path):
            backup_path = self.backup_dir / f"{Path(config_path).name}.{int(time.time())}"
            shutil.copy2(config_path, backup_path)
            logger.info(f"Backed up {config_path} to {backup_path}")
            return backup_path
        return None
    
    def write_config(self, config_path, content, backup=True):
        """Write configuration file with backup and validation"""
        try:
            # Backup existing config
            if backup:
                self.backup_config(config_path)
            
            # Ensure parent directory exists
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Write new configuration
            with open(config_path, 'w') as f:
                f.write(content)
            
            # Set appropriate permissions
            os.chmod(config_path, 0o644)
            logger.info(f"Successfully wrote configuration to {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to write config {config_path}: {e}")
            raise ValidationError(f"Failed to write configuration: {e}")
    
    def validate_path(self, path, must_exist=False, create_if_missing=False):
        """Validate and optionally create paths"""
        path_obj = Path(path)
        
        # Check if path exists when required
        if must_exist and not path_obj.exists():
            raise ValidationError(f"Path does not exist: {path}")
        
        # Create path if requested
        if create_if_missing and not path_obj.exists():
            try:
                path_obj.mkdir(parents=True, exist_ok=True)
                os.chmod(path, 0o755)
                logger.info(f"Created directory: {path}")
            except Exception as e:
                raise ValidationError(f"Failed to create directory {path}: {e}")
        
        # Validate permissions
        if path_obj.exists():
            if not os.access(path, os.R_OK):
                raise ValidationError(f"Path not readable: {path}")
            if path_obj.is_dir() and not os.access(path, os.X_OK):
                raise ValidationError(f"Directory not executable: {path}")
        
        return True

# Global template engine instance
template_engine = ServiceTemplateEngine()