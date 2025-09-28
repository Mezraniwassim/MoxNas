"""
WebSocket Events for Real-time MoxNAS Updates
Provides real-time system monitoring, alerts, and status updates
"""
import json
import time
import threading
from datetime import datetime
from flask import request, current_app
from flask_socketio import emit, disconnect
from flask_login import current_user
import psutil
from app.models import SystemLog, LogLevel, StoragePool, StorageDevice, Alert
from app import db
from sqlalchemy.orm import joinedload


def register_websocket_events(socketio):
    """Register WebSocket event handlers"""

    @socketio.on("connect")
    def handle_connect():
        """Handle client connection with enhanced security"""
        # Enhanced authentication check
        if not current_user.is_authenticated:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category="websocket_security",
                message="Unauthenticated WebSocket connection attempt",
                ip_address=request.remote_addr,
            )
            disconnect()
            return False

        # Check user permissions for WebSocket access
        if not hasattr(current_user, "role") or not current_user.role:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category="websocket_security",
                message=f"WebSocket access denied for user without proper role: {current_user.username}",
                user_id=current_user.id,
                ip_address=request.remote_addr,
            )
            disconnect()
            return False

        emit("status", {"msg": "Connected to MoxNAS real-time updates"})

        # Send initial system status with permission checks
        try:
            emit("system_stats", get_system_stats_secure())
            emit("storage_status", get_storage_status_secure())
            emit("alerts", get_recent_alerts_secure())
        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="websocket",
                message=f"Error sending initial data to WebSocket client: {e}",
                user_id=current_user.id,
            )

        SystemLog.log_event(
            level=LogLevel.DEBUG,
            category="websocket",
            message=f"WebSocket client connected: {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection"""
        if current_user.is_authenticated:
            SystemLog.log_event(
                level=LogLevel.DEBUG,
                category="websocket",
                message=f"WebSocket client disconnected: {current_user.username}",
                user_id=current_user.id,
            )

    @socketio.on("subscribe")
    def handle_subscribe(data):
        """Handle subscription to specific updates with validation"""
        if not current_user.is_authenticated:
            disconnect()
            return False

        # Validate subscription data
        if not isinstance(data, dict) or "type" not in data:
            emit("error", {"message": "Invalid subscription request"})
            return

        subscription_type = data.get("type")
        allowed_subscriptions = ["system", "storage", "network", "alerts"]

        if subscription_type in allowed_subscriptions:
            # Check user permissions for specific subscription types
            if subscription_type == "system" and current_user.role.value != "admin":
                emit("error", {"message": "Insufficient permissions for system updates"})
                return

            # Add user to subscription room
            from flask_socketio import join_room

            join_room(f"{subscription_type}_updates")
            emit("subscribed", {"type": subscription_type})

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="websocket",
                message=f"User subscribed to {subscription_type} updates",
                user_id=current_user.id,
            )
        else:
            emit("error", {"message": "Invalid subscription type"})

    @socketio.on("unsubscribe")
    def handle_unsubscribe(data):
        """Handle unsubscription from updates"""
        if not current_user.is_authenticated:
            disconnect()
            return False

        subscription_type = data.get("type")
        if subscription_type in ["system", "storage", "network", "alerts"]:
            from flask_socketio import leave_room

            leave_room(f"{subscription_type}_updates")
            emit("unsubscribed", {"type": subscription_type})

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="websocket",
                message=f"User unsubscribed from {subscription_type} updates",
                user_id=current_user.id,
            )

    @socketio.on("ping")
    def handle_ping():
        """Handle ping for connection testing"""
        if not current_user.is_authenticated:
            disconnect()
            return False
        emit("pong", {"timestamp": datetime.utcnow().isoformat()})


def get_system_stats_secure():
    """Get current system statistics with security filtering"""
    try:
        # Only provide stats if user is authenticated and authorized
        if not current_user.is_authenticated or current_user.role.value != "admin":
            return {"error": "Unauthorized access to system statistics"}

        # CPU stats - limit precision to prevent fingerprinting
        cpu_percent = round(psutil.cpu_percent(interval=0.1), 1)  # Shorter interval, less precision
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        # Memory stats
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk stats
        disk_usage = psutil.disk_usage("/")

        # Network stats
        network = psutil.net_io_counters()

        # Load average (Unix/Linux only)
        try:
            load_avg = psutil.getloadavg()
        except AttributeError:
            load_avg = [0, 0, 0]

        # System uptime
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "frequency": cpu_freq.current if cpu_freq else 0,
            },
            "memory": {
                "total": memory.total,
                "used": memory.used,
                "free": memory.free,
                "percent": round(memory.percent, 1),
                "available": memory.available,
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": round(swap.percent, 1),
            },
            "disk": {
                "total": disk_usage.total,
                "used": disk_usage.used,
                "free": disk_usage.free,
                "percent": round((disk_usage.used / disk_usage.total) * 100, 1),
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv,
            },
            "load_average": [round(x, 2) for x in load_avg],
            "uptime": round(uptime),
        }

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="websocket",
            message=f"Error getting system stats: {e}",
            user_id=getattr(current_user, "id", None),
        )
        return {"error": "Failed to retrieve system statistics"}


