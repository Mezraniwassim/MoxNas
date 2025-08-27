"""Main dashboard routes"""
from flask import render_template, jsonify, request
from flask_login import login_required, current_user
from app.main import bp
from app.models import StoragePool, StorageDevice, Share, BackupJob, SystemLog
from app import db
import psutil
import json

@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with system overview"""
    # System statistics
    system_stats = {
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': psutil.virtual_memory(),
        'disk_usage': psutil.disk_usage('/'),
        'boot_time': psutil.boot_time(),
        'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else (0, 0, 0)
    }
    
    # Storage overview
    storage_pools = StoragePool.query.all()
    total_storage = sum(pool.total_size or 0 for pool in storage_pools)
    used_storage = sum(pool.used_size or 0 for pool in storage_pools)
    
    # Device health
    devices = StorageDevice.query.all()
    healthy_devices = len([d for d in devices if d.status.value == 'healthy'])
    warning_devices = len([d for d in devices if d.status.value == 'warning'])
    failed_devices = len([d for d in devices if d.status.value in ['failed', 'smart_fail']])
    
    # Shares status
    shares = Share.query.all()
    active_shares = len([s for s in shares if s.status.value == 'active'])
    inactive_shares = len([s for s in shares if s.status.value == 'inactive'])
    
    # Backup status
    backup_jobs = BackupJob.query.all()
    running_backups = len([b for b in backup_jobs if b.status.value == 'running'])
    failed_backups = len([b for b in backup_jobs if b.status.value == 'failed'])
    
    # Recent system logs (last 10)
    recent_logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(10).all()
    
    return render_template('dashboard.html',
                         system_stats=system_stats,
                         storage_pools=storage_pools,
                         total_storage=total_storage,
                         used_storage=used_storage,
                         devices_summary={
                             'healthy': healthy_devices,
                             'warning': warning_devices,
                             'failed': failed_devices
                         },
                         shares_summary={
                             'active': active_shares,
                             'inactive': inactive_shares
                         },
                         backup_summary={
                             'running': running_backups,
                             'failed': failed_backups
                         },
                         recent_logs=recent_logs)

@bp.route('/services')
@login_required
def services():
    """Services management page"""
    from app.services.manager import service_manager
    
    # Get basic service status for template context
    services_status = {}
    try:
        services_status = service_manager.get_all_nas_services_status()
    except Exception as e:
        current_app.logger.error(f'Failed to get services status: {str(e)}')
    
    return render_template('services/index.html', services_status=services_status)

@bp.route('/api/system/stats')
@login_required
def system_stats_api():
    """Real-time system statistics API"""
    stats = {
        'timestamp': psutil.time.time(),
        'cpu': {
            'percent': psutil.cpu_percent(interval=0.1),
            'count': psutil.cpu_count(),
            'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        },
        'memory': {
            'total': psutil.virtual_memory().total,
            'available': psutil.virtual_memory().available,
            'percent': psutil.virtual_memory().percent,
            'used': psutil.virtual_memory().used,
            'free': psutil.virtual_memory().free
        },
        'swap': {
            'total': psutil.swap_memory().total,
            'used': psutil.swap_memory().used,
            'free': psutil.swap_memory().free,
            'percent': psutil.swap_memory().percent
        },
        'disk': {
            'usage': {
                'total': psutil.disk_usage('/').total,
                'used': psutil.disk_usage('/').used,
                'free': psutil.disk_usage('/').free,
                'percent': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            },
            'io': psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else None
        },
        'network': {}
    }
    
    # Network interfaces
    net_io = psutil.net_io_counters(pernic=True)
    for interface, io_stats in net_io.items():
        if not interface.startswith('lo'):  # Skip loopback
            stats['network'][interface] = {
                'bytes_sent': io_stats.bytes_sent,
                'bytes_recv': io_stats.bytes_recv,
                'packets_sent': io_stats.packets_sent,
                'packets_recv': io_stats.packets_recv,
                'errin': io_stats.errin,
                'errout': io_stats.errout,
                'dropin': io_stats.dropin,
                'dropout': io_stats.dropout
            }
    
    # Load average (Unix-like systems)
    if hasattr(psutil, 'getloadavg'):
        stats['load_avg'] = psutil.getloadavg()
    
    return jsonify(stats)

@bp.route('/api/storage/overview')
@login_required
def storage_overview_api():
    """Storage overview API"""
    pools = StoragePool.query.all()
    devices = StorageDevice.query.all()
    
    pool_data = []
    for pool in pools:
        pool_devices = [d for d in devices if d.pool_id == pool.id]
        pool_data.append({
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
            'healthy_devices': len([d for d in pool_devices if d.status.value == 'healthy']),
            'warning_devices': len([d for d in pool_devices if d.status.value == 'warning']),
            'failed_devices': len([d for d in pool_devices if d.status.value in ['failed', 'smart_fail']])
        })
    
    return jsonify({
        'pools': pool_data,
        'total_pools': len(pools),
        'total_devices': len(devices),
        'healthy_devices': len([d for d in devices if d.status.value == 'healthy']),
        'warning_devices': len([d for d in devices if d.status.value == 'warning']),
        'failed_devices': len([d for d in devices if d.status.value in ['failed', 'smart_fail']])
    })

@bp.route('/about')
def about():
    """About page with system information"""
    return render_template('about.html')

@bp.route('/help')
def help():
    """Help page"""
    return render_template('help.html')