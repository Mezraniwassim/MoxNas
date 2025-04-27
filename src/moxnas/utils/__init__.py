"""Utility functions for MoxNAS.

This module provides common utility functions and helpers for system operations,
logging, and security checks.
"""

# MoxNAS Project Instructions
# 1. Container-friendly implementations under LXC constraints
# 2. Prefer mount point-based storage over ZFS
# 3. Maintain compatibility with SMB, NFS, FTP, iSCSI
# 4. Integrate with Proxmox VE 8.4 requirements
# 5. Follow Python best practices and type hints
# 6. Include error handling for system-level operations
# 7. Ensure security best practices for network services
# 8. Add appropriate logging for system operations

import os
import pwd
import grp
from typing import Optional, Tuple, List
import logging
from pathlib import Path
import subprocess
import socket
import hashlib
import secrets

logger = logging.getLogger(__name__)

def setup_logging(log_path: Optional[Path] = None, debug: bool = False) -> None:
    """Configure logging for MoxNAS.
    
    Args:
        log_path: Optional path for log file
        debug: Enable debug logging if True
    """
    root = logging.getLogger()
    level = logging.DEBUG if debug else logging.INFO
    root.setLevel(level)
    # Remove all existing handlers
    for handler in list(root.handlers):
        root.removeHandler(handler)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # File handler
    if log_path:
        file_handler = logging.FileHandler(str(log_path))
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

def check_root_privileges() -> bool:
    """Check if current process has root privileges.
    
    Returns:
        bool: True if running as root
    """
    return os.geteuid() == 0

def secure_path_join(*paths: str) -> Path:
    """Securely join paths, avoiding path traversal.
    
    Args:
        *paths: Path components to join
        
    Returns:
        Path: Safely joined path
        
    Raises:
        ValueError: If path traversal is attempted
    """
    result = Path(os.path.join(*paths)).resolve()
    
    if not str(result).startswith(os.path.abspath(paths[0])):
        raise ValueError("Path traversal detected")
        
    return result

def generate_secure_token(length: int = 32) -> str:
    """Generate a secure random token.
    
    Args:
        length: Length of token in bytes
        
    Returns:
        str: Secure random token as hex string
    """
    return secrets.token_hex(length)

def hash_password(password: str) -> Tuple[str, str]:
    """Securely hash a password with salt.
    
    Args:
        password: Password to hash
        
    Returns:
        Tuple[str, str]: (salt, hash) pair
    """
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256()
    hash_obj.update(salt.encode())
    hash_obj.update(password.encode())
    return salt, hash_obj.hexdigest()

def verify_hash(password: str, salt: str, hash_value: str) -> bool:
    """Verify a password against its hash.
    
    Args:
        password: Password to verify
        salt: Salt used in hash
        hash_value: Expected hash value
        
    Returns:
        bool: True if password matches
    """
    hash_obj = hashlib.sha256()
    hash_obj.update(salt.encode())
    hash_obj.update(password.encode())
    return hash_obj.hexdigest() == hash_value

def check_port_available(port: int, address: str = '127.0.0.1') -> bool:
    """Check if a network port is available.
    
    Args:
        port: Port number to check
        address: IP address to check (default: localhost)
        
    Returns:
        bool: True if port is available
    """
    # Ports below 1024 require root privileges
    if port < 1024 and os.geteuid() != 0:
        logger.warning(f"Insufficient privileges to check port {port}")
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((address, port))
            return result != 0
    except Exception as e:
        logger.error(f"Error checking port {port}: {e}")
        return False