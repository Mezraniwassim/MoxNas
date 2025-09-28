from flask import request, jsonify
from flask_login import login_required
from app.api import bp
from app.models import StoragePool
from app.storage.manager import storage_manager


@bp.route("/storage/pools/<int:pool_id>/performance", methods=["GET"])
@login_required
def api_pool_performance(pool_id):
    """Get detailed performance metrics for a storage pool"""
    try:
        pool = StoragePool.query.get_or_404(pool_id)

        # Get performance data from the storage manager
        performance_data = storage_manager.get_pool_performance(pool)

        return jsonify(performance_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
