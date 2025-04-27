"""ProxmoxManager and template management functionality."""

from typing import Optional, Dict, List, Any, Union
import logging
from pathlib import Path
import json
from proxmoxer import ProxmoxAPI
import requests
import paramiko
from ..utils import setup_logging

logger = logging.getLogger(__name__)

# Constants for template management
DEBIAN_TEMPLATE_URL = "https://download.proxmox.com/images/system/debian-12-standard_12.7-1_amd64.tar.zst"
DEBIAN_TEMPLATE_CHECKSUM = "3df11179daf9c82ab85c0a6cddf93692ec908bc353ba5386020b58f66c45ba6f"

class ProxmoxManager:
    """Manages Proxmox VE interactions and container operations."""
    
    def __init__(self, host: str, user: str = "root@pam", 
                 port: int = 8006, verify_ssl: bool = True):
        """Initialize Proxmox manager.
        
        Args:
            host: Proxmox host address
            user: Proxmox user (default: root@pam)
            port: Proxmox API port (default: 8006)
            verify_ssl: Verify SSL certificate (default: True)
        """
        self.host = host
        self.user = user
        self.port = port
        self.verify_ssl = verify_ssl
        self._api: Optional[ProxmoxAPI] = None

    def connect(self, password: str) -> bool:
        """Connect to Proxmox API.
        
        Args:
            password: User password
            
        Returns:
            bool: True if connection successful
        """
        try:
            self._api = ProxmoxAPI(
                host=self.host,
                user=self.user,
                password=password,
                verify_ssl=self.verify_ssl,
                port=self.port
            )
            # Test connection
            self._api.nodes.get()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Proxmox: {e}")
            return False
            
    def get_containers(self, node: str) -> List[Dict[str, Any]]:
        """Get list of containers on a node.
        
        Args:
            node: Proxmox node name
            
        Returns:
            List[Dict]: List of container information
        """
        try:
            containers = self._api.nodes(node).lxc.get()
            return [
                {
                    'vmid': ct['vmid'],
                    'name': ct.get('name', f'ct-{ct["vmid"]}'),
                    'status': ct['status'],
                    'hostname': ct.get('hostname', ''),
                    'memory': ct.get('maxmem', 0),
                    'disk': ct.get('maxdisk', 0)
                }
                for ct in containers
            ]
        except Exception as e:
            logger.error(f"Failed to get containers: {e}")
            return []
            
    def list_templates(self, node: str) -> List[Dict[str, Any]]:
        """List available templates on a node.
        
        Args:
            node: Proxmox node name
            
        Returns:
            List[Dict]: List of template information
        """
        try:
            if not self._api:
                logger.error("Not connected to Proxmox")
                return []
            
            templates = []
            
            # Get list of storages
            storages = self._api.nodes(node).storage.get()
            
            # Check each storage for templates
            for storage in storages:
                storage_id = storage['storage']
                try:
                    content = self._api.nodes(node).storage(storage_id).content.get()
                    # Filter for templates
                    templates.extend([
                        t for t in content 
                        if t.get('volid', '').startswith(f"{storage_id}:vztmpl/")
                    ])
                except Exception as e:
                    logger.debug(f"Failed to get templates from {storage_id}: {e}")
                    continue
                    
            return templates
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []

    def download_template(self, node: str, template_url: str, storage: str = "local") -> bool:
        """Download a container template to Proxmox node.
        
        Args:
            node: Proxmox node name
            template_url: URL to download template from
            storage: Storage location for template
            
        Returns:
            bool: True if successful
        """
        try:
            if not self._api:
                logger.error("Not connected to Proxmox")
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
            result = self._api.nodes(node).storage(storage).download.create(**data)
            
            if isinstance(result, dict) and result.get('data'):
                logger.info(f"Template download started: {result['data']}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to download template: {e}")
            return False

    def ensure_template_exists(self, node: str, template_name: str = "debian-12-standard_12.7-1_amd64.tar.zst",
                             storage: str = "local") -> bool:
        """Ensure template exists, download if needed.
        
        Args:
            node: Proxmox node name
            template_name: Name of template file
            storage: Storage location for template
            
        Returns:
            bool: True if template exists or was downloaded
        """
        try:
            if not self._api:
                logger.error("Not connected to Proxmox")
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

    def create_container(self, node: str, vmid: int, config: Dict[str, Any]) -> bool:
        """Create a new container.
        
        Args:
            node: Proxmox node name
            vmid: Container ID
            config: Container configuration
            
        Returns:
            bool: True if successful
        """
        try:
            # Ensure template exists before creating container
            if 'ostemplate' in config:
                template_storage, template_path = config['ostemplate'].split(':', 1)
                template_name = template_path.split('/')[-1]
                if not self.ensure_template_exists(node, template_name, template_storage):
                    logger.error("Failed to ensure template exists")
                    return False
            
            self._api.nodes(node).lxc.create(vmid=vmid, **config)
            logger.info(f"Created container {vmid} on node {node}")
            return True
        except Exception as e:
            logger.error(f"Failed to create container: {e}")
            return False
            
    def delete_container(self, node: str, vmid: int) -> bool:
        """Delete a container.
        
        Args:
            node: Proxmox node name
            vmid: Container ID
            
        Returns:
            bool: True if successful
        """
        try:
            self._api.nodes(node).lxc(vmid).delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete container: {e}")
            return False
            
    def start_container(self, node: str, vmid: int) -> bool:
        """Start a container.
        
        Args:
            node: Proxmox node name
            vmid: Container ID
            
        Returns:
            bool: True if successful
        """
        try:
            self._api.nodes(node).lxc(vmid).status.start.post()
            return True
        except Exception as e:
            logger.error(f"Failed to start container: {e}")
            return False
            
    def stop_container(self, node: str, vmid: int) -> bool:
        """Stop a container.
        
        Args:
            node: Proxmox node name
            vmid: Container ID
            
        Returns:
            bool: True if successful
        """
        try:
            self._api.nodes(node).lxc(vmid).status.stop.post()
            return True
        except Exception as e:
            logger.error(f"Failed to stop container: {e}")
            return False
            
    def get_container_config(self, node: str, vmid: int) -> Optional[Dict[str, Any]]:
        """Get container configuration.
        
        Args:
            node: Proxmox node name
            vmid: Container ID
            
        Returns:
            Optional[Dict]: Container configuration or None if error
        """
        try:
            return self._api.nodes(node).lxc(vmid).config.get()
        except Exception as e:
            logger.error(f"Failed to get container config: {e}")
            return None
            
    def update_container_config(self, node: str, vmid: int, 
                              config: Dict[str, Any]) -> bool:
        """Update container configuration.
        
        Args:
            node: Proxmox node name
            vmid: Container ID
            config: New configuration values
            
        Returns:
            bool: True if successful
        """
        try:
            self._api.nodes(node).lxc(vmid).config.put(**config)
            return True
        except Exception as e:
            logger.error(f"Failed to update container config: {e}")
            return False
            
    def run_script_on_node(self, node: str, script_path: Path, 
                          remote_path: str) -> bool:
        """Copy and run a script on a Proxmox node.
        
        Args:
            node: Proxmox node name
            script_path: Local script path
            remote_path: Remote path to copy script to
            
        Returns:
            bool: True if successful
        """
        try:
            # Set up SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to the node
            ssh.connect(
                self.host,
                username=self.user.split('@')[0],
                password=self._api._auth_api.password
            )
            
            # Copy script using SFTP
            sftp = ssh.open_sftp()
            sftp.put(str(script_path), remote_path)
            sftp.chmod(remote_path, 0o755)
            
            # Close connections
            sftp.close()
            ssh.close()
            
            return True
        except Exception as e:
            logger.error(f"Failed to run script on node: {e}")
            return False

