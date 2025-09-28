"""
Enhanced Network Protocol Support for MoxNAS
Provides enterprise-grade SMB/CIFS, NFS, and FTP functionality
"""
import os
import subprocess
import re
import json
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from app.models import Share, ShareProtocol, ShareStatus, SystemLog, LogLevel, User
from app import db


class SMBProtocolVersion(Enum):
    """SMB protocol versions"""

    SMB1 = "SMB1"
    SMB2 = "SMB2"
    SMB2_02 = "SMB2_02"
    SMB2_10 = "SMB2_10"
    SMB3 = "SMB3"
    SMB3_00 = "SMB3_00"
    SMB3_02 = "SMB3_02"
    SMB3_11 = "SMB3_11"


class NFSVersion(Enum):
    """NFS protocol versions"""

    NFSv3 = "3"
    NFSv4 = "4"
    NFSv4_0 = "4.0"
    NFSv4_1 = "4.1"
    NFSv4_2 = "4.2"


@dataclass
class SMBShareConfig:
    """SMB share configuration"""

    name: str
    path: str
    comment: str = ""
    browseable: bool = True
    writable: bool = True
    read_only: bool = False
    guest_ok: bool = False
    valid_users: List[str] = None
    invalid_users: List[str] = None
    admin_users: List[str] = None
    hosts_allow: List[str] = None
    hosts_deny: List[str] = None
    create_mask: str = "0755"
    directory_mask: str = "0755"
    force_user: str = None
    force_group: str = None
    inherit_acls: bool = True
    inherit_permissions: bool = False
    store_dos_attributes: bool = True
    map_archive: bool = False
    map_hidden: bool = False
    map_readonly: bool = False
    map_system: bool = False
    vfs_objects: List[str] = None
    fruit_metadata: str = "stream"  # For macOS compatibility
    fruit_locking: str = "netatalk"
    fruit_encoding: str = "native"
    # Performance options
    socket_options: str = "TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=131072 SO_SNDBUF=131072"
    read_raw: bool = True
    write_raw: bool = True
    max_connections: int = 0  # 0 = unlimited
    deadtime: int = 0  # Minutes of inactivity before disconnect
    # Security options
    server_signing: str = "auto"  # auto, mandatory, disabled
    client_signing: str = "auto"
    smb_encrypt: str = "off"  # off, desired, required
    # Auditing
    full_audit: bool = False
    audit_prefix: str = "%u|%I"


@dataclass
class NFSExportConfig:
    """NFS export configuration"""

    path: str
    clients: List[str] = None  # Client specifications
    options: Dict[str, Any] = None
    # Access control
    rw: bool = True  # Read-write access
    ro: bool = False  # Read-only access
    sync: bool = True  # Synchronous writes
    async_mode: bool = False  # Asynchronous writes (performance vs safety)
    # Root access
    root_squash: bool = True  # Map root user to anonymous
    no_root_squash: bool = False  # Don't map root user
    all_squash: bool = False  # Map all users to anonymous
    # User mapping
    anonuid: int = None  # Anonymous UID
    anongid: int = None  # Anonymous GID
    # Security
    sec: List[str] = None  # Security flavors (sys, krb5, krb5i, krb5p)
    # Performance
    wdelay: bool = True  # Write delay optimization
    no_wdelay: bool = False  # Disable write delay
    subtree_check: bool = False  # Subtree checking
    no_subtree_check: bool = True  # Disable subtree checking
    # Protocol versions
    nfsvers: List[str] = None  # Allowed NFS versions
    # Extended attributes
    no_acl: bool = False  # Disable ACL support


