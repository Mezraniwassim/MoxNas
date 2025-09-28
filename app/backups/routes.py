"""Backup management routes with enhanced error handling"""
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.backups import bp
from app.models import BackupJob, BackupStatus, Dataset, SystemLog, LogLevel
from app import db
from datetime import datetime, timedelta
import os
import subprocess
from celery import current_app
from app.utils.enhanced_logging import get_logger, log_operation
from app.utils.error_handling import (
    with_error_handling, RetryPolicy, ErrorCategory, error_context,
    handle_database_errors, MoxNASError
)


@bp.route("/")
@login_required
@log_operation(operation_name="list_backup_jobs", category="backups")
def index():
    """Backup jobs overview page with enhanced error handling"""
    logger = get_logger('backups')
    
    with error_context(
        operation="list_backup_jobs",
        category=ErrorCategory.DATABASE
    ) as ctx:
        page = request.args.get("page", "1")
        try:
            page = int(page) if page else 1
        except (ValueError, TypeError):
            logger.warning(f"Invalid page parameter: {request.args.get('page')}")
            page = 1

        try:
            jobs = BackupJob.query.paginate(page=page, per_page=20, error_out=False)

            # Statistics
            total_jobs = BackupJob.query.count()
            running_jobs = BackupJob.query.filter_by(status=BackupStatus.RUNNING).count()
            failed_jobs = BackupJob.query.filter_by(status=BackupStatus.FAILED).count()
        
        except Exception as e:
            logger.error(
                f"Failed to retrieve backup jobs: {str(e)}",
                category='backups',
                operation_type='database_query_error',
                error_type=type(e).__name__
            )
            flash("Error retrieving backup jobs. Please try again.", "danger")
            # Return empty pagination for graceful degradation
            from flask_sqlalchemy import Pagination
            jobs = Pagination(BackupJob.query, page, 20, 0, [])
            total_jobs = running_jobs = failed_jobs = 0

    # Create backup stats object
    backup_stats = {
        "total": total_jobs,
        "running": running_jobs,
        "failed": failed_jobs,
        "successful": total_jobs - running_jobs - failed_jobs,
        "scheduled": BackupJob.query.filter(BackupJob.next_run.isnot(None)).count(),
    }

    return render_template(
        "backups/index.html",
        jobs=jobs,
        total_jobs=total_jobs,
        running_jobs=running_jobs,
        failed_jobs=failed_jobs,
        backup_stats=backup_stats,
    )


