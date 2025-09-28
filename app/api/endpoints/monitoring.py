from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from app.api import bp
from app.models import Alert, SystemLog
from datetime import datetime


# Monitoring API
@bp.route("/monitoring/system", methods=["GET"])
@login_required
def api_monitoring_system():
    """Get system monitoring data"""
    try:
        import psutil

        # Get system metrics
        system_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "cpu": {
                "percent": psutil.cpu_percent(interval=0.1),
                "count": psutil.cpu_count(),
                "load_avg": list(psutil.getloadavg())
                if hasattr(psutil, "getloadavg")
                else [0, 0, 0],
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
                "used": psutil.virtual_memory().used,
            },
            "disk": {"usage": {}, "io": {}},
            "network": {},
            "processes": len(psutil.pids()),
            "uptime": (datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds(),
        }

        # Disk usage
        for partition in psutil.disk_partitions():
            if partition.fstype and not partition.mountpoint.startswith("/snap"):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    system_data["disk"]["usage"][partition.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": (usage.used / usage.total) * 100 if usage.total > 0 else 0,
                    }
                except PermissionError:
                    continue

        # Disk I/O
        disk_io = psutil.disk_io_counters()
        if disk_io:
            system_data["disk"]["io"] = {
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
            }

        # Network I/O
        net_io = psutil.net_io_counters(pernic=True)
        for interface, stats in net_io.items():
            if not interface.startswith("lo"):
                system_data["network"][interface] = {
                    "bytes_sent": stats.bytes_sent,
                    "bytes_recv": stats.bytes_recv,
                    "packets_sent": stats.packets_sent,
                    "packets_recv": stats.packets_recv,
                }

        return jsonify(system_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/monitoring/alerts", methods=["GET"])
@login_required
def api_monitoring_alerts():
    """Get active alerts"""
    try:
        alerts = (
            Alert.query.filter_by(is_active=True).order_by(Alert.created_at.desc()).limit(20).all()
        )

        alerts_data = []
        for alert in alerts:
            alerts_data.append(
                {
                    "id": alert.id,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": alert.severity.value,
                    "category": alert.category,
                    "created_at": alert.created_at.isoformat(),
                    "acknowledged_at": alert.acknowledged_at.isoformat()
                    if alert.acknowledged_at
                    else None,
                    "acknowledged_by": alert.acknowledged_by.username
                    if alert.acknowledged_by
                    else None,
                }
            )

        return jsonify({"alerts": alerts_data, "total": len(alerts_data)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
