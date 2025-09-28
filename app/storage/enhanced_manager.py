"""
Enhanced Storage Management System for MoxNAS
Provides advanced RAID, device management, and performance optimization
"""
import os
import subprocess
import json
import re
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from app.models import StorageDevice, StoragePool, DeviceStatus, PoolStatus, SystemLog, LogLevel
from app import db
import psutil


class RAIDLevel(Enum):
    """Supported RAID levels with enhanced options"""

    RAID0 = "raid0"
    RAID1 = "raid1"
    RAID5 = "raid5"
    RAID6 = "raid6"  # Added RAID 6 support
    RAID10 = "raid10"
    JBOD = "jbod"  # Just a Bunch of Disks


@dataclass
class DeviceInfo:
    """Enhanced device information structure"""

    device_path: str
    device_name: str
    model: str
    serial: str
    size_bytes: int
    sector_size: int
    rotation_rate: int  # 0 for SSD, >0 for HDD
    interface: str  # SATA, NVMe, USB, etc.
    smart_enabled: bool
    temperature: Optional[int]
    power_on_hours: Optional[int]
    wear_level: Optional[int]  # For SSDs
    bad_sectors: int
    is_hotpluggable: bool
    partition_table: str
    health_status: DeviceStatus


@dataclass
class RAIDConfiguration:
    """RAID configuration parameters"""

    level: RAIDLevel
    devices: List[str]
    spare_devices: List[str]
    chunk_size: int = 512  # KB
    metadata_version: str = "1.2"
    bitmap: bool = True
    assume_clean: bool = False


