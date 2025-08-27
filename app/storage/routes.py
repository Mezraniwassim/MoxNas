"""Storage management routes"""
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.storage import bp
from app.storage.manager import storage_manager
from app.models import (StoragePool, StorageDevice, Dataset, PoolStatus, 
                       DeviceStatus, SystemLog, LogLevel, UserRole)
from app import db
from datetime import datetime

@bp.route('/')
@login_required
def index():
    \"\"\"Storage overview page\"\"\"
    pools = StoragePool.query.all()
    devices = StorageDevice.query.all()
    
    # Statistics
    total_capacity = sum(pool.total_size or 0 for pool in pools)
    used_capacity = sum(pool.used_size or 0 for pool in pools)
    available_capacity = total_capacity - used_capacity
    
    # Device status counts
    device_counts = {
        'total': len(devices),
        'healthy': len([d for d in devices if d.status == DeviceStatus.HEALTHY]),
        'warning': len([d for d in devices if d.status == DeviceStatus.WARNING]),
        'failed': len([d for d in devices if d.status in [DeviceStatus.FAILED, DeviceStatus.SMART_FAIL]])
    }
    
    return render_template('storage/index.html', 
                         pools=pools,
                         devices=devices,
                         total_capacity=total_capacity,
                         used_capacity=used_capacity,
                         available_capacity=available_capacity,
                         device_counts=device_counts)

@bp.route('/devices')
@login_required
def devices():
    \"\"\"Storage devices page\"\"\"
    page = request.args.get('page', 1, type=int)
    devices = StorageDevice.query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('storage/devices.html', devices=devices)

@bp.route('/devices/scan', methods=['POST'])
@login_required
def scan_devices():
    \"\"\"Scan for new storage devices\"\"\"
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Administrator privileges required'}), 403
    
    try:
        storage_manager.update_device_database()
        
        SystemLog.log_event(
            level=LogLevel.INFO,
            category='storage',
            message=f'Storage device scan initiated by {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        
        return jsonify({'success': True, 'message': 'Device scan completed successfully'})
        
    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='storage',
            message=f'Device scan failed: {str(e)}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/devices/<int:device_id>/smart')
@login_required
def device_smart_data(device_id):
    \"\"\"Get SMART data for a specific device\"\"\"
    device = StorageDevice.query.get_or_404(device_id)
    
    # Get fresh SMART data
    smart_data = storage_manager.get_smart_data(device.device_path)
    
    if smart_data:
        # Update database with fresh data
        device.update_smart_data(smart_data)
        db.session.commit()
    
    return jsonify({
        'device_id': device.id,
        'device_path': device.device_path,
        'smart_data': device.get_smart_data(),
        'status': device.status.value,
        'temperature': device.temperature,
        'power_on_hours': device.power_on_hours
    })

@bp.route('/pools')
@login_required
def pools():
    \"\"\"Storage pools page\"\"\"
    page = request.args.get('page', 1, type=int)
    pools = StoragePool.query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('storage/pools.html', pools=pools)