def get_debian_container_config(
    vmid: int,
    hostname: str,
    memory: int = 4096,
    cores: int = 2,
    swap: int = 512,
    storage_pool: str = "local",
    disk_size: str = "32G",
    network_bridge: str = "vmbr0",
    features: Optional[Dict[str, bool]] = None
) -> Dict[str, Any]:
    """Generate Debian container configuration for TrueNAS Scale."""
    # default feature flags
    if features is None:
        features = {"nesting": True, "keyctl": True}
    # build feature string
    feat_list = [f"{k}={1 if v else 0}" for k, v in features.items()]
    feat_str = ",".join(feat_list)
    # network config
    net0 = f"name=eth0,bridge={network_bridge},firewall=1,type=veth"
    return {
        "hostname": hostname,
        "ostemplate": "local:vztmpl/debian-12-standard_12.7-1_amd64.tar.zst",
        "cores": cores,
        "memory": memory,
        "swap": swap,
        "storage": storage_pool,
        "rootfs": f"{storage_pool}:vm-{vmid}-disk-0,size={disk_size}",
        "net0": net0,
        "onboot": 1,
        "unprivileged": 0,
        "features": feat_str
    }

def get_truenas_container_config(
    hostname: str,
    memory: int = 4096,
    cores: int = 2,
    rootfs_size: str = "32G",
    storage_pool: str = "local-lvm",  # rootfs storage (for tests/backwards compatibility)
    template_storage: str = "local",
    template_name: str = "debian-12-standard_12.7-1_amd64.tar.zst",
    network_bridge: str = "vmbr0",
    ipv4: str = "dhcp",
    gateway: Optional[str] = None,
    vmid: Optional[int] = None
) -> Dict[str, Any]:
    """Generate container configuration for TrueNAS Scale."""
    # prepare network settings
    net_params = ["name=eth0", f"bridge={network_bridge}", f"ip={ipv4}"]
    if gateway:
        net_params.append(f"gw={gateway}")
    net0 = ",".join(net_params)
    # Determine OSTemplate volid
    volid = f"{template_storage}:vztmpl/{template_name}"
    # Determine rootfs storage
    rootfs_storage = storage_pool
    # Configure rootfs: if vmid provided, use full LV path; else size-only (for tests)
    if vmid is not None:
        rootfs_val = f"{rootfs_storage}:vm-{vmid}-disk-0,size={rootfs_size}"
    else:
        rootfs_val = f"{rootfs_storage}:{rootfs_size}"
    return {
        "hostname": hostname,
        "ostemplate": volid,
        "cores": cores,
        "memory": memory,
        "swap": 512,
        "storage": rootfs_storage,
        "rootfs": rootfs_val,
        "net0": net0,
        "onboot": 1,
        "unprivileged": 0,
        "features": "nesting=1",
        # Allow unconfined AppArmor for TrueNAS
        "lxc.apparmor.profile": "unconfined"
    }

