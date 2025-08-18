from django.urls import path
from . import views, health_views, metrics_views

urlpatterns = [
    # Health check endpoints (for load balancers and monitoring)
    path('health/', health_views.health_check, name='health_check'),
    path('health/ready/', health_views.readiness_check, name='readiness_check'),
    path('health/live/', health_views.liveness_check, name='liveness_check'),
    path('health/detailed/', health_views.detailed_health_check, name='detailed_health_check'),
    path('metrics/', health_views.system_metrics, name='system_metrics'),
    path('version/', health_views.version_info, name='version_info'),
    
    # Metrics export endpoints
    path('metrics/prometheus/', metrics_views.prometheus_metrics, name='prometheus_metrics'),
    path('metrics/json/', metrics_views.metrics_json, name='metrics_json'),
    
    # System monitoring endpoints
    path('stats/', views.system_stats, name='system_stats'),
    path('info/', views.system_info, name='system_info'),
    path('logs/', views.system_logs, name='system_logs'),
    
    # System settings endpoints
    path('settings/', views.system_settings_list, name='system_settings'),
    path('settings/update/', views.system_settings_update, name='system_settings_update'),
    
    # System control endpoints
    path('reboot/', views.system_reboot, name='system_reboot'),
    path('shutdown/', views.system_shutdown, name='system_shutdown'),
]