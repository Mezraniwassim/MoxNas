from flask import request, jsonify
from flask_login import login_required
from app.api import bp
from app.models import SystemLog


# System logs API
@bp.route("/logs", methods=["GET"])
@login_required
def api_logs():
    """Get system logs"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = min(request.args.get("per_page", 50, type=int), 100)
        level = request.args.get("level")
        category = request.args.get("category")

        query = SystemLog.query

        if level:
            query = query.filter_by(level=level)
        if category:
            query = query.filter_by(category=category)

        logs = query.order_by(SystemLog.timestamp.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        logs_data = []
        for log in logs.items:
            logs_data.append(
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "level": log.level.value,
                    "category": log.category,
                    "message": log.message,
                    "user": log.user.username if log.user else None,
                    "ip_address": log.ip_address,
                    "details": log.get_details(),
                }
            )

        return jsonify(
            {
                "logs": logs_data,
                "pagination": {
                    "page": logs.page,
                    "pages": logs.pages,
                    "per_page": logs.per_page,
                    "total": logs.total,
                    "has_next": logs.has_next,
                    "has_prev": logs.has_prev,
                },
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
