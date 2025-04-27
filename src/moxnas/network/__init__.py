"""Network service configuration for MoxNAS.

This module handles network service configuration for TrueNAS Scale services
(SMB, NFS, FTP, iSCSI) with a focus on security and container compatibility.
"""

from typing import Optional, Dict, List
import logging
import subprocess
from pathlib import Path
import socket
import netifaces
import ipaddress

logger = logging.getLogger(__name__)

class ServiceConfig:
    """Base class for network service configuration."""
    
    def __init__(self, service_name: str, config_path: Path):
        """Initialize service configuration.
        
        Args:
            service_name: Name of the service (e.g., 'smb', 'nfs')
            config_path: Path to service configuration directory
        """
        self.service_name = service_name
        self.config_path = config_path
        self.active = False
        
    def validate_port(self, port: int) -> bool:
        """Validate if a port number is valid and available.
        
        Args:
            port: Port number to validate
            
        Returns:
            bool: True if port is valid and available
        """
        if not 1 <= port <= 65535:
            return False
            
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result != 0
        except Exception as e:
            logger.error(f"Port validation error: {e}")
            return False
            
    def validate_network(self, network: str) -> bool:
        """Validate network address/range.
        
        Args:
            network: Network address in CIDR notation
            
        Returns:
            bool: True if network is valid
        """
        try:
            ipaddress.ip_network(network)
            return True
        except ValueError:
            return False

class NetworkManager:
    """Manages network service configuration and operations."""
    
    def __init__(self, container_path: Path):
        """Initialize network manager.
        
        Args:
            container_path: Path to container root
        """
        self.container_path = container_path
        self.services: Dict[str, ServiceConfig] = {}
        self._discover_interfaces()
        
    def _discover_interfaces(self) -> None:
        """Discover available network interfaces."""
        try:
            self.interfaces = netifaces.interfaces()
            self.addresses = {
                iface: netifaces.ifaddresses(iface)
                for iface in self.interfaces
                if netifaces.AF_INET in netifaces.ifaddresses(iface)
            }
        except Exception as e:
            logger.error(f"Error discovering network interfaces: {e}")
            self.interfaces = []
            self.addresses = {}
            
    def get_interface_ips(self, interface: str) -> List[str]:
        """Get IP addresses for a network interface.
        
        Args:
            interface: Name of network interface
            
        Returns:
            List[str]: List of IP addresses assigned to interface
        """
        if interface not in self.addresses:
            return []
            
        return [
            addr['addr']
            for addr in self.addresses[interface].get(netifaces.AF_INET, [])
        ]
        
    def validate_service_config(self, service: str, config: Dict) -> bool:
        """Validate service configuration.
        
        Args:
            service: Service name
            config: Service configuration dictionary
            
        Returns:
            bool: True if configuration is valid
        """
        if service not in self.services:
            logger.error(f"Unknown service: {service}")
            return False
            
        return self.services[service].validate_configuration(config)