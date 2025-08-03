import logging
import time
import random
from typing import Dict, Any, List, Optional
from django.conf import settings
from apps.proxmox.services import ProxmoxService
from .models import MoxNasContainer, ContainerService

logger = logging.getLogger('moxnas.containers')


class ContainerManagementService:
    """Service for managing MoxNas containers"""
    
    def __init__(self):
        self.proxmox_service = ProxmoxService()
    
    def find_available_vmid(self, start_id: int = 200) -> int:
        """Find the next available VMID"""
        try:
            containers = self.proxmox_service.get_containers()
            used_vmids = {c.get('vmid') for c in containers}
            
            # Also check our database
            db_vmids = set(MoxNasContainer.objects.values_list('vmid', flat=True))
            used_vmids.update(db_vmids)
            
            # Find first available ID starting from start_id
            vmid = start_id
            while vmid in used_vmids:
                vmid += 1
                if vmid > 999:  # Reasonable upper limit
                    raise ValueError("No available VMID found")
            
            return vmid
        except Exception as e:
            logger.error(f"Failed to find available VMID: {e}")
            return random.randint(200, 999)
    
    def create_moxnas_container(self, config: Dict[str, Any]) -> Optional[MoxNasContainer]:
        """Create a new MoxNas container"""
        try:
            # Find available VMID if not provided
            vmid = config.get('vmid')
            if not vmid:
                vmid = self.find_available_vmid()
                config['vmid'] = vmid
            
            # Prepare container configuration
            container_config = {
                'hostname': config.get('hostname', f'moxnas-{vmid}'),
                'ostemplate': config.get('ostemplate', settings.CONTAINER_CONFIG['TEMPLATE']),
                'storage': config.get('storage', settings.CONTAINER_CONFIG['STORAGE']),
                'memory': config.get('memory', settings.CONTAINER_CONFIG['MEMORY']),
                'cores': config.get('cores', settings.CONTAINER_CONFIG['CORES']),
                'swap': config.get('swap', settings.CONTAINER_CONFIG['SWAP']),
                'net0': config.get('net0', 'name=eth0,bridge=vmbr0,ip=dhcp'),
                'rootfs': config.get('rootfs', f"{config.get('storage', 'local-lvm')}:8"),
                'unprivileged': 1,
                'onboot': 1,
                'start': 0,  # Don't start automatically, we'll start after setup
                'features': 'nesting=1,keyctl=1',  # Required for some services
            }
            
            # Create container in Proxmox
            success = self.proxmox_service.create_container(vmid, container_config)
            if not success:
                logger.error(f"Failed to create container {vmid} in Proxmox")
                return None
            
            # Create database record
            container = MoxNasContainer.objects.create(
                vmid=vmid,
                name=config.get('name', f'moxnas-{vmid}'),
                hostname=container_config['hostname'],
                node_id=1,  # Default node - should be configurable
                status='creating',
                memory=container_config['memory'],
                cores=container_config['cores'],
                swap=container_config['swap'],
                storage=container_config['storage'],
            )
            
            logger.info(f"Created MoxNas container {vmid}")
            return container
            
        except Exception as e:
            logger.error(f"Failed to create MoxNas container: {e}")
            return None
    
    def install_moxnas_in_container(self, container: MoxNasContainer) -> bool:
        """Install MoxNas software in the container"""
        try:
            # Wait for container to be ready
            self._wait_for_container_network(container.vmid)
            
            # Start container if not running
            if not self._ensure_container_running(container.vmid):
                return False
            
            # Installation commands
            install_commands = [
                'apt update',
                'apt install -y python3-pip python3-venv nodejs npm git curl',
                'mkdir -p /opt/moxnas',
                'cd /opt/moxnas && git clone https://github.com/Mezraniwassim/MoxNas.git .',
                'python3 -m venv /opt/moxnas/venv',
                'source /opt/moxnas/venv/bin/activate && pip install -r requirements.txt',
                'cd /opt/moxnas/frontend && npm install && npm run build',
                'cd /opt/moxnas/backend && python manage.py migrate',
                'cd /opt/moxnas/backend && python manage.py collectstatic --noinput',
            ]
            
            # Execute installation commands
            for command in install_commands:
                logger.info(f"Executing in container {container.vmid}: {command}")
                result = self.proxmox_service.execute_command(container.vmid, command)
                if not result:
                    logger.error(f"Command failed in container {container.vmid}: {command}")
                    return False
            
            # Create systemd service
            self._create_moxnas_service(container.vmid)
            
            # Update container status
            container.is_moxnas_ready = True
            container.status = 'running'
            container.save()
            
            # Create default services
            self._create_default_services(container)
            
            logger.info(f"MoxNas installation completed for container {container.vmid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install MoxNas in container {container.vmid}: {e}")
            container.status = 'error'
            container.installation_log = str(e)
            container.save()
            return False
    
    def _wait_for_container_network(self, vmid: int, timeout: int = 300) -> bool:
        """Wait for container network to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Try to ping a known host
                result = self.proxmox_service.execute_command(vmid, 'ping -c 1 8.8.8.8')
                if result:
                    return True
            except:
                pass
            time.sleep(10)
        return False
    
    def _ensure_container_running(self, vmid: int) -> bool:
        """Ensure container is running"""
        try:
            status = self.proxmox_service.get_container_status(vmid)
            if status.get('status') != 'running':
                return self.proxmox_service.start_container(vmid)
            return True
        except Exception as e:
            logger.error(f"Failed to ensure container {vmid} is running: {e}")
            return False
    
    def _create_moxnas_service(self, vmid: int):
        """Create systemd service for MoxNas"""
        service_content = """[Unit]
