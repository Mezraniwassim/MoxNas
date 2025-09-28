from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from app.api import bp
from app.models import (
    User,
    StorageDevice,
    StoragePool,
    Dataset,
    Share,
    BackupJob,
    SystemLog,
    Alert,
    LogLevel,
    UserRole,
    DeviceStatus,
    PoolStatus,
    ShareStatus,
)
from app import db, limiter
from app.storage.manager import storage_manager
from app.utils.error_handler import (
    secure_route,
    validate_input,
    log_sensitive_operation,
    DatabaseErrorHandler,
)
from app.security.hardening import InputSanitizer


# Storage API
@bp.route("/storage/devices", methods=["GET"])
@login_required
@secure_route
def api_storage_devices():
    """Get storage devices"""
    try:
        devices = StorageDevice.query.all()

        devices_data = []
        for device in devices:
            devices_data.append(
                {
                    "id": device.id,
                    "path": device.device_path,
                    "name": device.device_name,
                    "model": device.device_model,
                    "serial": device.device_serial,
                    "size": device.device_size,
                    "status": device.status.value,
                    "temperature": device.temperature,
                    "power_on_hours": device.power_on_hours,
                    "pool_id": device.pool_id,
                    "pool_name": device.pool.name if device.pool else None,
                    "smart_data": device.get_smart_data(),
                    "created_at": device.created_at.isoformat(),
                    "updated_at": device.updated_at.isoformat(),
                }
            )

        return jsonify({"devices": devices_data, "total": len(devices_data)})

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="storage",
            message=f"API error in storage devices: {str(e)}",
        )
        return jsonify({"error": "Failed to retrieve storage devices"}), 500


@bp.route("/storage/devices/scan", methods=["POST"])
@login_required
@limiter.limit("1 per minute")
@secure_route
@log_sensitive_operation("device_scan", "storage_device")
def api_scan_devices():
    """Scan for storage devices"""
    if not current_user.is_admin():
        return jsonify({"error": "Administrator privileges required"}), 403

    try:
        storage_manager.update_device_database()

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="storage",
            message=f"Device scan initiated via API by {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )

        return jsonify({"success": True, "message": "Device scan completed"})

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="storage",
            message=f"API device scan failed: {str(e)}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )
        return jsonify({"error": str(e)}), 500


@bp.route("/storage/pools", methods=["GET"])
@login_required
@secure_route
def api_storage_pools():
    """Get storage pools"""
    try:
        pools = StoragePool.query.all()

        pools_data = []
        for pool in pools:
            pool_devices = [d for d in pool.devices]
            pools_data.append(
                {
                    "id": pool.id,
                    "name": pool.name,
                    "raid_level": pool.raid_level,
                    "filesystem_type": pool.filesystem_type,
                    "mount_point": pool.mount_point,
                    "total_size": pool.total_size,
                    "used_size": pool.used_size,
                    "available_size": pool.available_size,
                    "status": pool.status.value,
                    "device_count": len(pool_devices),
                    "devices": [
                        {"id": d.id, "path": d.device_path, "status": d.status.value}
                        for d in pool_devices
                    ],
                    "last_scrub": pool.last_scrub.isoformat() if pool.last_scrub else None,
                    "created_at": pool.created_at.isoformat(),
                    "created_by": pool.created_by.username if pool.created_by else None,
                }
            )

        return jsonify({"pools": pools_data, "total": len(pools_data)})

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="storage",
            message=f"API error in storage pools: {str(e)}",
        )
        return jsonify({"error": "Failed to retrieve storage pools"}), 500


@bp.route("/storage/pools", methods=["POST"])
@login_required
@secure_route
@log_sensitive_operation("pool_creation", "storage_pool")
@validate_input(
    name=lambda x: InputSanitizer.sanitize_filename(x) == x and len(x) >= 3,
    raid_level=lambda x: x in ["single", "mirror", "raid5", "raid6"],
    filesystem=lambda x: x in ["ext4", "xfs", "btrfs", "zfs"],
)
def api_create_pool():
    """Create storage pool"""
    if not current_user.is_admin():
        return jsonify({"error": "Administrator privileges required"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        name = data.get("name", "").strip()
        raid_level = data.get("raid_level")
        filesystem = data.get("filesystem", "ext4")
        device_paths = data.get("devices", [])

        # Validation
        if not name or not raid_level or not device_paths:
            return jsonify({"error": "Name, RAID level, and devices are required"}), 400

        if StoragePool.query.filter_by(name=name).first():
            return jsonify({"error": "Pool name already exists"}), 409

        # Create RAID array
        success, message = storage_manager.create_raid_array(
            name=name, level=raid_level, devices=device_paths, filesystem=filesystem
        )

        if not success:
            return jsonify({"error": message}), 500

        # Create database record
        pool = StoragePool(
            name=name,
            raid_level=raid_level,
            filesystem_type=filesystem,
            mount_point=f"/mnt/{name}",
            status=PoolStatus.HEALTHY,
            created_by_id=current_user.id,
        )

        db.session.add(pool)
        db.session.flush()

        # Associate devices with pool
        for device_path in device_paths:
            device = StorageDevice.query.filter_by(device_path=device_path).first()
            if device:
                device.pool_id = pool.id

        # Calculate pool size
        raid_device = f"/dev/md/{name}"
        pool.total_size = storage_manager._get_device_size(raid_device)
        pool.available_size = pool.total_size

        success, error = DatabaseErrorHandler.safe_commit()
        if not success:
            return jsonify({"error": f"Database operation failed: {error}"}), 500

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="storage",
            message=f"Storage pool created via API: {name} by {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={"pool_id": pool.id, "raid_level": raid_level, "devices": device_paths},
        )

        return (
            jsonify(
                {
                    "success": True,
                    "pool": {
                        "id": pool.id,
                        "name": pool.name,
                        "raid_level": pool.raid_level,
                        "status": pool.status.value,
                        "total_size": pool.total_size,
                    },
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="storage",
            message=f"API pool creation failed: {str(e)}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )
        return jsonify({"error": "Pool creation failed"}), 500


@bp.route("/storage/pools/<int:pool_id>", methods=["GET"])
@login_required
@secure_route
def api_pool_detail(pool_id):
    """Get pool details"""
    try:
        pool = StoragePool.query.get_or_404(pool_id)

        # Get pool status from system
        pool_status = storage_manager.get_raid_status(pool)

        return jsonify(
            {
                "id": pool.id,
                "name": pool.name,
                "raid_level": pool.raid_level,
                "filesystem_type": pool.filesystem_type,
                "mount_point": pool.mount_point,
                "total_size": pool.total_size,
                "used_size": pool.used_size,
                "available_size": pool.available_size,
                "status": pool.status.value,
                "system_status": pool_status,
                "devices": [
                    {
                        "id": d.id,
                        "path": d.device_path,
                        "name": d.device_name,
                        "status": d.status.value,
                        "temperature": d.temperature,
                    }
                    for d in pool.devices
                ],
                "datasets_count": pool.datasets.count(),
                "last_scrub": pool.last_scrub.isoformat() if pool.last_scrub else None,
                "created_at": pool.created_at.isoformat(),
                "created_by": pool.created_by.username if pool.created_by else None,
            }
        )

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR, category="storage", message=f"API error in pool detail: {str(e)}"
        )
        return jsonify({"error": "Failed to retrieve pool details"}), 500
