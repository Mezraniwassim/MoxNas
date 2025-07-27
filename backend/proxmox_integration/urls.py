"""
URL patterns for Proxmox Integration app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'hosts', views.ProxmoxHostViewSet)
router.register(r'nodes', views.ProxmoxNodeViewSet)
router.register(r'containers', views.ProxmoxContainerViewSet)
router.register(r'storage', views.ProxmoxStorageViewSet)
router.register(r'tasks', views.ProxmoxTaskViewSet)

app_name = 'proxmox_integration'

urlpatterns = [
    # API endpoints (ViewSets via router)
    path('api/', include(router.urls)),
    
    # Function-based views for specific operations
    path('connect/', views.connect_proxmox, name='connect-proxmox'),
    path('config/', views.get_frontend_config, name='frontend-config'),
    
    # Real-time monitoring endpoints
    path('realtime/data/', views.get_realtime_data, name='realtime-data'),
    path('realtime/start/', views.start_realtime_monitoring_view, name='start-realtime'),
    path('realtime/stop/', views.stop_realtime_monitoring_view, name='stop-realtime'),
]