#!/usr/bin/env python3
"""
MoxNAS Startup Script
Handles Django setup, service initialization, and gunicorn startup
"""

import os
import sys
import subprocess
import logging
import time
import socket
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MoxNASStarter:
    def __init__(self):
        self.backend_dir = Path(__file__).parent
        self.project_root = self.backend_dir.parent
        self.venv_path = self.project_root / 'venv'
        
    def check_port_available(self, port=8000):
        """Check if port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return True
        except OSError:
            return False
    
    def kill_existing_processes(self, port=8000):
        """Kill existing processes on the port"""
        try:
            # Find and kill processes using the port
            result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        logger.info(f"Killing process {pid} on port {port}")
                        subprocess.run(['kill', '-9', pid], capture_output=True)
                time.sleep(2)
        except Exception as e:
            logger.warning(f"Error killing processes on port {port}: {e}")
    
    def setup_environment(self):
        """Setup required directories and environment"""
        try:
            # Create required directories
            directories = [
                '/mnt/storage',
                '/var/log/moxnas',
                '/etc/moxnas',
                '/var/run/moxnas'
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True, mode=0o755)
                logger.info(f"Ensured directory exists: {directory}")
            
            # Set DJANGO_SETTINGS_MODULE
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moxnas.settings')
            
            # Add backend directory to Python path
            if str(self.backend_dir) not in sys.path:
                sys.path.insert(0, str(self.backend_dir))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup environment: {e}")
            return False
    
    def run_django_setup(self):
        """Run Django migrations and setup"""
        try:
            os.chdir(self.backend_dir)
            
            # Check if Django is available
            try:
                import django
                logger.info(f"Using Django version: {django.get_version()}")
            except ImportError:
                logger.error("Django not found. Please install requirements.")
                return False
            
            # Run migrations
            logger.info("Running Django migrations...")
            result = subprocess.run([
                sys.executable, 'manage.py', 'migrate', '--noinput'
            ], cwd=self.backend_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"Migration warnings: {result.stderr}")
            else:
                logger.info("Migrations completed successfully")
            
            # Collect static files
            logger.info("Collecting static files...")
            result = subprocess.run([
                sys.executable, 'manage.py', 'collectstatic', '--noinput'
            ], cwd=self.backend_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"Static files collection warnings: {result.stderr}")
            else:
                logger.info("Static files collected successfully")
            
            # Initialize services
            logger.info("Initializing MoxNAS services...")
            result = subprocess.run([
                sys.executable, 'manage.py', 'initialize_services'
            ], cwd=self.backend_dir, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"Service initialization warnings: {result.stderr}")
            else:
                logger.info("Services initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Django setup failed: {e}")
            return False
    
    def start_gunicorn(self, port=8000, workers=3):
        """Start gunicorn server"""
        try:
            # Kill any existing processes on the port
            if not self.check_port_available(port):
                logger.info(f"Port {port} is busy, killing existing processes...")
                self.kill_existing_processes(port)
                time.sleep(3)
            
            # Check if port is now available
            if not self.check_port_available(port):
                logger.error(f"Port {port} is still not available")
                return False
            
            os.chdir(self.backend_dir)
            
            # Gunicorn command
            cmd = [
                'gunicorn',
                '--bind', f'0.0.0.0:{port}',
                '--workers', str(workers),
                '--timeout', '120',
                '--keep-alive', '2',
                '--max-requests', '1000',
                '--preload',
                '--access-logfile', '/var/log/moxnas/access.log',
                '--error-logfile', '/var/log/moxnas/error.log',
                '--log-level', 'info',
                'moxnas.wsgi:application'
            ]
            
            logger.info(f"Starting gunicorn on port {port} with {workers} workers...")
            logger.info(f"Command: {' '.join(cmd)}")
            
            # Start gunicorn
            process = subprocess.Popen(cmd, cwd=self.backend_dir)
            
            # Wait a moment and check if it started successfully
            time.sleep(3)
            if process.poll() is None:
                logger.info(f"✅ MoxNAS started successfully!")
                logger.info(f"🌐 Access MoxNAS at: http://localhost:{port}")
                logger.info(f"📊 Admin interface: http://localhost:{port}/admin")
                logger.info(f"🔧 API docs: http://localhost:{port}/api")
                
                # Wait for the process
                try:
                    process.wait()
                except KeyboardInterrupt:
                    logger.info("Shutting down MoxNAS...")
                    process.terminate()
                    process.wait()
                    
                return True
            else:
                logger.error("Gunicorn failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start gunicorn: {e}")
            return False
    
    def run_development_server(self, port=8000):
        """Run Django development server as fallback"""
        try:
            logger.info("Starting Django development server as fallback...")
            os.chdir(self.backend_dir)
            
            cmd = [sys.executable, 'manage.py', 'runserver', f'0.0.0.0:{port}']
            logger.info(f"Command: {' '.join(cmd)}")
            
            process = subprocess.Popen(cmd, cwd=self.backend_dir)
            
            try:
                process.wait()
            except KeyboardInterrupt:
                logger.info("Shutting down development server...")
                process.terminate()
                process.wait()
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to start development server: {e}")
            return False

def main():
    starter = MoxNASStarter()
    
    logger.info("🚀 Starting MoxNAS...")
    
    # Setup environment
    if not starter.setup_environment():
        logger.error("❌ Environment setup failed")
        sys.exit(1)
    
    # Run Django setup
    if not starter.run_django_setup():
        logger.error("❌ Django setup failed")
        sys.exit(1)
    
    # Try to start with gunicorn
    try:
        import gunicorn
        logger.info("✅ Gunicorn available, starting production server...")
        if not starter.start_gunicorn():
            logger.warning("⚠️ Gunicorn failed, trying development server...")
            starter.run_development_server()
    except ImportError:
        logger.info("ℹ️ Gunicorn not available, starting development server...")
        starter.run_development_server()

if __name__ == '__main__':
    main()