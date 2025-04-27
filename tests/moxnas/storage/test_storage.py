"""Tests for storage management functionality."""

import os
import pytest
from pathlib import Path
import subprocess
from unittest.mock import patch, MagicMock
from moxnas.storage import StorageManager

@pytest.fixture
def storage_manager(tmp_path):
    """Create a StorageManager instance with temporary paths."""
    container_path = tmp_path / "container"
    container_path.mkdir()
    (container_path / "rootfs" / "mnt").mkdir(parents=True)
    return StorageManager(container_path)

@pytest.fixture
def mock_subprocess():
    """Mock subprocess for mount operations."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        yield mock_run

@pytest.fixture
def mock_proc_mounts(tmp_path):
    """Create a mock /proc/mounts file."""
    mounts_file = tmp_path / "mounts"
    mounts_file.write_text("")
    with patch('builtins.open') as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = ""
        yield mock_open

def test_ensure_mount_point(storage_manager):
    """Test mount point creation."""
    mount_name = "test_mount"
    mount_path = storage_manager.ensure_mount_point(mount_name)
    assert mount_path.exists()
    assert mount_path.is_dir()
    assert mount_path == storage_manager.mounts_path / mount_name

def test_bind_mount(storage_manager, mock_subprocess, tmp_path):
    """Test bind mount creation."""
    source = tmp_path / "source"
    source.mkdir()
    
    # Test successful bind mount
    assert storage_manager.bind_mount(source, "test_bind")
    
    # Verify mount command
    mock_subprocess.assert_called_with(
        ["mount", "--bind", str(source), str(storage_manager.mounts_path / "test_bind")],
        capture_output=True,
        text=True,
        check=False
    )
    
    # Test read-only bind mount
    storage_manager.bind_mount(source, "test_bind_ro", read_only=True)
    assert mock_subprocess.call_count == 3  # bind + remount calls

def test_mount_device(storage_manager, mock_subprocess):
    """Test device mount functionality."""
    with patch('pathlib.Path.exists') as mock_exists, \
         patch('pathlib.Path.is_block_device') as mock_is_block:
        mock_exists.return_value = True
        mock_is_block.return_value = True
        
        device = Path("/dev/sda1")
        assert storage_manager.mount_device(device, "test_device", "ext4")
        
        # Verify mount command
        mock_subprocess.assert_called_with(
            ["mount", "-t", "ext4", str(device), 
             str(storage_manager.mounts_path / "test_device")],
            capture_output=True,
            text=True,
            check=False
        )

def test_add_to_fstab(storage_manager, tmp_path):
    """Test fstab entry creation."""
    storage_manager.fstab_path.touch()
    
    source = "/dev/sda1"
    mount_point = "test_mount"
    
    assert storage_manager.add_to_fstab(source, mount_point, "ext4", ["defaults"])
    
    with open(storage_manager.fstab_path) as f:
        content = f.read()
        assert f"{source} /mnt/{mount_point} ext4 defaults 0 0\n" in content

def test_unmount(storage_manager, mock_subprocess):
    """Test unmount functionality."""
    # Test successful unmount
    assert storage_manager.unmount("test_mount")
    
    # Test force unmount
    assert storage_manager.unmount("test_mount", force=True)
    mock_subprocess.assert_called_with(
        ["umount", "-f", str(storage_manager.mounts_path / "test_mount")],
        capture_output=True,
        text=True,
        check=False
    )

@pytest.mark.skipif(os.geteuid() != 0, reason="requires root")
def test_integration_bind_mount(storage_manager, tmp_path):
    """Integration test for bind mount (requires root)."""
    source = tmp_path / "source"
    source.mkdir()
    mount_point = "test_bind"
    
    try:
        assert storage_manager.bind_mount(source, mount_point)
        assert storage_manager.is_mounted(storage_manager.mounts_path / mount_point)
    finally:
        # Cleanup
        storage_manager.unmount(mount_point, force=True)