from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from app.api import bp
from app.models import Share, Dataset, SystemLog, LogLevel, ShareStatus
from app import db


# Shares API
@bp.route("/shares", methods=["GET"])
@login_required
def api_shares():
    """Get network shares"""
    try:
        shares = Share.query.all()

        shares_data = []
        for share in shares:
            shares_data.append(
                {
                    "id": share.id,
                    "name": share.name,
                    "protocol": share.protocol.value,
                    "dataset_id": share.dataset_id,
                    "dataset_name": share.dataset.name,
                    "dataset_path": share.dataset.path,
                    "owner": share.owner.username,
                    "guest_access": share.guest_access,
                    "read_only": share.read_only,
                    "status": share.status.value,
                    "allowed_hosts": share.get_allowed_hosts(),
                    "bytes_transferred": share.bytes_transferred,
                    "connections_count": share.connections_count,
                    "last_access": share.last_access.isoformat() if share.last_access else None,
                    "created_at": share.created_at.isoformat(),
                    "created_by": share.created_by.username if share.created_by else None,
                }
            )

        return jsonify({"shares": shares_data, "total": len(shares_data)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/shares", methods=["POST"])
@login_required
def api_create_share():
    """Create network share"""
    if not current_user.is_admin():
        return jsonify({"error": "Administrator privileges required"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        name = data.get("name", "").strip()
        protocol = data.get("protocol")
        dataset_id = data.get("dataset_id")
        guest_access = data.get("guest_access", False)
        read_only = data.get("read_only", False)
        allowed_hosts = data.get("allowed_hosts", [])

        # Validation
        if not name or not protocol or not dataset_id:
            return jsonify({"error": "Name, protocol, and dataset are required"}), 400

        if Share.query.filter_by(name=name).first():
            return jsonify({"error": "Share name already exists"}), 409

        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return jsonify({"error": "Dataset not found"}), 404

        # Create share
        from app.models import ShareProtocol

        share = Share(
            name=name,
            protocol=ShareProtocol(protocol),
            dataset_id=dataset_id,
            owner_id=current_user.id,
            guest_access=guest_access,
            read_only=read_only,
            status=ShareStatus.INACTIVE,
            created_by_id=current_user.id,
        )

        if allowed_hosts:
            share.set_allowed_hosts(allowed_hosts)

        db.session.add(share)
        db.session.commit()

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="shares",
            message=f"Share created via API: {name} by {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={"share_id": share.id, "protocol": protocol},
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
            message=f"API share creation failed: {str(e)}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )
        return jsonify({"error": str(e)}), 500
