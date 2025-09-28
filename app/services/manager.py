"""System service management for NAS services"""
import subprocess
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from app.models import SystemLog, LogLevel


class ServiceStatus(Enum):
    """Service status enumeration"""

    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    """Service information container"""

    name: str
    status: ServiceStatus
    active: bool
    enabled: bool
    uptime: Optional[str] = None
    memory_usage: Optional[int] = None
    cpu_usage: Optional[float] = None
    pid: Optional[int] = None
    description: Optional[str] = None
    port: Optional[int] = None


class SystemServiceManager:
    """Manage system services (systemd) for NAS functionality"""

    def __init__(self):
        self.managed_services = {
            # Core NAS services
            "samba": {
                "services": ["smbd", "nmbd"],
                "description": "SMB/CIFS File Sharing",
                "config_file": "/etc/samba/smb.conf",
                "ports": [139, 445],
                "restart_dependencies": ["smbd", "nmbd"],
            },
            "nfs": {
                "services": ["nfs-kernel-server", "rpcbind", "nfs-common"],
                "description": "Network File System",
                "config_file": "/etc/exports",
                "ports": [2049, 111],
                "restart_dependencies": ["rpcbind", "nfs-kernel-server"],
            },
            "ftp": {
                "services": ["vsftpd"],
                "description": "FTP File Transfer",
                "config_file": "/etc/vsftpd.conf",
                "ports": [21, 22],
                "restart_dependencies": ["vsftpd"],
            },
            # Core system services
            "postgresql": {
                "services": ["postgresql"],
                "description": "Database Server",
                "config_file": "/etc/postgresql/*/main/postgresql.conf",
                "ports": [5432],
                "restart_dependencies": ["postgresql"],
            },
            "redis": {
                "services": ["redis-server"],
                "description": "Cache and Message Broker",
                "config_file": "/etc/redis/redis.conf",
                "ports": [6379],
                "restart_dependencies": ["redis-server"],
            },
            "nginx": {
                "services": ["nginx"],
                "description": "Web Server and Reverse Proxy",
                "config_file": "/etc/nginx/sites-available/moxnas",
                "ports": [80, 443],
                "restart_dependencies": ["nginx"],
            },
            "supervisor": {
                "services": ["supervisor"],
                "description": "Process Manager (MoxNAS App)",
                "config_file": "/etc/supervisor/conf.d/moxnas.conf",
                "ports": [],
                "restart_dependencies": ["supervisor"],
            },
            # Storage services
            "mdadm": {
                "services": ["mdmonitor"],
                "description": "RAID Array Monitoring",
                "config_file": "/etc/mdadm/mdadm.conf",
                "ports": [],
                "restart_dependencies": ["mdmonitor"],
            },
        }

    def run_command(self, command: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """Execute system command safely"""
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout, check=False
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def get_service_status(self, service_name: str) -> ServiceInfo:
        """Get detailed status of a systemd service"""
        try:
            # Get service status using systemctl
            success, stdout, stderr = self.run_command(
                [
                    "systemctl",
                    "show",
                    service_name,
                    "--property=ActiveState,SubState,LoadState,UnitFileState,MainPID,MemoryCurrent,ExecMainStartTimestamp",
                ]
            )

            if not success:
                return ServiceInfo(
                    name=service_name, status=ServiceStatus.UNKNOWN, active=False, enabled=False
                )

            # Parse systemctl output
            properties = {}
            for line in stdout.strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    properties[key] = value

            # Map systemctl states to our enum
            active_state = properties.get("ActiveState", "unknown")
            sub_state = properties.get("SubState", "unknown")
            unit_state = properties.get("UnitFileState", "unknown")

            status_map = {
                "active": ServiceStatus.RUNNING,
                "inactive": ServiceStatus.STOPPED,
                "failed": ServiceStatus.FAILED,
                "activating": ServiceStatus.STARTING,
                "deactivating": ServiceStatus.STOPPING,
            }

            status = status_map.get(active_state, ServiceStatus.UNKNOWN)
            active = active_state == "active"
            enabled = unit_state in ["enabled", "static", "indirect"]

            # Get additional info if service is running
            pid = None
            memory_usage = None
            uptime = None

            if properties.get("MainPID", "0") != "0":
                pid = int(properties["MainPID"])

            if properties.get("MemoryCurrent") and properties["MemoryCurrent"] != "[not set]":
                try:
                    memory_usage = int(properties["MemoryCurrent"])
                except ValueError:
                    pass

            if properties.get("ExecMainStartTimestamp"):
                start_time = properties["ExecMainStartTimestamp"]
                if start_time != "0":
                    # Calculate uptime (simplified)
                    uptime = "Running"

            # Get service description
            desc_success, desc_stdout, _ = self.run_command(
                ["systemctl", "show", service_name, "--property=Description"]
            )
            description = None
            if desc_success and "=" in desc_stdout:
                description = desc_stdout.split("=", 1)[1].strip()

            return ServiceInfo(
                name=service_name,
                status=status,
                active=active,
                enabled=enabled,
                uptime=uptime,
                memory_usage=memory_usage,
                pid=pid,
                description=description,
            )

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="services",
                message=f"Failed to get status for service {service_name}: {str(e)}",
            )
            return ServiceInfo(
                name=service_name, status=ServiceStatus.UNKNOWN, active=False, enabled=False
            )

    def start_service(self, service_name: str) -> Tuple[bool, str]:
        """Start a systemd service"""
        try:
            success, stdout, stderr = self.run_command(["systemctl", "start", service_name])

            if success:
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="services",
                    message=f"Successfully started service: {service_name}",
                )
                return True, f"Service {service_name} started successfully"
            else:
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="services",
                    message=f"Failed to start service {service_name}: {stderr}",
                )
                return False, f"Failed to start service {service_name}: {stderr}"

        except Exception as e:
            error_msg = f"Error starting service {service_name}: {str(e)}"
            SystemLog.log_event(level=LogLevel.ERROR, category="services", message=error_msg)
            return False, error_msg

    def stop_service(self, service_name: str) -> Tuple[bool, str]:
        """Stop a systemd service"""
        try:
            success, stdout, stderr = self.run_command(["systemctl", "stop", service_name])

            if success:
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="services",
                    message=f"Successfully stopped service: {service_name}",
                )
                return True, f"Service {service_name} stopped successfully"
            else:
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="services",
                    message=f"Failed to stop service {service_name}: {stderr}",
                )
                return False, f"Failed to stop service {service_name}: {stderr}"

        except Exception as e:
            error_msg = f"Error stopping service {service_name}: {str(e)}"
            SystemLog.log_event(level=LogLevel.ERROR, category="services", message=error_msg)
            return False, error_msg

    def restart_service(self, service_name: str) -> Tuple[bool, str]:
        """Restart a systemd service"""
        try:
            success, stdout, stderr = self.run_command(["systemctl", "restart", service_name])

            if success:
                # Wait a moment for service to stabilize
                time.sleep(2)

                # Verify service is running
                status = self.get_service_status(service_name)
                if status.active:
                    SystemLog.log_event(
                        level=LogLevel.INFO,
                        category="services",
                        message=f"Successfully restarted service: {service_name}",
                    )
                    return True, f"Service {service_name} restarted successfully"
                else:
                    return False, f"Service {service_name} failed to start after restart"
            else:
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="services",
                    message=f"Failed to restart service {service_name}: {stderr}",
                )
                return False, f"Failed to restart service {service_name}: {stderr}"

        except Exception as e:
            error_msg = f"Error restarting service {service_name}: {str(e)}"
            SystemLog.log_event(level=LogLevel.ERROR, category="services", message=error_msg)
            return False, error_msg

    def enable_service(self, service_name: str) -> Tuple[bool, str]:
        """Enable a systemd service to start at boot"""
        try:
            success, stdout, stderr = self.run_command(["systemctl", "enable", service_name])

            if success:
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="services",
                    message=f"Successfully enabled service: {service_name}",
                )
                return True, f"Service {service_name} enabled for startup"
            else:
                return False, f"Failed to enable service {service_name}: {stderr}"

        except Exception as e:
            return False, f"Error enabling service {service_name}: {str(e)}"

    def disable_service(self, service_name: str) -> Tuple[bool, str]:
        """Disable a systemd service from starting at boot"""
        try:
            success, stdout, stderr = self.run_command(["systemctl", "disable", service_name])

            if success:
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="services",
                    message=f"Successfully disabled service: {service_name}",
                )
                return True, f"Service {service_name} disabled from startup"
            else:
                return False, f"Failed to disable service {service_name}: {stderr}"

        except Exception as e:
            return False, f"Error disabling service {service_name}: {str(e)}"

    def reload_service(self, service_name: str) -> Tuple[bool, str]:
        """Reload a systemd service configuration"""
        try:
            success, stdout, stderr = self.run_command(["systemctl", "reload", service_name])

            if success:
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="services",
                    message=f"Successfully reloaded service: {service_name}",
                )
                return True, f"Service {service_name} configuration reloaded"
            else:
                # If reload fails, try restart as fallback
                return self.restart_service(service_name)

        except Exception as e:
            return False, f"Error reloading service {service_name}: {str(e)}"

    def get_all_nas_services_status(self) -> Dict[str, Dict[str, ServiceInfo]]:
        """Get status of all NAS-related services"""
        services_status = {}

        for category, config in self.managed_services.items():
            services_status[category] = {}

            for service_name in config["services"]:
                status = self.get_service_status(service_name)
                services_status[category][service_name] = status

        return services_status

    def get_service_logs(self, service_name: str, lines: int = 50) -> Tuple[bool, List[str]]:
        """Get recent logs for a service"""
        try:
            success, stdout, stderr = self.run_command(
                ["journalctl", "-u", service_name, "--no-pager", "-n", str(lines)]
            )

            if success:
                log_lines = stdout.split("\n")
                return True, [line for line in log_lines if line.strip()]
            else:
                return False, [f"Failed to get logs: {stderr}"]

        except Exception as e:
            return False, [f"Error getting logs: {str(e)}"]

    def restart_nas_service_group(self, service_group: str) -> Tuple[bool, str]:
        """Restart all services in a NAS service group"""
        if service_group not in self.managed_services:
            return False, f"Unknown service group: {service_group}"

        config = self.managed_services[service_group]
        services_to_restart = config["restart_dependencies"]

        results = []
        all_success = True

        # Stop services in reverse order
        for service_name in reversed(services_to_restart):
            success, message = self.stop_service(service_name)
            if not success:
                all_success = False
                results.append(f"Failed to stop {service_name}: {message}")

        # Wait a moment
        time.sleep(2)

        # Start services in forward order
        for service_name in services_to_restart:
            success, message = self.start_service(service_name)
            if not success:
                all_success = False
                results.append(f"Failed to start {service_name}: {message}")
            else:
                results.append(f"Started {service_name} successfully")

        if all_success:
            SystemLog.log_event(
                level=LogLevel.INFO,
                category="services",
                message=f"Successfully restarted {service_group} service group",
            )
            return True, f"{service_group.upper()} services restarted successfully"
        else:
            return False, "; ".join(results)

    def check_service_health(self, service_name: str) -> Tuple[bool, Dict]:
        """Perform comprehensive health check on a service"""
        health_info = {
            "service_name": service_name,
            "status": "unknown",
            "issues": [],
            "recommendations": [],
        }

        try:
            # Get service status
            status = self.get_service_status(service_name)
            health_info["status"] = status.status.value
            health_info["active"] = status.active
            health_info["enabled"] = status.enabled
            health_info["memory_usage"] = status.memory_usage
            health_info["pid"] = status.pid

            # Check for issues
            if not status.active:
                health_info["issues"].append("Service is not running")
                health_info["recommendations"].append("Start the service")

            if not status.enabled:
                health_info["issues"].append("Service is not enabled for startup")
                health_info["recommendations"].append("Enable the service for automatic startup")

            if status.status == ServiceStatus.FAILED:
                health_info["issues"].append("Service is in failed state")
                health_info["recommendations"].append("Check service logs and restart")

                # Get recent error logs
                success, logs = self.get_service_logs(service_name, 10)
                if success:
                    error_logs = [
                        log for log in logs if "error" in log.lower() or "fail" in log.lower()
                    ]
                    if error_logs:
                        health_info["recent_errors"] = error_logs[:5]

            # Check memory usage if available
            if status.memory_usage and status.memory_usage > 1024 * 1024 * 1024:  # 1GB
                health_info["issues"].append("High memory usage detected")
                health_info["recommendations"].append(
                    "Monitor memory usage and consider service restart"
                )

            # Service-specific checks
            if service_name in ["smbd", "nmbd"]:
                # Check SMB configuration
                success, stdout, stderr = self.run_command(["testparm", "-s"])
                if not success:
                    health_info["issues"].append("SMB configuration has errors")
                    health_info["recommendations"].append("Fix SMB configuration file")

            elif service_name == "nfs-kernel-server":
                # Check NFS exports
                success, stdout, stderr = self.run_command(["exportfs", "-v"])
                if not success:
                    health_info["issues"].append("NFS exports configuration has issues")
                    health_info["recommendations"].append("Check /etc/exports file")

            elif service_name == "postgresql":
                # Check database connectivity
                success, stdout, stderr = self.run_command(["pg_isready"])
                if not success:
                    health_info["issues"].append("Database is not accepting connections")
                    health_info["recommendations"].append("Check PostgreSQL logs and configuration")

            # Overall health assessment
            if len(health_info["issues"]) == 0:
                health_info["overall_health"] = "healthy"
            elif len(health_info["issues"]) <= 2:
                health_info["overall_health"] = "warning"
            else:
                health_info["overall_health"] = "critical"

            return True, health_info

        except Exception as e:
            health_info["issues"].append(f"Health check failed: {str(e)}")
            health_info["overall_health"] = "unknown"
            return False, health_info

    def get_port_status(self, port: int) -> bool:
        """Check if a port is listening"""
        try:
            success, stdout, stderr = self.run_command(["netstat", "-tlnp"])
            if success:
                return f":{port} " in stdout
            return False
        except Exception:
            return False

    def get_service_dependencies(self, service_name: str) -> List[str]:
        """Get service dependencies"""
        try:
            success, stdout, stderr = self.run_command(
                ["systemctl", "list-dependencies", service_name, "--plain"]
            )

            if success:
                dependencies = []
                for line in stdout.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("●") and ".service" in line:
                        dep_name = line.replace("├─", "").replace("└─", "").strip()
                        if dep_name != service_name:
                            dependencies.append(dep_name)
                return dependencies
            return []
        except Exception:
            return []


# Global service manager instance
service_manager = SystemServiceManager()
