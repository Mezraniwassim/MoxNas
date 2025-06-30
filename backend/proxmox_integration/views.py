"""
Django views for Proxmox integration
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from .models import ProxmoxHost, ProxmoxNode, ProxmoxContainer, ProxmoxStorage, ProxmoxTask
from .manager import get_proxmox_manager, initialize_proxmox_connection
from .realtime import get_realtime_aggregator, start_realtime_monitoring, stop_realtime_monitoring
from secure_config import SecureConfig
import json
import logging
import time

logger = logging.getLogger(__name__)


@api_view(['GET'])
def get_frontend_config(request):
    """
    Return safe configuration values for frontend use.
    Does NOT include sensitive information like passwords.
    """
    try:
        proxmox_config = SecureConfig.get_proxmox_config()
        
        safe_config = {
            'proxmox': {
                'host': proxmox_config.get('host', ''),
                'port': proxmox_config.get('port', 8006),
                'user': proxmox_config.get('user', 'root@pam'),
                'verify_ssl': proxmox_config.get('verify_ssl', False),
            },
            'network': {
                'interface': SecureConfig.get_network_config().get('interface', 'eth0'),
                'bridge': SecureConfig.get_network_config().get('bridge', 'vmbr0'),
            },
            'storage': {
                'pool': SecureConfig.get_storage_config().get('pool', 'local-lvm'),
                'iso_storage': SecureConfig.get_storage_config().get('iso_storage', 'local'),
            }
        }
        
        return JsonResponse({
            'success': True,
            'config': safe_config
        })
    except Exception as e:
        logger.error(f"Failed to get frontend config: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load configuration'
        }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ProxmoxHostViewSet(viewsets.ModelViewSet):
    """Manage Proxmox host configurations"""
    queryset = ProxmoxHost.objects.all()
    
    def list(self, request):
        hosts = self.get_queryset()
        data = [
            {
                'id': host.id,
                'name': host.name,
                'host': host.host,
                'port': host.port,
                'user': host.user,
                'verify_ssl': host.verify_ssl,
                'is_active': host.is_active,
                'is_connected': host.is_connected,
                'last_connected': host.last_connected.isoformat() if host.last_connected else None,
            } for host in hosts
        ]
        return Response(data)
    
    def create(self, request):
        """Create a new Proxmox host"""
        try:
            data = request.data
            
            # Extract password but don't store it in the model
            password = data.get('password', '')
            
            # Create the host record
            host = ProxmoxHost.objects.create(
                name=data.get('name', ''),
                host=data.get('host', ''),
                port=data.get('port', 8006),
                user=data.get('user', 'root@pam'),
                verify_ssl=data.get('verify_ssl', False),
                is_active=True
            )
            
            # Test connection immediately after creation
            from .manager import test_proxmox_connection
            success, message = test_proxmox_connection(
                host=host.host,
                user=host.user,
                password=password,
                port=host.port,
                verify_ssl=host.verify_ssl
            )
            
            if success:
                host.is_connected = True
                host.last_connected = timezone.now()
                host.save()
                
                # Store password securely for this session
                # Note: In production, consider using encrypted storage
                from django.core.cache import cache
                cache.set(f'proxmox_password_{host.id}', password, 3600)  # 1 hour
                
                return Response({
                    'id': host.id,
                    'name': host.name,
                    'host': host.host,
                    'port': host.port,
                    'user': host.user,
                    'verify_ssl': host.verify_ssl,
                    'is_active': host.is_active,
                    'is_connected': host.is_connected,
                    'last_connected': host.last_connected.isoformat() if host.last_connected else None,
                }, status=status.HTTP_201_CREATED)
            else:
                host.delete()  # Remove if connection failed
                return Response({
                    'error': f'Failed to connect to Proxmox host: {message}'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Failed to create Proxmox host: {str(e)}")
            return Response({
                'error': f'Failed to create host: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def connect(self, request, pk=None):
        """Test and establish connection to a Proxmox host"""
        try:
            host = self.get_object()
            password = request.data.get('password', '')
            
            # Try to get password from cache if not provided
            if not password:
                from django.core.cache import cache
                password = cache.get(f'proxmox_password_{host.id}', '')
            
            if not password:
                return Response({
                    'error': 'Password required for connection'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from .manager import test_proxmox_connection
            success, message = test_proxmox_connection(
                host=host.host,
                user=host.user,
                password=password,
                port=host.port,
                verify_ssl=host.verify_ssl
            )
            
            if success:
                host.is_connected = True
                host.last_connected = timezone.now()
                host.save()
                
                return Response({
                    'success': True,
                    'message': f'Successfully connected to {host.name}',
                    'version': message  # test_proxmox_connection returns version info on success
                })
            else:
                host.is_connected = False
                host.save()
                return Response({
                    'success': False,
                    'error': message
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox host {pk}: {str(e)}")
            return Response({
                'success': False,
                'error': f'Connection failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class ProxmoxNodeViewSet(viewsets.ModelViewSet):
    """Manage Proxmox nodes"""
    queryset = ProxmoxNode.objects.all()
    
    def list(self, request):
        nodes = self.get_queryset()
        data = [
            {
                'id': node.id,
                'proxmox_host': node.proxmox_host.name,
                'name': node.name,
                'status': node.status,
                'uptime': node.uptime,
                'cpu_usage': node.cpu_usage,
                'memory_total': node.memory_total,
                'memory_used': node.memory_used,
                'memory_usage_percentage': node.memory_usage_percentage,
                'storage_total': node.storage_total,
                'storage_used': node.storage_used,
                'storage_usage_percentage': node.storage_usage_percentage,
                'last_updated': node.last_updated.isoformat(),
            } for node in nodes
        ]
        return Response(data)


@method_decorator(csrf_exempt, name='dispatch')
class ProxmoxContainerViewSet(viewsets.ModelViewSet):
    """Manage Proxmox containers"""
    queryset = ProxmoxContainer.objects.all()
    
    def list(self, request):
        containers = self.get_queryset()
        data = [
            {
                'id': container.id,
                'node': container.proxmox_node.name,
                'vmid': container.vmid,
                'name': container.name,
                'hostname': container.hostname,
                'status': container.status,
                'template': container.template,
                'cores': container.cores,
                'memory': container.memory,
                'swap': container.swap,
                'disk_size': container.disk_size,
                'uptime': container.uptime,
                'cpu_usage': container.cpu_usage,
                'memory_usage': container.memory_usage,
                'memory_usage_percentage': container.memory_usage_percentage,
                'is_moxnas': container.is_moxnas,
                'last_updated': container.last_updated.isoformat(),
            } for container in containers
        ]
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a container"""
        container = self.get_object()
        manager = get_proxmox_manager()
        
        if not manager:
            return Response({'error': 'Not connected to Proxmox'}, 
                          status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        success = manager.start_container(container.proxmox_node.name, container.vmid)
        if success:
            container.status = 'running'
            container.save()
            return Response({'success': True, 'message': f'Container {container.vmid} started'})
        else:
            return Response({'error': 'Failed to start container'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop a container"""
        container = self.get_object()
        manager = get_proxmox_manager()
        
        if not manager:
            return Response({'error': 'Not connected to Proxmox'}, 
                          status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        success = manager.stop_container(container.proxmox_node.name, container.vmid)
        if success:
            container.status = 'stopped'
            container.save()
            return Response({'success': True, 'message': f'Container {container.vmid} stopped'})
        else:
            return Response({'error': 'Failed to stop container'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def create_container(self, request):
        """Create a new container"""
        manager = get_proxmox_manager()
        
        # Initialize Proxmox connection if not already connected
        if not manager:
            logger.info("No Proxmox manager found, initializing connection...")
            from .manager import initialize_proxmox_connection
            from django.conf import settings
            
            # Get connection parameters from Django settings (which loads from environment variables)
            proxmox_config = getattr(settings, 'PROXMOX_CONFIG', {})
            success = initialize_proxmox_connection(
                host=proxmox_config.get('HOST', ''),
                user=proxmox_config.get('USER', 'root@pam'),
                password=proxmox_config.get('PASSWORD', ''),
                port=proxmox_config.get('PORT', 8006),
                verify_ssl=proxmox_config.get('VERIFY_SSL', False)
            )
            
            if success:
                manager = get_proxmox_manager()
                logger.info("Proxmox connection initialized successfully")
            else:
                logger.warning("Failed to initialize Proxmox connection, falling back to demo mode")
        
        # Demo mode: Simulate container creation when not connected to Proxmox
        if not manager:
            data = request.data
            node = data.get('node')
            vmid = data.get('vmid')
            hostname = data.get('hostname')
            
            if not all([node, vmid, hostname]):
                return Response({'error': 'Node, VMID, and hostname are required'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Simulate container creation with demo data
            container_data = {
                'vmid': vmid,
                'hostname': hostname,
                'node': node,
                'status': 'stopped',
                'memory': data.get('memory', 4096),
                'cores': data.get('cores', 2),
                'disk_size': data.get('disk_size', '32G'),
                'ip_address': 'dhcp' if data.get('ip_type') == 'dhcp' else data.get('ip_address', '192.168.1.100'),
                'created': True
            }
            
            return Response({
                'success': True,
                'message': f'Container {vmid} ({hostname}) created successfully (Demo Mode)',
                'data': container_data
            })
        
        try:
            data = request.data
            node = data.get('node')
            vmid = data.get('vmid')
            hostname = data.get('hostname')
            memory = data.get('memory', 4096)
            cores = data.get('cores', 2)
            disk_size = data.get('disk_size', '32G')
            storage_pool = data.get('storage_pool', 'local-lvm')
            template_storage = data.get('template_storage', 'local')
            network_bridge = data.get('network_bridge', 'vmbr0')
            ipv4 = data.get('ipv4', 'dhcp')
            gateway = data.get('gateway')
            
            if not all([node, vmid, hostname]):
                return Response({'error': 'Node, VMID, and hostname are required'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Get bridge and IP configuration
            bridge = data.get('bridge', 'vmbr0')
            ip_type = data.get('ip_type', 'dhcp')
            
            # Build network configuration
            if ip_type == 'dhcp':
                net_config = f"name=eth0,bridge={bridge},ip=dhcp"
            else:
                ip_address = data.get('ip_address', '')
                gateway = data.get('gateway', '')
                if ip_address:
                    net_config = f"name=eth0,bridge={bridge},ip={ip_address}"
                    if gateway:
                        net_config += f",gw={gateway}"
                else:
                    net_config = f"name=eth0,bridge={bridge},ip=dhcp"
            
            # Generate container configuration for Proxmox API
            # According to Proxmox API documentation and existing container format
            config = {
                "vmid": vmid,
                "hostname": hostname,
                "ostemplate": f"local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst",
                "cores": cores,
                "memory": memory,
                "swap": 512,
                "rootfs": f"{storage_pool}:{disk_size}G",  # Storage:size format
                "net0": net_config,
                "onboot": 1,
                "unprivileged": 1,
                "features": "nesting=1"
            }
            
            logger.info(f"Creating container with config: {config}")
            
            # Create container using the manager
            result = manager.create_container(node, vmid, config)
            
            if result["success"]:
                # Create ProxmoxContainer record
                proxmox_node = ProxmoxNode.objects.filter(name=node).first()
                container = None
                if proxmox_node:
                    container = ProxmoxContainer.objects.create(
                        proxmox_node=proxmox_node,
                        vmid=vmid,
                        name=hostname,
                        hostname=hostname,
                        status='stopped',
                        memory=memory,
                        cores=cores,
                        disk_size=int(disk_size.replace('G', '')) * 1024,  # Convert to MB
                        template='debian-12-standard',
                        is_moxnas=True
                    )
                
                return Response({
                    'success': True, 
                    'message': f'Container {vmid} created successfully',
                    'container_id': container.id if container else None,
                    'vmid': vmid,
                    'result': result.get("result")
                })
            else:
                error_msg = result.get("error", "Failed to create container")
                logger.error(f"Container creation failed: {error_msg}")
                return Response({
                    'success': False,
                    'error': error_msg,
                    'config': result.get("config")
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error creating container: {e}")
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def templates(self, request):
        """Get available container templates"""
        manager = get_proxmox_manager()
        
        if not manager:
            # Return demo data when not connected to Proxmox
            demo_templates = [
                {
                    'name': 'debian-12-standard_12.7-1_amd64.tar.zst',
                    'volid': 'local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst',
                    'description': 'Debian 12 Standard',
                    'size': 150000000,  # ~150MB
                    'format': 'tar.zst'
                },
                {
                    'name': 'ubuntu-22.04-standard_22.04-1_amd64.tar.zst',
                    'volid': 'local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst',
                    'description': 'Ubuntu 22.04 Standard',
                    'size': 200000000,  # ~200MB
                    'format': 'tar.zst'
                },
                {
                    'name': 'alpine-3.18-default_20230607_amd64.tar.xz',
                    'volid': 'local:vztmpl/alpine-3.18-default_20230607_amd64.tar.xz',
                    'description': 'Alpine Linux 3.18',
                    'size': 50000000,   # ~50MB
                    'format': 'tar.xz'
                }
            ]
            return Response({'success': True, 'data': demo_templates})
        
        try:
            node = request.query_params.get('node')
            if not node:
                # Get first available node
                nodes = manager.get_nodes()
                if not nodes:
                    return Response({'error': 'No nodes available'}, 
                                  status=status.HTTP_404_NOT_FOUND)
                node = nodes[0].get('node')
            
            # Get list of available templates
            templates = manager.get_templates(node) if hasattr(manager, 'get_templates') else []
            
            # Format response
            template_list = [
                {
                    'name': template.get('volid', '').split('/')[-1],
                    'volid': template.get('volid', ''),
                    'size': template.get('size', 0),
                    'format': template.get('format', 'unknown')
                }
                for template in templates
                if template.get('volid', '').endswith(('.tar.gz', '.tar.zst', '.tar.xz'))
            ]
            
            return Response({'success': True, 'data': template_list})
            
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def nodes(self, request):
        """Get available Proxmox nodes"""
        manager = get_proxmox_manager()
        
        if not manager:
            # Return demo data when not connected to Proxmox
            demo_nodes = [
                {'name': 'pve', 'status': 'online', 'type': 'node'},
                {'name': 'pve2', 'status': 'online', 'type': 'node'}
            ]
            return Response({'success': True, 'data': demo_nodes})
        
        try:
            nodes = manager.get_nodes()
            node_list = [
                {
                    'name': node.get('node'),
                    'status': node.get('status'),
                    'type': node.get('type', 'node')
                }
                for node in nodes
                if node.get('type') == 'node'
            ]
            
            return Response({'success': True, 'data': node_list})
            
        except Exception as e:
            logger.error(f"Error getting nodes: {e}")
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def storage_pools(self, request):
        """Get available storage pools for a node"""
        manager = get_proxmox_manager()
        
        if not manager:
            # Return demo data when not connected to Proxmox
            demo_storage = [
                {
                    'storage': 'local',
                    'type': 'dir',
                    'content': ['rootdir', 'images'],
                    'avail': 50 * 1024 * 1024 * 1024,  # 50GB
                    'used': 10 * 1024 * 1024 * 1024    # 10GB
                },
                {
                    'storage': 'local-lvm',
                    'type': 'lvm',
                    'content': ['rootdir', 'images'],
                    'avail': 100 * 1024 * 1024 * 1024,  # 100GB
                    'used': 20 * 1024 * 1024 * 1024     # 20GB
                }
            ]
            return Response({'success': True, 'data': demo_storage})
        
        try:
            node = request.query_params.get('node')
            if not node:
                # Get first available node
                nodes = manager.get_nodes()
                if not nodes:
                    return Response({'error': 'No nodes available'}, 
                                  status=status.HTTP_404_NOT_FOUND)
                node = nodes[0].get('node')
            
            # Get storage for the node
            storage_data = manager.get_storage(node) if hasattr(manager, 'get_storage') else []
            
            # Filter for container storage
            storage_pools = []
            for storage in storage_data:
                content = storage.get('content', '')
                if 'rootdir' in content or 'images' in content:
                    storage_pools.append({
                        'id': storage.get('storage'),
                        'type': storage.get('type'),
                        'content': content.split(','),
                        'enabled': storage.get('enabled', 1) == 1,
                        'shared': storage.get('shared', 0) == 1,
                        'available': storage.get('avail', 0),
                        'total': storage.get('total', 0),
                        'used': storage.get('used', 0)
                    })
            
            return Response({'storage_pools': storage_pools})
            
        except Exception as e:
            logger.error(f"Error getting storage pools: {e}")
            return Response({'error': str(e)}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class ProxmoxStorageViewSet(viewsets.ModelViewSet):
    """Manage Proxmox storage"""
    queryset = ProxmoxStorage.objects.all()
    
    def list(self, request):
        storage = self.get_queryset()
        data = [
            {
                'id': store.id,
                'node': store.proxmox_node.name,
                'storage_id': store.storage_id,
                'storage_type': store.storage_type,
                'content_types': store.content_types_list,
                'total_space': store.total_space,
                'used_space': store.used_space,
                'available_space': store.available_space,
                'usage_percentage': store.usage_percentage,
                'enabled': store.enabled,
                'shared': store.shared,
                'last_updated': store.last_updated.isoformat(),
            } for store in storage
        ]
        return Response(data)


@csrf_exempt
@api_view(['POST'])
def connect_proxmox(request):
    """Connect to Proxmox host"""
    try:
        data = json.loads(request.body)
        host = data.get('host')
        user = data.get('user', 'root@pam')
        password = data.get('password')
        port = data.get('port', 8006)
        verify_ssl = data.get('verify_ssl', False)
        
        if not host or not password:
            return JsonResponse({'error': 'Host and password are required'}, status=400)
        
        # Initialize connection
        success = initialize_proxmox_connection(host, user, password, port, verify_ssl)
        
        if success:
            # Update or create ProxmoxHost record
            proxmox_host, created = ProxmoxHost.objects.get_or_create(
                host=host,
                defaults={
                    'name': f"Proxmox-{host}",
                    'user': user,
                    'port': port,
                    'verify_ssl': verify_ssl,
                    'is_connected': True,
                }
            )
            
            if not created:
                proxmox_host.is_connected = True
                proxmox_host.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Connected to Proxmox successfully',
                'host_id': proxmox_host.id
            })
        else:
            return JsonResponse({'error': 'Failed to connect to Proxmox'}, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error connecting to Proxmox: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
def sync_proxmox_data(request):
    """Sync data from Proxmox"""
    manager = get_proxmox_manager()
    
    if not manager:
        return JsonResponse({'error': 'Not connected to Proxmox'}, status=503)
    
    try:
        # Get nodes
        nodes_data = manager.get_nodes()
        synced_nodes = 0
        synced_containers = 0
        synced_storage = 0
        
        # Get the active Proxmox host
        proxmox_host = ProxmoxHost.objects.filter(is_connected=True).first()
        if not proxmox_host:
            return JsonResponse({'error': 'No active Proxmox host found'}, status=404)
        
        for node_data in nodes_data:
            node_name = node_data.get('node')
            if not node_name:
                continue
            
            # Get detailed node status
            node_status = manager.get_node_status(node_name)
            
            # Create or update node
            node, created = ProxmoxNode.objects.get_or_create(
                proxmox_host=proxmox_host,
                name=node_name,
                defaults={
                    'status': node_data.get('status', 'unknown'),
                    'uptime': node_status.get('uptime', 0),
                    'cpu_usage': node_status.get('cpu', 0) * 100 if node_status.get('cpu') else 0,
                    'memory_total': node_status.get('memory', {}).get('total', 0),
                    'memory_used': node_status.get('memory', {}).get('used', 0),
                }
            )
            
            if not created:
                node.status = node_data.get('status', 'unknown')
                node.uptime = node_status.get('uptime', 0)
                node.cpu_usage = node_status.get('cpu', 0) * 100 if node_status.get('cpu') else 0
                node.memory_total = node_status.get('memory', {}).get('total', 0)
                node.memory_used = node_status.get('memory', {}).get('used', 0)
                node.save()
            
            synced_nodes += 1
            
            # Sync containers for this node
            containers_data = manager.get_containers(node_name)
            for container_data in containers_data:
                vmid = container_data.get('vmid')
                if not vmid:
                    continue
                
                container, created = ProxmoxContainer.objects.get_or_create(
                    proxmox_node=node,
                    vmid=vmid,
                    defaults={
                        'name': container_data.get('name', f'CT{vmid}'),
                        'status': container_data.get('status', 'unknown'),
                        'memory': container_data.get('maxmem', 0) // (1024 * 1024),  # Convert to MB
                        'cores': container_data.get('cpus', 1),
                        'uptime': container_data.get('uptime', 0),
                        'cpu_usage': container_data.get('cpu', 0) * 100 if container_data.get('cpu') else 0,
                    }
                )
                
                if not created:
                    container.status = container_data.get('status', 'unknown')
                    container.uptime = container_data.get('uptime', 0)
                    container.cpu_usage = container_data.get('cpu', 0) * 100 if container_data.get('cpu') else 0
                    container.save()
                
                synced_containers += 1
            
            # Sync storage for this node
            storage_data = manager.get_storage(node_name)
            for storage_item in storage_data:
                storage_id = storage_item.get('storage')
                if not storage_id:
                    continue
                
                storage, created = ProxmoxStorage.objects.get_or_create(
                    proxmox_node=node,
                    storage_id=storage_id,
                    defaults={
                        'storage_type': storage_item.get('type', 'unknown'),
                        'content_types': json.dumps(storage_item.get('content', '').split(',')),
                        'total_space': storage_item.get('total', 0),
                        'used_space': storage_item.get('used', 0),
                        'available_space': storage_item.get('avail', 0),
                        'enabled': storage_item.get('enabled', 1) == 1,
                        'shared': storage_item.get('shared', 0) == 1,
                    }
                )
                
                if not created:
                    storage.total_space = storage_item.get('total', 0)
                    storage.used_space = storage_item.get('used', 0)
                    storage.available_space = storage_item.get('avail', 0)
                    storage.enabled = storage_item.get('enabled', 1) == 1
                    storage.save()
                
                synced_storage += 1
        
        return JsonResponse({
            'success': True,
            'message': 'Proxmox data synced successfully',
            'stats': {
                'nodes': synced_nodes,
                'containers': synced_containers,
                'storage': synced_storage,
            }
        })
        
    except Exception as e:
        logger.error(f"Error syncing Proxmox data: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@api_view(['GET'])
def proxmox_cluster_status(request):
    """Get Proxmox cluster status"""
    manager = get_proxmox_manager()
    
    if not manager:
        return JsonResponse({'error': 'Not connected to Proxmox'}, status=503)
    
    try:
        cluster_status = manager.get_cluster_status()
        return JsonResponse(cluster_status)
    except Exception as e:
        logger.error(f"Error getting cluster status: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# Real-time monitoring endpoints
@csrf_exempt
@api_view(['GET'])
def realtime_dashboard(request):
    """Get real-time dashboard data"""
    try:
        aggregator = get_realtime_aggregator()
        dashboard_data = aggregator.get_dashboard_data()
        
        return JsonResponse({
            'success': True,
            'data': dashboard_data,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting real-time dashboard data: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }, status=500)


@csrf_exempt
@api_view(['GET'])
def realtime_node_data(request, node_name):
    """Get real-time data for a specific node"""
    try:
        aggregator = get_realtime_aggregator()
        node_data = aggregator.get_node_data(node_name)
        
        return JsonResponse({
            'success': True,
            'data': node_data,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting real-time node data: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }, status=500)


@csrf_exempt
@api_view(['GET'])
def realtime_container_data(request, node_name, vmid):
    """Get real-time data for a specific container"""
    try:
        aggregator = get_realtime_aggregator()
        container_data = aggregator.get_container_data(node_name, int(vmid))
        
        return JsonResponse({
            'success': True,
            'data': container_data,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting real-time container data: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }, status=500)


@csrf_exempt
@api_view(['POST'])
def start_monitoring(request):
    """Start real-time monitoring service"""
    try:
        start_realtime_monitoring()
        return JsonResponse({
            'success': True,
            'message': 'Real-time monitoring started',
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }, status=500)


@csrf_exempt
@api_view(['POST'])
def stop_monitoring(request):
    """Stop real-time monitoring service"""
    try:
        stop_realtime_monitoring()
        return JsonResponse({
            'success': True,
            'message': 'Real-time monitoring stopped',
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }, status=500)


@csrf_exempt
@api_view(['GET'])
def monitoring_status(request):
    """Get monitoring service status"""
    try:
        aggregator = get_realtime_aggregator()
        is_running = aggregator.monitor.is_running
        
        return JsonResponse({
            'success': True,
            'monitoring_active': is_running,
            'update_interval': aggregator.monitor.update_interval,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': time.time()
        }, status=500)
