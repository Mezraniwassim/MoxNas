import requests
import json
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

# Disable SSL warnings for self-signed certificates
disable_warnings(InsecureRequestWarning)

class ProxmoxAPI:
    """Proxmox VE API Client"""
    
    def __init__(self, host, port=8006, username='root', password='', realm='pam', ssl_verify=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.realm = realm
        self.ssl_verify = ssl_verify
        self.base_url = f"https://{host}:{port}/api2/json"
        self.ticket = None
        self.csrf_token = None
        
    def authenticate(self):
        """Authenticate with Proxmox API"""
        try:
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
        """Get list of Proxmox nodes"""
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
            
        except Exception as e:
            print(f"Failed to get nodes: {e}")
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