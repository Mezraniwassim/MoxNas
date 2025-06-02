from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from .models import NetworkInterface, SambaSetting, NFSSetting, FTPSetting, SSHSetting
from .services import (
    SMBService, NFSService, FTPService, SSHService, 
    NetworkInterfaceService, FirewallService
)


@method_decorator(csrf_exempt, name='dispatch')
class NetworkInterfaceViewSet(viewsets.ModelViewSet):
    queryset = NetworkInterface.objects.all()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interface_service = NetworkInterfaceService()
    
    def list(self, request):
        # Get database interfaces
        db_interfaces = self.get_queryset()
        db_data = [
            {
                'id': interface.id,
                'name': interface.name,
                'ip_address': interface.ip_address,
                'netmask': interface.netmask,
                'gateway': interface.gateway,
                'dns_servers': interface.dns_servers,
                'enabled': interface.enabled,
                'dhcp_enabled': interface.dhcp_enabled
            } for interface in db_interfaces
        ]
        
        # Get live interface data
        live_interfaces = self.interface_service.get_interfaces()
        
        return Response({
            'database_interfaces': db_data,
            'live_interfaces': live_interfaces
        })
    
    @action(detail=False, methods=['get'])
    def live_stats(self, request):
        """Get live network interface statistics"""
        interface_name = request.query_params.get('interface')
        if interface_name:
            stats = self.interface_service.get_interface_stats(interface_name)
            return Response(stats)
        
        # Get all interfaces
        interfaces = self.interface_service.get_interfaces()
        return Response(interfaces)
    
    @action(detail=False, methods=['post'])
    def test_connectivity(self, request):
        """Test network connectivity"""
        host = request.data.get('host')
        timeout = int(request.data.get('timeout', 5))
        
        if not host:
            return Response({'error': 'Host parameter required'}, status=400)
        
        result = self.interface_service.test_connectivity(host, timeout)
        return Response(result)


@method_decorator(csrf_exempt, name='dispatch')
class SMBServiceViewSet(viewsets.ViewSet):
    """ViewSet for SMB/CIFS service management"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smb_service = SMBService()
    
    def list(self, request):
        """Get SMB service status and configuration"""
        # Get database settings
        smb_setting = SambaSetting.objects.first()
        db_config = {}
        if smb_setting:
            db_config = {
                'workgroup': smb_setting.workgroup,
                'server_string': smb_setting.server_string,
                'netbios_name': smb_setting.netbios_name,
                'security': smb_setting.security,
                'guest_account': smb_setting.guest_account,
                'enable_recycle_bin': smb_setting.enable_recycle_bin,
                'audit_enable': smb_setting.audit_enable
            }
        
        # Get live service status
        service_status = self.smb_service.get_service_status()
        port_status = self.smb_service.check_port_status(self.smb_service.default_port)
        shares = self.smb_service.get_shares()
        
        return Response({
            'configuration': db_config,
            'service_status': service_status,
            'port_status': port_status,
            'shares': shares
        })
    
    @action(detail=False, methods=['post'])
    def manage_service(self, request):
        """Manage SMB service (start, stop, restart, etc.)"""
        action = request.data.get('action')
        if not action:
            return Response({'error': 'Action parameter required'}, status=400)
        
        result = self.smb_service.manage_service(action)
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def shares(self, request):
        """Get SMB shares"""
        shares = self.smb_service.get_shares()
        return Response({'shares': shares})
    
    @action(detail=False, methods=['get'])
    def sessions(self, request):
        """Get active SMB sessions"""
        sessions = self.smb_service.get_active_sessions()
        return Response({'sessions': sessions})
    
    @action(detail=False, methods=['post'])
    def test_share(self, request):
        """Test SMB share connectivity"""
        share_name = request.data.get('share_name')
        if not share_name:
            return Response({'error': 'share_name parameter required'}, status=400)
        
        result = self.smb_service.test_share_connectivity(share_name)
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def reload_config(self, request):
        """Reload SMB configuration"""
        result = self.smb_service.reload_config()
        return Response(result)


@method_decorator(csrf_exempt, name='dispatch')
class NFSServiceViewSet(viewsets.ViewSet):
    """ViewSet for NFS service management"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nfs_service = NFSService()
    
    def list(self, request):
        """Get NFS service status and configuration"""
        # Get database settings
        nfs_setting = NFSSetting.objects.first()
        db_config = {}
        if nfs_setting:
            db_config = {
                'nfs_v3_enabled': nfs_setting.nfs_v3_enabled,
                'nfs_v4_enabled': nfs_setting.nfs_v4_enabled,
                'rpc_mountd_port': nfs_setting.rpc_mountd_port,
                'rpc_statd_port': nfs_setting.rpc_statd_port,
                'rpc_lockd_port': nfs_setting.rpc_lockd_port,
                'enable_udp': nfs_setting.enable_udp,
                'servers': nfs_setting.servers
            }
        
        # Get live service status
        service_status = self.nfs_service.get_service_status()
        port_status = self.nfs_service.check_port_status(self.nfs_service.default_port)
        exports = self.nfs_service.get_exports()
        
        return Response({
            'configuration': db_config,
            'service_status': service_status,
            'port_status': port_status,
            'exports': exports
        })
    
    @action(detail=False, methods=['post'])
    def manage_service(self, request):
        """Manage NFS service"""
        action = request.data.get('action')
        if not action:
            return Response({'error': 'Action parameter required'}, status=400)
        
        result = self.nfs_service.manage_service(action)
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def exports(self, request):
        """Get NFS exports"""
        exports = self.nfs_service.get_exports()
        return Response({'exports': exports})
    
    @action(detail=False, methods=['get'])
    def mounts(self, request):
        """Get active NFS mounts"""
        mounts = self.nfs_service.get_active_mounts()
        return Response({'mounts': mounts})
    
    @action(detail=False, methods=['post'])
    def export_path(self, request):
        """Export a new path via NFS"""
        path = request.data.get('path')
        client = request.data.get('client', '*')
        options = request.data.get('options', ['rw', 'sync', 'no_subtree_check'])
        
        if not path:
            return Response({'error': 'Path parameter required'}, status=400)
        
        result = self.nfs_service.export_filesystem(path, client, options)
        return Response(result)
    
    @action(detail=False, methods=['post'])
    def unexport_path(self, request):
        """Remove NFS export"""
        path = request.data.get('path')
        if not path:
            return Response({'error': 'Path parameter required'}, status=400)
        
        result = self.nfs_service.unexport_filesystem(path)
        return Response(result)