@bp.route("/create", methods=["GET", "POST"])
@login_required
@log_operation(operation_name="create_backup_job", category="backups")
@with_error_handling(
    operation="create_backup_job",
    category=ErrorCategory.SYSTEM,
    retry_policy=RetryPolicy(max_attempts=1)  # No retry for user input
)
def create():
    """Create new backup job with enhanced validation and error handling"""
    logger = get_logger('backups')
    
    if not current_user.is_admin():
        logger.warning(
            "Non-admin user attempted to create backup job",
            category='security',
            user_id=current_user.id
        )
        flash("Administrator privileges required to create backup jobs", "danger")
        return redirect(url_for("backups.index"))

    if request.method == "POST":
        with error_context(
            operation="create_backup_job",
            category=ErrorCategory.VALIDATION
        ) as ctx:
            try:
                # Extract and validate form data
                name = request.form.get("name", "").strip()
                source_path = request.form.get("source_path", "").strip()
                destination_path = request.form.get("destination_path", "").strip()
                backup_type = request.form.get("backup_type", "incremental")
                schedule = request.form.get("schedule", "").strip()
                
                try:
                    retention_days = int(request.form.get("retention_days", 30))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid retention_days value: {request.form.get('retention_days')}")
                    retention_days = 30
                
                compression = request.form.get("compression") == "on"
                encryption = request.form.get("encryption") == "on"

                # Enhanced validation with detailed error reporting
                validation_errors = []
                
                if not name:
                    validation_errors.append("Backup job name is required")
                elif len(name) < 3:
                    validation_errors.append("Backup job name must be at least 3 characters")
                elif len(name) > 100:
                    validation_errors.append("Backup job name must be less than 100 characters")
                
                # Check for duplicate names
                if name:
                    existing_job = BackupJob.query.filter_by(name=name).first()
                    if existing_job:
                        validation_errors.append("Backup job name already exists")

                # Validate paths
                if not source_path:
                    validation_errors.append("Source path is required")
                elif not os.path.exists(source_path):
                    validation_errors.append(f"Source path does not exist: {source_path}")
                elif not os.access(source_path, os.R_OK):
                    validation_errors.append(f"Source path is not readable: {source_path}")

                if not destination_path:
                    validation_errors.append("Destination path is required")
                elif os.path.exists(destination_path) and not os.access(destination_path, os.W_OK):
                    validation_errors.append(f"Destination path is not writable: {destination_path}")
                
                # Validate backup type
                valid_backup_types = ['full', 'incremental', 'differential']
                if backup_type not in valid_backup_types:
                    validation_errors.append(f"Invalid backup type. Must be one of: {', '.join(valid_backup_types)}")
                
                # Validate retention days
                if retention_days < 1 or retention_days > 3650:
                    validation_errors.append("Retention days must be between 1 and 3650")
                
                # If there are validation errors, report them
                if validation_errors:
                    for error in validation_errors:
                        flash(error, "danger")
                    
                    logger.warning(
                        "Backup job creation failed validation",
                        category='backups',
                        operation_type='validation_failed',
                        user_id=current_user.id,
                        details={'errors': validation_errors, 'name': name}
                    )
                    
                    return redirect(url_for("backups.create"))

                # Create backup job with enhanced error handling
                try:
                    job = BackupJob(
                        name=name,
                        source_path=source_path,
                        destination_path=destination_path,
                        backup_type=backup_type,
                        schedule=schedule if schedule else None,
                        retention_days=retention_days,
                        compression=compression,
                        encryption=encryption,
                        status=BackupStatus.SCHEDULED,
                        created_by_id=current_user.id,
                    )

                    # Calculate next run time if scheduled
                    if schedule:
                        try:
                            job.next_run = calculate_next_run(schedule)
                        except Exception as schedule_error:
                            logger.warning(
                                f"Failed to calculate next run time for schedule '{schedule}': {schedule_error}",
                                category='backups',
                                operation_type='schedule_calculation_error'
                            )
                            # Continue without scheduling
                            job.next_run = None

                    # Save to database with error handling
                    db.session.add(job)
                    db.session.commit()

                    logger.info(
                        f"Backup job created successfully: {name}",
                        category='backups',
                        operation_type='job_created',
                        user_id=current_user.id,
                        job_id=job.id,
                        details={
                            'source': source_path,
                            'destination': destination_path,
                            'backup_type': backup_type,
                            'schedule': schedule,
                            'compression': compression,
                            'encryption': encryption
                        }
                    )
                    
                    SystemLog.log_event(
                        level=LogLevel.INFO,
                        category="backups",
                        message=f"Backup job created: {name} by {current_user.username}",
                        user_id=current_user.id,
                        ip_address=request.remote_addr,
                        details={"job_id": job.id, "source": source_path, "destination": destination_path},
                    )

                    flash(f'Backup job "{name}" created successfully', "success")
                    return redirect(url_for("backups.index"))
                    
                except Exception as db_error:
                    db.session.rollback()
                    error_msg = f"Database error creating backup job: {str(db_error)}"
                    logger.error(
                        error_msg,
                        category='backups',
                        operation_type='database_error',
                        user_id=current_user.id,
                        error_type=type(db_error).__name__
                    )
                    flash("Failed to create backup job due to database error", "danger")
                    return redirect(url_for("backups.create"))

            except Exception as e:
                db.session.rollback()
                error_msg = f"Unexpected error creating backup job: {str(e)}"
                logger.error(
                    error_msg,
                    category='backups',
                    operation_type='creation_error',
                    user_id=current_user.id,
                    error_type=type(e).__name__
                )
                
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="backups",
                    message=error_msg,
                    user_id=current_user.id,
                    ip_address=request.remote_addr,
                )
                
                flash("An unexpected error occurred while creating the backup job", "danger")
                return redirect(url_for("backups.create"))

    # GET request - show create form
    try:
        datasets = Dataset.query.all()
    except Exception as e:
        logger.error(
            f"Failed to retrieve datasets for backup creation form: {str(e)}",
            category='backups',
            operation_type='form_data_error'
        )
        datasets = []  # Graceful degradation
        flash("Warning: Could not load datasets. You may need to refresh the page.", "warning")
    
    backup_types = ["full", "incremental", "differential"]

    return render_template("backups/create.html", datasets=datasets, backup_types=backup_types)


