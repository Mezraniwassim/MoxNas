#!/usr/bin/env python3
"""
Secure configuration utility for MoxNAS
Loads environment variables from .env file for use in scripts and tests
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class SecureConfig:
    """Secure configuration manager using environment variables"""
    
    @staticmethod
    def get_proxmox_config():
        """Get Proxmox connection configuration from environment variables"""
        return {
            'host': os.getenv('PROXMOX_HOST', ''),
            'user': os.getenv('PROXMOX_USER', 'root@pam'),
            'password': os.getenv('PROXMOX_PASSWORD', ''),
            'port': int(os.getenv('PROXMOX_PORT', '8006')),
            'verify_ssl': os.getenv('PROXMOX_VERIFY_SSL', 'False').lower() == 'true'
        }
    
    @staticmethod
    def get_container_config():
        """Get container configuration from environment variables"""
        return {
            'root_password': os.getenv('CONTAINER_ROOT_PASSWORD', ''),
            'default_password': os.getenv('CONTAINER_DEFAULT_PASSWORD', ''),
        }
    
    @staticmethod
    def get_network_config():
        """Get network configuration from environment variables"""
        return {
            'interface': os.getenv('NETWORK_INTERFACE', 'eth0'),
            'bridge_interface': os.getenv('BRIDGE_INTERFACE', 'vmbr0'),
        }
    
    @staticmethod
    def get_storage_config():
        """Get storage configuration from environment variables"""
        return {
            'pool': os.getenv('STORAGE_POOL', 'local-lvm'),
            'iso_storage': os.getenv('ISO_STORAGE', 'local'),
            'backup_storage': os.getenv('BACKUP_STORAGE', 'local'),
        }
    
    @staticmethod
    def validate_required_vars():
        """Validate that required environment variables are set"""
        required_vars = [
            'PROXMOX_HOST',
            'PROXMOX_PASSWORD',
            'CONTAINER_ROOT_PASSWORD',
            'SECRET_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True

# Convenience functions for backward compatibility
def get_proxmox_connection_params():
    """Get Proxmox connection parameters (backward compatibility)"""
    return SecureConfig.get_proxmox_config()

def get_container_password():
    """Get container password (backward compatibility)"""
    return os.getenv('CONTAINER_DEFAULT_PASSWORD', '')

if __name__ == "__main__":
    # Test configuration loading
    try:
        config = SecureConfig()
        print("✓ Configuration loaded successfully")
        
        proxmox_config = config.get_proxmox_config()
        if proxmox_config['host']:
            print(f"✓ Proxmox host configured: {proxmox_config['host']}")
        else:
            print("⚠ Proxmox host not configured")
            
        if proxmox_config['password']:
            print("✓ Proxmox password configured")
        else:
            print("⚠ Proxmox password not configured")
            
        print("\nTo configure missing values, edit the .env file in the project root.")
        
    except Exception as e:
        print(f"✗ Configuration error: {e}")
