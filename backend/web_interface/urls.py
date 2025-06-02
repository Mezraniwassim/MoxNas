from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.http import FileResponse, Http404
from rest_framework.routers import DefaultRouter
import os
from . import views

def serve_frontend_static(request, path):
    """Serve frontend static files"""
    frontend_static_path = os.path.join(settings.BASE_DIR.parent, 'frontend', path)
    if os.path.exists(frontend_static_path):
        return serve(request, path, document_root=os.path.join(settings.BASE_DIR.parent, 'frontend'))
    raise Http404("File not found")

router = DefaultRouter()

urlpatterns = [
    # Frontend static files
    path('src/<path:path>', serve_frontend_static, name='frontend_static'),
    
    # API endpoints
    path('api/', include(router.urls)),
    path('api/status/', views.api_status, name='api_status'),
    path('api/system-info/', views.api_system_info, name='api_system_info'),
    
    # Enhanced API endpoints for TrueNAS-style dashboard
    path('api/system/', views.SystemAPIView.as_view(), name='api_system'),
    path('api/tasks/', views.TaskManagerAPIView.as_view(), name='api_tasks'),
    path('api/services/control/', views.ServiceControlAPIView.as_view(), name='api_service_control'),
    path('api/realtime/', views.RealtimeDataAPIView.as_view(), name='api_realtime'),
    
    # Main web interface
    path('', views.MainDashboardView.as_view(), name='main_dashboard'),
    path('dashboard/', views.MainDashboardView.as_view(), name='dashboard'),
    path('forms/', views.FormExampleView.as_view(), name='form_examples'),
]
