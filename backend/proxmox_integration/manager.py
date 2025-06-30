"""
Proxmox VE API Integration for MoxNAS

This module provides integration with Proxmox VE to manage containers,
storage, networking, and system resources directly from MoxNAS.
"""

import logging
from typing import Optional, Dict, List, Any
from proxmoxer import ProxmoxAPI
import ssl


logger = logging.getLogger(__name__)


class ProxmoxManager:
    """Manages connection and operations with Proxmox VE host"""
    
    def __init__(self, host: str, user: str = "root@pam", 
                 port: int = 8006, verify_ssl: bool = False):
        """
        Initialize Proxmox manager
        
        Args:
            host: Proxmox host IP/hostname (loaded from environment variables)
            user: Proxmox user (default: root@pam)
            port: Proxmox API port (default: 8006)
            verify_ssl: Whether to verify SSL certificates
        """
        self.host = host
        self.user = user
        self.port = port
        self.verify_ssl = verify_ssl
        self.api = None
        self.is_connected = False
        
    def connect(self, password: str) -> bool:
        """
        Connect to Proxmox VE API
        
        Args:
            password: User password
            
        Returns:
            bool: True if connection successful
        """
        try:
            # Create ProxmoxAPI connection with proper SSL handling
            self.api = ProxmoxAPI(
                host=self.host,
                user=self.user,
                password=password,
                verify_ssl=self.verify_ssl,
                port=self.port
            )
            
            # Test connection by getting version
            version = self.api.version.get()
            self.is_connected = True
            logger.info(f"Connected to Proxmox VE {version.get('version', 'Unknown')} at {self.host}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox: {e}")
            self.is_connected = False
            return False
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status information"""
        if not self.is_connected:
            return {"error": "Not connected to Proxmox"}
        
        try:
            status = self.api.cluster.status.get()
            return {"cluster_status": status}
        except Exception as e:
            logger.error(f"Error getting cluster status: {e}")
            return {"error": str(e)}
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get list of Proxmox nodes"""
        if not self.is_connected:
            return []
        
        try:
            nodes = self.api.nodes.get()
            return nodes
        except Exception as e:
            logger.error(f"Error getting nodes: {e}")
            return []
    
    def get_node_status(self, node: str) -> Dict[str, Any]:
        """Get detailed status of a specific node"""
        if not self.is_connected:
            return {"error": "Not connected to Proxmox"}
        
        try:
            status = self.api.nodes(node).status.get()
            return status
        except Exception as e:
            logger.error(f"Error getting node {node} status: {e}")
            return {"error": str(e)}
    
    def get_containers(self, node: str) -> List[Dict[str, Any]]:
        """Get list of LXC containers on a node"""
        if not self.is_connected:
            return []
        
        try:
            containers = self.api.nodes(node).lxc.get()
            return containers
        except Exception as e:
            logger.error(f"Error getting containers for node {node}: {e}")
            return []
    
    def get_container_status(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get status of a specific container"""
        if not self.is_connected:
            return {"error": "Not connected to Proxmox"}
        
        try:
            status = self.api.nodes(node).lxc(vmid).status.current.get()
            return status
        except Exception as e:
            logger.error(f"Error getting container {vmid} status: {e}")
            return {"error": str(e)}
    
    def get_storage(self, node: str) -> List[Dict[str, Any]]:
        """Get storage information for a node"""
        if not self.is_connected:
            return []
        
        try:
            storage = self.api.nodes(node).storage.get()
            return storage
        except Exception as e:
            logger.error(f"Error getting storage for node {node}: {e}")
            return []
    
    def get_storage_content(self, node: str, storage: str) -> List[Dict[str, Any]]:
        """Get content of a specific storage"""
        if not self.is_connected:
            return []
        
        try:
            content = self.api.nodes(node).storage(storage).content.get()
            return content
        except Exception as e:
            logger.error(f"Error getting storage {storage} content: {e}")
            return []
    
    def get_virtual_machines(self, node: str) -> List[Dict[str, Any]]:
        """Get list of virtual machines on a node"""
        if not self.is_connected:
            return []
        
        try:
            vms = self.api.nodes(node).qemu.get()
            return vms
        except Exception as e:
            logger.error(f"Error getting VMs for node {node}: {e}")
            return []
    
    def create_container(self, node: str, vmid: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new LXC container using Proxmox API
        
        Args:
            node: Target node name
            vmid: Container ID
            config: Container configuration
            
        Returns:
            Dict with success status and result/error message
        """
        if not self.is_connected:
            logger.warning("Not connected to Proxmox - cannot create container")
            return {"success": False, "error": "Not connected to Proxmox"}
        
        try:
            # Ensure vmid is included in config
            config['vmid'] = vmid
            
            # Validate required parameters according to Proxmox API docs
            required_params = ['vmid', 'ostemplate']
            missing_params = [param for param in required_params if param not in config]
            if missing_params:
                error_msg = f"Missing required parameters: {missing_params}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
            
            # Create container using the correct API endpoint
            # According to Proxmox API: POST /nodes/{node}/lxc
            logger.info(f"Creating container {vmid} on node {node} with config: {config}")
            result = self.api.nodes(node).lxc.post(**config)
            
            logger.info(f"Container {vmid} created successfully on node {node}")
            logger.debug(f"Create container result: {result}")
            return {"success": True, "result": result, "vmid": vmid}
            
        except Exception as e:
            error_msg = f"Error creating container {vmid} on node {node}: {e}"
            logger.error(error_msg)
            logger.error(f"Config used: {config}")
            return {"success": False, "error": str(e), "config": config}
    
    def get_templates(self, node: str, storage: str = 'local') -> List[Dict[str, Any]]:
        """
        Get available container templates from storage
        
        Args:
            node: Node name
            storage: Storage name (default: 'local')
            
        Returns:
            List of available templates
        """
        if not self.is_connected:
            return []
        
        try:
            # Get storage content filtered by templates
            # According to Proxmox API: GET /nodes/{node}/storage/{storage}/content
            content = self.api.nodes(node).storage(storage).content.get(content='vztmpl')
            return content
        except Exception as e:
            logger.error(f"Error getting templates from {storage} on node {node}: {e}")
            return []
    
    def get_container_config(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get container configuration"""
        if not self.is_connected:
            return {}
        
        try:
            config = self.api.nodes(node).lxc(vmid).config.get()
            return config
        except Exception as e:
            logger.error(f"Error getting container {vmid} config: {e}")
            return {}
    
    def delete_container(self, node: str, vmid: int) -> bool:
        """Delete a container"""
        if not self.is_connected:
            return False
        
        try:
            self.api.nodes(node).lxc(vmid).delete()
            logger.info(f"Container {vmid} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting container {vmid}: {e}")
            return False
    
    def start_container(self, node: str, vmid: int) -> bool:
        """Start a container"""
        if not self.is_connected:
            return False
        
        try:
            self.api.nodes(node).lxc(vmid).status.start.post()
            logger.info(f"Container {vmid} started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting container {vmid}: {e}")
            return False
    
    def stop_container(self, node: str, vmid: int) -> bool:
        """Stop a container"""
        if not self.is_connected:
            return False
        
        try:
            self.api.nodes(node).lxc(vmid).status.stop.post()
            logger.info(f"Container {vmid} stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Error stopping container {vmid}: {e}")
            return False
    
    def get_tasks(self, node: str) -> List[Dict[str, Any]]:
        """Get list of tasks for a node"""
        if not self.is_connected:
            return []
        
        try:
            tasks = self.api.nodes(node).tasks.get()
            return tasks
        except Exception as e:
            logger.error(f"Error getting tasks for node {node}: {e}")
            return []


# Global Proxmox manager instance
proxmox_manager = None


def get_proxmox_manager() -> Optional[ProxmoxManager]:
    """Get the global Proxmox manager instance"""
    return proxmox_manager


def initialize_proxmox_connection(host: str, user: str, password: str, 
                                port: int = 8006, verify_ssl: bool = False) -> bool:
    """
    Initialize global Proxmox connection
    
    Args:
        host: Proxmox host
        user: Username
        password: Password
        port: API port
        verify_ssl: SSL verification
        
    Returns:
        bool: True if connection successful
    """
    global proxmox_manager
    
    proxmox_manager = ProxmoxManager(host, user, port, verify_ssl)
    success = proxmox_manager.connect(password)
    
    if not success:
        proxmox_manager = None
        
    return success


def test_proxmox_connection(host: str, user: str, password: str, 
                          port: int = 8006, verify_ssl: bool = False) -> tuple[bool, str]:
    """
    Test connection to Proxmox without storing the connection globally
    
    Args:
        host: Proxmox host
        user: Username
        password: Password
        port: API port
        verify_ssl: SSL verification
        
    Returns:
        tuple: (success: bool, message: str) - message contains version info on success or error on failure
    """
    try:
        # Create temporary ProxmoxAPI connection
        api = ProxmoxAPI(
            host=host,
            user=user,
            password=password,
            verify_ssl=verify_ssl,
            port=port
        )
        
        # Test connection by getting version
        version = api.version.get()
        version_str = version.get('version', 'Unknown')
        
        logger.info(f"Successfully tested connection to Proxmox VE {version_str} at {host}")
        return True, version_str
        
    except Exception as e:
        logger.error(f"Failed to test connection to Proxmox at {host}: {e}")
        return False, str(e)
