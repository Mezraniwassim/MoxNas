from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.cache import cache
import time
from .models import StoragePool, Dataset, Share, AccessControlList
from .serializers import (
    StoragePoolSerializer, DatasetSerializer, 
    ShareSerializer, AccessControlListSerializer
)
from .services import StorageService, ShareService, ISCSIService, BackupService


@method_decorator(csrf_exempt, name='dispatch')
class StoragePoolViewSet(viewsets.ModelViewSet):
    queryset = StoragePool.objects.all()
    serializer_class = StoragePoolSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage_service = StorageService()

    @action(detail=True, methods=['post'])
    def refresh_size(self, request, pk=None):
        """Refresh storage pool size information"""
        storage_pool = self.get_object()
        storage_pool.update_size_info()
        return Response({'status': 'refreshed'})

    @action(detail=False, methods=['get'])
    def scan_mount_points(self, request):
        """Scan for available mount points"""
        mount_points = self.storage_service.scan_mount_points()
        return Response(mount_points)

    @action(detail=False, methods=['get'])
    def health_status(self, request):
        """Get storage health status"""
        # Try to get from cache first
        health_data = cache.get('storage_health')
        if not health_data:
            health_data = self.storage_service.monitor_storage_health()
            cache.set('storage_health', health_data, timeout=300)
        return Response(health_data)

    @action(detail=True, methods=['get'])
    def usage_stats(self, request, pk=None):
        """Get detailed usage statistics for a storage pool"""
        storage_pool = self.get_object()
        usage = self.storage_service.get_storage_usage(storage_pool.mount_path)
        return Response(usage or {'error': 'Unable to get usage statistics'})

    @action(detail=False, methods=['post'])
    def start_monitoring(self, request):
        """Start storage health monitoring"""
        success = self.storage_service.start_monitoring()
        return Response({'monitoring_started': success})

    @action(detail=False, methods=['post'])
    def stop_monitoring(self, request):
        """Stop storage health monitoring"""
        self.storage_service.stop_monitoring()
        return Response({'monitoring_stopped': True})


@method_decorator(csrf_exempt, name='dispatch')
class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.storage_service = StorageService()

    def perform_create(self, serializer):
        """Create dataset and its directory structure"""
        dataset = serializer.save()
        result = self.storage_service.create_dataset_directory(dataset)
        if not result['success']:
            dataset.delete()
            raise ValueError(result['message'])

    @action(detail=True, methods=['post'])
    def create_snapshot(self, request, pk=None):
        """Create a snapshot of the dataset"""
        dataset = self.get_object()
        snapshot_name = request.data.get('name', 'manual')
        result = self.storage_service.create_snapshot(dataset.full_path, snapshot_name)
        return Response(result)

    @action(detail=True, methods=['get'])
    def list_snapshots(self, request, pk=None):
        """List snapshots for the dataset"""
        dataset = self.get_object()
        snapshots = self.storage_service.list_snapshots(dataset.full_path)
        return Response(snapshots)

    @action(detail=True, methods=['post'])
    def cleanup_snapshots(self, request, pk=None):
        """Clean up old snapshots"""
        dataset = self.get_object()
        keep_count = request.data.get('keep_count', 10)
        result = self.storage_service.cleanup_old_snapshots(dataset.full_path, keep_count)
        return Response(result)

    @action(detail=True, methods=['post'])
    def set_permissions(self, request, pk=None):
        """Set permissions on dataset directory"""
        dataset = self.get_object()
        permissions = request.data.get('permissions', '755')
        result = self.storage_service.set_dataset_permissions(dataset, permissions)
        return Response(result)

    @action(detail=True, methods=['get'])
    def filesystem_info(self, request, pk=None):
        """Get detailed filesystem information"""
        dataset = self.get_object()
        info = self.storage_service.get_filesystem_info(dataset.full_path)
        return Response(info or {'error': 'Unable to get filesystem info'})


