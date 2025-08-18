from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from .managers import samba_manager, nfs_manager, ftp_manager
from ..shares.models import SMBShare, NFSShare
import logging
import time

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def control_service(request):
    """Control services (start, stop, restart, reload)"""
    service_name = request.data.get('service')
    action = request.data.get('action')
    
    if not service_name or not action:
        return Response(
            {'error': 'Both service and action are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Get service manager
    managers = {
        'samba': samba_manager,
        'smbd': samba_manager,
        'nfs': nfs_manager,
        'nfs-kernel-server': nfs_manager,
        'ftp': ftp_manager,
        'vsftpd': ftp_manager,
    }
    
    manager = managers.get(service_name.lower())
    if not manager:
        return Response(
            {'error': f'Unknown service: {service_name}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Execute action
    try:
        if action == 'start':
            result = manager.start()
        elif action == 'stop':
            result = manager.stop()
        elif action == 'restart':
            result = manager.restart()
        elif action == 'reload':
            result = manager.reload()
        elif action == 'enable':
            result = manager.enable()
        elif action == 'disable':
            result = manager.disable()
        else:
            return Response(
                {'error': f'Unknown action: {action}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if result:
            return Response({
                'success': True,
                'message': f'Successfully {action}ed {service_name}',
                'status': manager.status()
            })
        else:
            return Response(
                {'error': f'Failed to {action} {service_name}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        logger.error(f"Error controlling service {service_name}: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def service_status(request):
    """Get status of all services"""
    try:
        services = {
            'samba': samba_manager.status(),
            'nfs': nfs_manager.status(),
            'ftp': ftp_manager.status(),
        }
        
        return Response({
            'services': services,
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_config(request):
    """Regenerate service configurations"""
    service_name = request.data.get('service')
    
    if not service_name:
        return Response(
            {'error': 'Service name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        if service_name.lower() in ['samba', 'smb']:
            # Regenerate Samba configuration
            shares = SMBShare.objects.filter(enabled=True)
            config_content = samba_manager.generate_config(shares)
            
            # Test configuration
            valid, message = samba_manager.test_config()
            if not valid:
                return Response(
                    {'error': f'Invalid configuration generated: {message}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reload service
            samba_manager.reload_config()
            
            return Response({
                'success': True,
                'message': 'Samba configuration regenerated and reloaded',
                'config_preview': config_content[:500] + '...' if len(config_content) > 500 else config_content
            })
            
        elif service_name.lower() == 'nfs':
            # Regenerate NFS exports
            exports = NFSShare.objects.filter(enabled=True)
            exports_content = nfs_manager.generate_exports(exports)
            
            # Reload exports
            nfs_manager.reload_exports()
            
            return Response({
                'success': True,
                'message': 'NFS exports regenerated and reloaded',
                'config_preview': exports_content
            })
            
        elif service_name.lower() == 'ftp':
            # Regenerate FTP configuration
            config_content = ftp_manager.generate_config()
            
            # Restart FTP service
            ftp_manager.restart()
            
            return Response({
                'success': True,
                'message': 'FTP configuration regenerated and service restarted',
                'config_preview': config_content[:500] + '...' if len(config_content) > 500 else config_content
            })
            
        else:
            return Response(
                {'error': f'Configuration regeneration not supported for: {service_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Error regenerating config for {service_name}: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_configuration(request):
    """Test service configuration syntax"""
    service_name = request.data.get('service')
    
    if not service_name:
        return Response(
            {'error': 'Service name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        if service_name.lower() in ['samba', 'smb']:
            valid, message = samba_manager.test_config()
            return Response({
                'valid': valid,
                'message': message,
                'service': 'samba'
            })
        else:
            return Response(
                {'error': f'Configuration testing not supported for: {service_name}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        logger.error(f"Error testing config for {service_name}: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )