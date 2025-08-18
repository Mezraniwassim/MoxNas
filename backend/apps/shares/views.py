from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
import logging

from .models import SMBShare, NFSShare, FTPShare, SharePermission
from .serializers import (
    SMBShareSerializer, NFSShareSerializer, 
    FTPShareSerializer, SharePermissionSerializer
)
from .services import ShareService

logger = logging.getLogger(__name__)

class SMBShareViewSet(viewsets.ModelViewSet):
    queryset = SMBShare.objects.all()
    serializer_class = SMBShareSerializer

    def create(self, request, *args, **kwargs):
        """Create SMB share and update Samba configuration"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create the share
        share = serializer.save()
        
        # Update Samba configuration
        try:
            service = ShareService()
            if service.update_samba_config():
                logger.info(f"Created SMB share: {share.name}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                # Rollback if config update failed
                share.delete()
                return Response(
                    {'error': 'Failed to update Samba configuration'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            share.delete()
            logger.error(f"Error creating SMB share: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Update SMB share and Samba configuration"""
        response = super().update(request, *args, **kwargs)
        
        # Update Samba configuration
        try:
            service = ShareService()
            service.update_samba_config()
            return response
        except Exception as e:
            logger.error(f"Error updating SMB share: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Delete SMB share and update Samba configuration"""
        response = super().destroy(request, *args, **kwargs)
        
        # Update Samba configuration
        try:
            service = ShareService()
            service.update_samba_config()
            return response
        except Exception as e:
            logger.error(f"Error deleting SMB share: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """Test SMB connection"""
        try:
            service = ShareService()
            result = service.test_samba_connection()
            return Response(result)
        except Exception as e:
            logger.error(f"Error testing SMB connection: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class NFSShareViewSet(viewsets.ModelViewSet):
    queryset = NFSShare.objects.all()
    serializer_class = NFSShareSerializer

    def create(self, request, *args, **kwargs):
        """Create NFS share and update exports"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        share = serializer.save()
        
        try:
            service = ShareService()
            if service.update_nfs_exports():
                logger.info(f"Created NFS share: {share.path}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                share.delete()
                return Response(
                    {'error': 'Failed to update NFS exports'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            share.delete()
            logger.error(f"Error creating NFS share: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """Update NFS share and exports"""
        response = super().update(request, *args, **kwargs)
        
        try:
            service = ShareService()
            service.update_nfs_exports()
            return response
        except Exception as e:
            logger.error(f"Error updating NFS share: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Delete NFS share and update exports"""
        response = super().destroy(request, *args, **kwargs)
        
        try:
            service = ShareService()
            service.update_nfs_exports()
            return response
        except Exception as e:
            logger.error(f"Error deleting NFS share: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FTPShareViewSet(viewsets.ModelViewSet):
    queryset = FTPShare.objects.all()
    serializer_class = FTPShareSerializer

class SharePermissionViewSet(viewsets.ModelViewSet):
    queryset = SharePermission.objects.all()
    serializer_class = SharePermissionSerializer