from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated


class ServiceConfigView(APIView):
    """Manage NAS service configurations"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'message': 'Service configuration endpoints',
            'available_services': ['ftp', 'nfs', 'smb', 'ssh', 'webdav']
        })


class ServiceStatusView(APIView):
    """Get status of all services"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'services': {
                'ftp': {'status': 'stopped', 'port': 21},
                'nfs': {'status': 'stopped', 'port': 2049},
                'smb': {'status': 'stopped', 'port': 445},
                'ssh': {'status': 'running', 'port': 22},
            }
        })