class EnhancedSMBManager:
    """Enhanced SMB/CIFS management with enterprise features"""

    def __init__(self):
        self.tools = self._detect_samba_tools()
        self.config_file = "/etc/samba/smb.conf"
        self.backup_config_file = "/etc/samba/smb.conf.backup"
        self.testparm_cmd = self.tools.get("testparm")

    def _detect_samba_tools(self) -> Dict[str, str]:
        """Detect Samba tools and their paths"""
        tools = {}

        tool_paths = {
            "smbd": ["/usr/sbin/smbd", "/sbin/smbd"],
            "nmbd": ["/usr/sbin/nmbd", "/sbin/nmbd"],
            "smbcontrol": ["/usr/bin/smbcontrol", "/bin/smbcontrol"],
            "smbstatus": ["/usr/bin/smbstatus", "/bin/smbstatus"],
            "smbpasswd": ["/usr/bin/smbpasswd", "/bin/smbpasswd"],
            "pdbedit": ["/usr/bin/pdbedit", "/bin/pdbedit"],
            "testparm": ["/usr/bin/testparm", "/bin/testparm"],
            "net": ["/usr/bin/net", "/bin/net"],
            "smbclient": ["/usr/bin/smbclient", "/bin/smbclient"],
            "systemctl": ["/bin/systemctl", "/usr/bin/systemctl"],
        }

        for tool, paths in tool_paths.items():
            for path in paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    tools[tool] = path
                    break

        return tools

    def run_command(self, command: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """Execute system command with error handling"""
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout, check=False
            )

            success = result.returncode == 0
            if not success:
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category="shares",
                    message=f'SMB command failed: {" ".join(command)}',
                    details={"return_code": result.returncode, "stderr": result.stderr},
                )

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def create_smb_share(self, config: SMBShareConfig) -> Tuple[bool, str]:
        """Create SMB share with advanced configuration"""
        try:
            # Import input sanitizer
            from app.security.hardening import InputSanitizer

            # Validate input parameters
            if not InputSanitizer.validate_smb_share_name(config.name):
                return False, "Invalid share name format"

            if not InputSanitizer.validate_nfs_path(config.path):
                return False, "Invalid share path format"

            if (
                hasattr(config, "comment")
                and config.comment
                and not InputSanitizer.validate_smb_comment(config.comment)
            ):
                return False, "Invalid share comment format"

            # Validate path exists and is accessible
            if not os.path.exists(config.path):
                return False, f"Share path does not exist: {config.path}"

            if not os.access(config.path, os.R_OK):
                return False, f"Share path is not readable: {config.path}"

            # Backup current configuration
            self._backup_smb_config()

            # Generate share configuration
            share_config = self._generate_smb_share_config(config)

            # Add to smb.conf
            success = self._add_smb_share_to_config(config.name, share_config)
            if not success:
                return False, "Failed to update SMB configuration"

            # Test configuration
            if not self._test_smb_config():
                self._restore_smb_config()
                return False, "SMB configuration validation failed"

            # Reload SMB service
            success = self._reload_smb_service()
            if not success:
                self._restore_smb_config()
                return False, "Failed to reload SMB service"

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="shares",
                message=f"SMB share created: {config.name}",
                details={"path": config.path, "writable": config.writable},
            )

            return True, f"SMB share {config.name} created successfully"

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="shares",
                message=f"Failed to create SMB share: {e}",
                details={"share_name": getattr(config, "name", "unknown")},
            )
            return False, str(e)

    def _generate_smb_share_config(self, config: SMBShareConfig) -> List[str]:
        """Generate SMB share configuration lines"""
        lines = [f"[{config.name}]"]

        # Basic settings
        lines.append(f"   path = {config.path}")
        if config.comment:
            lines.append(f"   comment = {config.comment}")

        # Access control
        lines.append(f"   browseable = {'yes' if config.browseable else 'no'}")
        lines.append(f"   writable = {'yes' if config.writable else 'no'}")
        lines.append(f"   read only = {'yes' if config.read_only else 'no'}")
        lines.append(f"   guest ok = {'yes' if config.guest_ok else 'no'}")

        # User access
        if config.valid_users:
            lines.append(f"   valid users = {' '.join(config.valid_users)}")
        if config.invalid_users:
            lines.append(f"   invalid users = {' '.join(config.invalid_users)}")
        if config.admin_users:
            lines.append(f"   admin users = {' '.join(config.admin_users)}")

        # Host access
        if config.hosts_allow:
            lines.append(f"   hosts allow = {' '.join(config.hosts_allow)}")
        if config.hosts_deny:
            lines.append(f"   hosts deny = {' '.join(config.hosts_deny)}")

        # File permissions
        lines.append(f"   create mask = {config.create_mask}")
        lines.append(f"   directory mask = {config.directory_mask}")

        if config.force_user:
            lines.append(f"   force user = {config.force_user}")
        if config.force_group:
            lines.append(f"   force group = {config.force_group}")

        # ACL and permissions
        lines.append(f"   inherit acls = {'yes' if config.inherit_acls else 'no'}")
        lines.append(f"   inherit permissions = {'yes' if config.inherit_permissions else 'no'}")
        lines.append(f"   store dos attributes = {'yes' if config.store_dos_attributes else 'no'}")

        # DOS attribute mapping
        lines.append(f"   map archive = {'yes' if config.map_archive else 'no'}")
        lines.append(f"   map hidden = {'yes' if config.map_hidden else 'no'}")
        lines.append(f"   map readonly = {'yes' if config.map_readonly else 'no'}")
        lines.append(f"   map system = {'yes' if config.map_system else 'no'}")

        # VFS objects
        vfs_objects = config.vfs_objects or []
        if config.full_audit:
            vfs_objects.append(f"full_audit")
            lines.append(f"   full_audit:prefix = {config.audit_prefix}")
            lines.append("   full_audit:success = open opendir write unlink mkdir rmdir rename")
            lines.append("   full_audit:failure = all")

        # macOS support
        vfs_objects.extend(["fruit", "streams_xattr"])
        lines.append(f"   fruit:metadata = {config.fruit_metadata}")
        lines.append(f"   fruit:locking = {config.fruit_locking}")
        lines.append(f"   fruit:encoding = {config.fruit_encoding}")

        if vfs_objects:
            lines.append(f"   vfs objects = {' '.join(vfs_objects)}")

        # Performance settings
        if config.socket_options:
            lines.append(f"   socket options = {config.socket_options}")
        lines.append(f"   read raw = {'yes' if config.read_raw else 'no'}")
        lines.append(f"   write raw = {'yes' if config.write_raw else 'no'}")

        if config.max_connections > 0:
            lines.append(f"   max connections = {config.max_connections}")
        if config.deadtime > 0:
            lines.append(f"   deadtime = {config.deadtime}")

        # Security settings
        lines.append(f"   server signing = {config.server_signing}")
        lines.append(f"   client signing = {config.client_signing}")
        lines.append(f"   smb encrypt = {config.smb_encrypt}")

        return lines

    def _add_smb_share_to_config(self, share_name: str, config_lines: List[str]) -> bool:
        """Add share configuration to smb.conf"""
        try:
            # Read current configuration
            with open(self.config_file, "r") as f:
                content = f.read()

            # Remove existing share if present
            content = self._remove_smb_share_from_config(content, share_name)

            # Add new share configuration
            content += "\n\n" + "\n".join(config_lines) + "\n"

            # Write back to file
            with open(self.config_file, "w") as f:
                f.write(content)

            return True

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="shares",
                message=f"Failed to update SMB configuration: {e}",
            )
            return False

    def _remove_smb_share_from_config(self, content: str, share_name: str) -> str:
        """Remove share section from SMB configuration"""
        lines = content.split("\n")
        result_lines = []
        in_share_section = False

        for line in lines:
            if line.strip().startswith(f"[{share_name}]"):
                in_share_section = True
                continue
            elif line.strip().startswith("[") and line.strip().endswith("]"):
                in_share_section = False

            if not in_share_section:
                result_lines.append(line)

        return "\n".join(result_lines)

    def _test_smb_config(self) -> bool:
        """Test SMB configuration validity"""
        if not self.testparm_cmd:
            return True  # Skip if testparm not available

        success, stdout, stderr = self.run_command([self.testparm_cmd, "-s", self.config_file])

        return success

    def _backup_smb_config(self):
        """Backup current SMB configuration"""
        try:
            if os.path.exists(self.config_file):
                subprocess.run(["cp", self.config_file, self.backup_config_file], check=True)
        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category="shares",
                message=f"Failed to backup SMB config: {e}",
            )

    def _restore_smb_config(self):
        """Restore SMB configuration from backup"""
        try:
            if os.path.exists(self.backup_config_file):
                subprocess.run(["cp", self.backup_config_file, self.config_file], check=True)
        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="shares",
                message=f"Failed to restore SMB config: {e}",
            )

    def _reload_smb_service(self) -> bool:
        """Reload SMB service"""
        if "systemctl" not in self.tools:
            return False

        # Try to reload, then restart if reload fails
        success, stdout, stderr = self.run_command([self.tools["systemctl"], "reload", "smbd"])

        if not success:
            success, stdout, stderr = self.run_command([self.tools["systemctl"], "restart", "smbd"])

        return success

    def get_smb_status(self) -> Dict:
        """Get SMB service status and connections"""
        status = {"service_status": "unknown", "connections": []}

        # Check service status
        if "systemctl" in self.tools:
            success, stdout, stderr = self.run_command(
                [self.tools["systemctl"], "is-active", "smbd"]
            )
            status["service_status"] = stdout.strip() if success else "inactive"

        # Get active connections
        if "smbstatus" in self.tools:
            success, stdout, stderr = self.run_command([self.tools["smbstatus"], "-b"])
            if success:
                status["connections"] = self._parse_smb_connections(stdout)

        return status

    def _parse_smb_connections(self, output: str) -> List[Dict]:
        """Parse smbstatus output for connection information"""
        connections = []
        lines = output.split("\n")

        in_connections = False
        for line in lines:
            if "PID" in line and "Username" in line:
                in_connections = True
                continue
            elif in_connections and line.strip():
                parts = line.split()
                if len(parts) >= 7:
                    connections.append(
                        {
                            "pid": parts[0],
                            "username": parts[1],
                            "group": parts[2],
                            "machine": parts[3],
                            "protocol": parts[4],
                            "encryption": parts[5],
                            "signing": parts[6],
                        }
                    )

        return connections


