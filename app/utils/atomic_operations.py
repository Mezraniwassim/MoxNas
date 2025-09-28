"""
Atomic file operations for MoxNAS
Provides safe, atomic file and directory operations to prevent data corruption
"""
import os
import shutil
import tempfile
import fcntl
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Union, Generator, Optional
from app.models import SystemLog, LogLevel
from app.utils.error_handler import handle_file_operation_errors


class AtomicFileOperations:
    """Provides atomic file operations to ensure data integrity"""

    @staticmethod
    @handle_file_operation_errors
    def atomic_write(
        file_path: Union[str, Path], content: str, encoding: str = "utf-8"
    ) -> tuple[bool, str]:
        """
        Atomically write content to a file
        Uses a temporary file and atomic rename to ensure consistency
        """
        file_path = Path(file_path)
        temp_file = None

        try:
            # Create temporary file in the same directory for atomic rename
            temp_dir = file_path.parent
            temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                encoding=encoding,
                dir=temp_dir,
                delete=False,
                prefix=f".{file_path.name}.",
                suffix=".tmp",
            )

            # Write content to temporary file
            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())  # Force write to disk
            temp_file.close()

            # Set proper permissions before rename
            if file_path.exists():
                # Copy existing file permissions
                stat_info = file_path.stat()
                os.chmod(temp_file.name, stat_info.st_mode)
                os.chown(temp_file.name, stat_info.st_uid, stat_info.st_gid)
            else:
                # Set default secure permissions
                os.chmod(temp_file.name, 0o644)

            # Atomic rename
            os.rename(temp_file.name, file_path)

            SystemLog.log_event(
                level=LogLevel.DEBUG,
                category="file_operations",
                message=f"Atomic write completed: {file_path}",
            )

            return True, f"File written successfully: {file_path}"

        except Exception as e:
            # Clean up temporary file on error
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="file_operations",
                message=f"Atomic write failed: {file_path}, error: {e}",
            )

            return False, f"Failed to write file: {str(e)}"

    @staticmethod
    @handle_file_operation_errors
    def atomic_copy(
        source: Union[str, Path], destination: Union[str, Path], preserve_metadata: bool = True
    ) -> tuple[bool, str]:
        """
        Atomically copy a file
        Uses temporary file and atomic rename
        """
        source = Path(source)
        destination = Path(destination)

        if not source.exists():
            return False, f"Source file does not exist: {source}"

        if not source.is_file():
            return False, f"Source is not a file: {source}"

        try:
            # Create temporary file in destination directory
            temp_dir = destination.parent
            temp_file = tempfile.NamedTemporaryFile(
                dir=temp_dir, delete=False, prefix=f".{destination.name}.", suffix=".tmp"
            )
            temp_file.close()

            # Copy file content
            if preserve_metadata:
                shutil.copy2(source, temp_file.name)
            else:
                shutil.copy(source, temp_file.name)

            # Atomic rename
            os.rename(temp_file.name, destination)

            SystemLog.log_event(
                level=LogLevel.DEBUG,
                category="file_operations",
                message=f"Atomic copy completed: {source} -> {destination}",
            )

            return True, f"File copied successfully: {source} -> {destination}"

        except Exception as e:
            # Clean up temporary file on error
            if "temp_file" in locals() and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="file_operations",
                message=f"Atomic copy failed: {source} -> {destination}, error: {e}",
            )

            return False, f"Failed to copy file: {str(e)}"

    @staticmethod
    @handle_file_operation_errors
    def atomic_move(source: Union[str, Path], destination: Union[str, Path]) -> tuple[bool, str]:
        """
        Atomically move a file
        Uses atomic rename when possible, falls back to copy+delete for cross-device moves
        """
        source = Path(source)
        destination = Path(destination)

        if not source.exists():
            return False, f"Source file does not exist: {source}"

        try:
            # Try atomic rename first (same filesystem)
            os.rename(source, destination)

            SystemLog.log_event(
                level=LogLevel.DEBUG,
                category="file_operations",
                message=f"Atomic move completed: {source} -> {destination}",
            )

            return True, f"File moved successfully: {source} -> {destination}"

        except OSError as e:
            # If rename fails due to cross-device link, use copy+delete
            if e.errno == 18:  # EXDEV - Cross-device link
                # Use atomic copy then delete original
                success, message = AtomicFileOperations.atomic_copy(
                    source, destination, preserve_metadata=True
                )
                if success:
                    try:
                        os.unlink(source)
                        return (
                            True,
                            f"File moved successfully (cross-device): {source} -> {destination}",
                        )
                    except Exception as del_error:
                        # Copy succeeded but delete failed - log warning but don't fail
                        SystemLog.log_event(
                            level=LogLevel.WARNING,
                            category="file_operations",
                            message=f"Move completed but failed to delete source: {source}, error: {del_error}",
                        )
                        return (
                            True,
                            f"File copied but original not deleted: {source} -> {destination}",
                        )
                else:
                    return False, f"Failed to move file: {message}"
            else:
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="file_operations",
                    message=f"Atomic move failed: {source} -> {destination}, error: {e}",
                )
                return False, f"Failed to move file: {str(e)}"

    @staticmethod
    @handle_file_operation_errors
    def safe_delete(file_path: Union[str, Path], backup: bool = True) -> tuple[bool, str]:
        """
        Safely delete a file with optional backup
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return True, f"File already does not exist: {file_path}"

        try:
            if backup:
                # Create backup before deletion
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup.{int(time.time())}")
                success, message = AtomicFileOperations.atomic_copy(file_path, backup_path)
                if not success:
                    return False, f"Failed to create backup before deletion: {message}"

            # Delete the file
            os.unlink(file_path)

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="file_operations",
                message=f"File deleted: {file_path}"
                + (f" (backup created: {backup_path})" if backup else ""),
            )

            return True, f"File deleted successfully: {file_path}"

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="file_operations",
                message=f"Safe delete failed: {file_path}, error: {e}",
            )
            return False, f"Failed to delete file: {str(e)}"


class AtomicDirectoryOperations:
    """Provides atomic directory operations"""

    @staticmethod
    @handle_file_operation_errors
    def atomic_create_directory(dir_path: Union[str, Path], mode: int = 0o755) -> tuple[bool, str]:
        """
        Atomically create a directory with proper permissions
        """
        dir_path = Path(dir_path)

        try:
            # Create directory with parents if needed
            dir_path.mkdir(mode=mode, parents=True, exist_ok=True)

            # Ensure correct permissions
            os.chmod(dir_path, mode)

            SystemLog.log_event(
                level=LogLevel.DEBUG,
                category="file_operations",
                message=f"Directory created: {dir_path}",
            )

            return True, f"Directory created successfully: {dir_path}"

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="file_operations",
                message=f"Directory creation failed: {dir_path}, error: {e}",
            )
            return False, f"Failed to create directory: {str(e)}"

    @staticmethod
    @handle_file_operation_errors
    def safe_remove_directory(
        dir_path: Union[str, Path], recursive: bool = False
    ) -> tuple[bool, str]:
        """
        Safely remove a directory
        """
        dir_path = Path(dir_path)

        if not dir_path.exists():
            return True, f"Directory already does not exist: {dir_path}"

        if not dir_path.is_dir():
            return False, f"Path is not a directory: {dir_path}"

        try:
            if recursive:
                shutil.rmtree(dir_path)
            else:
                os.rmdir(dir_path)  # Only removes empty directories

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="file_operations",
                message=f"Directory removed: {dir_path}" + (" (recursive)" if recursive else ""),
            )

            return True, f"Directory removed successfully: {dir_path}"

        except OSError as e:
            if e.errno == 39:  # Directory not empty
                return False, f"Directory not empty: {dir_path}"
            else:
                SystemLog.log_event(
                    level=LogLevel.ERROR,
                    category="file_operations",
                    message=f"Directory removal failed: {dir_path}, error: {e}",
                )
                return False, f"Failed to remove directory: {str(e)}"


@contextmanager
def file_lock(file_path: Union[str, Path], timeout: float = 30.0) -> Generator[None, None, None]:
    """
    Context manager for file locking to prevent concurrent access
    """
    file_path = Path(file_path)
    lock_file = file_path.with_suffix(f"{file_path.suffix}.lock")

    lock_fd = None
    try:
        # Create lock file
        lock_fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)

        # Try to acquire exclusive lock with timeout
        start_time = time.time()
        while True:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except IOError:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not acquire file lock within {timeout} seconds")
                time.sleep(0.1)

        SystemLog.log_event(
            level=LogLevel.DEBUG,
            category="file_operations",
            message=f"File lock acquired: {file_path}",
        )

        yield

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="file_operations",
            message=f"File lock error: {file_path}, error: {e}",
        )
        raise
    finally:
        # Release lock and clean up
        if lock_fd is not None:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)
            except:
                pass

        # Remove lock file
        try:
            if lock_file.exists():
                os.unlink(lock_file)
        except:
            pass

        SystemLog.log_event(
            level=LogLevel.DEBUG,
            category="file_operations",
            message=f"File lock released: {file_path}",
        )


class ConfigurationManager:
    """Manages configuration files with atomic operations and versioning"""

    def __init__(self, config_path: Union[str, Path]):
        self.config_path = Path(config_path)
        self.backup_dir = self.config_path.parent / "config_backups"
        self.backup_dir.mkdir(exist_ok=True)

    def backup_config(self) -> tuple[bool, str]:
        """Create a timestamped backup of the configuration file"""
        if not self.config_path.exists():
            return False, "Configuration file does not exist"

        timestamp = int(time.time())
        backup_name = f"{self.config_path.name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name

        return AtomicFileOperations.atomic_copy(self.config_path, backup_path)

    def atomic_update_config(self, content: str) -> tuple[bool, str]:
        """Atomically update configuration with backup"""
        try:
            with file_lock(self.config_path):
                # Create backup first
                if self.config_path.exists():
                    success, message = self.backup_config()
                    if not success:
                        return False, f"Failed to create backup: {message}"

                # Atomically write new configuration
                return AtomicFileOperations.atomic_write(self.config_path, content)

        except Exception as e:
            return False, f"Failed to update configuration: {str(e)}"

    def rollback_to_backup(self, backup_timestamp: Optional[int] = None) -> tuple[bool, str]:
        """Rollback configuration to a previous backup"""
        try:
            if backup_timestamp:
                backup_name = f"{self.config_path.name}.{backup_timestamp}.backup"
            else:
                # Find most recent backup
                backups = sorted(
                    [f for f in self.backup_dir.glob(f"{self.config_path.name}.*.backup")]
                )
                if not backups:
                    return False, "No backups found"
                backup_name = backups[-1].name

            backup_path = self.backup_dir / backup_name
            if not backup_path.exists():
                return False, f"Backup not found: {backup_name}"

            with file_lock(self.config_path):
                return AtomicFileOperations.atomic_copy(backup_path, self.config_path)

        except Exception as e:
            return False, f"Failed to rollback configuration: {str(e)}"
