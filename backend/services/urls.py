from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'config', views.ServiceConfigViewSet)
router.register(r'cloud-sync', views.CloudSyncTaskViewSet)
router.register(r'rsync', views.RsyncTaskViewSet)
router.register(r'task-logs', views.TaskLogViewSet)
router.register(r'ups', views.UPSConfigViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('status/', views.services_status, name='services-status'),
    path('restart/<str:service_name>/', views.restart_service, name='restart-service'),
    path('start/<str:service_name>/', views.start_service, name='start-service'),
    path('stop/<str:service_name>/', views.stop_service, name='stop-service'),
    path('cloud-sync/<int:pk>/run/', views.run_cloud_sync_task, name='run-cloud-sync'),
    path('rsync/<int:pk>/run/', views.run_rsync_task, name='run-rsync'),
]