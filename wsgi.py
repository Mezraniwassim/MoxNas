"""WSGI entry point for MoxNAS"""
import os
from app import create_app

# Set default configuration
os.environ.setdefault('FLASK_ENV', 'production')

# Create application instance
app = create_app(os.environ.get('FLASK_ENV') or 'production')

if __name__ == '__main__':
    app.run()