"""Tests for Proxmox connection manager."""

import pytest
from unittest.mock import Mock, patch
from moxnas.proxmox import ProxmoxManager

def test_proxmox_connection_init():
    """Test ProxmoxManager initialization."""
    manager = ProxmoxManager(
        host="test-host",
        user="test-user",
        verify_ssl=False
    )
    assert manager.host == "test-host"
    assert manager.user == "test-user"
    assert not manager.verify_ssl
    assert not manager.is_connected

@patch('moxnas.proxmox.ProxmoxAPI')
def test_proxmox_connection_success(mock_proxmox):
    """Test successful Proxmox connection."""
    # Setup mock
    mock_api = Mock()
    mock_api.version.get.return_value = {"version": "8.4.0"}
    mock_proxmox.return_value = mock_api
    
    # Test connection
    manager = ProxmoxManager("test-host")
    assert manager.connect("test-password")
    assert manager.is_connected
    
    # Verify API calls
    mock_proxmox.assert_called_once_with(
        "test-host",
        user="root@pam",
        password="wc305ekb",
        verify_ssl=True,
        port=8006
    )

@patch('moxnas.proxmox.ProxmoxAPI')
def test_proxmox_connection_failure(mock_proxmox):
    """Test failed Proxmox connection."""
    # Setup mock to raise exception
    mock_proxmox.side_effect = Exception("Connection failed")
    
    # Test connection
    manager = ProxmoxManager("test-host")
    assert not manager.connect("test-password")
    assert not manager.is_connected

@patch('moxnas.proxmox.ProxmoxAPI')
def test_get_node_status(mock_proxmox):
    """Test getting node status."""
    # Setup mock
    mock_api = Mock()
    mock_node = Mock()
    mock_node.status.get.return_value = {"status": "running"}
    mock_api.nodes.return_value = mock_node
    mock_api.version.get.return_value = {"version": "8.4.0"}
    mock_proxmox.return_value = mock_api
    
    # Test node status
    manager = ProxmoxManager("test-host")
    manager.connect("test-password")
    status = manager.get_node_status("test-node")
    
    assert status == {"status": "running"}
    mock_api.nodes.assert_called_once_with("test-node")