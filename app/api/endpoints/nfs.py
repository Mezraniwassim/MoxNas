from flask import request, jsonify
from flask_login import login_required, current_user
from app.api import bp
from app.models import Share, Dataset, SystemLog, LogLevel, ShareProtocol, ShareStatus
from app.shares.protocols import create_nfs_share
from app import db


@bp.route("/shares/nfs", methods=["POST"])
@login_required
def api_create_nfs_share():
    """Create NFS share"""
    if not current_user.is_admin():
        return jsonify({"error": "Administrator privileges required"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        name = data.get("name", "").strip()
        dataset_id = data.get("dataset_id")
        allowed_hosts = data.get("allowed_hosts", [])
        read_only = data.get("read_only", False)

        # Validation
        if not name or not dataset_id:
            return jsonify({"error": "Name and dataset are required"}), 400

        if Share.query.filter_by(name=name).first():
            return jsonify({"error": "Share name already exists"}), 409

        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return jsonify({"error": "Dataset not found"}), 404

        # Create NFS export
        success, message = create_nfs_share(dataset.path, allowed_hosts, read_only)
        if not success:
            return jsonify({"error": message}), 500

        # Create share in database
        share = Share(
            name=name,
            protocol=ShareProtocol.NFS,
            dataset_id=dataset_id,
            owner_id=current_user.id,
            guest_access=False,
            read_only=read_only,
            status=ShareStatus.ACTIVE,
            created_by_id=current_user.id,
        )

        if allowed_hosts:
            share.set_allowed_hosts(allowed_hosts)

        db.session.add(share)
        db.session.commit()

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="shares",
            message=f"NFS Share created via API: {name} by {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={"share_id": share.id, "protocol": "nfs"},
        )

        return (
            jsonify(
                {
                    "success": True,
                    "share": {
                        "id": share.id,
                        "name": share.name,
                        "protocol": share.protocol.value,
                        "status": share.status.value,
                    },
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="shares",
            message=f"API NFS share creation failed: {str(e)}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )
        return jsonify({"error": str(e)}), 500
