#!/usr/bin/env python3
"""Example script for creating a base LXC container for TrueNAS Scale on Proxmox."""

import logging
from pathlib import Path
from moxnas.proxmox import ProxmoxManager
from moxnas.proxmox.templates import get_debian_container_config
from moxnas.utils import setup_logging

def main() -> None:
    # Set up logging
    setup_logging(debug=True)
    logger = logging.getLogger(__name__)

    # Proxmox connection details
    proxmox = ProxmoxManager(
        host="172.16.135.128",  # Your Proxmox host
        user="root@pam",
        port=8006,
        verify_ssl=False
    )

    # Connect to Proxmox
    if not proxmox.connect("wc305ekb"):  # Your password
        logger.error("Failed to connect to Proxmox")
        return

    # Get first available node
    nodes = proxmox.get_node_list()
    if not nodes:
        logger.error("No Proxmox nodes found")
        return
    node = nodes[0]['node']
    logger.info(f"Using Proxmox node: {node}")

    # Container configuration
    vmid = 201  # You can change this ID
    config = get_debian_container_config(
        vmid=vmid,
        hostname="truenas-base",
        memory=4096,
        cores=2,
        disk_size="32G",
        storage_pool="local-lvm",  # Use local-lvm for container storage
        network_bridge="vmbr0"
    )

    # Create container on Proxmox
    logger.info(f"Creating container {vmid}")
    if not proxmox.create_container(node, vmid, config):
        logger.error("Failed to create container")
        return

    # Start container
    logger.info("Starting container...")
    if not proxmox.start_container(node, vmid):
        logger.error("Failed to start container")
        return

    logger.info(f"Container {vmid} is running on node {node}")

if __name__ == "__main__":
    main()