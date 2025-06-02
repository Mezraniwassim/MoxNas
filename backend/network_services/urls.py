from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'interfaces', views.NetworkInterfaceViewSet)
router.register(r'smb', views.SMBServiceViewSet, basename='smb')
router.register(r'nfs', views.NFSServiceViewSet, basename='nfs')
router.register(r'ftp', views.FTPServiceViewSet, basename='ftp')
router.register(r'ssh', views.SSHServiceViewSet, basename='ssh')
router.register(r'firewall', views.FirewallViewSet, basename='firewall')

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    path('services/', views.network_services, name='network_services'),
    path('stats/', views.network_stats, name='network_stats'),
    
    # Web interface
    path('dashboard/', views.network_dashboard, name='network_dashboard'),
]
