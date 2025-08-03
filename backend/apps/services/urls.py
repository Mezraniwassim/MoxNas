from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.ServiceConfigView.as_view(), name='service-config'),
    path('status/', views.ServiceStatusView.as_view(), name='service-status'),
]