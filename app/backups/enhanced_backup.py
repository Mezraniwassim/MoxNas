"""
Enhanced Backup System for MoxNAS
Provides enterprise-grade backup capabilities with cloud integration,
encryption, compression, and automated verification
"""
import os
import re
import subprocess
import json
import hashlib
import gzip
import shutil
import boto3
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from app.models import BackupJob, BackupStatus, SourceType, DestinationType, SystemLog, LogLevel
from app import db, celery
from cryptography.fernet import Fernet
import tarfile
import tempfile


class BackupType(Enum):
    """Backup types"""

    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class CompressionType(Enum):
    """Compression algorithms"""

    NONE = "none"
    GZIP = "gzip"
    BZIP2 = "bzip2"
    XZ = "xz"
    ZSTD = "zstd"


class EncryptionType(Enum):
    """Encryption algorithms"""

    NONE = "none"
    AES256 = "aes256"
    FERNET = "fernet"
    GPG = "gpg"


class CloudProvider(Enum):
    """Cloud storage providers"""

    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"
    GOOGLE_CLOUD = "google_cloud"
    BACKBLAZE_B2 = "backblaze_b2"


@dataclass
class BackupConfig:
    """Enhanced backup configuration"""

    name: str
    source_path: str
    destination_path: str
    backup_type: BackupType = BackupType.INCREMENTAL
    compression: CompressionType = CompressionType.GZIP
    encryption: EncryptionType = EncryptionType.NONE
    encryption_key: str = None
    schedule: str = None  # Cron expression
    retention_days: int = 30
    retention_count: int = None  # Max number of backups to keep
    # Exclusions
    exclude_patterns: List[str] = None
    exclude_files: List[str] = None
    # Cloud storage
    cloud_provider: CloudProvider = None
    cloud_credentials: Dict[str, str] = None
    # Verification
    verify_backup: bool = True
    checksum_algorithm: str = "sha256"
    # Performance
    bandwidth_limit: str = None  # e.g., "10M" for 10MB/s
    io_nice_class: int = 2  # Idle priority
    cpu_nice: int = 19  # Lowest CPU priority
    # Notifications
    notify_on_success: bool = True
    notify_on_failure: bool = True
    notification_emails: List[str] = None
    # Advanced options
    follow_symlinks: bool = False
    preserve_hardlinks: bool = True
    preserve_acls: bool = True
    preserve_xattrs: bool = True
    delete_excluded: bool = False


@dataclass
class BackupMetadata:
    """Backup metadata for tracking"""

    backup_id: str
    job_name: str
    backup_type: BackupType
    start_time: datetime
    end_time: datetime = None
    source_path: str = None
    destination_path: str = None
    files_count: int = 0
    directories_count: int = 0
    bytes_transferred: int = 0
    compressed_size: int = 0
    compression_ratio: float = 0.0
    checksum: str = None
    checksum_algorithm: str = "sha256"
    encryption_used: bool = False
    status: BackupStatus = BackupStatus.RUNNING
    error_message: str = None
    parent_backup_id: str = None  # For incremental/differential


