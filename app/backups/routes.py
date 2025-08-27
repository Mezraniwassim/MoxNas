"""Backup management routes"""
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.backups import bp
from app.models import BackupJob, BackupStatus, Dataset, SystemLog, LogLevel
from app import db
from datetime import datetime, timedelta
import os
import subprocess
from celery import current_app

@bp.route('/')
@login_required
def index():
    """Backup jobs overview page"""
    page = request.args.get('page', 1, type=int)
    jobs = BackupJob.query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Statistics
    total_jobs = BackupJob.query.count()
    running_jobs = BackupJob.query.filter_by(status=BackupStatus.RUNNING).count()
    failed_jobs = BackupJob.query.filter_by(status=BackupStatus.FAILED).count()
    
    return render_template('backups/index.html', 
                         jobs=jobs,
                         total_jobs=total_jobs,
                         running_jobs=running_jobs,
                         failed_jobs=failed_jobs)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new backup job"""
    if not current_user.is_admin():
        flash('Administrator privileges required to create backup jobs', 'danger')
        return redirect(url_for('backups.index'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            source_path = request.form.get('source_path', '').strip()
            destination_path = request.form.get('destination_path', '').strip()
            backup_type = request.form.get('backup_type', 'incremental')
            schedule = request.form.get('schedule', '').strip()
            retention_days = int(request.form.get('retention_days', 30))
            compression = request.form.get('compression') == 'on'
            encryption = request.form.get('encryption') == 'on'
            
            # Validation
            if not name:
                flash('Backup job name is required', 'danger')
                return redirect(url_for('backups.create'))
            
            if BackupJob.query.filter_by(name=name).first():
                flash('Backup job name already exists', 'danger')
                return redirect(url_for('backups.create'))
            
            if not source_path or not os.path.exists(source_path):
                flash('Valid source path is required', 'danger')
                return redirect(url_for('backups.create'))
            
            if not destination_path:
                flash('Destination path is required', 'danger')
                return redirect(url_for('backups.create'))
            
            # Create backup job
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
                created_by_id=current_user.id
            )
            
            # Calculate next run time if scheduled
            if schedule:
                job.next_run = calculate_next_run(schedule)
            
            db.session.add(job)
            db.session.commit()
            
            SystemLog.log_event(
                level=LogLevel.INFO,
                category='backups',
                message=f'Backup job created: {name} by {current_user.username}',
                user_id=current_user.id,
                ip_address=request.remote_addr,
                details={
                    'job_id': job.id,
                    'source': source_path,
                    'destination': destination_path
                }
            )
            
            flash(f'Backup job "{name}" created successfully', 'success')
            return redirect(url_for('backups.index'))
            
        except Exception as e:
            db.session.rollback()
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category='backups',
                message=f'Failed to create backup job: {str(e)}',
                user_id=current_user.id,
                ip_address=request.remote_addr
            )
            flash(f'Error creating backup job: {str(e)}', 'danger')
            return redirect(url_for('backups.create'))
    
    # GET request - show create form
    datasets = Dataset.query.all()
    backup_types = ['full', 'incremental', 'differential']
    
    return render_template('backups/create.html', 
                         datasets=datasets,
                         backup_types=backup_types)

@bp.route('/<int:job_id>')
@login_required
def detail(job_id):
    """Backup job detail page"""
    job = BackupJob.query.get_or_404(job_id)
    
    # Get backup history/logs
    backup_history = get_backup_history(job)
    
    return render_template('backups/detail.html', 
                         job=job,
                         backup_history=backup_history)

@bp.route('/<int:job_id>/start', methods=['POST'])
@login_required
def start(job_id):
    """Start backup job manually"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Administrator privileges required'}), 403
    
    job = BackupJob.query.get_or_404(job_id)
    
    if job.status == BackupStatus.RUNNING:
        return jsonify({'success': False, 'error': 'Backup job is already running'}), 400
    
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
            category='backups',
            message=f'Backup job started: {job.name} by {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={'job_id': job.id, 'task_id': task.id}
        )
        
        return jsonify({
            'success': True, 
            'message': f'Backup job "{job.name}" started successfully',
            'task_id': task.id
        })
        
    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='backups',
            message=f'Error starting backup job {job.name}: {str(e)}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:job_id>/stop', methods=['POST'])
