from flask import request, jsonify
from flask_login import login_required, current_user
from app.api import bp
from app.models import Share, Dataset, SystemLog, LogLevel, ShareProtocol, ShareStatus
from app.shares.protocols import smb_manager
from app import db


@bp.route("/shares/smb", methods=["POST"])
@login_required
def api_create_smb_share():
    """Create SMB share"""
    if not current_user.is_admin():
        return jsonify({"error": "Administrator privileges required"}), 403

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        name = data.get("name", "").strip()
        dataset_id = data.get("dataset_id")
        guest_access = data.get("guest_access", False)
        read_only = data.get("read_only", False)

        # Validation
        if not name or not dataset_id:
            return jsonify({"error": "Name and dataset are required"}), 400

        if Share.query.filter_by(name=name).first():
            return jsonify({"error": "Share name already exists"}), 409

        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return jsonify({"error": "Dataset not found"}), 404

        # Create share in database
        share = Share(
            name=name,
            protocol=ShareProtocol.SMB,
            dataset_id=dataset_id,
            owner_id=current_user.id,
            guest_access=guest_access,
            read_only=read_only,
            status=ShareStatus.ACTIVE,
            created_by_id=current_user.id,
        )

        db.session.add(share)
        db.session.commit()

        # Create SMB share
        success, message = smb_manager.create_smb_share(share)
        if not success:
            # Rollback database change
            db.session.delete(share)
            db.session.commit()
            return jsonify({"error": message}), 500

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="shares",
            message=f"SMB Share created via API: {name} by {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={"share_id": share.id, "protocol": "smb"},
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
            message=f"API SMB share creation failed: {str(e)}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )
        return jsonify({"error": str(e)}), 500
