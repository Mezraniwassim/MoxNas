from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'pools', views.StoragePoolViewSet)
router.register(r'datasets', views.DatasetViewSet)
router.register(r'shares', views.ShareViewSet)
router.register(r'acls', views.AccessControlListViewSet)
router.register(r'iscsi', views.ISCSIViewSet, basename='iscsi')
router.register(r'backups', views.BackupViewSet, basename='backups')

urlpatterns = [
    # Custom endpoints (must come before router patterns)
    path('stats/', views.storage_stats, name='storage_stats'),
    path('monitoring/', views.storage_monitoring, name='storage_monitoring'),
    path('shares/stats/', views.shares_stats, name='shares_stats'),
    
    # Web interface views
    path('dashboard/', views.storage_dashboard, name='storage_dashboard'),
    path('shares/dashboard/', views.shares_dashboard, name='shares_dashboard'),
    path('iscsi/dashboard/', views.iscsi_dashboard, name='iscsi_dashboard'),
    path('backups/dashboard/', views.backup_dashboard, name='backup_dashboard'),
    
    # API endpoints (router patterns)
    path('', include(router.urls)),
]
