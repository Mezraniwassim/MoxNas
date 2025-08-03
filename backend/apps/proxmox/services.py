import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from proxmoxer import ProxmoxAPI
from django.conf import settings
from .models import ProxmoxNode, ProxmoxConnection

logger = logging.getLogger('moxnas.proxmox')


class ProxmoxService:
    """Service to handle Proxmox API interactions"""
    
    def __init__(self, node: Optional[ProxmoxNode] = None):
        self.node = node
        self._api = None
        
    def get_api_connection(self) -> Optional[ProxmoxAPI]:
        """Get or create Proxmox API connection"""
        if self._api:
            return self._api
            
        try:
            config = settings.PROXMOX_CONFIG
            if self.node:
                host = self.node.host
                user = self.node.username
                password = self.node.password
                port = self.node.port
                verify_ssl = self.node.verify_ssl
            else:
                host = config['HOST']
                user = config['USER']
                password = config['PASSWORD']
                port = config['PORT']
                verify_ssl = config['VERIFY_SSL']
            
            self._api = ProxmoxAPI(
                host,
                user=user,
                password=password,
                port=port,
                verify_ssl=verify_ssl
            )
            
            # Test connection
            self._api.version.get()
            self._update_connection_status(True)
            
            logger.info(f"Successfully connected to Proxmox at {host}")
            return self._api
            
        except Exception as e:
            self._update_connection_status(False, str(e))
            logger.error(f"Failed to connect to Proxmox: {e}")
            return None
    
    def _update_connection_status(self, connected: bool, error: str = ""):
        """Update connection status in database"""
        if self.node:
            connection, created = ProxmoxConnection.objects.get_or_create(
                node=self.node,
                defaults={
                    'is_connected': connected,
                    'connection_error': error,
                    'last_connected': datetime.now() if connected else None
                }
            )
            if not created:
                connection.is_connected = connected
                connection.connection_error = error
                if connected:
                    connection.last_connected = datetime.now()
                connection.save()
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get list of Proxmox nodes"""
        api = self.get_api_connection()
        if not api:
            return []
        
        try:
            nodes = api.nodes.get()
            return nodes
        except Exception as e:
            logger.error(f"Failed to get nodes: {e}")
            return []
    
    def get_node_status(self, node_name: str = None) -> Dict[str, Any]:
        """Get status of a specific node"""
        api = self.get_api_connection()
        if not api:
            return {}
        
        try:
            if not node_name:
                node_name = settings.PROXMOX_CONFIG['NODE']
            
            status = api.nodes(node_name).status.get()
            return status
        except Exception as e:
            logger.error(f"Failed to get node status: {e}")
            return {}
    
    def get_containers(self, node_name: str = None) -> List[Dict[str, Any]]:
        """Get list of LXC containers"""
        api = self.get_api_connection()
        if not api:
            return []
        
        try:
            if not node_name:
                node_name = settings.PROXMOX_CONFIG['NODE']
            
            containers = api.nodes(node_name).lxc.get()
            return containers
        except Exception as e:
            logger.error(f"Failed to get containers: {e}")
            return []
    
    def get_container_status(self, vmid: int, node_name: str = None) -> Dict[str, Any]:
        """Get status of a specific container"""
        api = self.get_api_connection()
        if not api:
            return {}
        
        try:
            if not node_name:
                node_name = settings.PROXMOX_CONFIG['NODE']
            
            status = api.nodes(node_name).lxc(vmid).status.current.get()
            return status
        except Exception as e:
            logger.error(f"Failed to get container {vmid} status: {e}")
            return {}
    
    def create_container(self, vmid: int, config: Dict[str, Any], node_name: str = None) -> bool:
        """Create a new LXC container"""
        api = self.get_api_connection()
        if not api:
            return False
        
        try:
            if not node_name:
                node_name = settings.PROXMOX_CONFIG['NODE']
            
            # Default configuration
            default_config = {
                'ostemplate': settings.CONTAINER_CONFIG['TEMPLATE'],
                'storage': settings.CONTAINER_CONFIG['STORAGE'],
                'memory': settings.CONTAINER_CONFIG['MEMORY'],
                'cores': settings.CONTAINER_CONFIG['CORES'],
                'swap': settings.CONTAINER_CONFIG['SWAP'],
                'unprivileged': 1,
                'onboot': 1,
                'start': 1,
            }
            
            # Merge with provided config
            final_config = {**default_config, **config}
            final_config['vmid'] = vmid
            
            task = api.nodes(node_name).lxc.create(**final_config)
            logger.info(f"Container {vmid} creation task started: {task}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create container {vmid}: {e}")
            return False
    
    def start_container(self, vmid: int, node_name: str = None) -> bool:
        """Start an LXC container"""
        api = self.get_api_connection()
        if not api:
            return False
        
        try:
            if not node_name:
                node_name = settings.PROXMOX_CONFIG['NODE']
            
            task = api.nodes(node_name).lxc(vmid).status.start.post()
            logger.info(f"Container {vmid} start task: {task}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start container {vmid}: {e}")
            return False
    
    def stop_container(self, vmid: int, node_name: str = None) -> bool:
        """Stop an LXC container"""
        api = self.get_api_connection()
        if not api:
            return False
        
        try:
            if not node_name:
                node_name = settings.PROXMOX_CONFIG['NODE']
            
            task = api.nodes(node_name).lxc(vmid).status.stop.post()
            logger.info(f"Container {vmid} stop task: {task}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop container {vmid}: {e}")
            return False
    
    def delete_container(self, vmid: int, node_name: str = None) -> bool:
        """Delete an LXC container"""
        api = self.get_api_connection()
        if not api:
            return False
        
        try:
            if not node_name:
                node_name = settings.PROXMOX_CONFIG['NODE']
            
            # Stop container first if running
            self.stop_container(vmid, node_name)
            
            # Delete container
            task = api.nodes(node_name).lxc(vmid).delete()
            logger.info(f"Container {vmid} deletion task: {task}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete container {vmid}: {e}")
            return False
    
    def execute_command(self, vmid: int, command: str, node_name: str = None) -> Dict[str, Any]:
        """Execute command in container"""
        api = self.get_api_connection()
        if not api:
            return {}
        
        try:
            if not node_name:
                node_name = settings.PROXMOX_CONFIG['NODE']
            
            result = api.nodes(node_name).lxc(vmid).exec.post(command=command)
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute command in container {vmid}: {e}")
            return {}
    
    def get_task_status(self, task_id: str, node_name: str = None) -> Dict[str, Any]:
        """Get status of a Proxmox task"""
        api = self.get_api_connection()
        if not api:
            return {}
        
        try:
            if not node_name:
                node_name = settings.PROXMOX_CONFIG['NODE']
            
            status = api.nodes(node_name).tasks(task_id).status.get()
            return status
            
        except Exception as e:
            logger.error(f"Failed to get task {task_id} status: {e}")
            return {}