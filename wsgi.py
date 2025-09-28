"""WSGI entry point for MoxNAS"""
import os
from dotenv import load_dotenv

# Load environment variables from .env.local
dotenv_path = os.path.join(os.path.dirname(__file__), '.env.local')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

from app import create_app

# Set default configuration
os.environ.setdefault('FLASK_ENV', 'production')

# Create application instance
app = create_app(os.environ.get('FLASK_ENV') or 'production')

if __name__ == '__main__':
    app.run()