@login_required
def stop(job_id):
    """Stop running backup job"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Administrator privileges required'}), 403
    
    job = BackupJob.query.get_or_404(job_id)
    
    if job.status != BackupStatus.RUNNING:
        return jsonify({'success': False, 'error': 'Backup job is not running'}), 400
    
    try:
        # TODO: Implement task cancellation
        # For now, just update status
        job.status = BackupStatus.CANCELLED
        job.error_message = f'Cancelled by {current_user.username}'
        db.session.commit()
        
        SystemLog.log_event(
            level=LogLevel.WARNING,
            category='backups',
            message=f'Backup job stopped: {job.name} by {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={'job_id': job.id}
        )
        
        return jsonify({
            'success': True, 
            'message': f'Backup job "{job.name}" stopped successfully'
        })
        
    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='backups',
            message=f'Error stopping backup job {job.name}: {str(e)}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/<int:job_id>/delete', methods=['POST'])
@login_required
def delete(job_id):
    """Delete backup job"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Administrator privileges required'}), 403
    
    job = BackupJob.query.get_or_404(job_id)
    
    if job.status == BackupStatus.RUNNING:
        return jsonify({'success': False, 'error': 'Cannot delete running backup job'}), 400
    
    try:
        job_name = job.name
        db.session.delete(job)
        db.session.commit()
        
        SystemLog.log_event(
            level=LogLevel.WARNING,
            category='backups',
            message=f'Backup job deleted: {job_name} by {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={'job_name': job_name}
        )
        
        return jsonify({
            'success': True, 
            'message': f'Backup job "{job_name}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='backups',
            message=f'Error deleting backup job {job.name}: {str(e)}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/status')
@login_required
def api_status():
    """API endpoint for backup status summary"""
    jobs = BackupJob.query.all()
    
    status_summary = {
        'total_jobs': len(jobs),
        'scheduled': len([j for j in jobs if j.status == BackupStatus.SCHEDULED]),
        'running': len([j for j in jobs if j.status == BackupStatus.RUNNING]),
        'completed': len([j for j in jobs if j.status == BackupStatus.COMPLETED]),
        'failed': len([j for j in jobs if j.status == BackupStatus.FAILED]),
        'jobs': []
    }
    
    for job in jobs:
        status_summary['jobs'].append({
            'id': job.id,
            'name': job.name,
            'status': job.status.value,
            'last_run': job.last_run.isoformat() if job.last_run else None,
            'next_run': job.next_run.isoformat() if job.next_run else None,
            'bytes_backed_up': job.bytes_backed_up,
            'error_message': job.error_message
        })
    
    return jsonify(status_summary)

def calculate_next_run(schedule_expression):
    """Calculate next run time from cron expression"""
    # This is a simplified implementation
    # In production, use a proper cron parser like croniter
    try:
        # For now, assume daily backup at midnight
        if schedule_expression == '0 2 * * *':  # Daily at 2 AM
            next_run = datetime.utcnow().replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= datetime.utcnow():
                next_run += timedelta(days=1)
            return next_run
        elif schedule_expression == '0 2 * * 0':  # Weekly on Sunday at 2 AM
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
            'date': datetime.utcnow() - timedelta(days=1),
            'status': 'completed',
            'size': '1.2 GB',
            'duration': '15 minutes'
        },
        {
            'date': datetime.utcnow() - timedelta(days=2),
            'status': 'completed', 
            'size': '1.1 GB',
            'duration': '12 minutes'
        }
    ]