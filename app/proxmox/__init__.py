"""Proxmox integration module for MoxNAS"""

from .integration import (
    ProxmoxCredentials,
    StorageDefinition,
    ProxmoxAPIClient,
    ProxmoxStorageIntegration,
    ProxmoxBackupIntegration,
    ProxmoxClusterIntegration,
    MoxNASProxmoxManager,
    initialize_proxmox_integration,
    get_proxmox_manager,
    ProxmoxResourceType,
    StorageType,
)

__all__ = [
    "ProxmoxCredentials",
    "StorageDefinition",
    "ProxmoxAPIClient",
    "ProxmoxStorageIntegration",
    "ProxmoxBackupIntegration",
    "ProxmoxClusterIntegration",
    "MoxNASProxmoxManager",
    "initialize_proxmox_integration",
    "get_proxmox_manager",
    "ProxmoxResourceType",
    "StorageType",
]
