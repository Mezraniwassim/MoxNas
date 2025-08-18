#!/usr/bin/env python3
"""
Service management utilities for MoxNAS
"""

import subprocess
import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceManager:
    """Service management utility class"""
    
    MANAGED_SERVICES = [
        'samba', 'smbd', 'nmbd',
        'nfs-kernel-server', 'rpcbind',
        'vsftpd',
        'nginx',
        'moxnas',
        'moxnas-monitor'
    ]
    
    def __init__(self):
        self.logger = logger
    
    def run_command(self, command, check=True):
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
    
    def get_service_status(self, service_name):
        """Get detailed status of a service"""
        # Get basic status
        returncode, output, error = self.run_command(
            ['systemctl', 'is-active', service_name], 
            check=False
        )
        active = output.strip() == 'active'
        
        # Get enabled status
        returncode, output, error = self.run_command(
            ['systemctl', 'is-enabled', service_name], 
            check=False
        )
        enabled = output.strip() == 'enabled'
        
        # Get detailed status
        returncode, status_output, error = self.run_command(
            ['systemctl', 'status', service_name, '--no-pager'], 
            check=False
        )
        
        # Get memory usage
        memory_usage = self._get_service_memory(service_name)
        
        return {
            'name': service_name,
            'active': active,
            'enabled': enabled,
            'status_output': status_output,
            'memory_usage': memory_usage
        }
    
    def _get_service_memory(self, service_name):
        """Get memory usage for a service"""
        try:
            returncode, output, error = self.run_command(
                ['systemctl', 'show', service_name, '--property=MemoryCurrent'],
                check=False
            )
            if returncode == 0 and 'MemoryCurrent=' in output:
                memory_bytes = output.split('=')[1].strip()
                if memory_bytes.isdigit():
                    return int(memory_bytes)
        except:
            pass
        return 0
    
    def start_service(self, service_name):
        """Start a service"""
        returncode, output, error = self.run_command(
            ['systemctl', 'start', service_name]
        )
        
        if returncode == 0:
            self.logger.info(f"Successfully started service: {service_name}")
            return True, f"Service {service_name} started successfully"
        else:
            self.logger.error(f"Failed to start service {service_name}: {error}")
            return False, error
    
    def stop_service(self, service_name):
        """Stop a service"""
        returncode, output, error = self.run_command(
            ['systemctl', 'stop', service_name]
        )
        
        if returncode == 0:
            self.logger.info(f"Successfully stopped service: {service_name}")
            return True, f"Service {service_name} stopped successfully"
        else:
            self.logger.error(f"Failed to stop service {service_name}: {error}")
            return False, error
    
    def restart_service(self, service_name):
        """Restart a service"""
        returncode, output, error = self.run_command(
            ['systemctl', 'restart', service_name]
        )
        
        if returncode == 0:
            self.logger.info(f"Successfully restarted service: {service_name}")
            return True, f"Service {service_name} restarted successfully"
        else:
            self.logger.error(f"Failed to restart service {service_name}: {error}")
            return False, error
    
    def enable_service(self, service_name):
        """Enable a service to start at boot"""
        returncode, output, error = self.run_command(
            ['systemctl', 'enable', service_name]
        )
        
        if returncode == 0:
            self.logger.info(f"Successfully enabled service: {service_name}")
            return True, f"Service {service_name} enabled successfully"
        else:
            self.logger.error(f"Failed to enable service {service_name}: {error}")
            return False, error
    
    def disable_service(self, service_name):
        """Disable a service from starting at boot"""
        returncode, output, error = self.run_command(
            ['systemctl', 'disable', service_name]
        )
        
        if returncode == 0:
            self.logger.info(f"Successfully disabled service: {service_name}")
            return True, f"Service {service_name} disabled successfully"
        else:
            self.logger.error(f"Failed to disable service {service_name}: {error}")
            return False, error
    
    def get_service_logs(self, service_name, lines=50):
        """Get recent logs for a service"""
        returncode, output, error = self.run_command(
            ['journalctl', '-u', service_name, '-n', str(lines), '--no-pager'],
            check=False
        )
        
        if returncode == 0:
            return output
        else:
            return f"Error getting logs: {error}"
    
    def get_all_services_status(self):
        """Get status of all managed services"""
        services_status = []
        
        for service in self.MANAGED_SERVICES:
            status = self.get_service_status(service)
            services_status.append(status)
        
        return services_status
    
    def check_port_usage(self, port):
        """Check if a port is in use"""
        returncode, output, error = self.run_command(
            ['ss', '-tlnp', f'sport = :{port}'],
            check=False
        )
        
        return len(output.strip().split('\n')) > 1
    
    def get_listening_ports(self):
        """Get all listening ports"""
        returncode, output, error = self.run_command(
            ['ss', '-tlnp'],
            check=False
        )
        
        ports = []
        if returncode == 0:
            lines = output.strip().split('\n')[1:]  # Skip header
            for line in lines:
                parts = line.split()
                if len(parts) >= 4:
                    local_address = parts[3]
                    if ':' in local_address:
                        port = local_address.split(':')[-1]
                        if port.isdigit():
                            ports.append({
                                'port': int(port),
                                'address': local_address,
                                'process': parts[-1] if len(parts) > 6 else 'unknown'
                            })
        
        return ports
    
    def setup_service_dependencies(self):
        """Setup dependencies for MoxNAS services"""
        # Reload systemd
        self.run_command(['systemctl', 'daemon-reload'])
        
        # Enable core services
        core_services = ['nginx', 'moxnas']
        for service in core_services:
            try:
                self.enable_service(service)
            except:
                self.logger.warning(f"Could not enable service: {service}")


def main():
    """Command line interface for service manager"""
    if len(sys.argv) < 2:
        print("Usage: service-manager.py <command> [args...]")
        print("Commands:")
        print("  status [service]        - Get service status")
        print("  start <service>         - Start service")
        print("  stop <service>          - Stop service")
        print("  restart <service>       - Restart service")
        print("  enable <service>        - Enable service")
        print("  disable <service>       - Disable service")
        print("  logs <service> [lines]  - Get service logs")
        print("  list                    - List all managed services")
        print("  ports                   - Show listening ports")
        sys.exit(1)
    
    manager = ServiceManager()
    command = sys.argv[1]
    
    if command == 'status':
        if len(sys.argv) > 2:
            service = sys.argv[2]
            status = manager.get_service_status(service)
            print(json.dumps(status, indent=2))
        else:
            statuses = manager.get_all_services_status()
            print(json.dumps(statuses, indent=2))
    
    elif command in ['start', 'stop', 'restart', 'enable', 'disable']:
        if len(sys.argv) != 3:
            print(f"Usage: service-manager.py {command} <service>")
            sys.exit(1)
        
        service = sys.argv[2]
        method = getattr(manager, f"{command}_service")
        success, message = method(service)
        print(message)
        sys.exit(0 if success else 1)
    
    elif command == 'logs':
        if len(sys.argv) < 3:
            print("Usage: service-manager.py logs <service> [lines]")
            sys.exit(1)
        
        service = sys.argv[2]
        lines = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        logs = manager.get_service_logs(service, lines)
        print(logs)
    
    elif command == 'list':
        print("Managed services:")
        for service in manager.MANAGED_SERVICES:
            print(f"  - {service}")
    
    elif command == 'ports':
        ports = manager.get_listening_ports()
        print("Listening ports:")
        for port_info in ports:
            print(f"  {port_info['port']} - {port_info['address']} ({port_info['process']})")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()