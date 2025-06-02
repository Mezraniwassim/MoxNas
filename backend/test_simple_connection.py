#!/usr/bin/env python3
"""
Simple Proxmox connection test
"""

import sys
import socket
from proxmoxer import ProxmoxAPI
from secure_config import SecureConfig

def test_network_connection():
    """Test basic network connectivity to Proxmox host"""
    config = SecureConfig.get_proxmox_config()
    
    if not config['host']:
        print("❌ Proxmox host not configured in .env file")
        return False
    
    host = config['host']
    port = config['port']
    
    print(f"Testing network connectivity to {host}:{port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)  # 10 second timeout
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print("✅ Network connection successful")
            return True
        else:
            print(f"❌ Network connection failed with error code: {result}")
            return False
    except Exception as e:
        print(f"❌ Network connection error: {e}")
        return False

def test_api_connection():
    """Test Proxmox API connection"""
    config = SecureConfig.get_proxmox_config()
    
    if not config['host'] or not config['password']:
        print("❌ Proxmox connection parameters not configured in .env file")
        return False
    
    print(f"\nTesting Proxmox API connection...")
    print(f"Host: {config['host']}:{config['port']}")
    print(f"User: {config['user']}")
    
    try:
        # Test with minimal parameters
        api = ProxmoxAPI(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            verify_ssl=config['verify_ssl'],
            port=config['port']
        )
        
        print("API object created successfully")
        
        # Test API call with timeout
        print("Testing API call...")
        version = api.version.get()
        print(f"✅ Proxmox version: {version}")
        return True
        
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    print("=== Proxmox Connection Test ===")
    
    # Test network connectivity first
    if not test_network_connection():
        print("\n❌ Network connectivity test failed. Check if Proxmox host is reachable.")
        sys.exit(1)
    
    # Test API connection
    if not test_api_connection():
        print("\n❌ API connection test failed.")
        sys.exit(1)
    
    print("\n✅ All tests passed!")
