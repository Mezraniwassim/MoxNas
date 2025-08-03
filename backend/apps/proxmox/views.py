from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import logging

from .services import ProxmoxService
from .models import ProxmoxNode
from .serializers import ProxmoxNodeSerializer

logger = logging.getLogger('moxnas.proxmox')


class ProxmoxDashboardView(APIView):
    """Main dashboard data for Proxmox"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            service = ProxmoxService()
            
            # Get node information
            nodes = service.get_nodes()
            node_name = settings.PROXMOX_CONFIG['NODE']
            node_status = service.get_node_status(node_name)
            
            # Get containers
            containers = service.get_containers(node_name)
            
            # Summary data
            running_containers = len([c for c in containers if c.get('status') == 'running'])
            stopped_containers = len([c for c in containers if c.get('status') == 'stopped'])
            
            data = {
                'nodes': nodes,
                'node_status': node_status,
                'containers': {
                    'total': len(containers),
                    'running': running_containers,
                    'stopped': stopped_containers,
                    'list': containers
                },
                'connection_status': service._api is not None
            }
            
            return Response(data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return Response(
                {'error': 'Failed to fetch dashboard data', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProxmoxNodesView(APIView):
    """Proxmox nodes management"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            service = ProxmoxService()
            nodes = service.get_nodes()
            return Response({'nodes': nodes}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Nodes fetch error: {e}")
            return Response(
                {'error': 'Failed to fetch nodes', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProxmoxNodeStatusView(APIView):
    """Get status of a specific node"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, node_name):
        try:
            service = ProxmoxService()
            node_status = service.get_node_status(node_name)
            return Response({'status': node_status}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Node status error: {e}")
            return Response(
                {'error': f'Failed to get status for node {node_name}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProxmoxContainersView(APIView):
    """Proxmox containers management"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            service = ProxmoxService()
            node_name = request.GET.get('node', settings.PROXMOX_CONFIG['NODE'])
            containers = service.get_containers(node_name)
            
            # Enhance container data with additional status info
            enhanced_containers = []
            for container in containers:
                vmid = container.get('vmid')
                if vmid:
                    container_status = service.get_container_status(vmid, node_name)
                    container.update(container_status)
                enhanced_containers.append(container)
            
            return Response({'containers': enhanced_containers}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Containers fetch error: {e}")
            return Response(
                {'error': 'Failed to fetch containers', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProxmoxContainerDetailView(APIView):
    """Individual container management"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, vmid):
        try:
            service = ProxmoxService()
            node_name = request.GET.get('node', settings.PROXMOX_CONFIG['NODE'])
            container_status = service.get_container_status(int(vmid), node_name)
            return Response({'container': container_status}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Container {vmid} status error: {e}")
            return Response(
                {'error': f'Failed to get container {vmid} status', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, vmid):
        """Create a new container"""
        try:
            service = ProxmoxService()
            node_name = request.data.get('node', settings.PROXMOX_CONFIG['NODE'])
            config = request.data.get('config', {})
            
            result = service.create_container(int(vmid), config, node_name)
            if result:
                return Response({'message': f'Container {vmid} creation started'}, status=status.HTTP_201_CREATED)
            else:
                return Response({'error': f'Failed to create container {vmid}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Container {vmid} creation error: {e}")
            return Response(
                {'error': f'Failed to create container {vmid}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, vmid):
        """Delete a container"""
        try:
            service = ProxmoxService()
            node_name = request.GET.get('node', settings.PROXMOX_CONFIG['NODE'])
            
            result = service.delete_container(int(vmid), node_name)
            if result:
                return Response({'message': f'Container {vmid} deletion started'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': f'Failed to delete container {vmid}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Container {vmid} deletion error: {e}")
            return Response(
                {'error': f'Failed to delete container {vmid}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProxmoxContainerActionView(APIView):
    """Container actions (start, stop, restart)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, vmid, action):
        try:
            service = ProxmoxService()
            node_name = request.data.get('node', settings.PROXMOX_CONFIG['NODE'])
            vmid = int(vmid)
            
            if action == 'start':
                result = service.start_container(vmid, node_name)
            elif action == 'stop':
                result = service.stop_container(vmid, node_name)
            elif action == 'restart':
                service.stop_container(vmid, node_name)
                result = service.start_container(vmid, node_name)
            else:
                return Response({'error': f'Invalid action: {action}'}, status=status.HTTP_400_BAD_REQUEST)
            
            if result:
                return Response({'message': f'Container {vmid} {action} started'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': f'Failed to {action} container {vmid}'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Container {vmid} {action} error: {e}")
            return Response(
                {'error': f'Failed to {action} container {vmid}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProxmoxContainerExecView(APIView):
    """Execute commands in container"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, vmid):
        try:
            service = ProxmoxService()
            node_name = request.data.get('node', settings.PROXMOX_CONFIG['NODE'])
            command = request.data.get('command')
            
            if not command:
                return Response({'error': 'Command is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            result = service.execute_command(int(vmid), command, node_name)
            return Response({'result': result}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Container {vmid} exec error: {e}")
            return Response(
                {'error': f'Failed to execute command in container {vmid}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProxmoxTestConnectionView(APIView):
    """Test Proxmox connection"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            service = ProxmoxService()
            api = service.get_api_connection()
            
            if api:
                version = api.version.get()
                return Response({
                    'connected': True,
                    'version': version,
                    'message': 'Successfully connected to Proxmox'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'connected': False,
                    'message': 'Failed to connect to Proxmox'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return Response(
                {'connected': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )