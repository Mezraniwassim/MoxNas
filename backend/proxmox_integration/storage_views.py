"""
Proxmox Storage Management Views for MoxNAS
Enhanced storage management through Proxmox API
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ProxmoxHost, ProxmoxNode, ProxmoxStorage, ProxmoxContainer
from .manager import get_proxmox_manager
import logging

logger = logging.getLogger(__name__)


class ProxmoxStorageViewSet(viewsets.ModelViewSet):
    """Manage Proxmox storage configurations"""
    queryset = ProxmoxStorage.objects.all()
    
    def list(self, request):
        """List all storage configurations"""
        storages = self.get_queryset().select_related('host', 'node')
        data = []
        
        for storage in storages:
            data.append({
                'id': storage.id,
                'storage_id': storage.storage_id,
                'type': storage.type,
                'path': storage.path,
                'server': storage.server,
                'export': storage.export,
                'total_space': storage.total_space,
                'used_space': storage.used_space,
                'available_space': storage.available_space,
                'usage_percentage': storage.get_usage_percentage(),
                'content_types': storage.content_types.split(',') if storage.content_types else [],
                'enabled': storage.enabled,
                'shared': storage.shared,
                'host': {
                    'id': storage.host.id,
                    'name': storage.host.name,
                    'host': storage.host.host
                },
                'node': {
                    'id': storage.node.id if storage.node else None,
                    'name': storage.node.name if storage.node else None
                } if storage.node else None,
                'last_updated': storage.last_updated.isoformat()
            })
        
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def sync_from_proxmox(self, request):
        """Sync storage configurations from Proxmox"""
        host_id = request.data.get('host_id')
        
        if not host_id:
            return Response({
                'error': 'host_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            host = ProxmoxHost.objects.get(id=host_id, enabled=True)
            manager = get_proxmox_manager(host)
            
            if not manager:
                return Response({
                    'error': 'Failed to connect to Proxmox'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Get storage from Proxmox
            storages = manager.get_storage()
            synced_count = 0
            
            for storage_data in storages:
                storage_id = storage_data.get('storage')
                storage_type = storage_data.get('type')
                
                # Get or create storage
                storage, created = ProxmoxStorage.objects.update_or_create(
                    host=host,
                    storage_id=storage_id,
                    defaults={
                        'type': storage_type,
                        'path': storage_data.get('path', ''),
                        'server': storage_data.get('server', ''),
                        'export': storage_data.get('export', ''),
                        'content_types': storage_data.get('content', ''),
                        'enabled': storage_data.get('enabled', True),
                        'shared': storage_data.get('shared', False),
                    }
                )
                
                synced_count += 1
            
            return Response({
                'success': True,
                'synced': synced_count,
                'message': f'Synced {synced_count} storage configurations'
            })
            
        except ProxmoxHost.DoesNotExist:
            return Response({
                'error': 'Proxmox host not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Storage sync failed: {str(e)}")
            return Response({
                'error': f'Storage sync failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def get_usage_stats(self, request):
        """Get storage usage statistics across all hosts"""
        host_id = request.query_params.get('host_id')
        
        queryset = self.get_queryset()
        if host_id:
            queryset = queryset.filter(host_id=host_id)
        
        total_space = 0
        used_space = 0
        storage_types = {}
        
        for storage in queryset:
            total_space += storage.total_space
            used_space += storage.used_space
            
            if storage.type not in storage_types:
                storage_types[storage.type] = {
                    'count': 0,
                    'total_space': 0,
                    'used_space': 0
                }
            
            storage_types[storage.type]['count'] += 1
            storage_types[storage.type]['total_space'] += storage.total_space
            storage_types[storage.type]['used_space'] += storage.used_space
        
        return Response({
            'total_space': total_space,
            'used_space': used_space,
            'available_space': total_space - used_space,
            'usage_percentage': (used_space / total_space * 100) if total_space > 0 else 0,
            'storage_types': storage_types
        })
    
    @action(detail=True, methods=['post'])
    def create_directory(self, request, pk=None):
        """Create a directory on storage"""
        storage = get_object_or_404(ProxmoxStorage, pk=pk)
        directory_path = request.data.get('path')
        
        if not directory_path:
            return Response({
                'error': 'Directory path is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            manager = get_proxmox_manager(storage.host)
            if not manager:
                return Response({
                    'error': 'Failed to connect to Proxmox'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Create directory through Proxmox API
            success = manager.create_storage_directory(storage.storage_id, directory_path)
            
            if success:
                return Response({
                    'success': True,
                    'message': f'Directory {directory_path} created successfully'
                })
            else:
                return Response({
                    'error': 'Failed to create directory'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Directory creation failed: {str(e)}")
            return Response({
                'error': f'Directory creation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def list_contents(self, request, pk=None):
        """List contents of a storage location"""
        storage = get_object_or_404(ProxmoxStorage, pk=pk)
        path = request.query_params.get('path', '')
        content_type = request.query_params.get('content', 'images')
        
        try:
            manager = get_proxmox_manager(storage.host)
            if not manager:
                return Response({
                    'error': 'Failed to connect to Proxmox'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Get storage contents
            contents = manager.get_storage_content(storage.storage_id, content_type, path)
            
            return Response({
                'success': True,
                'storage_id': storage.storage_id,
                'path': path,
                'content_type': content_type,
                'contents': contents
            })
            
        except Exception as e:
            logger.error(f"Failed to list storage contents: {str(e)}")
            return Response({
                'error': f'Failed to list contents: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ContainerStorageMountViewSet(viewsets.ViewSet):
    """Manage storage mounts for containers"""
    
    @action(detail=False, methods=['get'])
    def list_container_mounts(self, request):
        """List all container storage mounts"""
        container_id = request.query_params.get('container_id')
        
        if container_id:
            containers = ProxmoxContainer.objects.filter(id=container_id)
        else:
            containers = ProxmoxContainer.objects.all()
        
        data = []
        for container in containers:
            try:
                manager = get_proxmox_manager(container.host)
                if manager:
                    mounts = manager.get_container_mounts(container.node.node_id, container.vmid)
                    data.append({
                        'container': {
                            'id': container.id,
                            'vmid': container.vmid,
                            'name': container.name,
                            'status': container.status
                        },
                        'mounts': mounts
                    })
            except Exception as e:
                logger.error(f"Failed to get mounts for container {container.vmid}: {str(e)}")
        
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def add_mount(self, request):
        """Add storage mount to container"""
        container_id = request.data.get('container_id')
        storage_id = request.data.get('storage_id')
        mount_point = request.data.get('mount_point')
        host_path = request.data.get('host_path')
        
        if not all([container_id, mount_point]):
            return Response({
                'error': 'container_id and mount_point are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            container = ProxmoxContainer.objects.get(id=container_id)
            manager = get_proxmox_manager(container.host)
            
            if not manager:
                return Response({
                    'error': 'Failed to connect to Proxmox'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Add mount point to container
            success = manager.add_container_mount(
                node=container.node.node_id,
                vmid=container.vmid,
                storage_id=storage_id,
                mount_point=mount_point,
                host_path=host_path
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': f'Mount point {mount_point} added to container {container.vmid}'
                })
            else:
                return Response({
                    'error': 'Failed to add mount point'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except ProxmoxContainer.DoesNotExist:
            return Response({
                'error': 'Container not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to add mount: {str(e)}")
            return Response({
                'error': f'Failed to add mount: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['delete'])
    def remove_mount(self, request):
        """Remove storage mount from container"""
        container_id = request.data.get('container_id')
        mount_point = request.data.get('mount_point')
        
        if not all([container_id, mount_point]):
            return Response({
                'error': 'container_id and mount_point are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            container = ProxmoxContainer.objects.get(id=container_id)
            manager = get_proxmox_manager(container.host)
            
            if not manager:
                return Response({
                    'error': 'Failed to connect to Proxmox'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Remove mount point from container
            success = manager.remove_container_mount(
                node=container.node.node_id,
                vmid=container.vmid,
                mount_point=mount_point
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': f'Mount point {mount_point} removed from container {container.vmid}'
                })
            else:
                return Response({
                    'error': 'Failed to remove mount point'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except ProxmoxContainer.DoesNotExist:
            return Response({
                'error': 'Container not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to remove mount: {str(e)}")
            return Response({
                'error': f'Failed to remove mount: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProxmoxBackupViewSet(viewsets.ViewSet):
    """Manage Proxmox backups and snapshots"""
    
    @action(detail=False, methods=['get'])
    def list_backups(self, request):
        """List all backups"""
        host_id = request.query_params.get('host_id')
        
        if not host_id:
            return Response({
                'error': 'host_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            host = ProxmoxHost.objects.get(id=host_id, enabled=True)
            manager = get_proxmox_manager(host)
            
            if not manager:
                return Response({
                    'error': 'Failed to connect to Proxmox'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            backups = manager.get_backups()
            
            return Response({
                'success': True,
                'backups': backups
            })
            
        except ProxmoxHost.DoesNotExist:
            return Response({
                'error': 'Proxmox host not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to list backups: {str(e)}")
            return Response({
                'error': f'Failed to list backups: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def create_backup(self, request):
        """Create backup of container"""
        container_id = request.data.get('container_id')
        storage_id = request.data.get('storage_id', 'local')
        compression = request.data.get('compression', 'lzo')
        
        if not container_id:
            return Response({
                'error': 'container_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            container = ProxmoxContainer.objects.get(id=container_id)
            manager = get_proxmox_manager(container.host)
            
            if not manager:
                return Response({
                    'error': 'Failed to connect to Proxmox'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Create backup
            task_id = manager.create_backup(
                node=container.node.node_id,
                vmid=container.vmid,
                storage=storage_id,
                compression=compression
            )
            
            if task_id:
                return Response({
                    'success': True,
                    'task_id': task_id,
                    'message': f'Backup started for container {container.vmid}'
                })
            else:
                return Response({
                    'error': 'Failed to start backup'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except ProxmoxContainer.DoesNotExist:
            return Response({
                'error': 'Container not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            return Response({
                'error': f'Failed to create backup: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)