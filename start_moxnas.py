#!/usr/bin/env python3
"""
MoxNAS Django/React Startup Script
Starts both Django backend and React frontend for development
"""

import os
import sys
import subprocess
import threading
import time
import signal
from pathlib import Path

# Ensure .env file is in the correct location
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    print(f"📝 Using environment file: {env_file}")
else:
    print("⚠️  No .env file found - using default settings")

def start_django():
    """Start Django development server"""
    print("🚀 Starting Django backend...")
    backend_dir = Path(__file__).parent / 'backend'
    os.chdir(backend_dir)
    
    # Run migrations
    print("📦 Running Django migrations...")
    subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)
    
    # Create initial data
    print("🛠️ Creating initial service data...")
    subprocess.run([sys.executable, 'manage.py', 'shell', '-c', '''
from core.models import ServiceStatus
services = [
    {"name": "smb", "port": 445},
    {"name": "nfs", "port": 2049},
    {"name": "ftp", "port": 21},
    {"name": "ssh", "port": 22},
    {"name": "snmp", "port": 161},
    {"name": "iscsi", "port": 3260},
]
for service_data in services:
    ServiceStatus.objects.get_or_create(
        name=service_data["name"],
        defaults={"port": service_data["port"]}
    )
print("✅ Initial services created")
'''], check=False)
    
    # Start Django server
    print("🌐 Starting Django server on http://localhost:8000")
    subprocess.run([sys.executable, 'manage.py', 'runserver', '0.0.0.0:8000'])

def start_react():
    """Start React development server"""
    print("⚛️ Starting React frontend...")
    frontend_dir = Path(__file__).parent / 'frontend'
    os.chdir(frontend_dir)
    
    # Check if node_modules exists
    if not os.path.exists('node_modules'):
        print("📦 Installing React dependencies...")
        subprocess.run(['npm', 'install'], check=True)
    
    # Start React server
    print("🌐 Starting React server on http://localhost:3000")
    subprocess.run(['npm', 'start'])

def build_frontend():
    """Build React frontend for production"""
    print("⚛️ Building React frontend...")
    frontend_dir = Path(__file__).parent / 'frontend'
    os.chdir(frontend_dir)
    
    # Install dependencies if needed
    if not os.path.exists('node_modules'):
        print("📦 Installing React dependencies...")
        subprocess.run(['npm', 'install'], check=True)
    
    # Build React app
    print("🔨 Building React app...")
    subprocess.run(['npm', 'run', 'build'], check=True)
    print("✅ Frontend build completed")

def start_production():
    """Start production mode with gunicorn"""
    print("🚀 Starting MoxNAS in production mode...")
    
    # Build frontend first
    build_frontend()
    
    # Switch to backend directory
    backend_dir = Path(__file__).parent / 'backend'
    os.chdir(backend_dir)
    
    # Run migrations
    print("📦 Running Django migrations...")
    subprocess.run([sys.executable, 'manage.py', 'migrate'], check=True)
    subprocess.run([sys.executable, 'manage.py', 'collectstatic', '--noinput'], check=True)
    
    # Create initial data
    print("🛠️ Setting up initial services...")
    subprocess.run([sys.executable, 'manage.py', 'shell', '-c', '''
from core.models import ServiceStatus
from users.models import MoxNASUser
from django.contrib.auth import get_user_model

# Create default admin user if it doesn't exist
User = get_user_model()
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser(
        username="admin",
        email="admin@moxnas.local",
        password="moxnas123",
        full_name="MoxNAS Administrator"
    )
    print("✅ Admin user created (admin/moxnas123)")

# Create service entries
services = [
    {"name": "smb", "port": 445},
    {"name": "nfs", "port": 2049},
    {"name": "ftp", "port": 21},
    {"name": "ssh", "port": 22},
    {"name": "snmp", "port": 161},
    {"name": "iscsi", "port": 3260},
]
for service_data in services:
    ServiceStatus.objects.get_or_create(
        name=service_data["name"],
        defaults={"port": service_data["port"]}
    )
print("✅ Services initialized")
'''], check=False)
    
    print("🌐 Starting MoxNAS web server on http://0.0.0.0:8000")
    # Start gunicorn on port 8000 
    os.chdir(backend_dir)
    subprocess.run([
        sys.executable, '-m', 'gunicorn', 
        'moxnas.wsgi:application',
        '--bind', '0.0.0.0:8000',
        '--workers', '3',
        '--timeout', '60',
        '--access-logfile', '-',
        '--error-logfile', '-',
        '--log-level', 'info'
    ])

def main():
    """Main function to handle startup"""
    if len(sys.argv) > 1 and sys.argv[1] == '--production':
        start_production()
        return
    
    # Development mode - start both Django and React
    django_thread = threading.Thread(target=start_django)
    react_thread = threading.Thread(target=start_react)
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print('\n🛑 Shutting down MoxNAS...')
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 Starting MoxNAS Development Environment")
    print("=" * 50)
    print("📋 Services:")
    print("   - Django Backend: http://localhost:8000")
    print("   - React Frontend: http://localhost:3000")
    print("=" * 50)
    print("💡 Press Ctrl+C to stop all services")
    print()
    
    # Start Django first
    django_thread.start()
    time.sleep(3)  # Give Django time to start
    
    # Then start React
    react_thread.start()
    
    # Wait for threads
    try:
        django_thread.join()
        react_thread.join()
    except KeyboardInterrupt:
        print('\n🛑 Shutting down...')

if __name__ == '__main__':
    main()