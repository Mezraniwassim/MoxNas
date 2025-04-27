from typing import Optional, Dict, List, Any, Tuple, Union
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip loading .env
    def load_dotenv(*args, **kwargs):
        pass

from pathlib import Path
import json
import os
import proxmoxer
from proxmoxer import ProxmoxAPI
from ..core.exceptions import ProxmoxConnectionError
import logging

logger = logging.getLogger(__name__)

# Constants for template management
DEBIAN_TEMPLATE_URL = "https://download.proxmox.com/images/system/debian-12-standard_12.7-1_amd64.tar.zst"
DEBIAN_TEMPLATE_CHECKSUM = "3df11179daf9c82ab85c0a6cddf93692ec908bc353ba5386020b58f66c45ba6f"

class ContainerError(Exception):
    """Custom exception for container-related errors"""
    pass

class ProxmoxManager:
    def __init__(
        self,
        host: str,
        user: str = "root@pam",
        port: int = 8006,
        verify_ssl: bool = True,
        config_path: Optional[Path] = None
    ):
        # Initialize defaults then override from config if present
        self.host = host
        self.user = user  # Proxmox login user
        self.port = port
        self.verify_ssl = verify_ssl
        self.proxmox = None
        self.is_connected = False
        # Persisted config: load only if config_path explicitly provided
        self.config_path = config_path
        if self.config_path:
            loaded_config = self._load_config()
        else:
            loaded_config = {}
        # Load default password from environment or fallback to hardcoded
        default_config = {"password": os.getenv("MOXNAS_PROXMOX_PASSWORD", "wc305ekb")}
        # Use persisted config directly if available, else use default
        if loaded_config:
            self.config = loaded_config
        else:
            self.config = default_config
        # Override init args with persisted config values if available
        self.user = self.config.get("user", self.user)
        self.port = self.config.get("port", self.port)
        self.verify_ssl = self.config.get("verify_ssl", self.verify_ssl)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file if exists."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"Failed to load config: {str(e)}")
            return {}

    def _save_config(self) -> bool:
        """Save configuration to file."""
        try:
            # Create parent directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f)
            return True
        except Exception as e:
            logger.warning(f"Failed to save config: {str(e)}")
            return False

    def connect(
        self,
        user: Optional[str] = None,
        password: Optional[str] = None,
        token_name: Optional[str] = None,
        token_value: Optional[str] = None
    ) -> bool:
        """Establish connection to Proxmox server with password or API token."""
        try:
            # Determine authentication parameters based on provided credentials
            if token_name and token_value:
                # Use API token authentication
                auth_user = user if user is not None else self.user
                kwargs = {
                    "user": auth_user,
                    "token_name": token_name,
                    "token_value": token_value,
                    "verify_ssl": self.verify_ssl,
                    "port": self.port,
                }
            elif password is not None:
                # Use explicit password authentication
                auth_user = user if user is not None else self.user
                kwargs = {
                    "user": auth_user,
                    "password": password,
                    "verify_ssl": self.verify_ssl,
                    "port": self.port,
                }
            else:
                # No credentials provided: use persisted config
                auth_user = self.user
                auth_password = self.config.get("password")
                if not auth_password:
                    raise ValueError("Password must be provided for authentication")
                kwargs = {
                    "user": auth_user,
                    "password": auth_password,
                    "verify_ssl": self.verify_ssl,
                    "port": self.port,
                }
            # Create connection with positional host argument
            self.proxmox = ProxmoxAPI(self.host, **kwargs)
            
            # Test connection
            self.proxmox.version.get()
            self.is_connected = True
            logger.info(f"Successfully connected to Proxmox VE at {self.host}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox: {str(e)}")
            self.proxmox = None
            self.is_connected = False
            return False

    def get_node_list(self) -> List[Dict[str, Any]]:
        """Get list of Proxmox nodes."""
        try:
            if not self.proxmox:
                return []
            return self.proxmox.nodes.get()
        except Exception as e:
            logger.error(f"Failed to get node list: {str(e)}")
            return []

    def get_node_status(self, node: str) -> Any:
        """Get status for a specific node."""
        try:
            if not self.proxmox:
                return {}
            return self.proxmox.nodes(node).status.get()
        except Exception as e:
            logger.error(f"Failed to get node status: {str(e)}")
            return {}

    def get_containers(self, node: str) -> List[Dict[str, Any]]:
        """Get list of LXC containers on a specific node."""
        try:
            if not self.proxmox:
                return []
            return self.proxmox.nodes(node).lxc.get()
        except Exception as e:
            logger.error(f"Failed to get containers: {str(e)}")
            return []

    def get_storage_list(self, node: str) -> List[Dict[str, Any]]:
        """Get list of storage options for a node."""
        try:
            if not self.proxmox:
                return []
            return self.proxmox.nodes(node).storage.get()
        except Exception as e:
            logger.error(f"Failed to get storage list: {str(e)}")
            return []

    def get_container_config(self, node: str, vmid: int) -> Dict[str, Any]:
        """Get configuration for a specific container."""
        try:
            if not self.proxmox:
                return {}
            return self.proxmox.nodes(node).lxc(vmid).config.get()
        except Exception as e:
            logger.error(f"Failed to get container config: {str(e)}")
            return {}

    def create_container(
        self, 
        node: str,
        vmid: int,
        config: Dict[str, Any]
    ) -> bool:
        """Create a new LXC container with provided configuration."""
        try:
            if not self.proxmox:
                return False
            self.proxmox.nodes(node).lxc.create(vmid=vmid, **config)
            logger.info(f"Created container {vmid} on node {node}")
            return True
        except Exception as e:
            logger.error(f"Failed to create container: {str(e)}")
            return False

    def delete_container(self, node: str, vmid: int) -> bool:
        """Delete an LXC container."""
        try:
            if not self.proxmox:
                return False
            self.proxmox.nodes(node).lxc(vmid).delete()
            logger.info(f"Deleted container {vmid} on node {node}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete container: {str(e)}")
            return False

    def start_container(self, node: str, vmid: int) -> bool:
        """Start an LXC container."""
        try:
            if not self.proxmox:
                return False
            self.proxmox.nodes(node).lxc(vmid).status.start.post()
            logger.info(f"Started container {vmid} on node {node}")
            return True
        except Exception as e:
            logger.error(f"Failed to start container: {str(e)}")
            return False

    def stop_container(self, node: str, vmid: int) -> bool:
        """Stop an LXC container."""
        try:
            if not self.proxmox:
                return False
            self.proxmox.nodes(node).lxc(vmid).status.stop.post()
            logger.info(f"Stopped container {vmid} on node {node}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop container: {str(e)}")
            return False
            
    def verify_template(self, node: str, template_path: str) -> Tuple[bool, str]:
        """Verify if a template exists on a node.
        
        Args:
            node: Node name
            template_path: Template path (e.g. 'local:vztmpl/truenas-scale-24.10.2.1.tar.gz')
            
        Returns:
            Tuple of (exists, message)
        """
        try:
            if not self.proxmox:
                return False, "Not connected to Proxmox"
                
            # Parse storage from template path (format: storage:path/to/template)
            if ":" not in template_path:
                return False, "Invalid template path format, expected 'storage:path'"
                
            storage = template_path.split(":")[0]
            
            # Get templates from storage
            templates = self.proxmox.nodes(node).storage(storage).content.get()
            
            # Check if template exists
            for template in templates:
                if template.get('volid') == template_path:
                    return True, f"Template '{template_path}' found"
                    
            return False, f"Template '{template_path}' not found"
        except Exception as e:
            return False, f"Error verifying template: {str(e)}"
            
    def list_templates(self, node: str) -> List[Dict[str, Any]]:
        """List available templates on a node."""
        try:
            if not self.proxmox:
                return []
            
            templates = []
            
            # Get all storage
            storages = self.get_storage_list(node)
            
            # For each storage, get templates
            for storage in storages:
                storage_id = storage.get('storage')
                try:
                    templates = self.proxmox.nodes(node).storage(storage_id).content.get()
                    # Filter for templates only
                    templates = [t for t in templates if t.get('volid', '').endswith('.tar.gz') or t.get('volid', '').endswith('.tar.zst')]
                    return templates
                except Exception:
                    # Skip storages that don't support content listing
                    pass
                    
            return templates
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []

    def download_template(self, node: str, template_url: str, storage: str = "local") -> bool:
        """Download a container template to Proxmox node."""
        try:
            if not self.proxmox:
                return False

            # Start template download
            filename = template_url.split('/')[-1]
            data = {
                "storage": storage,
                "content": "vztmpl",
                "filename": filename,
                "url": template_url,
                "checksum": f"sha256:{DEBIAN_TEMPLATE_CHECKSUM}",
                "verify-checksum": "yes"
            }
            
            logger.info(f"Downloading template {filename} to {storage}")
            result = self.proxmox.nodes(node).storage(storage).download.create(**data)
            
            if isinstance(result, dict) and result.get('data'):
                logger.info(f"Template download started: {result['data']}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to download template: {e}")
            return False

    def ensure_template_exists(self, node: str, template_name: str = "debian-12-standard_12.7-1_amd64.tar.zst",
                             storage: str = "local") -> bool:
        """Ensure template exists, download if needed."""
        try:
            if not self.proxmox:
                return False

            templates = self.list_templates(node)
            template_path = f"{storage}:vztmpl/{template_name}"
            
            # Check if template exists
            exists = any(t.get('volid') == template_path for t in templates)
            if exists:
                logger.info(f"Template {template_name} already exists")
                return True
                
            # Download template if not found
            logger.info(f"Template {template_name} not found, downloading...")
            return self.download_template(node, DEBIAN_TEMPLATE_URL, storage)
            
        except Exception as e:
            logger.error(f"Failed to ensure template exists: {e}")
            return False

    def setup_truenas_storage(
        self,
        node: str,
        vmid: int,
        storage_configs: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """Configure storage for a TrueNAS container.
        
        Args:
            node: Node name
            vmid: VM ID of the container
            storage_configs: List of storage configurations
                Example: [
                    {
                        'type': 'disk',  # or 'directory'
                        'source': '/dev/sdb',  # for disk or path for directory
                        'target': '/mnt/tank',  # mount point inside container
                    },
                    ...
                ]
                
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.proxmox:
                return False, "Not connected to Proxmox"
            
            # Get existing container config
            existing_config = self.get_container_config(node, vmid)
            if not existing_config:
                return False, f"Container {vmid} not found"
            
            # Process each storage config
            updates = {}
            for idx, storage in enumerate(storage_configs):
                storage_type = storage.get('type', 'directory')
                source = storage.get('source')
                target = storage.get('target')
                
                if not source or not target:
                    continue
                
                # Find next available mp index
                mp_index = 0
                while f'mp{mp_index}' in existing_config:
                    mp_index += 1
                
                if storage_type == 'disk':
                    # Add disk device (requires privileged container)
                    updates[f'mp{mp_index}'] = f"dev={source},mp={target},backup=0"
                else:
                    # Add directory bind mount
                    updates[f'mp{mp_index}'] = f"bind={source},{target}"
            
            # Apply updates if any
            if updates:
                self.proxmox.nodes(node).lxc(vmid).config.put(**updates)
                logger.info(f"Added {len(updates)} storage mounts to container {vmid}")
                return True, f"Storage configured with {len(updates)} mounts"
            
            return False, "No valid storage configurations provided"
            
        except Exception as e:
            error_msg = f"Failed to configure storage: {str(e)}"
            logger.error(error_msg)
            return False, error_msg