class EnhancedStorageManager:
    """Advanced storage management with enterprise features"""

    def __init__(self):
        self.tools = self._detect_system_tools()
        self.monitoring_thread = None
        self.monitoring_active = False
        self._device_cache = {}
        self._last_scan = None

        # Performance monitoring
        self.io_stats = {}
        self.performance_history = {}

    def _detect_system_tools(self) -> Dict[str, str]:
        """Detect available system tools and their paths"""
        tools = {}

        # Essential tools
        tool_paths = {
            "mdadm": ["/sbin/mdadm", "/usr/sbin/mdadm"],
            "smartctl": ["/usr/sbin/smartctl", "/sbin/smartctl"],
            "lsblk": ["/bin/lsblk", "/usr/bin/lsblk"],
            "blkid": ["/sbin/blkid", "/usr/sbin/blkid"],
            "hdparm": ["/sbin/hdparm", "/usr/sbin/hdparm"],
            "nvme": ["/usr/sbin/nvme", "/sbin/nvme"],
            "parted": ["/sbin/parted", "/usr/sbin/parted"],
            "mkfs.ext4": ["/sbin/mkfs.ext4", "/usr/sbin/mkfs.ext4"],
            "mkfs.xfs": ["/sbin/mkfs.xfs", "/usr/sbin/mkfs.xfs"],
            "tune2fs": ["/sbin/tune2fs", "/usr/sbin/tune2fs"],
            "xfs_info": ["/usr/sbin/xfs_info", "/sbin/xfs_info"],
        }

        for tool, paths in tool_paths.items():
            for path in paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    tools[tool] = path
                    break

        return tools

    def run_command(
        self,
        command: List[str],
        timeout: int = 30,
        capture_output: bool = True,
        check: bool = False,
    ) -> Tuple[bool, str, str]:
        """Execute system command with enhanced error handling"""
        try:
            # Log command execution for debugging
            SystemLog.log_event(
                level=LogLevel.DEBUG,
                category="storage",
                message=f'Executing command: {" ".join(command)}',
                details={"timeout": timeout},
            )

            result = subprocess.run(
                command, capture_output=capture_output, text=True, timeout=timeout, check=check
            )

            success = result.returncode == 0
            if not success:
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category="storage",
                    message=f'Command failed: {" ".join(command)}',
                    details={"return_code": result.returncode, "stderr": result.stderr},
                )

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds"
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="storage",
                message=f'Command timeout: {" ".join(command)}',
                details={"timeout": timeout},
            )
            return False, "", error_msg

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="storage",
                message=f'Command execution error: {" ".join(command)}',
                details={"error": str(e)},
            )
            return False, "", str(e)

    def scan_storage_devices(self, force_rescan: bool = False) -> List[DeviceInfo]:
        """Enhanced device scanning with caching and detailed information"""
        # Use cache if recent scan available
        if (
            not force_rescan
            and self._last_scan
            and datetime.now() - self._last_scan < timedelta(minutes=5)
        ):
            return list(self._device_cache.values())

        devices = []

        # Primary scan using lsblk
        if "lsblk" in self.tools:
            devices.extend(self._scan_with_lsblk())

        # Enhance with SMART data
        for device in devices:
            device.smart_enabled = self._check_smart_support(device.device_path)
            if device.smart_enabled:
                smart_data = self._get_smart_data(device.device_path)
                if smart_data:
                    device.temperature = smart_data.get("temperature")
                    device.power_on_hours = smart_data.get("power_on_hours")
                    device.bad_sectors = smart_data.get("bad_sectors", 0)
                    device.wear_level = smart_data.get("wear_level")

                    # Determine health status
                    if smart_data.get("health_status") == "PASSED":
                        if device.temperature and device.temperature > 60:
                            device.health_status = DeviceStatus.WARNING
                        elif device.bad_sectors > 0:
                            device.health_status = DeviceStatus.WARNING
                        else:
                            device.health_status = DeviceStatus.HEALTHY
                    else:
                        device.health_status = DeviceStatus.FAILED

        # Update cache
        self._device_cache = {dev.device_path: dev for dev in devices}
        self._last_scan = datetime.now()

        return devices

    def _scan_with_lsblk(self) -> List[DeviceInfo]:
        """Scan devices using lsblk command"""
        devices = []

        success, stdout, stderr = self.run_command(
            [
                self.tools["lsblk"],
                "-J",
                "-b",
                "-o",
                "NAME,SIZE,TYPE,MOUNTPOINT,MODEL,SERIAL,ROTA,HOTPLUG,TRAN,PTTYPE",
            ]
        )

        if not success:
            return devices

        try:
            data = json.loads(stdout)
            for device_data in data.get("blockdevices", []):
                if device_data.get("type") == "disk":
                    device_info = self._parse_lsblk_device(device_data)
                    if device_info:
                        devices.append(device_info)
        except json.JSONDecodeError as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="storage",
                message=f"Failed to parse lsblk output: {e}",
                details={"stdout": stdout},
            )

        return devices

    def _parse_lsblk_device(self, device_data: Dict) -> Optional[DeviceInfo]:
        """Parse device information from lsblk output"""
        try:
            name = device_data.get("name", "")
            if not name:
                return None

            device_path = f"/dev/{name}"
            size = int(device_data.get("size", 0))

            # Skip devices that are too small (< 1GB) or mounted
            if size < 1024**3 or device_data.get("mountpoint"):
                return None

            device_info = DeviceInfo(
                device_path=device_path,
                device_name=name,
                model=device_data.get("model", "Unknown").strip() or "Unknown",
                serial=device_data.get("serial", "Unknown").strip() or "Unknown",
                size_bytes=size,
                sector_size=512,  # Default, will be updated if available
                rotation_rate=0 if device_data.get("rota") == "0" else 7200,
                interface=device_data.get("tran", "Unknown").upper(),
                smart_enabled=False,  # Will be updated
                temperature=None,
                power_on_hours=None,
                wear_level=None,
                bad_sectors=0,
                is_hotpluggable=device_data.get("hotplug") == "1",
                partition_table=device_data.get("pttype", "none"),
                health_status=DeviceStatus.HEALTHY,
            )

            return device_info

        except (ValueError, KeyError) as e:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category="storage",
                message=f"Failed to parse device data: {e}",
                details={"device_data": device_data},
            )
            return None

    def _check_smart_support(self, device_path: str) -> bool:
        """Check if device supports SMART monitoring"""
        if "smartctl" not in self.tools:
            return False

        success, stdout, stderr = self.run_command([self.tools["smartctl"], "-i", device_path])

        return success and "SMART support is: Enabled" in stdout

    def _get_smart_data(self, device_path: str) -> Optional[Dict]:
        """Get SMART data for device"""
        if "smartctl" not in self.tools:
            return None

        success, stdout, stderr = self.run_command(
            [self.tools["smartctl"], "-A", "-H", "-j", device_path]
        )

        if not success:
            # Try without JSON format for older versions
            success, stdout, stderr = self.run_command(
                [self.tools["smartctl"], "-A", "-H", device_path]
            )
            if success:
                return self._parse_smart_text(stdout)
            return None

        try:
            data = json.loads(stdout)
            return self._parse_smart_json(data)
        except json.JSONDecodeError:
            return self._parse_smart_text(stdout)

    def _parse_smart_json(self, data: Dict) -> Dict:
        """Parse SMART data from JSON format"""
        result = {}

        # Health status
        smart_status = data.get("smart_status", {})
        result["health_status"] = "PASSED" if smart_status.get("passed") else "FAILED"

        # Temperature
        temp_data = data.get("temperature", {})
        if temp_data:
            result["temperature"] = temp_data.get("current")

        # Attributes
        attributes = data.get("ata_smart_attributes", {}).get("table", [])
        for attr in attributes:
            attr_id = attr.get("id")
            value = attr.get("raw", {}).get("value", 0)

            if attr_id == 9:  # Power-on hours
                result["power_on_hours"] = value
            elif attr_id == 5:  # Reallocated sectors
                result["bad_sectors"] = value
            elif attr_id == 233:  # SSD wear level
                result["wear_level"] = attr.get("value", 0)

        return result

    def _parse_smart_text(self, output: str) -> Dict:
        """Parse SMART data from text format"""
        result = {}

        # Health status
        if "PASSED" in output:
            result["health_status"] = "PASSED"
        else:
            result["health_status"] = "FAILED"

        # Parse attributes with regex
        lines = output.split("\n")
        for line in lines:
            if "Temperature_Celsius" in line or "Current Temperature" in line:
                match = re.search(r"(\d+)", line)
                if match:
                    result["temperature"] = int(match.group(1))

            elif "Power_On_Hours" in line:
                match = re.search(r"\s+(\d+)$", line)
                if match:
                    result["power_on_hours"] = int(match.group(1))

            elif "Reallocated_Sector_Ct" in line:
                match = re.search(r"\s+(\d+)$", line)
                if match:
                    result["bad_sectors"] = int(match.group(1))

        return result

    def create_raid_array(
        self, config: RAIDConfiguration, pool_name: str, filesystem: str = "ext4"
    ) -> Tuple[bool, str]:
        """Create RAID array with enhanced configuration"""
        if "mdadm" not in self.tools:
            return False, "mdadm not available"

        # Validate configuration
        validation_error = self._validate_raid_config(config)
        if validation_error:
            return False, validation_error

        # Generate array device name
        array_device = self._get_next_md_device()
        if not array_device:
            return False, "No available MD devices"

        # Build mdadm command
        cmd = [
            self.tools["mdadm"],
            "--create",
            array_device,
            "--level",
            config.level.value,
            "--raid-devices",
            str(len(config.devices)),
            "--metadata",
            config.metadata_version,
        ]

        # Add chunk size for striped arrays
        if config.level in [RAIDLevel.RAID0, RAIDLevel.RAID5, RAIDLevel.RAID6, RAIDLevel.RAID10]:
            cmd.extend(["--chunk", str(config.chunk_size)])

        # Add bitmap for redundant arrays
        if config.bitmap and config.level in [RAIDLevel.RAID1, RAIDLevel.RAID5, RAIDLevel.RAID6]:
            cmd.append("--bitmap=internal")

        # Add spare devices
        if config.spare_devices:
            cmd.extend(["--spare-devices", str(len(config.spare_devices))])

        # Add assume-clean flag
        if config.assume_clean:
            cmd.append("--assume-clean")

        # Add all devices
        cmd.extend(config.devices + config.spare_devices)

        # Execute creation command
        success, stdout, stderr = self.run_command(cmd, timeout=300)
        if not success:
            return False, f"RAID creation failed: {stderr}"

        # Wait for array to become active
        if not self._wait_for_array_ready(array_device):
            return False, "Array did not become ready within timeout"

        # Create filesystem
        if filesystem != "none":
            success, error = self._create_filesystem(array_device, filesystem)
            if not success:
                return False, f"Filesystem creation failed: {error}"

        # Create database entries
        try:
            self._create_pool_database_entry(pool_name, config, array_device, filesystem)

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="storage",
                message=f"RAID array created successfully: {array_device}",
                details={
                    "pool_name": pool_name,
                    "raid_level": config.level.value,
                    "devices": config.devices,
                    "filesystem": filesystem,
                },
            )

            return True, array_device

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="storage",
                message=f"Failed to create database entries for RAID array: {e}",
                details={"array_device": array_device},
            )
            return False, f"Database error: {e}"

    def _validate_raid_config(self, config: RAIDConfiguration) -> Optional[str]:
        """Validate RAID configuration"""
        device_count = len(config.devices)

        # Check minimum device requirements
        min_devices = {
            RAIDLevel.RAID0: 2,
            RAIDLevel.RAID1: 2,
            RAIDLevel.RAID5: 3,
            RAIDLevel.RAID6: 4,
            RAIDLevel.RAID10: 4,
            RAIDLevel.JBOD: 1,
        }

        required = min_devices.get(config.level)
        if required and device_count < required:
            return f"RAID {config.level.value} requires at least {required} devices"

        # RAID 10 requires even number of devices
        if config.level == RAIDLevel.RAID10 and device_count % 2 != 0:
            return "RAID 10 requires an even number of devices"

        # Validate devices exist and are not in use
        for device in config.devices + config.spare_devices:
            if not os.path.exists(device):
                return f"Device {device} does not exist"

            if self._is_device_in_use(device):
                return f"Device {device} is already in use"

        return None

    def _is_device_in_use(self, device: str) -> bool:
        """Check if device is currently in use"""
        # Check if mounted
        success, stdout, stderr = self.run_command(["mount"])
        if success and device in stdout:
            return True

        # Check if part of existing RAID
        success, stdout, stderr = self.run_command([self.tools["mdadm"], "--examine", device])
        if success:
            return True

        # Check for partition table
        if "blkid" in self.tools:
            success, stdout, stderr = self.run_command([self.tools["blkid"], device])
            if success and stdout.strip():
                return True

        return False

    def _get_next_md_device(self) -> Optional[str]:
        """Get next available MD device"""
        for i in range(100):  # Check md0 through md99
            device = f"/dev/md{i}"
            if not os.path.exists(device):
                return device
        return None

    def _wait_for_array_ready(self, array_device: str, timeout: int = 60) -> bool:
        """Wait for RAID array to become ready"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if os.path.exists(array_device):
                # Check array status
                success, stdout, stderr = self.run_command(
                    [self.tools["mdadm"], "--detail", array_device]
                )

                if success and "State : clean" in stdout:
                    return True
                elif success and "State : active" in stdout:
                    return True

            time.sleep(2)

        return False

    def _create_filesystem(self, device: str, filesystem: str) -> Tuple[bool, str]:
        """Create filesystem on device"""
        if filesystem == "ext4" and "mkfs.ext4" in self.tools:
            cmd = [self.tools["mkfs.ext4"], "-F", device]
        elif filesystem == "xfs" and "mkfs.xfs" in self.tools:
            cmd = [self.tools["mkfs.xfs"], "-f", device]
        else:
            return False, f"Filesystem {filesystem} not supported"

        success, stdout, stderr = self.run_command(cmd, timeout=300)
        if not success:
            return False, stderr

        return True, "Filesystem created successfully"

    def _create_pool_database_entry(
        self, pool_name: str, config: RAIDConfiguration, array_device: str, filesystem: str
    ):
        """Create database entries for new storage pool"""
        # Create storage pool entry
        pool = StoragePool(
            name=pool_name,
            raid_level=config.level.value,
            filesystem_type=filesystem,
            mount_point=f"/mnt/{pool_name}",
            status=PoolStatus.HEALTHY,
            created_at=datetime.utcnow(),
        )

        db.session.add(pool)
        db.session.flush()  # Get pool ID

        # Create device entries
        for device_path in config.devices:
            device_info = self._device_cache.get(device_path)
            if device_info:
                device = StorageDevice(
                    device_path=device_path,
                    device_name=device_info.device_name,
                    device_model=device_info.model,
                    device_serial=device_info.serial,
                    device_size=device_info.size_bytes,
                    sector_size=device_info.sector_size,
                    pool_id=pool.id,
                    status=DeviceStatus.HEALTHY,
                )
                db.session.add(device)

        db.session.commit()

    def get_raid_status(self, array_device: str) -> Dict:
        """Get detailed RAID array status"""
        if "mdadm" not in self.tools:
            return {"error": "mdadm not available"}

        success, stdout, stderr = self.run_command([self.tools["mdadm"], "--detail", array_device])

        if not success:
            return {"error": f"Failed to get status: {stderr}"}

        return self._parse_mdadm_detail(stdout)

    def _parse_mdadm_detail(self, output: str) -> Dict:
        """Parse mdadm --detail output"""
        status = {}
        lines = output.split("\n")

        for line in lines:
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()

                if key == "state":
                    status["state"] = value
                elif key == "raid_level":
                    status["raid_level"] = value
                elif key == "array_size":
                    status["array_size"] = value
                elif key == "raid_devices":
                    status["raid_devices"] = int(value) if value.isdigit() else 0
                elif key == "spare_devices":
                    status["spare_devices"] = int(value) if value.isdigit() else 0
                elif key == "failed_devices":
                    status["failed_devices"] = int(value) if value.isdigit() else 0

        return status

    def monitor_storage_health(self):
        """Background thread for monitoring storage health"""
        self.monitoring_active = True

        while self.monitoring_active:
            try:
                # Update device SMART data
                self._update_smart_monitoring()

                # Check RAID array health
                self._check_raid_health()

                # Monitor I/O performance
                self._monitor_io_performance()

                # Sleep between checks
                time.sleep(60)  # Check every minute

            except Exception as e:
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="storage",
                    message=f"Storage monitoring error: {e}",
                )
                time.sleep(60)

    def start_monitoring(self):
        """Start storage health monitoring thread"""
        if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
            self.monitoring_thread = threading.Thread(
                target=self.monitor_storage_health, daemon=True
            )
            self.monitoring_thread.start()

            SystemLog.log_event(
                level=LogLevel.INFO, category="storage", message="Storage health monitoring started"
            )

    def stop_monitoring(self):
        """Stop storage health monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)

        SystemLog.log_event(
            level=LogLevel.INFO, category="storage", message="Storage health monitoring stopped"
        )

    def _update_smart_monitoring(self):
        """Update SMART data for all monitored devices"""
        devices = StorageDevice.query.all()

        for device in devices:
            if device.status != DeviceStatus.FAILED:
                smart_data = self._get_smart_data(device.device_path)
                if smart_data:
                    device.update_smart_data(smart_data)

        db.session.commit()

    def _check_raid_health(self):
        """Check health of all RAID arrays"""
        pools = StoragePool.query.all()

        for pool in pools:
            # Get array device (simplified - in production would track this)
            array_device = f"/dev/md/{pool.name}"
            if os.path.exists(array_device):
                status = self.get_raid_status(array_device)

                if "error" in status:
                    continue

                # Update pool status based on RAID state
                raid_state = status.get("state", "").lower()
                if "clean" in raid_state or "active" in raid_state:
                    pool.status = PoolStatus.HEALTHY
                elif "degraded" in raid_state:
                    pool.status = PoolStatus.DEGRADED
                elif "failed" in raid_state:
                    pool.status = PoolStatus.FAILED

        db.session.commit()

    def _monitor_io_performance(self):
        """Monitor I/O performance metrics"""
        try:
            io_counters = psutil.disk_io_counters(perdisk=True)
            current_time = time.time()

            for device, stats in io_counters.items():
                if device.startswith(("sd", "nvme", "md")):
                    # Store current stats
                    if device not in self.io_stats:
                        self.io_stats[device] = {
                            "last_update": current_time,
                            "last_read_bytes": stats.read_bytes,
                            "last_write_bytes": stats.write_bytes,
                            "last_read_count": stats.read_count,
                            "last_write_count": stats.write_count,
                        }
                    else:
                        # Calculate rates
                        prev = self.io_stats[device]
                        time_diff = current_time - prev["last_update"]

                        if time_diff > 0:
                            read_rate = (stats.read_bytes - prev["last_read_bytes"]) / time_diff
                            write_rate = (stats.write_bytes - prev["last_write_bytes"]) / time_diff

                            # Store performance history
                            if device not in self.performance_history:
                                self.performance_history[device] = []

                            self.performance_history[device].append(
                                {
                                    "timestamp": current_time,
                                    "read_rate": read_rate,
                                    "write_rate": write_rate,
                                    "read_iops": (stats.read_count - prev["last_read_count"])
                                    / time_diff,
                                    "write_iops": (stats.write_count - prev["last_write_count"])
                                    / time_diff,
                                }
                            )

                            # Keep only last 24 hours of data
                            cutoff = current_time - 86400
                            self.performance_history[device] = [
                                entry
                                for entry in self.performance_history[device]
                                if entry["timestamp"] > cutoff
                            ]

                        # Update stats
                        self.io_stats[device].update(
                            {
                                "last_update": current_time,
                                "last_read_bytes": stats.read_bytes,
                                "last_write_bytes": stats.write_bytes,
                                "last_read_count": stats.read_count,
                                "last_write_count": stats.write_count,
                            }
                        )

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.WARNING, category="storage", message=f"I/O monitoring error: {e}"
            )

    def get_performance_metrics(self, device: str, hours: int = 1) -> List[Dict]:
        """Get performance metrics for device"""
        if device not in self.performance_history:
            return []

        cutoff = time.time() - (hours * 3600)
        return [entry for entry in self.performance_history[device] if entry["timestamp"] > cutoff]


# Global instance
enhanced_storage_manager = EnhancedStorageManager()