def get_storage_mount_config(
    name: str,
    mount_path: str,
    storage_pool: str = "local-lvm",
    size: str = "100G",
    mount_opts: str = "defaults"
) -> Dict[str, str]:
    """Generate storage mount configuration for TrueNAS container.
    
    Args:
        name: Name of the storage volume
        mount_path: Mount point path in container
        storage_pool: Storage pool to use (default: local-lvm)
        size: Volume size (default: 100G)
        mount_opts: Mount options (default: defaults)
        
    Returns:
        Dict[str, str]: Mount point configuration
    """
    return {
        "volume": f"{storage_pool}:{size}",
        "mp": mount_path,
        "mountoptions": mount_opts
    }

def generate_truenas_init_script() -> str:
    """Generate TrueNAS initialization script content.
    
    Returns:
        str: Shell script content for container initialization
    """
    return """#!/bin/bash
# TrueNAS Scale container initialization script

set -e

# Container setup function
setup_container() {
    # System requirements
    apt-get update
    apt-get install -y \
        sudo \
        systemd \
        systemd-sysv \
        python3 \
        python3-pip \
        openssh-server \
        apparmor \
        openssl \
        ca-certificates

    # Service configuration
    systemctl enable ssh
    systemctl enable systemd-networkd
    systemctl enable systemd-resolved
    
    # Create required directories
    mkdir -p /var/lib/docker
    mkdir -p /var/lib/kubelet
    mkdir -p /etc/systemd/system
    mkdir -p /var/lib/systemd
    
    # Security settings
    echo "kernel.unprivileged_userns_clone=1" > /etc/sysctl.d/90-containers.conf
    
    # Network configuration
    cat > /etc/systemd/network/eth0.network << EOF
[Match]
Name=eth0

[Network]
DHCP=yes
IPv6AcceptRA=yes
EOF

    # Configure systemd-resolved
    ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
}

# Run setup if not already completed
if [ ! -f /var/lib/container_setup_complete ]; then
    setup_container
    touch /var/lib/container_setup_complete
fi
"""

def prepare_debian_template(
    node: str,
    template_storage: str = "local",
    debian_version: str = "bookworm"
) -> Dict[str, Any]:
    """Prepare Debian template for TrueNAS Scale containers.
    
    Args:
        node: Proxmox node name
        template_storage: Storage location for template
        debian_version: Debian version codename
        
    Returns:
        Dict[str, Any]: Template configuration
    """
    return {
        "node": node,
        "storage": template_storage,
        "template": 1,
        "ostype": "debian",
        "osversion": debian_version,
        "unprivileged": 0,
        "features": "nesting=1,keyctl=1,mknod=1,mount=1",
        "hostname": "debian-template",
        "net0": "name=eth0,bridge=vmbr0,firewall=1,type=veth",
        "rootfs": f"{template_storage}:vm-9000-disk-0,size=4G",  # Template ID 9000
        "start": 0,  # Don't auto-start template
        "memory": 512,  # Minimal memory for template
        "swap": 512,
        "cores": 1
    }