"""API endpoints for service management"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.auth.decorators import admin_required
from app.services.manager import service_manager
from app.models import SystemLog, LogLevel
import json

bp = Blueprint("services_api", __name__)


@bp.route("/services/status", methods=["GET"])
@login_required
def get_services_status():
    """Get status of all NAS services"""
    try:
        services_status = service_manager.get_all_nas_services_status()

        # Convert ServiceInfo objects to dictionaries
        result = {}
        for category, services in services_status.items():
            result[category] = {}
            for service_name, service_info in services.items():
                result[category][service_name] = {
                    "name": service_info.name,
                    "status": service_info.status.value,
                    "active": service_info.active,
                    "enabled": service_info.enabled,
                    "uptime": service_info.uptime,
                    "memory_usage": service_info.memory_usage,
                    "pid": service_info.pid,
                    "description": service_info.description,
                }

        return jsonify({"success": True, "services": result})

    except Exception as e:
        current_app.logger.error(f"Failed to get services status: {str(e)}")
        return (
            jsonify({"success": False, "message": f"Failed to get services status: {str(e)}"}),
            500,
        )


@bp.route("/services/<service_name>/start", methods=["POST"])
@login_required
@admin_required
def start_service(service_name):
    """Start a specific service"""
    try:
        success, message = service_manager.start_service(service_name)

        if success:
            SystemLog.log_event(
                level=LogLevel.INFO,
                category="services",
                message=f"User {current_user.username} started service: {service_name}",
            )

        return jsonify({"success": success, "message": message})

    except Exception as e:
        current_app.logger.error(f"Failed to start service {service_name}: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to start service: {str(e)}"}), 500


@bp.route("/services/<service_name>/stop", methods=["POST"])
@login_required
@admin_required
def stop_service(service_name):
    """Stop a specific service"""
    try:
        success, message = service_manager.stop_service(service_name)

        if success:
            SystemLog.log_event(
                level=LogLevel.INFO,
                category="services",
                message=f"User {current_user.username} stopped service: {service_name}",
            )

        return jsonify({"success": success, "message": message})

    except Exception as e:
        current_app.logger.error(f"Failed to stop service {service_name}: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to stop service: {str(e)}"}), 500


@bp.route("/services/<service_name>/restart", methods=["POST"])
@login_required
@admin_required
def restart_service(service_name):
    """Restart a specific service"""
    try:
        success, message = service_manager.restart_service(service_name)

        if success:
            SystemLog.log_event(
                level=LogLevel.INFO,
                category="services",
                message=f"User {current_user.username} restarted service: {service_name}",
            )

        return jsonify({"success": success, "message": message})

    except Exception as e:
        current_app.logger.error(f"Failed to restart service {service_name}: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to restart service: {str(e)}"}), 500


@bp.route("/services/<service_name>/enable", methods=["POST"])
@login_required
@admin_required
def enable_service(service_name):
    """Enable a service for automatic startup"""
    try:
        success, message = service_manager.enable_service(service_name)

        if success:
            SystemLog.log_event(
                level=LogLevel.INFO,
                category="services",
                message=f"User {current_user.username} enabled service: {service_name}",
            )

        return jsonify({"success": success, "message": message})

    except Exception as e:
        current_app.logger.error(f"Failed to enable service {service_name}: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to enable service: {str(e)}"}), 500


@bp.route("/services/<service_name>/disable", methods=["POST"])
@login_required
@admin_required
def disable_service(service_name):
    """Disable a service from automatic startup"""
    try:
        success, message = service_manager.disable_service(service_name)

        if success:
            SystemLog.log_event(
                level=LogLevel.INFO,
                category="services",
                message=f"User {current_user.username} disabled service: {service_name}",
            )

        return jsonify({"success": success, "message": message})

    except Exception as e:
        current_app.logger.error(f"Failed to disable service {service_name}: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to disable service: {str(e)}"}), 500


@bp.route("/services/<service_name>/reload", methods=["POST"])
@login_required
@admin_required
def reload_service(service_name):
    """Reload a service configuration"""
    try:
        success, message = service_manager.reload_service(service_name)

        if success:
            SystemLog.log_event(
                level=LogLevel.INFO,
                category="services",
                message=f"User {current_user.username} reloaded service: {service_name}",
            )

        return jsonify({"success": success, "message": message})

    except Exception as e:
        current_app.logger.error(f"Failed to reload service {service_name}: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to reload service: {str(e)}"}), 500


@bp.route("/services/group/<service_group>/restart", methods=["POST"])
@login_required
@admin_required
def restart_service_group(service_group):
    """Restart all services in a service group (e.g., 'samba', 'nfs')"""
    try:
        success, message = service_manager.restart_nas_service_group(service_group)

        if success:
            SystemLog.log_event(
                level=LogLevel.INFO,
                category="services",
                message=f"User {current_user.username} restarted service group: {service_group}",
            )

        return jsonify({"success": success, "message": message})

    except Exception as e:
        current_app.logger.error(f"Failed to restart service group {service_group}: {str(e)}")
        return (
            jsonify({"success": False, "message": f"Failed to restart service group: {str(e)}"}),
            500,
        )


@bp.route("/services/<service_name>/logs", methods=["GET"])
@login_required
@admin_required
def get_service_logs(service_name):
    """Get recent logs for a service"""
    try:
        lines = request.args.get("lines", 50, type=int)
        lines = min(lines, 1000)  # Limit to 1000 lines max

        success, logs = service_manager.get_service_logs(service_name, lines)

        return jsonify(
            {
                "success": success,
                "logs": logs,
                "service_name": service_name,
                "lines_requested": lines,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Failed to get logs for service {service_name}: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to get service logs: {str(e)}"}), 500


@bp.route("/services/<service_name>/health", methods=["GET"])
@login_required
def get_service_health(service_name):
    """Get comprehensive health information for a service"""
    try:
        success, health_info = service_manager.check_service_health(service_name)

        return jsonify({"success": success, "health": health_info})

    except Exception as e:
        current_app.logger.error(f"Failed to get health for service {service_name}: {str(e)}")
        return (
            jsonify({"success": False, "message": f"Failed to get service health: {str(e)}"}),
            500,
        )


@bp.route("/services/health-check", methods=["GET"])
@login_required
def comprehensive_health_check():
    """Run comprehensive health check on all NAS services"""
    try:
        services_status = service_manager.get_all_nas_services_status()
        health_report = {
            "overall_status": "healthy",
            "services": {},
            "critical_issues": [],
            "warnings": [],
            "recommendations": [],
        }

        critical_issues = 0
        warnings = 0

        for category, services in services_status.items():
            health_report["services"][category] = {}

            for service_name, service_info in services.items():
                success, health_info = service_manager.check_service_health(service_name)
                health_report["services"][category][service_name] = health_info

                # Count issues
                if health_info.get("overall_health") == "critical":
                    critical_issues += 1
                    health_report["critical_issues"].extend(health_info.get("issues", []))
                elif health_info.get("overall_health") == "warning":
                    warnings += 1
                    health_report["warnings"].extend(health_info.get("issues", []))

                # Collect recommendations
                health_report["recommendations"].extend(health_info.get("recommendations", []))

        # Determine overall status
        if critical_issues > 0:
            health_report["overall_status"] = "critical"
        elif warnings > 0:
            health_report["overall_status"] = "warning"

        health_report["summary"] = {
            "total_services": sum(len(services) for services in services_status.values()),
            "critical_issues": critical_issues,
            "warnings": warnings,
        }

        return jsonify({"success": True, "report": health_report})

    except Exception as e:
        current_app.logger.error(f"Failed to run comprehensive health check: {str(e)}")
        return jsonify({"success": False, "message": f"Failed to run health check: {str(e)}"}), 500


@bp.route("/services/dependencies/<service_name>", methods=["GET"])
@login_required
def get_service_dependencies(service_name):
    """Get service dependencies"""
    try:
        dependencies = service_manager.get_service_dependencies(service_name)

        return jsonify(
            {"success": True, "service_name": service_name, "dependencies": dependencies}
        )

    except Exception as e:
        current_app.logger.error(f"Failed to get dependencies for service {service_name}: {str(e)}")
        return (
            jsonify({"success": False, "message": f"Failed to get service dependencies: {str(e)}"}),
            500,
        )


@bp.route("/services/ports/check", methods=["GET"])
@login_required
def check_service_ports():
    """Check if NAS service ports are listening"""
    try:
        port_status = {}

        # Check common NAS ports
        common_ports = {
            "HTTP": 80,
            "HTTPS": 443,
            "SMB": 445,
            "NetBIOS": 139,
            "NFS": 2049,
            "FTP": 21,
            "SSH": 22,
            "PostgreSQL": 5432,
            "Redis": 6379,
        }

        for service_name, port in common_ports.items():
            is_listening = service_manager.get_port_status(port)
            port_status[service_name] = {
                "port": port,
                "listening": is_listening,
                "status": "open" if is_listening else "closed",
            }

        return jsonify({"success": True, "ports": port_status})

    except Exception as e:
        current_app.logger.error(f"Failed to check service ports: {str(e)}")
        return (
            jsonify({"success": False, "message": f"Failed to check service ports: {str(e)}"}),
            500,
        )


@bp.route("/services/quick-actions", methods=["POST"])
@login_required
@admin_required
def service_quick_actions():
    """Perform quick service management actions"""
    try:
        data = request.get_json()
        action = data.get("action")

        results = []

        if action == "restart_all_nas":
            # Restart all NAS services
            for service_group in ["samba", "nfs", "ftp"]:
                success, message = service_manager.restart_nas_service_group(service_group)
                results.append(
                    {"service_group": service_group, "success": success, "message": message}
                )

        elif action == "start_essential":
            # Start essential services
            essential_services = ["postgresql", "redis-server", "nginx", "supervisor"]
            for service in essential_services:
                success, message = service_manager.start_service(service)
                results.append({"service": service, "success": success, "message": message})

        elif action == "reload_configs":
            # Reload service configurations
            config_services = ["smbd", "nginx", "nfs-kernel-server"]
            for service in config_services:
                success, message = service_manager.reload_service(service)
                results.append({"service": service, "success": success, "message": message})

        else:
            return jsonify({"success": False, "message": f"Unknown action: {action}"}), 400

        # Log the action
        SystemLog.log_event(
            level=LogLevel.INFO,
            category="services",
            message=f"User {current_user.username} performed quick action: {action}",
        )

        return jsonify({"success": True, "action": action, "results": results})

    except Exception as e:
        current_app.logger.error(f"Failed to perform quick action: {str(e)}")
        return (
            jsonify({"success": False, "message": f"Failed to perform quick action: {str(e)}"}),
            500,
        )
