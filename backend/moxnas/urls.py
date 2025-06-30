"""
MoxNAS URL Configuration
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/core/', include('core.urls')),
    path('api/storage/', include('storage.urls')),
    path('api/services/', include('services.urls')),
    path('api/network/', include('network.urls')),
    path('api/users/', include('users.urls')),
    path('api/proxmox/', include('proxmox.urls')),
]

# Serve React app for all non-API routes
REACT_BUILD_DIR = os.path.join(settings.BASE_DIR.parent, 'frontend', 'build')
if os.path.exists(REACT_BUILD_DIR):
    urlpatterns += [
        re_path(r'^(?!api/)(?!admin/)(?!static/).*$', TemplateView.as_view(template_name='index.html'), name='index'),
    ]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)