import os
import subprocess
import json
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from app.models import SystemLog, LogLevel
from app.storage.zfs_db import (
    create_zfs_pool_database_entry,
    create_zfs_dataset_database_entry,
    get_pool_id,
)


class ZFSPoolType(Enum):
    """ZFS pool configuration types"""

    SINGLE = "single"
    MIRROR = "mirror"
    RAIDZ1 = "raidz1"  # Similar to RAID5
    RAIDZ2 = "raidz2"  # Similar to RAID6
    RAIDZ3 = "raidz3"  # Triple parity
    STRIPED = "striped"  # Similar to RAID0


class ZFSCompression(Enum):
    """ZFS compression algorithms"""

    OFF = "off"
    LZ4 = "lz4"
    GZIP = "gzip"
    ZSTD = "zstd"
    LZO = "lzo"


class ZFSWorkloadType(Enum):
    """ZFS workload optimization profiles"""

    DATABASE = "database"  # Small random I/O
    VIRTUAL_MACHINES = "vms"  # Mixed workload
    FILE_SHARES = "shares"  # Large sequential files
    BACKUP_TARGET = "backup"  # Write-heavy, compression focused
    MIXED = "mixed"  # General purpose


@dataclass
class ZFSPoolConfig:
    """ZFS pool configuration with workload optimization"""

    name: str
    pool_type: ZFSPoolType
    devices: List[str]
    spare_devices: List[str] = None
    cache_devices: List[str] = None  # L2ARC devices (SSDs)
    log_devices: List[str] = None  # ZIL devices (fast SSDs/NVMe)
    ashift: int = 12  # Sector size (2^ashift bytes, 12=4K)
    compression: ZFSCompression = ZFSCompression.LZ4
    deduplication: bool = False
    encryption: bool = False
    recordsize: str = "128K"  # Record size
    quota: Optional[str] = None
    reservation: Optional[str] = None
    workload_type: ZFSWorkloadType = ZFSWorkloadType.MIXED
    auto_snapshot: bool = True
    scrub_schedule: str = "weekly"  # weekly, monthly, disabled


@dataclass
class ZFSDatasetConfig:
    """ZFS dataset configuration"""

    name: str
    pool_name: str
    mount_point: Optional[str] = None
    compression: ZFSCompression = ZFSCompression.LZ4
    deduplication: bool = False
    encryption: bool = False
    recordsize: str = "128K"
    quota: Optional[str] = None
    reservation: Optional[str] = None
    sync: str = "standard"  # standard, always, disabled
    atime: bool = False  # Access time updates


@dataclass
class ZFSSnapshot:
    """ZFS snapshot information"""

    name: str
    dataset: str
    creation_time: datetime
    used_space: int
    referenced_space: int
    unique_space: int


