"""Monitoring and metrics routes"""
from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from app.monitoring import bp
from app.models import SystemLog, Alert, StorageDevice, StoragePool, Share
from app import db
import psutil
import json
import os
from datetime import datetime, timedelta

@bp.route('/')
@login_required
def index():
    """Monitoring dashboard"""
    # System overview
    system_info = get_system_info()
    
    # Recent alerts
    recent_alerts = Alert.query.filter_by(is_active=True).order_by(
        Alert.created_at.desc()
    ).limit(10).all()
    
    # Storage health
    devices = StorageDevice.query.all()
    pools = StoragePool.query.all()
    
    return render_template('monitoring/index.html',
                         system_info=system_info,
                         recent_alerts=recent_alerts,
                         devices=devices,
                         pools=pools)

@bp.route('/logs')
@login_required
def logs():
    """System logs page"""
    page = request.args.get('page', 1, type=int)
    level_filter = request.args.get('level')
    category_filter = request.args.get('category')
    
    query = SystemLog.query
    
    if level_filter:
        query = query.filter_by(level=level_filter)
    
    if category_filter:
        query = query.filter_by(category=category_filter)
    
    logs = query.order_by(SystemLog.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    
    # Get unique categories and levels for filters
    categories = db.session.query(SystemLog.category).distinct().all()
    categories = [c[0] for c in categories]
    
    from app.models import LogLevel
    levels = [level.value for level in LogLevel]
    
    return render_template('monitoring/logs.html',
                         logs=logs,
                         categories=categories,
                         levels=levels,
                         current_level=level_filter,
                         current_category=category_filter)

@bp.route('/alerts')
@login_required
def alerts():
    """System alerts page"""
    page = request.args.get('page', 1, type=int)
    show_all = request.args.get('show_all', False, type=bool)
    
    query = Alert.query
    if not show_all:
        query = query.filter_by(is_active=True)
    
    alerts = query.order_by(Alert.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('monitoring/alerts.html',
                         alerts=alerts,
                         show_all=show_all)

@bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@login_required
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Administrator privileges required'}), 403
    
    alert = Alert.query.get_or_404(alert_id)
    
    try:
        alert.acknowledge(current_user.id)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Alert acknowledged successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/performance')
@login_required
def performance():
    """Performance monitoring page"""
    # Get performance metrics
    performance_data = get_performance_metrics()
    
    return render_template('monitoring/performance.html',
                         performance_data=performance_data)

@bp.route('/api/system/metrics')
@login_required
def api_system_metrics():
    """Real-time system metrics API"""
    try:
        metrics = {
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
                'used': psutil.virtual_memory().used,
                'free': psutil.virtual_memory().free
            },
            'swap': {
                'total': psutil.swap_memory().total,
                'used': psutil.swap_memory().used,
                'free': psutil.swap_memory().free,
                'percent': psutil.swap_memory().percent
            },
            'disk': get_disk_metrics(),
            'network': get_network_metrics(),
            'processes': {
                'total': len(psutil.pids()),
                'running': len([p for p in psutil.process_iter(['status']) if p.info['status'] == 'running']),
                'sleeping': len([p for p in psutil.process_iter(['status']) if p.info['status'] == 'sleeping'])
            }
        }
        
        return jsonify(metrics)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/storage/health')
@login_required
def api_storage_health():
    """Storage health metrics API"""
    try:
        devices = StorageDevice.query.all()
        pools = StoragePool.query.all()
        
        health_data = {
            'devices': [],
            'pools': [],
            'summary': {
                'total_devices': len(devices),
                'healthy_devices': 0,
                'warning_devices': 0,
                'failed_devices': 0,
                'total_pools': len(pools),
                'healthy_pools': 0,
                'degraded_pools': 0,
                'failed_pools': 0
            }
        }
        
        # Process devices
        for device in devices:
            device_data = {
                'id': device.id,
                'path': device.device_path,
                'name': device.device_name,
                'model': device.device_model,
                'size': device.device_size,
                'status': device.status.value,
                'temperature': device.temperature,
                'smart_status': device.get_smart_data().get('overall_health', 'unknown')
            }
            health_data['devices'].append(device_data)
            
            # Update summary
            if device.status.value == 'healthy':
                health_data['summary']['healthy_devices'] += 1
            elif device.status.value == 'warning':
                health_data['summary']['warning_devices'] += 1
            else:
                health_data['summary']['failed_devices'] += 1
        
        # Process pools
        for pool in pools:
            pool_data = {
                'id': pool.id,
                'name': pool.name,
                'status': pool.status.value,
                'raid_level': pool.raid_level,
                'total_size': pool.total_size,
                'used_size': pool.used_size,
                'device_count': pool.devices.count()
            }
            health_data['pools'].append(pool_data)
            
            # Update summary
            if pool.status.value == 'healthy':
                health_data['summary']['healthy_pools'] += 1
            elif pool.status.value == 'degraded':
                health_data['summary']['degraded_pools'] += 1
            else:
                health_data['summary']['failed_pools'] += 1
        
        return jsonify(health_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/network/activity')
@login_required
def api_network_activity():
    """Network activity metrics API"""
    try:
        shares = Share.query.all()
        
        activity_data = {
            'shares': [],
            'protocols': {
                'smb': {'active': 0, 'connections': 0},
                'nfs': {'active': 0, 'connections': 0},
                'ftp': {'active': 0, 'connections': 0}
            }
        }
        
        for share in shares:
            share_data = {
                'id': share.id,
                'name': share.name,
                'protocol': share.protocol.value,
                'status': share.status.value,
                'bytes_transferred': share.bytes_transferred,
                'connections_count': share.connections_count,
                'last_access': share.last_access.isoformat() if share.last_access else None
            }
            activity_data['shares'].append(share_data)
            
            # Update protocol summary
            protocol = share.protocol.value
            if share.status.value == 'active':
                activity_data['protocols'][protocol]['active'] += 1
            activity_data['protocols'][protocol]['connections'] += share.connections_count
        
        return jsonify(activity_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_system_info():
    """Get comprehensive system information"""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        return {
            'hostname': os.uname().nodename,
            'platform': f"{os.uname().sysname} {os.uname().release}",
            'architecture': os.uname().machine,
            'boot_time': boot_time,
            'uptime': str(uptime).split('.')[0],  # Remove microseconds
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'disk_total': sum([psutil.disk_usage(p.mountpoint).total 
                             for p in psutil.disk_partitions() 
                             if p.fstype and not p.mountpoint.startswith('/snap')])
        }
    except Exception as e:
        return {'error': str(e)}

def get_performance_metrics():
    """Get detailed performance metrics"""
    try:
        # CPU usage per core
        cpu_per_core = psutil.cpu_percent(percpu=True)
        
        # Memory details
        memory = psutil.virtual_memory()
        
        # Top processes by CPU and memory
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        top_cpu = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:5]
        top_memory = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:5]
        
        return {
            'cpu_per_core': cpu_per_core,
            'memory_details': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free,
                'buffers': getattr(memory, 'buffers', 0),
                'cached': getattr(memory, 'cached', 0)
            },
            'top_cpu_processes': top_cpu,
            'top_memory_processes': top_memory
        }
    except Exception as e:
        return {'error': str(e)}

