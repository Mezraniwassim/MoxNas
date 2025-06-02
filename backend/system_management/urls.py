from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'services', views.SystemServiceViewSet)
router.register(r'cron-jobs', views.CronJobViewSet)
router.register(r'sync-tasks', views.SyncTaskViewSet)

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    path('info/', views.system_info, name='system_info'),
    path('logs/', views.system_logs, name='system_logs'),
    
    # Web interface
    path('dashboard/', views.system_dashboard, name='system_dashboard'),
]
