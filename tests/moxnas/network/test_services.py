"""Tests for NAS network service handlers."""

import pytest
from pathlib import Path
import os
from moxnas.network.services import (
    SMBService,
    NFSService,
    FTPService,
    iSCSIService
)

@pytest.fixture
def config_path(tmp_path):
    """Fixture providing a temporary configuration path."""
    return tmp_path / "config"

def test_smb_service_validation(config_path):
    """Test SMB service configuration validation."""
    service = SMBService(config_path)
    
    # Test valid configuration
    valid_config = {
        "workgroup": "WORKGROUP",
        "server_string": "MoxNAS Server",
        "shares": [
            {
                "name": "test_share",
                "path": "/mnt/test",
                "valid_users": ["user1", "user2"]
            }
        ]
    }
    assert service.validate_configuration(valid_config)
    
    # Test invalid configuration (missing required field)
    invalid_config = {
        "workgroup": "WORKGROUP",
        "shares": []
    }
    assert not service.validate_configuration(invalid_config)
    
    # Test invalid share configuration
    invalid_share_config = {
        "workgroup": "WORKGROUP",
        "server_string": "MoxNAS Server",
        "shares": [
            {
                "name": "test_share"
                # Missing path and valid_users
            }
        ]
    }
    assert not service.validate_configuration(invalid_share_config)

def test_nfs_service_validation(config_path):
    """Test NFS service configuration validation."""
    service = NFSService(config_path)
    
    # Test valid configuration
    valid_config = {
        "exports": [
            {
                "path": "/mnt/export",
                "clients": [
                    {
                        "network": "192.168.1.0/24",
                        "options": ["rw", "sync"]
                    }
                ]
            }
        ]
    }
    assert service.validate_configuration(valid_config)
    
    # Test invalid configuration (missing exports)
    invalid_config = {
        "something_else": []
    }
    assert not service.validate_configuration(invalid_config)
    
    # Test invalid network specification
    invalid_network_config = {
        "exports": [
            {
                "path": "/mnt/export",
                "clients": [
                    {
                        "network": "invalid_network",
                        "options": ["rw"]
                    }
                ]
            }
        ]
    }
    assert not service.validate_configuration(invalid_network_config)

def test_ftp_service_validation(config_path):
    """Test FTP service configuration validation."""
    service = FTPService(config_path)
    
    # Test valid configuration
    valid_config = {
        "anonymous_enable": False,
        "local_enable": True,
        "write_enable": True,
        "pasv_min_port": 49152,
        "pasv_max_port": 49252
    }
    assert service.validate_configuration(valid_config)
    
    # Test invalid configuration (missing required fields)
    invalid_config = {
        "anonymous_enable": False
    }
    assert not service.validate_configuration(invalid_config)
    
    # Test invalid passive port range
    invalid_port_config = {
        "anonymous_enable": False,
        "local_enable": True,
        "write_enable": True,
        "pasv_min_port": 50000,
        "pasv_max_port": 49000  # Min > Max
    }
    assert not service.validate_configuration(invalid_port_config)

def test_iscsi_service_validation(config_path):
    """Test iSCSI service configuration validation."""
    service = iSCSIService(config_path)
    
    # Test valid configuration
    valid_config = {
        "targets": [
            {
                "name": "iqn.2024-04.local.moxnas:target0",
                "luns": [
                    {
                        "id": 0,
                        "path": "/dev/zvol/tank/vol1",
                        "type": "block"
                    }
                ]
            }
        ]
    }
    assert service.validate_configuration(valid_config)
    
    # Test invalid configuration (missing targets)
    invalid_config = {
        "something_else": []
    }
    assert not service.validate_configuration(invalid_config)
    
    # Test invalid LUN type
    invalid_lun_config = {
        "targets": [
            {
                "name": "iqn.2024-04.local.moxnas:target0",
                "luns": [
                    {
                        "id": 0,
                        "path": "/path/to/file",
                        "type": "invalid_type"
                    }
                ]
            }
        ]
    }
    assert not service.validate_configuration(invalid_lun_config)

def test_smb_config_generation(config_path):
    """Test SMB configuration generation."""
    service = SMBService(config_path)
    
    config = {
        "workgroup": "WORKGROUP",
        "server_string": "MoxNAS Server",
        "shares": [
            {
                "name": "test_share",
                "path": "/mnt/test",
                "valid_users": ["user1", "user2"]
            }
        ]
    }
    
    content = service.generate_config(config)
    assert "[global]" in content
    assert "workgroup = WORKGROUP" in content
    assert "[test_share]" in content
    assert "valid users = user1,user2" in content
    
    # Test config application
    assert service.apply_config(config)
    assert os.path.exists(service.config_file)

def test_nfs_config_generation(config_path):
    """Test NFS configuration generation."""
    service = NFSService(config_path)
    
    config = {
        "exports": [
            {
                "path": "/mnt/export",
                "clients": [
                    {
                        "network": "192.168.1.0/24",
                        "options": ["rw", "sync", "no_subtree_check"]
                    }
                ]
            }
        ]
    }
    
    content = service.generate_config(config)
    assert "/mnt/export" in content
    assert "192.168.1.0/24(rw,sync,no_subtree_check)" in content
    
    # Test config application
    assert service.apply_config(config)
    assert os.path.exists(service.exports_file)

def test_ftp_config_generation(config_path):
    """Test FTP configuration generation."""
    service = FTPService(config_path)
    
    config = {
        "anonymous_enable": False,
        "local_enable": True,
        "write_enable": True,
        "pasv_min_port": 49152,
        "pasv_max_port": 49252,
        "ssl_enable": True,
        "ssl_cert_file": "/etc/ssl/test.pem",
        "ssl_key_file": "/etc/ssl/test.key"
    }
    
    content = service.generate_config(config)
    assert "anonymous_enable=false" in content
    assert "local_enable=true" in content
    assert "pasv_enable=YES" in content
    assert "ssl_enable=YES" in content
    assert "ssl_cert_file=/etc/ssl/test.pem" in content
    
    # Test config application
    assert service.apply_config(config)
    assert os.path.exists(service.config_file)

def test_iscsi_config_generation(config_path):
    """Test iSCSI configuration generation."""
    service = iSCSIService(config_path)
    
    config = {
        "targets": [
            {
                "name": "iqn.2024-04.local.moxnas:target0",
                "luns": [
                    {
                        "id": 0,
                        "path": "/dev/zvol/tank/vol1",
                        "type": "block"
                    }
                ],
                "allowed_initiators": ["iqn.2024-04.local.client:initiator0"]
            }
        ]
    }
    
    configs = service.generate_config(config)
    assert len(configs) == 1
    
    content = configs["iqn.2024-04.local.moxnas:target0"]
    assert "<target iqn.2024-04.local.moxnas:target0>" in content
    assert "lun 0" in content
    assert "device-type block" in content
    assert "iqn.2024-04.local.client:initiator0" in content
    
    # Test config application
    assert service.apply_config(config)
    assert os.path.exists(service.config_dir)
    assert os.path.exists(service.config_dir / "target0.conf")

def test_service_port_validation(config_path):
    """Test service port validation."""
    smb = SMBService(config_path)
    nfs = NFSService(config_path)
    ftp = FTPService(config_path)
    iscsi = iSCSIService(config_path)
    
    assert smb.validate_port(445)
    assert not smb.validate_port(0)
    assert not smb.validate_port(65536)
    
    # NFS uses multiple ports
    assert all(nfs.validate_port(port) for port in [2049, 111])
    
    # FTP passive port range
    assert ftp.validate_port(21)
    assert all(ftp.validate_port(port) for port in range(49152, 49252))
    
    assert iscsi.validate_port(3260)