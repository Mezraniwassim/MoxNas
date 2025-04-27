#!/usr/bin/env python3
"""Example script for testing Proxmox VE integration."""

import logging
import sys
import shutil
from pathlib import Path
from moxnas.proxmox import ProxmoxManager
from moxnas.proxmox.templates import get_debian_container_config, get_truenas_container_config
from moxnas.utils import setup_logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def copy_hook_script(proxmox_node: str, proxmox: ProxmoxManager) -> bool:
    """Copy the TrueNAS initialization script to Proxmox snippets."""
    script_path = Path(__file__).parent.parent / "src" / "moxnas" / "proxmox" / "scripts" / "truenas-init.sh"
    
    if not script_path.exists():
        logger.error(f"Hook script not found at {script_path}")
        return False
    
    try:
        # Make script executable
        script_path.chmod(0o755)
        
        # Copy script to Proxmox node using ssh
        result = proxmox.run_script_on_node(
            node=proxmox_node,
            script_path=script_path,
            remote_path="/var/lib/vz/snippets/truenas-init.sh"
        )
        
        return result
    except Exception as e:
        logger.error(f"Failed to copy hook script: {e}")
        return False

import pytest

@pytest.fixture
def proxmox_host():
    """Fixture providing the Proxmox host address."""
    return "172.16.135.128"  # You can override this in your pytest.ini or through CLI

@pytest.fixture
def mock_response(monkeypatch):
    """Mock requests.get for testing."""
    class MockResponse:
        def __init__(self):
            self.status_code = 200
            self.text = '{"data": {"version": "8.4.0"}}'

    def mock_get(*args, **kwargs):
        return MockResponse()

    import requests
    monkeypatch.setattr(requests, "get", mock_get)
    return MockResponse()

def check_proxmox_connection(host: str, port: int = 8006) -> bool:
    """Test basic connection to Proxmox server."""
    import requests
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    
    try:
        url = f"https://{host}:{port}/api2/json/version"
        logger.debug(f"Testing connection to {url}")
        response = requests.get(url, verify=False, timeout=5)
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response content: {response.text}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False

def test_proxmox_connection(proxmox_host, mock_response):
    """Test the connection to Proxmox server."""
    assert check_proxmox_connection(proxmox_host), "Failed to connect to Proxmox server"

def main():
    """Test Proxmox connection."""
    # Initialize ProxmoxManager with your credentials
    proxmox = ProxmoxManager(
        host="172.16.135.128",
        user="root@pam",
        port=8006,
        verify_ssl=False  # Set to True if you have valid SSL cert
    )
    
    # Connect to Proxmox
    if not proxmox.connect("wc305ekb"):
        logger.error("Failed to connect to Proxmox")
        return
    
    # Get the list of available nodes
    nodes = proxmox.get_node_list()
    if not nodes:
        logger.error("No nodes found")
        return
    
    node = nodes[0]['node']
    logger.info(f"Using node: {node}")
    
    # List existing containers
    containers = proxmox.get_containers(node)
    logger.info(f"Existing containers: {containers}")
    
    # Create a new TrueNAS container
    vmid = 200  # You can change this ID
    config = get_truenas_container_config(
        hostname="truenas-test",
        memory=4096,
        cores=2,
        rootfs_size="32G",
        ipv4="dhcp",
        vmid=vmid  # ensure proper rootfs LV name
    )
    
    if proxmox.create_container(node, vmid, config):
        logger.info(f"Created container {vmid}")
        
        # Start the container
        if proxmox.start_container(node, vmid):
            logger.info(f"Started container {vmid}")
        else:
            logger.error(f"Failed to start container {vmid}")
    else:
        logger.error("Failed to create container")

if __name__ == "__main__":
    main()