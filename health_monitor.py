#!/usr/bin/env python3
"""
MoxNAS Service Health Monitor
Monitors critical services and system health, provides recovery mechanisms
"""
import os
import sys
import time
import json
import logging
import subprocess
import psutil
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add app directory to path
sys.path.insert(0, '/opt/moxnas')

from app import create_app, db
from app.models import Alert, AlertSeverity, SystemHealth

class HealthMonitor:
    """System health monitoring service"""
    
    def __init__(self):
        self.app = create_app()
        self.setup_logging()
        self.services = [
            'postgresql',
            'redis-server',
            'nginx',
            'supervisor',
            'smbd',
            'nmbd',
            'nfs-kernel-server',
            'vsftpd'
        ]
        self.critical_services = ['postgresql', 'redis-server', 'supervisor']
        self.max_restart_attempts = 3
        self.restart_attempts = {}
        
    def setup_logging(self):
        """Configure logging"""
        log_dir = Path('/opt/moxnas/logs')
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'health_monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def check_service_status(self, service: str) -> Tuple[bool, str]:
        """Check if a systemd service is running"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True,
                text=True,
                timeout=10
            )
            status = result.stdout.strip()
            return status == 'active', status
        except Exception as e:
            return False, str(e)
    
    def check_port(self, port: int, host: str = '127.0.0.1') -> bool:
        """Check if a port is listening"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False
    
    def check_web_service(self) -> Tuple[bool, str]:
        """Check if the web service is responding"""
        try:
            response = requests.get(
                'http://127.0.0.1:5000/health',
                timeout=10
            )
            if response.status_code == 200:
                return True, "OK"
            else:
                return False, f"HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, str(e)
    
    def check_database_connection(self) -> Tuple[bool, str]:
        """Check database connectivity"""
        try:
            with self.app.app_context():
                db.session.execute('SELECT 1')
                return True, "Connected"
        except Exception as e:
            return False, str(e)
    
    def check_redis_connection(self) -> Tuple[bool, str]:
        """Check Redis connectivity"""
        try:
            import redis
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            client = redis.from_url(redis_url)
            client.ping()
            return True, "Connected"
        except Exception as e:
            return False, str(e)
    
    def check_storage_health(self) -> Tuple[bool, List[str]]:
        """Check storage system health"""
        issues = []
        
        # Check storage mounts
        critical_mounts = ['/mnt/storage', '/mnt/backups']
        for mount in critical_mounts:
            if not os.path.ismount(mount) and os.path.exists(mount):
                issues.append(f"Mount point {mount} is not mounted")
        
        # Check disk space
        for mount in critical_mounts:
            if os.path.exists(mount):
                usage = psutil.disk_usage(mount)
                used_percent = (usage.used / usage.total) * 100
                if used_percent > 95:
                    issues.append(f"Disk space critical on {mount}: {used_percent:.1f}% used")
                elif used_percent > 85:
                    issues.append(f"Disk space warning on {mount}: {used_percent:.1f}% used")
        
        # Check RAID status if available
        try:
            result = subprocess.run(['mdstat'], capture_output=True, text=True)
            if result.returncode == 0:
                mdstat_content = result.stdout
                if 'failed' in mdstat_content.lower() or 'degraded' in mdstat_content.lower():
                    issues.append("RAID array issues detected")
        except Exception:
            pass
        
        return len(issues) == 0, issues
    
    def check_system_resources(self) -> Tuple[bool, List[str]]:
        """Check system resource usage"""
        issues = []
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90:
            issues.append(f"High CPU usage: {cpu_percent}%")
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            issues.append(f"High memory usage: {memory.percent}%")
        
        # Check load average
        load_avg = os.getloadavg()
        cpu_count = psutil.cpu_count()
        if load_avg[0] > cpu_count * 2:
            issues.append(f"High system load: {load_avg[0]}")
        
        # Check swap usage
        swap = psutil.swap_memory()
        if swap.percent > 50:
            issues.append(f"High swap usage: {swap.percent}%")
        
        return len(issues) == 0, issues
    
    def restart_service(self, service: str) -> bool:
        """Attempt to restart a failed service"""
        if service not in self.restart_attempts:
            self.restart_attempts[service] = 0
        
        if self.restart_attempts[service] >= self.max_restart_attempts:
            self.logger.error(f"Service {service} has reached maximum restart attempts")
            return False
        
        try:
            self.logger.info(f"Attempting to restart service: {service}")
            result = subprocess.run(
                ['systemctl', 'restart', service],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.restart_attempts[service] = 0
                self.logger.info(f"Service {service} restarted successfully")
                
                # Wait a moment for service to stabilize
                time.sleep(5)
                
                # Verify service is running
                is_active, status = self.check_service_status(service)
                if is_active:
                    return True
                else:
                    self.logger.error(f"Service {service} failed to start after restart: {status}")
                    return False
            else:
                self.restart_attempts[service] += 1
                self.logger.error(f"Failed to restart service {service}: {result.stderr}")
                return False
                
        except Exception as e:
            self.restart_attempts[service] += 1
            self.logger.error(f"Exception while restarting service {service}: {e}")
            return False
    
    def create_alert(self, title: str, message: str, severity: AlertSeverity):
        """Create system alert"""
        try:
            with self.app.app_context():
                alert = Alert(
                    title=title,
                    message=message,
                    severity=severity,
                    component='system_monitor'
                )
                db.session.add(alert)
                db.session.commit()
        except Exception as e:
            self.logger.error(f"Failed to create alert: {e}")
    
    def update_system_health(self, status: Dict):
        """Update system health status in database"""
        try:
            with self.app.app_context():
                health = SystemHealth(
                    cpu_usage=status.get('cpu_usage', 0),
                    memory_usage=status.get('memory_usage', 0),
                    disk_usage=status.get('disk_usage', 0),
                    load_average=status.get('load_average', 0),
                    services_status=json.dumps(status.get('services', {})),
                    alerts_count=status.get('alerts_count', 0)
                )
                db.session.add(health)
                
                # Clean up old health records (keep only last 24 hours)
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                db.session.query(SystemHealth).filter(
                    SystemHealth.timestamp < cutoff_time
                ).delete()
                
                db.session.commit()
        except Exception as e:
            self.logger.error(f"Failed to update system health: {e}")
    
    def run_health_check(self) -> Dict:
        """Run comprehensive health check"""
        self.logger.info("Starting health check...")
        
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'services': {},
            'database': None,
            'redis': None,
            'web': None,
            'storage': None,
            'resources': None,
            'overall_status': 'healthy',
            'issues': [],
            'alerts_count': 0
        }
        
        # Check system services
        for service in self.services:
            is_active, status = self.check_service_status(service)
            health_status['services'][service] = {
                'active': is_active,
                'status': status
            }
            
            if not is_active:
                health_status['issues'].append(f"Service {service} is {status}")
                
                if service in self.critical_services:
                    health_status['overall_status'] = 'critical'
                    self.logger.error(f"Critical service {service} is down: {status}")
                    
                    # Attempt to restart critical services
                    if self.restart_service(service):
                        self.logger.info(f"Successfully restarted critical service: {service}")
                        health_status['services'][service]['active'] = True
                        health_status['services'][service]['status'] = 'restarted'
                        # Remove from issues since it's now fixed
                        if f"Service {service} is {status}" in health_status['issues']:
                            health_status['issues'].remove(f"Service {service} is {status}")
                    else:
                        self.create_alert(
                            f"Critical Service Failed: {service}",
                            f"Service {service} is down and failed to restart",
                            AlertSeverity.CRITICAL
                        )
                        health_status['alerts_count'] += 1
                elif health_status['overall_status'] != 'critical':
                    health_status['overall_status'] = 'warning'
        
        # Check database connection
        db_healthy, db_status = self.check_database_connection()
        health_status['database'] = {'healthy': db_healthy, 'status': db_status}
        if not db_healthy:
            health_status['issues'].append(f"Database connection failed: {db_status}")
            health_status['overall_status'] = 'critical'
            self.create_alert(
                "Database Connection Failed",
                f"Cannot connect to database: {db_status}",
                AlertSeverity.CRITICAL
            )
            health_status['alerts_count'] += 1
        
        # Check Redis connection
        redis_healthy, redis_status = self.check_redis_connection()
        health_status['redis'] = {'healthy': redis_healthy, 'status': redis_status}
        if not redis_healthy:
            health_status['issues'].append(f"Redis connection failed: {redis_status}")
            if health_status['overall_status'] != 'critical':
                health_status['overall_status'] = 'warning'
        
        # Check web service
        web_healthy, web_status = self.check_web_service()
        health_status['web'] = {'healthy': web_healthy, 'status': web_status}
        if not web_healthy:
            health_status['issues'].append(f"Web service check failed: {web_status}")
            if health_status['overall_status'] != 'critical':
                health_status['overall_status'] = 'warning'
        
        # Check storage health
        storage_healthy, storage_issues = self.check_storage_health()
        health_status['storage'] = {'healthy': storage_healthy, 'issues': storage_issues}
        if not storage_healthy:
            health_status['issues'].extend(storage_issues)
            if any('critical' in issue.lower() for issue in storage_issues):
                health_status['overall_status'] = 'critical'
                for issue in storage_issues:
                    if 'critical' in issue.lower():
                        self.create_alert(
                            "Critical Storage Issue",
                            issue,
                            AlertSeverity.CRITICAL
                        )
                        health_status['alerts_count'] += 1
            elif health_status['overall_status'] != 'critical':
                health_status['overall_status'] = 'warning'
        
        # Check system resources
        resources_healthy, resource_issues = self.check_system_resources()
        health_status['resources'] = {'healthy': resources_healthy, 'issues': resource_issues}
        if not resources_healthy:
            health_status['issues'].extend(resource_issues)
            if health_status['overall_status'] != 'critical':
                health_status['overall_status'] = 'warning'
        
        # Add system metrics
        health_status['cpu_usage'] = psutil.cpu_percent()
        health_status['memory_usage'] = psutil.virtual_memory().percent
        
        # Calculate average disk usage
        disk_usages = []
        for mount in ['/mnt/storage', '/mnt/backups', '/']:
            if os.path.exists(mount):
                usage = psutil.disk_usage(mount)
                disk_usages.append((usage.used / usage.total) * 100)
        health_status['disk_usage'] = sum(disk_usages) / len(disk_usages) if disk_usages else 0
        health_status['load_average'] = os.getloadavg()[0]
        
        # Update database with health status
        self.update_system_health(health_status)
        
        self.logger.info(f"Health check completed. Status: {health_status['overall_status']}")
        if health_status['issues']:
            self.logger.warning(f"Issues found: {health_status['issues']}")
        
        return health_status
    
    def run_continuous_monitoring(self, interval: int = 60):
        """Run continuous health monitoring"""
        self.logger.info(f"Starting continuous health monitoring (interval: {interval}s)")
        
        while True:
            try:
                health_status = self.run_health_check()
                
                # Write status to file for external monitoring
                status_file = Path('/opt/moxnas/health_status.json')
                with open(status_file, 'w') as f:
                    json.dump(health_status, f, indent=2)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.logger.info("Health monitoring stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                time.sleep(interval)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MoxNAS Health Monitor')
    parser.add_argument('--check', action='store_true', help='Run single health check')
    parser.add_argument('--monitor', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    
    args = parser.parse_args()
    
    monitor = HealthMonitor()
    
    if args.daemon:
        # Daemonize the process
        import daemon
        import lockfile
        
        pidfile = lockfile.FileLock('/var/run/moxnas-health-monitor.pid')
        
        with daemon.DaemonContext(pidfile=pidfile):
            monitor.run_continuous_monitoring(args.interval)
    
    elif args.monitor:
        monitor.run_continuous_monitoring(args.interval)
    
    elif args.check:
        status = monitor.run_health_check()
        print(json.dumps(status, indent=2))
        
        # Exit with appropriate code
        if status['overall_status'] == 'critical':
            sys.exit(2)
        elif status['overall_status'] == 'warning':
            sys.exit(1)
        else:
            sys.exit(0)
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()