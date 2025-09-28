from flask import request, jsonify
from flask_login import login_required
from app.api import bp
from app.proxmox.integration import proxmox_manager


@bp.route("/lxc/containers/status", methods=["GET"])
@login_required
def api_lxc_container_status():
    """Get status of all LXC containers"""
    try:
        status = proxmox_manager.vm_manager.get_all_vm_status()
        # Filter for LXC containers
        lxc_status = [s for s in status if s.get("type") == "lxc"]
        return jsonify(lxc_status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
