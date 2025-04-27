"""Service-specific handlers for NAS network services."""

from typing import Dict, Any, List, Optional
import logging
import subprocess
from pathlib import Path
import os
import shutil
from . import ServiceConfig

logger = logging.getLogger(__name__)

class SMBService(ServiceConfig):
    """SMB/CIFS service configuration handler."""
    
    DEFAULT_PORT = 445
    
    def __init__(self, config_path: Path):
        super().__init__("smb", config_path)
        self.config_file = self.config_path / "smb.conf"
        
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate SMB service configuration.
        
        Args:
            config: Configuration dictionary with SMB settings
            
        Returns:
            bool: True if configuration is valid
        """
        required_fields = ["workgroup", "server_string", "shares"]
        if not all(field in config for field in required_fields):
            logger.error("Missing required SMB configuration fields")
            return False
            
        # Validate shares configuration
        for share in config["shares"]:
            if not all(field in share for field in ["name", "path", "valid_users"]):
                logger.error(f"Invalid share configuration: {share}")
                return False
                
        return True

    def generate_config(self, config: Dict[str, Any]) -> str:
        """Generate SMB configuration content.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            str: Generated configuration content
        """
        if not self.validate_configuration(config):
            raise ValueError("Invalid SMB configuration")
            
        content = [
            "[global]",
            f"workgroup = {config['workgroup']}",
            f"server string = {config['server_string']}",
            "security = user",
            "map to guest = never",
            "unix extensions = yes",
            "allow insecure wide links = no",
            "follow symlinks = yes",
            "wide links = yes",
            "unix charset = UTF-8",
            "bind interfaces only = yes",
            ""  # Empty line before shares
        ]
        
        # Add share configurations
        for share in config["shares"]:
            content.extend([
                f"[{share['name']}]",
                f"path = {share['path']}",
                f"valid users = {','.join(share['valid_users'])}",
                "read only = no",
                "browseable = yes",
                "create mask = 0660",
                "directory mask = 0770",
                "force create mode = 0660",
                "force directory mode = 0770",
                ""  # Empty line between shares
            ])
            
        return "\n".join(content)

    def apply_config(self, config: Dict[str, Any]) -> bool:
        """Apply SMB configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            # Ensure configuration directory exists
            self.config_path.mkdir(parents=True, exist_ok=True)
            # Generate and write configuration
            content = self.generate_config(config)
            self.config_file.write_text(content)
            
            # Test configuration
            result = subprocess.run(
                ["testparm", "-s", str(self.config_file)],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"SMB configuration test failed: {result.stderr}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error applying SMB configuration: {e}")
            return False

class NFSService(ServiceConfig):
    """NFS service configuration handler."""
    
    DEFAULT_PORTS = [2049, 111]  # NFS and portmapper
    
    def __init__(self, config_path: Path):
        super().__init__("nfs", config_path)
        self.exports_file = self.config_path / "exports"
    
    def generate_config(self, config: Dict[str, Any]) -> str:
        """Generate NFS exports configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            str: Generated exports configuration
        """
        if not self.validate_configuration(config):
            raise ValueError("Invalid NFS configuration")
            
        content = []
        for export in config["exports"]:
            # Build client specifications
            client_specs = []
            for client in export["clients"]:
                options = client.get("options", ["rw", "sync"])
                client_specs.append(f"{client['network']}({','.join(options)})")
                
            # Add export entry
            content.append(f"{export['path']} {' '.join(client_specs)}")
            
        return "\n".join(content)
        
    def apply_config(self, config: Dict[str, Any]) -> bool:
        """Apply NFS configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            # Ensure configuration directory exists
            self.config_path.mkdir(parents=True, exist_ok=True)
            # Generate and write configuration
            content = self.generate_config(config)
            self.exports_file.write_text(content)
            
            # Validate exports file, skip if exportfs not available
            try:
                result = subprocess.run(
                    ["exportfs", "-rav"],
                    capture_output=True,
                    text=True,
                    check=False
                )
            except FileNotFoundError:
                logger.warning("exportfs command not found, skipping NFS validation")
                return True
            if result.returncode != 0:
                logger.error(f"NFS exports validation failed: {result.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error applying NFS configuration: {e}")
            return False
        
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate NFS service configuration.
        
        Args:
            config: Configuration dictionary with NFS settings
            
        Returns:
            bool: True if configuration is valid
        """
        if "exports" not in config:
            logger.error("No exports defined in NFS configuration")
            return False
            
        for export in config["exports"]:
            if not all(field in export for field in ["path", "clients"]):
                logger.error(f"Invalid export configuration: {export}")
                return False
            
            # Validate client specifications
            for client in export["clients"]:
                if not self.validate_network(client["network"]):
                    logger.error(f"Invalid network specification: {client['network']}")
                    return False
                    
        return True