@bp.route("/<int:job_id>")
@login_required
def detail(job_id):
    """Backup job detail page"""
    job = BackupJob.query.get_or_404(job_id)

    # Get backup history/logs
    backup_history = get_backup_history(job)

    return render_template("backups/detail.html", job=job, backup_history=backup_history)


@bp.route("/<int:job_id>/start", methods=["POST"])
@login_required
def start(job_id):
    """Start backup job manually"""
    if not current_user.is_admin():
        return jsonify({"success": False, "error": "Administrator privileges required"}), 403

    job = BackupJob.query.get_or_404(job_id)

    if job.status == BackupStatus.RUNNING:
        return jsonify({"success": False, "error": "Backup job is already running"}), 400

    try:
        # Start backup task
        from app.tasks import run_backup_job

        task = run_backup_job.delay(job.id)

        # Update job status
        job.status = BackupStatus.RUNNING
        job.last_run = datetime.utcnow()
        job.error_message = None
        db.session.commit()

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="backups",
            message=f"Backup job started: {job.name} by {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={"job_id": job.id, "task_id": task.id},
        )

        return jsonify(
            {
                "success": True,
                "message": f'Backup job "{job.name}" started successfully',
                "task_id": task.id,
            }
        )

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="backups",
            message=f"Error starting backup job {job.name}: {str(e)}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/<int:job_id>/stop", methods=["POST"])
@login_required
def stop(job_id):
    """Stop running backup job"""
    if not current_user.is_admin():
        return jsonify({"success": False, "error": "Administrator privileges required"}), 403

    job = BackupJob.query.get_or_404(job_id)

    if job.status != BackupStatus.RUNNING:
        return jsonify({"success": False, "error": "Backup job is not running"}), 400

    try:
        # Implement Celery task cancellation
        from app import celery
        from app.tasks import backup_task

        # Find and revoke the running task
        active_tasks = celery.control.active()
        task_cancelled = False

        for worker, tasks in active_tasks.items():
            for task in tasks:
                if (
                    task.get("name") == "app.tasks.backup_task"
                    and task.get("args")
                    and str(job.id) in str(task.get("args", []))
                ):
                    celery.control.revoke(task["id"], terminate=True)
                    task_cancelled = True
                    break

        # Update job status
        job.status = BackupStatus.CANCELLED
        job.error_message = f"Cancelled by {current_user.username}" + (
            " (task terminated)" if task_cancelled else " (task not found - may have completed)"
        )
        db.session.commit()

        SystemLog.log_event(
            level=LogLevel.WARNING,
            category="backups",
            message=f"Backup job cancelled: {job.name} by {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={"job_id": job.id, "task_cancelled": task_cancelled},
        )

        return jsonify(
            {"success": True, "message": f'Backup job "{job.name}" stopped successfully'}
        )

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="backups",
            message=f"Error stopping backup job {job.name}: {str(e)}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/<int:job_id>/delete", methods=["POST"])
