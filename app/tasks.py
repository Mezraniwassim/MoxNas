"""Background tasks for MoxNAS"""
from celery import current_task
from datetime import datetime, timedelta
from app import db, make_celery
from app.models import (StorageDevice, StoragePool, BackupJob, SystemLog, LogLevel, 
                       BackupStatus, Alert, DeviceStatus, PoolStatus)
from app.storage.manager import storage_manager
import os
import subprocess
import shutil
import json

# This will be initialized when the worker starts
celery = None

@celery.task(bind=True)
def scan_storage_devices(self):
    """Background task to scan storage devices"""
    try:
        storage_manager.update_device_database()
        
        SystemLog.log_event(
            level=LogLevel.INFO,
            category='storage',
            message='Automated storage device scan completed'
        )
        
        return {'success': True, 'message': 'Device scan completed'}
    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='storage',
            message=f'Automated device scan failed: {str(e)}'
        )
        return {'success': False, 'error': str(e)}

@celery.task(bind=True)
def check_device_health(self):
    """Background task to check device SMART health"""
    try:
        devices = StorageDevice.query.all()
        issues_found = 0
        alerts_created = 0
        
        for device in devices:
            smart_data = storage_manager.get_smart_data(device.device_path)
            if smart_data:
                old_status = device.status
                device.update_smart_data(smart_data)
                
                # Check for health issues
                if smart_data.get('overall_health') != 'PASSED':
                    issues_found += 1
                    
                    # Create alert if status changed to failed
                    if old_status != DeviceStatus.SMART_FAIL and device.status == DeviceStatus.SMART_FAIL:
                        alert = Alert(
                            title=f'Device SMART Failure: {device.device_name}',
                            message=f'Device {device.device_path} has failed SMART tests. Immediate attention required.',
                            severity=LogLevel.CRITICAL,
                            category='storage',
                            auto_resolve=False
                        )
                        db.session.add(alert)
                        alerts_created += 1
                    
                    SystemLog.log_event(
                        level=LogLevel.WARNING,
                        category='storage',
                        message=f'Device health warning: {device.device_path} - {smart_data.get("overall_health", "unknown")}',
                        details={'device_id': device.id, 'smart_data': smart_data}
                    )
                
                # Check temperature warnings
                if device.temperature and device.temperature > 60:
                    SystemLog.log_event(
                        level=LogLevel.WARNING,
                        category='storage',
                        message=f'High temperature warning: {device.device_path} - {device.temperature}°C',
                        details={'device_id': device.id, 'temperature': device.temperature}
                    )
        
        db.session.commit()
        
        return {
            'success': True,
            'devices_checked': len(devices),
            'issues_found': issues_found,
            'alerts_created': alerts_created
        }
        
    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='storage',
            message=f'Device health check failed: {str(e)}'
        )
        return {'success': False, 'error': str(e)}

@celery.task(bind=True)
def run_backup_job(self, job_id):
    """Execute a backup job"""
    try:
        job = BackupJob.query.get(job_id)
        if not job:
            return {'success': False, 'error': 'Backup job not found'}
        
        # Update job status
        job.status = BackupStatus.RUNNING
        job.last_run = datetime.utcnow()
        job.error_message = None
        db.session.commit()
        
        SystemLog.log_event(
            level=LogLevel.INFO,
            category='backups',
            message=f'Backup job started: {job.name}',
            details={'job_id': job.id, 'task_id': self.request.id}
        )
        
        # Execute backup
        success, bytes_transferred, error_msg = execute_backup(job, self)
        
        if success:
            job.status = BackupStatus.COMPLETED
            job.bytes_backed_up = bytes_transferred
            job.retry_count = 0
            
            SystemLog.log_event(
                level=LogLevel.INFO,
                category='backups',
                message=f'Backup job completed: {job.name} - {format_bytes(bytes_transferred)}',
                details={'job_id': job.id, 'bytes_backed_up': bytes_transferred}
            )
        else:
            job.status = BackupStatus.FAILED
            job.error_message = error_msg
            job.retry_count += 1
            
            # Create alert for failed backup
            alert = Alert(
                title=f'Backup Failed: {job.name}',
                message=f'Backup job {job.name} failed: {error_msg}',
                severity=LogLevel.ERROR,
                category='backups',
                auto_resolve=False
            )
            db.session.add(alert)
            
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category='backups',
                message=f'Backup job failed: {job.name} - {error_msg}',
                details={'job_id': job.id, 'error': error_msg}
            )
        
        db.session.commit()
        
        return {
            'success': success,
            'job_id': job.id,
            'bytes_transferred': bytes_transferred,
            'error_message': error_msg if not success else None
        }
        
    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='backups',
            message=f'Backup job exception: {str(e)}',
            details={'job_id': job_id, 'task_id': self.request.id}
        )
        return {'success': False, 'error': str(e)}

@celery.task(bind=True)
def cleanup_old_logs(self):
    """Background task to clean up old log entries"""
    try:
        # Keep logs for 90 days
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        old_logs = SystemLog.query.filter(SystemLog.timestamp < cutoff_date).all()
        count = len(old_logs)
        
        for log in old_logs:
            db.session.delete(log)
        
        db.session.commit()
        
        SystemLog.log_event(
            level=LogLevel.INFO,
            category='system',
            message=f'Log cleanup completed: {count} old entries removed'
        )
        
        return {'success': True, 'logs_removed': count}
        
    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='system',
            message=f'Log cleanup failed: {str(e)}'
        )
        return {'success': False, 'error': str(e)}

def execute_backup(job, task):
    """Execute the actual backup operation"""
    try:
        # Ensure destination directory exists
        dest_dir = os.path.dirname(job.destination_path)
        os.makedirs(dest_dir, exist_ok=True)
        
        # Build rsync command
        cmd = ['rsync', '-av', '--delete']
        
        if job.compression:
            cmd.append('--compress')
        
        cmd.extend(['--progress', '--stats'])
        cmd.extend([job.source_path, job.destination_path])
        
        # Execute command
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            # Parse bytes transferred from rsync stats
            bytes_transferred = 0
            for line in stdout.split('\n'):
                if 'Total transferred file size:' in line:
                    try:
                        bytes_str = line.split(':')[1].strip().split()[0]
                        bytes_transferred = int(bytes_str.replace(',', ''))
                    except:
                        pass
            
            return True, bytes_transferred, None
        else:
            return False, 0, stderr or f'Backup failed with exit code {process.returncode}'
            
    except Exception as e:
        return False, 0, str(e)

def format_bytes(bytes_value):
    """Format bytes to human readable string"""
    if bytes_value == 0:
        return '0 B'
    
    sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while bytes_value >= 1024 and i < len(sizes) - 1:
        bytes_value /= 1024.0
        i += 1
    
    return f'{bytes_value:.1f} {sizes[i]}'