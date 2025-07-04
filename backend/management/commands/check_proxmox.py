"""
Django management command to check Proxmox connectivity
Usage: python manage.py check_proxmox
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import socket
import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings
urllib3.disable_warnings(InsecureRequestWarning)

class Command(BaseCommand):
    help = 'Check Proxmox API connectivity and configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--host',
            type=str,
            help='Proxmox host to test (overrides settings)',
        )
        parser.add_argument(
            '--port',
            type=int,
            default=8006,
            help='Proxmox port (default: 8006)',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Proxmox username (overrides settings)',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Proxmox password (overrides settings)',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking Proxmox connectivity...")
        
        # Get configuration
        host = options.get('host') or getattr(settings, 'PROXMOX_HOST', '')
        port = options.get('port') or getattr(settings, 'PROXMOX_PORT', 8006)
        username = options.get('username') or getattr(settings, 'PROXMOX_USERNAME', 'root')
        password = options.get('password') or getattr(settings, 'PROXMOX_PASSWORD', '')
        realm = getattr(settings, 'PROXMOX_REALM', 'pam')
        
        if not host:
            self.stdout.write(self.style.ERROR("❌ No Proxmox host configured"))
            self.stdout.write("Set PROXMOX_HOST in settings or use --host parameter")
            return
            
        if not password:
            self.stdout.write(self.style.ERROR("❌ No Proxmox password configured"))
            self.stdout.write("Set PROXMOX_PASSWORD in settings or use --password parameter")
            return
        
        self.stdout.write(f"📝 Configuration:")
        self.stdout.write(f"   Host: {host}:{port}")
        self.stdout.write(f"   User: {username}@{realm}")
        self.stdout.write(f"   SSL Verify: {getattr(settings, 'PROXMOX_SSL_VERIFY', False)}")
        
        # Test network connectivity
        self.stdout.write(f"\n🌐 Testing network connectivity...")
        if self._test_connectivity(host, port):
            self.stdout.write(self.style.SUCCESS(f"   ✅ Port {port} is reachable"))
        else:
            self.stdout.write(self.style.ERROR(f"   ❌ Cannot reach {host}:{port}"))
            self.stdout.write("   💡 This is normal if running outside Proxmox network")
            return
        
        # Test Proxmox API
        self.stdout.write(f"\n🔧 Testing Proxmox API...")
        if self._test_api(host, port):
            self.stdout.write(self.style.SUCCESS("   ✅ Proxmox API is accessible"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ Proxmox API not accessible"))
            return
        
        # Test authentication
        self.stdout.write(f"\n🔐 Testing authentication...")
        if self._test_auth(host, port, username, password, realm):
            self.stdout.write(self.style.SUCCESS("   ✅ Authentication successful"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ Authentication failed"))
            return
        
        # Test MoxNAS integration
        self.stdout.write(f"\n🚀 Testing MoxNAS integration...")
        if self._test_integration():
            self.stdout.write(self.style.SUCCESS("   ✅ MoxNAS Proxmox integration working"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ MoxNAS integration failed"))
            return
        
        self.stdout.write(self.style.SUCCESS("\n🎉 All Proxmox connectivity tests passed!"))

    def _test_connectivity(self, host, port):
        """Test basic network connectivity"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _test_api(self, host, port):
        """Test Proxmox API endpoint"""
        try:
            url = f"https://{host}:{port}/api2/json/version"
            response = requests.get(url, verify=False, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def _test_auth(self, host, port, username, password, realm):
        """Test Proxmox authentication"""
        try:
            url = f"https://{host}:{port}/api2/json/access/ticket"
            data = {
                'username': f"{username}@{realm}",
                'password': password
            }
            response = requests.post(url, data=data, verify=False, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return bool(result.get('data', {}).get('ticket'))
            return False
        except Exception:
            return False

    def _test_integration(self):
        """Test MoxNAS Proxmox integration"""
        try:
            from proxmox_integration.manager import ProxmoxManager
            from secure_config import SecureConfig
            
            config = SecureConfig.get_proxmox_config()
            manager = ProxmoxManager(config)
            
            if manager.connect():
                # Try to get nodes as a basic test
                nodes = manager.get_nodes()
                return True
            return False
        except Exception as e:
            self.stdout.write(f"   Error: {e}")
            return False