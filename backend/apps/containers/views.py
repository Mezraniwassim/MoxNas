from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import logging

from .models import MoxNasContainer, ContainerService
from .services import ContainerManagementService
from .serializers import MoxNasContainerSerializer, ContainerServiceSerializer, ContainerCreateSerializer

logger = logging.getLogger('moxnas.containers')


class ContainerListView(APIView):
    """List and create MoxNas containers"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            containers = MoxNasContainer.objects.all().order_by('vmid')
            serializer = MoxNasContainerSerializer(containers, many=True)
            
            # Also sync with Proxmox to get latest status
            service = ContainerManagementService()
            synced_count = service.sync_containers()
            
            return Response({
                'containers': serializer.data,
                'total': containers.count(),
                'synced': synced_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to fetch containers: {e}")
            return Response(
                {'error': 'Failed to fetch containers', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request):
        """Create a new MoxNas container"""
        try:
            serializer = ContainerCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            service = ContainerManagementService()
            container = service.create_moxnas_container(serializer.validated_data)
            
            if container:
                # Start installation in background (in production, use Celery)
                try:
                    service.install_moxnas_in_container(container)
                except Exception as install_error:
                    logger.error(f"Installation failed for container {container.vmid}: {install_error}")
                    container.status = 'error'
                    container.installation_log = str(install_error)
                    container.save()
                
                return Response({
                    'message': f'Container {container.vmid} created successfully',
                    'container': MoxNasContainerSerializer(container).data
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': 'Failed to create container'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Container creation error: {e}")
            return Response(
                {'error': 'Failed to create container', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContainerDetailView(APIView):
    """Individual container management"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, vmid):
        try:
            container = MoxNasContainer.objects.get(vmid=vmid)
            service = ContainerManagementService()
            
            # Get enhanced info from Proxmox
            container_info = service.get_container_info(vmid)
            serializer_data = MoxNasContainerSerializer(container).data
            
            # Merge Proxmox data
            response_data = {**serializer_data, **container_info}
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except MoxNasContainer.DoesNotExist:
            return Response(
                {'error': f'Container {vmid} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to get container {vmid}: {e}")
            return Response(
                {'error': f'Failed to get container {vmid}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, vmid):
        """Delete a container"""
        try:
            container = MoxNasContainer.objects.get(vmid=vmid)
            service = ContainerManagementService()
            
            success = service.delete_container(container)
            if success:
                return Response(
                    {'message': f'Container {vmid} deleted successfully'},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': f'Failed to delete container {vmid}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except MoxNasContainer.DoesNotExist:
            return Response(
                {'error': f'Container {vmid} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to delete container {vmid}: {e}")
            return Response(
                {'error': f'Failed to delete container {vmid}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContainerActionView(APIView):
    """Container actions (start, stop, restart)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, vmid, action):
        try:
            container = MoxNasContainer.objects.get(vmid=vmid)
            service = ContainerManagementService()
            
            if action == 'start':
                result = service.proxmox_service.start_container(vmid)
            elif action == 'stop':
                result = service.proxmox_service.stop_container(vmid)
            elif action == 'restart':
                service.proxmox_service.stop_container(vmid)
                result = service.proxmox_service.start_container(vmid)
            elif action == 'reinstall':
                result = service.install_moxnas_in_container(container)
            else:
                return Response(
                    {'error': f'Invalid action: {action}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if result:
                # Update container status
                if action in ['start', 'restart']:
                    container.status = 'running'
                elif action == 'stop':
                    container.status = 'stopped'
                container.save()
                
                return Response(
                    {'message': f'Container {vmid} {action} completed successfully'},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': f'Failed to {action} container {vmid}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except MoxNasContainer.DoesNotExist:
            return Response(
                {'error': f'Container {vmid} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Container {vmid} {action} error: {e}")
            return Response(
                {'error': f'Failed to {action} container {vmid}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContainerServicesView(APIView):
    """Manage services within a container"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, vmid):
        try:
            container = MoxNasContainer.objects.get(vmid=vmid)
            services = container.services.all()
            serializer = ContainerServiceSerializer(services, many=True)
            
            return Response({
                'services': serializer.data,
                'container': container.name
            }, status=status.HTTP_200_OK)
            
        except MoxNasContainer.DoesNotExist:
            return Response(
                {'error': f'Container {vmid} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to get services for container {vmid}: {e}")
            return Response(
                {'error': f'Failed to get services for container {vmid}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContainerServiceActionView(APIView):
    """Control individual services in a container"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, vmid, service_type, action):
        try:
            container = MoxNasContainer.objects.get(vmid=vmid)
            service_obj = container.services.get(service_type=service_type)
            
            # Service-specific commands
            service_commands = {
                'ssh': {
                    'start': 'systemctl start ssh',
                    'stop': 'systemctl stop ssh',
                    'status': 'systemctl is-active ssh'
                },
                'ftp': {
                    'start': 'systemctl start vsftpd',
                    'stop': 'systemctl stop vsftpd',
                    'status': 'systemctl is-active vsftpd'
                },
                'nfs': {
                    'start': 'systemctl start nfs-kernel-server',
                    'stop': 'systemctl stop nfs-kernel-server',
                    'status': 'systemctl is-active nfs-kernel-server'
                },
                'smb': {
                    'start': 'systemctl start smbd',
                    'stop': 'systemctl stop smbd',
                    'status': 'systemctl is-active smbd'
                }
            }
            
            if service_type not in service_commands:
                return Response(
                    {'error': f'Unknown service type: {service_type}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if action not in service_commands[service_type]:
                return Response(
                    {'error': f'Invalid action for {service_type}: {action}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Execute command
            service = ContainerManagementService()
            command = service_commands[service_type][action]
            result = service.proxmox_service.execute_command(vmid, command)
            
            if result is not None:
                # Update service status
                if action == 'start':
                    service_obj.status = 'running'
                elif action == 'stop':
                    service_obj.status = 'stopped'
                service_obj.save()
                
                return Response(
                    {'message': f'Service {service_type} {action} completed'},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': f'Failed to {action} service {service_type}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except MoxNasContainer.DoesNotExist:
            return Response(
                {'error': f'Container {vmid} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ContainerService.DoesNotExist:
            return Response(
                {'error': f'Service {service_type} not found in container {vmid}'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Service {service_type} {action} error in container {vmid}: {e}")
            return Response(
                {'error': f'Failed to {action} service {service_type}', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ContainerStatsView(APIView):
    """Get container statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            total_containers = MoxNasContainer.objects.count()
            running_containers = MoxNasContainer.objects.filter(status='running').count()
            stopped_containers = MoxNasContainer.objects.filter(status='stopped').count()
            error_containers = MoxNasContainer.objects.filter(status='error').count()
            
            # Service statistics
            total_services = ContainerService.objects.count()
            running_services = ContainerService.objects.filter(status='running').count()
            
            return Response({
                'containers': {
                    'total': total_containers,
                    'running': running_containers,
                    'stopped': stopped_containers,
                    'error': error_containers
                },
                'services': {
                    'total': total_services,
                    'running': running_services,
                    'stopped': total_services - running_services
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Failed to get container stats: {e}")
            return Response(
                {'error': 'Failed to get container statistics', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )