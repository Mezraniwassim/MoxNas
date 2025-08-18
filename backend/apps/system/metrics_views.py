"""
Metrics export views for MoxNAS monitoring
"""

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .metrics import metrics_collector


@require_http_methods(["GET"])
@never_cache
def prometheus_metrics(request):
    """
    Export metrics in Prometheus format
    Public endpoint for Prometheus scraping
    """
    try:
        metrics_data = metrics_collector.collect_all_metrics()
        
        # Add Prometheus-required content type
        response = HttpResponse(
            metrics_data,
            content_type='text/plain; version=0.0.4; charset=utf-8'
        )
        
        return response
        
    except Exception as e:
        return HttpResponse(
            f"# Error collecting metrics: {str(e)}\n",
            content_type='text/plain; version=0.0.4; charset=utf-8',
            status=500
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def metrics_json(request):
    """
    Export metrics in JSON format for web interface
    Requires authentication
    """
    try:
        # Get detailed metrics for web interface
        from .health import health_checker
        
        health_result = health_checker.run_all_checks()
        
        # Combine health check with metrics
        metrics_data = {
            'timestamp': health_result['timestamp'],
            'uptime': health_result['uptime'],
            'status': health_result['status'],
            'health_checks': health_result['checks'],
            'raw_metrics': metrics_collector.collect_all_metrics()
        }
        
        return Response(metrics_data)
        
    except Exception as e:
        return Response({
            'error': f'Failed to collect metrics: {str(e)}',
            'timestamp': time.time()
        }, status=500)