from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import ProxmoxNode, LXCContainer
from .serializers import ProxmoxNodeSerializer, LXCContainerSerializer
from .proxmox_client import ProxmoxAPI
import os

class ProxmoxNodeViewSet(viewsets.ModelViewSet):
    queryset = ProxmoxNode.objects.all()
    serializer_class = ProxmoxNodeSerializer
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test connection to Proxmox node"""
        node = get_object_or_404(ProxmoxNode, pk=pk)
        
        try:
            client = ProxmoxAPI(
                host=node.host,
                port=node.port,
                username=node.username,
                password=node.password,
                realm=node.realm,
                ssl_verify=node.ssl_verify
            )
            
            if client.authenticate():
                nodes = client.get_nodes()
                return Response({
                    'success': True,
                    'message': 'Connection successful',
                    'nodes': len(nodes)
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Authentication failed'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Connection failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LXCContainerViewSet(viewsets.ModelViewSet):
    queryset = LXCContainer.objects.all()
    serializer_class = LXCContainerSerializer
    
    def _get_proxmox_client(self, node):
        """Get Proxmox API client for node"""
        return ProxmoxAPI(
            host=node.host,
            port=node.port,
            username=node.username,
            password=node.password,
            realm=node.realm,
            ssl_verify=node.ssl_verify
        )
    
    @action(detail=False, methods=['post'])
    def create_moxnas_container(self, request):
        """Create new MoxNAS container"""
        data = request.data
        vmid = data.get('vmid')
        node_id = data.get('node_id')
        hostname = data.get('hostname', f'moxnas-{vmid}')
        
        if not vmid or not node_id:
            return Response({
                'error': 'vmid and node_id are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            node = ProxmoxNode.objects.get(id=node_id, enabled=True)
            client = self._get_proxmox_client(node)
            
            # Get first available node name
            nodes = client.get_nodes()
            if not nodes:
                return Response({
                    'error': 'No Proxmox nodes available'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            node_name = nodes[0]['node']
            
            # Create container via Proxmox API
            success = client.create_container(
                node=node_name,
                vmid=vmid,
                hostname=hostname,
                memory=data.get('memory', 2048),
                cores=data.get('cores', 2),
                disk_size=data.get('disk_size', 8),
                template=data.get('template', 'ubuntu-22.04-standard')
            )
            
            if success:
                # Save container in database
                container = LXCContainer.objects.create(
                    vmid=vmid,
                    name=hostname,
                    node=node,
                    memory=data.get('memory', 2048),
                    cores=data.get('cores', 2),
                    disk_size=data.get('disk_size', 8),
                    template=data.get('template', 'ubuntu-22.04-standard'),
                    status='stopped'
                )
                
                serializer = self.get_serializer(container)
                return Response({
                    'success': True,
                    'message': f'Container {vmid} created successfully',
                    'container': serializer.data
                })
            else:
                return Response({
                    'error': 'Failed to create container via Proxmox API'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except ProxmoxNode.DoesNotExist:
            return Response({
                'error': 'Proxmox node not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Container creation failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start container"""
        container = get_object_or_404(LXCContainer, pk=pk)
        client = self._get_proxmox_client(container.node)
        
        # Get node name
        nodes = client.get_nodes()
        if not nodes:
            return Response({
                'error': 'No Proxmox nodes available'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        node_name = nodes[0]['node']
        
        try:
            success = client.start_container(node_name, container.vmid)
            if success:
                container.status = 'running'
                container.save()
                return Response({
                    'success': True,
                    'message': f'Container {container.vmid} started'
                })
            else:
                return Response({
                    'error': 'Failed to start container'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response({
                'error': f'Start failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop container"""
        container = get_object_or_404(LXCContainer, pk=pk)
        client = self._get_proxmox_client(container.node)
        
        # Get node name
        nodes = client.get_nodes()
        if not nodes:
            return Response({
                'error': 'No Proxmox nodes available'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        node_name = nodes[0]['node']
        
        try:
            success = client.stop_container(node_name, container.vmid)
            if success:
                container.status = 'stopped'
                container.save()
                return Response({
                    'success': True,
                    'message': f'Container {container.vmid} stopped'
                })
            else:
                return Response({
                    'error': 'Failed to stop container'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            return Response({
                'error': f'Stop failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def sync_from_proxmox(self, request):
        """Sync containers from Proxmox"""
        synced = 0
        errors = []
        
        for node in ProxmoxNode.objects.filter(enabled=True):
            try:
                client = self._get_proxmox_client(node)
                containers = client.get_containers()
                
                for container_data in containers:
                    vmid = container_data.get('vmid')
                    name = container_data.get('name', f'container-{vmid}')
                    status = container_data.get('status', 'unknown')
                    
                    # Update or create container
                    container, created = LXCContainer.objects.update_or_create(
                        vmid=vmid,
                        defaults={
                            'name': name,
                            'node': node,
                            'status': status,
                            'memory': container_data.get('maxmem', 0) // 1024 // 1024,  # Convert to MB
                            'disk_size': container_data.get('maxdisk', 0) // 1024 // 1024 // 1024,  # Convert to GB
                        }
                    )
                    synced += 1
                    
            except Exception as e:
                errors.append(f"Node {node.name}: {str(e)}")
        
        return Response({
            'synced': synced,
            'errors': errors
        })