class ZFSManager:
    """Advanced ZFS management system"""

    def __init__(self):
        self.tools = self._detect_zfs_tools()
        self.zfs_available = bool(self.tools.get("zfs") and self.tools.get("zpool"))

        if not self.zfs_available:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category="storage",
                message="ZFS tools not available on system",
            )

    def _detect_zfs_tools(self) -> Dict[str, str]:
        """Detect ZFS tools and their paths"""
        tools = {}

        tool_paths = {
            "zfs": ["/sbin/zfs", "/usr/sbin/zfs", "/usr/bin/zfs"],
            "zpool": ["/sbin/zpool", "/usr/sbin/zpool", "/usr/bin/zpool"],
            "zdb": ["/sbin/zdb", "/usr/sbin/zdb", "/usr/bin/zdb"],
            "zinject": ["/sbin/zinject", "/usr/sbin/zinject"],
            "zstreamdump": ["/sbin/zstreamdump", "/usr/sbin/zstreamdump"],
        }

        for tool, paths in tool_paths.items():
            for path in paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    tools[tool] = path
                    break

        return tools

    def run_zfs_command(
        self, command: List[str], timeout: int = 60
    ) -> Tuple[bool, str, str]:
        """Execute ZFS command with error handling"""
        if not self.zfs_available:
            return False, "", "ZFS tools not available"

        try:
            SystemLog.log_event(
                level=LogLevel.DEBUG,
                category="storage",
                message=f'Executing ZFS command: {" ".join(command)}',
                details={"timeout": timeout},
            )

            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout, check=False
            )

            success = result.returncode == 0
            if not success:
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category="storage",
                    message=f'ZFS command failed: {" ".join(command)}',
                    details={"return_code": result.returncode, "stderr": result.stderr},
                )

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = f"ZFS command timed out after {timeout} seconds"
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="storage",
                message=f'ZFS command timeout: {" ".join(command)}',
                details={"timeout": timeout},
            )
            return False, "", error_msg

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="storage",
                message=f'ZFS command execution error: {" ".join(command)}',
                details={"error": str(e)},
            )
            return False, "", str(e)

    def is_zfs_available(self) -> bool:
        """Check if ZFS is available on the system"""
        return self.zfs_available

    def list_pools(self) -> List[Dict]:
        """List all ZFS pools with detailed information"""
        if not self.zfs_available:
            return []

        success, stdout, stderr = self.run_zfs_command(
            [
                self.tools["zpool"],
                "list",
                "-H",
                "-o",
                "name,size,alloc,free,cap,dedup,health,altroot",
            ]
        )

        if not success:
            return []

        pools = []
        for line in stdout.strip().split("\n"):
            if line:
                parts = line.split("\t")
                if len(parts) >= 7:
                    pools.append(
                        {
                            "name": parts[0],
                            "size": parts[1],
                            "allocated": parts[2],
                            "free": parts[3],
                            "capacity": parts[4],
                            "dedup_ratio": parts[5],
                            "health": parts[6],
                            "altroot": parts[7] if len(parts) > 7 else "-",
                        }
                    )

        return pools

    def create_pool(self, config: ZFSPoolConfig) -> Tuple[bool, str]:
        """Create ZFS pool with advanced configuration"""
        if not self.zfs_available:
            return False, "ZFS not available"

        # Validate configuration
        validation_error = self._validate_zfs_config(config)
        if validation_error:
            return False, validation_error

        # Build zpool create command
        cmd = [self.tools["zpool"], "create"]

        # Add pool properties
        cmd.extend(["-o", f"ashift={config.ashift}"])

        # Add filesystem properties based on workload
        fs_props = self._get_workload_properties(config.workload_type)
        fs_props.append(f"compression={config.compression.value}")
        fs_props.append(f"atime=off")  # Disable access time for performance

        if config.deduplication:
            fs_props.append("dedup=on")

        if config.encryption:
            fs_props.append("encryption=aes-256-gcm")
            fs_props.append("keyformat=passphrase")

        for prop in fs_props:
            cmd.extend(["-O", prop])

        # Add pool name
        cmd.append(config.name)

        # Add vdev configuration
        if config.pool_type == ZFSPoolType.SINGLE:
            cmd.extend(config.devices)
        elif config.pool_type == ZFSPoolType.MIRROR:
            cmd.append("mirror")
            cmd.extend(config.devices)
        elif config.pool_type == ZFSPoolType.RAIDZ1:
            cmd.append("raidz1")
            cmd.extend(config.devices)
        elif config.pool_type == ZFSPoolType.RAIDZ2:
            cmd.append("raidz2")
            cmd.extend(config.devices)
        elif config.pool_type == ZFSPoolType.RAIDZ3:
            cmd.append("raidz3")
            cmd.extend(config.devices)
        elif config.pool_type == ZFSPoolType.STRIPED:
            # For striped, just add devices without vdev type
            cmd.extend(config.devices)

        # Add spare devices
        if config.spare_devices:
            cmd.append("spare")
            cmd.extend(config.spare_devices)

        # Add cache devices (L2ARC)
        if config.cache_devices:
            cmd.append("cache")
            cmd.extend(config.cache_devices)

        # Add log devices (ZIL)
        if config.log_devices:
            cmd.append("log")
            if len(config.log_devices) > 1:
                cmd.append("mirror")
            cmd.extend(config.log_devices)

        # Execute pool creation
        success, stdout, stderr = self.run_zfs_command(cmd, timeout=300)
        if not success:
            return False, f"Pool creation failed: {stderr}"

        # Set additional properties if specified
        if config.quota:
            self.run_zfs_command(
                [self.tools["zfs"], "set", f"quota={config.quota}", config.name]
            )

        if config.reservation:
            self.run_zfs_command(
                [
                    self.tools["zfs"],
                    "set",
                    f"reservation={config.reservation}",
                    config.name,
                ]
            )

        # Create database entries
        try:
            create_zfs_pool_database_entry(config)

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="storage",
                message=f"ZFS pool created successfully: {config.name}",
                details={
                    "pool_type": config.pool_type.value,
                    "devices": config.devices,
                    "compression": config.compression.value,
                },
            )

            return True, f"ZFS pool {config.name} created successfully"

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="storage",
                message=f"Failed to create database entries for ZFS pool: {e}",
                details={"pool_name": config.name},
            )
            return False, f"Database error: {e}"

    def create_dataset(self, config: ZFSDatasetConfig) -> Tuple[bool, str]:
        """Create ZFS dataset with configuration"""
        if not self.zfs_available:
            return False, "ZFS not available"

        dataset_name = f"{config.pool_name}/{config.name}"

        # Build dataset create command
        cmd = [self.tools["zfs"], "create"]

        # Add properties
        properties = []
        properties.append(f"compression={config.compression.value}")
        properties.append(f"recordsize={config.recordsize}")
        properties.append(f"sync={config.sync}")
        properties.append(f'atime={"on" if config.atime else "off"}')

        if config.deduplication:
            properties.append("dedup=on")

        if config.encryption:
            properties.append("encryption=aes-256-gcm")
            properties.append("keyformat=passphrase")

        if config.quota:
            properties.append(f"quota={config.quota}")

        if config.reservation:
            properties.append(f"reservation={config.reservation}")

        if config.mount_point:
            properties.append(f"mountpoint={config.mount_point}")

        for prop in properties:
            cmd.extend(["-o", prop])

        cmd.append(dataset_name)

        # Execute dataset creation
        success, stdout, stderr = self.run_zfs_command(cmd)
        if not success:
            return False, f"Dataset creation failed: {stderr}"

        # Create database entry
        try:
            pool_id = get_pool_id(config.pool_name)
            if pool_id:
                create_zfs_dataset_database_entry(config, pool_id)

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="storage",
                message=f"ZFS dataset created: {dataset_name}",
                details={
                    "compression": config.compression.value,
                    "mount_point": config.mount_point,
                },
            )

            return True, f"Dataset {dataset_name} created successfully"

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="storage",
                message=f"Failed to create database entry for dataset: {e}",
                details={"dataset_name": dataset_name},
            )
            return False, f"Database error: {e}"

    def create_snapshot(
        self, dataset: str, snapshot_name: str = None
    ) -> Tuple[bool, str]:
        """Create ZFS snapshot"""
        if not self.zfs_available:
            return False, "ZFS not available"

        if not snapshot_name:
            snapshot_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        full_snapshot_name = f"{dataset}@{snapshot_name}"

        success, stdout, stderr = self.run_zfs_command(
            [self.tools["zfs"], "snapshot", full_snapshot_name]
        )

        if not success:
            return False, f"Snapshot creation failed: {stderr}"

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="storage",
            message=f"ZFS snapshot created: {full_snapshot_name}",
        )

        return True, f"Snapshot {full_snapshot_name} created successfully"

    def list_snapshots(self, dataset: str = None) -> List[ZFSSnapshot]:
        """List ZFS snapshots"""
        if not self.zfs_available:
            return []

        cmd = [
            self.tools["zfs"],
            "list",
            "-t",
            "snapshot",
            "-H",
            "-o",
            "name,creation,used,refer,uniqueobjsonly",
        ]

        if dataset:
            cmd.extend(["-r", dataset])

        success, stdout, stderr = self.run_zfs_command(cmd)
        if not success:
            return []

        snapshots = []
        for line in stdout.strip().split("\n"):
            if line and "@" in line:
                parts = line.split("\t")
                if len(parts) >= 5:
                    name_parts = parts[0].split("@")
                    snapshots.append(
                        ZFSSnapshot(
                            name=name_parts[1],
                            dataset=name_parts[0],
                            creation_time=datetime.fromtimestamp(int(parts[1])),
                            used_space=self._parse_size(parts[2]),
                            referenced_space=self._parse_size(parts[3]),
                            unique_space=self._parse_size(parts[4]),
                        )
                    )

        return snapshots

    def rollback_snapshot(
        self, dataset: str, snapshot_name: str, force: bool = False
    ) -> Tuple[bool, str]:
        """Rollback to ZFS snapshot"""
        if not self.zfs_available:
            return False, "ZFS not available"

        full_snapshot_name = f"{dataset}@{snapshot_name}"

        cmd = [self.tools["zfs"], "rollback"]
        if force:
            cmd.append("-r")
        cmd.append(full_snapshot_name)

        success, stdout, stderr = self.run_zfs_command(cmd)
        if not success:
            return False, f"Rollback failed: {stderr}"

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="storage",
            message=f"ZFS rollback completed: {full_snapshot_name}",
        )

        return True, f"Rollback to {full_snapshot_name} completed"

    def destroy_snapshot(self, dataset: str, snapshot_name: str) -> Tuple[bool, str]:
        """Destroy ZFS snapshot"""
        if not self.zfs_available:
            return False, "ZFS not available"

        full_snapshot_name = f"{dataset}@{snapshot_name}"

        success, stdout, stderr = self.run_zfs_command(
            [self.tools["zfs"], "destroy", full_snapshot_name]
        )

        if not success:
            return False, f"Snapshot destruction failed: {stderr}"

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="storage",
            message=f"ZFS snapshot destroyed: {full_snapshot_name}",
        )

        return True, f"Snapshot {full_snapshot_name} destroyed"

    def get_pool_status(self, pool_name: str) -> Dict:
        """Get detailed ZFS pool status"""
        if not self.zfs_available:
            return {"error": "ZFS not available"}

        success, stdout, stderr = self.run_zfs_command(
            [self.tools["zpool"], "status", "-v", pool_name]
        )

        if not success:
            return {"error": f"Failed to get pool status: {stderr}"}

        return self._parse_zpool_status(stdout)

    def scrub_pool(self, pool_name: str) -> Tuple[bool, str]:
        """Start ZFS pool scrub"""
        if not self.zfs_available:
            return False, "ZFS not available"

        success, stdout, stderr = self.run_zfs_command(
            [self.tools["zpool"], "scrub", pool_name]
        )

        if not success:
            return False, f"Scrub start failed: {stderr}"

        SystemLog.log_event(
            level=LogLevel.INFO,
            category="storage",
            message=f"ZFS pool scrub started: {pool_name}",
        )

        return True, f"Scrub started for pool {pool_name}"

    def get_compression_stats(self, dataset: str) -> Dict:
        """Get compression statistics for dataset"""
        if not self.zfs_available:
            return {}

        success, stdout, stderr = self.run_zfs_command(
            [
                self.tools["zfs"],
                "get",
                "-H",
                "-o",
                "value",
                "compressratio,used,logicalused",
                dataset,
            ]
        )

        if not success:
            return {}

        values = stdout.strip().split("\n")
        if len(values) >= 3:
            return {
                "compression_ratio": values[0],
                "used_space": values[1],
                "logical_space": values[2],
            }

        return {}

    def get_dedup_stats(self, pool_name: str) -> Dict:
        """Get deduplication statistics for pool"""
        if not self.zfs_available:
            return {}

        success, stdout, stderr = self.run_zfs_command(
            [self.tools["zpool"], "list", "-H", "-o", "dedup", pool_name]
        )

        if not success:
            return {}

        dedup_ratio = stdout.strip()
        return {"dedup_ratio": dedup_ratio}

    def _get_workload_properties(self, workload_type: ZFSWorkloadType) -> List[str]:
        """Get ZFS properties based on workload type"""
        if workload_type == ZFSWorkloadType.DATABASE:
            return ["recordsize=8K", "primarycache=metadata", "logbias=throughput"]
        elif workload_type == ZFSWorkloadType.VIRTUAL_MACHINES:
            return ["recordsize=64K", "primarycache=all", "logbias=latency"]
        elif workload_type == ZFSWorkloadType.FILE_SHARES:
            return ["recordsize=1M", "primarycache=all", "logbias=throughput"]
        elif workload_type == ZFSWorkloadType.BACKUP_TARGET:
            return [
                "recordsize=1M",
                "primarycache=all",
                "logbias=throughput",
                "compression=lz4",
            ]
        else:  # Mixed
            return ["recordsize=128K", "primarycache=all", "logbias=latency"]

    def _validate_zfs_config(self, config: ZFSPoolConfig) -> Optional[str]:
        """Validate ZFS pool configuration"""
        device_count = len(config.devices)

        # Check minimum device requirements
        min_devices = {
            ZFSPoolType.SINGLE: 1,
            ZFSPoolType.MIRROR: 2,
            ZFSPoolType.RAIDZ1: 3,
            ZFSPoolType.RAIDZ2: 4,
            ZFSPoolType.RAIDZ3: 5,
            ZFSPoolType.STRIPED: 2,
        }

        required = min_devices.get(config.pool_type)
        if required and device_count < required:
            return f"ZFS {config.pool_type.value} requires at least {required} devices"

        # Validate pool name
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", config.name):
            return "Invalid pool name format"

        # Check if pool already exists
        existing_pools = self.list_pools()
        if any(pool["name"] == config.name for pool in existing_pools):
            return f"Pool {config.name} already exists"

        # Validate devices exist
        for device in config.devices:
            if not os.path.exists(device):
                return f"Device {device} does not exist"

        return None

    def _parse_size(self, size_str: str) -> int:
        """Parse ZFS size string to bytes"""
        size_str = size_str.strip()
        if not size_str or size_str == "-":
            return 0

        # Remove units and convert
        multipliers = {
            "K": 1024,
            "M": 1024**2,
            "G": 1024**3,
            "T": 1024**4,
            "P": 1024**5,
            "E": 1024**6,
        }

        if size_str[-1] in multipliers:
            return int(float(size_str[:-1]) * multipliers[size_str[-1]])

        return int(float(size_str))

    def _parse_zpool_status(self, output: str) -> Dict:
        """Parse zpool status output"""
        status = {}
        lines = output.split("\n")

        current_section = None
        for line in lines:
            line = line.strip()

            if line.startswith("pool:"):
                status["pool"] = line.split(":", 1)[1].strip()
            elif line.startswith("state:"):
                status["state"] = line.split(":", 1)[1].strip()
            elif line.startswith("scan:"):
                status["scan"] = line.split(":", 1)[1].strip()
            elif line.startswith("errors:"):
                status["errors"] = line.split(":", 1)[1].strip()

        return status


# Global ZFS manager instance
zfs_manager = ZFSManager()