@method_decorator(csrf_exempt, name='dispatch')
class ShareViewSet(viewsets.ModelViewSet):
    queryset = Share.objects.all()
    serializer_class = ShareSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.share_service = ShareService()

    def perform_create(self, serializer):
        """Validate and create share"""
        share_data = serializer.validated_data
        errors = self.share_service.validate_share_config(share_data)
        if errors:
            raise ValueError('; '.join(errors))
        
        share = serializer.save()
        
        # Apply share configuration
        result = self.share_service.enable_share(share)
        if not result['success']:
            share.delete()
            raise ValueError(result['message'])

    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """Enable a share"""
        share = self.get_object()
        share.enabled = True
        share.save()
        result = self.share_service.enable_share(share)
        return Response(result)

    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable a share"""
        share = self.get_object()
        share.enabled = False
        share.save()
        result = self.share_service.disable_share(share)
        return Response(result)

    @action(detail=False, methods=['get'])
    def active_connections(self, request):
        """Get active connections to shares"""
        share_type = request.query_params.get('type', 'all')
        connections = self.share_service.get_active_connections(share_type)
        return Response(connections)

    @action(detail=True, methods=['get'])
    def test_connectivity(self, request, pk=None):
        """Test share connectivity"""
        share = self.get_object()
        test_results = self.share_service.test_share_connectivity(share)
        return Response(test_results)

    @action(detail=False, methods=['post'])
    def bulk_operation(self, request):
        """Perform bulk operations on multiple shares"""
        share_ids = request.data.get('share_ids', [])
        operation = request.data.get('operation')
        
        if not share_ids or not operation:
            return Response({'error': 'share_ids and operation required'}, status=400)
            
        results = self.share_service.bulk_share_operation(share_ids, operation)
        return Response(results)

    @action(detail=False, methods=['get'])
    def usage_report(self, request):
        """Generate comprehensive share usage report"""
        report = self.share_service.generate_share_report()
        return Response(report)

    @action(detail=False, methods=['post'])
    def create_template(self, request):
        """Create a reusable share template"""
        template_name = request.data.get('name')
        config = request.data.get('config', {})
        
        if not template_name:
            return Response({'error': 'Template name required'}, status=400)
            
        result = self.share_service.create_user_template(template_name, config)
        return Response(result)

    @action(detail=False, methods=['post'])
    def apply_template(self, request):
        """Apply a template to create a new share"""
        template_name = request.data.get('template')
        share_name = request.data.get('share_name')
        dataset_id = request.data.get('dataset_id')
        
        if not all([template_name, share_name, dataset_id]):
            return Response({'error': 'template, share_name, and dataset_id required'}, status=400)
            
        try:
            dataset = Dataset.objects.get(id=dataset_id)
            result = self.share_service.apply_template(template_name, share_name, dataset)
            return Response(result)
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found'}, status=404)

    @action(detail=False, methods=['post'])
    def restart_services(self, request):
        """Restart all share services"""
        results = self.share_service.restart_all_services()
        return Response(results)


@method_decorator(csrf_exempt, name='dispatch')
class AccessControlListViewSet(viewsets.ModelViewSet):
    queryset = AccessControlList.objects.all()
    serializer_class = AccessControlListSerializer


@method_decorator(csrf_exempt, name='dispatch')  
class ISCSIViewSet(viewsets.ViewSet):
    """ViewSet for iSCSI target management"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.iscsi_service = ISCSIService()
    
    def list(self, request):
        """List all iSCSI targets"""
        targets = self.iscsi_service.list_targets()
        return Response(targets)
    
    def create(self, request):
        """Create a new iSCSI target"""
        config = request.data
        result = self.iscsi_service.create_target_advanced(config)
        
        if result['success']:
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        """Delete an iSCSI target"""
        result = self.iscsi_service.delete_target_advanced(pk)
        
        if result['success']:
            return Response(result, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get active sessions for a target"""
        sessions = self.iscsi_service.get_target_sessions(pk)
        return Response(sessions)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get statistics for a target"""
        stats = self.iscsi_service.get_target_stats(pk)
        return Response(stats)
    
    @action(detail=False, methods=['post'])
    def backup_config(self, request):
        """Backup all target configurations"""
        result = self.iscsi_service.backup_target_config()
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def restore_config(self, request):
        """Restore target configurations from backup"""
        backup_file = request.data.get('backup_file')
        if not backup_file:
            return Response({'error': 'backup_file required'}, status=400)
            
        result = self.iscsi_service.restore_target_config(backup_file)
        return Response(result)


@method_decorator(csrf_exempt, name='dispatch')
class BackupViewSet(viewsets.ViewSet):
    """ViewSet for backup management"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backup_service = BackupService()
    
    def list(self, request):
        """List available backups"""
        backups = self.backup_service.list_backups()
        return Response(backups)
    
    def create(self, request):
        """Create a new backup"""
        dataset_id = request.data.get('dataset_id')
        destination = request.data.get('destination')
        compression = request.data.get('compression', True)
        
        if not dataset_id:
            return Response({'error': 'dataset_id required'}, status=400)
            
        try:
            dataset = Dataset.objects.get(id=dataset_id)
            result = self.backup_service.create_dataset_backup(dataset, destination, compression)
            
            if result['success']:
                return Response(result, status=status.HTTP_201_CREATED)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Dataset.DoesNotExist:
            return Response({'error': 'Dataset not found'}, status=404)
    
    @action(detail=False, methods=['post'])
    def restore(self, request):
        """Restore a backup"""
        backup_file = request.data.get('backup_file')
        destination = request.data.get('destination')
        
        if not backup_file or not destination:
            return Response({'error': 'backup_file and destination required'}, status=400)
            
        result = self.backup_service.restore_backup(backup_file, destination)
        return Response(result)


# Traditional Django views for web interface
def storage_dashboard(request):
    """Storage dashboard view - returns JSON for API"""
    storage_pools = StoragePool.objects.all()
    
    # Get health status from cache
    health_data = cache.get('storage_health', {})
    
    data = {
        'storage_pools': [
            {
                'id': pool.id,
                'name': pool.name,
                'mount_path': pool.mount_path,
                'total_size': pool.total_size,
                'used_size': pool.used_size,
                'available_size': pool.available_size,
                'usage_percentage': pool.usage_percentage,
                'is_active': pool.is_active,
                'health': health_data.get(pool.mount_path, {})
            }
            for pool in storage_pools
        ],
        'health_summary': {
            'total_pools': len(storage_pools),
            'healthy_pools': len([p for p in health_data.values() if p.get('healthy', True)]),
            'warning_pools': len([p for p in health_data.values() if p.get('warnings', [])])
        }
    }
    return JsonResponse(data)


def shares_dashboard(request):
    """Shares dashboard view"""
    shares = Share.objects.all()
    share_service = ShareService()
    
    # Get active connections
    connections = share_service.get_active_connections()
    
    data = {
        'shares': [
            {
                'id': share.id,
                'name': share.name,
                'share_type': share.share_type,
                'enabled': share.enabled,
                'dataset': share.dataset.name,
                'readonly': share.readonly,
                'guest_access': share.guest_access
            }
            for share in shares
        ],
        'connections': connections,
        'summary': {
            'total_shares': shares.count(),
            'enabled_shares': shares.filter(enabled=True).count(),
            'smb_shares': shares.filter(share_type='smb').count(),
            'nfs_shares': shares.filter(share_type='nfs').count(),
            'ftp_shares': shares.filter(share_type='ftp').count(),
        }
    }
    return JsonResponse(data)


def iscsi_dashboard(request):
    """iSCSI dashboard view"""
    iscsi_service = ISCSIService()
    
    targets = iscsi_service.list_targets()
    all_sessions = iscsi_service.get_target_sessions()
    
    data = {
        'targets': targets,
        'sessions': all_sessions,
        'summary': {
            'total_targets': len(targets),
            'active_sessions': len(all_sessions),
            'total_luns': sum(len(t.get('luns', [])) for t in targets)
        }
    }
    return JsonResponse(data)


def backup_dashboard(request):
    """Backup dashboard view"""
    backup_service = BackupService()
    
    backups = backup_service.list_backups()
    
    # Calculate summary statistics
    total_size = sum(b['size'] for b in backups)
    recent_backups = [b for b in backups if (time.time() - b['created']) < 86400]  # Last 24 hours
    
    data = {
        'backups': backups,
        'summary': {
            'total_backups': len(backups),
            'total_size': total_size,
            'recent_backups': len(recent_backups),
            'oldest_backup': min([b['created'] for b in backups]) if backups else None,
            'newest_backup': max([b['created'] for b in backups]) if backups else None
        }
    }
    return JsonResponse(data)


@csrf_exempt
def storage_stats(request):
    """Get storage statistics for dashboard"""
    try:
        pools = StoragePool.objects.all()
        stats = {
            'total_pools': pools.count(),
            'active_pools': pools.filter(is_active=True).count(),
            'total_capacity': sum(pool.total_size for pool in pools if pool.total_size),
            'used_capacity': sum(pool.used_size for pool in pools if pool.used_size),
            'available_capacity': sum(pool.available_size for pool in pools),
        }
        
        # Calculate usage percentage
        if stats['total_capacity'] > 0:
            stats['usage_percentage'] = (stats['used_capacity'] / stats['total_capacity']) * 100
        else:
            stats['usage_percentage'] = 0
            
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  
def storage_monitoring(request):
    """Get storage monitoring status"""
    try:
        # Return basic monitoring data for now
        monitoring_data = [
            {
                'mount_point': '/mnt/pool0',
                'service_active': True,
                'mounted': True,
                'status': 'healthy'
            },
            {
                'mount_point': '/mnt/tank',
                'service_active': True, 
                'mounted': True,
                'status': 'healthy'
            }
        ]
        return JsonResponse(monitoring_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def shares_stats(request):
    """Get shares statistics for dashboard"""
    try:
        shares = Share.objects.all()
        stats = {
            'total_shares': shares.count(),
            'smb_count': shares.filter(protocol='SMB').count(),
            'nfs_count': shares.filter(protocol='NFS').count(), 
            'ftp_count': shares.filter(protocol='FTP').count(),
            'active_count': shares.filter(enabled=True).count(),
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
