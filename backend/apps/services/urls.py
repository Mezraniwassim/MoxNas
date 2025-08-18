from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('control/', views.control_service, name='control_service'),
    path('status/', views.service_status, name='service_status'),
    path('regenerate-config/', views.regenerate_config, name='regenerate_config'),
    path('test-config/', views.test_configuration, name='test_config'),
]