from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import SystemInfo, ServiceStatus, LogEntry
from .serializers import SystemInfoSerializer, ServiceStatusSerializer, LogEntrySerializer
from services.service_manager import ServiceManager, SystemInfoManager
import subprocess
import socket

class SystemInfoViewSet(viewsets.ModelViewSet):
    queryset = SystemInfo.objects.all()
    serializer_class = SystemInfoSerializer
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.system_manager = SystemInfoManager()
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current system information with real-time stats"""
        try:
            # Get real-time system stats
            stats = self.system_manager.get_system_stats()
            
            # Update or create system info record
            system_info = SystemInfo.objects.first()
            if not system_info:
                system_info = SystemInfo.objects.create(
                    hostname=stats.get('hostname', socket.gethostname()),
                    uptime=stats.get('uptime', 0)
                )
            else:
                system_info.hostname = stats.get('hostname', system_info.hostname)
                system_info.uptime = stats.get('uptime', 0)
                system_info.save()
            
            # Combine database info with real-time stats
            response_data = {
                'id': system_info.id,
                'hostname': system_info.hostname,
                'version': system_info.version,
                'uptime': system_info.uptime,
                'last_updated': system_info.last_updated,
                'cpu_usage': stats.get('cpu_usage', 0),
                'memory_usage': stats.get('memory_usage', {}),
                'disk_usage': stats.get('disk_usage', {}),
                'network_interfaces': stats.get('network_interfaces', [])
            }
            
            return Response(response_data)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ServiceStatusViewSet(viewsets.ModelViewSet):
    queryset = ServiceStatus.objects.all()
    serializer_class = ServiceStatusSerializer
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_manager = ServiceManager()
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a service"""
        service = get_object_or_404(ServiceStatus, pk=pk)
        
        # Map service names to systemd service names
        service_map = {
            'smb': 'smbd',
            'nfs': 'nfs-kernel-server',
            'ftp': 'vsftpd',
            'ssh': 'ssh',
            'snmp': 'snmpd',
            'iscsi': 'tgt'
        }
        
        systemd_name = service_map.get(service.name, service.name)
        success = self.service_manager.start_service(systemd_name)
        service.running = success
        service.save()
        
        return Response({
            'success': success,
            'message': f"Service {service.name} {'started' if success else 'failed to start'}"
        })
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """Stop a service"""
        service = get_object_or_404(ServiceStatus, pk=pk)
        
        service_map = {
            'smb': 'smbd',
            'nfs': 'nfs-kernel-server',
            'ftp': 'vsftpd',
            'ssh': 'ssh',
            'snmp': 'snmpd',
            'iscsi': 'tgt'
        }
        
        systemd_name = service_map.get(service.name, service.name)
        success = self.service_manager.stop_service(systemd_name)
        service.running = not success if success else False
        service.save()
        
        return Response({
            'success': success,
            'message': f"Service {service.name} {'stopped' if success else 'failed to stop'}"
        })
    
    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        """Restart a service"""
        service = get_object_or_404(ServiceStatus, pk=pk)
        
        service_map = {
            'smb': 'smbd',
            'nfs': 'nfs-kernel-server',
            'ftp': 'vsftpd',
            'ssh': 'ssh',
            'snmp': 'snmpd',
            'iscsi': 'tgt'
        }
        
        systemd_name = service_map.get(service.name, service.name)
        success = self.service_manager.restart_service(systemd_name)
        service.running = success
        service.save()
        
        return Response({
            'success': success,
            'message': f"Service {service.name} {'restarted' if success else 'failed to restart'}"
        })
    
    @action(detail=False, methods=['get'])
    def status_all(self, request):
        """Get status of all services"""
        service_map = {
            'smb': 'smbd',
            'nfs': 'nfs-kernel-server',
            'ftp': 'vsftpd',
            'ssh': 'ssh',
            'snmp': 'snmpd',
            'iscsi': 'tgt'
        }
        
        services = []
        for service in self.queryset:
            systemd_name = service_map.get(service.name, service.name)
            service.running = self.service_manager.is_service_running(systemd_name)
            service.save()
            services.append(service)
        
        serializer = self.get_serializer(services, many=True)
        return Response(serializer.data)

class LogEntryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LogEntry.objects.all()
    serializer_class = LogEntrySerializer
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent log entries"""
        logs = self.queryset[:50]  # Last 50 entries
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)