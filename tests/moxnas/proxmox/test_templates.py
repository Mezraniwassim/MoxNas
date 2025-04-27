"""Tests for Proxmox VE template management."""

import pytest
from pathlib import Path
from moxnas.proxmox.templates import (
    get_truenas_container_config,
    get_storage_mount_config,
    get_debian_container_config,
    generate_truenas_init_script,
    prepare_debian_template
)

def test_truenas_container_config():
    """Test TrueNAS container configuration generation."""
    # Test default configuration
    config = get_truenas_container_config("truenas-test")
    assert config["hostname"] == "truenas-test"
    assert config["memory"] == 4096
    assert config["cores"] == 2
    assert config["rootfs"] == "local-lvm:32G"
    assert config["unprivileged"] == 0
    assert config["features"] == "nesting=1"
    assert "net0" in config
    assert config["lxc.apparmor.profile"] == "unconfined"
    
    # Test custom configuration
    custom_config = get_truenas_container_config(
        hostname="truenas-prod",
        memory=8192,
        cores=4,
        rootfs_size="64G",
        storage_pool="nvme-pool",
        network_bridge="vmbr1",
        ipv4="192.168.1.100/24",
        gateway="192.168.1.1"
    )
    assert custom_config["hostname"] == "truenas-prod"
    assert custom_config["memory"] == 8192
    assert custom_config["cores"] == 4
    assert custom_config["rootfs"] == "nvme-pool:64G"
    assert "ip=192.168.1.100/24" in custom_config["net0"]
    assert "gw=192.168.1.1" in custom_config["net0"]
    assert "bridge=vmbr1" in custom_config["net0"]

def test_storage_mount_config():
    """Test storage mount configuration generation."""
    # Test default configuration
    config = get_storage_mount_config(
        "data01",
        "/mnt/data01"
    )
    assert config["volume"] == "local-lvm:100G"
    assert config["mp"] == "/mnt/data01"
    assert config["mountoptions"] == "defaults"
    
    # Test custom configuration
    custom_config = get_storage_mount_config(
        "media01",
        "/mnt/media",
        storage_pool="nvme-pool",
        size="500G",
        mount_opts="noatime,nodiratime"
    )
    assert custom_config["volume"] == "nvme-pool:500G"
    assert custom_config["mp"] == "/mnt/media"
    assert custom_config["mountoptions"] == "noatime,nodiratime"

def test_debian_container_config_defaults():
    """Test default container configuration generation."""
    config = get_debian_container_config(vmid=100, hostname="truenas-test")
    
    assert config["hostname"] == "truenas-test"
    assert config["memory"] == 4096
    assert config["swap"] == 512
    assert config["cores"] == 2
    assert config["rootfs"] == "local:vm-100-disk-0,size=32G"
    assert "nesting=1" in config["features"]
    assert "keyctl=1" in config["features"]
    assert config["unprivileged"] == 0
    assert config["onboot"] == 1

def test_debian_container_config_custom():
    """Test container configuration with custom values."""
    custom_features = {
        "nesting": True,
        "keyctl": False,
        "mount": True
    }
    
    config = get_debian_container_config(
        vmid=101,
        hostname="truenas-custom",
        memory=8192,
        cores=4,
        disk_size="64G",
        network_bridge="vmbr1",
        features=custom_features
    )
    
    assert config["hostname"] == "truenas-custom"
    assert config["memory"] == 8192
    assert config["cores"] == 4
    assert config["rootfs"] == "local:vm-101-disk-0,size=64G"
    assert config["net0"] == "name=eth0,bridge=vmbr1,firewall=1,type=veth"
    assert "nesting=1" in config["features"]
    assert "keyctl=0" in config["features"]
    assert "mount=1" in config["features"]

def test_generate_truenas_init_script():
    """Test initialization script generation."""
    script = generate_truenas_init_script()
    
    assert "#!/bin/bash" in script
    assert "setup_container()" in script
    assert "apt-get update" in script
    assert "systemctl enable" in script
    assert "mkdir -p /var/lib/docker" in script
    assert "/var/lib/container_setup_complete" in script

def test_prepare_debian_template_defaults():
    """Test template preparation with default values."""
    template = prepare_debian_template(node="pve1")
    
    assert template["node"] == "pve1"
    assert template["storage"] == "local"
    assert template["osversion"] == "bookworm"
    assert template["template"] == 1
    assert template["unprivileged"] == 0
    assert "nesting=1" in template["features"]
    assert template["memory"] == 512
    assert template["cores"] == 1

def test_prepare_debian_template_custom():
    """Test template preparation with custom values."""
    template = prepare_debian_template(
        node="pve2",
        template_storage="storage1",
        debian_version="bullseye"
    )
    
    assert template["node"] == "pve2"
    assert template["storage"] == "storage1"
    assert template["osversion"] == "bullseye"
    assert template["template"] == 1
    assert template["unprivileged"] == 0
    assert template["rootfs"] == "storage1:vm-9000-disk-0,size=4G"