def get_storage_status_secure():
    """Get storage system status with security filtering"""
    try:
        # Check user permissions
        if not current_user.is_authenticated:
            return {"error": "Authentication required"}

        # Query pools without eager loading first to avoid issues with empty database
        pools = StoragePool.query.all()
        
        devices = StorageDevice.query.all()

        storage_data = {
            "pools": [],
            "devices": [],
            "summary": {
                "total_pools": len(pools),
                "healthy_pools": len([p for p in pools if p.status.value == "healthy"]),
                "total_devices": len(devices),
                "healthy_devices": len([d for d in devices if d.status.value == "healthy"]),
            },
        }

        # Pool information - filter sensitive data (skip if no pools)
        for pool in pools:
            try:
                pool_data = {
                    "id": pool.id,
                    "name": pool.name,
                    "status": pool.status.value,
                    "raid_level": pool.raid_level,
                    "total_size": pool.total_size,
                    "used_size": pool.used_size,
                }

                # Only include detailed info for admins
                if current_user.role.value == "admin":
                    pool_data.update(
                        {
                            "mount_point": getattr(pool, "mount_point", None),
                            "available_size": getattr(pool, "available_size", None),
                            "last_scrub": getattr(pool, "last_scrub", None),
                        }
                    )

                storage_data["pools"].append(pool_data)
            except Exception as pool_error:
                # Skip problematic pools but log the error
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category="websocket",
                    message=f"Skipping pool {getattr(pool, 'id', 'unknown')}: {pool_error}",
                    user_id=getattr(current_user, "id", None),
                )

        # Device information - basic info only for non-admins
        for device in devices:
            device_data = {
                "id": device.id,
                "name": device.device_name,
                "status": device.status.value,
                "size": device.device_size,
            }

            if current_user.role.value == "admin":
                device_data.update(
                    {
                        "device_path": device.device_path,
                        "serial": device.device_serial,
                        "model": device.device_model,
                        "temperature": device.temperature,
                    }
                )

            storage_data["devices"].append(device_data)

        return storage_data

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="websocket",
            message=f"Error getting storage status: {str(e)}",
            user_id=getattr(current_user, "id", None),
            details={"error_type": type(e).__name__, "traceback": error_details}
        )
        return {"error": f"Failed to retrieve storage status: {str(e)}"}


def get_recent_alerts_secure():
    """Get recent alerts with security filtering"""
    try:
        if not current_user.is_authenticated:
            return {"error": "Authentication required"}

        # Get recent alerts with limit
        alerts = (
            Alert.query.filter(Alert.is_active == True)
            .order_by(Alert.created_at.desc())
            .limit(10)
            .all()
        )

        alerts_data = []
        for alert in alerts:
            alert_data = {
                "id": alert.id,
                "severity": alert.severity.value,
                "message": alert.message,
                "created_at": alert.created_at.isoformat(),
                "category": getattr(alert, "category", "general"),
            }

            # Only include detailed info for admins
            if current_user.role.value == "admin":
                alert_data.update({"component": getattr(alert, "component", "system"), "title": getattr(alert, "title", "")})

            alerts_data.append(alert_data)

        return {"alerts": alerts_data}

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="websocket",
            message=f"Error getting alerts: {e}",
            user_id=getattr(current_user, "id", None),
        )
        return {"error": "Failed to retrieve alerts"}


def broadcast_system_update(update_type, data):
    """Broadcast system updates to subscribed clients securely"""
    try:
        from flask_socketio import emit
        from app import socketio

        # Validate update type
        valid_types = ["system", "storage", "network", "alerts"]
        if update_type not in valid_types:
            return False

        # Filter sensitive data based on update type
        if update_type == "system":
            # Only send to admin subscribers
            socketio.emit("system_update", data, room="system_updates")
        else:
            # Send to all subscribers of this type
            socketio.emit(f"{update_type}_update", data, room=f"{update_type}_updates")

        return True

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="websocket",
            message=f"Error broadcasting update: {e}",
            details={"update_type": update_type},
        )
        return False


# Background monitoring thread management
class MonitoringThreadManager:
    """Manages background monitoring threads securely"""

    def __init__(self):
        self.threads = {}
        self.shutdown_event = threading.Event()

    def start_monitoring(self, monitor_type, interval=60):
        """Start monitoring thread with proper error handling"""
        if monitor_type in self.threads and self.threads[monitor_type].is_alive():
            return True  # Already running

        if monitor_type == "system":
            thread = threading.Thread(
                target=self._system_monitor,
                args=(interval,),
                daemon=True,
                name=f"SystemMonitor-{monitor_type}",
            )
        elif monitor_type == "storage":
            thread = threading.Thread(
                target=self._storage_monitor,
                args=(interval,),
                daemon=True,
                name=f"StorageMonitor-{monitor_type}",
            )
        else:
            return False

        self.threads[monitor_type] = thread
        thread.start()
        return True

    def stop_monitoring(self, monitor_type=None):
        """Stop monitoring threads gracefully"""
        self.shutdown_event.set()

        if monitor_type:
            if monitor_type in self.threads:
                self.threads[monitor_type].join(timeout=5)
                del self.threads[monitor_type]
        else:
            # Stop all threads
            for thread in self.threads.values():
                thread.join(timeout=5)
            self.threads.clear()

    def _system_monitor(self, interval):
        """System monitoring thread"""
        while not self.shutdown_event.wait(interval):
            try:
                stats = get_system_stats_secure()
                broadcast_system_update("system", stats)
            except Exception as e:
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="monitoring",
                    message=f"System monitoring error: {e}",
                )

    def _storage_monitor(self, interval):
        """Storage monitoring thread"""
        while not self.shutdown_event.wait(interval):
            try:
                status = get_storage_status_secure()
                broadcast_system_update("storage", status)
            except Exception as e:
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="monitoring",
                    message=f"Storage monitoring error: {e}",
                )


# Global monitoring manager
monitoring_manager = MonitoringThreadManager()
