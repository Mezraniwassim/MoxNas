"""RESTful API routes for MoxNAS"""
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from app.api import bp
from app.models import (User, StorageDevice, StoragePool, Dataset, Share, BackupJob,
                       SystemLog, LogLevel, UserRole, DeviceStatus, PoolStatus, ShareStatus)
from app import db, limiter
from app.storage.manager import storage_manager
from datetime import datetime
import json

# Authentication API
@bp.route('/auth/login', methods=['POST'])
@limiter.limit('10 per minute')
def api_login():
    """API login endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            # In a real API, you would generate a JWT token here
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role.value,
                    'last_login': user.last_login.isoformat() if user.last_login else None
                }
            })
        else:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category='auth',
                message=f'API login failed for user: {username}',
                ip_address=request.remote_addr
            )
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/auth/user', methods=['GET'])
@login_required
def api_current_user():
    """Get current user information"""
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'role': current_user.role.value,
        'last_login': current_user.last_login.isoformat() if current_user.last_login else None,
        'totp_enabled': current_user.totp_enabled
    })

# Storage API
@bp.route('/storage/devices', methods=['GET'])
@login_required
def api_storage_devices():
    """Get storage devices"""
    try:
        devices = StorageDevice.query.all()
        
        devices_data = []
        for device in devices:
            devices_data.append({
                'id': device.id,
                'path': device.device_path,
                'name': device.device_name,
                'model': device.device_model,
                'serial': device.device_serial,
                'size': device.device_size,
                'status': device.status.value,
                'temperature': device.temperature,
                'power_on_hours': device.power_on_hours,
                'pool_id': device.pool_id,
                'pool_name': device.pool.name if device.pool else None,
                'smart_data': device.get_smart_data(),
                'created_at': device.created_at.isoformat(),
                'updated_at': device.updated_at.isoformat()
            })
        
        return jsonify({
            'devices': devices_data,
            'total': len(devices_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/storage/devices/scan', methods=['POST'])
@login_required
@limiter.limit('1 per minute')
def api_scan_devices():
    """Scan for storage devices"""
    if not current_user.is_admin():
        return jsonify({'error': 'Administrator privileges required'}), 403
    
    try:
        storage_manager.update_device_database()
        
        SystemLog.log_event(
            level=LogLevel.INFO,
            category='storage',
            message=f'Device scan initiated via API by {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        
        return jsonify({'success': True, 'message': 'Device scan completed'})
        
    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='storage',
            message=f'API device scan failed: {str(e)}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        return jsonify({'error': str(e)}), 500

@bp.route('/storage/pools', methods=['GET'])
@login_required
def api_storage_pools():
    """Get storage pools"""
    try:
        pools = StoragePool.query.all()
        
        pools_data = []
        for pool in pools:
            pool_devices = [d for d in pool.devices]
            pools_data.append({
                'id': pool.id,
                'name': pool.name,
                'raid_level': pool.raid_level,
                'filesystem_type': pool.filesystem_type,
                'mount_point': pool.mount_point,
                'total_size': pool.total_size,
                'used_size': pool.used_size,
                'available_size': pool.available_size,
                'status': pool.status.value,
                'device_count': len(pool_devices),
                'devices': [{'id': d.id, 'path': d.device_path, 'status': d.status.value} for d in pool_devices],
                'last_scrub': pool.last_scrub.isoformat() if pool.last_scrub else None,
                'created_at': pool.created_at.isoformat(),
                'created_by': pool.created_by.username if pool.created_by else None
            })
        
        return jsonify({
            'pools': pools_data,
            'total': len(pools_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/storage/pools', methods=['POST'])
@login_required
def api_create_pool():
    """Create storage pool"""
    if not current_user.is_admin():
        return jsonify({'error': 'Administrator privileges required'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        name = data.get('name', '').strip()
        raid_level = data.get('raid_level')
        filesystem = data.get('filesystem', 'ext4')
        device_paths = data.get('devices', [])
        
        # Validation
        if not name or not raid_level or not device_paths:
            return jsonify({'error': 'Name, RAID level, and devices are required'}), 400
        
        if StoragePool.query.filter_by(name=name).first():
            return jsonify({'error': 'Pool name already exists'}), 409
        
        # Create RAID array
        success, message = storage_manager.create_raid_array(
            name=name,
            level=raid_level,
            devices=device_paths,
            filesystem=filesystem
        )
        
        if not success:
            return jsonify({'error': message}), 500
        
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
        db.session.flush()
        
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
            message=f'Storage pool created via API: {name} by {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={'pool_id': pool.id, 'raid_level': raid_level, 'devices': device_paths}
        )
        
        return jsonify({
            'success': True,
            'pool': {
                'id': pool.id,
                'name': pool.name,
                'raid_level': pool.raid_level,
                'status': pool.status.value,
                'total_size': pool.total_size
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='storage',
            message=f'API pool creation failed: {str(e)}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        return jsonify({'error': str(e)}), 500

@bp.route('/storage/pools/<int:pool_id>', methods=['GET'])
@login_required
def api_pool_detail(pool_id):
    """Get pool details"""
    try:
        pool = StoragePool.query.get_or_404(pool_id)
        
        # Get pool status from system
        pool_status = storage_manager.get_raid_status(pool)
        
        return jsonify({
            'id': pool.id,
            'name': pool.name,
            'raid_level': pool.raid_level,
            'filesystem_type': pool.filesystem_type,
            'mount_point': pool.mount_point,
            'total_size': pool.total_size,
            'used_size': pool.used_size,
            'available_size': pool.available_size,
            'status': pool.status.value,
            'system_status': pool_status,
            'devices': [{
                'id': d.id,
                'path': d.device_path,
                'name': d.device_name,
                'status': d.status.value,
                'temperature': d.temperature
            } for d in pool.devices],
            'datasets_count': pool.datasets.count(),
            'last_scrub': pool.last_scrub.isoformat() if pool.last_scrub else None,
            'created_at': pool.created_at.isoformat(),
            'created_by': pool.created_by.username if pool.created_by else None
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Shares API
@bp.route('/shares', methods=['GET'])
@login_required
def api_shares():
    """Get network shares"""
    try:
        shares = Share.query.all()
        
        shares_data = []
        for share in shares:
            shares_data.append({
                'id': share.id,
                'name': share.name,
                'protocol': share.protocol.value,
                'dataset_id': share.dataset_id,
                'dataset_name': share.dataset.name,
                'dataset_path': share.dataset.path,
                'owner': share.owner.username,
                'guest_access': share.guest_access,
                'read_only': share.read_only,
                'status': share.status.value,
                'allowed_hosts': share.get_allowed_hosts(),
                'bytes_transferred': share.bytes_transferred,
                'connections_count': share.connections_count,
                'last_access': share.last_access.isoformat() if share.last_access else None,
                'created_at': share.created_at.isoformat(),
                'created_by': share.created_by.username if share.created_by else None
            })
        
        return jsonify({
            'shares': shares_data,
            'total': len(shares_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/shares', methods=['POST'])
@login_required
def api_create_share():
    """Create network share"""
    if not current_user.is_admin():
        return jsonify({'error': 'Administrator privileges required'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        name = data.get('name', '').strip()
        protocol = data.get('protocol')
        dataset_id = data.get('dataset_id')
        guest_access = data.get('guest_access', False)
        read_only = data.get('read_only', False)
        allowed_hosts = data.get('allowed_hosts', [])
        
        # Validation
        if not name or not protocol or not dataset_id:
            return jsonify({'error': 'Name, protocol, and dataset are required'}), 400
        
        if Share.query.filter_by(name=name).first():
            return jsonify({'error': 'Share name already exists'}), 409
        
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return jsonify({'error': 'Dataset not found'}), 404
        
        # Create share
        from app.models import ShareProtocol
        share = Share(
            name=name,
            protocol=ShareProtocol(protocol),
            dataset_id=dataset_id,
            owner_id=current_user.id,
            guest_access=guest_access,
            read_only=read_only,
            status=ShareStatus.INACTIVE,
            created_by_id=current_user.id
        )
        
        if allowed_hosts:
            share.set_allowed_hosts(allowed_hosts)
        
        db.session.add(share)
        db.session.commit()
        
        SystemLog.log_event(
            level=LogLevel.INFO,
            category='shares',
            message=f'Share created via API: {name} by {current_user.username}',
            user_id=current_user.id,
            ip_address=request.remote_addr,
            details={'share_id': share.id, 'protocol': protocol}
        )
        
        return jsonify({
            'success': True,
            'share': {
                'id': share.id,
                'name': share.name,
                'protocol': share.protocol.value,
                'status': share.status.value
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category='shares',
            message=f'API share creation failed: {str(e)}',
            user_id=current_user.id,
            ip_address=request.remote_addr
        )
        return jsonify({'error': str(e)}), 500

# Backup API
@bp.route('/backups', methods=['GET'])
@login_required
def api_backup_jobs():
    """Get backup jobs"""
    try:
        jobs = BackupJob.query.all()
        
        jobs_data = []
        for job in jobs:
            jobs_data.append({
                'id': job.id,
                'name': job.name,
                'source_path': job.source_path,
                'destination_path': job.destination_path,
                'backup_type': job.backup_type,
                'schedule': job.schedule,
                'status': job.status.value,
                'last_run': job.last_run.isoformat() if job.last_run else None,
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'bytes_backed_up': job.bytes_backed_up,
                'retention_days': job.retention_days,
                'compression': job.compression,
                'encryption': job.encryption,
                'error_message': job.error_message,
                'created_at': job.created_at.isoformat(),
                'created_by': job.created_by_user.username if job.created_by_user else None
            })
        
        return jsonify({
            'jobs': jobs_data,
            'total': len(jobs_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Monitoring API
@bp.route('/monitoring/system', methods=['GET'])
@login_required
def api_monitoring_system():
    """Get system monitoring data"""
    try:
        import psutil
        
        # Get system metrics
        system_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'cpu': {
                'percent': psutil.cpu_percent(interval=0.1),
                'count': psutil.cpu_count(),
                'load_avg': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'percent': psutil.virtual_memory().percent,
                'used': psutil.virtual_memory().used
            },
            'disk': {
                'usage': {},
                'io': {}
            },
            'network': {},
            'processes': len(psutil.pids()),
            'uptime': (datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds()
        }
        
        # Disk usage
        for partition in psutil.disk_partitions():
            if partition.fstype and not partition.mountpoint.startswith('/snap'):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    system_data['disk']['usage'][partition.mountpoint] = {
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
                    }
                except PermissionError:
                    continue
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        if disk_io:
            system_data['disk']['io'] = {
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count
            }
        
        # Network I/O
        net_io = psutil.net_io_counters(pernic=True)
        for interface, stats in net_io.items():
            if not interface.startswith('lo'):
                system_data['network'][interface] = {
                    'bytes_sent': stats.bytes_sent,
                    'bytes_recv': stats.bytes_recv,
                    'packets_sent': stats.packets_sent,
                    'packets_recv': stats.packets_recv
                }
        
        return jsonify(system_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/monitoring/alerts', methods=['GET'])
@login_required
def api_monitoring_alerts():
    """Get active alerts"""
    try:
        alerts = Alert.query.filter_by(is_active=True).order_by(
            Alert.created_at.desc()
        ).limit(20).all()
        
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity.value,
                'category': alert.category,
                'created_at': alert.created_at.isoformat(),
                'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                'acknowledged_by': alert.acknowledged_by.username if alert.acknowledged_by else None
            })
        
        return jsonify({
            'alerts': alerts_data,
            'total': len(alerts_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# System logs API
@bp.route('/logs', methods=['GET'])
@login_required
def api_logs():
    """Get system logs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        level = request.args.get('level')
        category = request.args.get('category')
        
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
            logs_data.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'level': log.level.value,
                'category': log.category,
                'message': log.message,
                'user': log.user.username if log.user else None,
                'ip_address': log.ip_address,
                'details': log.get_details()
            })
        
        return jsonify({
            'logs': logs_data,
            'pagination': {
                'page': logs.page,
                'pages': logs.pages,
                'per_page': logs.per_page,
                'total': logs.total,
                'has_next': logs.has_next,
                'has_prev': logs.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500