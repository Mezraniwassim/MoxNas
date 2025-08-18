"""
URL configuration for MoxNAS project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# API URL patterns
api_patterns = [
    path('storage/', include('apps.storage.urls')),
    path('shares/', include('apps.shares.urls')),
    path('users/', include('apps.users.urls')),
    path('network/', include('apps.network.urls')),
    path('services/', include('apps.services.urls')),
    path('system/', include('apps.system.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_patterns)),
    # Serve React app for all other routes
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
]

# Serve static and media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)