class EnhancedBackupManager:
    """Enhanced backup management system"""

    def __init__(self):
        self.tools = self._detect_backup_tools()
        self.metadata_dir = "/var/lib/moxnas/backups"
        self.temp_dir = "/tmp/moxnas_backups"
        self.encryption_keys = {}
        self._ensure_directories()

    def _detect_backup_tools(self) -> Dict[str, str]:
        """Detect backup tools and their paths"""
        tools = {}

        tool_paths = {
            "rsync": ["/usr/bin/rsync", "/bin/rsync"],
            "tar": ["/usr/bin/tar", "/bin/tar"],
            "gzip": ["/usr/bin/gzip", "/bin/gzip"],
            "bzip2": ["/usr/bin/bzip2", "/bin/bzip2"],
            "xz": ["/usr/bin/xz", "/bin/xz"],
            "zstd": ["/usr/bin/zstd", "/bin/zstd"],
            "gpg": ["/usr/bin/gpg", "/bin/gpg"],
            "aws": ["/usr/local/bin/aws", "/usr/bin/aws"],
            "gsutil": ["/usr/local/bin/gsutil", "/usr/bin/gsutil"],
            "az": ["/usr/local/bin/az", "/usr/bin/az"],
            "b2": ["/usr/local/bin/b2", "/usr/bin/b2"],
            "ionice": ["/usr/bin/ionice", "/bin/ionice"],
            "nice": ["/usr/bin/nice", "/bin/nice"],
            "pv": ["/usr/bin/pv", "/bin/pv"],  # Pipe viewer for progress
        }

        for tool, paths in tool_paths.items():
            for path in paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    tools[tool] = path
                    break

        return tools

    def _ensure_directories(self):
        """Ensure required directories exist"""
        for directory in [self.metadata_dir, self.temp_dir]:
            os.makedirs(directory, exist_ok=True)

    def create_backup_job(self, config: BackupConfig) -> Tuple[bool, str]:
        """Create new backup job"""
        try:
            # Validate configuration
            validation_error = self._validate_backup_config(config)
            if validation_error:
                return False, validation_error

            # Generate encryption key if needed
            if config.encryption != EncryptionType.NONE and not config.encryption_key:
                config.encryption_key = self._generate_encryption_key(config.encryption)

            # Create database entry
            job = BackupJob(
                name=config.name,
                source_type=SourceType.DIRECTORY,
                source_path=config.source_path,
                destination_type=self._get_destination_type(config),
                destination_path=config.destination_path,
                backup_type=config.backup_type.value,
                schedule=config.schedule,
                retention_days=config.retention_days,
                compression=config.compression != CompressionType.NONE,
                encryption=config.encryption != EncryptionType.NONE,
                is_active=True,
                created_at=datetime.utcnow(),
            )

            db.session.add(job)
            db.session.commit()

            # Store configuration metadata
            self._save_job_config(job.id, config)

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="backup",
                message=f"Backup job created: {config.name}",
                details={
                    "source": config.source_path,
                    "destination": config.destination_path,
                    "type": config.backup_type.value,
                },
            )

            return True, f"Backup job {config.name} created successfully"

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="backup",
                message=f"Failed to create backup job: {e}",
                details={"config": asdict(config)},
            )
            return False, str(e)

    @celery.task(bind=True)
    def run_backup_job_async(self, job_id: int):
        """Asynchronously execute backup job"""
        with celery.app.app_context():
            self.run_backup_job(job_id)

    def run_backup_job(self, job_id: int, is_async: bool = True) -> Tuple[bool, str]:
        """Execute backup job"""
        if is_async:
            self.run_backup_job_async.delay(job_id)
            return True, "Backup job started in the background"

        try:
            job = BackupJob.query.get(job_id)
            if not job:
                return False, f"Backup job {job_id} not found"

            config = self._load_job_config(job_id)
            if not config:
                return False, "Failed to load job configuration"

            # Update job status
            job.status = BackupStatus.RUNNING
            job.last_run = datetime.utcnow()
            db.session.commit()

            # Generate backup metadata
            metadata = BackupMetadata(
                backup_id=self._generate_backup_id(),
                job_name=job.name,
                backup_type=BackupType(config.backup_type),
                start_time=datetime.utcnow(),
                source_path=config.source_path,
                destination_path=self._resolve_destination_path(config),
            )

            # Determine parent backup for incremental/differential
            if config.backup_type in [BackupType.INCREMENTAL, BackupType.DIFFERENTIAL]:
                metadata.parent_backup_id = self._get_parent_backup_id(job_id, config.backup_type)

            # Execute backup based on type
            success, error_message = self._execute_backup(config, metadata)

            # Update metadata and job status
            metadata.end_time = datetime.utcnow()
            metadata.status = BackupStatus.COMPLETED if success else BackupStatus.FAILED
            metadata.error_message = error_message

            job.status = metadata.status
            if success:
                job.bytes_backed_up = metadata.bytes_transferred
            else:
                job.error_message = error_message

            db.session.commit()

            # Save metadata
            self._save_backup_metadata(metadata)

            # Send notifications
            if config.notify_on_success and success:
                self._send_notification(job, metadata, success=True)
            elif config.notify_on_failure and not success:
                self._send_notification(job, metadata, success=False)

            # Cleanup old backups
            if success:
                self._cleanup_old_backups(job_id, config)

            SystemLog.log_event(
                level=LogLevel.INFO if success else LogLevel.ERROR,
                category="backup",
                message=f'Backup job {"completed" if success else "failed"}: {job.name}',
                details={
                    "backup_id": metadata.backup_id,
                    "bytes_transferred": metadata.bytes_transferred,
                    "error": error_message if not success else None,
                },
            )

            return success, error_message or f"Backup completed successfully"

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="backup",
                message=f"Backup job execution failed: {e}",
                details={"job_id": job_id},
            )
            return False, str(e)

    def _execute_backup(
        self, config: BackupConfig, metadata: BackupMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Execute backup based on configuration"""
        try:
            if config.backup_type == BackupType.FULL:
                return self._execute_full_backup(config, metadata)
            elif config.backup_type == BackupType.INCREMENTAL:
                return self._execute_incremental_backup(config, metadata)
            elif config.backup_type == BackupType.DIFFERENTIAL:
                return self._execute_differential_backup(config, metadata)
            elif config.backup_type == BackupType.SNAPSHOT:
                return self._execute_snapshot_backup(config, metadata)
            else:
                return False, f"Unsupported backup type: {config.backup_type}"

        except Exception as e:
            return False, str(e)

    def _execute_full_backup(
        self, config: BackupConfig, metadata: BackupMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Execute full backup"""
        # Create temporary archive if compression/encryption is used
        if config.compression != CompressionType.NONE or config.encryption != EncryptionType.NONE:
            return self._execute_archive_backup(config, metadata)
        else:
            return self._execute_rsync_backup(config, metadata)

    def _execute_rsync_backup(
        self, config: BackupConfig, metadata: BackupMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Execute backup using rsync"""
        if "rsync" not in self.tools:
            return False, "rsync not available"

        cmd = [self.tools["rsync"]]

        # Basic options
        cmd.extend(["-av", "--progress", "--stats"])

        # Performance options
        if config.bandwidth_limit:
            cmd.extend(["--bwlimit", config.bandwidth_limit])

        # Preservation options
        if config.preserve_acls:
            cmd.append("-A")
        if config.preserve_xattrs:
            cmd.append("-X")
        if config.preserve_hardlinks:
            cmd.append("-H")

        # Symlink handling
        if config.follow_symlinks:
            cmd.append("-L")
        else:
            cmd.append("-l")

        # Exclusions
        if config.exclude_patterns:
            for pattern in config.exclude_patterns:
                cmd.extend(["--exclude", pattern])

        if config.exclude_files:
            for exclude_file in config.exclude_files:
                cmd.extend(["--exclude-from", exclude_file])

        # Delete excluded files
        if config.delete_excluded:
            cmd.append("--delete-excluded")

        # Add source and destination
        cmd.append(config.source_path + ("/" if not config.source_path.endswith("/") else ""))
        cmd.append(metadata.destination_path)

        # Execute with nice/ionice
        cmd = self._add_priority_control(cmd, config)

        success, stdout, stderr = self._run_backup_command(cmd)

        if success:
            # Parse rsync stats
            stats = self._parse_rsync_stats(stdout)
            metadata.files_count = stats.get("files_transferred", 0)
            metadata.bytes_transferred = stats.get("bytes_transferred", 0)

        return success, stderr if not success else None

    def _upload_to_s3(
        self, source_path: str, config: BackupConfig, metadata: BackupMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Upload backup to AWS S3"""
        try:
            if "aws" not in self.tools:
                return False, "AWS CLI not available"

            s3_path = f"s3://{config.destination_path}/{os.path.basename(source_path)}"

            cmd = [
                self.tools["aws"],
                "s3",
                "cp",
                source_path,
                s3_path,
                "--storage-class",
                "INTELLIGENT_TIERING",
                "--acl",
                "private",
            ]

            # Add credentials
            env = os.environ.copy()
            env["AWS_ACCESS_KEY_ID"] = config.cloud_credentials.get("aws_access_key_id")
            env["AWS_SECRET_ACCESS_KEY"] = config.cloud_credentials.get("aws_secret_access_key")
            env["AWS_DEFAULT_REGION"] = config.cloud_credentials.get("aws_region")

            success, stdout, stderr = self._run_backup_command(cmd, env=env)

            if success:
                metadata.destination_path = s3_path

            return success, stderr if not success else None

        except Exception as e:
            return False, str(e)

    def _execute_archive_backup(
        self, config: BackupConfig, metadata: BackupMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Execute backup creating compressed/encrypted archive"""
        try:
            # Create temporary archive
            with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as temp_file:
                temp_archive = temp_file.name

            # Create tar archive
            success, error = self._create_tar_archive(config, temp_archive, metadata)
            if not success:
                os.unlink(temp_archive)
                return False, error

            # Apply compression
            if config.compression != CompressionType.NONE:
                compressed_archive = temp_archive + f".{config.compression.value}"
                success, error = self._compress_archive(
                    temp_archive, compressed_archive, config.compression
                )
                os.unlink(temp_archive)
                if not success:
                    return False, error
                temp_archive = compressed_archive

            # Apply encryption
            if config.encryption != EncryptionType.NONE:
                encrypted_archive = temp_archive + ".enc"
                success, error = self._encrypt_archive(temp_archive, encrypted_archive, config)
                os.unlink(temp_archive)
                if not success:
                    return False, error
                temp_archive = encrypted_archive

            # Move to final destination or upload to cloud
            if config.cloud_provider == CloudProvider.AWS_S3:
                success, error = self._upload_to_s3(temp_archive, config, metadata)
                os.unlink(temp_archive)
                if not success:
                    return False, error
            else:
                final_path = os.path.join(
                    metadata.destination_path,
                    f"{metadata.backup_id}.tar"
                    + (
                        f".{config.compression.value}"
                        if config.compression != CompressionType.NONE
                        else ""
                    )
                    + (".enc" if config.encryption != EncryptionType.NONE else ""),
                )
                shutil.move(temp_archive, final_path)

            # Update metadata
            if not config.cloud_provider:
                metadata.compressed_size = os.path.getsize(final_path)
                if metadata.bytes_transferred > 0:
                    metadata.compression_ratio = (
                        metadata.compressed_size / metadata.bytes_transferred
                    )

                # Generate checksum
                if config.verify_backup:
                    metadata.checksum = self._calculate_file_checksum(
                        final_path, config.checksum_algorithm
                    )
                    metadata.checksum_algorithm = config.checksum_algorithm

            return True, None

        except Exception as e:
            return False, str(e)

    def _create_tar_archive(
        self, config: BackupConfig, archive_path: str, metadata: BackupMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Create tar archive from source directory"""
        try:
            files_count = 0
            dirs_count = 0
            bytes_count = 0

            with tarfile.open(archive_path, "w") as tar:
                for root, dirs, files in os.walk(config.source_path):
                    # Apply exclusion patterns
                    if self._should_exclude_path(root, config.exclude_patterns):
                        dirs.clear()  # Don't recurse into excluded directories
                        continue

                    dirs_count += len(dirs)

                    for file in files:
                        file_path = os.path.join(root, file)

                        if self._should_exclude_path(file_path, config.exclude_patterns):
                            continue

                        try:
                            # Get file info
                            file_stat = os.lstat(file_path)
                            bytes_count += file_stat.st_size
                            files_count += 1

                            # Add to archive
                            arcname = os.path.relpath(file_path, config.source_path)
                            tar.add(file_path, arcname=arcname, recursive=False)

                        except (OSError, IOError) as e:
                            SystemLog.log_event(
                                level=LogLevel.WARNING,
                                category="backup",
                                message=f"Failed to backup file: {file_path}",
                                details={"error": str(e)},
                            )

            metadata.files_count = files_count
            metadata.directories_count = dirs_count
            metadata.bytes_transferred = bytes_count

            return True, None

        except Exception as e:
            return False, str(e)

    def _compress_archive(
        self, source_path: str, dest_path: str, compression: CompressionType
    ) -> Tuple[bool, Optional[str]]:
        """Compress archive using specified algorithm"""
        try:
            if compression == CompressionType.GZIP and "gzip" in self.tools:
                cmd = [self.tools["gzip"], "-c", source_path]
                with open(dest_path, "wb") as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=False)
                return (
                    result.returncode == 0,
                    result.stderr.decode() if result.returncode != 0 else None,
                )

            elif compression == CompressionType.BZIP2 and "bzip2" in self.tools:
                cmd = [self.tools["bzip2"], "-c", source_path]
                with open(dest_path, "wb") as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=False)
                return (
                    result.returncode == 0,
                    result.stderr.decode() if result.returncode != 0 else None,
                )

            elif compression == CompressionType.XZ and "xz" in self.tools:
                cmd = [self.tools["xz"], "-c", source_path]
                with open(dest_path, "wb") as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=False)
                return (
                    result.returncode == 0,
                    result.stderr.decode() if result.returncode != 0 else None,
                )

            elif compression == CompressionType.ZSTD and "zstd" in self.tools:
                cmd = [self.tools["zstd"], "-c", source_path]
                with open(dest_path, "wb") as f:
                    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=False)
                return (
                    result.returncode == 0,
                    result.stderr.decode() if result.returncode != 0 else None,
                )

            else:
                return False, f"Compression {compression.value} not available"

        except Exception as e:
            return False, str(e)

    def _encrypt_archive(
        self, source_path: str, dest_path: str, config: BackupConfig
    ) -> Tuple[bool, Optional[str]]:
        """Encrypt archive using specified algorithm"""
        try:
            if config.encryption == EncryptionType.FERNET:
                # Use Fernet encryption
                key = (
                    config.encryption_key.encode()
                    if isinstance(config.encryption_key, str)
                    else config.encryption_key
                )
                f = Fernet(key)

                with open(source_path, "rb") as src, open(dest_path, "wb") as dst:
                    # Read and encrypt in chunks to handle large files
                    while True:
                        chunk = src.read(8192)
                        if not chunk:
                            break
                        encrypted_chunk = f.encrypt(chunk)
                        dst.write(encrypted_chunk)

                return True, None

            elif config.encryption == EncryptionType.GPG and "gpg" in self.tools:
                cmd = [
                    self.tools["gpg"],
                    "--cipher-algo",
                    "AES256",
                    "--compress-algo",
                    "2",
                    "--symmetric",
                    "--passphrase",
                    config.encryption_key,
                    "--batch",
                    "--yes",
                    "--quiet",
                    "--output",
                    dest_path,
                    source_path,
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0, result.stderr if result.returncode != 0 else None

            else:
                return False, f"Encryption {config.encryption.value} not available"

        except Exception as e:
            return False, str(e)

    def _should_exclude_path(self, path: str, exclude_patterns: List[str]) -> bool:
        """Check if path should be excluded based on patterns"""
        if not exclude_patterns:
            return False

        import fnmatch

        for pattern in exclude_patterns:
            if fnmatch.fnmatch(path, pattern):
                return True

        return False

    def _add_priority_control(self, cmd: List[str], config: BackupConfig) -> List[str]:
        """Add nice and ionice to command for priority control"""
        if "nice" in self.tools:
            cmd = [self.tools["nice"], "-n", str(config.cpu_nice)] + cmd

        if "ionice" in self.tools:
            cmd = [self.tools["ionice"], "-c", str(config.io_nice_class)] + cmd

        return cmd

    def _run_backup_command(self, cmd: List[str], timeout: int = 3600) -> Tuple[bool, str, str]:
        """Run backup command with timeout"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Backup command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def _parse_rsync_stats(self, output: str) -> Dict[str, int]:
        """Parse rsync statistics from output"""
        stats = {}

        patterns = {
            "files_transferred": r"Number of files transferred: (\d+)",
            "bytes_transferred": r"Total transferred file size: (\d+)",
            "files_created": r"Number of created files: (\d+)",
            "files_deleted": r"Number of deleted files: (\d+)",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                stats[key] = int(match.group(1))

        return stats

    def _calculate_file_checksum(self, file_path: str, algorithm: str = "sha256") -> str:
        """Calculate file checksum"""
        hash_func = getattr(hashlib, algorithm)()

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hash_func.update(chunk)

        return hash_func.hexdigest()

    def _generate_backup_id(self) -> str:
        """Generate unique backup ID"""
        return f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

    def _generate_encryption_key(self, encryption_type: EncryptionType) -> str:
        """Generate encryption key"""
        if encryption_type == EncryptionType.FERNET:
            return Fernet.generate_key().decode()
        elif encryption_type == EncryptionType.AES256:
            return os.urandom(32).hex()
        else:
            return os.urandom(32).hex()

    def _validate_backup_config(self, config: BackupConfig) -> Optional[str]:
        """Validate backup configuration"""
        if not os.path.exists(config.source_path):
            return f"Source path does not exist: {config.source_path}"

        if not os.path.isdir(config.source_path):
            return f"Source path is not a directory: {config.source_path}"

        # Validate destination based on type
        if config.cloud_provider:
            if not config.cloud_credentials:
                return "Cloud credentials required for cloud backup"
        else:
            dest_dir = os.path.dirname(config.destination_path)
            if not os.path.exists(dest_dir):
                try:
                    os.makedirs(dest_dir, exist_ok=True)
                except Exception as e:
                    return f"Cannot create destination directory: {e}"

        return None

    def _get_destination_type(self, config: BackupConfig) -> DestinationType:
        """Determine destination type from configuration"""
        if config.cloud_provider:
            if config.cloud_provider == CloudProvider.AWS_S3:
                return DestinationType.S3
            else:
                return DestinationType.REMOTE
        else:
            return DestinationType.DIRECTORY

    def _resolve_destination_path(self, config: BackupConfig) -> str:
        """Resolve actual destination path"""
        if config.cloud_provider:
            return config.destination_path  # Cloud path as-is
        else:
            # Local path with timestamp directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return os.path.join(config.destination_path, f"{config.name}_{timestamp}")

    def _save_job_config(self, job_id: int, config: BackupConfig):
        """Save job configuration to metadata"""
        config_path = os.path.join(self.metadata_dir, f"job_{job_id}_config.json")
        with open(config_path, "w") as f:
            # Convert dataclass to dict, handling enums
            config_dict = asdict(config)
            for key, value in config_dict.items():
                if hasattr(value, "value"):  # Enum
                    config_dict[key] = value.value
            json.dump(config_dict, f, indent=2, default=str)

    def _load_job_config(self, job_id: int) -> Optional[BackupConfig]:
        """Load job configuration from metadata"""
        config_path = os.path.join(self.metadata_dir, f"job_{job_id}_config.json")
        try:
            with open(config_path, "r") as f:
                config_dict = json.load(f)

            # Convert back to proper types
            if "backup_type" in config_dict:
                config_dict["backup_type"] = BackupType(config_dict["backup_type"])
            if "compression" in config_dict:
                config_dict["compression"] = CompressionType(config_dict["compression"])
            if "encryption" in config_dict:
                config_dict["encryption"] = EncryptionType(config_dict["encryption"])
            if "cloud_provider" in config_dict and config_dict["cloud_provider"]:
                config_dict["cloud_provider"] = CloudProvider(config_dict["cloud_provider"])

            return BackupConfig(**config_dict)

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="backup",
                message=f"Failed to load job config: {e}",
                details={"job_id": job_id},
            )
            return None

    def _save_backup_metadata(self, metadata: BackupMetadata):
        """Save backup metadata"""
        metadata_path = os.path.join(self.metadata_dir, f"{metadata.backup_id}_metadata.json")
        with open(metadata_path, "w") as f:
            # Convert dataclass to dict
            metadata_dict = asdict(metadata)
            json.dump(metadata_dict, f, indent=2, default=str)


# Global enhanced backup manager instance
enhanced_backup_manager = EnhancedBackupManager()
