"""
Secure configuration module for MoxNAS
Handles secure retrieval of configuration values from Django settings
"""
from django.conf import settings
from typing import Dict, Any, Optional


class SecureConfig:
    """
    Centralized configuration management for secure settings
    """
    
    @staticmethod
    def get_proxmox_config() -> Dict[str, Any]:
        """
        Get Proxmox configuration from Django settings
        
        Returns:
            Dict containing Proxmox configuration
        """
        return {
            'host': getattr(settings, 'PROXMOX_HOST', ''),
            'port': getattr(settings, 'PROXMOX_PORT', 8006),
            'username': getattr(settings, 'PROXMOX_USERNAME', 'root'),
            'password': getattr(settings, 'PROXMOX_PASSWORD', ''),
            'realm': getattr(settings, 'PROXMOX_REALM', 'pam'),
            'ssl_verify': getattr(settings, 'PROXMOX_SSL_VERIFY', False),
        }
    
    @staticmethod
    def get_network_config() -> Dict[str, Any]:
        """
        Get network configuration from Django settings
        
        Returns:
            Dict containing network configuration
        """
        return {
            'timeout': getattr(settings, 'NETWORK_TIMEOUT', 30),
            'retries': getattr(settings, 'NETWORK_RETRIES', 3),
            'ssl_verify': getattr(settings, 'PROXMOX_SSL_VERIFY', False),
        }
    
    @staticmethod
    def get_storage_config() -> Dict[str, Any]:
        """
        Get storage configuration from Django settings
        
        Returns:
            Dict containing storage configuration
        """
        return {
            'default_storage': getattr(settings, 'DEFAULT_STORAGE', 'local'),
            'storage_path': getattr(settings, 'STORAGE_PATH', '/var/lib/moxnas'),
            'max_storage_size': getattr(settings, 'MAX_STORAGE_SIZE', 1024 * 1024 * 1024),  # 1GB default
        }
    
    @staticmethod
    def get_config_value(key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return getattr(settings, key, default)
    
    @staticmethod
    def is_proxmox_configured() -> bool:
        """
        Check if Proxmox is properly configured
        
        Returns:
            True if Proxmox configuration is valid
        """
        config = SecureConfig.get_proxmox_config()
        return bool(config['host'] and config['username'] and config['password'])