class FTPService(ServiceConfig):
    """FTP service configuration handler."""
    
    DEFAULT_PORTS = [21, range(49152, 49252)]  # Control and passive data ports
    
    def __init__(self, config_path: Path):
        super().__init__("ftp", config_path)
        self.config_file = self.config_path / "vsftpd.conf"
        
    def generate_config(self, config: Dict[str, Any]) -> str:
        """Generate vsftpd configuration content.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            str: Generated configuration content
        """
        if not self.validate_configuration(config):
            raise ValueError("Invalid FTP configuration")
            
        content = [
            "# vsftpd configuration generated by MoxNAS",
            f"anonymous_enable={str(config['anonymous_enable']).lower()}",
            f"local_enable={str(config['local_enable']).lower()}",
            f"write_enable={str(config['write_enable']).lower()}",
            "userlist_enable=YES",
            "userlist_deny=NO",
            "tcp_wrappers=YES",
            "xferlog_enable=YES",
            "connect_from_port_20=NO",
            "seccomp_sandbox=NO",  # Required for container compatibility
            "listen=YES",
            "listen_ipv6=NO",
            "require_ssl_reuse=NO",  # Better container compatibility
            "ssl_ciphers=HIGH"
        ]
        
        # Add passive mode configuration if specified
        if "pasv_min_port" in config and "pasv_max_port" in config:
            content.extend([
                "pasv_enable=YES",
                f"pasv_min_port={config['pasv_min_port']}",
                f"pasv_max_port={config['pasv_max_port']}"
            ])
            
        # Add SSL configuration if enabled
        if config.get("ssl_enable", False):
            content.extend([
                "ssl_enable=YES",
                "allow_anon_ssl=NO",
                "force_local_data_ssl=YES",
                "force_local_logins_ssl=YES",
                "ssl_tlsv1=YES",
                "ssl_sslv2=NO",
                "ssl_sslv3=NO",
                f"ssl_cert_file={config.get('ssl_cert_file', '/etc/ssl/certs/vsftpd.pem')}",
                f"ssl_key_file={config.get('ssl_key_file', '/etc/ssl/private/vsftpd.key')}"
            ])
            
        return "\n".join(content)
        
    def apply_config(self, config: Dict[str, Any]) -> bool:
        """Apply FTP configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            # Ensure configuration directory exists
            self.config_path.mkdir(parents=True, exist_ok=True)
            # Generate and write configuration
            content = self.generate_config(config)
            self.config_file.write_text(content)
            
            # Skip FTP validation if vsftpd is not installed
            if shutil.which("vsftpd") is None:
                logger.warning("vsftpd command not found, skipping FTP validation")
                return True
            # Test configuration
            result = subprocess.run(
                ["vsftpd", "-olisten=NO", str(self.config_file)],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode != 0:
                logger.error(f"FTP configuration test failed: {result.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error applying FTP configuration: {e}")
            return False
        
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate FTP service configuration.
        
        Args:
            config: Configuration dictionary with FTP settings
            
        Returns:
            bool: True if configuration is valid
        """
        required_fields = ["anonymous_enable", "local_enable", "write_enable"]
        if not all(field in config for field in required_fields):
            logger.error("Missing required FTP configuration fields")
            return False
            
        # Validate passive port range if specified
        if "pasv_min_port" in config and "pasv_max_port" in config:
            if not (1024 <= config["pasv_min_port"] <= config["pasv_max_port"] <= 65535):
                logger.error("Invalid passive port range")
                return False
                
        return True

class iSCSIService(ServiceConfig):
    """iSCSI service configuration handler."""
    
    DEFAULT_PORT = 3260
    
    def __init__(self, config_path: Path):
        super().__init__("iscsi", config_path)
        self.config_dir = self.config_path / "targets"
        
    def generate_target_config(self, target: Dict[str, Any]) -> str:
        """Generate configuration for a single iSCSI target.
        
        Args:
            target: Target configuration dictionary
            
        Returns:
            str: Generated target configuration
        """
        content = [
            f"<target {target['name']}>",
            "    driver iscsi",
            "    vendor_id MoxNAS",
            f"    device_id {target['name'].split(':')[-1]}"
        ]
        
        # Add LUN configurations
        for lun in target["luns"]:
            content.extend([
                f"    <backing-store {lun['path']}>",
                f"        lun {lun['id']}",
                f"        device-type {lun['type']}",
                "        removable 0",
                "        readonly 0",
                "        write-cache on",
                "    </backing-store>"
            ])
            
        # Add initiator ACLs if specified
        if "allowed_initiators" in target:
            content.extend([
                "    <initiator-address>",
                *[f"        {initiator}" for initiator in target["allowed_initiators"]],
                "    </initiator-address>"
            ])
            
        content.append("</target>")
        return "\n".join(content)
        
    def generate_config(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Generate iSCSI target configurations.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dict[str, str]: Map of target name to configuration content
        """
        if not self.validate_configuration(config):
            raise ValueError("Invalid iSCSI configuration")
            
        return {
            target["name"]: self.generate_target_config(target)
            for target in config["targets"]
        }
        
    def apply_config(self, config: Dict[str, Any]) -> bool:
        """Apply iSCSI configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            bool: True if successful
        """
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate and write target configurations
            target_configs = self.generate_config(config)
            for target_name, content in target_configs.items():
                target_file = self.config_dir / f"{target_name.split(':')[-1]}.conf"
                target_file.write_text(content)
            
            # Validate iSCSI configuration, skip if tgtadm not available
            try:
                result = subprocess.run(
                    ["tgtadm", "--lld", "iscsi", "--op", "show", "--mode", "target"],
                    capture_output=True,
                    text=True,
                    check=False
                )
            except FileNotFoundError:
                logger.warning("tgtadm command not found, skipping iSCSI validation")
                return True
            if result.returncode != 0:
                logger.error(f"iSCSI configuration test failed: {result.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error applying iSCSI configuration: {e}")
            return False
        
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate iSCSI service configuration.
        
        Args:
            config: Configuration dictionary with iSCSI settings
            
        Returns:
            bool: True if configuration is valid
        """
        if "targets" not in config:
            logger.error("No targets defined in iSCSI configuration")
            return False
            
        for target in config["targets"]:
            if not all(field in target for field in ["name", "luns"]):
                logger.error(f"Invalid target configuration: {target}")
                return False
                
            # Validate LUN configurations
            for lun in target["luns"]:
                if not all(field in lun for field in ["id", "path", "type"]):
                    logger.error(f"Invalid LUN configuration: {lun}")
                    return False
                    
                if lun["type"] not in ["fileio", "block"]:
                    logger.error(f"Invalid LUN type: {lun['type']}")
                    return False
                    
        return True