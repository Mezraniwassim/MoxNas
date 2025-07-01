from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Dataset, Share, MountPoint
from .serializers import DatasetSerializer, ShareSerializer, MountPointSerializer
from services.service_manager import SambaManager, NFSManager
import os
import subprocess
import shutil

class DatasetViewSet(viewsets.ModelViewSet):
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer
    
    def perform_create(self, serializer):
        """Create dataset and directory"""
        dataset = serializer.save()
        # Create directory if it doesn't exist
        os.makedirs(dataset.path, exist_ok=True)
        # Set permissions
        os.chmod(dataset.path, 0o755)
    
    @action(detail=True, methods=['get'])
    def usage(self, request, pk=None):
        """Get dataset disk usage"""
        dataset = get_object_or_404(Dataset, pk=pk)
        
        try:
            if os.path.exists(dataset.path):
                usage = shutil.disk_usage(dataset.path)
                return Response({
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
                })
            else:
                return Response({
                    'total': 0,
                    'used': 0, 
                    'free': 0,
                    'percent': 0
                })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ShareViewSet(viewsets.ModelViewSet):
    queryset = Share.objects.all()
    serializer_class = ShareSerializer
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.samba_manager = SambaManager()
        self.nfs_manager = NFSManager()
    
    def perform_create(self, serializer):
        """Create share and configure service"""
        share = serializer.save()
        # Create directory if it doesn't exist
        os.makedirs(share.path, exist_ok=True)
        # Configure the actual service
        self._configure_share(share)
    
    def perform_update(self, serializer):
        """Update share and reconfigure service"""
        old_share = self.get_object()
        share = serializer.save()
        
        # Remove old configuration if name or protocol changed
        if old_share.name != share.name or old_share.protocol != share.protocol:
            self._remove_share_config(old_share)
        
        # Apply new configuration
        self._configure_share(share)
    
    def perform_destroy(self, instance):
        """Remove share configuration before deletion"""
        self._remove_share_config(instance)
        instance.delete()
    
    def _configure_share(self, share):
        """Configure share based on protocol"""
        try:
            if share.protocol == 'smb':
                success = self.samba_manager.create_share(
                    share_name=share.name,
                    path=share.path,
                    read_only=share.read_only,
                    guest_ok=share.guest_ok
                )
                if not success:
                    raise Exception("Failed to configure SMB share")
                    
            elif share.protocol == 'nfs':
                success = self.nfs_manager.create_export(
                    path=share.path,
                    read_only=share.nfs_readonly or share.read_only,
                    sync=share.nfs_sync
                )
                if not success:
                    raise Exception("Failed to configure NFS export")
                    
            elif share.protocol == 'ftp':
                # FTP configuration would go here
                # For now, just ensure directory exists and has proper permissions
                os.chmod(share.path, 0o755)
                
        except Exception as e:
            # Log the error but don't fail the database operation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to configure {share.protocol} share {share.name}: {e}")
    
    def _remove_share_config(self, share):
        """Remove share configuration"""
        try:
            if share.protocol == 'smb':
                self.samba_manager.remove_share(share.name)
            elif share.protocol == 'nfs':
                self.nfs_manager.remove_export(share.path)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to remove {share.protocol} share {share.name}: {e}")

class MountPointViewSet(viewsets.ModelViewSet):
    queryset = MountPoint.objects.all()
    serializer_class = MountPointSerializer
    
    @action(detail=True, methods=['post'])
    def mount(self, request, pk=None):
        """Mount a filesystem"""
        mount_point = get_object_or_404(MountPoint, pk=pk)
        
        try:
            # Create mount point directory if it doesn't exist
            os.makedirs(mount_point.path, exist_ok=True)
            
            # Mount the filesystem
            cmd = [
                'mount', 
                '-t', mount_point.filesystem,
                '-o', mount_point.options,
                mount_point.source,
                mount_point.path
            ]
            subprocess.run(cmd, check=True)
            
            mount_point.mounted = True
            mount_point.save()
            
            return Response({
                'success': True,
                'message': f"Mounted {mount_point.source} at {mount_point.path}"
            })
            
        except subprocess.CalledProcessError as e:
            return Response({
                'success': False,
                'message': f"Failed to mount: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': f"Error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def unmount(self, request, pk=None):
        """Unmount a filesystem"""
        mount_point = get_object_or_404(MountPoint, pk=pk)
        
        try:
            subprocess.run(['umount', mount_point.path], check=True)
            mount_point.mounted = False
            mount_point.save()
            
            return Response({
                'success': True,
                'message': f"Unmounted {mount_point.path}"
            })
            
        except subprocess.CalledProcessError as e:
            return Response({
                'success': False,
                'message': f"Failed to unmount: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def check_mounts(self, request):
        """Check current mount status"""
        for mount_point in self.queryset:
            mount_point.mounted = self._is_mounted(mount_point.path)
            mount_point.save()
        
        serializer = self.get_serializer(self.queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def usage(self, request, pk=None):
        """Get mount point disk usage"""
        mount_point = get_object_or_404(MountPoint, pk=pk)
        
        try:
            if mount_point.mounted and os.path.exists(mount_point.path):
                usage = shutil.disk_usage(mount_point.path)
                return Response({
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': (usage.used / usage.total) * 100 if usage.total > 0 else 0
                })
            else:
                return Response({
                    'total': 0,
                    'used': 0,
                    'free': 0,
                    'percent': 0,
                    'mounted': mount_point.mounted
                })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _is_mounted(self, path):
        """Check if a path is currently mounted"""
        try:
            result = subprocess.run(
                ['mountpoint', '-q', path],
                capture_output=True
            )
            return result.returncode == 0
        except:
            return False