"""
Proxmox VE API Integration for MoxNAS

This module provides integration with Proxmox VE to manage containers,
storage, networking, and system resources directly from MoxNAS.
"""

import logging
import time
from typing import Optional, Dict, List, Any, Union
from proxmoxer import ProxmoxAPI
import ssl
from .models import ProxmoxHost


logger = logging.getLogger(__name__)


class ProxmoxManager:
    """Enhanced Proxmox API Manager with session management and caching"""
    
    def __init__(self, host_config: Union[ProxmoxHost, Dict[str, Any], str]):
        """
        Initialize Proxmox manager
        
        Args:
            host_config: ProxmoxHost instance, configuration dict, or hostname string
        """
        if isinstance(host_config, ProxmoxHost):
            self.host = host_config.host
            self.port = host_config.port
            self.user = f"{host_config.username}@{host_config.realm}"
            self.password = host_config.password
            self.verify_ssl = host_config.ssl_verify
            self.host_obj = host_config
        elif isinstance(host_config, dict):
            self.host = host_config['host']
            self.port = host_config.get('port', 8006)
            self.user = f"{host_config['username']}@{host_config.get('realm', 'pam')}"
            self.password = host_config['password']
            self.verify_ssl = host_config.get('ssl_verify', False)
            self.host_obj = None
        else:
            # Legacy string hostname support
            self.host = host_config
            self.port = 8006
            self.user = "root@pam"
            self.password = None
            self.verify_ssl = False
            self.host_obj = None
        
        self.api = None
        self.is_connected = False
        self._session = None
        self._last_auth_time = None
        self._auth_timeout = 7200  # 2 hours
        
    def _ensure_connection(self) -> bool:
        """
        Ensure we have a valid connection, reuse existing session if possible
        
        Returns:
            bool: True if connection is valid
        """
        current_time = time.time()
        
        # Check if we need to authenticate
        if (self.api is None or 
            self._last_auth_time is None or 
            current_time - self._last_auth_time > self._auth_timeout):
            return self.connect()
        
        return self.is_connected
        
    def connect(self, password: str = None) -> bool:
        """
        Connect to Proxmox VE API with session management
        
        Args:
            password: User password (optional if already set)
            
        Returns:
            bool: True if connection successful
        """
        try:
            # Use provided password or existing one
            auth_password = password or self.password
            if not auth_password:
                logger.error("No password provided for Proxmox connection")
                return False
            
            # Create ProxmoxAPI connection with proper SSL handling
            self.api = ProxmoxAPI(
                host=self.host,
                user=self.user,
                password=auth_password,
                verify_ssl=self.verify_ssl,
                port=self.port
            )
            
            # Test connection by getting version
            version = self.api.version.get()
            self.is_connected = True
            self._last_auth_time = time.time()
            
            # Store password for session management
            if password:
                self.password = password
            
            logger.info(f"Connected to Proxmox VE {version.get('version', 'Unknown')} at {self.host}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox: {e}")
            
            # Provide helpful debugging information
            if "ConnectTimeoutError" in str(e) or "timed out" in str(e):
                logger.error("Connection timeout - possible causes:")
                logger.error("1. Proxmox host is not reachable from this network")
                logger.error("2. Firewall blocking port 8006")
                logger.error("3. Proxmox service not running")
                logger.error(f"4. Verify host {self.host} is accessible")
            elif "SSLError" in str(e):
                logger.error("SSL Error - possible causes:")
                logger.error("1. Self-signed certificate (normal for Proxmox)")
                logger.error("2. Set ssl_verify=False in configuration")
            elif "401" in str(e) or "authentication" in str(e).lower():
                logger.error("Authentication error - check credentials:")
                logger.error(f"1. Username: {self.user}")
                logger.error("2. Password: [hidden]")
                logger.error("3. Realm: usually 'pam' or 'pve'")
            
            self.is_connected = False
            self._last_auth_time = None
            return False
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status information"""
        if not self._ensure_connection():
            return {"error": "Not connected to Proxmox"}
        
        try:
            status = self.api.cluster.status.get()
            return {"cluster_status": status}
        except Exception as e:
            logger.error(f"Error getting cluster status: {e}")
            return {"error": str(e)}
    
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get list of Proxmox nodes"""
        if not self._ensure_connection():
            return []
        
        try:
            nodes = self.api.nodes.get()
            return nodes
        except Exception as e:
            logger.error(f"Error getting nodes: {e}")
            return []
    
    def get_node_status(self, node: str) -> Dict[str, Any]:
        """Get detailed status of a specific node"""
        if not self._ensure_connection():
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
