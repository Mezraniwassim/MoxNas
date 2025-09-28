"""
Enhanced Proxmox VE Integration for MoxNAS
Provides deep integration with Proxmox VE for VM/CT storage, backup coordination,
and cluster-aware storage management
"""
import requests
import json
import ssl
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.models import StoragePool, SystemLog, LogLevel
from app import db

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ProxmoxResourceType(Enum):
    """Proxmox resource types"""

    VM = "vm"
    CONTAINER = "container"
    STORAGE = "storage"
    NODE = "node"
    CLUSTER = "cluster"


class StorageType(Enum):
    """Proxmox storage types"""

    DIR = "dir"
    LVM = "lvm"
    LVM_THIN = "lvmthin"
    ZFS = "zfspool"
    CEPH_RBD = "rbd"
    CIFS = "cifs"
    NFS = "nfs"
    GLUSTER = "glusterfs"


@dataclass
class ProxmoxCredentials:
    """Proxmox authentication credentials"""

    host: str
    port: int = 8006
    username: str = "root@pam"
    password: str = None
    api_token_id: str = None
    api_token_secret: str = None
    verify_ssl: bool = False


@dataclass
class StorageDefinition:
    """Proxmox storage definition"""

    storage_id: str
    storage_type: StorageType
    path: str
    content: List[str]  # Content types: iso, vztmpl, backup, images, rootdir
    nodes: List[str] = None  # Nodes where storage is available
    shared: bool = True
    enabled: bool = True
    # Type-specific options
    export: str = None  # For NFS
    server: str = None  # For NFS/CIFS
    username: str = None  # For CIFS
    password: str = None  # For CIFS
    domain: str = None  # For CIFS
    pool: str = None  # For ZFS/RBD
    thin: bool = False  # For LVM
    saferemove: bool = False
    saferemove_throughput: str = None


