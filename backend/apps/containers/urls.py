from django.urls import path
from . import views

app_name = 'containers'

urlpatterns = [
    path('', views.ContainerListView.as_view(), name='container-list'),
    path('stats/', views.ContainerStatsView.as_view(), name='container-stats'),
    path('<int:vmid>/', views.ContainerDetailView.as_view(), name='container-detail'),
    path('<int:vmid>/<str:action>/', views.ContainerActionView.as_view(), name='container-action'),
    path('<int:vmid>/services/', views.ContainerServicesView.as_view(), name='container-services'),
    path('<int:vmid>/services/<str:service_type>/<str:action>/', views.ContainerServiceActionView.as_view(), name='service-action'),
]