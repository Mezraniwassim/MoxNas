from django.urls import path
from . import views

app_name = 'proxmox'

urlpatterns = [
    path('dashboard/', views.ProxmoxDashboardView.as_view(), name='dashboard'),
    path('nodes/', views.ProxmoxNodesView.as_view(), name='nodes'),
    path('nodes/<str:node_name>/status/', views.ProxmoxNodeStatusView.as_view(), name='node-status'),
    path('containers/', views.ProxmoxContainersView.as_view(), name='containers'),
    path('containers/<int:vmid>/', views.ProxmoxContainerDetailView.as_view(), name='container-detail'),
    path('containers/<int:vmid>/<str:action>/', views.ProxmoxContainerActionView.as_view(), name='container-action'),
    path('containers/<int:vmid>/exec/', views.ProxmoxContainerExecView.as_view(), name='container-exec'),
    path('test-connection/', views.ProxmoxTestConnectionView.as_view(), name='test-connection'),
]