@login_required
def delete(job_id):
    """Delete backup job"""
    if not current_user.is_admin():
        return jsonify({"success": False, "error": "Administrator privileges required"}), 403

    job = BackupJob.query.get_or_404(job_id)

    if job.status == BackupStatus.RUNNING:
        return jsonify({"success": False, "error": "Cannot delete running backup job"}), 400

    try:
        job_name = job.name
        db.session.delete(job)
        db.session.commit()

        SystemLog.log_event(
            level=LogLevel.WARNING,
            category="backups",
            message=f"Backup job deleted: {job_name} by {current_user.username}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={"job_name": job_name},
        )

        return jsonify(
            {"success": True, "message": f'Backup job "{job_name}" deleted successfully'}
        )

    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="backups",
            message=f"Error deleting backup job {job.name}: {str(e)}",
            user_id=current_user.id,
            ip_address=request.remote_addr,
        )
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/api/status")
@login_required
def api_status():
    """API endpoint for backup status summary"""
    jobs = BackupJob.query.all()

    status_summary = {
        "total_jobs": len(jobs),
        "scheduled": len([j for j in jobs if j.status == BackupStatus.SCHEDULED]),
        "running": len([j for j in jobs if j.status == BackupStatus.RUNNING]),
        "completed": len([j for j in jobs if j.status == BackupStatus.COMPLETED]),
        "failed": len([j for j in jobs if j.status == BackupStatus.FAILED]),
        "jobs": [],
    }

    for job in jobs:
        status_summary["jobs"].append(
            {
                "id": job.id,
                "name": job.name,
                "status": job.status.value,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "bytes_backed_up": job.bytes_backed_up,
                "error_message": job.error_message,
            }
        )

    return jsonify(status_summary)


def calculate_next_run(schedule_expression):
    """Calculate next run time from cron expression"""
    # This is a simplified implementation
    # In production, use a proper cron parser like croniter
    try:
        # For now, assume daily backup at midnight
        if schedule_expression == "0 2 * * *":  # Daily at 2 AM
            next_run = datetime.utcnow().replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= datetime.utcnow():
                next_run += timedelta(days=1)
            return next_run
        elif schedule_expression == "0 2 * * 0":  # Weekly on Sunday at 2 AM
            next_run = datetime.utcnow().replace(hour=2, minute=0, second=0, microsecond=0)
            days_ahead = 6 - next_run.weekday()  # Sunday is 6
            if days_ahead <= 0:
                days_ahead += 7
            next_run += timedelta(days=days_ahead)
            return next_run
    except:
        pass

    return None


def get_backup_history(job):
    """Get backup history for a job"""
    # This would typically read from backup logs or database
    # For now, return a sample history
    return [
        {
            "date": datetime.utcnow() - timedelta(days=1),
            "status": "completed",
            "size": "1.2 GB",
            "duration": "15 minutes",
        },
        {
            "date": datetime.utcnow() - timedelta(days=2),
            "status": "completed",
            "size": "1.1 GB",
            "duration": "12 minutes",
        },
    ]


# Additional API Routes


@bp.route("/api/jobs/<int:job_id>/run", methods=["POST"])
@login_required
def api_run_job(job_id):
    """API endpoint to run a backup job"""
    try:
        job = BackupJob.query.get_or_404(job_id)

        # Here you would trigger the actual backup job
        job.status = BackupStatus.RUNNING
        job.last_run = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {"status": "success", "message": f'Backup job "{job.name}" started successfully'}
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route("/api/jobs/<int:job_id>", methods=["DELETE"])
@login_required
def api_delete_job(job_id):
    """API endpoint to delete a backup job"""
    try:
        job = BackupJob.query.get_or_404(job_id)
        job_name = job.name

        db.session.delete(job)
        db.session.commit()

        return jsonify(
            {"status": "success", "message": f'Backup job "{job_name}" deleted successfully'}
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
