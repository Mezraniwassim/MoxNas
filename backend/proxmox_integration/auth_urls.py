"""
URL patterns for Proxmox Authentication endpoints
"""
from django.urls import path
from . import auth_views

app_name = 'proxmox_auth'

urlpatterns = [
    # Authentication endpoints
    path('login/', auth_views.proxmox_login, name='login'),
    path('logout/', auth_views.proxmox_logout, name='logout'),
    path('session-status/', auth_views.proxmox_session_status, name='session-status'),
    
    # Proxmox API endpoints (authenticated)
    path('nodes/', auth_views.proxmox_nodes, name='nodes'),
    path('storage/', auth_views.proxmox_storage, name='storage'),
    path('containers/', auth_views.proxmox_containers, name='containers'),
    path('api-proxy/', auth_views.proxmox_api_proxy, name='api-proxy'),
    
    # Saved hosts management
    path('saved-hosts/', auth_views.get_saved_hosts, name='saved-hosts'),
]