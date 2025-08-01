import requests
import json
import ssl
import logging
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

# Disable SSL warnings for self-signed certificates
disable_warnings(InsecureRequestWarning)

logger = logging.getLogger(__name__)

class ProxmoxAPI:
    """Proxmox VE API Client"""
    
    def __init__(self, host, port=8006, username='root', password='', realm='pam', ssl_verify=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.realm = realm
        self.ssl_verify = ssl_verify
        
        # Handle container-to-host communication
        # If we're in a container and host is localhost/127.0.0.1, use gateway IP
        if host in ['localhost', '127.0.0.1', '::1']:
            try:
                import subprocess
                result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Extract gateway IP from 'default via X.X.X.X dev eth0'
                    for line in result.stdout.split('\n'):
                        if 'default via' in line:
                            gateway_ip = line.split()[2]
                            self.host = gateway_ip
                            logger.info(f"Container detected, using gateway IP: {gateway_ip}")
                            break
            except Exception as e:
                logger.warning(f"Failed to detect gateway IP: {e}")
        
        self.base_url = f"https://{self.host}:{port}/api2/json"
        self.ticket = None
        self.csrf_token = None
        
    def authenticate(self):
        """Authenticate with Proxmox API with session management"""
        try:
            # Check if we already have a valid session
            if self.ticket and self.csrf_token:
                # Test if current session is still valid
                try:
                    test_url = f"{self.base_url}/version"
                    headers = self._get_headers()
                    response = requests.get(test_url, headers=headers, verify=self.ssl_verify, timeout=10)
                    if response.status_code == 200:
                        return True
                except:
                    pass  # Session expired, need to re-authenticate
            
            url = f"{self.base_url}/access/ticket"
            data = {
                'username': f"{self.username}@{self.realm}",
                'password': self.password
            }
            
            response = requests.post(url, data=data, verify=self.ssl_verify, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('data'):
                self.ticket = result['data']['ticket']
                self.csrf_token = result['data']['CSRFPreventionToken']
                return True
            return False
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
    
    def _get_headers(self):
        """Get headers for API requests"""
        headers = {
            'Content-Type': 'application/json',
        }
        if self.csrf_token:
            headers['CSRFPreventionToken'] = self.csrf_token
        return headers
    
    def _get_cookies(self):
        """Get cookies for API requests"""
        if self.ticket:
            return {'PVEAuthCookie': self.ticket}
        return {}
    
    def get_nodes(self):
        """Get list of Proxmox nodes with enhanced error handling"""
        try:
            if not self.authenticate():
                return []
                
            url = f"{self.base_url}/nodes"
            response = requests.get(
                url, 
                headers=self._get_headers(),
                cookies=self._get_cookies(),
                verify=self.ssl_verify,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('data', [])
            
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL Error connecting to Proxmox at {self.host}:{self.port}: {e}")
            logger.info("Try setting SSL Verify to False for self-signed certificates")
            return []
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection Error to Proxmox at {self.host}:{self.port}: {e}")
            logger.info("Possible solutions:")
            logger.info("1. Check Proxmox host IP is correct")
            logger.info("2. Ensure port 8006 is accessible from container")
            logger.info("3. Check firewall settings on Proxmox host")
            logger.info("4. If in container, host may need to be gateway IP, not localhost")
            return []
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout connecting to Proxmox: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to get nodes: {e}")
            return []
    
    def get_containers(self, node=''):
        """Get list of LXC containers"""
        try:
            if not self.authenticate():
                return []
            
            # If no node specified, get first available node
            if not node:
                nodes = self.get_nodes()
                if not nodes:
                    return []
                node = nodes[0]['node']
                
            url = f"{self.base_url}/nodes/{node}/lxc"
            response = requests.get(
                url,
                headers=self._get_headers(),
                cookies=self._get_cookies(),
                verify=self.ssl_verify,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('data', [])
            
        except Exception as e:
            print(f"Failed to get containers: {e}")
            return []
    
    def create_container(self, node, vmid, **kwargs):
        """Create new LXC container"""
        try:
            if not self.authenticate():
                return False
                
            url = f"{self.base_url}/nodes/{node}/lxc"
            
            # Default container configuration
            data = {
                'vmid': vmid,
                'ostemplate': kwargs.get('template', 'ubuntu-22.04-standard'),
                'hostname': kwargs.get('hostname', f'moxnas-{vmid}'),
                'memory': kwargs.get('memory', 2048),
                'cores': kwargs.get('cores', 2),
                'rootfs': f"local-lvm:{kwargs.get('disk_size', 8)}",
                'net0': 'name=eth0,bridge=vmbr0,ip=dhcp',
                'features': 'nesting=1,keyctl=1',
                'unprivileged': 0,
                'onboot': 1,
                'password': kwargs.get('password', 'moxnas123'),
            }
            
            response = requests.post(
                url,
                data=data,
                headers=self._get_headers(),
                cookies=self._get_cookies(),
                verify=self.ssl_verify,
                timeout=30
            )
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            print(f"Failed to create container: {e}")
            return False
    
    def start_container(self, node, vmid):
        """Start LXC container"""
        try:
            if not self.authenticate():
                return False
                
            url = f"{self.base_url}/nodes/{node}/lxc/{vmid}/status/start"
            response = requests.post(
                url,
                headers=self._get_headers(),
                cookies=self._get_cookies(),
                verify=self.ssl_verify,
                timeout=10
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"Failed to start container: {e}")
            return False
    
    def stop_container(self, node, vmid):
        """Stop LXC container"""
        try:
            if not self.authenticate():
                return False
                
            url = f"{self.base_url}/nodes/{node}/lxc/{vmid}/status/stop"
            response = requests.post(
                url,
                headers=self._get_headers(),
                cookies=self._get_cookies(),
                verify=self.ssl_verify,
                timeout=10
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"Failed to stop container: {e}")
            return False
    
    def get_container_status(self, node, vmid):
        """Get container status"""
        try:
            if not self.authenticate():
                return 'unknown'
                
            url = f"{self.base_url}/nodes/{node}/lxc/{vmid}/status/current"
            response = requests.get(
                url,
                headers=self._get_headers(),
                cookies=self._get_cookies(),
                verify=self.ssl_verify,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('data', {}).get('status', 'unknown')
            
        except Exception as e:
            print(f"Failed to get container status: {e}")
            return 'unknown'