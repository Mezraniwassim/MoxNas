"""
Health check API endpoints for MoxNAS
"""

import time
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .health import health_checker


@require_http_methods(["GET"])
@never_cache
def health_check(request):
    """
    Basic health check endpoint for load balancers and monitoring systems.
    Returns 200 if the system is healthy, 503 if critical issues are detected.
    """
    try:
        # Run basic checks only
        db_check = health_checker.check_database()
        
        if db_check['status'] == 'critical':
            return JsonResponse({
                'status': 'unhealthy',
                'message': 'Critical system issues detected',
                'timestamp': time.time()
            }, status=503)
        
        return JsonResponse({
            'status': 'healthy',
            'message': 'System is operational',
            'timestamp': time.time()
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'message': f'Health check failed: {str(e)}',
            'timestamp': time.time()
        }, status=503)


@require_http_methods(["GET"])
@never_cache
def readiness_check(request):
    """
    Readiness check for Kubernetes/container orchestration.
    Returns 200 when the application is ready to serve traffic.
    """
    try:
        # Check if critical services are ready
        db_check = health_checker.check_database()
        service_check = health_checker.check_services()
        
        critical_issues = []
        
        if db_check['status'] == 'critical':
            critical_issues.append('Database not ready')
        
        if service_check['status'] == 'critical':
            critical_issues.append('Critical services not ready')
        
        if critical_issues:
            return JsonResponse({
                'status': 'not_ready',
                'message': 'Application not ready to serve traffic',
                'issues': critical_issues,
                'timestamp': time.time()
            }, status=503)
        
        return JsonResponse({
            'status': 'ready',
            'message': 'Application is ready to serve traffic',
            'timestamp': time.time()
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'not_ready',
            'message': f'Readiness check failed: {str(e)}',
            'timestamp': time.time()
        }, status=503)


@require_http_methods(["GET"])
@never_cache
def liveness_check(request):
    """
    Liveness check for Kubernetes/container orchestration.
    Returns 200 if the application process is alive and functioning.
    """
    try:
        # Very basic check - if we can respond, we're alive
        return JsonResponse({
            'status': 'alive',
            'message': 'Application process is alive',
            'timestamp': time.time()
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'dead',
            'message': f'Liveness check failed: {str(e)}',
            'timestamp': time.time()
        }, status=503)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detailed_health_check(request):
    """
    Comprehensive health check with detailed information.
    Requires authentication and provides full system status.
    """
    try:
        health_result = health_checker.run_all_checks()
        
        # Determine HTTP status code based on overall health
        if health_result['status'] == 'critical':
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_result['status'] == 'warning':
            http_status = status.HTTP_200_OK  # Still operational, but with warnings
        else:
            http_status = status.HTTP_200_OK
        
        return Response(health_result, status=http_status)
        
    except Exception as e:
        return Response({
            'status': 'critical',
            'message': f'Health check system failed: {str(e)}',
            'timestamp': time.time(),
            'checks': {}
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_metrics(request):
    """
    System performance metrics endpoint.
    Returns detailed performance and resource usage metrics.
    """
    try:
        # Get system metrics
        system_check = health_checker.check_system()
        storage_check = health_checker.check_storage()
        network_check = health_checker.check_network()
        
        metrics = {
            'timestamp': time.time(),
            'system': system_check['details'],
            'storage': storage_check['details'],
            'network': network_check['details']
        }
        
        return Response(metrics)
        
    except Exception as e:
        return Response({
            'error': f'Failed to collect metrics: {str(e)}',
            'timestamp': time.time()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def version_info(request):
    """
    Application version and build information.
    Public endpoint that doesn't require authentication.
    """
    try:
        from django import VERSION as DJANGO_VERSION
        import sys
        
        version_data = {
            'application': 'MoxNAS',
            'version': '1.0.0',  # Should be read from version file or environment
            'build_date': '2025-01-17',  # Should be set during build
            'python_version': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            'django_version': f"{DJANGO_VERSION[0]}.{DJANGO_VERSION[1]}.{DJANGO_VERSION[2]}",
            'timestamp': time.time()
        }
        
        return Response(version_data)
        
    except Exception as e:
        return Response({
            'error': f'Failed to get version info: {str(e)}',
            'timestamp': time.time()
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)