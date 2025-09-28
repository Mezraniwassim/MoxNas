from flask import request, jsonify
from flask_login import login_required
from app.api import bp
from app.proxmox.integration import proxmox_manager


@bp.route("/proxmox/vms/status", methods=["GET"])
@login_required
def api_proxmox_vm_status():
    """Get status of all Proxmox VMs"""
    try:
        status = proxmox_manager.get_all_vm_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
