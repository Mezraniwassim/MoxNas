"""
Security utilities for MoxNAS service management
"""

import os
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class PathValidator:
    """Path validation and sanitization utilities"""
    
    # Allowed base directories for file operations
    ALLOWED_BASES = [
        '/mnt/storage',
        '/opt/moxnas/storage', 
        '/home',
        '/tmp/moxnas'
    ]
    
    @classmethod
    def sanitize_path(cls, input_path: str) -> str:
        """
        Sanitize and validate file paths
        
        Args:
            input_path: Raw path input
            
        Returns:
            Sanitized absolute path
            
        Raises:
            ValueError: If path is invalid or unsafe
        """
        if not input_path or not isinstance(input_path, str):
            raise ValueError("Path cannot be empty or non-string")
        
        # Remove any path traversal attempts
        clean_path = re.sub(r'\.\.+', '', input_path.strip())
        clean_path = os.path.normpath(clean_path)
        
        # Ensure absolute path
        if not clean_path.startswith('/'):
            clean_path = '/' + clean_path
        
        # Additional security checks
        if any(dangerous in clean_path for dangerous in ['..', '~', '$']):
            raise ValueError(f"Path contains dangerous characters: {clean_path}")
        
        return os.path.abspath(clean_path)
    
    @classmethod
    def validate_path(cls, path: str, allowed_bases: Optional[List[str]] = None) -> str:
        """
        Validate path is within allowed directories
        
        Args:
            path: Path to validate
            allowed_bases: Optional list of allowed base directories
            
        Returns:
            Validated path or fallback to default
        """
        if allowed_bases is None:
            allowed_bases = cls.ALLOWED_BASES
        
        sanitized_path = cls.sanitize_path(path)
        
        # Check if path is within allowed directories
        if not any(sanitized_path.startswith(base) for base in allowed_bases):
            logger.warning(f"Path {sanitized_path} not in allowed directories, using /mnt/storage")
            return '/mnt/storage'
        
        return sanitized_path


class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_service_name(name: str) -> bool:
        """Validate service names"""
        if not name or not isinstance(name, str):
            return False
        
        # Only allow alphanumeric and common service characters
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, name)) and len(name) <= 50
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate usernames"""
        if not username or not isinstance(username, str):
            return False
        
        # Standard username validation
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, username)) and 3 <= len(username) <= 32
    
    @staticmethod
    def validate_share_name(share_name: str) -> bool:
        """Validate share names"""
        if not share_name or not isinstance(share_name, str):
            return False
        
        # Share names should not contain special characters
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, share_name)) and len(share_name) <= 255
    
    @staticmethod
    def sanitize_config_value(value: str) -> str:
        """Sanitize configuration values"""
        if not isinstance(value, str):
            return str(value)
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[;&|`$(){}[\]\\]', '', value)
        return sanitized.strip()


class CommandValidator:
    """Validate subprocess commands for security"""
    
    ALLOWED_COMMANDS = {
        'systemctl', 'useradd', 'userdel', 'usermod', 'groupadd', 'groupdel',
        'chown', 'chmod', 'mkdir', 'chpasswd', 'passwd', 'testparm',
        'exportfs', 'setfacl', 'getfacl'
    }
    
    @classmethod
    def validate_command(cls, command_list: List[str]) -> bool:
        """
        Validate that subprocess commands are safe
        
        Args:
            command_list: List of command arguments
            
        Returns:
            True if command is safe
        """
        if not command_list or not isinstance(command_list, list):
            return False
        
        # Check if base command is allowed
        base_command = os.path.basename(command_list[0])
        if base_command not in cls.ALLOWED_COMMANDS:
            logger.warning(f"Command not allowed: {base_command}")
            return False
        
        # Check for shell injection attempts
        for arg in command_list:
            if any(char in str(arg) for char in ['&', '|', ';', '`', '$', '(', ')']):
                logger.warning(f"Dangerous characters in command argument: {arg}")
                return False
        
        return True
    
    @classmethod
    def sanitize_command_args(cls, args: List[str]) -> List[str]:
        """Sanitize command arguments"""
        sanitized = []
        for arg in args:
            # Remove potentially dangerous characters but preserve necessary ones
            clean_arg = re.sub(r'[;&|`$()]', '', str(arg))
            sanitized.append(clean_arg)
        return sanitized