@method_decorator(csrf_exempt, name='dispatch')
class FTPServiceViewSet(viewsets.ViewSet):
    """ViewSet for FTP service management"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ftp_service = FTPService()
    
    def list(self, request):
        """Get FTP service status and configuration"""
        # Get database settings
        ftp_setting = FTPSetting.objects.first()
        db_config = {}
        if ftp_setting:
            db_config = {
                'enabled': ftp_setting.enabled,
                'port': ftp_setting.port,
                'max_clients': ftp_setting.max_clients,
                'max_per_ip': ftp_setting.max_per_ip,
                'anonymous_access': ftp_setting.anonymous_access,
                'local_user_access': ftp_setting.local_user_access,
                'passive_ports_min': ftp_setting.passive_ports_min,
                'passive_ports_max': ftp_setting.passive_ports_max,
                'tls_enabled': ftp_setting.tls_enabled
            }
        
        # Get live service status
        service_status = self.ftp_service.get_service_status()
        port_status = self.ftp_service.check_port_status(self.ftp_service.default_port)
        connections = self.ftp_service.get_active_connections()
        
        return Response({
            'configuration': db_config,
            'service_status': service_status,
            'port_status': port_status,
            'connections': connections
        })
    
    @action(detail=False, methods=['post'])
    def manage_service(self, request):
        """Manage FTP service"""
        action = request.data.get('action')
        if not action:
            return Response({'error': 'Action parameter required'}, status=400)
        
        result = self.ftp_service.manage_service(action)
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def connections(self, request):
        """Get active FTP connections"""
        connections = self.ftp_service.get_active_connections()
        return Response({'connections': connections})
    
    @action(detail=False, methods=['post'])
    def test_login(self, request):
        """Test FTP login"""
        username = request.data.get('username', 'anonymous')
        password = request.data.get('password', '')
        
        result = self.ftp_service.test_ftp_login(username, password)
        return Response(result)


@method_decorator(csrf_exempt, name='dispatch')
class SSHServiceViewSet(viewsets.ViewSet):
    """ViewSet for SSH service management"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssh_service = SSHService()
    
    def list(self, request):
        """Get SSH service status and configuration"""
        # Get database settings
        ssh_setting = SSHSetting.objects.first()
        db_config = {}
        if ssh_setting:
            db_config = {
                'enabled': ssh_setting.enabled,
                'port': ssh_setting.port,
                'permit_root_login': ssh_setting.permit_root_login,
                'password_authentication': ssh_setting.password_authentication,
                'pubkey_authentication': ssh_setting.pubkey_authentication,
                'x11_forwarding': ssh_setting.x11_forwarding,
                'max_auth_tries': ssh_setting.max_auth_tries,
                'client_alive_interval': ssh_setting.client_alive_interval
            }
        
        # Get live service status
        service_status = self.ssh_service.get_service_status()
        port_status = self.ssh_service.check_port_status(self.ssh_service.default_port)
        sessions = self.ssh_service.get_active_sessions()
        
        return Response({
            'configuration': db_config,
            'service_status': service_status,
            'port_status': port_status,
            'sessions': sessions
        })
    
    @action(detail=False, methods=['post'])
    def manage_service(self, request):
        """Manage SSH service"""
        action = request.data.get('action')
        if not action:
            return Response({'error': 'Action parameter required'}, status=400)
        
        result = self.ssh_service.manage_service(action)
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def sessions(self, request):
        """Get active SSH sessions"""
        sessions = self.ssh_service.get_active_sessions()
        return Response({'sessions': sessions})
    
    @action(detail=False, methods=['get'])
    def failed_logins(self, request):
        """Get recent failed SSH login attempts"""
        lines = int(request.query_params.get('lines', 50))
        failed_logins = self.ssh_service.get_failed_logins(lines)
        return Response({'failed_logins': failed_logins})


