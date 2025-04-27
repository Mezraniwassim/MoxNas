"""Tests for Proxmox VE integration."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from moxnas.proxmox import ProxmoxManager

@pytest.fixture
def proxmox_manager(tmp_path):
    """Create a ProxmoxManager instance for testing."""
    config_path = tmp_path / "proxmox.json"
    return ProxmoxManager("proxmox.local", config_path=config_path)

@pytest.fixture
def mock_proxmoxer():
    """Mock ProxmoxAPI for testing."""
    with patch('moxnas.proxmox.ProxmoxAPI') as mock:
        mock.return_value.version.get.return_value = {"version": "8.4.0"}
        yield mock

def test_proxmox_connection(proxmox_manager, mock_proxmoxer):
    """Test Proxmox API connection."""
    # Test password authentication
    assert proxmox_manager.connect("user@pam", password="password")
    mock_proxmoxer.assert_called_with(
        "proxmox.local",
        port=8006,
        user="user@pam",
        password="password",
        verify_ssl=True
    )
    
    # Test token authentication
    mock_proxmoxer.reset_mock()
    assert proxmox_manager.connect(
        "user@pam",
        token_name="token",
        token_value="secret"
    )
    mock_proxmoxer.assert_called_with(
        "proxmox.local",
        port=8006,
        user="user@pam",
        token_name="token",
        token_value="secret",
        verify_ssl=True
    )

def test_node_operations(proxmox_manager, mock_proxmoxer):
    """Test node-related operations."""
    mock_nodes = [
        {"node": "node1", "status": "online"},
        {"node": "node2", "status": "online"}
    ]
    mock_proxmoxer.return_value.nodes.get.return_value = mock_nodes
    
    # Connect first
    proxmox_manager.connect("user@pam", password="password")
    
    # Test node listing
    nodes = proxmox_manager.get_node_list()
    assert nodes == mock_nodes
    
    # Test error handling when not connected
    proxmox_manager.proxmox = None
    assert proxmox_manager.get_node_list() == []

def test_storage_operations(proxmox_manager, mock_proxmoxer):
    """Test storage-related operations."""
    mock_storage = [
        {"storage": "local", "type": "dir"},
        {"storage": "local-lvm", "type": "lvmthin"}
    ]
    mock_proxmoxer.return_value.nodes.return_value.storage.get.return_value = mock_storage
    
    # Connect first
    proxmox_manager.connect("user@pam", password="password")
    
    # Test storage listing
    storage = proxmox_manager.get_storage_list("node1")
    assert storage == mock_storage
    
    # Test error handling
    proxmox_manager.proxmox = None
    assert proxmox_manager.get_storage_list("node1") == []

def test_container_operations(proxmox_manager, mock_proxmoxer):
    """Test container-related operations."""
    mock_config = {
        "hostname": "truenas",
        "memory": 4096,
        "swap": 0,
        "cores": 2
    }
    mock_proxmoxer.return_value.nodes.return_value.lxc.return_value.config.get.return_value = mock_config
    
    # Connect first
    proxmox_manager.connect("user@pam", password="password")
    
    # Test container config retrieval
    config = proxmox_manager.get_container_config("node1", 100)
    assert config == mock_config
    
    # Test container creation
    assert proxmox_manager.create_container("node1", 101, mock_config)
    mock_proxmoxer.return_value.nodes.return_value.lxc.create.assert_called_with(
        vmid=101,
        **mock_config
    )
    
    # Test container deletion
    assert proxmox_manager.delete_container("node1", 101)
    mock_proxmoxer.return_value.nodes.return_value.lxc.return_value.delete.assert_called_once()

def test_config_persistence(proxmox_manager, tmp_path):
    """Test configuration persistence."""
    config = {
        "default_node": "node1",
        "storage_pool": "local-lvm"
    }
    
    # Save config
    proxmox_manager.config = config
    assert proxmox_manager._save_config()
    
    # Load in new instance
    new_manager = ProxmoxManager("proxmox.local", config_path=proxmox_manager.config_path)
    assert new_manager.config == config

def test_template_verification(proxmox_manager, mock_proxmoxer):
    """Test template verification functionality."""
    mock_templates = [
        {"volid": "local:vztmpl/truenas-scale-24.10.2.1.tar.gz", "size": 1024},
        {"volid": "local:vztmpl/debian-12.tar.gz", "size": 512}
    ]
    
    mock_proxmoxer.return_value.nodes.return_value.storage.return_value.content.get.return_value = mock_templates
    
    # Connect first
    proxmox_manager.connect("user@pam", password="password")
    
    # Test existing template
    exists, message = proxmox_manager.verify_template(
        "node1", 
        "local:vztmpl/truenas-scale-24.10.2.1.tar.gz"
    )
    assert exists
    assert "found" in message
    
    # Test non-existent template
    exists, message = proxmox_manager.verify_template(
        "node1",
        "local:vztmpl/nonexistent.tar.gz"
    )
    assert not exists
    assert "not found" in message

def test_list_templates(proxmox_manager, mock_proxmoxer):
    """Test template listing functionality."""
    mock_storage = [
        {"storage": "local", "type": "dir"},
        {"storage": "local-lvm", "type": "lvmthin"}
    ]
    mock_templates = [
        {"volid": "local:vztmpl/template1.tar.gz", "size": 1024},
        {"volid": "local:vztmpl/template2.tar.gz", "size": 2048}
    ]
    
    mock_proxmoxer.return_value.nodes.return_value.storage.get.return_value = mock_storage
    mock_proxmoxer.return_value.nodes.return_value.storage.return_value.content.get.return_value = mock_templates
    
    # Connect first
    proxmox_manager.connect("user@pam", password="password")
    
    # Test template listing
    templates = proxmox_manager.list_templates("node1")
    assert len(templates) > 0
    assert all("volid" in template for template in templates)
    
    # Test error handling when not connected
    proxmox_manager.proxmox = None
    assert proxmox_manager.list_templates("node1") == []