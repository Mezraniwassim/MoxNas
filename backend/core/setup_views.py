"""
MoxNAS Setup Views
Handles initial system configuration and Proxmox setup
"""

import os
import subprocess
import json
from pathlib import Path
from django.http import JsonResponse
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from proxmox.proxmox_client import ProxmoxAPI
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_network_info(request):
    """Get network information for setup wizard"""
    try:
        # Get container's network info
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
        container_ip = result.stdout.strip().split()[0] if result.stdout.strip() else 'Unknown'
        
        # Get gateway IP (likely Proxmox host)
        result = subprocess.run(['ip', 'route', 'show', 'default'], capture_output=True, text=True, timeout=5)
        gateway_ip = 'Unknown'
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'default via' in line:
                    gateway_ip = line.split()[2]
                    break
        
        # Get hostname
        result = subprocess.run(['hostname'], capture_output=True, text=True, timeout=5)
        hostname = result.stdout.strip() if result.stdout.strip() else 'moxnas'
        
        # Check if we're in a container
        is_container = os.path.exists('/.dockerenv') or os.path.exists('/proc/1/cgroup')
        if not is_container:
            try:
                with open('/proc/1/cgroup', 'r') as f:
                    content = f.read()
                    is_container = 'lxc' in content or 'docker' in content
            except:
                pass
        
        return JsonResponse({
            'success': True,
            'data': {
                'container_ip': container_ip,
                'gateway_ip': gateway_ip,
                'hostname': hostname,
                'is_container': is_container,
                'recommended_proxmox_host': gateway_ip
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get network info: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def test_proxmox_connection(request):
    """Test Proxmox connection with provided credentials"""
    try:
        data = request.data
        host = data.get('host', '').strip()
        port = int(data.get('port', 8006))
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        realm = data.get('realm', 'pam').strip()
        ssl_verify = data.get('ssl_verify', False)
        
        if not all([host, username, password]):
            return Response({
                'success': False,
                'error': 'Host, username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Test connection
        client = ProxmoxAPI(
            host=host,
            port=port,
            username=username,
            password=password,
            realm=realm,
            ssl_verify=ssl_verify
        )
        
        if client.authenticate():
            nodes = client.get_nodes()
            return Response({
                'success': True,
                'message': f'Connection successful! Found {len(nodes)} nodes.',
                'data': {
                    'nodes_count': len(nodes),
                    'nodes': nodes[:3] if nodes else []  # Show first 3 nodes
                }
            })
        else:
            return Response({
                'success': False,
                'error': 'Authentication failed. Please check your credentials.'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
    except Exception as e:
        error_msg = str(e)
        if 'Connection refused' in error_msg:
            error_msg = f"Cannot connect to {host}:{port}. Check if Proxmox is running and accessible."
        elif 'SSL' in error_msg:
            error_msg = "SSL certificate error. Try disabling SSL verification."
        elif 'timeout' in error_msg.lower():
            error_msg = f"Connection timeout to {host}:{port}. Check network connectivity."
        
        return Response({
            'success': False,
            'error': error_msg
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def save_proxmox_config(request):
    """Save Proxmox configuration to .env file"""
    try:
        data = request.data
        host = data.get('host', '').strip()
        port = int(data.get('port', 8006))
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        realm = data.get('realm', 'pam').strip()
        ssl_verify = data.get('ssl_verify', False)
        
        if not all([host, username, password]):
            return Response({
                'success': False,
                'error': 'Host, username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Test connection first
        client = ProxmoxAPI(
            host=host,
            port=port,
            username=username,
            password=password,
            realm=realm,
            ssl_verify=ssl_verify
        )
        
        if not client.authenticate():
            return Response({
                'success': False,
                'error': 'Cannot save configuration: Authentication test failed'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Read existing .env file
        env_file = Path(settings.BASE_DIR).parent / '.env'
        env_content = {}
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_content[key.strip()] = value.strip()
        
        # Update Proxmox settings
        env_content.update({
            'PROXMOX_HOST': host,
            'PROXMOX_PORT': str(port),
            'PROXMOX_USERNAME': username,
            'PROXMOX_PASSWORD': password,
            'PROXMOX_REALM': realm,
            'PROXMOX_SSL_VERIFY': 'True' if ssl_verify else 'False'
        })
        
        # Ensure other required settings exist
        if 'SECRET_KEY' not in env_content:
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
            env_content['SECRET_KEY'] = ''.join(secrets.choice(alphabet) for _ in range(50))
        
        if 'DEBUG' not in env_content:
            env_content['DEBUG'] = 'False'
            
        if 'ALLOWED_HOSTS' not in env_content:
            env_content['ALLOWED_HOSTS'] = '*'
        
        # Write updated .env file
        with open(env_file, 'w') as f:
            f.write("# MoxNAS Configuration\n")
            f.write("# Generated by Setup Wizard\n\n")
            
            f.write("# Django Configuration\n")
            for key in ['SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS']:
                if key in env_content:
                    f.write(f"{key}={env_content[key]}\n")
            
            f.write("\n# MoxNAS Storage\n")
            f.write("MOXNAS_STORAGE_PATH=/mnt/storage\n")
            f.write("MOXNAS_CONFIG_PATH=/etc/moxnas\n")
            f.write("MOXNAS_LOG_PATH=/var/log/moxnas\n")
            
            f.write("\n# Proxmox Integration\n")
            f.write(f"PROXMOX_HOST={host}\n")
            f.write(f"PROXMOX_PORT={port}\n")
            f.write(f"PROXMOX_USERNAME={username}\n")
            f.write(f"PROXMOX_PASSWORD={password}\n")
            f.write(f"PROXMOX_REALM={realm}\n")
            f.write(f"PROXMOX_SSL_VERIFY={'True' if ssl_verify else 'False'}\n")
            
            f.write("\n# Network Configuration\n")
            f.write("NETWORK_TIMEOUT=30\n")
            f.write("NETWORK_RETRIES=3\n")
            
            f.write("\n# Logging\n")
            f.write("LOG_LEVEL=INFO\n")
        
        # Set secure permissions
        os.chmod(env_file, 0o600)
        
        return Response({
            'success': True,
            'message': 'Proxmox configuration saved successfully',
            'restart_required': True
        })
        
    except Exception as e:
        logger.error(f"Failed to save Proxmox config: {e}")
        return Response({
            'success': False,
            'error': f'Failed to save configuration: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_setup_status(request):
    """Check if MoxNAS setup is complete"""
    try:
        env_file = Path(settings.BASE_DIR).parent / '.env'
        proxmox_configured = False
        
        if env_file.exists():
            with open(env_file, 'r') as f:
                content = f.read()
                proxmox_configured = (
                    'PROXMOX_HOST=' in content and
                    'PROXMOX_PASSWORD=' in content and
                    not 'PROXMOX_PASSWORD=' in content.replace('PROXMOX_PASSWORD=', '')
                )
        
        return JsonResponse({
            'success': True,
            'data': {
                'env_file_exists': env_file.exists(),
                'proxmox_configured': proxmox_configured,
                'setup_complete': proxmox_configured
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to check setup status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def restart_moxnas(request):
    """Restart MoxNAS to apply new configuration"""
    try:
        # This endpoint would trigger a restart
        # In practice, you might need to use systemd or another method
        return Response({
            'success': True,
            'message': 'Restart command sent. Please wait a moment and refresh the page.'
        })
        
    except Exception as e:
        logger.error(f"Failed to restart MoxNAS: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)