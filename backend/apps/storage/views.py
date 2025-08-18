from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import subprocess
import json
import psutil
import logging

from .models import Disk, MountPoint, StoragePool
from .serializers import DiskSerializer, MountPointSerializer, StoragePoolSerializer
from .services import StorageService

logger = logging.getLogger(__name__)

class DiskViewSet(viewsets.ModelViewSet):
    queryset = Disk.objects.all()
    serializer_class = DiskSerializer

    @action(detail=False, methods=['post'])
    def scan(self, request):
        """Scan system for available disks"""
        try:
            service = StorageService()
            disks = service.scan_disks()
            return Response({
                'message': f'Found {len(disks)} disks',
                'disks': disks
            })
        except Exception as e:
            logger.error(f"Error scanning disks: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """Refresh disk information"""
        disk = get_object_or_404(Disk, pk=pk)
        try:
            disk.refresh_info()
            serializer = self.get_serializer(disk)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error refreshing disk {disk.device}: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MountPointViewSet(viewsets.ModelViewSet):
    queryset = MountPoint.objects.all()
    serializer_class = MountPointSerializer

    @action(detail=True, methods=['post'])
    def mount(self, request, pk=None):
        """Mount the filesystem"""
        mount_point = get_object_or_404(MountPoint, pk=pk)
        try:
            if mount_point.mount():
                return Response({'message': 'Mounted successfully'})
            else:
                return Response(
                    {'error': 'Failed to mount'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.error(f"Error mounting {mount_point.path}: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def unmount(self, request, pk=None):
        """Unmount the filesystem"""
        mount_point = get_object_or_404(MountPoint, pk=pk)
        try:
            if mount_point.unmount():
                return Response({'message': 'Unmounted successfully'})
            else:
                return Response(
                    {'error': 'Failed to unmount'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            logger.error(f"Error unmounting {mount_point.path}: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StoragePoolViewSet(viewsets.ModelViewSet):
    queryset = StoragePool.objects.all()
    serializer_class = StoragePoolSerializer

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get storage overview statistics"""
        try:
            service = StorageService()
            overview = service.get_storage_overview()
            return Response(overview)
        except Exception as e:
            logger.error(f"Error getting storage overview: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )