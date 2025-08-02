"""
Proxmox Authentication and Credential Management
Secure handling of Proxmox host credentials for MoxNAS
"""

import os
import json
import base64
import logging
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from django.core.cache import cache
from django.conf import settings
from django.contrib.sessions.models import Session
from .models import ProxmoxHost
import requests
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ProxmoxAuthManager:
    """Manages Proxmox authentication and secure credential storage"""
    
    def __init__(self):
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        self.session_timeout = 3600  # 1 hour
    
    def _get_or_create_encryption_key(self):
        """Get or create encryption key for credential storage"""
        key_file = os.path.join(settings.BASE_DIR, '.proxmox_key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Secure the key file
            os.chmod(key_file, 0o600)
            return key
    
    def encrypt_password(self, password):
        """Encrypt password for secure storage"""
        if not password:
            return ""
        return self.fernet.encrypt(password.encode()).decode()
    
    def decrypt_password(self, encrypted_password):
        """Decrypt password for use"""
        if not encrypted_password:
            return ""
        try:
            return self.fernet.decrypt(encrypted_password.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt password: {e}")
            return ""
    
    def authenticate_proxmox(self, host, port, username, password, realm='pam', verify_ssl=False):
        """Authenticate with Proxmox host and return session info"""
        try:
            # Proxmox API authentication endpoint
            auth_url = f"{'https' if port == 8006 else 'http'}://{host}:{port}/api2/json/access/ticket"
            
            # Authentication data
            auth_data = {
                'username': f"{username}@{realm}",
                'password': password
            }
            
            # Make authentication request
            response = requests.post(
                auth_url,
                data=auth_data,
                verify=verify_ssl,
                timeout=10
            )
            
            if response.status_code == 200:
                auth_result = response.json()
                
                if 'data' in auth_result:
                    ticket = auth_result['data']['ticket']
                    csrf_token = auth_result['data']['CSRFPreventionToken']
                    
                    # Create session info
                    session_info = {
                        'host': host,
                        'port': port,
                        'username': username,
                        'realm': realm,
                        'ticket': ticket,
                        'csrf_token': csrf_token,
                        'verify_ssl': verify_ssl,
                        'authenticated_at': datetime.now().isoformat(),
                        'expires_at': (datetime.now() + timedelta(hours=2)).isoformat()
                    }
                    
                    return {
                        'success': True,
                        'session_info': session_info,
                        'message': 'Authentication successful'
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Invalid response from Proxmox'
                    }
            else:
                error_msg = 'Authentication failed'
                try:
                    error_data = response.json()
                    if 'errors' in error_data:
                        error_msg = error_data['errors'].get('password', error_msg)
                except Exception:
                    pass
                
                return {
                    'success': False,
                    'message': error_msg
                }
                
        except requests.exceptions.ConnectTimeout:
            return {
                'success': False,
                'message': 'Connection timeout - check host and port'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'Connection failed - check host and network'
            }
        except Exception as e:
            logger.error(f"Proxmox authentication error: {e}")
            return {
                'success': False,
                'message': f'Authentication error: {str(e)}'
            }
    
    def store_session_credentials(self, session_key, session_info):
        """Store encrypted session credentials"""
        try:
            # Encrypt the entire session info
            encrypted_session = self.fernet.encrypt(json.dumps(session_info).encode()).decode()
            
            # Store in cache with timeout
            cache_key = f"proxmox_session_{session_key}"
            cache.set(cache_key, encrypted_session, self.session_timeout)
            
            return True
        except Exception as e:
            logger.error(f"Failed to store session credentials: {e}")
            return False
    
    def get_session_credentials(self, session_key):
        """Retrieve and decrypt session credentials"""
        try:
            cache_key = f"proxmox_session_{session_key}"
            encrypted_session = cache.get(cache_key)
            
            if encrypted_session:
                decrypted_data = self.fernet.decrypt(encrypted_session.encode()).decode()
                session_info = json.loads(decrypted_data)
                
                # Check if session is still valid
                expires_at = datetime.fromisoformat(session_info['expires_at'])
                if datetime.now() < expires_at:
                    return session_info
                else:
                    # Session expired, remove from cache
                    cache.delete(cache_key)
                    return None
            
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve session credentials: {e}")
            return None
    
    def make_proxmox_request(self, session_info, endpoint, method='GET', data=None):
        """Make authenticated request to Proxmox API"""
        try:
            base_url = f"{'https' if session_info['port'] == 8006 else 'http'}://{session_info['host']}:{session_info['port']}"
            url = f"{base_url}{endpoint}"
            
            # Prepare headers
            headers = {
                'Cookie': f"PVEAuthCookie={session_info['ticket']}",
                'CSRFPreventionToken': session_info['csrf_token']
            }
            
            # Make request
            if method.upper() == 'GET':
                response = requests.get(
                    url,
                    headers=headers,
                    verify=session_info['verify_ssl'],
                    timeout=30
                )
            elif method.upper() == 'POST':
                response = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    verify=session_info['verify_ssl'],
                    timeout=30
                )
            elif method.upper() == 'PUT':
                response = requests.put(
                    url,
                    headers=headers,
                    data=data,
                    verify=session_info['verify_ssl'],
                    timeout=30
                )
            elif method.upper() == 'DELETE':
                response = requests.delete(
                    url,
                    headers=headers,
                    verify=session_info['verify_ssl'],
                    timeout=30
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json().get('data', {}),
                    'status_code': response.status_code
                }
            else:
                return {
                    'success': False,
                    'message': f'Request failed with status {response.status_code}',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Proxmox API request failed: {e}")
            return {
                'success': False,
                'message': f'Request failed: {str(e)}'
            }
    
    def get_proxmox_nodes(self, session_info):
        """Get list of Proxmox nodes"""
        return self.make_proxmox_request(session_info, '/api2/json/nodes')
    
    def get_proxmox_storage(self, session_info, node=None):
        """Get Proxmox storage information"""
        if node:
            endpoint = f'/api2/json/nodes/{node}/storage'
        else:
            endpoint = '/api2/json/storage'
        return self.make_proxmox_request(session_info, endpoint)
    
    def get_proxmox_containers(self, session_info, node=None):
        """Get Proxmox containers"""
        if node:
            endpoint = f'/api2/json/nodes/{node}/lxc'
        else:
            # Get from all nodes
            nodes_result = self.get_proxmox_nodes(session_info)
            if nodes_result['success']:
                all_containers = []
                for node_info in nodes_result['data']:
                    node_name = node_info['node']
                    containers_result = self.make_proxmox_request(
                        session_info, 
                        f'/api2/json/nodes/{node_name}/lxc'
                    )
                    if containers_result['success']:
                        all_containers.extend(containers_result['data'])
                return {
                    'success': True,
                    'data': all_containers
                }
            else:
                return nodes_result
        
        return self.make_proxmox_request(session_info, endpoint)
    
    def test_proxmox_connection(self, session_info):
        """Test Proxmox connection with current session"""
        try:
            # Try to get cluster status or nodes
            result = self.make_proxmox_request(session_info, '/api2/json/cluster/status')
            if not result['success']:
                # Fallback to nodes endpoint
                result = self.get_proxmox_nodes(session_info)
            
            return result
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}'
            }
    
    def logout_proxmox(self, session_key):
        """Logout from Proxmox and clear session"""
        try:
            # Clear session from cache
            cache_key = f"proxmox_session_{session_key}"
            cache.delete(cache_key)
            
            return {
                'success': True,
                'message': 'Logged out successfully'
            }
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return {
                'success': False,
                'message': f'Logout failed: {str(e)}'
            }
    
    def get_session_status(self, session_key):
        """Get current session status"""
        session_info = self.get_session_credentials(session_key)
        
        if session_info:
            expires_at = datetime.fromisoformat(session_info['expires_at'])
            time_remaining = expires_at - datetime.now()
            
            return {
                'authenticated': True,
                'host': session_info['host'],
                'username': session_info['username'],
                'realm': session_info['realm'],
                'authenticated_at': session_info['authenticated_at'],
                'expires_at': session_info['expires_at'],
                'time_remaining_seconds': int(time_remaining.total_seconds())
            }
        else:
            return {
                'authenticated': False,
                'message': 'No active session'
            }


# Global instance
proxmox_auth_manager = ProxmoxAuthManager()