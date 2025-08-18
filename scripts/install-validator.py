#!/usr/bin/env python3
"""
Installation validation utilities for MoxNAS
"""

import subprocess
import json
import logging
import sys
import os
from pathlib import Path
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InstallValidator:
    """Installation validation utility class"""
    
    REQUIRED_PACKAGES = [
        'python3', 'python3-pip', 'python3-venv',
        'nodejs', 'npm',
        'nginx',
        'sqlite3',
        'git', 'curl', 'wget', 'unzip',
        'samba', 'nfs-kernel-server', 'vsftpd'
    ]
    
    REQUIRED_DIRECTORIES = [
        '/opt/moxnas',
        '/opt/moxnas/backend',
        '/opt/moxnas/frontend',
        '/opt/moxnas/venv',
        '/var/log/moxnas',
        '/var/lib/moxnas'
    ]
    
    REQUIRED_SERVICES = [
        'nginx',
        'moxnas'
    ]
    
    REQUIRED_PORTS = [
        {'port': 8000, 'service': 'MoxNAS Web Interface'},
        {'port': 80, 'service': 'Nginx (optional)'},
        {'port': 445, 'service': 'Samba SMB'},
        {'port': 2049, 'service': 'NFS'},
        {'port': 21, 'service': 'FTP'}
    ]
    
    def __init__(self):
        self.logger = logger
        self.validation_results = {
            'packages': {},
            'directories': {},
            'services': {},
            'ports': {},
            'permissions': {},
            'configuration': {},
            'connectivity': {}
        }
    
    def run_command(self, command, check=False):
        """Run a system command and return the result"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=check
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return e.returncode, e.stdout, e.stderr
        except FileNotFoundError:
            return 127, '', f'Command not found: {command[0]}'
    
    def validate_packages(self):
        """Validate required packages are installed"""
        self.logger.info("Validating required packages...")
        
        for package in self.REQUIRED_PACKAGES:
            # Check if package is installed
            if package in ['python3', 'python3-pip', 'python3-venv']:
                # Check Python packages
                returncode, output, error = self.run_command(['which', package.replace('python3-', '')])
                installed = returncode == 0
            elif package in ['nodejs', 'npm']:
                # Check Node.js packages
                returncode, output, error = self.run_command(['which', package])
                installed = returncode == 0
            else:
                # Check system packages via dpkg
                returncode, output, error = self.run_command(['dpkg', '-l', package])
                installed = returncode == 0 and f'ii  {package}' in output
            
            self.validation_results['packages'][package] = {
                'installed': installed,
                'required': True
            }
            
            if installed:
                self.logger.info(f"✓ Package {package} is installed")
            else:
                self.logger.warning(f"✗ Package {package} is NOT installed")
    
    def validate_directories(self):
        """Validate required directories exist with correct permissions"""
        self.logger.info("Validating required directories...")
        
        for directory in self.REQUIRED_DIRECTORIES:
            path = Path(directory)
            exists = path.exists()
            is_directory = path.is_dir() if exists else False
            
            # Check ownership
            owner = None
            group = None
            permissions = None
            
            if exists:
                try:
                    stat_info = path.stat()
                    permissions = oct(stat_info.st_mode)[-3:]
                    
                    # Get owner and group names
                    import pwd
                    import grp
                    owner = pwd.getpwuid(stat_info.st_uid).pw_name
                    group = grp.getgrgid(stat_info.st_gid).gr_name
                except Exception as e:
                    self.logger.warning(f"Could not get permissions for {directory}: {e}")
            
            self.validation_results['directories'][directory] = {
                'exists': exists,
                'is_directory': is_directory,
                'owner': owner,
                'group': group,
                'permissions': permissions
            }
            
            if exists and is_directory:
                self.logger.info(f"✓ Directory {directory} exists")
            else:
                self.logger.warning(f"✗ Directory {directory} does NOT exist or is not a directory")
    
    def validate_services(self):
        """Validate required services are configured and running"""
        self.logger.info("Validating required services...")
        
        for service in self.REQUIRED_SERVICES:
            # Check if service exists
            returncode, output, error = self.run_command(['systemctl', 'cat', service])
            exists = returncode == 0
            
            # Check if service is enabled
            returncode, output, error = self.run_command(['systemctl', 'is-enabled', service])
            enabled = output.strip() == 'enabled'
            
            # Check if service is active
            returncode, output, error = self.run_command(['systemctl', 'is-active', service])
            active = output.strip() == 'active'
            
            self.validation_results['services'][service] = {
                'exists': exists,
                'enabled': enabled,
                'active': active
            }
            
            if exists and enabled and active:
                self.logger.info(f"✓ Service {service} is properly configured and running")
            else:
                self.logger.warning(f"✗ Service {service} has issues - exists: {exists}, enabled: {enabled}, active: {active}")
    
    def validate_ports(self):
        """Validate required ports are available or in use by correct services"""
        self.logger.info("Validating port availability...")
        
        # Get all listening ports
        returncode, output, error = self.run_command(['ss', '-tlnp'])
        listening_ports = set()
        
        if returncode == 0:
            lines = output.strip().split('\n')[1:]  # Skip header
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    local_address = parts[3]
                    if ':' in local_address:
                        port = local_address.split(':')[-1]
                        if port.isdigit():
                            listening_ports.add(int(port))
        
        for port_info in self.REQUIRED_PORTS:
            port = port_info['port']
            service_name = port_info['service']
            
            is_listening = port in listening_ports
            
            self.validation_results['ports'][port] = {
                'service': service_name,
                'listening': is_listening,
                'required': port in [8000]  # Only web interface is strictly required
            }
            
            if port == 8000:  # Web interface port is critical
                if is_listening:
                    self.logger.info(f"✓ Port {port} ({service_name}) is listening")
                else:
                    self.logger.warning(f"✗ Port {port} ({service_name}) is NOT listening")
            else:
                self.logger.info(f"Port {port} ({service_name}) - listening: {is_listening}")
    
    def validate_web_interface(self):
        """Validate web interface is accessible"""
        self.logger.info("Validating web interface connectivity...")
        
        test_urls = [
            'http://localhost:8000',
            'http://127.0.0.1:8000'
        ]
        
        for url in test_urls:
            try:
                response = requests.get(url, timeout=10)
                accessible = response.status_code == 200
                
                self.validation_results['connectivity'][url] = {
                    'accessible': accessible,
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds()
                }
                
                if accessible:
                    self.logger.info(f"✓ Web interface accessible at {url}")
                else:
                    self.logger.warning(f"✗ Web interface returned status {response.status_code} at {url}")
                    
            except requests.exceptions.RequestException as e:
                self.validation_results['connectivity'][url] = {
                    'accessible': False,
                    'error': str(e)
                }
                self.logger.warning(f"✗ Web interface NOT accessible at {url}: {e}")
    
    def validate_database(self):
        """Validate database connectivity"""
        self.logger.info("Validating database...")
        
        db_path = Path('/opt/moxnas/backend/db.sqlite3')
        
        self.validation_results['configuration']['database'] = {
            'exists': db_path.exists(),
            'readable': False,
            'writable': False
        }
        
        if db_path.exists():
            self.validation_results['configuration']['database']['readable'] = os.access(db_path, os.R_OK)
            self.validation_results['configuration']['database']['writable'] = os.access(db_path, os.W_OK)
            
            if self.validation_results['configuration']['database']['readable']:
                self.logger.info("✓ Database file exists and is readable")
            else:
                self.logger.warning("✗ Database file exists but is not readable")
        else:
            self.logger.warning("✗ Database file does not exist")
    
    def validate_python_environment(self):
        """Validate Python virtual environment"""
        self.logger.info("Validating Python environment...")
        
        venv_path = Path('/opt/moxnas/venv')
        python_path = venv_path / 'bin' / 'python'
        pip_path = venv_path / 'bin' / 'pip'
        
        self.validation_results['configuration']['python_venv'] = {
            'venv_exists': venv_path.exists(),
            'python_exists': python_path.exists(),
            'pip_exists': pip_path.exists(),
            'packages_installed': False
        }
        
        if python_path.exists():
            # Check if required packages are installed
            returncode, output, error = self.run_command([str(pip_path), 'list'])
            required_packages = ['django', 'djangorestframework', 'gunicorn']
            packages_found = 0
            
            for package in required_packages:
                if package.lower() in output.lower():
                    packages_found += 1
            
            self.validation_results['configuration']['python_venv']['packages_installed'] = packages_found >= len(required_packages)
            
            if packages_found >= len(required_packages):
                self.logger.info("✓ Python virtual environment is properly configured")
            else:
                self.logger.warning(f"✗ Python virtual environment missing packages ({packages_found}/{len(required_packages)})")
        else:
            self.logger.warning("✗ Python virtual environment not found")
    
    def run_full_validation(self):
        """Run complete validation suite"""
        self.logger.info("Starting MoxNAS installation validation...")
        
        self.validate_packages()
        self.validate_directories()
        self.validate_services()
        self.validate_ports()
        self.validate_web_interface()
        self.validate_database()
        self.validate_python_environment()
        
        return self.validation_results
    
    def generate_report(self):
        """Generate a validation report"""
        results = self.run_full_validation()
        
        # Count issues
        total_checks = 0
        passed_checks = 0
        failed_checks = 0
        
        # Package checks
        for package, result in results['packages'].items():
            total_checks += 1
            if result['installed']:
                passed_checks += 1
            else:
                failed_checks += 1
        
        # Directory checks
        for directory, result in results['directories'].items():
            total_checks += 1
            if result['exists'] and result['is_directory']:
                passed_checks += 1
            else:
                failed_checks += 1
        
        # Service checks
        for service, result in results['services'].items():
            total_checks += 1
            if result['exists'] and result['enabled'] and result['active']:
                passed_checks += 1
            else:
                failed_checks += 1
        
        # Critical port checks (only check required ports)
        for port, result in results['ports'].items():
            if result.get('required', False):
                total_checks += 1
                if result['listening']:
                    passed_checks += 1
                else:
                    failed_checks += 1
        
        report = {
            'validation_timestamp': subprocess.run(['date'], capture_output=True, text=True).stdout.strip(),
            'summary': {
                'total_checks': total_checks,
                'passed': passed_checks,
                'failed': failed_checks,
                'success_rate': round((passed_checks / total_checks) * 100, 2) if total_checks > 0 else 0
            },
            'results': results
        }
        
        return report


def main():
    """Command line interface for install validator"""
    if len(sys.argv) < 2:
        print("Usage: install-validator.py <command>")
        print("Commands:")
        print("  validate                - Run full validation")
        print("  packages               - Validate packages only")
        print("  directories            - Validate directories only")
        print("  services               - Validate services only")
        print("  ports                  - Validate ports only")
        print("  web                    - Validate web interface only")
        print("  report                 - Generate full report")
        sys.exit(1)
    
    validator = InstallValidator()
    command = sys.argv[1]
    
    if command == 'validate':
        results = validator.run_full_validation()
        print(json.dumps(results, indent=2))
    
    elif command == 'packages':
        validator.validate_packages()
        print(json.dumps(validator.validation_results['packages'], indent=2))
    
    elif command == 'directories':
        validator.validate_directories()
        print(json.dumps(validator.validation_results['directories'], indent=2))
    
    elif command == 'services':
        validator.validate_services()
        print(json.dumps(validator.validation_results['services'], indent=2))
    
    elif command == 'ports':
        validator.validate_ports()
        print(json.dumps(validator.validation_results['ports'], indent=2))
    
    elif command == 'web':
        validator.validate_web_interface()
        print(json.dumps(validator.validation_results['connectivity'], indent=2))
    
    elif command == 'report':
        report = validator.generate_report()
        print(json.dumps(report, indent=2))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()