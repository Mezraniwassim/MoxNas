#!/usr/bin/env python3
"""
MoxNas Development Server Startup Script
This script starts both the Django backend and React frontend for development
"""

import os
import sys
import subprocess
import threading
import signal
import time
from pathlib import Path

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def log(message, color=Colors.BLUE):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"{color}[{timestamp}]{Colors.NC} {message}")

def error(message):
    log(f"ERROR: {message}", Colors.RED)

def success(message):
    log(f"SUCCESS: {message}", Colors.GREEN)

def warning(message):
    log(f"WARNING: {message}", Colors.YELLOW)

class MoxNasServer:
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.base_dir = Path(__file__).parent.absolute()
        self.backend_dir = self.base_dir / 'backend'
        self.frontend_dir = self.base_dir / 'frontend'
        
    def check_requirements(self):
        """Check if all requirements are met"""
        log("Checking requirements...")
        
        # Check if directories exist
        if not self.backend_dir.exists():
            error(f"Backend directory not found: {self.backend_dir}")
            return False
            
        if not self.frontend_dir.exists():
            error(f"Frontend directory not found: {self.frontend_dir}")
            return False
        
        # Check if Python virtual environment exists
        venv_path = self.base_dir / 'venv'
        if not venv_path.exists():
            warning("Python virtual environment not found, creating one...")
            self.create_venv()
        
        # Check if Node.js is installed
        try:
            subprocess.run(['node', '--version'], check=True, capture_output=True)
            subprocess.run(['npm', '--version'], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            error("Node.js and npm are required but not installed")
            return False
        
        success("Requirements check passed")
        return True
    
    def create_venv(self):
        """Create Python virtual environment"""
        try:
            log("Creating Python virtual environment...")
            subprocess.run([sys.executable, '-m', 'venv', 'venv'], 
                         cwd=self.base_dir, check=True)
            success("Virtual environment created")
        except subprocess.CalledProcessError as e:
            error(f"Failed to create virtual environment: {e}")
            sys.exit(1)
    
    def setup_backend(self):
        """Setup Django backend"""
        log("Setting up Django backend...")
        
        # Get Python executable path
        if os.name == 'nt':  # Windows
            python_exe = self.base_dir / 'venv' / 'Scripts' / 'python.exe'
            pip_exe = self.base_dir / 'venv' / 'Scripts' / 'pip.exe'
        else:  # Unix/Linux
            python_exe = self.base_dir / 'venv' / 'bin' / 'python'
            pip_exe = self.base_dir / 'venv' / 'bin' / 'pip'
        
        # Install requirements
        requirements_file = self.base_dir / 'requirements.txt'
        if requirements_file.exists():
            log("Installing Python dependencies...")
            try:
                subprocess.run([str(pip_exe), 'install', '-r', str(requirements_file)], 
                             check=True, capture_output=True)
                success("Python dependencies installed")
            except subprocess.CalledProcessError as e:
                error(f"Failed to install Python dependencies: {e}")
                return False
        
        # Run migrations
        log("Running database migrations...")
        try:
            subprocess.run([str(python_exe), 'manage.py', 'migrate'], 
                         cwd=self.backend_dir, check=True, capture_output=True)
            success("Database migrations completed")
        except subprocess.CalledProcessError as e:
            error(f"Database migration failed: {e}")
            return False
        
        # Create superuser if it doesn't exist
        log("Creating admin user...")
        try:
            create_user_script = '''
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@moxnas.local", "admin123")
    print("Admin user created: admin/admin123")
else:
    print("Admin user already exists")
'''
            subprocess.run([str(python_exe), 'manage.py', 'shell', '-c', create_user_script], 
                         cwd=self.backend_dir, check=True, capture_output=True)
            success("Admin user ready")
        except subprocess.CalledProcessError:
            warning("Could not create admin user (may already exist)")
        
        return True
    
    def setup_frontend(self):
        """Setup React frontend"""
        log("Setting up React frontend...")
        
        # Check if node_modules exists
        node_modules = self.frontend_dir / 'node_modules'
        if not node_modules.exists():
            log("Installing Node.js dependencies...")
            try:
                subprocess.run(['npm', 'install'], cwd=self.frontend_dir, check=True)
                success("Node.js dependencies installed")
            except subprocess.CalledProcessError as e:
                error(f"Failed to install Node.js dependencies: {e}")
                return False
        
        return True
    
    def start_backend(self):
        """Start Django development server"""
        log("Starting Django backend server on http://localhost:8000", Colors.PURPLE)
        
        # Get Python executable path
        if os.name == 'nt':  # Windows
            python_exe = self.base_dir / 'venv' / 'Scripts' / 'python.exe'
        else:  # Unix/Linux
            python_exe = self.base_dir / 'venv' / 'bin' / 'python'
        
        self.backend_process = subprocess.Popen(
            [str(python_exe), 'manage.py', 'runserver', '0.0.0.0:8000'],
            cwd=self.backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor backend output
        def monitor_backend():
            for line in self.backend_process.stdout:
                print(f"{Colors.PURPLE}[BACKEND]{Colors.NC} {line.strip()}")
        
        backend_thread = threading.Thread(target=monitor_backend, daemon=True)
        backend_thread.start()
    
    def start_frontend(self):
        """Start React development server"""
        log("Starting React frontend server on http://localhost:3000", Colors.CYAN)
        
        # Set environment variable to avoid browser auto-opening
        env = os.environ.copy()
        env['BROWSER'] = 'none'
        
        self.frontend_process = subprocess.Popen(
            ['npm', 'start'],
            cwd=self.frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            env=env
        )
        
        # Monitor frontend output
        def monitor_frontend():
            for line in self.frontend_process.stdout:
                # Filter out some verbose npm output
                if not any(skip in line.lower() for skip in ['webpack compiled', 'compiled successfully']):
                    print(f"{Colors.CYAN}[FRONTEND]{Colors.NC} {line.strip()}")
        
        frontend_thread = threading.Thread(target=monitor_frontend, daemon=True)
        frontend_thread.start()
    
    def start_production(self):
        """Start production server with Gunicorn"""
        log("Starting production server on http://localhost:8000", Colors.GREEN)
        
        # Get Python executable path
        if os.name == 'nt':  # Windows
            python_exe = self.base_dir / 'venv' / 'Scripts' / 'python.exe'
            gunicorn_exe = self.base_dir / 'venv' / 'Scripts' / 'gunicorn.exe'
        else:  # Unix/Linux
            python_exe = self.base_dir / 'venv' / 'bin' / 'python'
            gunicorn_exe = self.base_dir / 'venv' / 'bin' / 'gunicorn'
        
        # Collect static files first
        log("Collecting static files...")
        try:
            subprocess.run([str(python_exe), 'manage.py', 'collectstatic', '--noinput'], 
                         cwd=self.backend_dir, check=True, capture_output=True)
            success("Static files collected")
        except subprocess.CalledProcessError as e:
            error(f"Failed to collect static files: {e}")
            return
        
        # Build frontend if needed
        build_dir = self.frontend_dir / 'build'
        if not build_dir.exists():
            log("Building React frontend...")
            try:
                subprocess.run(['npm', 'run', 'build'], cwd=self.frontend_dir, check=True)
                success("Frontend build completed")
            except subprocess.CalledProcessError as e:
                error(f"Frontend build failed: {e}")
                return
        
        # Start Gunicorn
        self.backend_process = subprocess.Popen(
            [str(gunicorn_exe), '--bind', '0.0.0.0:8000', '--workers', '3', 
             '--chdir', str(self.backend_dir), 'moxnas.wsgi:application'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor gunicorn output
        def monitor_gunicorn():
            for line in self.backend_process.stdout:
                print(f"{Colors.GREEN}[GUNICORN]{Colors.NC} {line.strip()}")
        
        gunicorn_thread = threading.Thread(target=monitor_gunicorn, daemon=True)
        gunicorn_thread.start()
    
    def show_urls(self):
        """Show access URLs"""
        log("=" * 50, Colors.GREEN)
        log("MoxNas is now running!", Colors.GREEN)
        log("=" * 50, Colors.GREEN)
        log("Web Interface: http://localhost:8000", Colors.GREEN)
        log("Admin Panel:   http://localhost:8000/admin", Colors.GREEN)
        log("API Docs:      http://localhost:8000/api", Colors.GREEN)
        log("")
        log("Default admin credentials:", Colors.YELLOW)
        log("  Username: admin", Colors.YELLOW)
        log("  Password: admin123", Colors.YELLOW)
        log("")
        log("Press Ctrl+C to stop all servers", Colors.BLUE)
        log("=" * 50, Colors.GREEN)
    
    def cleanup(self):
        """Clean up processes"""
        log("Shutting down servers...")
        
        if self.backend_process:
            self.backend_process.terminate()
            self.backend_process.wait()
        
        if self.frontend_process:
            self.frontend_process.terminate()
            self.frontend_process.wait()
        
        success("All servers stopped")
    
    def run_development(self):
        """Run development servers"""
        if not self.check_requirements():
            sys.exit(1)
        
        if not self.setup_backend():
            sys.exit(1)
        
        if not self.setup_frontend():
            sys.exit(1)
        
        # Start servers
        self.start_backend()
        time.sleep(3)  # Give backend time to start
        
        self.start_frontend()
        time.sleep(3)  # Give frontend time to start
        
        self.show_urls()
        
        try:
            # Keep the main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()
    
    def run_production(self):
        """Run production server"""
        if not self.check_requirements():
            sys.exit(1)
        
        if not self.setup_backend():
            sys.exit(1)
        
        self.start_production()
        self.show_urls()
        
        try:
            # Keep the main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.cleanup()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--production':
        log("Starting MoxNas in production mode...")
        server = MoxNasServer()
        server.run_production()
    else:
        log("Starting MoxNas in development mode...")
        log("Use --production flag for production mode")
        server = MoxNasServer()
        server.run_development()

if __name__ == '__main__':
    main()