"""Tests for container management functionality."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from moxnas.core import ContainerManager

@pytest.fixture
def container_manager(tmp_path):
    """Create a ContainerManager instance with temporary paths."""
    return ContainerManager("test-container", base_path=tmp_path)

@pytest.fixture
def mock_subprocess():
    """Mock subprocess for container operations."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="RUNNING\n")
        yield mock_run

def test_container_creation(container_manager, mock_subprocess, tmp_path):
    """Test container creation."""
    template_path = tmp_path / "truenas-template"
    config = {
        "lxc.net.0.type": "veth",
        "lxc.net.0.link": "lxcbr0",
        "lxc.net.0.flags": "up"
    }
    # Patch check_container_exists to return False so creation proceeds
    from unittest.mock import patch
    with patch.object(container_manager, "check_container_exists", return_value=False):
        assert container_manager.create_container(template_path, config)
        # Verify create command
        mock_subprocess.assert_any_call(
            ["lxc-create", "-n", "test-container", "-t", str(template_path), "-B", "dir"],
            capture_output=True,
            text=True,
            check=False
        )

def test_container_lifecycle(container_manager, mock_subprocess):
    """Test container start/stop operations."""
    # Test start
    assert container_manager.start(wait=True)
    mock_subprocess.assert_any_call(
        ["lxc-start", "-n", "test-container"],
        capture_output=True,
        text=True,
        check=False
    )
    
    # Test stop
    assert container_manager.stop()
    mock_subprocess.assert_any_call(
        ["lxc-stop", "-n", "test-container", "-t", "30"],
        capture_output=True,
        text=True,
        check=False
    )

def test_container_cloning(container_manager, mock_subprocess):
    """Test container cloning."""
    assert container_manager.clone("new-container", snapshot=True)
    mock_subprocess.assert_called_with(
        ["lxc-copy", "-n", "test-container", "-N", "new-container", "-s"],
        capture_output=True,
        text=True,
        check=False
    )

def test_snapshot_operations(container_manager, mock_subprocess):
    """Test snapshot creation and restoration."""
    # Test snapshot creation
    assert container_manager.snapshot("test-snap")
    mock_subprocess.assert_any_call(
        ["lxc-snapshot", "-n", "test-container", "-N", "test-snap"],
        capture_output=True,
        text=True,
        check=False
    )
    
    # Test snapshot restoration
    with patch('pathlib.Path.exists') as mock_exists:
        mock_exists.return_value = True
        assert container_manager.restore_snapshot("test-snap")
        mock_subprocess.assert_any_call(
            ["lxc-snapshot", "-n", "test-container", "-r", "test-snap"],
            capture_output=True,
            text=True,
            check=False
        )

def test_config_update(container_manager, tmp_path):
    """Test container configuration updates."""
    # Create mock config file
    config_path = container_manager.config_path
    config_path.parent.mkdir(parents=True)
    config_path.write_text("""
# Network configuration
lxc.net.0.type = veth
lxc.net.0.link = lxcbr0

# Resource limits
lxc.cgroup.memory.limit_in_bytes = 4G
""")
    
    new_config = {
        "lxc.net.0.link": "br0",
        "lxc.cgroup.memory.limit_in_bytes": "8G",
        "lxc.cgroup.cpu.shares": "1024"
    }
    
    assert container_manager.update_config(new_config)
    
    # Verify config file content
    content = config_path.read_text()
    assert "lxc.net.0.link = br0" in content
    assert "lxc.cgroup.memory.limit_in_bytes = 8G" in content
    assert "lxc.cgroup.cpu.shares = 1024" in content
    assert "# Network configuration" in content  # Comments preserved

def test_container_status(container_manager, mock_subprocess):
    """Test container status checking."""
    assert container_manager.get_container_status() == "RUNNING"
    mock_subprocess.assert_called_with(
        ["lxc-info", "-n", "test-container", "-s"],
        capture_output=True,
        text=True,
        check=True
    )