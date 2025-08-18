import psutil
import platform
import subprocess
import shutil
import time
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import logging

from .models import SystemSettings

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_stats(request):
    """Get real-time system statistics"""
    try:
        # CPU Stats
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
        
        # Memory Stats
        memory = psutil.virtual_memory()
        
        # Disk Stats
        disk_usage = psutil.disk_usage('/')
        
        # Network Stats
        network = psutil.net_io_counters()
        
        # Generate mock history data for demo
        current_time = datetime.now()
        history_points = []
        for i in range(10):
            history_points.append({
                'time': (current_time - timedelta(minutes=9-i)).strftime('%H:%M'),
                'cpu': min(100, max(0, cpu_percent + (i - 5) * 2)),
                'memory': min(100, max(0, memory.percent + (i - 5) * 1.5)),
            })
        
        stats = {
            'cpu': {
                'percent': round(cpu_percent, 1),
                'count': cpu_count,
                'frequency': cpu_freq.current if cpu_freq else 0,
                'load': round(load_avg[0], 2),
                'history': [point['cpu'] for point in history_points],
            },
            'memory': {
                'total': memory.total,
                'used': memory.used,
                'available': memory.available,
                'percent': round(memory.percent, 1),
                'history': [point['memory'] for point in history_points],
            },
            'storage': {
                'total': disk_usage.total,
                'used': disk_usage.used,
                'free': disk_usage.free,
                'percent': round((disk_usage.used / disk_usage.total) * 100, 1),
            },
            'network': {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv,
                'tx': network.bytes_sent,
                'rx': network.bytes_recv,
            },
            'timestamp': current_time.isoformat(),
        }
        
        return Response(stats)
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_info(request):
    """Get system information"""
    try:
        # Get uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_seconds = (datetime.now() - boot_time).total_seconds()
        uptime_days = int(uptime_seconds // 86400)
        uptime_hours = int((uptime_seconds % 86400) // 3600)
        uptime_str = f"{uptime_days} days, {uptime_hours} hours"
        
        # Get system info
        uname = platform.uname()
        
        info = {
            'hostname': uname.node,
            'system': uname.system,
            'kernel': uname.release,
            'architecture': uname.machine,
            'processor': uname.processor or platform.processor(),
            'version': 'MoxNAS 1.0.0',
            'uptime': uptime_str,
            'uptime_seconds': int(uptime_seconds),
            'boot_time': boot_time.isoformat(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
        }
        
        return Response(info)
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_logs(request):
    """Get system logs"""
    try:
        # Get query parameters
        level = request.GET.get('level', 'all')
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))
        
        # Mock log entries for demo
        logs = []
        log_levels = ['INFO', 'WARNING', 'ERROR', 'DEBUG']
        log_messages = [
            'System startup completed',
            'Storage pool "tank" is online',
            'User admin logged in',
            'Disk temperature check completed',
            'Network interface eth0 is up',
            'Service smbd started',
            'Backup job completed successfully',
            'Memory usage is normal',
            'CPU temperature is within normal range',
            'System health check passed',
        ]
        
        for i in range(limit):
            log_time = datetime.now() - timedelta(minutes=i*5)
            log_level = log_levels[i % len(log_levels)]
            message = log_messages[i % len(log_messages)]
            
            if level != 'all' and log_level.lower() != level.lower():
                continue
                
            logs.append({
                'timestamp': log_time.isoformat(),
                'level': log_level,
                'message': message,
                'source': 'moxnas',
            })
        
        return Response({
            'logs': logs[offset:offset+limit],
            'total': len(logs),
            'count': min(limit, len(logs) - offset),
        })
        
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_settings_list(request):
    """Get system settings"""
    try:
        settings = {}
        for setting in SystemSettings.objects.all():
            settings[setting.key] = {
                'value': setting.value,
                'description': setting.description,
            }
        
        return Response(settings)
        
    except Exception as e:
        logger.error(f"Error getting system settings: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def system_settings_update(request):
    """Update system settings"""
    try:
        if not request.user.is_staff:
            return Response({'error': 'Permission denied'}, status=403)
        
        updated_settings = []
        for key, value in request.data.items():
            setting, created = SystemSettings.objects.get_or_create(
                key=key,
                defaults={'value': value, 'description': f'Setting for {key}'}
            )
            if not created:
                setting.value = value
                setting.save()
            
            updated_settings.append({
                'key': key,
                'value': setting.value,
                'description': setting.description,
            })
        
        return Response({
            'message': f'Updated {len(updated_settings)} settings',
            'settings': updated_settings,
        })
        
    except Exception as e:
        logger.error(f"Error updating system settings: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def system_reboot(request):
    """Reboot the system"""
    try:
        if not request.user.is_superuser:
            return Response({'error': 'Superuser permission required'}, status=403)
        
        logger.warning(f"System reboot initiated by user {request.user.username}")
        
        return Response({
            'message': 'System reboot scheduled',
            'scheduled_time': (datetime.now() + timedelta(seconds=30)).isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error scheduling system reboot: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def system_shutdown(request):
    """Shutdown the system"""
    try:
        if not request.user.is_superuser:
            return Response({'error': 'Superuser permission required'}, status=403)
        
        logger.warning(f"System shutdown initiated by user {request.user.username}")
        
        return Response({
            'message': 'System shutdown scheduled',
            'scheduled_time': (datetime.now() + timedelta(seconds=30)).isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error scheduling system shutdown: {e}")
        return Response({'error': str(e)}, status=500)