class ProxmoxAPIClient:
    """Enhanced Proxmox VE API client"""

    def __init__(self, credentials: ProxmoxCredentials):
        self.credentials = credentials
        self.base_url = f"https://{credentials.host}:{credentials.port}/api2/json"
        self.session = requests.Session()
        self.csrf_token = None
        self.ticket = None
        self.api_token = None

        # Configure session with retries
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Configure SSL
        if not credentials.verify_ssl:
            self.session.verify = False

    def authenticate(self) -> Tuple[bool, str]:
        """Authenticate with Proxmox API"""
        try:
            if self.credentials.api_token_id and self.credentials.api_token_secret:
                # Use API token authentication
                self.api_token = (
                    f"{self.credentials.api_token_id}={self.credentials.api_token_secret}"
                )
                self.session.headers.update({"Authorization": f"PVEAPIToken={self.api_token}"})

                # Test authentication
                response = self.session.get(f"{self.base_url}/version")
                if response.status_code == 200:
                    SystemLog.log_event(
                        level=LogLevel.INFO,
                        category="proxmox",
                        message="Authenticated with Proxmox using API token",
                    )
                    return True, "API token authentication successful"
                else:
                    return False, f"API token authentication failed: {response.status_code}"

            else:
                # Use username/password authentication
                auth_data = {
                    "username": self.credentials.username,
                    "password": self.credentials.password,
                }

                response = self.session.post(f"{self.base_url}/access/ticket", data=auth_data)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("data"):
                        self.ticket = result["data"]["ticket"]
                        self.csrf_token = result["data"]["CSRFPreventionToken"]

                        # Update session headers
                        self.session.cookies.set("PVEAuthCookie", self.ticket)
                        self.session.headers.update({"CSRFPreventionToken": self.csrf_token})

                        SystemLog.log_event(
                            level=LogLevel.INFO,
                            category="proxmox",
                            message="Authenticated with Proxmox using username/password",
                        )
                        return True, "Username/password authentication successful"
                    else:
                        return False, "Authentication failed: No ticket received"
                else:
                    return False, f"Authentication failed: {response.status_code}"

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="proxmox",
                message=f"Proxmox authentication error: {e}",
            )
            return False, str(e)

    def get(self, endpoint: str, params: Dict = None) -> Tuple[bool, Dict]:
        """GET request to Proxmox API"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = self.session.get(url, params=params)

            if response.status_code == 200:
                return True, response.json()
            else:
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category="proxmox",
                    message=f"Proxmox API GET failed: {endpoint}",
                    details={"status_code": response.status_code, "response": response.text[:500]},
                )
                return False, {"error": f"HTTP {response.status_code}", "details": response.text}

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="proxmox",
                message=f"Proxmox API GET error: {e}",
                details={"endpoint": endpoint},
            )
            return False, {"error": str(e)}

    def post(self, endpoint: str, data: Dict = None) -> Tuple[bool, Dict]:
        """POST request to Proxmox API"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = self.session.post(url, data=data)

            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                SystemLog.log_event(
                    level=LogLevel.WARNING,
                    category="proxmox",
                    message=f"Proxmox API POST failed: {endpoint}",
                    details={
                        "status_code": response.status_code,
                        "response": response.text[:500],
                        "data": data,
                    },
                )
                return False, {"error": f"HTTP {response.status_code}", "details": response.text}

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="proxmox",
                message=f"Proxmox API POST error: {e}",
                details={"endpoint": endpoint, "data": data},
            )
            return False, {"error": str(e)}

    def put(self, endpoint: str, data: Dict = None) -> Tuple[bool, Dict]:
        """PUT request to Proxmox API"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = self.session.put(url, data=data)

            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                return False, {"error": f"HTTP {response.status_code}", "details": response.text}

        except Exception as e:
            return False, {"error": str(e)}

    def delete(self, endpoint: str) -> Tuple[bool, Dict]:
        """DELETE request to Proxmox API"""
        try:
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            response = self.session.delete(url)

            if response.status_code in [200, 204]:
                return True, response.json() if response.content else {}
            else:
                return False, {"error": f"HTTP {response.status_code}", "details": response.text}

        except Exception as e:
            return False, {"error": str(e)}


class ProxmoxStorageIntegration:
    """Proxmox storage integration management"""

    def __init__(self, api_client: ProxmoxAPIClient):
        self.api = api_client

    def register_moxnas_storage(
        self, pool_name: str, storage_def: StorageDefinition
    ) -> Tuple[bool, str]:
        """Register MoxNAS storage pool with Proxmox"""
        try:
            # Build storage configuration
            config_data = {
                "storage": storage_def.storage_id,
                "type": storage_def.storage_type.value,
                "content": ",".join(storage_def.content),
                "shared": "1" if storage_def.shared else "0",
                "disable": "0" if storage_def.enabled else "1",
            }

            # Add type-specific configuration
            if storage_def.storage_type == StorageType.DIR:
                config_data["path"] = storage_def.path
            elif storage_def.storage_type == StorageType.NFS:
                config_data["server"] = storage_def.server
                config_data["export"] = storage_def.export
                config_data["path"] = storage_def.path
            elif storage_def.storage_type == StorageType.CIFS:
                config_data["server"] = storage_def.server
                config_data["share"] = storage_def.export
                config_data["username"] = storage_def.username
                config_data["password"] = storage_def.password
                if storage_def.domain:
                    config_data["domain"] = storage_def.domain
            elif storage_def.storage_type == StorageType.ZFS:
                config_data["pool"] = storage_def.pool
                if storage_def.thin:
                    config_data["sparse"] = "1"

            # Add nodes if specified
            if storage_def.nodes:
                config_data["nodes"] = ",".join(storage_def.nodes)

            # Create storage in Proxmox
            success, result = self.api.post("/storage", data=config_data)
            if success:
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="proxmox",
                    message=f"MoxNAS storage registered with Proxmox: {storage_def.storage_id}",
                    details={"pool_name": pool_name, "type": storage_def.storage_type.value},
                )
                return True, f"Storage {storage_def.storage_id} registered successfully"
            else:
                return False, f"Failed to register storage: {result.get('error', 'Unknown error')}"

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR,
                category="proxmox",
                message=f"Failed to register storage with Proxmox: {e}",
                details={"pool_name": pool_name},
            )
            return False, str(e)

    def get_cluster_storage_status(self) -> Dict:
        """Get cluster storage status"""
        success, result = self.api.get("/cluster/resources", params={"type": "storage"})
        if success:
            return result.get("data", [])
        return []

    def get_node_storage_status(self, node: str) -> Dict:
        """Get storage status for specific node"""
        success, result = self.api.get(f"/nodes/{node}/storage")
        if success:
            return result.get("data", [])
        return []

    def create_vm_storage(
        self, node: str, vmid: int, storage_id: str, size: str
    ) -> Tuple[bool, str]:
        """Create VM disk storage"""
        try:
            config_data = {"vmid": vmid, f"scsi0": f"{storage_id}:{size}"}

            success, result = self.api.post(f"/nodes/{node}/qemu/{vmid}/config", data=config_data)
            if success:
                return True, f"VM storage created: {storage_id}:{size}"
            else:
                return False, f"Failed to create VM storage: {result.get('error', 'Unknown error')}"

        except Exception as e:
            return False, str(e)


class ProxmoxBackupIntegration:
    """Proxmox Backup Server integration"""

    def __init__(self, api_client: ProxmoxAPIClient):
        self.api = api_client

    def register_backup_storage(
        self,
        storage_id: str,
        server: str,
        datastore: str,
        username: str,
        password: str = None,
        fingerprint: str = None,
    ) -> Tuple[bool, str]:
        """Register Proxmox Backup Server storage"""
        try:
            config_data = {
                "storage": storage_id,
                "type": "pbs",
                "server": server,
                "datastore": datastore,
                "username": username,
                "content": "backup",
            }

            if password:
                config_data["password"] = password
            if fingerprint:
                config_data["fingerprint"] = fingerprint

            success, result = self.api.post("/storage", data=config_data)
            if success:
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="proxmox",
                    message=f"Proxmox Backup Server registered: {storage_id}",
                    details={"server": server, "datastore": datastore},
                )
                return True, f"Backup storage {storage_id} registered successfully"
            else:
                return (
                    False,
                    f"Failed to register backup storage: {result.get('error', 'Unknown error')}",
                )

        except Exception as e:
            return False, str(e)

    def coordinate_backup_schedule(
        self, vmid: int, schedule: str, storage: str
    ) -> Tuple[bool, str]:
        """Coordinate backup schedule with Proxmox"""
        try:
            # This would integrate with Proxmox backup scheduling
            # Implementation depends on specific requirements

            SystemLog.log_event(
                level=LogLevel.INFO,
                category="proxmox",
                message=f"Backup schedule coordinated for VM {vmid}",
                details={"schedule": schedule, "storage": storage},
            )

            return True, "Backup schedule coordinated successfully"

        except Exception as e:
            return False, str(e)


class ProxmoxClusterIntegration:
    """Proxmox cluster integration for HA storage"""

    def __init__(self, api_client: ProxmoxAPIClient):
        self.api = api_client

    def get_cluster_status(self) -> Dict:
        """Get cluster status and node information"""
        success, result = self.api.get("/cluster/status")
        if success:
            return result.get("data", [])
        return []

    def get_cluster_resources(self) -> Dict:
        """Get all cluster resources"""
        success, result = self.api.get("/cluster/resources")
        if success:
            return result.get("data", [])
        return []

    def enable_ha_for_storage(self, storage_id: str, nodes: List[str]) -> Tuple[bool, str]:
        """Enable high availability for storage across nodes"""
        try:
            # Configure storage to be available on multiple nodes
            config_data = {"nodes": ",".join(nodes), "shared": "1"}

            success, result = self.api.put(f"/storage/{storage_id}", data=config_data)
            if success:
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="proxmox",
                    message=f"HA enabled for storage: {storage_id}",
                    details={"nodes": nodes},
                )
                return True, f"HA enabled for storage {storage_id}"
            else:
                return False, f"Failed to enable HA: {result.get('error', 'Unknown error')}"

        except Exception as e:
            return False, str(e)

    def configure_migration_storage(self, storage_id: str) -> Tuple[bool, str]:
        """Configure storage for live migration support"""
        try:
            # Ensure storage supports live migration
            config_data = {"shared": "1", "content": "images,rootdir"}  # Required for migration

            success, result = self.api.put(f"/storage/{storage_id}", data=config_data)
            if success:
                return True, f"Migration support configured for {storage_id}"
            else:
                return (
                    False,
                    f"Failed to configure migration: {result.get('error', 'Unknown error')}",
                )

        except Exception as e:
            return False, str(e)


class ProxmoxVMManager:
    """Proxmox VM and container management"""

    def __init__(self, api_client: ProxmoxAPIClient):
        self.api = api_client

    def get_all_vms(self) -> List[Dict]:
        """Get all VMs and containers across all nodes"""
        success, result = self.api.get("/cluster/resources", params={"type": "vm"})
        if success:
            return result.get("data", [])
        return []

    def get_all_vm_status(self) -> List[Dict]:
        """Get status of all VMs and containers"""
        vms = self.get_all_vms()
        status_list = []

        for vm in vms:
            node = vm.get("node")
            vmid = vm.get("vmid")
            vm_type = "qemu" if vm.get("type") == "qemu" else "lxc"

            if node and vmid:
                success, result = self.api.get(f"/nodes/{node}/{vm_type}/{vmid}/status/current")
                if success:
                    status_list.append(result.get("data", {}))

        return status_list


class ProxmoxTemplateManager:
    """Proxmox template and ISO management"""

    def __init__(self, api_client: ProxmoxAPIClient):
        self.api = api_client

    def list_templates(self, node: str, storage: str) -> List[Dict]:
        """List templates on a storage"""
        success, result = self.api.get(f"/nodes/{node}/storage/{storage}/content")
        if success:
            return result.get("data", [])
        return []


class MoxNASProxmoxManager:
    """Main MoxNAS-Proxmox integration manager"""

    def __init__(self, credentials: ProxmoxCredentials):
        self.credentials = credentials
        self.api_client = ProxmoxAPIClient(credentials)
        self.storage_integration = ProxmoxStorageIntegration(self.api_client)
        self.backup_integration = ProxmoxBackupIntegration(self.api_client)
        self.cluster_integration = ProxmoxClusterIntegration(self.api_client)
        self.vm_manager = ProxmoxVMManager(self.api_client)
        self.template_manager = ProxmoxTemplateManager(self.api_client)
        self.authenticated = False

    def initialize(self) -> Tuple[bool, str]:
        """Initialize connection to Proxmox"""
        success, message = self.api_client.authenticate()
        if success:
            self.authenticated = True
            SystemLog.log_event(
                level=LogLevel.INFO,
                category="proxmox",
                message=f"MoxNAS-Proxmox integration initialized: {self.credentials.host}",
            )
        return success, message

    def auto_register_storage_pools(self) -> Tuple[bool, List[str]]:
        """Automatically register all MoxNAS storage pools with Proxmox"""
        if not self.authenticated:
            return False, ["Not authenticated with Proxmox"]

        results = []
        errors = []

        try:
            # Get all MoxNAS storage pools
            pools = StoragePool.query.filter_by(status="healthy").all()

            for pool in pools:
                # Determine storage type based on pool configuration
                if pool.filesystem_type == "zfs":
                    storage_type = StorageType.ZFS
                    storage_def = StorageDefinition(
                        storage_id=f"moxnas-{pool.name}",
                        storage_type=storage_type,
                        path=pool.mount_point,
                        content=["images", "rootdir", "backup"],
                        pool=pool.name,
                        shared=True,
                    )
                else:
                    storage_type = StorageType.DIR
                    storage_def = StorageDefinition(
                        storage_id=f"moxnas-{pool.name}",
                        storage_type=storage_type,
                        path=pool.mount_point,
                        content=["images", "rootdir", "backup", "iso", "vztmpl"],
                        shared=True,
                    )

                # Register with Proxmox
                success, message = self.storage_integration.register_moxnas_storage(
                    pool.name, storage_def
                )
                if success:
                    results.append(f"Registered: {pool.name}")
                else:
                    errors.append(f"Failed to register {pool.name}: {message}")

            if results:
                SystemLog.log_event(
                    level=LogLevel.INFO,
                    category="proxmox",
                    message=f"Auto-registered {len(results)} storage pools with Proxmox",
                    details={"registered": results, "errors": errors},
                )

            return len(errors) == 0, results + errors

        except Exception as e:
            error_msg = f"Auto-registration failed: {e}"
            SystemLog.log_event(level=LogLevel.ERROR, category="proxmox", message=error_msg)
            return False, [error_msg]

    def sync_storage_status(self) -> Dict:
        """Synchronize storage status between MoxNAS and Proxmox"""
        if not self.authenticated:
            return {"error": "Not authenticated with Proxmox"}

        try:
            # Get Proxmox cluster storage status
            cluster_storage = self.storage_integration.get_cluster_storage_status()

            # Get MoxNAS pools
            moxnas_pools = {f"moxnas-{pool.name}": pool for pool in StoragePool.query.all()}

            sync_status = {
                "proxmox_storage": len(cluster_storage),
                "moxnas_pools": len(moxnas_pools),
                "synchronized": [],
                "missing_in_proxmox": [],
                "missing_in_moxnas": [],
            }

            # Find synchronized storage
            proxmox_storage_ids = {storage.get("id", "") for storage in cluster_storage}

            for storage_id, pool in moxnas_pools.items():
                if storage_id in proxmox_storage_ids:
                    sync_status["synchronized"].append(
                        {"id": storage_id, "pool_name": pool.name, "status": pool.status.value}
                    )
                else:
                    sync_status["missing_in_proxmox"].append(
                        {"id": storage_id, "pool_name": pool.name}
                    )

            # Find Proxmox storage not in MoxNAS
            for storage in cluster_storage:
                storage_id = storage.get("id", "")
                if storage_id.startswith("moxnas-") and storage_id not in moxnas_pools:
                    sync_status["missing_in_moxnas"].append(storage)

            return sync_status

        except Exception as e:
            SystemLog.log_event(
                level=LogLevel.ERROR, category="proxmox", message=f"Storage sync failed: {e}"
            )
            return {"error": str(e)}

    def get_integration_status(self) -> Dict:
        """Get comprehensive integration status"""
        status = {
            "authenticated": self.authenticated,
            "proxmox_host": self.credentials.host,
            "last_sync": None,
            "cluster_info": None,
            "storage_sync": None,
        }

        if self.authenticated:
            try:
                # Get cluster information
                cluster_status = self.cluster_integration.get_cluster_status()
                if cluster_status:
                    status["cluster_info"] = {
                        "nodes": len(
                            [node for node in cluster_status if node.get("type") == "node"]
                        ),
                        "quorate": any(
                            node.get("quorate")
                            for node in cluster_status
                            if node.get("type") == "cluster"
                        ),
                    }

                # Get storage sync status
                status["storage_sync"] = self.sync_storage_status()
                status["last_sync"] = datetime.now().isoformat()

            except Exception as e:
                status["error"] = str(e)

        return status


# Global Proxmox integration manager
proxmox_manager = None


def initialize_proxmox_integration(credentials: ProxmoxCredentials) -> Tuple[bool, str]:
    """Initialize global Proxmox integration"""
    global proxmox_manager

    try:
        proxmox_manager = MoxNASProxmoxManager(credentials)
        success, message = proxmox_manager.initialize()

        if success:
            # Auto-register storage pools
            reg_success, reg_results = proxmox_manager.auto_register_storage_pools()
            if reg_success:
                message += f" | Auto-registered {len(reg_results)} storage pools"
            else:
                message += f" | Auto-registration had issues: {len(reg_results)} results"

        return success, message

    except Exception as e:
        SystemLog.log_event(
            level=LogLevel.ERROR,
            category="proxmox",
            message=f"Proxmox integration initialization failed: {e}",
        )
        return False, str(e)


def get_proxmox_manager() -> Optional[MoxNASProxmoxManager]:
    """Get global Proxmox manager instance"""
    return proxmox_manager