Description=MoxNas Web Interface
After=network.target

[Service]
Type=forking
User=root
WorkingDirectory=/opt/moxnas
Environment=PATH=/opt/moxnas/venv/bin
ExecStart=/opt/moxnas/venv/bin/gunicorn --bind 0.0.0.0:8000 --workers 3 --chdir backend --daemon moxnas.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
"""
        
        commands = [
            f'echo "{service_content}" > /etc/systemd/system/moxnas.service',
            'systemctl daemon-reload',
            'systemctl enable moxnas',
            'systemctl start moxnas',
        ]
        
        for command in commands:
            self.proxmox_service.execute_command(vmid, command)
    
    def _create_default_services(self, container: MoxNasContainer):
        """Create default services for the container"""
        default_services = [
            {'service_type': 'ssh', 'port': 22},
            {'service_type': 'ftp', 'port': 21},
            {'service_type': 'nfs', 'port': 2049},
            {'service_type': 'smb', 'port': 445},
        ]
        
        for service_config in default_services:
            ContainerService.objects.get_or_create(
                container=container,
                service_type=service_config['service_type'],
                defaults={
                    'port': service_config['port'],
                    'status': 'stopped',
                    'is_enabled': True,
                    'auto_start': False,
                }
            )
    
    def delete_container(self, container: MoxNasContainer) -> bool:
        """Delete a MoxNas container"""
        try:
            # Delete from Proxmox
            success = self.proxmox_service.delete_container(container.vmid)
            if success:
                # Delete from database
                container.delete()
                logger.info(f"Deleted container {container.vmid}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete container {container.vmid}: {e}")
            return False
    
    def get_container_info(self, vmid: int) -> Dict[str, Any]:
        """Get detailed container information"""
        try:
            # Get Proxmox status
            proxmox_status = self.proxmox_service.get_container_status(vmid)
            
            # Get database info
            try:
                container = MoxNasContainer.objects.get(vmid=vmid)
                db_info = {
                    'name': container.name,
                    'hostname': container.hostname,
                    'is_moxnas_ready': container.is_moxnas_ready,
                    'web_url': container.web_url,
                    'services': list(container.services.values(
                        'service_type', 'status', 'port', 'is_enabled'
                    ))
                }
            except MoxNasContainer.DoesNotExist:
                db_info = {}
            
            return {**proxmox_status, **db_info}
            
        except Exception as e:
            logger.error(f"Failed to get container {vmid} info: {e}")
            return {}
    
    def sync_containers(self) -> int:
        """Sync containers between Proxmox and database"""
        try:
            proxmox_containers = self.proxmox_service.get_containers()
            synced_count = 0
            
            for px_container in proxmox_containers:
                vmid = px_container.get('vmid')
                if not vmid:
                    continue
                
                try:
                    container = MoxNasContainer.objects.get(vmid=vmid)
                    # Update status
                    container.status = px_container.get('status', 'unknown')
                    container.save()
                except MoxNasContainer.DoesNotExist:
                    # Check if this is a MoxNas container by looking for our marker
                    if self._is_moxnas_container(vmid):
                        MoxNasContainer.objects.create(
                            vmid=vmid,
                            name=px_container.get('name', f'container-{vmid}'),
                            hostname=px_container.get('name', f'container-{vmid}'),
                            node_id=1,
                            status=px_container.get('status', 'unknown'),
                            is_moxnas_ready=True  # Assume ready if we found it
                        )
                
                synced_count += 1
            
            return synced_count
            
        except Exception as e:
            logger.error(f"Failed to sync containers: {e}")
            return 0
    
    def _is_moxnas_container(self, vmid: int) -> bool:
        """Check if a container is a MoxNas container"""
        try:
            # Check for MoxNas installation
            result = self.proxmox_service.execute_command(vmid, 'test -d /opt/moxnas')
            return result is not None
        except:
            return False