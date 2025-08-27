#!/usr/bin/env python3
"""
MoxNAS Service Management Script
Handles all MoxNAS services and provides health monitoring
"""
import os
import sys
import time
import signal
import subprocess
import psutil
import json
from datetime import datetime
from pathlib import Path

class MoxNASService:
    """MoxNAS Service Manager"""
    
    def __init__(self):
        self.base_dir = Path('/opt/moxnas')
        self.venv_python = self.base_dir / 'venv' / 'bin' / 'python'
        self.services = {
            'web': {
                'command': [str(self.venv_python), '-m', 'gunicorn', '--bind', '127.0.0.1:5000', '--workers', '3', 'wsgi:app'],
                'cwd': str(self.base_dir),
                'env': self._get_env(),
                'process': None,
                'required': True
            },
            'worker': {
                'command': [str(self.venv_python), '-m', 'celery', '-A', 'celery_worker.celery', 'worker', '--loglevel=info'],
                'cwd': str(self.base_dir),
                'env': self._get_env(),
                'process': None,
                'required': True
            },
            'scheduler': {
                'command': [str(self.venv_python), '-m', 'celery', '-A', 'celery_worker.celery', 'beat', '--loglevel=info'],
                'cwd': str(self.base_dir),
                'env': self._get_env(),
                'process': None,
                'required': True
            }
        }
        self.running = False
        self.health_check_interval = 30  # seconds
        
    def _get_env(self):
        """Get environment variables for services"""
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.base_dir)
        env['FLASK_APP'] = 'wsgi.py'
        
        # Load .env file if exists
        env_file = self.base_dir / '.env'
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env[key.strip()] = value.strip().strip('"\'')
        
        return env
    
    def start_service(self, service_name):
        """Start a specific service"""
        if service_name not in self.services:
            self.log(f"Unknown service: {service_name}")
            return False
        
        service = self.services[service_name]
        
        if service['process'] and service['process'].poll() is None:
            self.log(f"Service {service_name} is already running")
            return True
        
        try:
            self.log(f"Starting {service_name} service...")
            service['process'] = subprocess.Popen(
                service['command'],
                cwd=service['cwd'],
                env=service['env'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            
            # Wait a moment to check if it started successfully
            time.sleep(2)
            if service['process'].poll() is None:
                self.log(f"Service {service_name} started successfully (PID: {service['process'].pid})")
                return True
            else:
                self.log(f"Service {service_name} failed to start")
                return False
                
        except Exception as e:
            self.log(f"Error starting {service_name}: {str(e)}")
            return False
    
    def stop_service(self, service_name):
        """Stop a specific service"""
        if service_name not in self.services:
            self.log(f"Unknown service: {service_name}")
            return False
        
        service = self.services[service_name]
        
        if not service['process'] or service['process'].poll() is not None:
            self.log(f"Service {service_name} is not running")
            return True
        
        try:
            self.log(f"Stopping {service_name} service...")
            
            # Try graceful shutdown first
            service['process'].terminate()
            
            # Wait up to 10 seconds for graceful shutdown
            try:
                service['process'].wait(timeout=10)
                self.log(f"Service {service_name} stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown failed
                self.log(f"Service {service_name} didn't stop gracefully, killing...")
                os.killpg(os.getpgid(service['process'].pid), signal.SIGKILL)
                service['process'].wait()
                self.log(f"Service {service_name} killed")
            
            service['process'] = None
            return True
            
        except Exception as e:
            self.log(f"Error stopping {service_name}: {str(e)}")
            return False
    
    def restart_service(self, service_name):
        """Restart a specific service"""
        self.log(f"Restarting {service_name} service...")
        self.stop_service(service_name)
        time.sleep(2)
        return self.start_service(service_name)
    
    def start_all(self):
        """Start all services"""
        self.log("Starting MoxNAS services...")
        success = True
        
        for service_name, service in self.services.items():
            if not self.start_service(service_name):
                success = False
                if service['required']:
                    self.log(f"Failed to start required service: {service_name}")
                    return False
        
        if success:
            self.log("All MoxNAS services started successfully")
            self.running = True
        
        return success
    
    def stop_all(self):
        """Stop all services"""
        self.log("Stopping MoxNAS services...")
        self.running = False
        
        for service_name in self.services.keys():
            self.stop_service(service_name)
        
        self.log("All MoxNAS services stopped")
    
    def get_status(self):
        """Get status of all services"""
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'services': {},
            'overall': 'healthy'
        }
        
        healthy_count = 0
        total_count = len(self.services)
        
        for service_name, service in self.services.items():
            if service['process'] and service['process'].poll() is None:
                # Service is running, get additional info
                try:
                    proc = psutil.Process(service['process'].pid)
                    service_status = {
                        'status': 'running',
                        'pid': service['process'].pid,
                        'memory': proc.memory_info().rss,
                        'cpu_percent': proc.cpu_percent(),
                        'started': datetime.fromtimestamp(proc.create_time()).isoformat()
                    }
                    healthy_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    service_status = {
                        'status': 'unknown',
                        'pid': service['process'].pid
                    }
            else:
                service_status = {
                    'status': 'stopped',
                    'pid': None
                }
            
            status['services'][service_name] = service_status
        
        # Determine overall health
        if healthy_count == 0:
            status['overall'] = 'critical'
        elif healthy_count < total_count:
            status['overall'] = 'degraded'
        else:
            status['overall'] = 'healthy'
        
        return status
    
    def health_check(self):
        """Perform health check and restart failed services"""
        status = self.get_status()
        
        for service_name, service_status in status['services'].items():
            if service_status['status'] == 'stopped' and self.services[service_name]['required']:
                self.log(f"Service {service_name} is down, restarting...")
                self.start_service(service_name)
        
        return status
    
    def run_daemon(self):
        """Run as daemon with health monitoring"""
        self.log("Starting MoxNAS daemon...")
        
        if not self.start_all():
            self.log("Failed to start services, exiting")
            return 1
        
        # Install signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        try:
            while self.running:
                time.sleep(self.health_check_interval)
                if self.running:  # Check again in case we received signal
                    self.health_check()
        
        except KeyboardInterrupt:
            pass
        
        self.stop_all()
        self.log("MoxNAS daemon stopped")
        return 0
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.log(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def log(self, message):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")
        
        # Also log to file
        log_file = self.base_dir / 'logs' / 'moxnas-service.log'
        log_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass  # Don't fail if we can't write to log
    
    def show_logs(self, service_name=None, lines=50):
        """Show logs for services"""
        if service_name and service_name in self.services:
            service = self.services[service_name]
            if service['process']:
                # This would show recent output, but subprocess.PIPE doesn't store history
                # In production, you'd use proper logging to files
                self.log(f"Service {service_name} is running (PID: {service['process'].pid})")
            else:
                self.log(f"Service {service_name} is not running")
        else:
            # Show service status
            status = self.get_status()
            print(json.dumps(status, indent=2))

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python moxnas-service.py <command> [service_name]")
        print("Commands:")
        print("  start [service]    - Start service(s)")
        print("  stop [service]     - Stop service(s)")
        print("  restart [service]  - Restart service(s)")
        print("  status            - Show status")
        print("  daemon            - Run as daemon")
        print("  logs [service]    - Show logs")
        return 1
    
    service_manager = MoxNASService()
    command = sys.argv[1].lower()
    service_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    if command == 'start':
        if service_name:
            success = service_manager.start_service(service_name)
        else:
            success = service_manager.start_all()
        return 0 if success else 1
    
    elif command == 'stop':
        if service_name:
            success = service_manager.stop_service(service_name)
        else:
            service_manager.stop_all()
            success = True
        return 0 if success else 1
    
    elif command == 'restart':
        if service_name:
            success = service_manager.restart_service(service_name)
        else:
            service_manager.stop_all()
            time.sleep(2)
            success = service_manager.start_all()
        return 0 if success else 1
    
    elif command == 'status':
        status = service_manager.get_status()
        print(json.dumps(status, indent=2))
        return 0
    
    elif command == 'daemon':
        return service_manager.run_daemon()
    
    elif command == 'logs':
        service_manager.show_logs(service_name)
        return 0
    
    else:
        print(f"Unknown command: {command}")
        return 1

if __name__ == '__main__':
    sys.exit(main())