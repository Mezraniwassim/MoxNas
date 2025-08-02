"""
Proxmox Authentication Views for MoxNAS
Handles Proxmox host login, session management, and authenticated operations
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .auth_manager import proxmox_auth_manager
from .models import ProxmoxHost
import logging
import uuid

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
@api_view(['POST'])
@permission_classes([AllowAny])
def proxmox_login(request):
    """Login to Proxmox host and create authenticated session"""
    try:
        data = request.data
        
        # Extract login parameters
        host = data.get('host', '').strip()
        port = data.get('port', 8006)
        username = data.get('username', 'root').strip()
        password = data.get('password', '').strip()
        realm = data.get('realm', 'pam').strip()
        verify_ssl = data.get('verify_ssl', False)
        remember_host = data.get('remember_host', False)
        
        # Validate required fields
        if not host or not username or not password:
            return Response({
                'success': False,
                'message': 'Host, username, and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Attempt authentication
        auth_result = proxmox_auth_manager.authenticate_proxmox(
            host=host,
            port=port,
            username=username,
            password=password,
            realm=realm,
            verify_ssl=verify_ssl
        )
        
        if auth_result['success']:
            # Generate session key
            session_key = str(uuid.uuid4())
            
            # Store session credentials
            session_stored = proxmox_auth_manager.store_session_credentials(
                session_key, 
                auth_result['session_info']
            )
            
            if session_stored:
                # Test connection to verify everything works
                test_result = proxmox_auth_manager.test_proxmox_connection(
                    auth_result['session_info']
                )
                
                response_data = {
                    'success': True,
                    'message': 'Login successful',
                    'session_key': session_key,
                    'host_info': {
                        'host': host,
                        'port': port,
                        'username': username,
                        'realm': realm
                    },
                    'connection_test': test_result['success']
                }
                
                # Optionally save host configuration
                if remember_host:
                    try:
                        # Check if host already exists
                        existing_host = ProxmoxHost.objects.filter(
                            host=host, 
                            port=port
                        ).first()
                        
                        if not existing_host:
                            ProxmoxHost.objects.create(
                                name=f"{host}:{port}",
                                host=host,
                                port=port,
                                username=f"{username}@{realm}",
                                password="",  # Don't store password in database
                                realm=realm,
                                ssl_verify=verify_ssl,
                                enabled=True
                            )
                            response_data['host_saved'] = True
                        else:
                            response_data['host_exists'] = True
                    except Exception as e:
                        logger.warning(f"Failed to save host configuration: {e}")
                
                return Response(response_data)
            else:
                return Response({
                    'success': False,
                    'message': 'Failed to create session'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'success': False,
                'message': auth_result['message']
            }, status=status.HTTP_401_UNAUTHORIZED)
            
    except Exception as e:
        logger.error(f"Proxmox login error: {e}")
        return Response({
            'success': False,
            'message': f'Login failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def proxmox_logout(request):
    """Logout from Proxmox session"""
    try:
        session_key = request.data.get('session_key') or request.headers.get('X-Proxmox-Session')
        
        if not session_key:
            return Response({
                'success': False,
                'message': 'Session key required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = proxmox_auth_manager.logout_proxmox(session_key)
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Proxmox logout error: {e}")
        return Response({
            'success': False,
            'message': f'Logout failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def proxmox_session_status(request):
    """Get current Proxmox session status"""
    try:
        session_key = request.query_params.get('session_key') or request.headers.get('X-Proxmox-Session')
        
        if not session_key:
            return Response({
                'authenticated': False,
                'message': 'No session key provided'
            })
        
        status_info = proxmox_auth_manager.get_session_status(session_key)
        
        return Response(status_info)
        
    except Exception as e:
        logger.error(f"Session status error: {e}")
        return Response({
            'authenticated': False,
            'message': f'Status check failed: {str(e)}'
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def proxmox_nodes(request):
    """Get Proxmox nodes using authenticated session"""
    try:
        session_key = request.query_params.get('session_key') or request.headers.get('X-Proxmox-Session')
        
        if not session_key:
            return Response({
                'success': False,
                'message': 'Session key required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        session_info = proxmox_auth_manager.get_session_credentials(session_key)
        if not session_info:
            return Response({
                'success': False,
                'message': 'Invalid or expired session'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        result = proxmox_auth_manager.get_proxmox_nodes(session_info)
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Get nodes error: {e}")
        return Response({
            'success': False,
            'message': f'Failed to get nodes: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def proxmox_storage(request):
    """Get Proxmox storage using authenticated session"""
    try:
        session_key = request.query_params.get('session_key') or request.headers.get('X-Proxmox-Session')
        node = request.query_params.get('node')
        
        if not session_key:
            return Response({
                'success': False,
                'message': 'Session key required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        session_info = proxmox_auth_manager.get_session_credentials(session_key)
        if not session_info:
            return Response({
                'success': False,
                'message': 'Invalid or expired session'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        result = proxmox_auth_manager.get_proxmox_storage(session_info, node)
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Get storage error: {e}")
        return Response({
            'success': False,
            'message': f'Failed to get storage: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def proxmox_containers(request):
    """Get Proxmox containers using authenticated session"""
    try:
        session_key = request.query_params.get('session_key') or request.headers.get('X-Proxmox-Session')
        node = request.query_params.get('node')
        
        if not session_key:
            return Response({
                'success': False,
                'message': 'Session key required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        session_info = proxmox_auth_manager.get_session_credentials(session_key)
        if not session_info:
            return Response({
                'success': False,
                'message': 'Invalid or expired session'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        result = proxmox_auth_manager.get_proxmox_containers(session_info, node)
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Get containers error: {e}")
        return Response({
            'success': False,
            'message': f'Failed to get containers: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def proxmox_api_proxy(request):
    """Proxy authenticated requests to Proxmox API"""
    try:
        session_key = request.data.get('session_key') or request.headers.get('X-Proxmox-Session')
        endpoint = request.data.get('endpoint')
        method = request.data.get('method', 'GET')
        params = request.data.get('params', {})
        
        if not session_key or not endpoint:
            return Response({
                'success': False,
                'message': 'Session key and endpoint are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        session_info = proxmox_auth_manager.get_session_credentials(session_key)
        if not session_info:
            return Response({
                'success': False,
                'message': 'Invalid or expired session'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Ensure endpoint starts with /api2/json
        if not endpoint.startswith('/api2/json'):
            endpoint = f"/api2/json{endpoint}" if endpoint.startswith('/') else f"/api2/json/{endpoint}"
        
        result = proxmox_auth_manager.make_proxmox_request(
            session_info, 
            endpoint, 
            method, 
            params
        )
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"API proxy error: {e}")
        return Response({
            'success': False,
            'message': f'API request failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_saved_hosts(request):
    """Get list of saved Proxmox hosts"""
    try:
        hosts = ProxmoxHost.objects.filter(enabled=True).values(
            'id', 'name', 'host', 'port', 'username', 'realm', 'ssl_verify', 'created_at'
        )
        
        return Response({
            'success': True,
            'hosts': list(hosts)
        })
        
    except Exception as e:
        logger.error(f"Get saved hosts error: {e}")
        return Response({
            'success': False,
            'message': f'Failed to get saved hosts: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)