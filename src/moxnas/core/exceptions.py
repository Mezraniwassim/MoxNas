class MoxNASError(Exception):
    """Base exception for MoxNAS errors"""
    pass

class ProxmoxConnectionError(MoxNASError):
    """Raised when Proxmox connection fails"""
    pass

class ContainerError(MoxNASError):
    """Raised when container operations fail"""
    pass

class StorageError(MoxNASError):
    """Raised when storage operations fail"""
    pass

class NetworkError(MoxNASError):
    """Raised when network operations fail"""
    pass