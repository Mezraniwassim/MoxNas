"""
URL patterns for Proxmox integration
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'hosts', views.ProxmoxHostViewSet)
router.register(r'nodes', views.ProxmoxNodeViewSet)
router.register(r'containers', views.ProxmoxContainerViewSet)
router.register(r'storage', views.ProxmoxStorageViewSet)

app_name = 'proxmox_integration'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Configuration endpoint (safe values only)
    path('api/config/', views.get_frontend_config, name='frontend-config'),
    
    # Additional endpoints
    path('api/connect/', views.connect_proxmox, name='connect'),
    path('api/sync/', views.sync_proxmox_data, name='sync'),
    path('api/cluster-status/', views.proxmox_cluster_status, name='cluster-status'),
    
    # Real-time monitoring endpoints
    path('api/realtime/dashboard/', views.realtime_dashboard, name='realtime-dashboard'),
    path('api/realtime/node/<str:node_name>/', views.realtime_node_data, name='realtime-node'),
    path('api/realtime/container/<str:node_name>/<int:vmid>/', views.realtime_container_data, name='realtime-container'),
    path('api/monitoring/start/', views.start_monitoring, name='start-monitoring'),
    path('api/monitoring/stop/', views.stop_monitoring, name='stop-monitoring'),
    path('api/monitoring/status/', views.monitoring_status, name='monitoring-status'),
]