class EnhancedNFSManager:
    """Enhanced NFS management with enterprise features"""

    def __init__(self):
        self.tools = self._detect_nfs_tools()
        self.exports_file = "/etc/exports"
        self.backup_exports_file = "/etc/exports.backup"

    def _detect_nfs_tools(self) -> Dict[str, str]:
        """Detect NFS tools and their paths"""
        tools = {}

        tool_paths = {
            "exportfs": ["/usr/sbin/exportfs", "/sbin/exportfs"],
            "showmount": ["/usr/sbin/showmount", "/sbin/showmount"],
            "nfsstat": ["/usr/sbin/nfsstat", "/sbin/nfsstat"],
            "rpc.nfsd": ["/usr/sbin/rpc.nfsd", "/sbin/rpc.nfsd"],
            "rpc.mountd": ["/usr/sbin/rpc.mountd", "/sbin/rpc.mountd"],
            "systemctl": ["/bin/systemctl", "/usr/bin/systemctl"],
            "service": ["/usr/sbin/service", "/sbin/service"],
        }

        for tool, paths in tool_paths.items():
            for path in paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    tools[tool] = path
                    break

        return tools

    def run_command(self, command: List[str], timeout: int = 30) -> Tuple[bool, str, str]:
        """Execute system command with error handling"""
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout, check=False
            )

            success = result.returncode == 0
            if not success:
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category="shares",
                    message=f'NFS command failed: {" ".join(command)}',
                    details={"return_code": result.returncode, "stderr": result.stderr},
                )

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, "", str(e)

    def create_nfs_export(self, config: NFSExportConfig) -> Tuple[bool, str]:
        """Create NFS export with advanced configuration"""
        try:
            # Backup current exports
            self._backup_exports_file()

            # Generate export line
            export_line = self._generate_nfs_export_line(config)

            # Add to exports file
            success = self._add_nfs_export_to_file(export_line)
            if not success:
                return False, "Failed to update exports file"

            # Export filesystem
            success = self._export_nfs_filesystem()
            if not success:
                self._restore_exports_file()
                return False, "Failed to export NFS filesystem"

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="shares",
                message=f"NFS export created: {config.path}",
                details={"clients": config.clients, "rw": config.rw},
            )

            return True, f"NFS export {config.path} created successfully"

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="shares",
                message=f"Failed to create NFS export: {e}",
                details={"path": config.path},
            )
            return False, str(e)

    def _generate_nfs_export_line(self, config: NFSExportConfig) -> str:
        """Generate NFS export line"""
        options = []

        # Access options
        if config.rw:
            options.append("rw")
        elif config.ro:
            options.append("ro")

        # Sync options
        if config.sync:
            options.append("sync")
        elif config.async_mode:
            options.append("async")

        # Root squashing
        if config.root_squash:
            options.append("root_squash")
        elif config.no_root_squash:
            options.append("no_root_squash")

        if config.all_squash:
            options.append("all_squash")

        # Anonymous user mapping
        if config.anonuid is not None:
            options.append(f"anonuid={config.anonuid}")
        if config.anongid is not None:
            options.append(f"anongid={config.anongid}")

        # Security
        if config.sec:
            options.append(f'sec={":".join(config.sec)}')

        # Performance options
        if config.no_wdelay:
            options.append("no_wdelay")
        elif config.wdelay:
            options.append("wdelay")

        if config.no_subtree_check:
            options.append("no_subtree_check")
        elif config.subtree_check:
            options.append("subtree_check")

        # Protocol versions
        if config.nfsvers:
            for version in config.nfsvers:
                options.append(f"nfsvers={version}")

        # Extended attributes
        if config.no_acl:
            options.append("no_acl")

        # Combine with clients
        clients = config.clients or ["*"]
        client_specs = []

        for client in clients:
            if options:
                client_specs.append(f'{client}({",".join(options)})')
            else:
                client_specs.append(client)

        return f'{config.path} {" ".join(client_specs)}'

    def _add_nfs_export_to_file(self, export_line: str) -> bool:
        """Add export line to exports file"""
        try:
            # Read current exports
            content = ""
            if os.path.exists(self.exports_file):
                with open(self.exports_file, "r") as f:
                    content = f.read()

            # Add new export
            if content and not content.endswith("\n"):
                content += "\n"
            content += export_line + "\n"

            # Write back to file
            with open(self.exports_file, "w") as f:
                f.write(content)

            return True

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="shares",
                message=f"Failed to update exports file: {e}",
            )
            return False

    def _export_nfs_filesystem(self) -> bool:
        """Export NFS filesystems"""
        if "exportfs" not in self.tools:
            return False

        success, stdout, stderr = self.run_command([self.tools["exportfs"], "-ra"])

        return success

    def _backup_exports_file(self):
        """Backup current exports file"""
        try:
            if os.path.exists(self.exports_file):
                subprocess.run(["cp", self.exports_file, self.backup_exports_file], check=True)
        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.WARNING,
                category="shares",
                message=f"Failed to backup exports file: {e}",
            )

    def _restore_exports_file(self):
        """Restore exports file from backup"""
        try:
            if os.path.exists(self.backup_exports_file):
                subprocess.run(["cp", self.backup_exports_file, self.exports_file], check=True)
        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="shares",
                message=f"Failed to restore exports file: {e}",
            )

    def get_nfs_status(self) -> Dict:
        """Get NFS service status and exports"""
        status = {"service_status": "unknown", "exports": [], "clients": []}

        # Check service status
        if "systemctl" in self.tools:
            success, stdout, stderr = self.run_command(
                [self.tools["systemctl"], "is-active", "nfs-server"]
            )
            status["service_status"] = stdout.strip() if success else "inactive"

        # Get current exports
        if "exportfs" in self.tools:
            success, stdout, stderr = self.run_command([self.tools["exportfs"], "-v"])
            if success:
                status["exports"] = self._parse_nfs_exports(stdout)

        # Get connected clients
        if "showmount" in self.tools:
            success, stdout, stderr = self.run_command([self.tools["showmount"], "-a"])
            if success:
                status["clients"] = self._parse_nfs_clients(stdout)

        return status

    def _parse_nfs_exports(self, output: str) -> List[Dict]:
        """Parse exportfs output"""
        exports = []
        for line in output.strip().split("\n"):
            if line.strip():
                parts = line.split()
                if len(parts) >= 2:
                    exports.append(
                        {
                            "path": parts[0],
                            "clients": parts[1] if len(parts) > 1 else "*",
                            "options": " ".join(parts[2:]) if len(parts) > 2 else "",
                        }
                    )
        return exports

    def _parse_nfs_clients(self, output: str) -> List[Dict]:
        """Parse showmount output for client connections"""
        clients = []
        for line in output.strip().split("\n"):
            if line.strip() and ":" in line:
                client, mount = line.split(":", 1)
                clients.append({"client": client.strip(), "mount_point": mount.strip()})
        return clients


# Global instances
enhanced_smb_manager = EnhancedSMBManager()
enhanced_nfs_manager = EnhancedNFSManager()
