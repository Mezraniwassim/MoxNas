from flask import request, jsonify
from flask_login import login_required
from app.api import bp
from app.models import BackupJob


# Backup API
@bp.route("/backups", methods=["GET"])
@login_required
def api_backup_jobs():
    """Get backup jobs"""
    try:
        jobs = BackupJob.query.all()

        jobs_data = []
        for job in jobs:
            jobs_data.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "source_path": job.source_path,
                    "destination_path": job.destination_path,
                    "backup_type": job.backup_type,
                    "schedule": job.schedule,
                    "status": job.status.value,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "next_run": job.next_run.isoformat() if job.next_run else None,
                    "bytes_backed_up": job.bytes_backed_up,
                    "retention_days": job.retention_days,
                    "compression": job.compression,
                    "encryption": job.encryption,
                    "error_message": job.error_message,
                    "created_at": job.created_at.isoformat(),
                    "created_by": job.created_by_user.username if job.created_by_user else None,
                }
            )

        return jsonify({"jobs": jobs_data, "total": len(jobs_data)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
