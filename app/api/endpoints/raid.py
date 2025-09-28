from flask import request, jsonify
from flask_login import login_required
from app.api import bp
from app.storage.manager import storage_manager


@bp.route("/storage/raid/status", methods=["GET"])
@login_required
def api_raid_status():
    """Get status of all RAID arrays"""
    try:
        status = storage_manager.get_all_raid_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