def get_disk_metrics():
    """Get disk I/O metrics"""
    try:
        disk_io = psutil.disk_io_counters()
        partitions = []
        
        for partition in psutil.disk_partitions():
            if partition.fstype and not partition.mountpoint.startswith('/snap'):
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partitions.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
                    })
                except PermissionError:
                    continue
        
        return {
            'io_counters': {
                'read_count': disk_io.read_count if disk_io else 0,
                'write_count': disk_io.write_count if disk_io else 0,
                'read_bytes': disk_io.read_bytes if disk_io else 0,
                'write_bytes': disk_io.write_bytes if disk_io else 0
            },
            'partitions': partitions
        }
    except Exception as e:
        return {'error': str(e)}

def get_network_metrics():
    """Get network interface metrics"""
    try:
        net_io = psutil.net_io_counters(pernic=True)
        interfaces = {}
        
        for interface, stats in net_io.items():
            if not interface.startswith('lo'):  # Skip loopback
                interfaces[interface] = {
                    'bytes_sent': stats.bytes_sent,
                    'bytes_recv': stats.bytes_recv,
                    'packets_sent': stats.packets_sent,
                    'packets_recv': stats.packets_recv,
                    'errin': stats.errin,
                    'errout': stats.errout,
                    'dropin': stats.dropin,
                    'dropout': stats.dropout
                }
        
        return interfaces
    except Exception as e:
        return {'error': str(e)}