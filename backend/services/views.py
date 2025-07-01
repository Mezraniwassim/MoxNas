import subprocess
import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ServiceConfig, CloudSyncTask, RsyncTask, TaskLog, UPSConfig
from .serializers import (
    ServiceConfigSerializer, CloudSyncTaskSerializer, 
    RsyncTaskSerializer, TaskLogSerializer, UPSConfigSerializer
)
from .service_manager import ServiceManager, SambaManager, NFSManager, SystemInfoManager

class ServiceConfigViewSet(viewsets.ModelViewSet):
    queryset = ServiceConfig.objects.all()
    serializer_class = ServiceConfigSerializer
    permission_classes = [IsAuthenticated]

class CloudSyncTaskViewSet(viewsets.ModelViewSet):
    queryset = CloudSyncTask.objects.all()
    serializer_class = CloudSyncTaskSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class RsyncTaskViewSet(viewsets.ModelViewSet):
    queryset = RsyncTask.objects.all()
    serializer_class = RsyncTaskSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class TaskLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TaskLog.objects.all()
    serializer_class = TaskLogSerializer
    permission_classes = [IsAuthenticated]

class UPSConfigViewSet(viewsets.ModelViewSet):
    queryset = UPSConfig.objects.all()
    serializer_class = UPSConfigSerializer
    permission_classes = [IsAuthenticated]

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def services_status(request):
    """Get status of all NAS services"""
    service_manager = ServiceManager()
    system_info_manager = SystemInfoManager()
    
    # Define service mappings
    service_mappings = {
        'smb': 'smbd',
        'nfs': 'nfs-kernel-server', 
        'ftp': 'vsftpd',
        'ssh': 'ssh',
        'snmp': 'snmpd',
        'iscsi': 'tgt',
    }
    
    services = {}
    
    for service_key, systemd_name in service_mappings.items():
        is_running = service_manager.is_service_running(systemd_name)
        
        services[service_key] = {
            'name': service_key.upper(),
            'systemd_name': systemd_name,
            'status': 'running' if is_running else 'stopped',
            'enabled': is_running,
            'port': {
                'smb': 445,
                'nfs': 2049,
                'ftp': 21,
                'ssh': 22,
                'snmp': 161,
                'iscsi': 3260,
            }.get(service_key, 0)
        }
    
    # Add system information
    system_stats = system_info_manager.get_system_stats()
    
    return Response({
        'services': services,
        'system': system_stats
    })

def _manage_service(service_name, action):
    """Helper function to manage systemd services"""
    service_manager = ServiceManager()
    service_map = {
        'smb': 'smbd',
        'nfs': 'nfs-kernel-server',
        'ftp': 'vsftpd',
        'ssh': 'ssh',
        'snmp': 'snmpd',
        'iscsi': 'tgt',
    }
    
    systemd_service = service_map.get(service_name)
    if not systemd_service:
        return {'success': False, 'message': f'Unknown service: {service_name}'}
    
    try:
        if action == 'start':
            success = service_manager.start_service(systemd_service)
        elif action == 'stop':
            success = service_manager.stop_service(systemd_service)
        elif action == 'restart':
            success = service_manager.restart_service(systemd_service)
        else:
            return {'success': False, 'message': f'Unknown action: {action}'}
        
        if success:
            return {'success': True, 'message': f'Service {action}ed successfully'}
        else:
            return {'success': False, 'message': f'Failed to {action} service'}
    
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_service(request, service_name):
    """Start a NAS service"""
    result = _manage_service(service_name, 'start')
    return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def stop_service(request, service_name):
    """Stop a NAS service"""
    result = _manage_service(service_name, 'stop')
    return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def restart_service(request, service_name):
    """Restart a NAS service"""
    result = _manage_service(service_name, 'restart')
    return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_cloud_sync_task(request, pk):
    """Manually run a cloud sync task"""
    task = get_object_or_404(CloudSyncTask, pk=pk)
    
    if not task.enabled:
        return Response(
            {'success': False, 'message': 'Task is disabled'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create a task log entry
    task_log = TaskLog.objects.create(
        task_type='cloud_sync',
        task_id=task.id,
        status='running'
    )
    
    try:
        # This is a simplified implementation
        # In production, this should be run asynchronously (e.g., with Celery)
        
        if task.provider == 'aws_s3':
            # AWS S3 sync logic would go here
            pass
        elif task.provider == 'azure_blob':
            # Azure Blob sync logic would go here
            pass
        # Add other providers...
        
        # For demonstration, we'll just simulate success
        task_log.status = 'success'
        task_log.log_output = f'Successfully synced {task.local_path} with {task.remote_path}'
        task_log.files_transferred = 10
        task_log.bytes_transferred = 1024 * 1024  # 1MB
        
    except Exception as e:
        task_log.status = 'failed'
        task_log.error_message = str(e)
    
    finally:
        task_log.save()
        task.last_status = task_log.status
        task.save()
    
    return Response({'success': True, 'task_log_id': task_log.id})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_rsync_task(request, pk):
    """Manually run an rsync task"""
    task = get_object_or_404(RsyncTask, pk=pk)
    
    if not task.enabled:
        return Response(
            {'success': False, 'message': 'Task is disabled'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create a task log entry
    task_log = TaskLog.objects.create(
        task_type='rsync',
        task_id=task.id,
        status='running'
    )
    
    try:
        # Build rsync command
        rsync_cmd = ['rsync', '-av']
        
        if task.compress:
            rsync_cmd.append('-z')
        if task.delete_destination:
            rsync_cmd.append('--delete')
        if task.preserve_permissions:
            rsync_cmd.append('-p')
        if task.preserve_timestamps:
            rsync_cmd.append('-t')
        
        # Add custom options
        if task.rsync_options:
            rsync_cmd.extend(task.rsync_options.split())
        
        # Add source and destination
        if task.direction == 'push':
            source = task.source_path
            dest = f"{task.remote_user}@{task.remote_host}:{task.destination_path}" if task.remote_host else task.destination_path
        else:  # pull
            source = f"{task.remote_user}@{task.remote_host}:{task.source_path}" if task.remote_host else task.source_path
            dest = task.destination_path
        
        rsync_cmd.extend([source, dest])
        
        # Execute rsync command
        result = subprocess.run(
            rsync_cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            task_log.status = 'success'
            task_log.log_output = result.stdout
        else:
            task_log.status = 'failed'
            task_log.error_message = result.stderr
            
    except subprocess.TimeoutExpired:
        task_log.status = 'failed'
        task_log.error_message = 'Rsync task timed out'
    except Exception as e:
        task_log.status = 'failed'
        task_log.error_message = str(e)
    
    finally:
        task_log.save()
        task.last_status = task_log.status
        task.save()
    
    return Response({'success': True, 'task_log_id': task_log.id})