@method_decorator(csrf_exempt, name='dispatch')
class FirewallViewSet(viewsets.ViewSet):
    """ViewSet for firewall management"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.firewall_service = FirewallService()
    
    def list(self, request):
        """Get firewall status and rules"""
        status = self.firewall_service.get_firewall_status()
        return Response(status)
    
    @action(detail=False, methods=['post'])
    def open_port(self, request):
        """Open a port in the firewall"""
        port = request.data.get('port')
        protocol = request.data.get('protocol', 'tcp')
        
        if not port:
            return Response({'error': 'Port parameter required'}, status=400)
        
        try:
            port = int(port)
            result = self.firewall_service.open_port(port, protocol)
            return Response(result)
        except ValueError:
            return Response({'error': 'Invalid port number'}, status=400)


@csrf_exempt
@api_view(['GET'])
def network_services(request):
    """Get network services configuration"""
    try:
        data = {
            'smb': {},
            'nfs': {},
            'ftp': {},
            'ssh': {}
        }
        
        # Get SMB settings
        smb = SambaSetting.objects.first()
        if smb:
            data['smb'] = {
                'workgroup': smb.workgroup,
                'server_string': smb.server_string,
                'netbios_name': smb.netbios_name,
                'security': smb.security,
                'guest_account': smb.guest_account,
                'enable_recycle_bin': smb.enable_recycle_bin,
                'audit_enable': smb.audit_enable
            }
        
        # Get NFS settings
        nfs = NFSSetting.objects.first()
        if nfs:
            data['nfs'] = {
                'nfs_v3_enabled': nfs.nfs_v3_enabled,
                'nfs_v4_enabled': nfs.nfs_v4_enabled,
                'rpc_mountd_port': nfs.rpc_mountd_port,
                'rpc_statd_port': nfs.rpc_statd_port,
                'rpc_lockd_port': nfs.rpc_lockd_port,
                'enable_udp': nfs.enable_udp,
                'servers': nfs.servers
            }
        
        # Get FTP settings
        ftp = FTPSetting.objects.first()
        if ftp:
            data['ftp'] = {
                'enabled': ftp.enabled,
                'port': ftp.port,
                'max_clients': ftp.max_clients,
                'max_per_ip': ftp.max_per_ip,
                'anonymous_access': ftp.anonymous_access,
                'local_user_access': ftp.local_user_access,
                'passive_ports_min': ftp.passive_ports_min,
                'passive_ports_max': ftp.passive_ports_max,
                'tls_enabled': ftp.tls_enabled
            }
        
        # Get SSH settings
        ssh = SSHSetting.objects.first()
        if ssh:
            data['ssh'] = {
                'enabled': ssh.enabled,
                'port': ssh.port,
                'permit_root_login': ssh.permit_root_login,
                'password_authentication': ssh.password_authentication,
                'pubkey_authentication': ssh.pubkey_authentication,
                'x11_forwarding': ssh.x11_forwarding,
                'max_auth_tries': ssh.max_auth_tries,
                'client_alive_interval': ssh.client_alive_interval
            }
        
        return Response(data)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@csrf_exempt
def network_dashboard(request):
    """Network services dashboard"""
    data = {
        'title': 'Network Services',
        'services': ['SMB', 'NFS', 'FTP', 'SSH'],
    }
    return JsonResponse(data)


@csrf_exempt
def network_stats(request):
    """Get network statistics for dashboard"""
    try:
        interfaces = NetworkInterface.objects.all()
        stats = {
            'total_interfaces': interfaces.count(),
            'active_interfaces': interfaces.filter(enabled=True).count(),
            'dhcp_interfaces': interfaces.filter(dhcp_enabled=True).count(),
            'static_interfaces': interfaces.filter(dhcp_enabled=False).count(),
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