@bp.route('/pools/create', methods=['GET', 'POST'])
@login_required
def create_pool():
    \"\"\"Create new storage pool\"\"\"
    if not current_user.is_admin():
        flash('Administrator privileges required to create storage pools', 'danger')
        return redirect(url_for('storage.pools'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            raid_level = request.form.get('raid_level')
            filesystem = request.form.get('filesystem', 'ext4')
            device_paths = request.form.getlist('devices')
            
            # Validation
            if not name:
                flash('Pool name is required', 'danger')
                return redirect(url_for('storage.create_pool'))
            
            if StoragePool.query.filter_by(name=name).first():
                flash('Pool name already exists', 'danger')
                return redirect(url_for('storage.create_pool'))
            
            if not device_paths:
                flash('At least one device is required', 'danger')
                return redirect(url_for('storage.create_pool'))
            
            # Create RAID array
            success, message = storage_manager.create_raid_array(
                name=name,
                level=raid_level,
                devices=device_paths,
                filesystem=filesystem
            )
            
            if not success:
                flash(f'Failed to create storage pool: {message}', 'danger')
                return redirect(url_for('storage.create_pool'))
            
            # Create database record
            pool = StoragePool(
                name=name,
                raid_level=raid_level,
                filesystem_type=filesystem,
                mount_point=f'/mnt/{name}',
                status=PoolStatus.HEALTHY,
                created_by_id=current_user.id
            )
            
            db.session.add(pool)
            db.session.flush()  # Get pool ID
            
            # Associate devices with pool
            for device_path in device_paths:
                device = StorageDevice.query.filter_by(device_path=device_path).first()
                if device:
                    device.pool_id = pool.id
            
            # Calculate pool size
            raid_device = f'/dev/md/{name}'
            pool.total_size = storage_manager._get_device_size(raid_device)
            pool.available_size = pool.total_size
            
            db.session.commit()
            
            SystemLog.log_event(
                level=LogLevel.INFO,
                category='storage',
                message=f'Storage pool created: {name} ({raid_level}) by {current_user.username}',
                user_id=current_user.id,
                ip_address=request.remote_addr,
                details={
                    'pool_id': pool.id,
                    'raid_level': raid_level,
                    'devices': device_paths
                }
            )
            
            flash(f'Storage pool \"{name}\" created successfully', 'success')
            return redirect(url_for('storage.pools'))
            
        except Exception as e:
            db.session.rollback()
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category='storage',
                message=f'Failed to create storage pool: {str(e)}',
                user_id=current_user.id,
                ip_address=request.remote_addr
            )
            flash(f'Error creating storage pool: {str(e)}', 'danger')
            return redirect(url_for('storage.create_pool'))
    
    # GET request - show create form
    # Get available devices (not in any pool)
    available_devices = StorageDevice.query.filter_by(pool_id=None).all()
    
    return render_template('storage/create_pool.html', 
                         available_devices=available_devices)

@bp.route('/pools/<int:pool_id>')
@login_required
def pool_detail(pool_id):
    \"\"\"Storage pool detail page\"\"\"
    pool = StoragePool.query.get_or_404(pool_id)
    
    # Get pool status from system
    pool_status = storage_manager.get_raid_status(pool)
    
    return render_template('storage/pool_detail.html', 
                         pool=pool, 
                         pool_status=pool_status)

@bp.route('/pools/<int:pool_id>/scrub', methods=['POST'])
@login_required
def start_pool_scrub(pool_id):
    \"\"\"Start scrubbing a storage pool\"\"\"
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Administrator privileges required'}), 403
    
    pool = StoragePool.query.get_or_404(pool_id)
    
    try:
        success, message = storage_manager.scrub_raid_array(pool)
        
        if success:
            pool.status = PoolStatus.SCRUBBING
            pool.scrub_progress = 0
            db.session.commit()
            
            SystemLog.log_event(
                level=LogLevel.INFO,
                category='storage',
                message=f'Scrub started for pool {pool.name} by {current_user.username}',
                user_id=current_user.id,
                ip_address=request.remote_addr,
                details={'pool_id': pool.id}
            )
            
            return jsonify({'success': True, 'message': message})
        else:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category='storage',
                message=f'Failed to start scrub for pool {pool.name}: {message}',
                user_id=current_user.id,
                ip_address=request.remote_addr
            )
            return jsonify({'success': False, 'error': message}), 500
            
    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='storage',
            message=f'Error starting scrub for pool {pool.name}: {str(e)}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/pools/<int:pool_id>/delete', methods=['POST'])
@login_required
def delete_pool(pool_id):
    \"\"\"Delete a storage pool\"\"\"
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Administrator privileges required'}), 403
    
    pool = StoragePool.query.get_or_404(pool_id)
    
    # Check if pool has any datasets
    if pool.datasets.count() > 0:
        return jsonify({'success': False, 'error': 'Cannot delete pool with datasets'}), 400
    
    try:
        success, message = storage_manager.delete_raid_array(pool)
        
        if success:
            # Remove pool from database
            pool_name = pool.name
            
            # Free up devices
            for device in pool.devices:
                device.pool_id = None
            
            db.session.delete(pool)
            db.session.commit()
            
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='storage',
                message=f'Storage pool deleted: {pool_name} by {current_user.username}',
                user_id=current_user.id,
                ip_address=request.remote_addr,
                details={'pool_name': pool_name}
            )
            
            return jsonify({'success': True, 'message': f'Pool \"{pool_name}\" deleted successfully'})
        else:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category='storage',
                message=f'Failed to delete pool {pool.name}: {message}',
                user_id=current_user.id,
                ip_address=request.remote_addr
            )
            return jsonify({'success': False, 'error': message}), 500
            
    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='storage',
            message=f'Error deleting pool {pool.name}: {str(e)}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/datasets')
@login_required
def datasets():
    \"\"\"Datasets page\"\"\"
    page = request.args.get('page', 1, type=int)
    datasets = Dataset.query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('storage/datasets.html', datasets=datasets)

@bp.route('/datasets/create', methods=['GET', 'POST'])
@login_required
def create_dataset():
    \"\"\"Create new dataset\"\"\"
    if not current_user.is_admin():
        flash('Administrator privileges required to create datasets', 'danger')
        return redirect(url_for('storage.datasets'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            pool_id = int(request.form.get('pool_id'))
            quota_size = request.form.get('quota_size', type=int)
            
            # Validation
            if not name:
                flash('Dataset name is required', 'danger')
                return redirect(url_for('storage.create_dataset'))
            
            pool = StoragePool.query.get(pool_id)
            if not pool:
                flash('Invalid storage pool selected', 'danger')
                return redirect(url_for('storage.create_dataset'))
            
            # Create dataset path
            dataset_path = f'{pool.mount_point}/{name}'
            
            # Check if path already exists
            if Dataset.query.filter_by(path=dataset_path).first():
                flash('Dataset path already exists', 'danger')
                return redirect(url_for('storage.create_dataset'))
            
            # Create directory
            import os
            os.makedirs(dataset_path, mode=0o755, exist_ok=False)
            
            # Create database record
            dataset = Dataset(
                name=name,
                path=dataset_path,
                pool_id=pool_id,
                quota_size=quota_size,
                created_by_id=current_user.id
            )
            
            db.session.add(dataset)
            db.session.commit()
            
            SystemLog.log_event(
                level=LogLevel.INFO,
                category='storage',
                message=f'Dataset created: {name} on pool {pool.name} by {current_user.username}',
                user_id=current_user.id,
                ip_address=request.remote_addr,
                details={
                    'dataset_id': dataset.id,
                    'pool_id': pool_id,
                    'path': dataset_path
                }
            )
            
            flash(f'Dataset \"{name}\" created successfully', 'success')
            return redirect(url_for('storage.datasets'))
            
        except Exception as e:
            db.session.rollback()
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category='storage',
                message=f'Failed to create dataset: {str(e)}',
                user_id=current_user.id,
                ip_address=request.remote_addr
            )
            flash(f'Error creating dataset: {str(e)}', 'danger')
            return redirect(url_for('storage.create_dataset'))
    
    # GET request - show create form
    pools = StoragePool.query.filter_by(status=PoolStatus.HEALTHY).all()
    return render_template('storage/create_dataset.html', pools=pools)

@bp.route('/api/pools/<int:pool_id>/status')
@login_required
def api_pool_status(pool_id):
    \"\"\"API endpoint for pool status\"\"\"
    pool = StoragePool.query.get_or_404(pool_id)
    status = storage_manager.get_raid_status(pool)
    
    return jsonify({
        'pool_id': pool_id,
        'name': pool.name,
        'status': status,
        'last_updated': datetime.utcnow().isoformat()
    })

@bp.route('/api/devices/health')
@login_required
def api_device_health():
    \"\"\"API endpoint for device health overview\"\"\"
    devices = StorageDevice.query.all()
    
    health_summary = {
        'total_devices': len(devices),
        'healthy_devices': 0,
        'warning_devices': 0,
        'failed_devices': 0,
        'devices': []
    }
    
    for device in devices:
        device_data = {
            'id': device.id,
            'path': device.device_path,
            'name': device.device_name,
            'model': device.device_model,
            'status': device.status.value,
            'temperature': device.temperature,
            'power_on_hours': device.power_on_hours,
            'pool_name': device.pool.name if device.pool else None
        }
        
        health_summary['devices'].append(device_data)
        
        if device.status == DeviceStatus.HEALTHY:
            health_summary['healthy_devices'] += 1
        elif device.status == DeviceStatus.WARNING:
            health_summary['warning_devices'] += 1
        else:
            health_summary['failed_devices'] += 1
    
    return jsonify(health_summary)