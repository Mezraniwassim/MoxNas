from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, setup_views

router = DefaultRouter()
router.register(r'system', views.SystemInfoViewSet)
router.register(r'services', views.ServiceStatusViewSet)
router.register(r'logs', views.LogEntryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # Setup wizard endpoints
    path('setup/network-info/', setup_views.get_network_info, name='setup_network_info'),
    path('setup/test-proxmox/', setup_views.test_proxmox_connection, name='setup_test_proxmox'),
    path('setup/save-proxmox/', setup_views.save_proxmox_config, name='setup_save_proxmox'),
    path('setup/status/', setup_views.get_setup_status, name='setup_status'),
    path('setup/restart/', setup_views.restart_moxnas, name='setup_restart'),
]